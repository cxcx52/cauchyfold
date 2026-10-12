# Carrier and direct source checks

Code and results comparing the Cauchy carrier with checking all source quadratic equations in the field reduction. Both variants use canonical state encodings and the same selected lattice-backend schedule.

| Arity-1024 configuration | Active coefficients | Field terms | No-retry communication |
|---|---:|---:|---:|
| Existing carrier | 5,204,641 | 5,469,091 | 162.67 KiB |
| Grouped carrier | 5,196,001 | 5,460,019 | 163.21 KiB |
| Grouped direct checks | 4,212,961 | 4,464,727 | 161.04 KiB |

Communication includes both directions and excludes incoming commitments and the CRS. These are message-format calculations, not measured proof files. The carrier has a simpler field-sumcheck structure; direct checks reduce encoding and commitment costs. The [methods](METHODS.md) explain the comparison and the sparse-weight optimization.

## Files

- [`results/`](results/): parameter sets, exact statistical bounds, communication comparison, and relation-size calculations.
- [`direct/`](direct/): direct compiler, field prover/checker, commitment-map check, and estimator results.
- [`carrier/`](carrier/): grouped carrier compiler and estimator results.
- [`checks/`](checks/): repeated semantic folds, sumcheck arithmetic, and sparse-weight checks.
- [`baseline/profile.json`](baseline/profile.json): the existing carrier configuration used for this comparison.

The existing carrier has 17 independent commitment matrices; direct checks use 16. Saved [carrier](carrier/results/estimator/results.md) and [direct](direct/results/estimator/results.md) estimates use official lattice-estimator commit `53da5982597709ba0fdf94ea37a84d822310fd84`, with classical and quantum cost models.

## Recalculate

From the repository root, with Python 3.11 or later:

```sh
python comparisons/source-checks/recalculate.py
python comparisons/source-checks/verify.py
```

These commands use the saved compiler metadata and transcripts. The structural checks run separately:

```sh
python comparisons/source-checks/checks/check.py
python comparisons/source-checks/checks/sparse_weights.py
```

The latter reconstructs the deterministic group map when the generated binary is absent, and checks it against the saved digest. Large sparse matrices are generated locally and are not stored in Git.

To build and execute the compilers, use g++ with C++17 on Linux, or g++ installed in WSL on Windows:

```sh
python comparisons/source-checks/direct/run.py --arity 4 --extended-checks
python comparisons/source-checks/carrier/run.py
```

The direct runner also accepts `--arity 1024`. The carrier runner checks both compiler sizes and runs the arity-4 field transcript. Saved direct results include the arity-1024 field transcript and terminal linear checks. No complete lattice prover or running-time comparison is included.

For an estimator rerun, invoke `direct/backend/run_estimator.py` or `carrier/run_estimator.py` with Sage Python and explicit `--upstream`, `--inputs`, and `--output` arguments. Use the pinned upstream checkout and the corresponding `results/estimator-inputs.json`; output should be the corresponding `results/estimator/` directory.
