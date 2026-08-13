# CARE-ASE Stage-B Forgetting Diagnostic

这不是单纯的评估口径问题。formal-inner 全量结果已经显示 no-T2/partial scar 在 Stage B 内真实遗忘，fold3 从 step2000 的 0.862 降到 step6000 的 0.045，且 22/22 no-T2 scar case 变成空预测；补充 GPU 只读诊断显示 actual-train partial 在 fold3 step6000 的选例同样全空，因此更支持训练动力学/目标竞争崩塌，而不是普通 held-out 泛化失败。当前没有发现新的实现性 regression 或 partial runtime 语义 bug，诊断证据不足以阻断 frozen 14000-step formal training，应继续训练并把该问题作为 post-run scientific diagnosis 记录。

## Direct Answers

- 评估口径：不是单纯口径问题；6-case panel 只能作为 `CORE_6_CASE_INNER_TREND_PANEL`，但 35-case formal-inner no-T2 scar 和 GPU actual-train 选例都支持真实退化。
- 新实现 regression：未发现；当前状态为 `NO_PARTIAL_RUNTIME_SEMANTIC_BUG_FOUND` / `NO_NEW_IMPLEMENTATION_REGRESSION_EVIDENCE`。
- forgetting：支持 `REAL_STAGE_B_PARTIAL_NO_T2_SCAR_FORGETTING`，fold3 强于 fold2。
- 起始层级：更像 `FINAL_CLASS_COMPETITION_COLLAPSE_WITH_SHARED_REPRESENTATION_DRIFT`，不是 extent/wall 单独导致，也不是 sampler 未采到。
- 当前训练：继续 frozen schedule 到 14000；不得 early stop、回滚、调参或按诊断选择 checkpoint。

## Formal Inner Subgroup Trend

| fold | step | complete scar Dice | no-T2 scar Dice | complete edema Dice | no-T2 empty scar cases |
|---:|---:|---:|---:|---:|---:|
| 2 | 2000 | 0.961 | 0.873 | 0.905 | 0/22 |
| 2 | 4000 | 0.929 | 0.763 | 0.844 | 0/22 |
| 2 | 6000 | 0.930 | 0.668 | 0.841 | 0/22 |
| 3 | 2000 | 0.954 | 0.862 | 0.909 | 1/22 |
| 3 | 4000 | 0.920 | 0.530 | 0.857 | 1/22 |
| 3 | 6000 | 0.920 | 0.045 | 0.852 | 22/22 |

## Actual-Train Vs Inner GPU Spot Check

GPU 诊断是 selected-case full-volume inference，不代表 full actual-train 均值；它用于区分训练动力学崩塌与 held-out 泛化失败。

| fold | step | inner selected no-T2 scar | actual-train selected no-T2 scar | actual-train empty | complete control scar |
|---:|---:|---:|---:|---:|---:|
| 2 | 2000 | 0.830 | 0.896 | 0/3 | 0.962 |
| 2 | 4000 | 0.633 | 0.833 | 0/3 | 0.939 |
| 2 | 6000 | 0.312 | 0.684 | 0/3 | 0.938 |
| 3 | 2000 | 0.849 | 0.906 | 0/3 | 0.961 |
| 3 | 4000 | 0.646 | 0.813 | 0/3 | 0.938 |
| 3 | 6000 | 0.000 | 0.000 | 3/3 | 0.940 |

## GT-Scar Logit Margin

| fold | step | role | margin scar-vs-myo mean | frac margin > 0 | z_scar mean | myo logit mean | scar half mean | scar full mean |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 2 | 2000 | inner | 3.626 | 0.836 | 4.398 | 1.010 | 6.060 | 4.398 |
| 2 | 2000 | actual-train | 6.280 | 0.933 | 6.037 | 0.054 | 7.992 | 6.037 |
| 2 | 4000 | inner | -0.794 | 0.543 | 3.982 | 5.202 | 5.931 | 3.982 |
| 2 | 4000 | actual-train | 3.658 | 0.853 | 6.111 | 3.401 | 9.319 | 6.111 |
| 2 | 6000 | inner | -4.388 | 0.209 | 3.253 | 7.926 | 5.287 | 3.253 |
| 2 | 6000 | actual-train | 1.586 | 0.674 | 6.248 | 5.379 | 9.929 | 6.248 |
| 3 | 2000 | inner | 4.432 | 0.899 | 4.777 | 0.632 | 6.360 | 4.777 |
| 3 | 2000 | actual-train | 8.064 | 0.946 | 6.846 | -0.904 | 9.222 | 6.846 |
| 3 | 4000 | inner | -0.878 | 0.572 | 4.222 | 5.950 | 5.334 | 4.222 |
| 3 | 4000 | actual-train | 2.355 | 0.799 | 7.323 | 6.035 | 8.586 | 7.323 |
| 3 | 6000 | inner | -24.560 | 0.000 | 2.392 | 27.664 | 7.325 | 2.392 |
| 3 | 6000 | actual-train | -16.081 | 0.231 | 5.772 | 22.663 | 10.339 | 5.772 |

Interpretation: fold3 step6000 still has nonzero scar-half/scar-full/z_scar signals, but myocardium logit rises far above scar on GT scar voxels. This supports `FINAL_COMPETITION_MYOCARDIUM_DOMINANCE_SIGNAL`; fold2 shows the same direction more weakly.

