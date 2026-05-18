# CineMyoPS round5 prompt: fixed inference-semantics debug before any more training

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 CineMyoPS，但本轮不要开始新的训练。本轮只验证一个主要假设：

> round4 的四种 combine mode 全部导出 all-background，问题可能发生在 direct branch logits、sliding-window inference、BN/eval mode、或 export label path。之前 debug 脚本选错 2D slice/patch，未能回答这个问题；本轮必须先用修复后的 diagnostic 闭合 inference 语义。

## 必须先读

- `docs/notes/CineMyoPS_improvement_round4.md`
- `results/experiments/CineMyoPS_iteration_log.md`
- `prompts/CineMyoPS/prompt4_inference_semantics.md`
- `prompts/Baseline_report.md`
- `results/metrics/nnUNet.md`
- `jobs/CineMyoPS/README.md`

## 当前事实

nnU-Net CineMyoPS local reference:

| metric | nnU-Net |
| --- | ---: |
| `myocardium_cinemyops` local proxy / class_1 | 0.6808 |

Current CineMyoPS results:

| variant | class_1 myocardium | class_2 LV | class_3 scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| train-mode diagnostic before round4 | 0.0004 | 0.3091 | 0.0016 | 0.1037 |
| round4 `current` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| round4 `cardiac_only` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| round4 `myocardium_gated_scar` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| round4 `pathology_direct` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Important code context:

- `scripts/evaluation/debug_cinemyops_inference_semantics.py` has been fixed to infer the 2D slice axis from trainer patch size and image dimensions.
- `jobs/CineMyoPS/sbatch_round5_debug_fixed.sh` is prepared as a short diagnostic wrapper.

## Round5 目标

1. Run the fixed diagnostic on GPU and inspect `results/diagnostics/CineMyoPS_round5/inference_semantics_fixed.json`.
2. Determine exactly where predictions collapse:
   - direct eval forward branch logits;
   - direct train-mode forward branch logits;
   - compact-softmax combine;
   - sliding-window aggregation;
   - exported NIfTI label mapping.
3. If the diagnostic identifies a small inference/export bug, fix it and run one export-only fold0 evaluation.
4. If direct logits are already collapsed, do not train longer; prepare the next prompt around trainer supervision/normalization instead.

## 必须运行

Use the existing short Slurm diagnostic:

```bash
cd /overflow/htzhu/CARE
sbatch jobs/CineMyoPS/sbatch_round5_debug_fixed.sh
```

Expected output:

- `results/diagnostics/CineMyoPS_round5/inference_semantics_fixed.json`
- log under `logs/CineMyoPS_R5_debug_<jobid>_<timestamp>.log`

If the job fails, fix only the diagnostic shape/device/env issue and rerun. Do not move to training.

## 若发现可修复 inference/export bug

Allowed fixes:

- wrong network input patch extraction;
- wrong compact label argmax / class mapping;
- sliding-window softmax shape/order bug;
- eval-mode BN switch or recalibration bug if proven by direct train/eval contrast;
- export NIfTI label remap bug.

Then run only a short export/eval, not training. Use config-specific prediction dirs, for example:

- `results/predictions/CineMyoPS_R5_fixed_inference/fold_0`
- `results/metrics/unified/CineMyoPS_R5_fixed_inference/fold_0`

## 结果判定

- If direct branch logits contain meaningful non-background labels but exported predictions are empty: fix inference/export and re-evaluate.
- If direct eval logits are empty but direct train-mode logits are non-empty: focus on BN/eval statistics, not architecture.
- If direct train-mode and eval-mode logits are both empty: current checkpoint/training objective failed; next round should redesign supervision/normalization, not continue epochs.
- Only consider new training if the diagnostic proves the existing checkpoint cannot produce useful logits even in direct train-mode.

## 禁止事项

- 不要提交新的 CineMyoPS training job。
- 不要扩展到 folds 1-4。
- 不要用 official validation submission 测试这个模型。
- 不要把 online training Dice 当成最终结论；必须以 protocol validation export/eval 为准。
- 不要复用旧 `results/predictions/CineMyoPS*` 目录作为新结果。

## 交付物

- 追加：`results/experiments/CineMyoPS_iteration_log.md`
- 新报告：`docs/notes/CineMyoPS_improvement_round5.md`
- Diagnostic JSON: `results/diagnostics/CineMyoPS_round5/inference_semantics_fixed.json`
- 如修复 export/inference：对应 metric JSON and prediction dirs

最终报告必须明确回答：CineMyoPS 当前是 direct logits collapse、eval-mode collapse、sliding-window collapse，还是 export label collapse；下一轮是否允许训练，以及训练要改什么。
