# Field-reduction comparison

The relation consists of four length-eight dot products, Q_j(z)=Σ_l a_jl b_jl−u x_j. A fresh state has u=1, Q(z)=0, and base-field coordinates. An accumulated state has Q(z)=E over the declared quartic extension. The state commitment includes a canonical encoding of z and E.

The carrier variant commits a degree-less-than-k polynomial before the Cauchy challenge, forms the folded state and residual from it, and checks the output quadratic equation. The direct variant instead checks every source quadratic equation, the linear state fold, and Q(z*)=E*. For valid sources, both produce the same semantic output. State encoding and the honest opening bound are preserved in both variants.

## Grouped constraints

A group is a sum of sparse products, F_j(b)=Σ_{t in group j}(A_t(b)B_t(b)−C_t(b)). This avoids introducing encoded intermediate values for every product. After commitments are fixed, sample r and weight each term by eq(r,j(t)). Sumcheck on W̃(ÃB̃−C̃) has individual degree three. Its terminal values Ã(τ), B̃(τ), C̃(τ) give twelve scalar equations over the base field, together with the commitment and fixed-coordinate equations.

A general cubic round needs three transmitted coefficients: the current claim s determines g₀=(s−g₁−g₂−g₃)/2. The original ungrouped carrier relation has an equality factor and supports its two-coefficient encoding. The grouped carrier comparison applies the same gate-elimination optimization as the direct compiler.

## Extraction interface

For a fixed bad opening, the field error is at most 1−(1−|K|⁻¹)^g(1−3|K|⁻¹)^ℓ, where g and ℓ are the batching and sumcheck dimensions. At fixed post-challenge commitments, two independent field recovery trials either agree on an opening or yield a short kernel from differing commitment segments. Public offsets cancel, and coordinate insertion does not increase the norm. With the original linear-chain extraction theorem, this gives direct-source extraction with loss κ_chain+ε_F and frontend comparison radius 2γ₀. The direct relation already checks source validity, so its argument needs no additional pre-Cauchy comparison.

This composition relies on the linear-chain theorem and its checkpoint, norm, and retry hypotheses. Estimator results and finite compiler tests do not prove those hypotheses. The saved estimates use coefficient-SIS dimensions n=d·rows and m=d·columns and retain the per-role radius and extrapolation flag.

## Field arithmetic

For padded length P=2²³, the specified dense pair-polynomial and table-fold loops use 14(P−1) extension-field multiplications for a generic four-table implementation and 9(P−1) when the equality factor is used. These are partial operation counts, excluding other field work, commitments, and the backend.

The direct group map differs from the term index at only 36,943 positions. Choosing equality weights on zero-padding rows leaves the Boolean sum unchanged. The public weight then decomposes as W̃=eq_r+Δ̃, with sparse Δ. Reusing the equality-factor loop and tracking the correction gives at most 77,766,415 multiplications in those same core loops, versus 75,497,463 for the original carrier and 117,440,498 for the generic direct implementation.

`checks/sparse_weights.py` checks the new algorithm against a generic implementation on small transcripts over the actual extension field. The large-instance bound comes from the deterministic group map and is not a full optimized arity-1024 prover run. It preserves the grouped protocol's three-coefficient message count.

## Scope of the results

The comparison retains the selected backend schedule and recomputes dimensions and bounds. It is not a global parameter search. Communication, field-core arithmetic, CRS storage, and projection work are distinct costs; they are not combined into a running-time claim. Relation-size scans are layout derivations, not newly compiled and screened profiles. Deterministic fixture coins are for regression tests, not production randomness or Fiat–Shamir challenges.
