# U-MyoPS round7 prompt: paper-aligned Stage1 prior repair instead of more export calibration

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 U-MyoPS。本轮目标是回到更贴近 U-MyoPS 论文思想的方向：修复 Stage1 prior / aligned multi-sequence inputs 在 CARE 上伤害 scar 的问题，而不是继续做纯导出后处理。

本轮允许一个短 budget fold0 训练，但必须只测试一个主要假设：

> 原始 U-MyoPS Stage1 prior 不是完全无用，而是作为 hard/narrow prior 或与缺失 C0/T2 一起输入时过度约束 Stage2，导致 scar under-segmentation。一个 CARE-aware 的 soft/dilated prior + LGE Stage2 task 可能保留论文中的 prior-aware idea，同时避免原始 full-input route 的负迁移。

## 必须先读

- `docs/notes/U-MyoPS_improvement_round6.md`
- `results/experiments/U-MyoPS_iteration_log.md`
- `prompts/U-MyoPS/prompt6_missing_modality_scar_calibration.md`
- `results/diagnostics/U-MyoPS_round6/per_case_umyops_vs_nnunet_scar.md`
- `results/metrics/unified/U-MyoPS_round6_scar_component_filter_250/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/evaluation_summary.json`
- `third_party/U-MyoPS_myops/README.md`
- `README.md`
- `AGENTS.md`

## 当前事实

Reference and current U-MyoPS:

| model/variant | all-case scar | complete/T2-present scar | missing-modality scar |
| --- | ---: | ---: | ---: |
| nnU-Net501 fold0 | 0.5602 | 0.6933 | 0.4841 |
| nnU-Net501 5-fold mean | 0.5592 | - | - |
| U-MyoPS Task912 LGE-only/no-prior `model_best` | 0.5307 | 0.6463 | 0.4646 |
| best pure round6 calibration | 0.5352 | 0.6202 | - |
| best hybrid diagnostic | 0.5431 | 0.6463 | nnU-Net fallback |

Round6 conclusion:

- Pure U-MyoPS export calibration did not cross nnU-Net.
- Hybrid fallback also did not cross nnU-Net because complete cases also trail same-fold nnU-Net.
- Edema remains unsolved and should not be claimed from all-case empty-GT inflation.
- Continuing postprocessing is not justified.

Worst current failures include large under-segmentation cases such as `Case3038` and `Case5005`. This supports a model-level Stage2/prior repair rather than another component filter.

## Round7 目标

1. Build one CARE-aware prior Stage2 task that is closer to U-MyoPS paper than `LGE-only/no-prior`, but safer than `existing_full`.
2. Train fold0 only with <=8h budget and early stopping.
3. Export/evaluate with task-specific cache isolation.
4. Compare against:
   - Task912 LGE-only/no-prior `model_best`;
   - original full-input/ScarCE2 results;
   - nnU-Net fold0 and 5-fold references.

## 建议实现

### 1. New input variant

Extend `code/U-MyoPS/build_stage2_task_from_stage1.py` with one new `--input-variant`, for example:

- `lge_dilated_prior`

Expected channels:

| channel | content |
| --- | --- |
| 0 prior | Stage1 prior dilated/softened support mask, not GT oracle |
| 1 C0 | zero or omitted-equivalent placeholder |
| 2 T2 | zero or omitted-equivalent placeholder |
| 3 LGE | real LGE |

Rationale:

- Keeps the U-MyoPS prior-aware idea.
- Avoids reintroducing unreliable aligned C0/T2 for missing-modality CARE cases.
- Dilation/softening should reduce under-segmentation caused by overly narrow priors.

Do not use GT-derived oracle prior for training. Oracle prior can be reported only as a diagnostic upper bound.

### 2. New Task

Suggested task name:

- `Task914_CARE_UmyopsLGEDilatedPrior_fold0`

Prepare raw/preprocessed task via existing `prepare_stage2_task.sh` path if possible, with `UMYOPS_STAGE2_INPUT_VARIANT=lge_dilated_prior`.

### 3. Training budget

Use `nnUNetTrainerPSNV8ScarCE2` unless a concrete reason requires a new trainer.

Constraints:

- fold0 only;
- walltime <= 8h;
- `UMYOPS_STAGE2_EPOCHS <= 80`;
- runtime guard around 7.5h;
- patience around 20;
- early-stop metric scar;
- no folds 1-4.

### 4. Export/eval

Use task-specific output tags, for example:

- `results/predictions/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0`
- `results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0`

Grouped diagnostics must include:

- all cases;
- scar-positive-only;
- complete/T2-present;
- missing-modality;
- per-case failures for `Case3038`, `Case5005`, `Case3023`, `Case1021`.

## 结果判定

- Success: pure U-MyoPS all-case scar > `0.5592` without nnU-Net fallback.
- Partial success: scar improves over Task912 `0.5307` while preserving complete/T2-present scar >= `0.6463`; next round may tune prior dilation/gating.
- Failure: scar <= Task912 or complete-case under-segmentation worsens; stop U-MyoPS training and keep nnU-Net as MyoPS default.
- If prior helps only complete cases but hurts missing cases, next prompt should implement prior reliability gating, not fold expansion.

## 禁止事项

- 不要继续 round6 component/volume postprocessing.
- 不要把 hybrid fallback 写成 pure U-MyoPS.
- 不要使用 GT oracle prior for training.
- 不要重新启用 raw `existing_full` prior+C0+T2+LGE as the only experiment; round4 showed it hurts.
- 不要扩展 folds 1-4 unless fold0 pure U-MyoPS crosses nnU-Net.
- 不要声称 U-MyoPS solves edema unless T2-present/GT-positive edema improves substantially.

## 交付物

- Code/script changes.
- New report: `docs/notes/U-MyoPS_improvement_round7.md`.
- Append: `results/experiments/U-MyoPS_iteration_log.md`.
- Metric JSON and grouped diagnostics for the new task/checkpoint.
- If the task fails to build/train, report the blocker and do not substitute unrelated postprocessing.

最终报告必须明确回答：CARE-aware Stage1 prior repair 是否让 U-MyoPS 回到 paper-aligned 且超过 nnU-Net 的方向；如果不能，是否应该停止 U-MyoPS 主线投入。
