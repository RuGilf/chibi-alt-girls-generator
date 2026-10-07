#!/usr/bin/env python3
"""Run integration suites using an existing Blender installation; never download Blender."""
import argparse, os, shutil, subprocess, sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SUITES = {'app': 'blender_app_checks.py', 'styles': 'blender_style_checks.py',
          'appearance': 'blender_appearance_checks.py', 'poses': 'blender_pose_checks.py'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', default=os.environ.get('BLENDER_BIN') or shutil.which('blender'))
    parser.add_argument('--suite', choices=['all', *SUITES], default='all')
    args = parser.parse_args()
    if not args.blender: parser.error('Blender was not found. Pass --blender with the path to an existing executable.')
    executable = shutil.which(args.blender) or args.blender
    folder = ROOT / 'build/test-reports'; folder.mkdir(parents=True, exist_ok=True)
    outcomes = {}
    for name in SUITES if args.suite == 'all' else [args.suite]:
        print(f'Running Blender suite: {name}', flush=True)
        with (folder / f'{name}.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([executable, '--background', '--factory-startup', '--python-exit-code', '1',
                                     '--python', str(ROOT / 'tests' / SUITES[name])], cwd=ROOT,
                                    stdout=log, stderr=subprocess.STDOUT)
        outcomes[name] = result.returncode == 0
        print(f'{name}: {"PASS" if outcomes[name] else "FAIL"}', flush=True)
        if not outcomes[name]: print((folder / f'{name}.log').read_text(encoding='utf-8', errors='replace')[-6000:])
    (folder / 'summary.json').write_text(json.dumps(outcomes, indent=2) + '\n', encoding='utf-8')
    return 0 if all(outcomes.values()) else 1

if __name__ == '__main__': sys.exit(main())
