# CauchyFold

This repository accompanies **CauchyFold: Residue-Optimal High-Arity Lattice Folding via Scaled Cauchy Challenges**. It contains the reference compiler, parameter files, and scripts used to reproduce the paper's concrete communication, operation-count, statistical, and lattice-estimator data.

## Reproduction

### Requirements

- Python 3
- the packages listed in [`requirements.txt`](requirements.txt)

From the repository root, run:

```sh
python -m pip install -r requirements.txt
python reproduce/reproduce_concrete.py
```

The script regenerates the concrete instance and compares the generated JSON files with the data in [`artifacts/`](artifacts/). Saved lattice-estimator outputs are checked as part of the reproduction but are not recomputed. The projection and additional parameter studies provide their own commands in [`projection/`](projection/) and [`profiles/`](profiles/README.md).

## Repository structure

| Path | Contents |
|---|---|
| [`relation/`](relation/) | Sparse quadratic relation used by the compiler |
| [`compiler/`](compiler/) | Deterministic front-end compiler |
| [`parameters/`](parameters/) | Concrete parameters and reduction schedule |
| [`artifacts/`](artifacts/) | Generated compiler, security, communication, and operation data |
| [`projection/`](projection/) | Seeded projection construction and checks |
| [`estimator/`](estimator/) | Lattice-estimator inputs and saved outputs |
| [`profiles/`](profiles/README.md) | Additional parameter profiles and reproduction scripts |
| [`checks/`](checks/) | Field-arithmetic and serialization checks |
| [`reproduce/`](reproduce/) | Main reproduction entry point |

Communication values are exact for the specified message syntax. Lattice-estimator values are heuristic attack-cost estimates produced with the pinned estimator revision recorded in the artifacts.

Released under the [MIT License](LICENSE).
