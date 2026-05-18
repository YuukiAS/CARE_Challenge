# U-MyoPS round3 prompt: close ScarCE2 export/eval and verify Stage2 label semantics

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续改进 U-MyoPS，但本轮不要先训练更久。本轮只验证一个主要假设：

> round2 的 `nnUNetTrainerPSNV8ScarCE2` 训练完成后还没有被正确导出和统一评估；同时 Stage2 internal metric 与 CARE unified metric 口径可能不一致。继续训练前必须先校准 trainer/checkpoint/export/cache 和 Stage2 label oracle。

## 必须先读

- `docs/notes/U-MyoPS_improvement_round2.md`
- `results/experiments/U-MyoPS_iteration_log.md`
- `results/metrics/unified/U-MyoPS_model_best/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/grouped_diagnostics.md`
- `prompts/U-MyoPS/prompt2_improve_umyops.md`
- `prompts/U-MyoPS/U-MyoPS_myops_scar_diagnosis.md`
- `prompts/Baseline_report.md`
- `results/metrics/nnUNet.md`

## 当前事实

nnU-Net MyoPS 5-fold reference:

| metric | nnU-Net |
| --- | ---: |
| `myops_scar` / class_5 | 0.5592 |
| `myops_edema` / class_4 | 0.4197 |

U-MyoPS explicit old checkpoints:

| checkpoint | group | myops_edema | myops_scar |
| --- | --- | ---: | ---: |
| `model_final_checkpoint` | all cases | 0.6507 | 0.2823 |
| `model_final_checkpoint` | edema GT-positive/T2-present | 0.0393 | 0.0781 |
| `model_final_checkpoint` | complete modalities | 0.0393 | 0.0781 |
| `model_best` | all cases | 0.6517 | 0.2800 |
| `model_best` | edema GT-positive/T2-present | 0.0421 | 0.0782 |
| `model_best` | complete modalities | 0.0421 | 0.0782 |

round2 `nnUNetTrainerPSNV8ScarCE2`:

- job `51256750`
- log `logs/U-MyoPS_Stage2_51256750_20260517_042736.log`
- ran 80 epochs, no patience early stop
- internal Stage2 scar/class_2 metric mostly 0.58-0.61
- new final checkpoint:
  `third_party/U-MyoPS_myops/outputs/nnunet/output/nnUNet/2d/Task901_CARE_UmyopsPathology_fold0/nnUNetTrainerPSNV8ScarCE2__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model`
- no new 2026-05-17 `model_best.model` found in ScarCE2 fold dir
- no unified `results/metrics/unified/*ScarCE2*` result exists yet

Important bug/risk: `jobs/U-MyoPS/sbatch_export_eval_fold0.sh` currently calls `export_stage2_val_predictions.py` without `--trainer`, and the export script defaults to `nnUNetTrainerPSNV8`. So a naive export can silently evaluate the old trainer instead of ScarCE2.

## Round3 目标

先闭合评估，不要盲目训练：

1. 修复 export entrypoint so trainer, checkpoint, output tag, and cache root are explicit.
2. 导出并评估 `nnUNetTrainerPSNV8ScarCE2` 的 `model_final_checkpoint`。
3. 做 Stage2 label oracle：直接把 Task901 validation labels remap `1->4`, `2->5`，和 Dataset501 fold0 GT 比较。
4. 校准 Stage2 internal online metric 与 CARE unified metric 的差异来源。
5. 修复 best checkpoint 保存/可导出问题，避免下一轮无法选 best。

## 必须实现或检查

### 1. Export trainer/checkpoint isolation

更新以下文件之一或多个：

- `jobs/U-MyoPS/sbatch_export_eval_fold0.sh`
- `code/U-MyoPS/export_stage2_val_predictions.py`
- 必要时新增一个 round3 专用 Slurm entrypoint

要求：

- 支持 `UMYOPS_EXPORT_TRAINER=nnUNetTrainerPSNV8ScarCE2`，并传给 `--trainer`。
- metric/prediction dir tag 必须包含 trainer 和 checkpoint，例如：
  - `results/predictions/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0`
  - `results/metrics/unified/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0`
- fallback tmp cache root 也必须包含 trainer，避免和旧 `nnUNetTrainerPSNV8` 复用同一个 raw prediction cache。
- 默认 `UMYOPS_EXPORT_FORCE_FALLBACK=1`，本轮不要复用 stale `validation_raw`。

