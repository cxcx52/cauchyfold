# Bounds and concrete parameters

The current profiles retain the relation, encoding, challenge sets, message order, block/radix schedules, and retry boundaries. They tighten norm estimates and select new matrix ranks and projection parameters. The resulting communication change reflects all of these choices, rather than the CBC constant alone.

## Shared-center compare before clearing

Let `(z, c)`, `(z1, c1)`, and `(z2, c2)` be the three responses and challenges used by the comparison step. Suppose each response has coefficient Euclidean norm at most `Z`, and multiplication by each challenge has operator norm at most `T_op`. Writing `Xj = zj - z` and `Delta_j = cj - c`, the existing cross-multiplied candidate is

$$
v=X_1\Delta_2-X_2\Delta_1
 =(z_1-z)c_2-(z_2-z)c_1+(z_2-z_1)c.
$$

The three differences share their endpoints. Their squared lengths satisfy

$$
\|z_1-z\|_2^2+\|z_2-z\|_2^2+\|z_2-z_1\|_2^2
=3(\|z\|_2^2+\|z_1\|_2^2+\|z_2\|_2^2)-\|z+z_1+z_2\|_2^2
\le9Z^2.
$$

Cauchy–Schwarz therefore gives

$$
\|v\|_2\le T_{\rm op}(\|z_1-z\|_2+\|z_2-z\|_2+\|z_2-z_1\|_2)
\le3\sqrt3\,T_{\rm op}Z.
$$

This bounds the same candidate used in extraction. Its kernel membership and nonzero condition remain those of the comparison argument. No inverse challenge is lifted to an integer opening.

Squaring the new factor replaces `64 T_op^2` by `27 T_op^2` in the main-matrix radius formulas. The implementation uses exact integer and rational arithmetic:

| Matrix | Kernel radius |
|---|---|
| Nonterminal main | `ceil(sqrt(27 T_op^2 (1 + rho^2) sigma^2 S_child))` |
| Terminal main | `ceil(sqrt(27 T_op^2 G_L))` |
| Auxiliary | `ceil(2 sqrt(sigma^2 S_child))` |
| Front end | `ceil(2 sqrt(sigma^2 S_0))` |
| Pivot | `ceil(8 sqrt(d a_L 16))` |

Here `rho` is the layer radix, `S_child` is the child opening's squared-norm bound, `G_L` is the terminal response threshold, and `a_L` is the terminal main rank. This shared-center derivation is independent of the projection estimate discussed below.

## Norm accounting

For the degree-64 ring and full coefficient challenge box `{-2,-1,0,1,2}^64`, the deterministic operator bound is `2 csc(pi/128) < 82`; the profiles take `T_op = 82`. The challenge moment remains `mu = 128`.

The canonical layout gives `S_0 = 7561 k + 65521`. Generic, fixed-zero, and fixed-one coordinates are counted separately. The exact maximum centered-digit energies are 249, 8129, and 25537 for radices 8, 64, and 128. [`norm_bounds.py`](norm_bounds.py) contains the digit recurrence and encoding calculation; [`artifacts/norm_bounds.json`](artifacts/norm_bounds.json) preserves their finite calculation and regression results.

For a nonterminal layer, put `b = rho/2`, let `n` be its block length, and let `E_t, E_h` be the two digit-vector energy bounds. The propagated child bound is

$$
S_{\rm child}=dn b^2+E_t+E_h+
\left\lceil\frac{G+dn b^2+2b\sqrt{dnG}}{\rho^2}\right\rceil.
$$

The threshold is `G = 256 S - 1`. At the pivot terminal it is `ceil(256 M S/(M-1)) - 1`, where `M = 5^64`. The code evaluates the ceiling of the square-root expression by integer comparisons.

## Projection and error terms

All six profiles use 384 projection rows and `sigma^2 = 38400/4121`. The projection specialization of PikkuFold's Theorem 2 uses `(lambda, m, alpha, b_mod) = (192, 384, 41.21, 176)`. Each layer checks `41.21 sigma^2 >= 384` and `176^2 sigma^2 S < q^2`. This supplies the independent-projection error `2^-192`; the generator transport adds at most `2^-150`. PikkuFold is used for this projection estimate, not for the shared-center CBC bound.

The seed parameters are chosen by exact integer inequalities. With stream length `R = 2 m N` and state bound `w = ceil(log2((R+1) 4 q (mS+2)))`, the selected integers `b,h` cover the stream and satisfy

$$
(2^h-1)\delta+\frac{2^{6w}h}{2^b\delta^2}\le2^{-150},
\qquad \delta=\frac{2}{3(2^h-1)2^{150}}.
$$

The seed has `b + h(3b-1)` bits. The per-layer artifacts store these quantities and the exact transport error.

Field error is accumulated as `1 - (1-q^-4)^ell_F (1-3q^-4)^ell_F`. Projection retries use the conditional complement bound `1 - (1-epsilon_P)^160`. The Cauchy, structured-aggregation, and adaptive coordinate-recovery terms are recorded separately before summation. Every arity file contains exact numerator/denominator pairs for the statistical error and honest retry exhaustion. A displayed negative binary logarithm describes a statistical bound, not computational security.

## Saved results

| Arity | P → V bytes | V → P bytes | Total bytes | Previous total bytes |
|---:|---:|---:|---:|---:|
| 2 | 66,565 | 8,170 | 74,735 | 117,248 |
| 4 | 83,775 | 8,257 | 92,032 | 136,962 |
| 8 | 107,546 | 8,752 | 116,298 | 166,885 |
| 16 | 146,990 | 9,332 | 156,322 | 215,196 |
| 32 | 128,569 | 26,251 | 154,820 | 244,521 |
| 1024 | 128,563 | 48,854 | 177,417 | 280,832 |

These are no-retry syntax counts. Incoming commitments, CRS storage, and maximum accepted-attempt counts have separate fields. The retained schedules can differ between arities, so the selected communication totals need not increase monotonically with arity. They are not claimed to minimize the full parameter space.

[`artifacts/operation_counts.json`](artifacts/operation_counts.json) reports the affected algebraic subroutines in separate units. Sparse field applications and sumcheck remain in the earlier compiler artifacts; the selected-operation file does not claim to enumerate every machine instruction or implementation cost.

Each role is mapped to coefficient-expanded Euclidean SIS with dimensions `n = d rows`, `m = d columns`, modulus `q`, and its derived radius. [`estimator/results.md`](estimator/results.md) lists both MATZOV models. Its weakest-role summaries range only over finite reported costs. The two arity-2 carrier outputs are non-finite and remain unassigned; block sizes above the model's documented range remain flagged as extrapolations. The saved estimates do not replace the protocol's role-specific Module-SIS assumptions.
