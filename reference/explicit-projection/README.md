# Explicit-projection reference

This directory contains the complete arity-16 Profile I reference configuration in which the verifier sends every projection matrix explicitly. Its no-retry interaction is 482,734,680 bytes (460.37 MiB), excluding incoming commitments and the CRS.

The directory includes the deterministic relation compiler, concrete parameters, the 20-role matrix registry, statistical and operation ledgers, and saved official lattice-estimator results. It is retained as the common reference for the seeded-projection comparison. The smaller communication profiles are under [`../../profiles/`](../../profiles/).

Run the exact-data reproduction from the repository root:

```sh
python reference/explicit-projection/reproduce/reproduce_concrete.py
```

The script regenerates the compiler and concrete ledgers, then compares them with [`artifacts/`](artifacts/). Saved estimator outputs are checked but not recomputed.
