# U-MyoPS 改进 round3：ScarCE2 export/eval 与 Stage2 label oracle

日期：2026-05-17

## 约束

- 本轮不继续训练，不提交更长 Stage2 job。
- 只验证一个主要假设：round2 `nnUNetTrainerPSNV8ScarCE2` 是否尚未被正确导出，以及 Stage2 internal metric 是否和 CARE unified metric 口径不一致。
- 只处理 fold0，不扩展 fold1-4。

## 代码改动

- `jobs/U-MyoPS/sbatch_export_eval_fold0.sh`
  - 新增 `UMYOPS_EXPORT_TRAINER`，默认从 `UMYOPS_STAGE2_TRAINER` 或 `nnUNetTrainerPSNV8` 解析。
  - prediction / metric tag 改为包含 trainer 和 checkpoint：
    - `results/predictions/U-MyoPS_<trainer>_<checkpoint>/fold_0`
    - `results/metrics/unified/U-MyoPS_<trainer>_<checkpoint>/fold_0`
  - 默认 `UMYOPS_EXPORT_FORCE_FALLBACK=1`，并显式传 `--trainer`、`--checkpoint`、`--force-fallback`。
  - export 后自动运行 grouped diagnostics 和 fold aggregate。
- `code/U-MyoPS/export_stage2_val_predictions.py`
  - fallback tmp cache root 加入 trainer tag，避免 `nnUNetTrainerPSNV8` 与 `nnUNetTrainerPSNV8ScarCE2` 共享 raw prediction cache。
- `scripts/evaluation/report_umyops_stage2_oracle.py`
  - 新增 Task901 label oracle：Stage2 `1->4 edema`, `2->5 scar`，直接对 Dataset501 fold0 GT 计算 Dice 和 voxel counts。
- `scripts/evaluation/report_umyops_round2.py`
  - geometry check 使用 `atol=1e-5`，避免方向矩阵浮点尾差误报。
- `third_party/U-MyoPS_myops/jrs/nnunet/training/network_training/nnUNetTrainerPSNV8.py`
  - 为后续训练加了 initial best checkpoint fallback：如果第一次验证后没有 `model_best.model`，保存当前模型为初始 best，避免下一轮无法导出 best。

## Stage2 label oracle

产物：

- `results/metrics/unified/U-MyoPS_stage2_oracle/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_stage2_oracle/fold_0/grouped_metrics.json`
- `results/metrics/unified/U-MyoPS_stage2_oracle/fold_0/per_case_counts.csv`

结果：

| group | n | myops_edema | myops_scar |
| --- | ---: | ---: | ---: |
| all_cases | 44 | 1.0000 | 1.0000 |
| edema_gt_positive_only | 16 | 1.0000 | 1.0000 |
| edema_t2_present_only | 16 | 1.0000 | 1.0000 |
| scar_gt_positive_only | 43 | 1.0000 | 1.0000 |
| scar_complete_modalities_only | 16 | 1.0000 | 1.0000 |

Geometry mismatches: none.

结论：Task901 validation labels 与 Dataset501 fold0 GT 在 label remap、slice order 和 geometry 上是正确的。Stage2 task label construction 不是当前 scar 低分主因。

## ScarCE2 unified export/eval

运行命令：

```bash
sbatch --parsable --export=ALL,UMYOPS_EXPORT_TRAINER=nnUNetTrainerPSNV8ScarCE2,UMYOPS_EXPORT_CHECKPOINT=model_final_checkpoint,UMYOPS_STAGE2_WHICH_SUBNET=scar,UMYOPS_EXPORT_FORCE_FALLBACK=1 jobs/U-MyoPS/sbatch_export_eval_fold0.sh
```

- Job: `51264404`
- Log: `logs/U-MyoPS_ExportEval_51264404_20260517_060141.log`
- Trainer: `nnUNetTrainerPSNV8ScarCE2`
- Checkpoint: `model_final_checkpoint`
- Cache: `results/predictions/_tmp/U-MyoPS/fold_0_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/validation_raw`
- Output predictions: `results/predictions/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0`
- Unified metrics: `results/metrics/unified/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0/evaluation_summary.json`

