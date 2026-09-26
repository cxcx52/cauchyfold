# Parameter profiles

This directory contains the compact communication profiles.

- [`finite-arities/`](finite-arities/) covers arities 2, 4, 8, 16, and 32 within a fixed finite parameter grid.
- [`arity-1024/`](arity-1024/) contains the large-arity front end, field transcript, and role-specific lattice-estimator results.

The finite-grid communication values range from 114.50 KiB to 238.79 KiB. The arity-1024 syntax totals 274.25 KiB. These profiles use structured aggregation; they are separate from the earlier explicit- and seeded-projection configurations under [`../reference/`](../reference/).

Each subdirectory states its parameter model, reproduced components, and commands. The arity-1024 material covers the front end and field protocol rather than a complete recursive lattice-node implementation.
