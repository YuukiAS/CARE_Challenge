# CARE-ASE outer diagnostic subgroup correction

当前 `scar -0.105394` headline 不能单独作为科学结论，因为它把 complete tri-modal 目标域病例和 no-T2 partial-modality 病例混在同一个均值里。从原始 casewise CSV 重新分层后，complete tri-modal scar 已经与 matched nnU-Net 持平并轻微高出；真正把 all-scar headline 拉低的是 partial-modality scar。

这不等于 CARE-ASE 已经整体胜过 nnU-Net：pure edema 的评价分母本来就是 T2-present 病例，combined delta 仍为负，尤其 fold3 暴露了真实的 edema 欠激活/校准问题。

## Primary Subgroup Table

| Group | Split | Cases | CARE Dice | nnU-Net Dice | Delta |
|---|---:|---:|---:|---:|---:|
| all outer scar | fold2 | 44 | 0.567347 | 0.590806 | -0.023459 |
| all outer scar | fold3 | 44 | 0.217733 | 0.521776 | -0.304043 |
| all outer scar | combined | 88 | 0.392540 | 0.556291 | -0.163751 |
| complete tri-modal scar | fold2 | 16 | 0.694271 | 0.698013 | -0.003742 |
| complete tri-modal scar | fold3 | 16 | 0.598765 | 0.647076 | -0.048311 |
| complete tri-modal scar | combined | 32 | 0.646518 | 0.672544 | -0.026026 |
| partial-modality scar | fold2 | 28 | 0.494819 | 0.529544 | -0.034725 |
| partial-modality scar | fold3 | 28 | 0.000000 | 0.450176 | -0.450176 |
| partial-modality scar | combined | 56 | 0.247409 | 0.489860 | -0.242451 |
| pure edema on T2-present | fold2 | 16 | 0.512826 | 0.506578 | 0.006249 |
| pure edema on T2-present | fold3 | 16 | 0.448863 | 0.443799 | 0.005065 |
| pure edema on T2-present | combined | 32 | 0.480845 | 0.475188 | 0.005657 |

## Complete Tri-Modal Center Breakdown

| Group | Split | Cases | CARE Dice | nnU-Net Dice | Delta |
|---|---:|---:|---:|---:|---:|
| CenterB complete scar | fold2 | 7 | 0.701409 | 0.702832 | -0.001423 |
| CenterB complete scar | fold3 | 7 | 0.629544 | 0.715480 | -0.085936 |
| CenterB complete scar | combined | 14 | 0.665477 | 0.709156 | -0.043679 |
| CenterB complete edema | fold2 | 7 | 0.607091 | 0.617815 | -0.010724 |
| CenterB complete edema | fold3 | 7 | 0.513604 | 0.524436 | -0.010832 |
| CenterB complete edema | combined | 14 | 0.560348 | 0.571126 | -0.010778 |
| CenterC complete scar | fold2 | 9 | 0.688719 | 0.694265 | -0.005546 |
| CenterC complete scar | fold3 | 9 | 0.574826 | 0.593872 | -0.019047 |
| CenterC complete scar | combined | 18 | 0.631772 | 0.644069 | -0.012296 |
| CenterC complete edema | fold2 | 9 | 0.439509 | 0.420059 | 0.019450 |
| CenterC complete edema | fold3 | 9 | 0.398509 | 0.381081 | 0.017428 |
| CenterC complete edema | combined | 18 | 0.419009 | 0.400570 | 0.018439 |

## Help/Harm And Shape Metrics

| Group | Split | Help | Harm | Tie | CARE sens | nnU-Net sens | CARE prec | nnU-Net prec | CARE HD95 | nnU-Net HD95 | CARE vol ratio | nnU-Net vol ratio | CARE empty pred | nnU-Net empty pred |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| complete tri-modal scar | fold2 | 10 | 6 | 0 | 0.718927 | 0.750369 | 0.707285 | 0.687609 | 28.119 | 31.193 | 1.147635 | 1.293833 | 0 | 0 |
| complete tri-modal scar | fold3 | 6 | 9 | 1 | 0.686016 | 0.757769 | 0.650981 | 0.665235 | 62509.724 | 62511.311 | 1.252230 | 1.429622 | 0 | 0 |
| complete tri-modal scar | combined | 16 | 15 | 1 | 0.703002 | 0.753950 | 0.679133 | 0.676422 | 31268.921 | 31271.252 | 1.198245 | 1.359537 | 0 | 0 |
| partial-modality scar | fold2 | 8 | 17 | 3 | 0.483258 | 0.574035 | 0.597548 | 0.540009 | 71448.091 | 71444.857 | 0.924511 | 1.198053 | 1 | 1 |
| partial-modality scar | fold3 | 0 | 26 | 2 | 0.000000 | 0.422537 | NA | 0.566833 | 1000000.000 | 35738.950 | 0.000000 | 0.743727 | 28 | 1 |
| partial-modality scar | combined | 8 | 43 | 5 | 0.227952 | 0.493999 | 0.597548 | 0.553421 | 535724.045 | 53591.903 | 0.436090 | 0.958032 | 29 | 2 |
| pure edema on T2-present | fold2 | 11 | 5 | 0 | 0.508124 | 0.489750 | 0.584648 | 0.636958 | 33.881 | 24.375 | 0.877447 | 0.851601 | 0 | 0 |
| pure edema on T2-present | fold3 | 9 | 7 | 0 | 0.419480 | 0.401935 | 0.577925 | 0.591702 | 28.340 | 26.048 | 0.794856 | 0.736170 | 0 | 0 |
| pure edema on T2-present | combined | 20 | 12 | 0 | 0.463802 | 0.445842 | 0.581286 | 0.614330 | 31.110 | 25.212 | 0.836152 | 0.793885 | 0 | 0 |

