# MyoPS-Net improvement round2

日期：2026-05-17

## 目标

本轮只测试一个主要假设：让 MyoPS-Net 的 `challenge3` 训练显式知道 CARE 的 source modality availability，并用轻量 C0/T2 modality dropout 提升缺模态鲁棒性。严格保持 `edema=class_4`，`scar=class_5`，不恢复 T1m/T2* mapping 分支，不跑 5 folds。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `code/MyoPS-Net/prepare_myops_net_layout.py` | staging 输出 `modalities_present.json`；T1m/T2starm 仍只做文件名兼容 placeholder |
| `third_party/MyoPS-Net/utils/dataloader.py` | 读取/返回 `source_mask` 和 `train_mask`；只对 source-present C0/T2 做 dropout，LGE 保留 |
| `third_party/MyoPS-Net/utils/tools.py` | 全零 placeholder 归一化为零，避免 NaN |
| `third_party/MyoPS-Net/train.py` | 记录模态组合、effective dropout 组合、best/last checkpoint、runtime guard、early stop summary |
| `third_party/MyoPS-Net/utils/config.py` | 增加 `--max_runtime_hours` 与 `--early_stop_patience` |
| `jobs/MyoPS-Net/sbatch.sh` | 默认 8 小时 walltime；timestamped tee logging；支持隔离 export/eval 目录 |
| `code/MyoPS-Net/report_modality_groups.py` | 输出 fold metrics 的 source-modality 分组报告 |
| `scripts/evaluation/run_unified_eval_model.sh` | MyoPS-Net 统一评估后自动生成 modality-group metrics |

## challenge3 链路核查

- Training command 显式设置 `MYOPS_NET_VARIANT=challenge3`。
- `network/model.py` 在 `challenge3` 下 `uses_mapping=False`，forward 只 concat `C0/LGE/T2`；`T1m/T2starm` 不进入模型。
- `criterion/loss.py` 在 `challenge3` 下不使用 mapping loss，且禁用 PI inclusive loss，避免把 scar 当作 edema union。
- `LabelTransform` 对 edema 使用 strict class: raw `1220 -> edema`, raw `2221 -> myocardium/non-edema`。
- Export 输出 compact CARE labels: pathology `1 -> 4` edema, `2 -> 5` scar。

## 已有 fold0 基线

`results/metrics/unified/MyoPS-Net/fold_0/evaluation_summary.json`

| metric | fold0 |
| --- | ---: |
| `myops_edema` / class_4 | 0.2794 |
| `myops_scar` / class_5 | 0.4637 |
| foreground_mean | 0.4039 |

与 nnU-Net 5-fold prompt baseline 差距：

| metric | nnU-Net 5-fold | MyoPS-Net fold0 | gap |
| --- | ---: | ---: | ---: |
| `myops_edema` | 0.4197 | 0.2794 | -0.1403 |
| `myops_scar` | 0.5592 | 0.4637 | -0.0955 |

## 按模态组合的 baseline 诊断

`results/metrics/unified/MyoPS-Net/fold_0/modality_group_metrics.md`

| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | NA | 0.3910 | 0.3910 |
| C0+LGE+T2 | 16 | 0.3143 | 0.6043 | 0.4593 |
| LGE | 24 | 0.0000 | 0.3820 | 0.3690 |

解释：edema 在 LGE-only 子集接近不可见，fold0 的 `class_4` 均值主要由 T2-present 子集决定。HD 风险主要来自无 T2 病例的 edema false positive 或 T2-present 病例的小离群连通域；本轮不改后处理，只先验证 modality-aware training 是否减少这一类风险。

## round2 fold0 作业

Slurm job: `51256887`

```bash
sbatch --export=ALL,FOLD=0,PREPARE=1,MYOPS_NET_DATA=/overflow/htzhu/CARE/data/benchmarks/MyoPS-Net/fold_0_moddrop_round2,MYOPS_NET_WORKDIR=/overflow/htzhu/CARE/results/checkpoints/MyoPS-Net/fold_0_moddrop_round2,MYOPS_NET_VARIANT=challenge3,MYOPS_NET_END_EPOCH=120,MYOPS_NET_MAX_RUNTIME_HOURS=7.75,MYOPS_NET_EARLY_STOP_PATIENCE=20,MYOPS_NET_MODALITY_DROPOUT=1,MYOPS_NET_DROPOUT_C0=0.10,MYOPS_NET_DROPOUT_T2=0.20,MYOPS_NET_PATHOLOGY_SAMPLER=1,MYOPS_NET_EXPORT_EVAL=1,MYOPS_NET_PRED_DIR=/overflow/htzhu/CARE/results/predictions/MyoPS-Net_moddrop_round2/fold_0,MYOPS_NET_EVAL_OUTPUT_DIR=/overflow/htzhu/CARE/results/metrics/unified/MyoPS-Net_moddrop_round2/fold_0 jobs/MyoPS-Net/sbatch.sh
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
| Export/eval | after training, isolated round2 output dirs |

启动日志：

- `logs/MyoPS-Net_51256887_20260517_042939.log`
- Train groups: LGE 92 cases, C0+LGE 20 cases, C0+LGE+T2 64 cases.
- Val groups: LGE 24 cases, C0+LGE 4 cases, C0+LGE+T2 16 cases.
- Pathology sampler: scar-positive 1429 slices, edema-positive 259 slices.

## round2 结果

训练已完成并触发 early stop：

| item | value |
| --- | --- |
| stop reason | `early_stop_patience` |
| actual epochs | 49 |
| best epoch | 29 |
| elapsed | 2787.7 seconds |
| best 2D pathology Dice | 0.2027 |
| checkpoint exported | `checkpoints/best.pth` |

结果文件：

- `results/checkpoints/MyoPS-Net/fold_0_moddrop_round2/checkpoints/train_stop_summary.json`
- `results/metrics/unified/MyoPS-Net_moddrop_round2/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_moddrop_round2/fold_0/modality_group_metrics.md`

与 round2 前 fold0 对比：

| metric | fold0 baseline | round2 moddrop | change | nnU-Net 5-fold |
| --- | ---: | ---: | ---: | ---: |
| `myops_edema` / class_4 | 0.2794 | 0.1496 | -0.1298 | 0.4197 |
| `myops_scar` / class_5 | 0.4637 | 0.4584 | -0.0053 | 0.5592 |
| foreground_mean | 0.4039 | 0.3317 | -0.0722 | — |

按模态组合：

| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | 0.0000 | 0.4557 | 0.2278 |
| C0+LGE+T2 | 16 | 0.3367 | 0.5943 | 0.4655 |
| LGE | 24 | 0.0000 | 0.3682 | 0.2598 |

解释：

- 轻量 modality dropout 没有改善总体指标；scar 基本持平但仍低于 nnU-Net，edema 明显下降。
- T2-present 子集的 edema 从 0.3143 小幅升到 0.3367，说明 T2 监督方向有一点有效信号；但总体仍被缺 T2 / LGE-only 病例拖垮。
- round2 只让 dataloader 记录/扰动模态，没有让 loss 显式跳过缺失 C0/T2 分支。缺 T2 病例仍可能用零图参与 T2 edema loss 与 C0-T2 invariant loss，继续把模型推向“edema 背景化”。
- 下一轮不应继续加 epoch 或扩大 folds，应先做 source/effective modality mask aware 的 loss gating。

## 是否值得扩展 5 folds

现在不能扩展。round2 没有超过 baseline，也没有缩小与 nnU-Net 的差距。round3 应只做 fold0 小轮次，核心假设是“缺模态病例不应贡献对应分支和 invariant loss”。