### 2. Stage2 label oracle

新增或扩展一个脚本，建议：

- `scripts/evaluation/report_umyops_stage2_oracle.py`

它应读取 Task901 fold0 validation labels，并做：

- Stage2 label `1 -> CARE compact 4` edema
- Stage2 label `2 -> CARE compact 5` scar
- 与 `nnUNet_raw/Dataset501_CAREMyoPS/labelsTr` 中同 case 的 fold0 GT 比较 Dice
- 输出 all cases、GT-positive-only、T2-present-only、complete-modality-only
- 输出 per-case label voxel counts 和 geometry check

如果 oracle `myops_scar` / `myops_edema` 本身很低，说明 Task901 构造、slice order、geometry 或 label remap 有问题，不能继续训练。

### 3. Best checkpoint behavior

检查为什么 ScarCE2 目录没有新 `model_best.model`：

- 是 nnU-Net 没有保存 best？
- 是 continued training 继承了旧 best 状态？
- 是 output dir 被覆盖/没有写权限？

修复后至少要在报告中说明下一轮如何可靠导出 best。不要把 final 误当 best。

## 本轮运行

本轮可以先跑 export/eval + oracle，不需要 8 小时训练。若需要 Slurm，walltime <= 4h 即可。

建议命令形态：

```bash
sbatch --export=ALL,UMYOPS_EXPORT_TRAINER=nnUNetTrainerPSNV8ScarCE2,UMYOPS_EXPORT_CHECKPOINT=model_final_checkpoint,UMYOPS_STAGE2_WHICH_SUBNET=scar,UMYOPS_EXPORT_FORCE_FALLBACK=1 jobs/U-MyoPS/sbatch_export_eval_fold0.sh
```

如果你修了 entrypoint，使用修复后的命令，并在报告里记录完整 command/env。

## 结果判定

先比较三层结果：

1. Stage2 label oracle vs Dataset501 GT
2. ScarCE2 model_final_checkpoint unified prediction vs Dataset501 GT
3. old PSNV8 model_final_checkpoint unified prediction vs Dataset501 GT

解释规则：

- oracle 高、ScarCE2 低：训练/推理/whichsubnet/checkpoint 问题。
- oracle 低、ScarCE2 低：Stage2 task construction、geometry、label remap 或 Stage1 aggregation 问题。
- ScarCE2 高于 old PSNV8：round2 的 scar CE/sampling 有效，下一轮可以训练更稳或跑 folds。
- ScarCE2 不高于 old PSNV8：不要继续加 CE weight；转向 task construction / prior / label semantics。

成功阈值：

- minimum: ScarCE2 unified result真实生成，prediction非空，且没有复用旧 trainer/cache。
- useful: complete-modality scar 明显超过旧 checkpoint 的约 0.078。
- continue training: all-cases scar 超过 0.30 或 GT-positive/complete-modality scar 大幅提升。
- expand folds: 只有 fold0 scar 接近或超过 nnU-Net fold0/5-fold 参考时再考虑。

## 禁止事项

- 不要在 export/eval 未闭合前继续提交 Stage2 长训。
- 不要把 old `results/metrics/unified/U-MyoPS_model_final_checkpoint` 当成 ScarCE2 结果。
- 不要把 all-cases edema 0.65 当成真实 edema 成功；必须报告 GT-positive/T2-present。
- 不要把 edema 改成 union target。
- 不要复用 stale prediction cache。

## 交付物

- 代码改动。
- 新报告：`docs/notes/U-MyoPS_improvement_round3.md`
- 追加：`results/experiments/U-MyoPS_iteration_log.md`
- Oracle 报告，例如：
  - `results/metrics/unified/U-MyoPS_stage2_oracle/fold_0/grouped_diagnostics.md`
- ScarCE2 unified metrics，例如：
  - `results/metrics/unified/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0/evaluation_summary.json`
  - `results/metrics/unified/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0/grouped_diagnostics.md`

最终报告必须明确回答：round2 是训练本身没用，还是还没正确导出；U-MyoPS 继续投入的下一步应该是 task construction 修复、Stage1 prior 修复，还是 Stage2 loss/sampling。
