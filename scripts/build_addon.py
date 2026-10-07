#!/usr/bin/env python3
"""Build a reproducible Blender add-on ZIP with the Python standard library."""
import argparse, ast, hashlib, json, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'chibi_generator'

def version():
    for node in ast.parse((ADDON / '__init__.py').read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'bl_info' for t in node.targets):
            return '.'.join(map(str, ast.literal_eval(node.value)['version']))
    raise RuntimeError('bl_info version is missing')

def build(destination):
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f'chibi_generator_v{version()}.zip'
    files = [(p, p.relative_to(ROOT).as_posix()) for p in sorted(ADDON.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py', '.json', '.blend', '.png'}]
    if (ROOT / 'LICENSE').exists(): files.append((ROOT / 'LICENSE', 'chibi_generator/LICENSE'))
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in sorted(files, key=lambda item: item[1]):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None: raise RuntimeError('Corrupt ZIP')
        if 'chibi_generator/__init__.py' not in archive.namelist(): raise RuntimeError('Invalid add-on root')
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(f'{checksum}  {target.name}\n', encoding='utf-8')
    print(json.dumps({'archive': str(target), 'sha256': checksum, 'files': len(files)}, indent=2))
    return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    build(parser.parse_args().output.resolve())