结果：

| checkpoint/trainer | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| old PSNV8 final | all_cases | 44 | 0.6507 | 0.2823 |
| old PSNV8 final | scar_gt_positive_only | 43 | 0.6425 | 0.2888 |
| old PSNV8 final | scar_complete_modalities_only | 16 | 0.0393 | 0.0781 |
| ScarCE2 final | all_cases | 44 | 0.6338 | 0.2932 |
| ScarCE2 final | scar_gt_positive_only | 43 | 0.6253 | 0.3000 |
| ScarCE2 final | scar_complete_modalities_only | 16 | 0.0554 | 0.0767 |

Interpretation:

- ScarCE2 all-cases scar 从 `0.2823` 到 `0.2932`，只有很小提升。
- scar-positive-only 从 `0.2888` 到 `0.3000`，也只是轻微提升。
- 完整三序列 scar 从 `0.0781` 到 `0.0767`，没有改善。
- GT-positive/T2-present edema 从 `0.0393` 到 `0.0554`，略有提升，但仍远低于 nnU-Net fold0 edema `0.3944` 和 5-fold mean `0.4197`。

## Internal metric 与 unified metric 差异

round2 训练日志中的 internal Stage2 online scar/class_2 多数在 `0.58-0.61`，但 CARE unified scar 只有 `0.2932`，完整三序列 scar 只有 `0.0767`。

原因判断：

- 不是 label oracle 问题：Task901 label oracle 为 1.0。
- 不是 naive export 用旧 trainer：round3 已确认使用 ScarCE2 trainer 和隔离 cache。
- internal metric 是 nnU-Net 训练期在线估计，按 batch/global foreground 统计，且在 preprocessed/internal label space 下运行；它不是 checkpoint-specific、case-wise、CARE compact label 的统一评估。
- 关键低分病例仍是 Case20xx/30xx 完整三序列病例，说明模型在 full U-MyoPS path 上仍没有学到可泛化 scar localization。

## Best checkpoint 行为

ScarCE2 本次目录没有新的 `model_best.model`：

`third_party/U-MyoPS_myops/outputs/nnunet/output/nnUNet/2d/Task901_CARE_UmyopsPathology_fold0/nnUNetTrainerPSNV8ScarCE2__nnUNetPlansv2.1/fold_0/`

只看到：

- `model_final_checkpoint.model`
- `model_final_checkpoint.model.pkl`
- training logs / debug metadata

原因：当前 nnU-Net `NetworkTrainer.manage_patience()` 在首次初始化 `best_val_eval_criterion_MA` 时不会立即保存 `model_best.model`，只有 moving-average validation criterion 后续超过初始 best 才保存。本次 run 没触发该保存路径。

已修复后续行为：`nnUNetTrainerPSNV8.on_epoch_end()` 会在首次验证后若没有 `model_best.model` 则保存 initial best fallback。当前 run 已结束，因此不把 final 伪装成 best；本轮只导出 final。

## 结论

round2 不是单纯“还没正确导出”。正确导出 ScarCE2 后，all-cases scar 只有轻微提升，完整三序列 scar 未改善。Stage2 label oracle 完全正确，因此当前瓶颈不是 Task901 label remap / slice order / geometry。

下一步不应继续加 CE weight 或盲目训练更久。应转向：

1. Stage1 prior / aligned feature 有效性修复：重点 Case20xx/Case30xx，尤其 prior 与 pathology overlap 很低的病例。
2. Stage2 输入语义修复：当前 prior/C0/T2/LGE channels 可能没有给 pathology head 提供稳定定位信息，需要做 ablation/oracle prior 或用 Dataset501 GT myocardium/pathology support 构造 controlled prior 对照。
3. 缺模态 routing 仍要保留，但完整三序列病例失败更优先。

暂不启动 fold1-4。
