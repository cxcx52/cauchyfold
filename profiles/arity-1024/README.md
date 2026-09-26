# Arity-1024 component profile

This directory records an experimental `k=1024` CauchyFold profile. It is
included to make the front-end scaling calculation and its concrete evidence
reproducible. It is not the repository's main concrete profile.

The parameter derivation and projection argument are collected in
[METHOD.md](METHOD.md).

Implemented components:

- materialized sparse field constraints with 47,324,211 rows and 168,555,697
  entries;
- complete vectorized comparison of every stored row pointer and sparse entry;
- a 26-round field transcript of 3,816 bytes and an independent Python check;
- a strict parser for the proposed interactive grammar;
- seventeen independently sampled matrix roles with classical and quantum
  official lattice-estimator results.

The exact no-retry grammar has 230,502 prover bytes and 50,330 verifier bytes,
for 280,832 bytes in total, excluding incoming commitments and the CRS. The
compiler profile records 12,582,912 bytes for 1,024 fresh commitments and
3,474,533,376 bytes of explicit CRS.

The lattice-estimator run uses commit
`53da5982597709ba0fdf94ea37a84d822310fd84` and SageMath 10.9. The weakest
saved estimates both occur at `A_1`:

| model | log2(rop) | block size |
|---|---:|---:|
| classical | 257.585 | 804 |
| quantum | 240.628 | 804 |

These values are heuristic estimates for coefficient-expanded Euclidean SIS.
Results with block size above 1024 are marked as extrapolated in
[`estimator/results.json`](estimator/results.json).

The complete recursive lattice prover and verifier are not implemented here.
The parser creates a synthetic grammar fixture with placeholder lattice
payloads; that fixture is deliberately omitted from the repository. The
280,832-byte value is therefore an exact syntax calculation, not a measured
proof size.

Regenerate and check the parameter ledger:

```sh
python profiles/arity-1024/src/profile.py
python profiles/arity-1024/src/check_transcript.py
```

To inspect the full sparse compiler artifacts, first unpack the compressed
files and then run the complete template check:

```sh
python profiles/arity-1024/src/unpack_compiler_data.py
python profiles/arity-1024/src/check_compiler.py
```

The unpacked compiler directory is about 2 GiB and is ignored by Git.
