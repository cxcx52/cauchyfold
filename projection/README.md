# Seeded projections

This directory contains the seeded projection configuration used by the current arity-16 CauchyFold instance. It changes how the verifier describes each projection matrix. The folding relation, commitment matrices, kernel radii, aggregation randomness, and prover-to-verifier messages remain unchanged.

For each of the six lattice layers, the verifier sends a complete Nisan-generator seed. Both parties expand the same lazy-ternary projection through streaming forward and adjoint operators. The expanded matrix is never sent or materialized.

## Files

| File | Contents |
|---|---|
| `parameters.json` | Per-layer generator parameters and seed lengths |
| `communication.json` | Exact message lengths for one fold |
| `comparison.json` | Explicit-projection and seeded-projection comparison |
| `statistical_bounds.json` | Exact rational statistical bounds |
| `completeness.json` | Honest retry bound |
| `operation_counts.json` | Typed field, ring, and generator operation counts |
| `runtime_bounds.json` | Symbolic extractor-runtime recurrence |
| `src/` | Reference forward, adjoint, session, and native generator code |

Run the consistency check from the repository root:

```sh
python projection/check.py
```

The check confirms the six layer descriptors, the byte totals, and the published explicit-to-seeded comparison. It does not run a protocol benchmark or the lattice estimator.

## Communication summary

The no-retry transcript contains 342,690 bytes from prover to verifier and 10,341,123 bytes from verifier to prover. The total is 10,683,813 bytes (10.19 MiB). Of the verifier-to-prover total, 52,557 bytes describe all six projections and 10,286,694 bytes are the unchanged aggregation randomness.

The maximum accepted-attempt syntax has 19,175,844 bytes in total. This is a worst-case message-format bound for the fixed retry limits, rather than expected communication.

The explicit projection configuration sent 472,103,424 bytes of projection descriptions. Seeded descriptions reduce that component to 52,557 bytes. This comparison changes only the projection description and its expansion cost.
