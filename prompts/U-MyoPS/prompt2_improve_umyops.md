# U-MyoPS 改进 Prompt：修复 Stage1/Stage2 scar 召回并重报 strict 指标

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中改进 U-MyoPS，使其在 CARE MyoPS 多模态任务上真正接近或超过 nnU-Net 本地 5-fold 基线：

| metric | nnU-Net 5-fold mean | 当前 U-MyoPS explicit checkpoint fold0 |
| --- | ---: | ---: |
| `myops_scar` / class_5 | 0.5592 | 约 0.2800-0.2823 |
| `myops_edema` / class_4 | 0.4197 | 约 0.6507-0.6517，但需 GT-positive-only 复核 |

## 背景

必须先阅读：

- `docs/literature/Ding 等 - 2023 - Aligning Multi-Sequence CMR Towards Fully Automated Myocardial Pathology Segmentation.pdf`
- `prompts/Baseline_report.md`
- `prompts/U-MyoPS/U-MyoPS_myops_scar_diagnosis.md`
- `prompts/U-MyoPS/improvement_suggestion.md`
- `results/metrics/nnUNet.md`
- `results/metrics/unified/U-MyoPS_model_best/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/evaluation_summary.json`
- `TODO.md`

论文要点：

- U-MyoPS 的核心不是普通多通道分割，而是 bSSFP/T2 到 LGE common space 的 TPS registration、MSF feature fusion、SPG myocardium prior。
- 论文假设 bSSFP/LGE/T2 完整；CARE 训练集中仅 80/220 三序列完整，其余大量缺 C0/T2。
- 论文中的 edema 解释可能包含 union 口径；CARE 主指标必须 strict `class_4=edema`。

当前实现状态：

- Stage1 已加入 `subject_meta.json`、有效 z-slice 采样、缺模态 manifest。
- Stage2 已构建 fold-specific nnU-Net v1 task，并 remap `1->4 edema`, `2->5 scar`。
- 显式 `model_best` / `model_final_checkpoint` 复评后 scar 仍只有约 0.28；说明当前瓶颈不是单纯旧 cache。
- Edema 平均值被大量 empty-GT case 拉高，必须重报 GT-positive-only。

## 任务目标

先解释并修复 scar 召回低的问题，再决定是否扩展 5 folds。不要在 Stage1/Stage2 链路未可信前换模型。

## 运行预算与迭代策略

本 prompt 是多轮改进任务，不允许一次性提交超长训练。每一轮必须遵守：

- 单个 Slurm 训练/评估 job walltime 目标不超过 **8 小时**；Stage1 与 Stage2 如果都要跑，必须拆成可单独判断的两个 job。
- 每轮只验证一个主要假设，例如 Stage1 prior 对齐、scar-positive sampling、scar class weight、缺模态 routing、checkpoint/export cache，不要一次混入多个无法归因的改动。
- 先做 fold0 小预算闭环；只有 fold0 scar 明显提升且 Stage1/Stage2 语义可信，才准备 fold1-4。
- 不要用 1000/2000 epoch 盲目长训补 scar；如果 8 小时内 scar recall 或 GT-positive Dice 没有改善，停止并做 per-case 失败分析。
- 如果 Stage2 trainer 还没有合适的 early stopping 或 checkpoint selection，本轮优先加上：
  - max runtime / max epoch 双限制；
  - validation `myops_scar` 或 scar foreground metric plateau patience；
  - 保存并导出 best checkpoint；
  - 日志中记录实际 epoch、elapsed time、best metric、停止原因。
- 三个模型之间的实验预算要尽量公平：每轮先用近似 **8 小时 walltime** 的 fold0 预算比较方向，再决定是否扩展。
- 除非发现会影响数据合规、label 定义或 leaderboard 提交口径的关键问题，不要停下来问用户；直接做下一轮可回滚的小改动并记录结果。

必须完成：

1. 指标重报：
   - 报告 all cases、GT-positive-only、T2-present-only 的 `myops_edema`。
   - 报告 all cases、scar-positive-only、三序列完整病例的 `myops_scar`。
   - 明确 empty-GT case 是否被计为 1.0，并说明对当前结论的影响。

