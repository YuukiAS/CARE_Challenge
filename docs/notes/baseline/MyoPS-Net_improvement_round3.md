# MyoPS-Net improvement round3

日期：2026-05-17

## 目标

本轮只测试一个主要假设：round2 modality dropout 失败，是因为缺失 C0/T2 或被 dropout 的 C0/T2 仍然参与对应 branch loss 与 invariant loss。Round3 实现 source/effective modality mask aware loss gating，不换 backbone，不恢复 T1m/T2* mapping，不改变 edema/scar 标签口径。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `third_party/MyoPS-Net/criterion/loss.py` | `MyoPSLoss.forward(..., train_mask=...)`；按有效 sub-batch 计算 branch loss 和 invariant loss |
| `third_party/MyoPS-Net/train.py` | 传入 `train_mask`；每 epoch 打印有效 loss 样本数 |
| `third_party/MyoPS-Net/utils/config.py` | 增加 `--mask_gated_loss` / `MYOPS_NET_MASK_GATED_LOSS` |
| `code/MyoPS-Net/run_train.sh` | 透传并打印 `MYOPS_NET_MASK_GATED_LOSS` |
| `jobs/MyoPS-Net/sbatch.sh` | 打印 `MYOPS_NET_MASK_GATED_LOSS`，保持 8 小时入口和 isolated export/eval |

## challenge3 与标签核查

- `challenge3` 下 `network/model.py` 只使用 `C0/LGE/T2`，不使用 T1m/T2starm mapping branch。
- `criterion/loss.py` 在 `challenge3` 下 inclusive loss 仍为 0，不使用 scar-in-edema union 假设。
- `LabelTransform` 仍保持 strict edema：raw `1220 -> edema`，raw `2221 -> non-edema myocardium`。
- Export 仍输出 compact CARE labels：`4=edema`, `5=scar`。

## Loss Gating 语义

| loss component | valid mask |
| --- | --- |
| C0 cardiac branch | `train_mask[:, 0]` |
| LGE scar branch | `train_mask[:, 1]`，LGE 默认保留 |
| T2 edema branch | `train_mask[:, 2]` |
| C0-LGE invariant | `train_mask[:, 0] & train_mask[:, 1]` |
| C0-T2 invariant | `train_mask[:, 0] & train_mask[:, 2]` |

如果某个 batch 内没有有效样本，对应 loss 返回 0，不用零图拟合真值。

## 既有结果

| metric | pre-round2 fold0 | round2 moddrop | nnU-Net 5-fold |
| --- | ---: | ---: | ---: |
| `myops_edema` / class_4 | 0.2794 | 0.1496 | 0.4197 |
| `myops_scar` / class_5 | 0.4637 | 0.4584 | 0.5592 |
| foreground_mean | 0.4039 | 0.3317 | NA |

Round2 分组：

| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | 0.0000 | 0.4557 | 0.2278 |
| C0+LGE+T2 | 16 | 0.3367 | 0.5943 | 0.4655 |
| LGE | 24 | 0.0000 | 0.3682 | 0.2598 |

## Round3 作业

Slurm job: `51264396`

```bash
sbatch --export=ALL,FOLD=0,PREPARE=1,MYOPS_NET_DATA=/overflow/htzhu/CARE/data/benchmarks/MyoPS-Net/fold_0_maskgated_round3,MYOPS_NET_WORKDIR=/overflow/htzhu/CARE/results/checkpoints/MyoPS-Net/fold_0_maskgated_round3,MYOPS_NET_VARIANT=challenge3,MYOPS_NET_END_EPOCH=120,MYOPS_NET_MAX_RUNTIME_HOURS=7.75,MYOPS_NET_EARLY_STOP_PATIENCE=20,MYOPS_NET_MODALITY_DROPOUT=0,MYOPS_NET_MASK_GATED_LOSS=1,MYOPS_NET_PATHOLOGY_SAMPLER=1,MYOPS_NET_SAMPLE_WEIGHT_SCAR=2.0,MYOPS_NET_SAMPLE_WEIGHT_EDEMA=8.0,MYOPS_NET_EXPORT_EVAL=1,MYOPS_NET_PRED_DIR=/overflow/htzhu/CARE/results/predictions/MyoPS-Net_maskgated_round3/fold_0,MYOPS_NET_EVAL_OUTPUT_DIR=/overflow/htzhu/CARE/results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0 jobs/MyoPS-Net/sbatch.sh
```

