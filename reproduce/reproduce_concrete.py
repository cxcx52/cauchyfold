#!/usr/bin/env python3
"""Rebuild the paper instance and compare exact outputs with published hashes."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.set_int_max_str_digits(0)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def read(path):
    return json.loads(path.read_bytes())


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(output):
    assert not output.exists(), 'Use a new output directory; existing evidence is never overwritten.'
    output.mkdir(parents=True)
    sources = {
        'compiler/build_cfdagger_frontend.py': 'build_cfdagger_frontend.py',
        'compiler/compiler_manifest.schema.json': 'compiler_manifest.schema.json',
        'relation/relation_spec.json': 'relation_spec.json',
        'parameters/parameters.json': 'parameters.json',
        'parameters/expected_schedule.json': 'expected_schedule.json',
        'parameters/prime_certificate.json': 'prime_certificate.json',
        'parameters/backend_inputs.json': 'backend_inputs.json',
        'reproduce/core.py': 'core.py',
        'reproduce/cost_formulas.py': 'cost_formulas.py',
        'checks/field_certificate.py': 'field_certificate.py',
        'checks/wire_codec.py': 'wire_codec.py',
        'estimator/run_official_estimator.py': 'run_official_estimator.py',
        'estimator/environment.json': 'estimator_environment.json',
    }
    for source, target in sources.items():
        shutil.copyfile(ROOT / source, output / target)
    shutil.copyfile(ROOT / 'parameters/backend_inputs.json', output / 'candidate_backend_inputs.json')
    shutil.copytree(ROOT / 'estimator/raw', output / 'estimator_raw')
    subprocess.run([sys.executable, '-X', 'utf8', '-u', str(output / 'build_cfdagger_frontend.py')], cwd=output, check=True)
    core = load_module('concrete_core', output / 'core.py')
    p = core.load('parameters.json')
    c = core.load('compiler_manifest.json')
    core.validate_compiler(p, c)
    assert p['profile'] == 'I' and p['cauchy']['arity'] == 16
    assert c['status'] == 'COMPLETE'
    tests = core.load('compiler_tests.json')
    assert tests['status'] == 'PASS' and all(t['status'] == 'PASS' for t in tests['test_results'])
    field = load_module('field_check', output / 'field_certificate.py')
    core.put('field_certificate.json', field.verify_prime_and_field())
    layers = core.build_layers(p)
    core.put('reduction_schedule.json', {'profile': 'I', 'k': 16, 'source_schedule_match': True, 'layers': layers})
    registry = core.registry(p, layers, c)
    assert len(registry['roles']) == registry['independent_matrix_count'] == 20
    core.put('node_registry.json', registry)
    stat, completeness = core.statistics(p, layers, c)
    core.put('statistical_security.json', stat)
    core.put('completeness.json', completeness)
    core.generate_inputs(p, registry)
    codec = load_module('wire_codec', output / 'wire_codec.py')
    core.put('serialization_checks.json', codec.check_components())
    costs = load_module('cost_formulas', output / 'cost_formulas.py')
    cost = costs.build_costs(p, layers, registry, c)
    comm, ops = cost if isinstance(cost, tuple) else (cost['communication'], cost['operations'])
    assert not comm['unresolved'] and not ops['unresolved']
    core.put('communication_ledger.json', comm)
    core.put('operation_counts.json', ops)
    estimator = load_module('official_runner', output / 'run_official_estimator.py')
    estimator.HERE = output
    estimates = estimator.summarize()
    assert estimates['task_counts'] == {'DONE_FINITE': 40}
    assert estimates['weakest_full_node_status'] == 'ALL_20_MATRICES_FINITE'
    verified = []
    for item in read(ROOT / 'checks/expected_outputs.json')['files']:
        path = output / item['path']
        data = path.read_bytes()
        assert len(data) == item['bytes'], ('byte length', item['path'])
        assert hashlib.sha256(data).hexdigest() == item['sha256'], ('SHA256 mismatch', item['path'])
        semantic = None
        if path.suffix == '.json':
            obj = json.loads(data)
            assert canonical(obj) == data, ('noncanonical JSON', item['path'])
            reference = ROOT / 'artifacts' / item['path']
            if item['path'].startswith('estimator_inputs/'):
                reference = ROOT / 'estimator/inputs' / path.name
            if reference.exists():
                assert obj == read(reference), ('semantic mismatch', item['path'])
                assert data == reference.read_bytes(), ('canonical byte mismatch', item['path'])
                semantic = True
        verified.append({**item, 'sha256_match': True, 'semantic_json_match': semantic})
    report = {'status': 'PASS', 'profile': 'I', 'k': 16, 'independent_matrices': 20,
              'recorded_estimator_outputs_validated': 40, 'estimator_attacks_executed': False,
              'benchmark_executed': False, 'full_proof_generated': False,
              'canonical_byte_and_sha256_comparison': True, 'files': verified}
    core.put('reproduction_report.json', report)
    print('PASS: exact outputs and hashes match; 20 matrices and 40 recorded estimates validated.')
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=Path('build'), help='New output path relative to the repository root, or an explicit absolute path.')
    args = ap.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    run(output.resolve())


if __name__ == '__main__':
    main()
