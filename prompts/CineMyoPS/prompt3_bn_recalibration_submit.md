# CineMyoPS round3 Prompt：修复 eval-mode BN collapse，提交预算内 fold0 训练并导出评估

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续改进 CineMyoPS。本轮必须在修复 `CARECineMyoPSTrainer` eval-mode inference 语义后，提交一个预算内 fold0 训练/导出/评估 Slurm job。不要只停留在代码修改或 export-only 诊断。

## 必须遵守

- 遵守 `AGENTS.md` 的 `Iterative model-improvement runs`。
- 单个训练/评估 job walltime 不超过 **8 小时**。
- 本轮只围绕一个主假设：**BatchNorm running stats / eval-mode inference collapse**。
- 不要跑 1000/2000 epoch。
- 不要扩展 5 folds。
- 不要做 official validation submission，除非 fold0 本地指标已经有实际可用信号；本轮“提交模型”指提交 Slurm 训练/评估 job。
- 不要覆盖或破坏已有 2026-05-12 的 `Task026_Cine_4D/CARECineMyoPSTrainer` checkpoint。若需要训练新变体，请使用新的 trainer class/name、备份输出目录，或在报告中明确说明隔离策略。

## 当前 round2 事实

必须先阅读：

- `docs/notes/CineMyoPS_improvement_round2.md`
- `results/experiments/CineMyoPS_iteration_log.md`
- `results/metrics/unified/CineMyoPS/fold_0/evaluation_summary.json`
- `prompts/CineMyoPS/prompt2_improve_cinemyops.md`
- `TODO.md`
- `AGENTS.md`

round2 已证实：

- 没有提交新训练；两个 Slurm job 都是 export/eval 诊断。
- `sanity_check_task026.py` 通过，64 个 Task026 cases 正常。
- `verify_ed_at_t0.py` 通过，`warn_count=0`。
- 当前 export 使用 `Task026_Cine_4D` + `CARECineMyoPSTrainer`，没有发现 Task025 混入。
- `model_final_checkpoint` 在常规 eval mode 导出仍全背景。
- `CINE_INFERENCE_TRAIN_MODE=1` 可让预测非空，说明 eval-mode BatchNorm running stats 高概率失效。
- train-mode 诊断结果仍不可用：`class_1=0.0003976`, `class_2=0.3090714`, `class_3=0.0016201`。
- `results/predictions/CineMyoPS/fold_0` 里是 symlink；统计文件数量时使用 `find -L` 或 `ls -l`，不要用 `find -type f` 误判为空。

当前本地基线：

| metric | nnU-Net 5-fold mean | CineMyoPS round2 train-mode diagnostic |
| --- | ---: | ---: |
| `class_1` / `myocardium_cinemyops` proxy | 0.6808 | 0.0004 |
| `class_3` / scar sanity | 0.2586 | 0.0016 |

## 本轮目标

1. 实现一个可复现的 eval-mode 修复路径。
2. 用常规 eval mode 导出，不再依赖 `CINE_INFERENCE_TRAIN_MODE=1`。
3. 提交一个 fold0 预算训练 job，并在训练结束后自动 export/eval。
4. 把结果写入新的 round3 报告和 iteration log。

## 推荐技术路线

按顺序执行，只有前一步失败才进入下一步：

### A. BN recalibration export-only 快速验证

先实现一个 BN recalibration pass：

- 加一个开关，例如 `CINE_BN_RECALIBRATE=1`。
- 在加载 checkpoint 后、正式 validation prediction 前：
  - 让模型进入 train mode 以更新 BatchNorm running mean/var；
  - 禁用梯度；
  - 使用训练集若干 batch 前向，batch 数可由 `CINE_BN_RECALIB_BATCHES` 控制；
  - 不更新 optimizer，不反传；
  - recalibration 完成后切回 eval mode；
  - 记录 recalibration batch 数、耗时、BN 层数量。
- 然后用正常 eval mode 导出 fold0，不启用 `CINE_INFERENCE_TRAIN_MODE=1`。

如果 BN recalibration 后 class_1/class_3 仍接近 0，继续 B。

### B. 训练新变体，避免覆盖旧 checkpoint

新建或配置一个隔离的 trainer，例如：

- `CARECineMyoPSTrainerBNCalib`
- 或 `CARECineMyoPSTrainerGN`（如果决定把 BatchNorm 替换为 GroupNorm/InstanceNorm）

优先选择最小改动：

