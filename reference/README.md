# Reference configurations

These configurations preserve earlier parameter choices. The [current profiles](../profiles/compact/) incorporate the updated compiler, norm bounds, and five-point extraction. Use their statistical certificates for current claims; the certificates here describe earlier extraction analyses.

| Configuration | Arity | No-retry interaction |
|---|---:|---:|
| [Earlier compact profiles](compact/) | 2, 4, 8, 16, 32, 1024 | 114.50–274.25 KiB |
| [Seeded projection](seeded-projection/) | 16 | 10.19 MiB |
| [Explicit projection](explicit-projection/) | 16 | 460.37 MiB |

The compact configurations use structured aggregation. The two projection references retain explicit aggregation. Counts exclude incoming commitments and the CRS; each directory records its own parameters, code, and saved results.
