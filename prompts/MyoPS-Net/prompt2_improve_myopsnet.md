# MyoPS-Net 改进 Prompt：缺模态鲁棒训练与 5-fold 超越 nnU-Net

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中系统性改进 MyoPS-Net，使其在 CARE MyoPS 多模态任务上尽可能超过 nnU-Net 本地 5-fold 基线：

| metric | nnU-Net 5-fold mean | 当前 MyoPS-Net fold0 |
| --- | ---: | ---: |
| `myops_scar` / class_5 | 0.5592 | 0.4637 |
| `myops_edema` / class_4 | 0.4197 | 0.2794 |

## 背景

必须先阅读：

- `docs/literature/Qiu 等 - 2023 - MyoPS-Net Myocardial pathology segmentation with flexible combination of multi-sequence CMR images.pdf`
- `prompts/Baseline_report.md`
- `prompts/MyoPS-Net/improvement_suggestion.md`
- `results/metrics/nnUNet.md`
- `results/metrics/unified/MyoPS-Net/fold_0/evaluation_summary.json`
- `TODO.md`

论文要点：

- MyoPS-Net 的核心是 CMFF 跨模态融合、MPC myocardium prior、PI scar-in-edema 约束。
- 完整论文输入是 C0/LGE/T2/T1 mapping/T2*，公开 challenge 使用 C0/LGE/T2 的 MyoPS-Net-L。
- CARE 没有 T1m/T2*，且 MyoPS_train 只有 80/220 三序列完整、24/220 缺 T2、116/220 LGE-only。

当前实现状态：

- `MYOPS_NET_VARIANT=challenge3` 已禁用 mapping 分支和 PI loss，避免 T1m/T2* 零图污染。
- 仍有零填充 C0/T2 缺失模态进入三模态输入，模型无法区分真实零强度与缺失。
- 只有 fold0 结果，不足以证明能否超过 nnU-Net。

## 任务目标

实现并验证一个保守、可复现的 MyoPS-Net 改进版本，优先解决 CARE 缺模态分布，而不是换 backbone。

## 运行预算与迭代策略

本 prompt 是多轮改进任务，不允许一次性提交超长训练。每一轮必须遵守：

- 单个 Slurm 训练/评估 job walltime 目标不超过 **8 小时**；如脚本默认更长，先把本轮实验入口改成 8 小时内可完成。
- 每轮只改一个主要假设，例如 modality mask/dropout、positive sampling、loss weight、后处理，不要一次混入多个无法归因的改动。
- 每轮必须先跑 fold0 或小预算 protocol validation；只有 fold0 稳定提升、预测非空、label 语义正确，才准备 fold1-4。
- 不要跑 1000/2000 epoch 这类长训；如果 8 小时内 loss/val Dice 没有明显改善，应该停止并分析失败原因。
- 如果现有训练器没有 early stopping 或 checkpoint selection，本轮优先加上：
  - max runtime / max epoch 双限制；
  - validation metric plateau patience；
  - 保存 best checkpoint，并在 export/eval 中显式使用 best checkpoint；
  - 日志中记录实际 epoch、elapsed time、best metric、停止原因。
- 三个模型之间的实验预算要尽量公平：每轮先用近似 **8 小时 walltime** 的 fold0 预算比较方向，再决定是否扩展到 5 folds。
- 除非发现会影响数据合规、label 定义或 leaderboard 提交口径的关键问题，不要停下来问用户；直接做下一轮可回滚的小改动并记录结果。

必须完成：

1. 全链路核查 `challenge3`：
   - 训练、export、eval 必须都使用 `MYOPS_NET_VARIANT=challenge3`。
   - T1m/T2starm placeholder 只能作为文件名兼容，不得进入前向或 loss。
   - `result_transform` 和 export remap 必须严格输出 CARE compact `4=edema`, `5=scar`。

2. 实现 modality-aware 训练：
   - dataloader 记录每个 case 的 `modalities_present`，至少区分 `c0`, `lge`, `t2`。
   - 模型或训练 batch 可以读取 modality mask；最低要求是在 loss/log 中按模态组合分组统计。
   - 训练时添加 modality dropout：随机 drop C0/T2，LGE 默认保留；drop 概率可配置。
   - 不要把 missing-zero 和 real-zero 混为一谈。

3. 强化 pathology 监督：
   - scar-positive 与 edema-positive slice/patch sampling 必须可配置。
   - class-specific loss weight 或 Tversky/Focal loss 只做小范围、可回滚改动。
   - edema 必须保持 strict class_4，不允许改成 `edema ∪ scar`。

4. 评估与报告：
   - fold0 先跑改进版 export/eval。
   - 按模态组合报告：LGE-only、C0+LGE、C0+LGE+T2。
   - 若 fold0 指标超过或接近 nnU-Net，再准备 fold1-4 Slurm 入口。
   - 报告必须同时说明 `myops_scar`、`myops_edema`、HD 风险和 empty-GT 处理。

## 推荐实现范围

优先编辑：

- `code/MyoPS-Net/prepare_myops_net_layout.py`
- `third_party/MyoPS-Net/utils/dataloader.py`
- `third_party/MyoPS-Net/criterion/loss.py`
- `third_party/MyoPS-Net/main.py` / config 相关文件
- `code/MyoPS-Net/run_train.sh`
- `code/MyoPS-Net/export_val_predictions.py`
- `jobs/MyoPS-Net/sbatch.sh`
- `scripts/evaluation/run_unified_eval_model.sh` 仅在必须修 cache/export 时编辑

不要做：

- 不要引入外部训练数据。
- 不要恢复 T1m/T2* mapping 分支。
- 不要把 edema 改成 union target。
- 不要在 fold0 未可信前直接大规模跑 5 folds。

## 验证命令建议

```bash
cd /overflow/htzhu/CARE

# 快速核查现有指标
python -m json.tool results/metrics/unified/MyoPS-Net/fold_0/evaluation_summary.json

# 重新导出评估 fold0
MYOPS_NET_VARIANT=challenge3 bash scripts/evaluation/run_unified_eval_model.sh MyoPS-Net --folds 0

# 正式 fold0 训练建议走 Slurm
MYOPS_NET_VARIANT=challenge3 MYOPS_NET_END_EPOCH=<budgeted_epoch_or_earlystop> \
  sbatch -t 08:00:00 jobs/MyoPS-Net/sbatch.sh
```

## 交付物

1. 代码改动，保持现有风格。
2. 新的中文报告：`docs/notes/MyoPS-Net_improvement_round2.md`
3. 更新或追加实验记录：`results/experiments/MyoPS-Net_iteration_log.md`
4. 若训练完成，更新 `results/metrics/unified/MyoPS-Net/aggregate.md/json`

报告必须明确列出：

- 改了哪些文件。
- 当前 fold 覆盖情况。
- 与 nnU-Net 的差距是否缩小。
- 按模态组合的 `myops_scar` / `myops_edema`。
- 本轮 walltime、实际 epoch、best checkpoint、停止原因。
- 下一步是否值得跑 5 folds。