1. 先试 `CARECineMyoPSTrainerBNCalib`：保持网络结构，只在 validation/export 前做 BN recalibration。
2. 如果 BN recalibration 无效，再考虑 GroupNorm/InstanceNorm 变体，但不要在同一轮同时混入其他结构变化。

训练要求：

- fold0 only。
- `CINE_NNUNET_EPOCHS` 控制在 8 小时内，默认可从 `120` 或 `200` 开始；如果已有经验显示 300 仍在 8 小时内，也可用 300，但必须记录理由。
- 使用 `CINE_SKIP_PREPARE=1`，除非 Task026 raw/preprocessed 缺失。
- 训练结束后自动 export/eval。
- 导出必须使用 normal eval mode；`CINE_INFERENCE_TRAIN_MODE=1` 只能作为对照，不作为最终结果。

### C. 输出语义检查

训练和导出后必须检查：

- `results/predictions/CineMyoPS/fold_0` 是否有 13 个 symlink 且 target 存在。
- 每例 prediction unique labels 和体素数。
- `class_1` 是否不再只有极少数 voxel。
- `class_3` scar 是否有合理非零预测。
- 是否出现 class_2 dominating、class_1 nearly absent 的失败模式。

## 建议编辑范围

优先编辑：

- `third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py`
- 新增 trainer 文件时放在同目录，例如 `CARECineMyoPSTrainerBNCalib.py`
- `code/CineMyoPS/export_protocol_val_predictions.sh`
- `jobs/CineMyoPS/sbatch_fold0_pipeline.sh`
- `jobs/CineMyoPS/sbatch_export_eval.sh`
- `jobs/CineMyoPS/run_task026_paper_steps.sh`
- `code/CineMyoPS/run_train.sh`

不要编辑：

- 不要改 Task026 label map。
- 不要改 `Dataset502_CARECineMyoPS` GT。
- 不要改官方 submission packaging 作为本轮主任务。
- 不要改 MyoPS-Net 或 U-MyoPS。

## 必须提交的 Slurm job

代码改完并通过最小 sanity 后，必须提交一个 fold0 训练+export+eval job。示例：

```bash
cd /overflow/htzhu/CARE

FOLD=0 \
CINE_NNUNET_TASK=Task026_Cine_4D \
CINE_NNUNET_TRAINER=CARECineMyoPSTrainerBNCalib \
CINE_NNUNET_EPOCHS=200 \
CINE_SKIP_PREPARE=1 \
CINE_RUN_EXPORT_EVAL=1 \
CINE_BN_RECALIBRATE=1 \
CINE_BN_RECALIB_BATCHES=32 \
sbatch jobs/CineMyoPS/sbatch_fold0_pipeline.sh
```

如果你没有新增 trainer，而是在原 trainer 上加开关，则把 `CINE_NNUNET_TRAINER` 改回 `CARECineMyoPSTrainer`，但必须说明如何避免覆盖旧 checkpoint。

提交后：

- 记录 Slurm job id。
- 不要等待超过当前交互能承受的时间；但要记录如何检查日志和结果。
- 如果提交失败，修复脚本并重新提交。

## 训练完成后的必跑评估

如果 job 已完成或你能继续等到完成，读取：

```bash
python -m json.tool results/metrics/unified/CineMyoPS/fold_0/evaluation_summary.json
python -m json.tool results/metrics/unified/CineMyoPS/aggregate.json
```

并检查 prediction labels：

```bash
find -L results/predictions/CineMyoPS/fold_0 -maxdepth 1 -name '*.nii.gz' | wc -l
```

写一个简短 Python/SimpleITK 统计每例 unique labels 和 voxel counts。不要用 `find -type f` 判断 symlink 目录是否为空。

## 交付物

1. 代码改动。
2. Slurm 训练 job 已提交的证据：job id、log path、命令/env。
3. 新报告：`docs/notes/CineMyoPS_improvement_round3.md`
4. 追加：`results/experiments/CineMyoPS_iteration_log.md`
5. 若 job 完成，更新：
   - `results/metrics/unified/CineMyoPS/fold_0/evaluation_summary.json`
   - `results/metrics/unified/CineMyoPS/aggregate.json`
   - `results/metrics/unified/CineMyoPS/aggregate.md`

报告必须包含：

- 是否实现 BN recalibration。
- 是否仍需要 `CINE_INFERENCE_TRAIN_MODE=1`。
- normal eval mode 下 class_1 / class_2 / class_3 的 Dice。
- 每例 prediction unique labels 总结。
- 训练 walltime、actual epochs、best checkpoint、停止原因。
- 是否值得进入 round4，以及 round4 只能测试的一个主假设。
