# CauchyFold

Code and concrete parameters for **CauchyFold: Residue-Optimal High-Arity Lattice Folding via Scaled Cauchy Challenges**.

CauchyFold combines one accumulator with `k` fresh instances of a quadratic relation. This repository contains the parameter calculations, relation compiler, carrier algorithms, and supporting code used to study the construction.

## Start here

The current parameter sets cover `k = 2, 4, 8, 16, 32, 1024` and live in [`profiles/compact/`](profiles/compact/).

| Material | Where to find it |
|---|---|
| Current result summary | [`summary.json`](profiles/compact/artifacts/summary.json) |
| Parameter choices and formulas | [`profiles/compact/METHODS.md`](profiles/compact/METHODS.md) |
| Per-arity parameters, matrix dimensions, norm bounds, statistical errors, and communication counts | [`profiles/compact/artifacts/`](profiles/compact/artifacts/) |
| Arithmetic operation counts | [`operation_counts.json`](profiles/compact/artifacts/operation_counts.json) |
| Classical and quantum lattice-attack estimates | [`estimator/results.md`](profiles/compact/estimator/results.md) |

The [relation compiler and field-transcript code](reference/compact/) remain with the earlier artifacts and use the same relation and encoding. [`reference/`](reference/) separates earlier compact, seeded-projection, and explicit-projection parameter sets; their communication figures belong to those earlier configurations.

## Recalculate the parameters and counts

Use **Python 3.11 or later**. These two scripts use only the Python standard library. Run them in order from the repository root:

```sh
python profiles/compact/build_profiles.py
python profiles/compact/count_operations.py
```

The first command writes `arity-<k>.json`, `summary.json`, and `estimator-inputs.json` to [`profiles/compact/artifacts/`](profiles/compact/artifacts/). The per-arity files contain the reduction schedule, commitment matrices, exact statistical bounds, and communication counts. The second command updates `operation_counts.json` with counts for the selected arithmetic routines.

Saved estimator results can be viewed directly. To recompute them separately, follow the [SageMath instructions](profiles/compact/README.md#estimator), which pin the official lattice-estimator revision. These are modeled attack-cost estimates; the result files identify extrapolated and non-finite outputs.

## Communication

| Fresh instances (`k`) | No-retry interaction |
|---:|---:|
| 2 | 72.98 KiB |
| 4 | 89.88 KiB |
| 8 | 113.57 KiB |
| 16 | 152.66 KiB |
| 32 | 151.19 KiB |
| 1024 | 173.26 KiB |

Each row counts both directions of one fold using its selected parameters. The counts follow the specified message format and exclude incoming commitments, the CRS, and application-level public-input encodings. They are communication calculations, not measured proof files or running times. The byte totals are in [`summary.json`](profiles/compact/artifacts/summary.json).

Released under the [MIT License](LICENSE).
