# CauchyFold

Reproducibility code and data for **CauchyFold: Residue-Optimal High-Arity Lattice Folding via Scaled Cauchy Challenges**, maintained by [cxcx52](https://github.com/cxcx52).

This repository accompanies the paper's CF† v2 concrete instantiation: **Profile I, folding arity 16**, one explicit sparse quadratic relation, and 20 independently sampled commitment matrices.

## Reproduce

Python 3.12 and the dependency in `requirements.txt` are sufficient for the default run:

```sh
python -m pip install -r requirements.txt
python reproduce/reproduce_concrete.py
```

The command creates `build/`. It compiles the relation, runs the compiler self-checks, regenerates exact ledgers and all estimator inputs, validates the 40 saved estimator records, and compares output SHA256 hashes and canonical JSON bytes with the published expectations. It ends with `PASS` and writes `build/reproduction_report.json`.

Existing output directories are never overwritten. For another clean run:

```sh
python reproduce/reproduce_concrete.py --output build-second
```

All paths are relative to this repository or, within generated manifests, to the generated output directory. The command works from another working directory as well. The compiler generates approximately 48 MB of sparse CSR matrix files. These deterministic files are omitted from Git and checked against the hashes in `checks/expected_outputs.json`.

The default command runs neither lattice attacks nor protocol benchmarks. It does not produce a serialized folding proof. Communication values are exact lengths under the selected message grammar.

## Evidence and paper tables

| Paper material in §7 | Artifact |
|---|---|
| Table 3: concrete parameters and relation | `parameters/parameters.json`, `relation/relation_spec.json` |
| Tables 6–7: encoding and field circuit | `artifacts/compiler_manifest.json`, `artifacts/compiler_artifacts/` |
| Table 3: six-layer reduction schedule | `artifacts/reduction_schedule.json` |
| Tables 8–9: commitment roles and kernel radii | `artifacts/node_registry.json` |
| Table 4: statistical error and completeness | `artifacts/statistical_security.json`, `artifacts/completeness.json` |
| Tables 4 and 8: Module-SIS attack estimates | `artifacts/estimator_results.json`, `estimator/raw/` |
| Tables 5 and 10: communication | `artifacts/communication_ledger.json` |
| Tables 2, 5, and 11–13: typed arithmetic and carrier comparison | `artifacts/operation_counts.json` |
| Compiler regression checks | `artifacts/compiler_tests.json` |

The three front-end matrices have 219, 192, and 4,350 ring columns. The shared state matrix covers the accumulator, sixteen fresh inputs, and output. There are seventeen further backend matrices. Field sumcheck has 21 rounds.

No-retry folding communication is **342,690 B P→V** and **482,391,990 B V→P**, totaling **482,734,680 B**. Sixteen incoming fresh commitments add 196,608 B; the incoming accumulator commitment adds 12,288 B. Profile I sends independent verifier randomness explicitly.

## Estimator

The saved results use official [lattice-estimator](https://github.com/malb/lattice-estimator) commit `53da5982597709ba0fdf94ea37a84d822310fd84`, with `SIS.estimate` and `MATZOV(nn="classical")` / `MATZOV(nn="quantum")`. The coefficient embedding uses `n=64*rows`, `m=64*columns`, and the registered coefficient ℓ₂ radius.

The execution environment was SageMath 10.9, Python 3.12.14, NumPy 2.5.3, and SciPy 1.18.0; see `estimator/environment.json`. Ordinary exact reproduction only requires Python and jsonschema. Instructions for separately rerunning the estimator are in [estimator/README.md](estimator/README.md).

Both weakest recorded full-node estimates occur at `backend_0_A`: classical `log2(rop)=255.490229` and quantum `log2(rop)=238.730181`. These are model estimates for the attacks returned by the pinned estimator, not a complete concrete-security certification. Each record flags block sizes beyond the model's documented fit range. Unreported attack memory and success probability remain explicitly unreported.

## What the checks establish

The compiler layouts, rational statistical bounds, syntax-level lengths, and typed operation counts are exact finite calculations. Compiler self-checks are finite regression evidence. Lattice costs are heuristic estimates. Neither category substitutes for the paper's proofs.

The companion Resource paper supplies the retained-width theory and carrier representation. This repository concerns the committed realization and concrete-instantiation calculations.

## Integrity and organization

```sh
python checks/verify_manifest.py
```

`manifest.json` hashes every distributed file except itself. `checks/expected_outputs.json` additionally pins generated outputs, including the sparse matrices. The relation, parameters, numeric ledgers, estimator inputs, and raw estimator records retain their original evidence bytes. Packaging changes the execution entry points, dependency layout, result filenames, and host-specific environment paths. The compiler algorithm is unchanged; its source hash reflects the renamed test output.

The parameter ID retains its original `compiler-conditional` suffix to preserve the parameter-file hash. The actual bound instance is the `COMPLETE` manifest plus the relation and parameter hashes. The `protocol_source` and backend `source` strings in those preserved input files are historical provenance identifiers, not files opened by the public reproduction command. No historical review or source bundle is required.

The repository contains no paper PDF, LaTeX source, historical protocol benchmarks, or large CRS files. Code is released under the [MIT License](LICENSE); citation metadata is in [CITATION.cff](CITATION.cff).
