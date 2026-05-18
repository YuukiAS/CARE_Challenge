# U-MyoPS round6 prompt: missing-modality scar calibration to cross nnU-Net

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 U-MyoPS。本轮目标是让 U-MyoPS 在 MyoPS scar 上超过 nnU-Net；不要声称它解决 edema，除非 T2-present/GT-positive edema 也真实改善。

本轮不要先训练长任务。round5 已确认 `model_best` 略优于 final，但 all-case scar 仍低于 nnU-Net；下一步应集中修复缺 T2 / LGE-only 病例的 scar 短板。

定位说明：当前最强 route 是 `LGE-only/no-prior`，它是 CARE-driven ablation / scar-specialist 路线，不是 U-MyoPS 论文中“Stage1 alignment prior + aligned multi-sequence inputs”的完整复现。任何使用 nnU-Net fallback 或删除 Stage1 prior 的结果都必须如实标注为 diagnostic/specialist/hybrid，不能写成 paper-faithful U-MyoPS final model。

## 必须先读

- `docs/notes/U-MyoPS_improvement_round4.md`
- `results/experiments/U-MyoPS_iteration_log.md`
- `prompts/U-MyoPS/prompt5_best_checkpoint_and_scar_specialist.md`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/grouped_diagnostics.md`
- `logs/U-MyoPS_r5_export_51354910_20260517_233346.log`
- `prompts/Baseline_report.md`
- `results/metrics/nnUNet.md`

## 当前事实

nnU-Net MyoPS reference:

| metric | nnU-Net 5-fold mean |
| --- | ---: |
| myops_edema / class_4 | 0.4197 |
| myops_scar / class_5 | 0.5592 |

U-MyoPS round5:

| checkpoint | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| final | all_cases | 44 | 0.6726 | 0.5248 |
| final | complete/T2-present | 16 | 0.1622 | 0.6524 |
| best | all_cases | 44 | 0.6518 | 0.5307 |
| best | scar_gt_positive_only | 43 | 0.6437 | 0.5430 |
| best | complete/T2-present | 16 | 0.1675 | 0.6463 |

Lowest scar cases for `model_best` are mostly missing-modality cases:

- `Case8021`, `Case7005`, `Case1029`, `Case1045`, `Case8011`, `Case5005`
- complete-modality scar is already strong; all-case gap is driven by LGE-only / missing-T2 behavior.

## Round6 目标

1. Analyze per-case U-MyoPS best vs nnU-Net501 fold0 predictions for scar on the same fold0 cases.
2. Identify whether U-MyoPS is worse due to over-segmentation, under-segmentation, or false positives on missing-modality cases.
3. Build one or more export-only scar calibration/routing variants:
   - class_5 component filtering;
   - class_5 volume-ratio constraints for missing-modality cases;
   - U-MyoPS for complete cases + fallback for missing-modality cases if nnU-Net/MyoPS-Net is better there;
   - optional softmax threshold sweep if U-MyoPS raw softmax can be exported.
4. Evaluate all-cases, scar-positive-only, complete-modality, and missing-modality subsets.

## 建议实现

Create a short diagnostic/calibration script, for example:

- `scripts/evaluation/compare_umyops_nnunet_scar_cases.py`
- `code/U-MyoPS/apply_round6_scar_calibration.py`
- `jobs/U-MyoPS/sbatch_round6_scar_calibration.sh`

Inputs:

- U-MyoPS best predictions: `results/predictions/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0`
- nnU-Net501 predictions: `results/predictions/nnUNet501/fold_0`
- GT: `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr`
- fold split: `data/benchmarks/protocol/splits_MyoPS.json`
- modality metadata: use existing staged metadata / `modalities_present.json`

Candidate output dirs:

- `results/predictions/U-MyoPS_round6_scar_component_filter/fold_0`
- `results/metrics/unified/U-MyoPS_round6_scar_component_filter/fold_0`
- `results/predictions/U-MyoPS_round6_complete_umyops_missing_nnunet/fold_0`
- `results/metrics/unified/U-MyoPS_round6_complete_umyops_missing_nnunet/fold_0`

If using nnU-Net fallback, label it clearly as a hybrid diagnostic, not pure U-MyoPS.

Paper-aligned follow-up guard:

- If pure U-MyoPS LGE-only calibration cannot cross nnU-Net, recommend either hybrid packaging for CARE or a separate paper-faithful Stage1 repair round.
- A paper-faithful repair round should focus on why the original prior hurt scar: prior quality, mask-aware missing modality, skip-bad-prior gating, and aligned C0/T2 reliability. Do not simply re-enable Stage1 prior by default.

## 结果判定

- Pure U-MyoPS success: all-case `myops_scar > 0.5592` without using nnU-Net predictions.
- Hybrid diagnostic success: complete cases use U-MyoPS and missing-modality cases use a better fallback, with all-case scar > `0.5592`; this can inform validation packaging but is not a pure U-MyoPS win.
- If only complete-modality cases remain strong but missing cases stay poor, U-MyoPS should be treated as official-validation-like complete-case scar specialist only.
- Edema must be reported on T2-present/GT-positive cases; do not use all-case empty-GT inflation as evidence.

## 禁止事项

- 不要重新启用 Stage1 prior/C0/T2 as default for scar; round4 showed it hurts.
- 不要启动长训或 folds 1-4 before export-only calibration is exhausted.
- 不要把 nnU-Net fallback result 写成 U-MyoPS pure result.
- 不要把 LGE-only/no-prior route 写成 U-MyoPS 论文完整思想；它是 CARE adaptation / scar specialist.
- 不要牺牲 complete-case scar below `0.62` unless all-case scar crosses nnU-Net and the tradeoff is documented.

## 交付物

- 新报告：`docs/notes/U-MyoPS_improvement_round6.md`
- 追加：`results/experiments/U-MyoPS_iteration_log.md`
- Per-case comparison CSV/MD
- 每个 variant 的 `evaluation_summary.json` 和 grouped diagnostics
- 如新增脚本：更新 `jobs/U-MyoPS/README.md`

最终报告必须明确回答：U-MyoPS 是否能作为纯 scar 模型超过 nnU-Net；如果不能，是否只有 hybrid routing 或 official-validation complete-case route 值得继续。
