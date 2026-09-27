# CauchyFold

Code and concrete data for **CauchyFold: Residue-Optimal High-Arity Lattice Folding via Scaled Cauchy Challenges**.

The [current profiles](profiles/compact/) include the updated compare-before-clearing bound, concrete parameters, communication and operation counts, and saved lattice-estimator results.

| Folding arity | No-retry interaction |
|---:|---:|
| 2 | 72.98 KiB |
| 4 | 89.88 KiB |
| 8 | 113.57 KiB |
| 16 | 152.66 KiB |
| 32 | 151.19 KiB |
| 1024 | 173.26 KiB |

Communication counts follow the stated message syntax and exclude incoming commitments and the CRS. Estimator outputs are heuristic attack-cost estimates; their range flags and non-finite results are retained.

## Use

```sh
python profiles/compact/build_profiles.py
python profiles/compact/count_operations.py
```

These commands require Python 3.11 or later. Parameters, formulas, and optional estimator commands are documented in [`profiles/compact/`](profiles/compact/).

Earlier compact, seeded-projection, and explicit-projection configurations are kept separately under [`reference/`](reference/), together with their compiler and transcript artifacts.

Released under the [MIT License](LICENSE).
