"""Execute the matched carrier compiler and small field proof; no timing comparison."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'direct'))
from run import native
import os


def call(command, name):
    with (ROOT/'logs'/name).open('wb') as log:
        subprocess.run((['wsl', '--exec'] if os.name == 'nt' else [])+command,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    print('PASS', name, flush=True)


def main():
    for name in ('build', 'results', 'logs'):
        (ROOT/name).mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(ROOT/'prepare.py')], check=True)
    for name in ('carrier', 'field'):
        call(['g++', '-O3', '-std=c++17', native(ROOT/'src'/(name+'.cpp')),
              '-o', native(ROOT/'build'/name)], name+'-build.log')
    for k in (4, 1024):
        folder = ROOT/'results'/f'arity-{k}'
        folder.mkdir(exist_ok=True)
        for op in ('compile', 'verify'):
            call([native(ROOT/'build/carrier'), op, str(k), native(folder)], f'{k}-{op}.log')
        if k == 4:
            call([native(ROOT/'build/carrier'), 'second', str(k), native(folder)], '4-second.log')
            for op in ('prove', 'verify'):
                call([native(ROOT/'build/field'), op, str(k), native(folder)], '4-field-'+op+'.log')


if __name__ == '__main__':
    main()
