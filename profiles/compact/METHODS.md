# Bounds and concrete parameters

The selected profiles share the relation and challenge sets. Their block/radix schedules are retained from the earlier compact configurations. Matrix ranks, projection parameters, and norm accounting are recorded in the per-arity artifacts. The large-arity profile additionally uses fixed-coordinate elimination, a specialized canonical comparator, two-coefficient sumcheck messages, and exact Rice capacities.

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

This argument requires a shared center. To compare independent trials, each coordinate fiber retains five successful responses with distinct challenges. Challenge differences must be units, as required by the short-challenge set. Within a trial, the four slopes are compared against the same center; a disagreement uses the bound above.

For two internally consistent trials with different recovered slopes, let `X_e, D_e` denote response and challenge differences along each of the ten pairs in one trial, and use tildes for the other. Every certificate

$$K_{e,f}=\widetilde D_f X_e-D_e\widetilde X_f$$

is a nonzero modular kernel. For `h` responses per trial, pairwise energy identities give

$$
\sum_e\|X_e\|^2\le h^2Z^2,\qquad
\sum_f\|\widetilde D_f x\|^2\le h^2T_{\rm op}^2\|x\|^2.
$$

Thus the sum of squared certificate norms is at most `4 h^4 T_op^2 Z^2`. There are `binom(h,2)^2` candidates, so one has norm at most `4h/(h-1) T_op Z`. With five points this is `5 T_op Z`, below `3 sqrt(3) T_op Z`. The registered radius therefore covers both branches. No inverse challenge is lifted to an integer opening.

Five-point recovery changes the coordinate loss to `10 R_C sum_j 1/M_j` and expected oracle calls to `1+4s`. The extraction-time recurrence is

$$T_i^{\rm ext}\le W_i^{(5)}+2R_{C,i}(1+4s_i)(H_i+T_{i+1}^{\rm ext}).$$

At the terminal layer the child term is absent. `W_i^(5)` includes shared-center comparisons and up to 100 cross-trial certificates per coordinate. These changes affect extraction analysis, not honest communication.

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

The reference canonical layout gives `S_0 = 7561 k + 65521`. For the selected large-arity layout, put `f = 84k+728`; then `N_used = 60f+1`, `S_0 = 49f+1`, and the unpadded field circuit has `63f+4k+123` rows. Its auxiliary commitment stores `3696k+15648` bits, packed into degree-64 ring elements. Generic, fixed-zero, and fixed-one coordinates are counted separately. The exact maximum centered-digit energies are 249, 8129, and 25537 for radices 8, 64, and 128. [`norm_bounds.py`](norm_bounds.py) contains the digit recurrence and encoding calculation; [`artifacts/norm_bounds.json`](artifacts/norm_bounds.json) preserves their finite calculation and regression results.

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
| 1024 | 120,224 | 46,355 | 166,579 | 280,832 |

These are no-retry syntax counts. Incoming commitments, CRS storage, and maximum accepted-attempt counts have separate fields. The retained schedules can differ between arities, so the selected communication totals need not increase monotonically with arity. They are not claimed to minimize the full parameter space.

[`artifacts/operation_counts.json`](artifacts/operation_counts.json) reports the affected algebraic subroutines in separate units. The large-arity entry also includes sparse field applications, encoding, and sumcheck counts derived from the saved compiler shape. Smaller profiles retain their reference field counts. Algebraic operations are not machine instructions or elapsed-time estimates.

Each role is mapped to coefficient-expanded Euclidean SIS with dimensions `n = d rows`, `m = d columns`, modulus `q`, and its derived radius. [`estimator/results.md`](estimator/results.md) lists both MATZOV models. Its weakest-role summaries range only over finite reported costs. The two arity-2 carrier outputs are non-finite and remain unassigned; block sizes above the model's documented range remain flagged as extrapolations. The saved estimates do not replace the protocol's role-specific Module-SIS assumptions.
