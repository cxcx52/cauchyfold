# Exact syntax-level communication

This ledger fixes CF† v2, Profile I, k=16 and the compiler output in this directory. The actual field depth is 21; the handoff has 505599 fixed-zero coordinates. Both values come from the generated layout, not a capacity substituted for a circuit size.

| Message group | P→V bytes | V→P bytes |
|---|---|---|
| 16 incoming fresh commitments, separate | 196608 | — |
| Incoming accumulator commitment, separate | 12288 | — |
| Carrier/output/field auxiliary commitments | 36864 | — |
| Cauchy challenge | — | 24 |
| Field sumcheck and terminal evaluations | 2088 | 1008 |
| Nonterminal fixed lattice payloads | 87360 | — |
| Terminal fixed lattice payload | 216366 | — |
| Retry/accept tags, no retry / maximum | 12 / 1920 | — |
| Independent projections, one attempt per layer | — | 472103424 |
| Aggregation randomness, once per layer | — | 10286694 |
| Short challenges, one attempt per layer | — | 840 |
| Fold without retries | 342690 | 482391990 |
| Accepted fold at both retry caps | 344598 | 75546969966 |

The no-retry interactive fold totals **482734680 bytes**. An accepted transcript with all projection and response attempt counts at 160 totals **75547314564 bytes**. These counts exclude the separately listed incoming commitments. Transporting all 17 incoming commitments adds 208896 bytes.

For arbitrary accepted attempt counts P_i,C_i, the exact fold lengths are `342678+sum_i(P_i+C_i)` P→V bytes and `10287726+sum_i(216*N_i*P_i+24*s_i*C_i)` V→P bytes. Here N_i is the padded coefficient length and s_i is the block count in the six-row schedule. Each P_i,C_i lies in1,…,160. Failed or malformed sessions can end earlier; they have no single full-transcript length.

Profile I sends the sampled independent projection matrices explicitly. No seed replaces these messages. The public instance, parameter identifier and CRS are prior public inputs and lie outside this fold syntax; their application transport is not assigned a hidden zero cost. The output public coordinates are computed from the public inputs and Cauchy challenge.

The result is **syntax-level exact communication, not measured serialized proof files**. One ACCEPT/RETRY byte is counted for every attempt; successful payloads occur only once at their prescribed checkpoints. The full per-layer message list and parser conventions are in communication_ledger.json and SERIALIZATION_CONTRACT.md.
