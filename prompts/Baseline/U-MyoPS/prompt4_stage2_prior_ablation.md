# U-MyoPS round4 prompt: Stage2 input/prior ablation after perfect label oracle

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续改进 U-MyoPS。本轮只验证一个主要假设：

> Stage2 label/remap/geometry 已被 oracle 排除；ScarCE2 训练只小幅改善 scar。当前瓶颈更可能是 Stage1 prior / aligned C0-T2-LGE input channels 没有给 Stage2 提供稳定 pathology localization，尤其在完整三序列 Case20xx/30xx 上失败。

## 必须先读

- `docs/notes/U-MyoPS_improvement_round3.md`
- `results/experiments/U-MyoPS_iteration_log.md`
- `results/metrics/unified/U-MyoPS_stage2_oracle/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0/grouped_diagnostics.md`
- `logs/U-MyoPS_ExportEval_51264404_20260517_060141.log`
- `results/metrics/nnUNet.md`

## 当前事实

| result | myops_edema | myops_scar |
| --- | ---: | ---: |
| old PSNV8 final all-cases | 0.6507 | 0.2823 |
| round3 ScarCE2 final all-cases | 0.6338 | **0.2932** |
| round3 ScarCE2 scar-positive-only | 0.6253 | 0.3000 |
| round3 ScarCE2 complete-modalities | 0.0554 | 0.0767 |
| Stage2 label oracle | 1.0000 | 1.0000 |
| nnU-Net Dataset501 5-fold | 0.4197 | 0.5592 |

Interpretation:

- Label construction/remap/slice order/geometry are correct.
- More scar CE weight is not the answer.
- Complete three-sequence cases are still failing, so the paper's intended full U-MyoPS path is not working.

## Round4 目标

Run input/prior diagnostics and one controlled Stage2 ablation. Do not run Stage1 full retraining or folds 1-4.

## Required diagnostics

Create or extend a report script, for example:

- `scripts/evaluation/report_umyops_stage2_input_qc.py`

For fold0 val cases, especially lowest scar cases, report per channel:

- nonzero voxel count;
- intensity min/mean/max/std inside myocardium/prior support;
- aligned C0/T2/LGE geometry;
- prior support Dice vs GT myocardium/anatomy where available;
- pathology overlap with prior;
- per-case predicted scar voxel count vs GT scar voxel count.

Focus cases:

- `Case2002`, `Case2007`, `Case2020`, `Case2031`, `Case2033`
- `Case3004`, `Case3012`, `Case3040`, `Case3044`
- `Case7005`, `Case8021` as missing-modality controls

## Controlled Stage2 ablation

Build isolated Stage2 fold0 tasks or input variants with identical labels/splits:

1. `existing_full`
   - current Stage1-derived channels.
2. `lge_only_no_prior`
   - keep LGE channel; zero or drop aligned C0/T2/prior channels.
3. `oracle_prior_diagnostic`
   - replace Stage1 prior with a GT-derived myocardium/support prior for train/val only as a diagnostic upper-bound. This is not submission-legal; mark clearly.

If task creation is too expensive, implement a dataloader/channel-masking trainer switch instead, but prediction/metric directories must be isolated by variant.

Run at most one <=8h fold0 training job first. Recommended first training variant:

- `lge_only_no_prior`
- trainer derived from current PSNV8 or a simple nnU-Net v1 2D trainer already available in U-MyoPS stack
- same labels/splits
- checkpoint/metrics under:
  - `results/predictions/U-MyoPS_round4_lge_only_no_prior/fold_0`
  - `results/metrics/unified/U-MyoPS_round4_lge_only_no_prior/fold_0`

Only run `oracle_prior_diagnostic` training if the setup is already implemented and remains within budget; otherwise produce the task/QC artifacts and leave it as next-step.

## Required interpretation

Compare:

- old PSNV8 final;
- ScarCE2 final;
- round4 ablation variant;
- Stage2 oracle.

Decision rules:

- If `lge_only_no_prior` beats ScarCE2 on complete-modality scar, existing Stage1 prior/aligned C0/T2 channels are harming Stage2.
- If `lge_only_no_prior` is also poor, failure is likely PSNV8 trainer/architecture or class imbalance rather than prior alone.
- If oracle prior diagnostic is much better, Stage1 prior quality is the bottleneck.
- If no variant approaches nnU-Net, U-MyoPS should not be expanded to 5 folds.

## Deliverables

- Code changes.
- New report: `docs/notes/U-MyoPS_improvement_round4.md`.
- Append `results/experiments/U-MyoPS_iteration_log.md`.
- Input QC:
  - `results/metrics/unified/U-MyoPS_stage2_input_qc/fold_0/*.csv`
  - `results/metrics/unified/U-MyoPS_stage2_input_qc/fold_0/*.md`
- Ablation metrics:
  - `results/metrics/unified/U-MyoPS_round4_<variant>/fold_0/evaluation_summary.json`
  - grouped diagnostics for all-cases, scar-positive-only, complete-modality, edema GT-positive/T2-present.

Final report must answer whether the next move is Stage1 prior repair, Stage2 input simplification, architecture replacement, or stopping U-MyoPS as noncompetitive.
