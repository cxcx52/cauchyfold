# Official lattice-estimator results

## Scope

These results use the unmodified official `malb/lattice-estimator` commit
`53da5982597709ba0fdf94ea37a84d822310fd84` under SageMath 10.9. Each
Module-SIS role is mapped to a coefficient-expanded Euclidean SIS instance
with `n = d * rows`, `m = d * columns`, and the registered coefficient
`l2` radius. Both classical and quantum MATZOV reduction-cost models are run.

This is a heuristic attack-cost screening result. It does not model every
possible module-specific attack and does not by itself certify the complete
protocol reduction or a concrete security level.

## Regression and completion

- Classical regression: 255.490229 log2(rop), expected 255.490229.
- Quantum regression: 238.730181 log2(rop), expected 238.730181.
- Completed role/model jobs: 34/34.
- Nonfinite or failed jobs: 0.

## Weakest estimates

- Classical: `A_1`, 257.585 log2(rop), block size 804, lattice attack dimension 4979.
- Quantum: `A_1`, 240.628 log2(rop), block size 804, lattice attack dimension 4979.

Both weakest estimates use block size 804 and are not marked as extrapolated
by the package threshold. Results whose block size exceeds 1024 are explicitly
marked `EXTRAPOLATED_ABOVE_1024` below.

## Per-role results

| role | module shape | coefficient SIS `(n,m)` | radius | classical log2(rop) / beta | quantum log2(rop) / beta | fit |
|---|---:|---:|---:|---:|---:|---|
| `A_st` | 32 x 219 | (2,048, 14,016) | 44,071 | 2070.073 / 7206 | 1870.967 / 7206 | extrapolated |
| `A_H` | 32 x 12288 | (2,048, 786,432) | 44,071 | 2070.073 / 7206 | 1870.967 / 7206 | extrapolated |
| `A_aux` | 32 x 237198 | (2,048, 15,180,672) | 44,071 | 2070.073 / 7206 | 1870.967 / 7206 | extrapolated |
| `A_0` | 28 x 15807 | (1,792, 1,011,648) | 12,330,665,646 | 276.645 / 872 | 257.775 / 872 | within fit or unknown |
| `B_0` | 16 x 6720 | (1,024, 430,080) | 376,257 | 583.582 / 1965 | 533.824 / 1965 | extrapolated |
| `D_0` | 16 x 11160 | (1,024, 714,240) | 376,257 | 583.582 / 1965 | 533.824 / 1965 | extrapolated |
| `A_1` | 28 x 3536 | (1,792, 226,304) | 25,109,346,730 | 257.585 / 804 | 240.628 / 804 | within fit or unknown |
| `B_1` | 16 x 2744 | (1,024, 175,616) | 383,127 | 581.609 / 1958 | 532.049 / 1958 | extrapolated |
| `D_1` | 16 x 2205 | (1,024, 141,120) | 383,127 | 581.609 / 1958 | 532.049 / 1958 | extrapolated |
| `A_2` | 28 x 1503 | (1,792, 96,192) | 17,190,024,523 | 267.394 / 839 | 249.453 / 839 | within fit or unknown |
| `B_2` | 16 x 1568 | (1,024, 100,352) | 262,291 | 624.764 / 2111 | 570.867 / 2111 | extrapolated |
| `D_2` | 16 x 756 | (1,024, 48,384) | 262,291 | 624.764 / 2111 | 570.867 / 2111 | extrapolated |
| `A_3` | 28 x 889 | (1,792, 56,896) | 13,777,860,934 | 273.561 / 861 | 255.001 / 861 | within fit or unknown |
| `B_3` | 16 x 1176 | (1,024, 75,264) | 210,228 | 652.135 / 2208 | 595.486 / 2208 | extrapolated |
| `D_3` | 16 x 441 | (1,024, 28,224) | 210,228 | 652.135 / 2208 | 595.486 / 2208 | extrapolated |
| `A_4` | 28 x 679 | (1,792, 43,456) | 430,545,016 | 400.506 / 1313 | 369.199 / 1313 | extrapolated |
| `B_pivot` | 4 x 448 | (256, 28,672) | 1,355 | 439.460 / 1460 | 403.999 / 1460 | extrapolated |

## Reproducibility

- SageMath: 10.9.
- Python: 3.12.14.
- Estimator checkout: clean, detached at the pinned commit.
- Raw role/model JSON files, captured estimator fields, environment metadata,
  and the conda explicit package list are stored beside this report.
