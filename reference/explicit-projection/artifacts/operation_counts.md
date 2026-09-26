# Concrete typed operation counts

The counts use the selected sparse relation and deterministic compiler. They count stated arithmetic loops, not elapsed time. A field multiplication, ring multiplication, bounded-coefficient product and bit operation remain distinct units.

## Relation and carrier

For j=0,…,3, Q_j(z)=sum_(l=0)^7 a_(j,l)b_(j,l)−u x_j. One Q evaluation uses 36 K multiplications and 32 K additions/subtractions. Direct polarization uses 72 K multiplications and 68 K additions/subtractions. U=J=I_4; each basis application copies four K coordinates and performs no field arithmetic.

| Algorithm | Q calls | B calls | J calls | K-by-Fq products | K products | K additions/subtractions |
|---|---|---|---|---|---|---|
| Streaming pairs | 0 | 136 | 136 | 8224 | 9792 | 17472 |
| Multipoint, source Q cached | 16 | 0 | 16 | 43372 | 576 | 48624 |
| Pole-residue | 0 | 16 | 16 | 41995 | 1152 | 46720 |

The map-call columns identify work already expanded into the arithmetic columns; they must not be added again. Multipoint construction with uncached source Q-values adds 17 Q calls,612 K products and 544 K additions. All three algorithms compute the same carrier. Schoolbook polynomial loops are counted here. Their faster polynomial-arithmetic asymptotics are stated separately in the final section.

Shared public preparation for the fast algorithms costs 1693 Fq products,1630 Fq additions/subtractions and 48 inversions under the direct-inverse model. The unoptimized streaming reference additionally prepares its P_i/P_ij polynomials with 29040 Fq products and 29040 additions. These costs are outside the online carrier table.

## Encoding and sparse field circuit

| Compiler quantity | Count |
|---|---|
| Canonical encoded K values | 1414 |
| Canonical Fq coefficients | 5656 |
| Canonical value bits | 271488 |
| Prefix helper bits | 271488 |
| Private bits in all committed segments | 542976 |
| Fixed-zero handoff coordinates | 505599 |
| Padded zero constraint rows | 745214 |

The full canonical comparator, row-category and compilation counts are in `compiler_artifacts/operation_derivation.json`, copied into `operation_counts.json`. Bit extraction, prefix Boolean operations, artifact writes and finite-field arithmetic are separate quantities.

The literal witness builder rematerializes all source, carrier, output and gate encodings. The incoming commitment matvecs remain excluded from fold work. It performs 1232 K products and 1232 K additions for the folded z/E values, followed by 36 products for the Q gate values. Public coefficient preparation also uses one K inversion and 360 Fq negations; these are separate from the multiplication/addition columns below.

| Field operation | K-by-Fq products | K products | K additions/subtractions |
|---|---|---|---|
| Public coefficient preparation, each party once | 0 | 9391 | 96 |
| Folded semantic state/residual construction | 0 | 1232 | 1232 |
| Auxiliary Q product-gate values | 0 | 36 | 0 |
| A applied to encoded b | 1358814 | 0 | 6876 |
| Aᵀ eq_tau, each party once | 0 | 1358814 | 815837 |
| B applied to encoded b | 2384833 | 0 | 1032895 |
| Bᵀ eq_tau, each party once | 0 | 2384833 | 1336257 |
| C applied to encoded b | 278400 | 0 | 6876 |
| Cᵀ eq_tau, each party once | 0 | 278400 | 0 |
| Prover equality table | 0 | 2097151 | 2097151 |
| Prover sumcheck table rounds | 0 | 29360114 | 35651567 |
| Verifier equality table for transposes | 0 | 2097151 | 2097151 |
| Verifier sumcheck rounds | 0 | 63 | 147 |
| Verifier final identity | 0 | 64 | 64 |

Sparse counts execute one product per stored coefficient, including a stored zero coefficient. Each nonempty dot product starts with its first product. This makes the declared loop counts independent of the Cauchy challenge. Reference actual nonzero counts are retained separately. The sparse A/B/C applications multiply K coefficients by input bits in Fq. Transposes multiply K coefficients by K equality-table values. Their arithmetic units therefore differ.

The sumcheck table loops already produce the final t_A,t_B,t_C values; reading those three entries requires no additional evaluation circuit. The verifier's terminal equality computation and equality table are listed separately. Field-row materialization and all twelve scalar rows of the initial lattice relation are included in `initial_relation_operator`.

## Commitments and lattice layers

| New commitment | Rq products | Rq additions |
|---|---|---|
| New state | 7008 | 6976 |
| Carrier | 6144 | 6112 |
| Field auxiliary | 139200 | 139168 |

Fresh and accumulator commitment construction is listed separately in JSON, outside fold prover work. Ring matvec counts are a fixed reference algorithm. A bit-aware implementation could replace products by conditional additions, but that data-dependent optimization is not used to lower these counts.

| Level | All t Rq products | Symmetric h Rq products | u1/pivot Rq products | u2 Rq products | Projection trits per attempt | Bounded-coefficient products per response |
|---|---|---|---|---|---|---|
| 0 | 393336 | 442503 | 27648 | 17280 | 906246144 | 67129344 |
| 1 | 154800 | 116100 | 18432 | 8064 | 356659200 | 26419200 |
| 2 | 91440 | 57150 | 15360 | 5760 | 210677760 | 15605760 |
| 3 | 68256 | 34128 | 12288 | 3840 | 157261824 | 11649024 |
| 4 | 58368 | 29184 | 12288 | 3840 | 134479872 | 9961472 |
| 5 | 53424 | 46746 | 1536 | 0 | 123088896 | 9117696 |

Commitment and h preparation occur once per layer. Projection and response counts are per attempt. For a realized projection, signed additions equal the number of nonzero trits; their expectation is half the inspected trits. These are recorded as a realized-count formula and an expectation, not a fabricated exact deterministic value. Each trit uses two independent fair bits.

The JSON includes ring additions, all radix operations, retry norm checks, first and recursive Apply/TransposeApply circuits, pivot recovery, terminal relation checks and verifier work. No typed counts are collapsed into a unit-free total or converted to seconds.
