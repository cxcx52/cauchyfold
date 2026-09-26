# Official lattice-estimator results: CF† v2 Profile I, k=16

Selected task counts: `{'DONE_FINITE': 40}`. Front-end status: `DONE_FINITE`.

Pinned upstream commit: `53da5982597709ba0fdf94ea37a84d822310fd84`. No upstream or protocol parameter modifications.

The two cost models are official `MATZOV(nn='classical')` and `MATZOV(nn='quantum')`; the latter uses the depth-times-width nearest-neighbor convention. Coefficient expansion is `n=64*rows`, `m=64*columns`, coefficient l2 bound `beta`. All runs use `SIS.estimate`, not its rough interface.

These are generic q-ary lattice attack estimates on coefficient-expanded Module-SIS dimensions. The estimator does not certify module-specific attack coverage or the full reduction advantage. The reported minimum is among the attacks implemented and returned at this commit. Values below are log2(rop), not a security proof.

| Matrix | Rows | Columns | Coefficient l2 radius | Coefficient SIS (n,m) | Classical log2(rop) | Quantum log2(rop) | BKZ block size | Fit range |
|---|---:|---:|---:|---|---:|---:|---:|---|
| backend_0_A | 24 | 1821 | 4567851477 | (1536, 116544) | 255.490229 | 238.730181 | 797 | WITHIN_DOCUMENTED_FIT_RANGE |
| backend_0_B | 16 | 1728 | 139383 | (1024, 110592) | 708.029999 | 645.762494 | 2406 | EXTRAPOLATED_ABOVE_1024 |
| backend_0_D | 16 | 1080 | 139383 | (1024, 69120) | 708.029999 | 645.762494 | 2406 | EXTRAPOLATED_ABOVE_1024 |
| backend_1_A | 24 | 1075 | 3861716751 | (1536, 68800) | 260.253045 | 243.014926 | 814 | WITHIN_DOCUMENTED_FIT_RANGE |
| backend_1_B | 16 | 1152 | 117836 | (1024, 73728) | 732.600006 | 667.862561 | 2493 | EXTRAPOLATED_ABOVE_1024 |
| backend_1_D | 16 | 504 | 117836 | (1024, 32256) | 732.600006 | 667.862561 | 2493 | EXTRAPOLATED_ABOVE_1024 |
| backend_2_A | 24 | 762 | 3353291926 | (1536, 48768) | 264.176141 | 246.544243 | 828 | WITHIN_DOCUMENTED_FIT_RANGE |
| backend_2_B | 16 | 960 | 102322 | (1024, 61440) | 754.350020 | 687.426014 | 2570 | EXTRAPOLATED_ABOVE_1024 |
| backend_2_D | 16 | 360 | 102322 | (1024, 23040) | 754.350020 | 687.426014 | 2570 | EXTRAPOLATED_ABOVE_1024 |
| backend_3_A | 24 | 711 | 3025014479 | (1536, 45504) | 266.979220 | 249.066012 | 838 | WITHIN_DOCUMENTED_FIT_RANGE |
| backend_3_B | 16 | 768 | 92305 | (1024, 49152) | 770.736050 | 702.164711 | 2628 | EXTRAPOLATED_ABOVE_1024 |
| backend_3_D | 16 | 240 | 92305 | (1024, 15360) | 770.736050 | 702.164711 | 2628 | EXTRAPOLATED_ABOVE_1024 |
| backend_4_A | 24 | 608 | 2902545478 | (1536, 38912) | 268.380127 | 250.326251 | 843 | WITHIN_DOCUMENTED_FIT_RANGE |
| backend_4_B | 16 | 768 | 88568 | (1024, 49152) | 777.517268 | 708.264196 | 2652 | EXTRAPOLATED_ABOVE_1024 |
| backend_4_D | 16 | 240 | 88568 | (1024, 15360) | 777.517268 | 708.264196 | 2652 | EXTRAPOLATED_ABOVE_1024 |
| backend_5_A | 24 | 318 | 181386952 | (1536, 20352) | 370.277913 | 341.992942 | 1206 | EXTRAPOLATED_ABOVE_1024 |
| backend_5_pivot | 4 | 384 | 1255 | (256, 24576) | 450.689099 | 414.096839 | 1500 | EXTRAPOLATED_ABOVE_1024 |
| frontend_state | 32 | 219 | 8192 | (2048, 14016) | 3124.362637 | 2819.195639 | 10912 | EXTRAPOLATED_ABOVE_1024 |
| frontend_carrier | 32 | 192 | 8192 | (2048, 12288) | 3305.553978 | 2981.964406 | 11555 | EXTRAPOLATED_ABOVE_1024 |
| frontend_auxiliary | 32 | 4350 | 8192 | (2048, 278400) | 3102.031169 | 2799.155880 | 10832 | EXTRAPOLATED_ABOVE_1024 |

Memory and attack success probability are **not reported** by the official Euclidean SIS branch. They are stored as null with an explicit reason; no infinity-norm success probability or proxy memory estimate is substituted.

The MATZOV source states that its fitted data cover block size up to 1024. Outputs using larger block sizes are **model extrapolations**, marked in JSON. Finite output alone is not a calibrated security certificate.

The front-end independent matrices `A_st`, `A_H`, and `A_aux` are evaluated only after their generated inputs become READY. Current readiness and results are in the JSON frontend_records. The shared state matrix is counted once. Unresolved matrices cannot be covered by the backend minimum.

Raw results, errors, stdout/stderr, model configuration, wall/CPU time, and process peak RSS are in `estimator_raw/`. Time/RSS here measure estimator execution only, never protocol performance.

Weakest classical **among completed backend outputs**: `backend_0_A` at 255.490229 log2(rop).
Weakest quantum **among completed backend outputs**: `backend_0_A` at 238.730181 log2(rop).

Weakest classical **across all 20 independently sampled node matrices**: `backend_0_A` at 255.490229 log2(rop), block size 797.
Weakest quantum **across all 20 independently sampled node matrices**: `backend_0_A` at 238.730181 log2(rop), block size 797.
