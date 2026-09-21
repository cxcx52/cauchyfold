#!/usr/bin/env python3
"""Check the published seeded-projection parameters and byte totals."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def main():
    parameters = load('parameters.json')
    communication = load('communication.json')
    comparison = load('comparison.json')

    assert len(parameters) == 6
    assert [row['layer'] for row in parameters] == list(range(6))
    assert all(row['seed_bytes'] == (row['seed_bits'] + 7) // 8 for row in parameters)
    assert sum(row['seed_bytes'] for row in parameters) == 52_557

    prover = communication['fold_P_to_V']['no_retry_bytes']
    verifier = communication['fold_V_to_P']['no_retry_bytes']
    total = communication['interactive_total']['no_retry_bytes']
    assert (prover, verifier, total) == (342_690, 10_341_123, 10_683_813)
    assert prover + verifier == total
    assert communication['interactive_total']['maximum_attempts_bytes'] == 19_175_844

    values = {row['metric']: row for row in comparison['communication']}
    assert values['interactive_total.no_retry_bytes']['N'] == total
    assert comparison['projection_descriptors_N'] == 52_557
    assert comparison['projection_descriptors_I'] == 472_103_424
    assert comparison['same_folding_relation'] is True
    assert comparison['same_twenty_MSIS_instances'] is True

    print('PASS: seeded-projection parameters and communication totals agree.')


if __name__ == '__main__':
    main()
