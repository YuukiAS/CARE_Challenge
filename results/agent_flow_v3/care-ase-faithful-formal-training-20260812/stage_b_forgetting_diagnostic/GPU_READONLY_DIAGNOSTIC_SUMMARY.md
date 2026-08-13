# GPU Read-Only Stage-B Forgetting Diagnostic Summary

这次 GPU 只读诊断没有发现训练进程或 checkpoint 需要中断的实现性硬错误。小样本 full-volume 证据显示，fold3 step6000 的 no-T2 scar collapse 同时出现在 inner partial 和 actual-train partial，因此它不是单纯 held-out 泛化问题；最强信号是 GT scar 上 final scar-vs-myocardium margin 被 myocardium logit 大幅压成负值，关闭 global extent/wall 没有救回空预测。当前结论仍然支持继续 frozen 14000-step formal training，同时把 partial/no-T2 scar forgetting 记录为训练动力学/最终类别竞争诊断问题。

## Job Accounting

- job_id: `63560023`
- job_name: `ASEdiagB`
- partition: `a100-gpu`
- node: `g141601`
- state: `COMPLETED`
- exit_code: `0:0`
- elapsed: `00:02:15`
- log: `stage_b_forgetting_diagnostic/gpu_readonly_63560023/logs/ASEdiagB_63560023_20260813T161652Z.log`
- outer_accessed: `false`
- training_mutated: `false`
- device: `NVIDIA A100-PCIE-40GB`

## Sample Scope

This is a targeted diagnostic sample, not a replacement for complete formal-inner evaluation.

- folds: `2`, `3`
- steps: `2000`, `6000`
- selected cases per fold: `7`
- per fold sample: 3 inner partial no-T2, 3 actual-train partial no-T2, 1 actual-train complete control
- evidence one-source-off: one inner partial no-T2 case per fold

## Actual-Train vs Inner Partial

| fold | step | population | n | mean scar Dice | mean sensitivity | empty |
|---:|---:|---|---:|---:|---:|---:|
| 2 | 2000 | inner partial | 3 | 0.8303 | 0.7860 | 0/3 |
| 2 | 2000 | actual-train partial | 3 | 0.8958 | 0.8539 | 0/3 |
| 2 | 6000 | inner partial | 3 | 0.3123 | 0.1941 | 0/3 |
| 2 | 6000 | actual-train partial | 3 | 0.6839 | 0.5685 | 0/3 |
| 3 | 2000 | inner partial | 3 | 0.8487 | 0.7862 | 0/3 |
| 3 | 2000 | actual-train partial | 3 | 0.9060 | 0.8597 | 0/3 |
| 3 | 6000 | inner partial | 3 | 0.0000 | 0.0000 | 3/3 |
| 3 | 6000 | actual-train partial | 3 | 0.0000 | 0.0000 | 3/3 |

Interpretation: fold3 follows Pattern 1 from the diagnostic contract: actual-train partial also collapses, supporting `TRAINING_DYNAMICS_OR_OBJECTIVE_COLLAPSE` over a pure held-out generalization failure. Fold2 also degrades but is not fully empty in the sampled cases.

## GT Scar Margin

Mean `z_scar - anatomy_class1_logit` on GT scar voxels:

| fold | step | role | mean margin | frac > 0 | mean z_scar | mean anatomy class1 |
|---:|---:|---|---:|---:|---:|---:|
| 2 | 2000 | inner | 3.6260 | 0.8359 | 4.3981 | 1.0098 |
| 2 | 6000 | inner | -4.3884 | 0.2086 | 3.2528 | 7.9261 |
| 2 | 2000 | actual-train | 6.2800 | 0.9327 | 6.0371 | 0.0540 |
| 2 | 6000 | actual-train | 1.5857 | 0.6742 | 6.2475 | 5.3792 |
| 3 | 2000 | inner | 4.4318 | 0.8986 | 4.7773 | 0.6324 |
| 3 | 6000 | inner | -24.5604 | 0.0000 | 2.3915 | 27.6638 |
| 3 | 2000 | actual-train | 8.0640 | 0.9460 | 6.8464 | -0.9045 |
| 3 | 6000 | actual-train | -16.0812 | 0.2312 | 5.7719 | 22.6634 |

Interpretation: the dominant observed change is final myocardium competition. Scar logit is not universally absent, especially in fold3 actual-train, but anatomy class1 rises enough to dominate the final argmax. This supports `FINAL_COMPETITION_MYOCARDIUM_DOMINANCE_SIGNAL`, with some additional fold3 inner scar-logit weakening.

## Extent/Wall Intervention

Disabling global extent/wall did not rescue the fold3 step6000 empty cases.

- fold3 step6000 inner: mean Dice delta `0.0000`, rescued empty `0/3`, changed voxels mean `0.0`
- fold3 step6000 actual-train: mean Dice delta `0.0000`, rescued empty `0/4`, changed voxels mean `0.0`
- fold2 step6000 inner: mean Dice delta `-0.0430`, rescued empty `0/3`
- fold2 step6000 actual-train: mean Dice delta `-0.0683`, rescued empty `0/4`

Interpretation: `EXTENT_WALL_NEGATIVE_BIAS_CAUSAL_SIGNAL` is not supported as the primary cause in this sample.

## Evidence Intervention

At fold3 step6000, one-source-off changes do not alter Dice because the selected no-T2 case is already empty under normal inference. This means the evidence intervention cannot yet localize which source failed after collapse. At fold2 step6000, disabling soft-wall geometry, LGE adapter, occupancy, and center generally harms scar Dice, indicating those sources still contribute in the less-collapsed fold.

## Causal Diagnosis Update

- PRIMARY_CAUSE: `FINAL_COMPETITION_MYOCARDIUM_DOMINANCE_SIGNAL`
- SECONDARY_CAUSE: `STAGE_B_SHARED_REPRESENTATION_OR_CLASS_COMPETITION_DRIFT`
- RULED_OUT_OR_WEAK_CAUSES: `EXTENT_WALL_NEGATIVE_BIAS_CAUSAL_SIGNAL`, `SAMPLER_EFFECTIVE_SUPERVISION_GAP`, pure held-out-only generalization failure
- UNRESOLVED: exact upstream level that drives myocardium dominance; broader all-case actual-train diagnostic remains incomplete

## Training Decision

No implementation blocker candidate was found in this GPU diagnostic. Continue formal fold2/fold3 training to the frozen 14000-step schedule. Do not stop, rollback, select checkpoint, or tune threshold/loss/sampler from this diagnostic.
