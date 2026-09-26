# Additional arity profiles

The main artifact remains the arity-16 profile described in the repository
root. This directory contains two separate extensions:

- `arity/` derives and searches compact profiles for arities 2, 4, 8, 16, and
  32 within a fixed finite parameter grid.
- `k1024/` records an experimental arity-1024 front end, field transcript, and
  role-specific lattice-estimator results.

The finite-grid profiles are exact within their stated model. The arity-1024
directory is a component-level scalability result: its front end and field
protocol are implemented, but the complete recursive lattice node is not.
