"""Build the independent direct field-reduction experiment on Linux or WSL."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def native(path):
    path = Path(path).resolve()
    if os.name == 'nt':
        return '/mnt/' + path.drive[0].lower() + '/' + '/'.join(path.parts[1:])
    return str(path)


def run(command, log):
    with (ROOT/'logs'/log).open('wb') as output:
        subprocess.run((['wsl', '--exec'] if os.name == 'nt' else []) + command,
                       stdout=output, stderr=subprocess.STDOUT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arity', type=int, default=4)
    parser.add_argument('--skip-build', action='store_true')
    parser.add_argument('--extended-checks', action='store_true')
    args = parser.parse_args()
    for name in ('build', 'logs', 'results'):
        (ROOT/name).mkdir(exist_ok=True)
    if not args.skip_build:
        for tool in ('direct', 'field', 'commitments'):
            run(['g++', '-O3', '-std=c++17', native(ROOT/'src'/(tool+'.cpp')),
                 '-o', native(ROOT/'build'/tool)], tool+'-build.log')
    run([native(ROOT/'build/commitments'), native(ROOT/'results/commitments.json')], 'commitments.log')
    out = ROOT/'results'/f'arity-{args.arity}'
    for op in ['compile', 'verify'] + (['second', 'negative'] if args.extended_checks else []):
        run([native(ROOT/'build/direct'), op, str(args.arity), native(out)], f'{args.arity}-{op}.log')
        print(f'PASS {op} k={args.arity}', flush=True)
    for op in ('prove', 'verify'):
        run([native(ROOT/'build/field'), op, str(args.arity), native(out)], f'{args.arity}-field-{op}.log')
        print(f'PASS field {op} k={args.arity}', flush=True)


if __name__ == '__main__':
    main()
