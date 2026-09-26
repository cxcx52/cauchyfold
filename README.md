# CauchyFold

This repository accompanies **CauchyFold: Residue-Optimal High-Arity Lattice Folding via Scaled Cauchy Challenges**. It contains parameter profiles, exact communication and operation counts, compiler artifacts, and saved lattice-estimator results.

## Results

The repository separates the compact profiles from two earlier projection configurations.

| Configuration | Arity | No-retry interaction | Location |
|---|---:|---:|---|
| Compact finite profiles | 2, 4, 8, 16, 32 | 114.50–238.79 KiB | [`profiles/finite-arities/`](profiles/finite-arities/) |
| Large-arity profile | 1024 | 274.25 KiB | [`profiles/arity-1024/`](profiles/arity-1024/) |
| Seeded-projection reference | 16 | 10.19 MiB | [`reference/seeded-projection/`](reference/seeded-projection/) |
| Explicit-projection reference | 16 | 460.37 MiB | [`reference/explicit-projection/`](reference/explicit-projection/) |

The compact profiles use structured aggregation. The two reference configurations retain the earlier explicit aggregation and are kept for comparison. Communication totals are exact for their stated message syntax; incoming commitments and the CRS are reported separately.

## Repository structure

| Path | Contents |
|---|---|
| [`profiles/`](profiles/) | Compact finite-arity and large-arity profiles |
| [`reference/`](reference/) | Earlier explicit- and seeded-projection configurations |
| [`requirements.txt`](requirements.txt) | Python dependencies |

Each profile directory contains its own reproduction commands and scope. Saved lattice-estimator values are heuristic attack-cost estimates produced with the pinned estimator revision recorded alongside the results.

Released under the [MIT License](LICENSE).
