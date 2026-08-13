# CARE-ASE outer diagnostic subgroup correction

当前 `scar -0.105394` headline 不能单独作为科学结论，因为它把 complete tri-modal 目标域病例和 no-T2 partial-modality 病例混在同一个均值里。从原始 casewise CSV 重新分层后，complete tri-modal scar 已经与 matched nnU-Net 持平并轻微高出；真正把 all-scar headline 拉低的是 partial-modality scar。

这不等于 CARE-ASE 已经整体胜过 nnU-Net：pure edema 的评价分母本来就是 T2-present 病例，combined delta 仍为负，尤其 fold3 暴露了真实的 edema 欠激活/校准问题。

## Primary Subgroup Table

| Group | Split | Cases | CARE Dice | nnU-Net Dice | Delta |
|---|---:|---:|---:|---:|---:|
| all outer scar | fold2 | 44 | 0.529509 | 0.590782 | -0.061272 |
| all outer scar | fold3 | 44 | 0.372246 | 0.521763 | -0.149516 |
| all outer scar | combined | 88 | 0.450878 | 0.556272 | -0.105394 |
| complete tri-modal scar | fold2 | 16 | 0.704129 | 0.697969 | 0.006160 |
| complete tri-modal scar | fold3 | 16 | 0.654441 | 0.647050 | 0.007391 |
| complete tri-modal scar | combined | 32 | 0.679285 | 0.672510 | 0.006775 |
| partial-modality scar | fold2 | 28 | 0.429727 | 0.529531 | -0.099805 |
| partial-modality scar | fold3 | 28 | 0.210992 | 0.450170 | -0.239177 |
| partial-modality scar | combined | 56 | 0.320360 | 0.489851 | -0.169491 |
| pure edema on T2-present | fold2 | 16 | 0.507419 | 0.506598 | 0.000822 |
| pure edema on T2-present | fold3 | 16 | 0.393242 | 0.443793 | -0.050551 |
| pure edema on T2-present | combined | 32 | 0.450331 | 0.475196 | -0.024865 |

## Complete Tri-Modal Center Breakdown

| Group | Split | Cases | CARE Dice | nnU-Net Dice | Delta |
|---|---:|---:|---:|---:|---:|
| CenterB complete scar | fold2 | 7 | 0.719907 | 0.702761 | 0.017146 |
| CenterB complete scar | fold3 | 7 | 0.617510 | 0.715274 | -0.097764 |
| CenterB complete scar | combined | 14 | 0.668708 | 0.709017 | -0.040309 |
| CenterB complete edema | fold2 | 7 | 0.608713 | 0.617819 | -0.009105 |
| CenterB complete edema | fold3 | 7 | 0.438806 | 0.524348 | -0.085542 |
| CenterB complete edema | combined | 14 | 0.523760 | 0.571083 | -0.047324 |
| CenterC complete scar | fold2 | 9 | 0.691857 | 0.694243 | -0.002385 |
| CenterC complete scar | fold3 | 9 | 0.683165 | 0.593987 | 0.089178 |
| CenterC complete scar | combined | 18 | 0.687511 | 0.644115 | 0.043396 |
| CenterC complete edema | fold2 | 9 | 0.428635 | 0.420093 | 0.008543 |
| CenterC complete edema | fold3 | 9 | 0.357803 | 0.381140 | -0.023336 |
| CenterC complete edema | combined | 18 | 0.393219 | 0.400616 | -0.007397 |

## Help/Harm And Shape Metrics

| Group | Split | Help | Harm | Tie | CARE sens | nnU-Net sens | CARE prec | nnU-Net prec | CARE HD95 | nnU-Net HD95 | CARE vol ratio | nnU-Net vol ratio | CARE empty pred | nnU-Net empty pred |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| complete tri-modal scar | fold2 | 11 | 5 | 0 | 0.737107 | 0.750335 | 0.705321 | 0.687565 | 29.271 | 31.193 | 1.176592 | 1.293962 | 0 | 0 |
| complete tri-modal scar | fold3 | 8 | 8 | 0 | 0.663391 | 0.757766 | 0.738881 | 0.665278 | 62508.375 | 62511.311 | 1.177537 | 1.429508 | 2 | 0 |
| complete tri-modal scar | combined | 19 | 13 | 0 | 0.701438 | 0.753930 | 0.720983 | 0.676421 | 31268.823 | 31271.252 | 1.177049 | 1.359549 | 2 | 0 |
| partial-modality scar | fold2 | 5 | 20 | 3 | 0.381458 | 0.574013 | 0.642905 | 0.540004 | 71451.329 | 71444.858 | 0.712842 | 1.198026 | 1 | 1 |
| partial-modality scar | fold3 | 2 | 24 | 2 | 0.154877 | 0.422540 | 0.713931 | 0.566834 | 285736.829 | 35738.950 | 0.224688 | 0.743806 | 8 | 1 |
| partial-modality scar | combined | 7 | 44 | 5 | 0.261755 | 0.493989 | 0.673129 | 0.553419 | 178594.079 | 53591.904 | 0.454950 | 0.958061 | 9 | 2 |
| pure edema on T2-present | fold2 | 6 | 10 | 0 | 0.482059 | 0.489780 | 0.634697 | 0.636976 | 25.208 | 24.374 | 0.815729 | 0.851508 | 0 | 0 |
| pure edema on T2-present | fold3 | 6 | 10 | 0 | 0.342850 | 0.401968 | 0.634391 | 0.591657 | 62528.738 | 26.047 | 0.585583 | 0.736394 | 1 | 0 |
| pure edema on T2-present | combined | 12 | 20 | 0 | 0.412455 | 0.445874 | 0.634549 | 0.614317 | 31276.973 | 25.211 | 0.700656 | 0.793951 | 1 | 0 |

