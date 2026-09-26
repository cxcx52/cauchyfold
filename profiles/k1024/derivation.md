# Derivation of the arity-1024 component profile

## Front-end dimensions

The compact front-end formulas specialize at `k=1024` to

```text
N_used = 29568k + 69889 = 30,347,521,
M_F = 46109k + 108595 = 47,324,211,
ell_F = ceil(log2(M_F)) = 26.
```

The compiler materializes the unpadded field system and records 168,555,697
sparse entries across its three matrices. The row table is padded to `2^26`
for sumcheck. The additional padded rows are zero constraints and introduce no
new witness coordinates.

The state commitment has 219 ring columns. The degree-`<1024` carrier uses
12,288 columns, and the auxiliary segment uses 237,198 columns. All states use
the same `A_st`; the carrier and auxiliary segments use independent matrices.

## The 384-row projection test

The projection argument specializes Theorem 2 of
[PikkuFold](https://eprint.iacr.org/2026/1809). For security parameter
`lambda=192`, that modular lower-tail statement has 384 biased-ternary rows and
constants `alpha=41.21` and `b=176`. For a vector whose coefficient squared
norm exceeds `16S`, put `theta=4 sqrt(S)`. The theorem bounds the event

```text
||Jw mod q||_2 <= sqrt(alpha) * theta.
```

The verifier accepts a projection only when its squared norm is at most
`384S`. Since

```text
384S < 41.21 * 16S = 659.36S,
```

acceptance is contained in the theorem's bad-vector event. The profile checks
the remaining range premise `theta <= q/176` at every layer.

For an honest vector of squared norm at most `S`, each ternary entry has second
moment `1/2`, so

```text
E[||Jw||_2^2] = 192 ||w||_2^2 <= 192S.
```

Markov's inequality gives honest acceptance probability at least one half at
the threshold `384S`. This argument concerns one fixed vector and one fresh
projection trial. The transcript keeps the retry checkpoint and state-reset
rules explicit.

## Statistical ledger

The profile recomputes the projection-generator seed for each layer with the
384-row threshold and an error target below `2^-150`. Field, Cauchy,
aggregation, coordinate-recovery, and retry terms are represented as exact
rationals. Their displayed sum satisfies

```text
-log2(kappa) = 133.699073856...
```

This number is a statistical-error summary. It is not a computational-security
estimate.

## Module-SIS estimates

The registry contains seventeen independent matrices. A role with module shape
`rows x columns` over a degree-64 ring is passed to the estimator as

```text
n = 64 * rows,
m = 64 * columns,
norm = 2,
length_bound = registered coefficient-l2 radius.
```

The unmodified pinned estimator returns finite classical and quantum values for
all roles. The weakest is `A_1`, whose coefficient instance has
`(n,m)=(1792,226304)` and radius 25,109,346,730. Its reported costs are 257.585
classical and 240.628 quantum `log2(rop)`, both at block size 804.

This embedding provides standard attack-cost screening. It does not account
for every possible use of module structure, and estimator work factors are not
formal bounds on the complete protocol advantage.

## Evidence boundary

The included field transcript is an actual 26-round execution. The full wire
parser checks canonical coefficients, challenge syntax, retry caps, norm
codecs, and the field equations. Its lattice payload fixture is synthetic. No
claim in this directory relies on that fixture satisfying the commitment or
principal lattice equations.

Accordingly, this profile establishes front-end and field scalability plus
role-specific estimator evidence. It does not establish an end-to-end
arity-1024 lattice proof or a prover-time benchmark.
