# Derivation of the compact arity profiles

## Front-end size

The relation has semantic dimensions `(n,y,r) = (69,4,4)`. With `k` fresh
records, one accumulator, one folded output, `4k` carrier values, and 36
quadratic helper values, the number of extension-field values is

```text
V_K = (k+2)(69+4) + 4k + 36 = 77k + 182.
```

The canonical encoding uses 192 value bits and 192 comparison-helper bits per
extension-field value, together with one fixed coordinate. Consequently,

```text
N_used = 384 V_K + 1 = 29568k + 69889.
```

With minimal witness capacity, the unpadded number of field constraints is

```text
M_F = 46109k + 108595,
ell_F = ceil(log2(M_F)).
```

Only the row table is padded to `2^ell_F`. Coordinates that were formerly
reserved as fixed zeros are removed from the witness rather than exposed as
unconstrained variables. Backend block padding is introduced separately and
receives explicit zero equations.

## Backend recurrence

For an even power-of-two radix `rho`, put

```text
ell = ceil(48 / log2(rho)),  b = rho/2,  d = 64,  tau = 3.
B_t = ell * 24 * s,
B_h = ell * tau * s(s+1)/2.
```

If a layer receives `N_raw` coefficient coordinates with energy bound `S`, it
uses

```text
n = ceil(N_raw/(64s)),  N = 64sn,  G = 256S
```

and produces

```text
N'_raw = 2dn + d(B_t+B_h),
S' = dn b^2 + ceil((2G+2dn b^2)/rho^2) + d(B_t+B_h)b^2.
```

These are sufficient integer bounds. They do not use the observed energy of a
sampled witness. At the terminal, excluding the zero short challenge changes
the response bound to

```text
G_T = ceil(256 S_T * 5^64/(5^64-1)) = 256 S_T + 1
```

for every selected profile.

## Restricted-grid optimality

At a fixed depth, every future transition and message length depends on the
prefix only through `(N_raw,S)`. The exhaustive search therefore keeps the
cheapest prefix only when both values are identical. Its remaining cuts use a
nonnegative lower bound on every future message and a structural lower bound
on the terminal payload. Neither cut assumes that seed length is monotone.

The search enumerates all paths with up to five nonterminal layers, every
`s` in `[2,32]`, and every radix in `{4,8,16,32,64,128}` that satisfies the
registered matrix envelopes. It follows that each reported result is minimal
inside this finite grid. The argument does not compare against different
ranks, codecs, challenge sets, or protocol structures.

## Relative Module-SIS envelope

Each selected matrix is compared with a registered reference matrix having the
same row rank and ring. The selected matrix has no more columns and no larger
coefficient `l2` radius.

Given a uniformly sampled reference matrix `A` with `b_ref` columns, expose its
first `b <= b_ref` columns to an algorithm for the selected role. If the
algorithm returns a nonzero short kernel `x`, extend it by zeros. The extended
vector is a kernel of `A`, remains nonzero modulo `q`, and has the same norm.
Thus an algorithm for the selected role yields an algorithm for the reference
role with the same success probability, provided the selected radius is at
most the reference radius.

For `k=32`, the auxiliary opening has 8,046 ring columns and cannot use the
4,350-column reference key as one matrix. The profile splits the existing
vector into 4,350 and 3,696 columns and commits with two independent matrices.
This changes neither the coordinates nor the field constraints. A disagreement
in either segment yields a short kernel for that segment's matrix.

The reduction is a relative hardness statement. It does not transfer numerical
attack exponents verbatim and does not replace the full-node sum of
role-specific advantages.

## Statistical and serialization checks

The scripts use exact rational arithmetic for field, aggregation, projection,
and short-challenge terms. Every selected profile is below `2^-130` in that
ledger. Projection and terminal responses use fixed-capacity signed Rice
encoding derived from the public squared-norm bound. Decoding checks the norm,
coordinate range, and unused padding bits.

The values in `results/` are syntax-level byte counts. A complete protocol
implementation and wall-clock measurements are outside this profile study.
