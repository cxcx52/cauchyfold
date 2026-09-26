# CauchyFold

Code and data accompanying **CauchyFold: Residue-Optimal High-Arity Lattice Folding via Scaled Cauchy Challenges**, maintained by [cxcx52](https://github.com/cxcx52).

The repository contains an arity-16 relation compiler, concrete protocol parameters, exact communication and operation counts, and lattice-estimator inputs and results. The current configuration uses seeded projection descriptors; the original explicit-projection configuration is retained as a comparison point.

## Repository layout

```text
relation/       Sparse quadratic relation used by the compiler
compiler/       Deterministic front-end compiler
parameters/     Field, commitment, and reduction parameters
artifacts/      Generated relation, security, and cost data
projection/     Seeded projection parameters, operators, and comparison data
estimator/      Pinned lattice-estimator inputs and saved results
profiles/       Additional finite-grid and scalability profiles
reproduce/      Reproduction entry point
checks/         Field and serialization checks
```

## Reproduce the concrete instance

Python 3.12 and the dependency in `requirements.txt` are sufficient for the default run:

```sh
python -m pip install -r requirements.txt
python reproduce/reproduce_concrete.py
```

The command builds the relation in a new `build/` directory, checks the compiler output, regenerates the concrete tables, and compares the generated JSON data with the files under `artifacts/`. It uses the saved estimator results and does not run lattice attacks or performance benchmarks.

To use another output directory:

```sh
python reproduce/reproduce_concrete.py --output build-second
```

The compiler generates about 48 MB of deterministic sparse matrices in the output directory. These matrices are omitted from Git.

## Seeded projections

The seeded projection configuration is described in [projection/README.md](projection/README.md). Its no-retry transcript has:

- prover-to-verifier communication: 342,690 bytes;
- verifier-to-prover communication: 10,341,123 bytes;
- total interactive communication: 10,683,813 bytes, or 10.19 MiB.

These are exact lengths under the specified interactive message format. They are not measured proof sizes or wall-clock benchmarks. Incoming commitments and CRS storage are accounted for separately in the data files.

## Concrete data

| Result | Files |
|---|---|
| Relation and parameters | `relation/relation_spec.json`, `parameters/parameters.json` |
| Compiler output | `artifacts/compiler_manifest.json`, `artifacts/compiler_artifacts/` |
| Reduction schedule | `artifacts/reduction_schedule.json` |
| Commitment matrices and kernel radii | `artifacts/node_registry.json` |
| Statistical bounds and completeness | `artifacts/statistical_security.json`, `artifacts/completeness.json` |
| Module-SIS estimates | `artifacts/estimator_results.json`, `estimator/raw/` |
| Communication | `projection/communication.json` |
| Typed operation counts | `projection/operation_counts.json` |

## Lattice estimator

The saved results use official [lattice-estimator](https://github.com/malb/lattice-estimator) commit `53da5982597709ba0fdf94ea37a84d822310fd84`, with `SIS.estimate` and the MATZOV classical and quantum near-neighbor options. The coefficient embedding uses `n = 64 * rows`, `m = 64 * columns`, and the coefficient \(\ell_2\) radius recorded for each role.

The weakest saved full-node estimates both occur at `backend_0_A`: classical `log2(rop) = 255.490229` and quantum `log2(rop) = 238.730181`. These are attack-model estimates, not a complete security certification. Entries outside the documented fit range are marked in the result files.

The compiler layouts, rational probability bounds, message lengths, and typed operation counts are finite calculations. The estimator values are heuristic attack estimates. Code is available under the [MIT License](LICENSE).

## Additional arities

The [profile directory](profiles/README.md) contains exact restricted-grid
results for arities 2, 4, 8, 16, and 32, together with an experimental
arity-1024 front-end profile. The arity-1024 material includes a materialized
field compiler, a complete field transcript, and official estimator output for
its seventeen matrix roles. Its recursive lattice backend is not implemented,
so it is presented as component-level scalability evidence rather than a
complete proof benchmark.