## Diagnostic Boundaries

- `volume_ratio`: reported from explicit prediction/GT voxel-count fields (`PASS`); these are diagnostic-only and do not alter Dice denominators or checkpoint selection.
- `empty pred`: counted from blank precision in the existing CSV, which is emitted when there are zero predicted voxels for that class.
- `subgroup verification`: `scripts/evaluation/care_ase/verify_outer_diagnostic_subgroup_summary.py` recomputes the key subgroup rows from raw outer casewise CSV plus MyoPS metadata and writes `outer_diagnostic_subgroup_verification_receipt.json`.
- `Case2012`: fold3 complete/T2-present case with CARE scar Dice 0 and edema Dice 0; retained in the official subgroup means.
- `no-T2 baseline asymmetry`: CARE no-T2 decode excludes class 4 (`0,1,2,3,5`), while the current matched nnU-Net baseline row in `run_current_user_authorized_outer_diagnostic.py` uses direct six-class argmax. This is a diagnostic comparison asymmetry, not checkpoint-selection evidence.

## no-T2 Matched Class-Set Diagnostic

| Split | Cases | CARE scar | nnU-Net direct | nnU-Net no-T2 matched | CARE-direct delta | CARE-matched delta | matched-direct | CARE vol ratio | nnU-Net matched vol ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fold2 partial scar | 28 | 0.494819 | 0.529544 | 0.529544 | -0.034725 | -0.034725 | 0.000000 | 0.924511 | 1.198053 |
| fold3 partial scar | 28 | 0.000000 | 0.450176 | 0.450176 | -0.450176 | -0.450176 | 0.000000 | 0.000000 | 0.743727 |
| combined partial scar | 56 | 0.247409 | 0.489860 | 0.489860 | -0.242451 | -0.242451 | 0.000000 | 0.436090 | 0.958032 |

Interpretation: matched no-T2 class-set argmax produced the same scar Dice as direct six-class argmax on the partial-modality rows in this diagnostic rerun. The code asymmetry is real and now audited, but it is not the cause of the observed partial-scar deficit.

## Provenance Snapshot

| Fold | Step | training source | formal checkout | source manifest | config hash | split hash | plans hash | stock hash | contract hash |
|---:|---:|---|---|---|---|---|---|---|---|
| 2 | 12000 | `fdd45b5ee1c1abea352c318c66951910e565262f` | `fdd45b5ee1c1abea352c318c66951910e565262f` | `33ec5151957f652467a18787e7f068abb368ab575697ba27dcef0cfc1a8c5831` | `e9f9b60a10ac147d35521b8d90fc31773c09969a72f0888f0119e7c51d8819da` | `9c3e9f3b7e4565a5c3c2589ddbb913c78c0ad423f4265370585841c93c6f880a` | `06492f8fc75b5de383a28006f76b7f1099f305422953cf9d4f89ae1ec38d3e2f` | `31470ab242055b0af5c783f0f522bc8e490199cb2b4d42f5d0cefffb41de019b` | `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d` |
| 3 | 11000 | `fdd45b5ee1c1abea352c318c66951910e565262f` | `fdd45b5ee1c1abea352c318c66951910e565262f` | `33ec5151957f652467a18787e7f068abb368ab575697ba27dcef0cfc1a8c5831` | `5ffefbc3d0df432efac993f522f7d275f3f2c71c3fab8a959acdbb78fe3da9f8` | `9c3e9f3b7e4565a5c3c2589ddbb913c78c0ad423f4265370585841c93c6f880a` | `06492f8fc75b5de383a28006f76b7f1099f305422953cf9d4f89ae1ec38d3e2f` | `0c27009930261c93a4890c66aa7f88f226a5f8b32a3358e43dd10d357b6fdeb8` | `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d` |

Provenance judgment: `NO_NEW_FAITHFULNESS_REGRESSION_EVIDENCE`. The inspected checkpoints bind the same frozen contract and source manifest; the post-review changes visible before `fdd45b5` are formal runtime/path/cache namespace, authorization, fold selection, checkpoint cadence, and monitoring/evidence wiring, not model/loss/sampler/inference semantic redesign.

Operational judgment: continue formal training to the frozen 14000-step schedule. The current 4000/5000-step mixed outer metrics justify reporting correction and later diagnostic monitoring, not early implementation block.