预算与停止条件：

| item | value |
| --- | --- |
| Fold | 0 only |
| Slurm walltime | 08:00:00 |
| Train runtime guard | 7.75 hours |
| Max epochs | 120 |
| Early stop patience | 20 validation epochs |
| Checkpoint selection | `checkpoints/best.pth` by validation pathology average |
| Export/eval | isolated round3 output dirs |

启动核查：

- `MYOPS_NET_MODALITY_DROPOUT=0`
- `MYOPS_NET_MASK_GATED_LOSS=1`
- Train source groups: LGE 92 cases, C0+LGE 20 cases, C0+LGE+T2 64 cases.
- Val source groups: LGE 24 cases, C0+LGE 4 cases, C0+LGE+T2 16 cases.
- Epoch 1 loss valid counts: C0 branch 890, LGE branch 1792, T2 branch 823, C0-LGE invariant 890, C0-T2 invariant 823.

## 训练结果

`results/checkpoints/MyoPS-Net/fold_0_maskgated_round3/checkpoints/train_stop_summary.json`

| item | value |
| --- | --- |
| stop reason | `early_stop_patience` |
| actual epochs | 49 |
| best epoch | 29 |
| elapsed | 1771.6 seconds |
| best 2D pathology Dice | 0.2039 |
| mask gated loss | true |
| checkpoint exported | `checkpoints/best.pth` |

Prediction sanity:

- Prediction files: 44/44.
- Non-empty predictions: 44/44.
- Label set: compact CARE labels only, `(0, 4, 5)`.
- Bad labels: none.

## 3D fold0 指标

`results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0/evaluation_summary.json`

| metric | pre-round2 fold0 | round2 moddrop | round3 mask-gated | nnU-Net 5-fold |
| --- | ---: | ---: | ---: | ---: |
| `myops_edema` / class_4 | 0.2794 | 0.1496 | 0.1293 | 0.4197 |
| `myops_scar` / class_5 | 0.4637 | 0.4584 | 0.4965 | 0.5592 |
| foreground_mean | 0.4039 | 0.3317 | 0.3129 | NA |

Round3 按 source modality group：

| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | 0.0000 | 0.4072 | 0.2036 |
| C0+LGE+T2 | 16 | 0.3555 | 0.6171 | 0.4863 |
| LGE | 24 | 0.0000 | 0.4311 | 0.2155 |

Key deltas:

- T2-present edema improved: baseline 0.3143 -> round2 0.3367 -> round3 0.3555.
- T2-present scar improved over both prior runs: baseline 0.6043 -> round2 0.5943 -> round3 0.6171.
- LGE-only scar improved: baseline 0.3820 -> round2 0.3682 -> round3 0.4311.
- Overall edema worsened further because non-T2 groups still produce edema false positives scored as 0 under `--skip-dice-if-gt-empty` when predictions are non-empty.

HD risk:

- HD was not computed in this budgeted round (`MYOPS_NET_EVAL_HD` was not enabled).
- The main HD risk remains edema false positives in T2-missing cases and small isolated pathology components. This risk is consistent with the Dice drop in non-T2 source groups.

## 结论

Round2 失败不是单纯由“缺模态 loss 未 gated”造成。Loss gating 确实改善了 T2-present pathology 和 LGE-only scar，但没有解决 T2-missing edema false positives；overall `myops_edema` 继续下降，未达到 prompt3 成功标准。

当前不值得扩展 5 folds。下一轮如果继续 MyoPS-Net，应优先做 inference/branch routing 或 loss/output gating：T2 缺失时不要让 T2 edema branch 输出参与最终 `class_4`，或只在 T2-present/GT-positive 子集训练 edema expert；不要再对 LGE-only 强求 edema。
