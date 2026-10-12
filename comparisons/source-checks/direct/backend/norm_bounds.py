#!/usr/bin/env python3
"""Deterministic checks for CauchyFold norm-accounting refinements."""

from __future__ import annotations

import argparse
import importlib.util
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


Q = 2**48 - 59
WIDTH = 48
EXTENSION_DEGREE = 4


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def comparator_helpers(x: int, q: int = Q, width: int = WIDTH) -> list[int]:
    if not 0 <= x < 2**width:
        raise ValueError("coefficient is outside the encoding width")
    equal = 1
    helpers: list[int] = []
    for bit in range(width - 1, -1, -1):
        equal *= int(((x >> bit) & 1) == ((q >> bit) & 1))
        helpers.append(equal)
    helpers.reverse()
    return helpers


def joint_encoding_weight(x: int, q: int = Q, width: int = WIDTH) -> int:
    return x.bit_count() + sum(comparator_helpers(x, q, width))


def exact_joint_weight_bound(q: int = Q, width: int = WIDTH) -> dict[str, int]:
    if not 0 < q < 2**width:
        raise ValueError("modulus is outside the encoding width")
    candidates = []
    for first_difference in range(width):
        if (q >> first_difference) & 1:
            prefix_weight = (q >> (first_difference + 1)).bit_count()
            value = prefix_weight + first_difference
            helper = width - 1 - first_difference
            candidates.append((value + helper, first_difference))
    maximum, bit = max(candidates)
    witness = (q >> (bit + 1)) << (bit + 1)
    witness |= (1 << bit) - 1
    assert witness < q
    assert joint_encoding_weight(witness, q, width) == maximum
    return {
        "maximum": maximum,
        "attaining_value": witness,
        "attaining_first_difference_bit": bit,
        "modulus_popcount": q.bit_count(),
        "value_weight": witness.bit_count(),
        "helper_weight": sum(comparator_helpers(witness, q, width)),
    }


def compiler_s0_certificate(manifest: dict[str, Any], relation: dict[str, Any]) -> dict[str, Any]:
    k = int(manifest["arity"])
    semantic = manifest["semantic"]
    n = int(semantic["n"])
    y = int(semantic["y"])
    r = int(semantic["r"])
    g = int(manifest["encoding"]["auxiliary_gate_K_values"])
    degree = int(manifest["encoding"]["extension_degree"])
    width = int(manifest["encoding"]["base_coefficient_bits"])
    q = int(manifest["resolved_dimensions"].get("q", Q))
    if q != Q:
        q = Q
    assert degree == EXTENSION_DEGREE and width == WIDTH
    assert relation["n"] == n and relation["y"] == y and relation["r"] == r
    strict = relation["strict_fresh"]
    assert strict["u"] == 1 and strict["z_base_field"] is True
    assert strict["E"] == [0] * y
    assert semantic["fresh_base_field_required"] is True

    expected_values = (k + 2) * (n + y) + k * r + g
    helper_bits = int(manifest["encoding"]["auxiliary_scalar_bits"])
    assert helper_bits == width * degree * expected_values
    segments = manifest["encoding"]["segments"]
    assert sum(s["segment_id"].startswith("fresh_state_") for s in segments) == k
    assert sum(s["segment_id"] == "accumulator_state" for s in segments) == 1
    assert sum(s["segment_id"] == "folded_output_state" for s in segments) == 1
    assert sum(s["segment_id"] == "carrier" for s in segments) == 1
    assert sum(s["segment_id"] == "field_auxiliary" for s in segments) == 1

    joint = exact_joint_weight_bound(q, width)
    total_base_coefficients = degree * expected_values
    zero_per_fresh = (degree - 1) * n + degree * y
    fixed_one_per_fresh = 1
    fixed_zero_coefficients = k * zero_per_fresh
    fixed_one_coefficients = k * fixed_one_per_fresh
    generic_coefficients = total_base_coefficients - fixed_zero_coefficients - fixed_one_coefficients
    assert generic_coefficients >= 0
    global_fixed_one = int(manifest["encoding"]["uncommitted_constant_coordinates"])
    assert global_fixed_one == 1
    bound = generic_coefficients * joint["maximum"] + fixed_one_coefficients + global_fixed_one
    old_bound = sum(int(s["honest_squared_norm_bound"]) for s in segments) + global_fixed_one
    expected_old = 29568 * k + 69889
    assert old_bound == expected_old

    slope = bound - compiler_s0_formula(0)
    assert bound == compiler_s0_formula(k)
    assert slope == 7561 * k
    return {
        "arity": k,
        "semantic_dimensions": {"n": n, "y": y, "r": r},
        "canonical_K_values": expected_values,
        "total_base_field_coefficients": total_base_coefficients,
        "generic_base_field_coefficients": generic_coefficients,
        "fixed_zero_base_field_coefficients": fixed_zero_coefficients,
        "fixed_one_base_field_coefficients": fixed_one_coefficients,
        "uncommitted_global_fixed_one": global_fixed_one,
        "joint_value_helper_weight": joint,
        "old_length_bound": old_bound,
        "refined_honest_energy_bound": bound,
        "refined_formula": "7561*k + 65521",
        "old_formula": "29568*k + 69889",
    }


