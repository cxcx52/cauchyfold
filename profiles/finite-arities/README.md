# Compact arity profiles

This directory parameterizes the compact CauchyFold handoff by the number `k`
of fresh records folded with one accumulator. It contains exact finite-grid
search results for `k = 2, 4, 8, 16, 32` and exploratory profiles for `k = 6`
and `k = 10`.

These are the compact-profile results. The earlier 460.37 MiB explicit-projection and 10.19 MiB seeded-projection configurations are kept separately under [`../../reference/`](../../reference/).

The selected no-retry interaction lengths exclude incoming commitments and
the CRS:

| arity | bytes | selected backend schedule |
|---:|---:|---|
| 2 | 117,248 | terminal `s=3` |
| 4 | 136,962 | terminal `s=3` |
| 8 | 166,885 | terminal `s=4` |
| 16 | 215,196 | terminal `s=6` |
| 32 | 244,521 | `(s=9,rho=64) -> (s=6,rho=64) -> terminal s=5` |

These values minimize the declared grid: zero through five nonterminal layers,
`s` from 2 through 32, and radix in `{4,8,16,32,64,128}`. They are not global
communication optima and are not measured serialized proof sizes.

Run the finite checks with Python 3.10 or later:

```sh
python profiles/finite-arities/reproduce.py
```

Repeat the five exhaustive searches with:

```sh
python profiles/finite-arities/reproduce.py --search
```

The exhaustive search may use several hundred MiB of memory. It is a parameter
search, not a prover benchmark. The mathematical derivation and the precise
scope of the search certificate are given in [METHOD.md](METHOD.md).
