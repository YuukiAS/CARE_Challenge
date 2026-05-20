# CineMyoPS improvement round2

日期: 2026-05-17

## 目标

本轮严格按 `AGENTS.md` 的 iterative model-improvement 规则执行: 不长训, 不扩展 5 folds, 只围绕 fold0 全 0 定位做 export/eval 诊断。没有启动新的训练 job。

主问题: `results/predictions/CineMyoPS/fold_0/*.nii.gz` 在常规导出下 13 个 protocol val cases 全背景, unified eval 全 0。

## 已验证的数据链路

- `./env_CARE/bin/python code/CineMyoPS/sanity_check_task026.py`: 通过。64 个 Task026 cases 的 shape/labels 正常, 抽样 morphology Dice 非零。
- `./env_CARE/bin/python code/CineMyoPS/verify_ed_at_t0.py`: 通过。`total_cases=64`, `warn_count=0`。
- fold0 protocol val: 13 cases, 来自 `data/benchmarks/protocol/splits_CineMyoPS.json`。
- Task026 raw input: 每个 fold0 val case 都有 4 个通道, 即 `CINE_NUM_FRAMES=4`。
- 当前 export 日志使用 `Task026_Cine_4D` + `CARECineMyoPSTrainer`; 本轮没有发现 Task025 参与当前 protocol export/eval。

## checkpoint 诊断

旧的默认 export 读 `model_best.model`。该文件时间早于最终 checkpoint:

| checkpoint | mtime |
| --- | --- |
| `model_best.model` | `2026-05-12 17:52:01 -0400` |
| `model_final_checkpoint.model` | `2026-05-12 20:05:52 -0400` |

为排除 checkpoint 选择问题, 提交了 export-only job:

| job | checkpoint | extra env | elapsed | result |
| --- | --- | --- | ---: | --- |
| `51256637` | `model_final_checkpoint` | none | `00:14:36` | 仍全 0 |

结论: 全 0 不是单纯因为 export 读取了旧 `model_best`。

## 根因定位

训练日志末尾显示在线 validation 的 foreground Dice 估计非零, 且 loss 组件有限:

- `motion loss` 非零且有限。
- `cardiac_seg loss`, `pathology_seg loss` 有限。
- epoch 399 在线估计约为 class1/class2/class3 = `0.7263 / 0.9393 / 0.4925`。

但是同一个 final checkpoint 在常规 inference eval mode 下导出全背景。随后只改变一个变量重新导出:

```bash
CINE_INFERENCE_TRAIN_MODE=1 \
FOLD=0 CINE_PRED_CHECKPOINT=model_final_checkpoint \
CINE_NNUNET_TASK=Task026_Cine_4D \
CINE_NNUNET_TRAINER=CARECineMyoPSTrainer \
sbatch jobs/CineMyoPS/sbatch_export_eval.sh
```

该 job `51259699` 用时 `00:06:50`, 输出从全 0 变为非空。最可能根因是 `CARECineMyoPSTrainer` 的 eval-mode BatchNorm running stats 失效/未校准, 导致 inference collapse 到背景; train-mode BatchNorm 使用当前 case/batch 统计后不再全背景。

## 本轮代码改动

- `jobs/CineMyoPS/*.sh`: 将 CineMyoPS 训练入口 walltime 改为不超过 8 小时。
- `code/CineMyoPS/run_train.sh`, `jobs/CineMyoPS/run_task026_paper_steps.sh` 和 `CARECineMyoPSTrainer`: 默认 epoch cap 从 500 改为 300。
- `code/CineMyoPS/export_protocol_val_predictions.sh`: 默认 checkpoint 改为 `model_final_checkpoint`, 并打印 checkpoint path/mtime/size; 如果 `model_best` 比 final 旧则警告。
- `third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py`: 添加诊断开关 `CINE_INFERENCE_TRAIN_MODE=1`, 仅用于验证 eval-mode BatchNorm collapse。

## 当前 fold0 结果

最终 metrics 来自 job `51259699`, 即 final checkpoint + `CINE_INFERENCE_TRAIN_MODE=1` 的诊断导出:

| metric | CineMyoPS fold0 | nnU-Net ref | gap |
| --- | ---: | ---: | ---: |
| `class_1` / `myocardium_cinemyops` proxy | 0.0004 | 0.6808 | -0.6804 |
| `class_3` / scar sanity | 0.0016 | 0.2586 | -0.2570 |
| `class_2` / LV_blood sanity | 0.3091 | n/a | n/a |
| `foreground_mean` | 0.1037 | n/a | n/a |

Prediction unique labels are no longer all 0. However, label semantics are still poor:

- `class_2` and `class_3` dominate the nonzero voxels.
- `class_1` appears in only 3/13 cases and only a few voxels.
- This is a pipeline-health result, not a model-quality result.

## 是否值得官方 validation submission

暂不值得。虽然全 0 已被定位并通过 train-mode BatchNorm 诊断恢复为非空, 但 `class_1=0.0004` 和 `class_3=0.0016` 远低于 nnU-Net reference, 且输出语义明显偏向 class2/class3。下一轮应优先修复 BatchNorm/eval inference 语义, 例如重新校准 running stats、替换/冻结 BN 策略, 或保存可用于 eval-mode 的 checkpoint, 再考虑 official validation dry-run。

## 下一轮建议

只测试一个假设: BatchNorm running stats 校准。

建议 fold0 小步:

1. 在训练结束后增加 BN recalibration pass, 使用训练集若干 batch 前向更新 running stats, 不反传。
2. 用常规 eval mode 导出 final checkpoint, 不启用 `CINE_INFERENCE_TRAIN_MODE=1`。
3. 比较 unique labels、`class_1`、`class_3` 是否仍非空且语义改善。
