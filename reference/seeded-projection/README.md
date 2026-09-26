# Seeded-projection reference

This arity-16 reference configuration replaces the explicit projection matrices with Nisan-generator seeds. It retains the same folding relation, commitment matrices, kernel radii, aggregation randomness, and prover messages as the explicit-projection configuration.

For each of the six lattice layers, the verifier sends a complete generator seed. Both parties expand the corresponding lazy-ternary projection through streaming forward and adjoint operators; the matrix is neither transmitted nor materialized.

The no-retry transcript contains 342,690 prover bytes and 10,341,123 verifier bytes, for a total of 10,683,813 bytes (10.19 MiB). The verifier total includes 52,557 bytes of projection seeds and 10,286,694 bytes of explicit aggregation randomness. The compact profiles under [`../../profiles/`](../../profiles/) use structured aggregation instead.

Run the consistency check from the repository root:

```sh
python reference/seeded-projection/check.py
```

The check verifies the six layer descriptors and the communication totals. It does not run a protocol benchmark or the lattice estimator.