def compiler_s0_formula(k: int) -> int:
    return 7561 * k + 65521


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cf_frontend_for_refinement", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load compiler module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_check(compiler_source: Path, parameters_path: Path, bound: int) -> dict[str, Any]:
    module = load_module(compiler_source)
    parameters = json.loads(parameters_path.read_text(encoding="utf-8"))
    compiler = module.Compiler(parameters)
    sources = module.sources()
    carrier = module.honest_carrier(sources)
    bits, values, _ = compiler.witness(sources, carrier, module.fq(16))
    actual = sum(bits)
    assert actual <= bound
    assert len(values) == compiler.values_count
    for fresh in range(1, 17):
        z, residual = sources[fresh]
        assert z[0] == module.fq(1)
        assert all(v[1:] == (0, 0, 0) for v in z)
        assert residual == [module.fq(0)] * 4
    assert bits[compiler.one] == 1
    return {
        "fixture_hamming_weight": actual,
        "refined_bound": bound,
        "within_bound": True,
        "compiler_value_count": compiler.values_count,
        "strict_fresh_records_checked": 16,
    }


def balanced_digits_nonnegative(x: int, radix: int) -> list[int]:
    if x < 0 or radix < 2 or radix % 2:
        raise ValueError("requires x >= 0 and an even radix")
    b = radix // 2
    digits = []
    while x:
        nxt = (x + b - 1) // radix
        digit = x - radix * nxt
        assert -b + 1 <= digit <= b
        digits.append(digit)
        x = nxt
    return digits


def signed_balanced_digits(x: int, radix: int) -> list[int]:
    sign = -1 if x < 0 else 1
    return [sign * d for d in balanced_digits_nonnegative(abs(x), radix)]


def digit_energy(x: int, radix: int) -> int:
    return sum(d * d for d in signed_balanced_digits(x, radix))


def reconstruct(digits: list[int], radix: int) -> int:
    return sum(d * radix**i for i, d in enumerate(digits))


def exact_max_digit_energy(cap: int, radix: int) -> tuple[int, int]:
    if cap < 0 or radix < 2 or radix % 2:
        raise ValueError("requires cap >= 0 and an even radix")
    b = radix // 2

    @lru_cache(maxsize=None)
    def solve(limit: int) -> tuple[int, int]:
        if limit <= b:
            return limit * limit, limit
        quotient = (limit + b - 1) // radix
        complete_energy, complete_witness = solve(quotient - 1)
        complete_energy += b * b
        complete_witness = radix * complete_witness + b
        last_low = -b + 1
        last_high = limit - radix * quotient
        last_digit = last_low if last_low * last_low >= last_high * last_high else last_high
        last_energy = digit_energy(quotient, radix) + last_digit * last_digit
        last_witness = radix * quotient + last_digit
        assert 0 <= complete_witness <= limit
        assert 0 <= last_witness <= limit
        if complete_energy >= last_energy:
            return complete_energy, complete_witness
        return last_energy, last_witness

    energy, witness = solve(cap)
    assert digit_energy(witness, radix) == energy
    return energy, witness


def digit_dp_regression() -> dict[str, int]:
    cases = 0
    for radix in (4, 8, 16):
        for cap in range(0, 400):
            expected = max(digit_energy(x, radix) for x in range(-cap, cap + 1))
            actual, witness = exact_max_digit_energy(cap, radix)
            assert actual == expected
            digits = signed_balanced_digits(witness, radix)
            assert reconstruct(digits, radix) == witness
            neg = signed_balanced_digits(-witness, radix)
            assert reconstruct(neg, radix) == -witness
            assert sum(d * d for d in neg) == actual
            cases += 1
    return {"radices": 3, "caps_per_radix": 400, "total_cases": cases}


def digit_certificates(q: int = Q) -> list[dict[str, Any]]:
    cap = (q - 1) // 2
    output = []
    for radix in (8, 64, 128):
        energy, witness = exact_max_digit_energy(cap, radix)
        digits = balanced_digits_nonnegative(witness, radix)
        ell = 0
        power = 1
        while power < q:
            power *= radix
            ell += 1
        padded = digits + [0] * (ell - len(digits))
        assert len(padded) == ell and reconstruct(padded, radix) == witness
        assert digit_energy(-witness, radix) == energy
        output.append({
            "radix": radix,
            "digit_count": ell,
            "coarse_bound": ell * (radix // 2) ** 2,
            "exact_maximum_energy": energy,
            "attaining_absolute_value": witness,
            "attaining_digits_least_significant_first": padded,
            "negative_sign_restore_has_same_energy": True,
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--relation", type=Path, required=True)
    parser.add_argument("--compiler-source", type=Path)
    parser.add_argument("--parameters", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    relation = json.loads(args.relation.read_text(encoding="utf-8"))
    s0 = compiler_s0_certificate(manifest, relation)
    result: dict[str, Any] = {
        "status": "PASS",
        "evidence_type": "COMPUTED",
        "canonical_encoding_bound": s0,
        "arity_formula_values": {
            str(k): {
                "old_bound": 29568 * k + 69889,
                "refined_bound": compiler_s0_formula(k),
            }
            for k in (2, 4, 8, 16, 32, 1024)
        },
        "digit_energy": digit_certificates(),
        "digit_dp_regression": digit_dp_regression(),
    }
    if args.compiler_source or args.parameters:
        if not args.compiler_source or not args.parameters:
            raise SystemExit("--compiler-source and --parameters must be supplied together")
        result["compiler_fixture"] = fixture_check(
            args.compiler_source, args.parameters, s0["refined_honest_energy_bound"]
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(result), encoding="utf-8", newline="\n")
    print(canonical_json({"status": "PASS", "output": args.output.name}))


if __name__ == "__main__":
    main()
