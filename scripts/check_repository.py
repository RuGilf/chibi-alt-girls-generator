#!/usr/bin/env python3
"""Check source syntax, catalogs, public presets, links and release integrity."""
import ast
import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '__pycache__', 'build', 'dist', '.venv', 'venv'}


def main():
    errors = []
    files = [p for p in ROOT.rglob('*') if p.is_file()
             and not SKIP.intersection(p.relative_to(ROOT).parts)]
    required = ['README.md', 'README.en.md', 'CONTRIBUTING.md', 'CHANGELOG.md',
                '.gitignore', '.gitattributes', '.github/workflows/ci.yml',
                'chibi_generator/__init__.py', 'chibi_generator/assets/chibi_base.blend',
                'tests/fixtures/legacy_v07.blend', 'scripts/build_addon.py',
                'scripts/test_blender.py', 'docs/PUBLISHING.md']
    for name in required:
        if not (ROOT / name).is_file():
            errors.append(f'Missing required file: {name}')
    for path in files:
        name = path.relative_to(ROOT).as_posix()
        if path.name in {'.DS_Store', 'Thumbs.db', '.env'} or path.name.endswith(('.pyc', '.blend1')):
            errors.append(f'Unexpected local file: {name}')
        if path.suffix not in {'.py', '.md', '.json', '.yml', '.yaml', '.toml', '.txt'}:
            continue
        source = path.read_text(encoding='utf-8')
        # Construct the patterns in parts so this checker can check its own source.
        for private in ('/' + 'Users/', '/' + 'var/folders/', 'Documents/' + 'Codex'):
            if private in source:
                errors.append(f'Local machine path in {name}')
        try:
            if path.suffix == '.py':
                ast.parse(source, filename=name)
            elif path.suffix == '.json':
                json.loads(source)
        except (SyntaxError, ValueError) as exc:
            errors.append(f'{name}: {exc}')
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^\s)]+)(?:\s+[^)]*)?\)', source):
                target = target.strip('<>')
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                resolved = (path.parent / unquote(parsed.path)).resolve()
                if not resolved.is_relative_to(ROOT) or not resolved.exists():
                    errors.append(f'Broken local link in {name}: {target}')
    spec = importlib.util.spec_from_file_location('public_model', ROOT / 'chibi_generator/model.py')
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    presets = list((ROOT / 'examples').rglob('*.json'))
    for path in presets:
        try:
            model.load_preset(path)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f'Invalid public preset {path.relative_to(ROOT)}: {exc}')
    for name, choices in [('face', model.FACE_PRESETS), ('makeup', model.MAKEUP_PRESETS),
                          ('hair', model.HAIR_PRESETS), ('pose', model.POSE_PRESETS)]:
        for key in choices:
            if not (ROOT / f'chibi_generator/assets/previews/{name}_{key}.png').is_file():
                errors.append(f'Missing preview: {name}_{key}')
    archives = list((ROOT / 'releases').glob('*.zip'))
    if not archives:
        errors.append('No installable release ZIP')
    for path in archives:
        checksum_file = path.with_suffix('.zip.sha256')
        if not checksum_file.exists() or checksum_file.read_text().split()[0] != hashlib.sha256(path.read_bytes()).hexdigest():
            errors.append(f'Checksum mismatch: {path.name}')
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if archive.testzip() or 'chibi_generator/__init__.py' not in names:
                errors.append(f'Invalid add-on archive: {path.name}')
            if any(not n.startswith('chibi_generator/') or '..' in Path(n).parts for n in names):
                errors.append(f'Unexpected ZIP path: {path.name}')
            expected = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'chibi_generator').rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts
                        and p.suffix in {'.py', '.json', '.blend', '.png'}}
            if (ROOT / 'LICENSE').is_file():
                expected.add('chibi_generator/LICENSE')
            if set(names) != expected:
                errors.append(f'Release contents differ from source: {path.name}')
            for name in expected.intersection(names):
                source_path = ROOT / ('LICENSE' if name == 'chibi_generator/LICENSE' else name)
                if archive.read(name) != source_path.read_bytes():
                    errors.append(f'Rebuild release: {name} differs from source')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(files)} files, {len(presets)} public presets, Markdown links, previews and release checksums')


if __name__ == '__main__':
    main()
