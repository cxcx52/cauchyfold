#!/usr/bin/env python3
"""Opt-in estimator rerun, isolated from the published raw records."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=Path('build-estimator'))
    ap.add_argument('--upstream', type=Path, default=Path('vendor/lattice-estimator'))
    args = ap.parse_args()
    output = (ROOT / args.output).resolve()
    upstream = (ROOT / args.upstream).resolve()
    assert not output.exists(), 'Use a new directory; published records are immutable.'
    assert (ROOT / 'build/reproduction_report.json').exists(), 'Run default exact reproduction first.'
    assert upstream.is_dir(), 'Clone the pinned official estimator into vendor/lattice-estimator first.'
    output.mkdir(parents=True)
    for name in ('compiler_manifest.json', 'node_registry.json', 'candidate_backend_inputs.json', 'backend_inputs.json'):
        shutil.copyfile(ROOT / 'build' / name, output / name)
    shutil.copytree(ROOT / 'build/estimator_inputs', output / 'estimator_inputs')
    env = dict(os.environ, CFDAGGER_RUN_DIR=str(output), CFDAGGER_ESTIMATOR_PATH=str(upstream))
    subprocess.run([sys.executable, str(ROOT / 'estimator/run_official_estimator.py'), '--include-ready-frontends'], env=env, check=True)


if __name__ == '__main__':
    main()