2. Stage1 prior 体检：
   - 抽查 Case20xx / Case30xx 低分病例。
   - 对每例输出 aligned C0/T2/LGE、myocardium prior、GT scar/edema 的 geometry 和 overlap 统计。
   - 检查 case id、slice order、spacing/origin/direction 是否一致。
   - 对缺 C0/T2 病例确认不会拿零图做伪 registration 监督。

3. Stage2 scar 召回改进：
   - 检查 `whichsubnet` 训练与推理一致。
   - 在 `nnUNetTrainerPSNV8` 或派生 trainer 中加入 scar-positive sampling / scar CE or Tversky weight。
   - 对比当前 `nnUNetTrainerPSNV8ScarCE2`，不要盲目只加 epoch。
   - 输出 per-case predicted scar voxel count 与 GT scar voxel count，优先修 false negative。

4. 缺模态策略：
   - 三序列完整病例优先走完整 U-MyoPS path。
   - LGE-only 或缺 T2 病例需要 routing 或弱化缺失通道 prior；至少在报告中单独统计。
   - 不要让 zero-filled C0/T2 污染 Stage1/Stage2 的结论。

5. 评估闭环：
   - 显式 checkpoint export 不得复用 stale prediction cache。
   - `model_best` 和 `model_final_checkpoint` 要分别保存在不同 prediction/metric 目录。
   - 若 fold0 scar 达不到接近 nnU-Net，不要直接跑 fold1-4。

## 推荐实现范围

优先编辑：

- `code/U-MyoPS/build_stage2_task_from_stage1.py`
- `code/U-MyoPS/export_stage2_val_predictions.py`
- `third_party/U-MyoPS_myops/jrs/dataloader/jrsdataset.py`
- `third_party/U-MyoPS_myops/jrs/experiment/mscmr_asn_com_de.py`
- `third_party/U-MyoPS_myops/jrs/nnunet/training/network_training/nnUNetTrainerPSNV8*.py`
- `jobs/U-MyoPS/sbatch_stage1.sh`
- `jobs/U-MyoPS/sbatch_stage2.sh`
- `jobs/U-MyoPS/sbatch_export_eval_fold0.sh`

不要做：

- 不要引入外部训练数据。
- 不要把 edema 训练成 `edema ∪ scar`。
- 不要在 remap/cache 未可信时汇报 5-fold。
- 不要把旧 `results/metrics/unified/U-MyoPS/fold_0` 当最新结果。

## 验证命令建议

```bash
cd /overflow/htzhu/CARE

# 查看两个显式 checkpoint
python -m json.tool results/metrics/unified/U-MyoPS_model_best/fold_0/evaluation_summary.json
python -m json.tool results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/evaluation_summary.json

# 重新导出指定 checkpoint
UMYOPS_EXPORT_CHECKPOINT=model_best UMYOPS_EXPORT_FORCE_FALLBACK=1 \
  bash scripts/evaluation/run_unified_eval_model.sh U-MyoPS --folds 0

UMYOPS_EXPORT_CHECKPOINT=model_final_checkpoint UMYOPS_EXPORT_FORCE_FALLBACK=1 \
  bash scripts/evaluation/run_unified_eval_model.sh U-MyoPS --folds 0

# 小预算 Stage2 训练示例；具体 epoch 由本轮预算和 early stopping 决定
sbatch --export=ALL,UMYOPS_STAGE2_CONTINUE=1,UMYOPS_STAGE2_EPOCHS=<budgeted_epoch_or_earlystop>,FOLD=0 \
  -t 08:00:00 jobs/U-MyoPS/sbatch_stage2.sh
```

## 交付物

1. 代码改动，保持现有 Stage1/Stage2 边界。
2. 新的中文报告：`docs/notes/U-MyoPS_improvement_round2.md`
3. 更新或追加实验记录：`results/experiments/U-MyoPS_iteration_log.md`
4. 若重新评估完成，更新 `results/metrics/unified/U-MyoPS_<checkpoint>/aggregate.md/json`

报告必须明确列出：

- `myops_scar` 低分最主要原因是 Stage1 prior、Stage2 loss/sampling、缺模态，还是 export/cache。
- empty-GT 对 edema 的影响。
- 哪些病例或中心仍失败。
- 本轮 walltime、实际 epoch、best checkpoint、停止原因。
- 是否值得启动 fold1-4。
