# MyoPS-Net round3 prompt: source-mask gated loss for CARE missing modalities

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续改进 MyoPS-Net，但本轮只验证一个主要假设：

> round2 的 modality dropout 没有提升，是因为模型虽然知道 `modalities_present`，但 loss 仍在缺失 C0/T2 的零图分支上计算 segmentation/invariant loss，尤其把缺 T2 病例当成 edema 背景训练，压低 `myops_edema`。

## 必须先读

- `docs/notes/MyoPS-Net_improvement_round2.md`
- `results/experiments/MyoPS-Net_iteration_log.md`
- `results/metrics/unified/MyoPS-Net/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_moddrop_round2/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_moddrop_round2/fold_0/modality_group_metrics.md`
- `prompts/MyoPS-Net/prompt2_improve_myopsnet.md`
- `prompts/Baseline_report.md`
- `results/metrics/nnUNet.md`

## 当前事实

nnU-Net 5-fold reference:

| metric | nnU-Net |
| --- | ---: |
| `myops_scar` / class_5 | 0.5592 |
| `myops_edema` / class_4 | 0.4197 |

MyoPS-Net fold0:

| metric | pre-round2 | round2 moddrop | conclusion |
| --- | ---: | ---: | --- |
| `myops_edema` / class_4 | 0.2794 | 0.1496 | worsened |
| `myops_scar` / class_5 | 0.4637 | 0.4584 | no improvement |
| foreground_mean | 0.4039 | 0.3317 | worsened |

round2 early stopped at epoch 49, best epoch 29. Do not expand to folds 1-4.

## Round3 目标

实现并验证 source/effective modality mask aware loss gating。不要换 backbone，不要恢复 T1m/T2* mapping，不要把 edema 改成 union target。

必须做到：

1. `CrossModalDataLoader` 返回的 `source_mask` / `train_mask` 要被训练 loss 真正使用。
2. 缺失 C0 的样本不应贡献 C0 cardiac branch loss，也不应参与 C0-LGE / C0-T2 invariant loss。
3. 缺失 T2 的样本不应贡献 T2 edema branch loss，也不应参与 C0-T2 invariant loss。
4. LGE 始终保留并继续贡献 scar loss。
5. 如果启用 modality dropout，被 dropout 的 C0/T2 也必须按 `train_mask` 从对应 branch loss/invariant loss 中排除；不要用零输入强迫网络拟合真值。
6. Edema 保持 strict class_4，scar 保持 class_5。

## 推荐实现

优先编辑：

- `third_party/MyoPS-Net/criterion/loss.py`
- `third_party/MyoPS-Net/train.py`
- `third_party/MyoPS-Net/utils/dataloader.py`
- `third_party/MyoPS-Net/utils/config.py`
- `jobs/MyoPS-Net/sbatch.sh`

建议把 `MyoPSLoss.forward` 扩展为可选参数，例如：

```python
loss_seg, loss_invariant, loss_inclusive, loss = mlsc_loss(seg, label, train_mask=train_mask)
```

其中 `train_mask` 至少包含 batch 级 `[C0, LGE, T2]` 或字典 `{c0,lge,t2}`。按样本 mask 做 loss 时要避免简单取 batch mean 后再乘一个标量；应尽量只在有效样本上求均值，空有效样本返回 0 loss。

如果实现逐样本 loss 改动过大，可以先实现保守版本：

- branch segmentation loss 使用有效样本子 batch；
- invariant loss 只在两端模态都有效的样本上计算；
- inclusive loss 继续在 `challenge3` 下为 0。

## 本轮实验设置

跑一个新的 fold0 隔离实验，建议命名：

- data: `data/benchmarks/MyoPS-Net/fold_0_maskgated_round3`
- checkpoint: `results/checkpoints/MyoPS-Net/fold_0_maskgated_round3`
- predictions: `results/predictions/MyoPS-Net_maskgated_round3/fold_0`
- metrics: `results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0`

先关闭 modality dropout，只测试 loss gating：

```bash
sbatch --export=ALL,FOLD=0,PREPARE=1,MYOPS_NET_DATA=/overflow/htzhu/CARE/data/benchmarks/MyoPS-Net/fold_0_maskgated_round3,MYOPS_NET_WORKDIR=/overflow/htzhu/CARE/results/checkpoints/MyoPS-Net/fold_0_maskgated_round3,MYOPS_NET_VARIANT=challenge3,MYOPS_NET_END_EPOCH=120,MYOPS_NET_MAX_RUNTIME_HOURS=7.75,MYOPS_NET_EARLY_STOP_PATIENCE=20,MYOPS_NET_MODALITY_DROPOUT=0,MYOPS_NET_MASK_GATED_LOSS=1,MYOPS_NET_PATHOLOGY_SAMPLER=1,MYOPS_NET_SAMPLE_WEIGHT_SCAR=2.0,MYOPS_NET_SAMPLE_WEIGHT_EDEMA=8.0,MYOPS_NET_EXPORT_EVAL=1,MYOPS_NET_PRED_DIR=/overflow/htzhu/CARE/results/predictions/MyoPS-Net_maskgated_round3/fold_0,MYOPS_NET_EVAL_OUTPUT_DIR=/overflow/htzhu/CARE/results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0 jobs/MyoPS-Net/sbatch.sh
```

保持单 job walltime <= 8h。不要跑 1000/2000 epoch。

## 必须报告的检查

1. 训练日志中打印每个 epoch 或启动时的有效 loss 样本数：
   - C0 branch valid count
   - LGE branch valid count
   - T2 branch valid count
   - C0-LGE invariant valid count
   - C0-T2 invariant valid count
2. 导出必须使用 `checkpoints/best.pth`，且 prediction/metric 目录不能复用 round2。
3. 评估后生成按模态组合报告：
   - LGE-only
   - C0+LGE
   - C0+LGE+T2
4. 对比 pre-round2、round2、round3：
   - `myops_scar`
   - `myops_edema`
   - foreground_mean
   - T2-present edema
   - LGE-only scar

## 成功/失败判定

- 如果 round3 `myops_edema` 回到并超过 0.2794，且 scar 不低于 0.46，loss gating 值得继续。
- 如果 T2-present edema 明显提升但 overall 仍低，下一轮应考虑 edema 只在 T2-present/GT-positive 子集建专家或推理路由，不要继续对 LGE-only 强求 edema。
- 如果 scar 下降超过 0.03，检查 gating 是否错误跳过 LGE scar loss。
- 只有 fold0 同时缩小与 nnU-Net 的差距，才准备 folds 1-4。

## 交付物

- 代码改动。
- 新报告：`docs/notes/MyoPS-Net_improvement_round3.md`
- 追加：`results/experiments/MyoPS-Net_iteration_log.md`
- 新 metrics：
  - `results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0/evaluation_summary.json`
  - `results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0/modality_group_metrics.md`

报告里必须明确回答：round2 失败是否主要因为缺模态 loss 未 gated；是否值得继续 MyoPS-Net；是否可以扩展 5 folds。
