# Reference configurations

This directory keeps two earlier arity-16 configurations so their calculations remain reproducible without being confused with the compact profiles.

| Configuration | Projection description | Aggregation description | No-retry interaction |
|---|---|---|---:|
| [`explicit-projection/`](explicit-projection/) | Explicit matrices | Explicit field elements | 482,734,680 B (460.37 MiB) |
| [`seeded-projection/`](seeded-projection/) | Nisan-generator seeds | Explicit field elements | 10,683,813 B (10.19 MiB) |

The compact profiles under [`../profiles/`](../profiles/) additionally use structured aggregation and therefore have substantially smaller communication totals.