## Diagnostic Boundaries

- `volume_ratio`: reported from explicit prediction/GT voxel-count fields (`PASS`); these are diagnostic-only and do not alter Dice denominators or checkpoint selection.
- `empty pred`: counted from blank precision in the existing CSV, which is emitted when there are zero predicted voxels for that class.
- `subgroup verification`: `scripts/evaluation/care_ase/verify_outer_diagnostic_subgroup_summary.py` recomputes the key subgroup rows from raw outer casewise CSV plus MyoPS metadata and writes `outer_diagnostic_subgroup_verification_receipt.json`.
- `Case2012`: fold3 complete/T2-present case with CARE scar Dice 0 and edema Dice 0; retained in the official subgroup means.
- `no-T2 baseline asymmetry`: CARE no-T2 decode excludes class 4 (`0,1,2,3,5`), while the current matched nnU-Net baseline row in `run_current_user_authorized_outer_diagnostic.py` uses direct six-class argmax. This is a diagnostic comparison asymmetry, not checkpoint-selection evidence.

## no-T2 Matched Class-Set Diagnostic

| Split | Cases | CARE scar | nnU-Net direct | nnU-Net no-T2 matched | CARE-direct delta | CARE-matched delta | matched-direct | CARE vol ratio | nnU-Net matched vol ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fold2 partial scar | 28 | 0.429727 | 0.529547 | 0.529547 | -0.099820 | -0.099820 | 0.000000 | 0.712842 | 1.198026 |
| fold3 partial scar | 28 | 0.210992 | 0.450179 | 0.450179 | -0.239187 | -0.239187 | 0.000000 | 0.224688 | 0.743806 |
| combined partial scar | 56 | 0.320360 | 0.489863 | 0.489863 | -0.169503 | -0.169503 | 0.000000 | 0.454950 | 0.958061 |

Interpretation: matched no-T2 class-set argmax produced the same scar Dice as direct six-class argmax on the partial-modality rows in this diagnostic rerun. The code asymmetry is real and now audited, but it is not the cause of the observed partial-scar deficit.

## Provenance Snapshot

| Fold | Step | training source | formal checkout | source manifest | config hash | split hash | plans hash | stock hash | contract hash |
|---:|---:|---|---|---|---|---|---|---|---|
| 2 | 5000 | `fdd45b5ee1c1abea352c318c66951910e565262f` | `fdd45b5ee1c1abea352c318c66951910e565262f` | `33ec5151957f652467a18787e7f068abb368ab575697ba27dcef0cfc1a8c5831` | `e9f9b60a10ac147d35521b8d90fc31773c09969a72f0888f0119e7c51d8819da` | `9c3e9f3b7e4565a5c3c2589ddbb913c78c0ad423f4265370585841c93c6f880a` | `06492f8fc75b5de383a28006f76b7f1099f305422953cf9d4f89ae1ec38d3e2f` | `31470ab242055b0af5c783f0f522bc8e490199cb2b4d42f5d0cefffb41de019b` | `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d` |
| 3 | 4000 | `fdd45b5ee1c1abea352c318c66951910e565262f` | `fdd45b5ee1c1abea352c318c66951910e565262f` | `33ec5151957f652467a18787e7f068abb368ab575697ba27dcef0cfc1a8c5831` | `5ffefbc3d0df432efac993f522f7d275f3f2c71c3fab8a959acdbb78fe3da9f8` | `9c3e9f3b7e4565a5c3c2589ddbb913c78c0ad423f4265370585841c93c6f880a` | `06492f8fc75b5de383a28006f76b7f1099f305422953cf9d4f89ae1ec38d3e2f` | `0c27009930261c93a4890c66aa7f88f226a5f8b32a3358e43dd10d357b6fdeb8` | `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d` |

Provenance judgment: `NO_NEW_FAITHFULNESS_REGRESSION_EVIDENCE`. The inspected checkpoints bind the same frozen contract and source manifest; the post-review changes visible before `fdd45b5` are formal runtime/path/cache namespace, authorization, fold selection, checkpoint cadence, and monitoring/evidence wiring, not model/loss/sampler/inference semantic redesign.

Operational judgment: continue formal training to the frozen 14000-step schedule. The current 4000/5000-step mixed outer metrics justify reporting correction and later diagnostic monitoring, not early implementation block.
