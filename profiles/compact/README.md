# Compact profiles

Concrete parameters for folding arities 2, 4, 8, 16, 32, and 1024. These profiles use the shared-center compare-before-clearing bound, exact digit energies, seeded projections, and structured aggregation.

## Data

| Path | Contents |
|---|---|
| [`parameters.json`](parameters.json) | Selected matrix ranks |
| [`schedules/`](schedules/) | Retained block/radix schedules |
| [`artifacts/`](artifacts/) | Role dimensions and radii, exact statistical and completeness bounds, byte counts, and typed operations |
| [`estimator/results.md`](estimator/results.md) | Classical and quantum estimates for every role |
| [`METHODS.md`](METHODS.md) | CBC bound and parameter formulas |

The six profiles use main, auxiliary, front-end, and pivot ranks 16, 6, 4, and 2, respectively; 384 projection rows; and squared projection slack 38400/4121. The block/radix schedules are retained from the [earlier compact configurations](../../reference/compact/). Communication improvements combine these parameter choices with tighter norm bounds.

## Rebuild the counts

From the repository root, with Python 3.11 or later:

```sh
python profiles/compact/build_profiles.py
python profiles/compact/count_operations.py
```

Both scripts use the standard library. The first writes the per-arity profiles, exact rational error terms, communication totals, and estimator inputs. The second writes selected typed operation counts. Incoming commitments and CRS storage are separate fields. These are syntax and arithmetic counts, not timings or measured proof files.

The relation compiler and field-transcript code remain with their [earlier artifacts](../../reference/compact/). The current layout uses the same relation and encoding; updated commitment dimensions and norm bounds are recorded here.

## Estimator

Saved results use official lattice-estimator commit `53da5982597709ba0fdf94ea37a84d822310fd84`, SageMath 10.9, coefficient-expanded Euclidean SIS, and classical/quantum MATZOV cost models. There are 88 distinct jobs: 86 finite outputs and two non-finite outputs, both for the arity-2 carrier matrix. A non-finite output does not establish a security bound. The results also identify estimates outside the model's documented block-size range.

To run the estimator separately in a Linux SageMath environment:

```sh
git clone https://github.com/malb/lattice-estimator.git vendor/lattice-estimator
git -C vendor/lattice-estimator checkout 53da5982597709ba0fdf94ea37a84d822310fd84
sage -python profiles/compact/run_estimator.py --upstream vendor/lattice-estimator --output profiles/compact/build/estimator
```

The runner requires that exact, unmodified upstream revision. New results go to `build/`; the published estimates remain in `estimator/`. Results rank only finite reported attack costs and do not certify full-protocol computational security.
