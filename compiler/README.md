# Relation compiler

Deterministic sparse quadratic relation, canonical encoding, field sumcheck, and scalar handoff. The relation is a synthetic instance of the mathematical interface, not an application workload.

The compiler eliminates fixed coordinates from the active witness. It supports a prefix comparator (`prefix`) and a comparator specialized to `q = 2^48 - 59` (`special`). Both encode the same relation. The selected large-arity parameters use `special`; the smaller selected profiles retain their reference layouts.

## Run

Use Python 3.11 or later and GCC with C++17 on Linux or WSL. From the repository root:

```sh
python compiler/run.py --arity 4
```

This builds the sparse circuit and checks its witness, a second Cauchy challenge, rejected mutations, field transcript, and linear handoff. The separate commitment-link check uses arity 4 and deterministic test matrices. It is a regression test, not a production CRS generator.

For the selected large instance, use `--arity 1024`. Generated matrices and intermediate tables can be large; they are written to the ignored `compiler/build/` directory. Add `--check-layout` to compare every sparse row against independently constructed templates; this optional check requires NumPy.

## Files

| Path | Contents |
|---|---|
| `src/arithmetic.cpp` | Field arithmetic, relation fixture, and encoding primitives |
| `src/compile.cpp` | Sparse circuit and witness construction |
| `src/sumcheck.cpp` | Two-coefficient sumcheck transcript and verification |
| `src/check_handoff.cpp` | Scalar handoff verification |
| `src/check_commitments.cpp` | Commitment-link regression check |
| `checks/` | Independent sparse-layout templates and checks |
| `examples/` | Saved arity-1024 compiler and field-check metadata; commitment check at arity 4 |

The saved metadata records finite execution checks. The selected dimensions, communication counts, statistical bounds, and attack estimates are in [`profiles/compact/`](../profiles/compact/).
