"""Build and check the deterministic relation compiler on Linux or WSL."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def native_path(path):
    path = Path(path).resolve()
    if os.name == 'nt':
        drive = path.drive.rstrip(':').lower()
        return '/mnt/' + drive + '/' + '/'.join(path.parts[1:])
    return str(path)


def run(command):
    subprocess.run((['wsl', '--exec'] if os.name == 'nt' else []) + command, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arity', type=int, default=4)
    parser.add_argument('--mode', choices=['special', 'prefix'], default='special')
    parser.add_argument('--check-layout', action='store_true', help='also check every sparse row with NumPy')
    args = parser.parse_args()
    if not 1 <= args.arity <= 1024:
        parser.error('arity must be between 1 and 1024')
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    for name in ('compile', 'sumcheck', 'check_handoff', 'check_commitments'):
        run(['g++', '-O3', '-std=c++17', native_path(ROOT / 'src' / (name + '.cpp')),
             '-o', native_path(build / name)])
    circuit = build / f'{args.mode}-{args.arity}'
    field = build / f'{args.mode}-{args.arity}-field'
    for operation in ('compile', 'verify', 'second', 'negative'):
        run([native_path(build / 'compile'), operation, str(args.arity), args.mode, native_path(circuit)])
    run([native_path(build / 'sumcheck'), native_path(circuit), native_path(field), '6'])
    run([native_path(build / 'check_handoff'), str(args.arity), args.mode, native_path(circuit), native_path(field)])
    run([native_path(build / 'check_commitments'), args.mode, native_path(build / (args.mode + '_commitments.json'))])
    if args.check_layout:
        subprocess.run([sys.executable, str(ROOT / 'checks' / 'layout.py'), '--arity', str(args.arity),
                        '--mode', args.mode], check=True)
    print('Compiler and field checks completed.')


if __name__ == '__main__':
    main()