## Extent / Wall Intervention

| fold | step | role | cases | Dice delta without extent/wall | rescued empty cases | changed voxels mean |
|---:|---:|---|---:|---:|---:|---:|
| 2 | 2000 | actual-train | 4 | -0.001 | 0 | 64.500 |
| 2 | 2000 | inner | 3 | -0.001 | 0 | 25.333 |
| 2 | 4000 | actual-train | 4 | -0.033 | 0 | 558.750 |
| 2 | 4000 | inner | 3 | -0.045 | 0 | 178.333 |
| 2 | 6000 | actual-train | 4 | -0.068 | 0 | 642.000 |
| 2 | 6000 | inner | 3 | -0.043 | 0 | 55.667 |
| 3 | 2000 | actual-train | 4 | -0.007 | 0 | 73.250 |
| 3 | 2000 | inner | 3 | -0.008 | 0 | 64.333 |
| 3 | 4000 | actual-train | 4 | -0.106 | 0 | 492.500 |
| 3 | 4000 | inner | 3 | -0.109 | 0 | 371.667 |
| 3 | 6000 | actual-train | 4 | 0.000 | 0 | 0.000 |
| 3 | 6000 | inner | 3 | 0.000 | 0 | 0.000 |

Extent/wall disabling did not rescue fold3 step6000 empty no-T2 predictions and often reduced Dice in fold2. `EXTENT_WALL_NEGATIVE_BIAS_CAUSAL_SIGNAL` is weak or ruled out as the primary cause for the fold3 collapse.

## Sampler Effective Supervision

| fold | steps | partial scar events | bad fallback rate | unexpected random rate | candidate coord mean | gap flag |
|---:|---|---:|---:|---:|---:|---|
| 2 | (2000,4000] | 1000 | 0.000 | 0.000 | 1325.518 | False |
| 2 | (4000,6000] | 1000 | 0.000 | 0.000 | 1312.638 | False |
| 2 | (6000,7000] | 500 | 0.000 | 0.000 | 1254.352 | False |
| 3 | (2000,4000] | 1000 | 0.000 | 0.000 | 1270.706 | False |
| 3 | (4000,6000] | 1000 | 0.000 | 0.000 | 1252.818 | False |
| 3 | (6000,7000] | 122 | 0.000 | 0.000 | 1235.098 | False |

Sampler logs do not support “partial 没采到”：fold2/fold3 Stage B windows都有大量 partial scar events，bad fallback rate 为 0，unexpected random rate 为 0。

## Parameter Drift

| fold | step | upper encoder drift | shared decoder drift | anatomy decoder drift | scar classifier drift |
|---:|---:|---:|---:|---:|---:|
| 2 | 2000 | 0.000 | 0.000 | 0.000 | 0.256 |
| 2 | 4000 | 0.284 | 0.346 | 0.134 | 0.378 |
| 2 | 6000 | 0.442 | 0.471 | 0.179 | 0.474 |
| 3 | 2000 | 0.000 | 0.000 | 0.000 | 0.192 |
| 3 | 4000 | 0.267 | 0.343 | 0.138 | 0.295 |
| 3 | 6000 | 0.343 | 0.449 | 0.207 | 0.399 |

Shared low-mid decoder and upper encoder begin drifting exactly after Stage B unfreeze. The drift is present in both folds, but fold3 develops much stronger final myocardium dominance on no-T2 scar voxels.

## Causal Diagnosis

- PRIMARY_CAUSE: `FINAL_CLASS_COMPETITION_COLLAPSE_WITH_SHARED_REPRESENTATION_DRIFT`.
- SECONDARY_CAUSE: `PARTIAL_MODALITY_TRAINING_DYNAMICS_COLLAPSE`, because fold3 selected actual-train partial cases also collapse at step6000.
- RULED_OUT_OR_WEAK_CAUSES: `SAMPLER_EFFECTIVE_SUPERVISION_GAP` weak; `EXTENT_WALL_NEGATIVE_BIAS_CAUSAL_SIGNAL` weak; static/GPU runtime audit found no no-T2 decode/availability semantic bug.
- UNRESOLVED: why fold3 shared/anatomy competition is much more destructive than fold2 despite similar sampler and drift direction; full actual-train population inference remains intentionally sampled, not exhaustive.

## Runtime And Job Evidence

- diagnostic Slurm status: `63560023:a100-gpu:COMPLETED:0:0:00:02:15;63587878:a100-gpu:COMPLETED:0:0:00:02:57`
- completed GPU diagnostic dirs: `gpu_readonly_63560023, gpu_readonly_63587878_step4000`
- `outer_accessed`: false for these scripts.
- `training_mutated`: false.
- current conclusion: continue formal training; no implementation blocker candidate from this diagnostic pass.

## Required Machine Labels

- `CORE_6_CASE_INNER_TREND_PANEL`: temporal trend / anomaly only, not superiority evidence.
- `FORMAL_35_CASE_INNER`: primary inner subgroup trend source.
- `ACTUAL_TRAIN_DIAGNOSTIC`: GPU selected-case causal discriminator.
- `HELD_OUT_OUTER_ALREADY_ACCESSED_DIAGNOSTIC`: not read or updated by this diagnostic branch.
