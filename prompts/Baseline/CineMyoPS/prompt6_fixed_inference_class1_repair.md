# CineMyoPS round6 prompt: fixed-inference combine ablation and class_1 repair

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 CineMyoPS。本轮目标是让 CineMyoPS 在自己的 Cine 任务上超过 nnU-Net，尤其是 local protocol `class_1` myocardium proxy。

本轮不要先训练。round5 已证明 direct logits 有效，fixed inference 后不再全背景；现在要做的是 fixed-inference 条件下的 combine/export ablation 与 class_1 优先修复。

## 必须先读

- `docs/notes/CineMyoPS_improvement_round4.md`
- `results/experiments/CineMyoPS_iteration_log.md`
- `prompts/CineMyoPS/prompt5_fixed_inference_debug.md`
- `results/diagnostics/CineMyoPS_round5/inference_semantics_fixed.json`
- `results/metrics/unified/CineMyoPS_R5_fixed_inference/fold_0/evaluation_summary.json`
- `logs/CineMyoPS_export_eval_51354763_20260517_232845.log`
- `prompts/Baseline_report.md`
- `results/metrics/nnUNet.md`

## 当前事实

nnU-Net CineMyoPS reference:

| metric | nnU-Net 5-fold mean | nnU-Net fold0 |
| --- | ---: | ---: |
| class_1 myocardium | 0.6808 | 0.6864 |
| class_3 scar sanity | 0.2586 | 0.2446 |

Current CineMyoPS:

| variant | class_1 myocardium | class_2 LV | class_3 scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| round4 all combine modes | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| round5 fixed inference, `current` combine | 0.6067 | 0.9305 | 0.3942 | 0.6438 |

Round5 diagnostic conclusion:

- Direct eval forward produces non-background myocardium/LV/scar on sampled slices.
- Direct train-mode forward also produces non-background labels.
- `predict_preprocessed_data_return_seg_and_softmax` originally collapsed to all-background, then fixed inference recovered usable protocol predictions.
- The remaining gap is `class_1`: scar sanity already exceeds nnU-Net, but class_1 is still below nnU-Net by about `0.074`.

## Round6 目标

1. Under the fixed inference path, rerun combine-mode export ablations:
   - `current`
   - `cardiac_only`
   - `myocardium_gated_scar`
   - `pathology_direct`
2. Compare class_1, class_2, class_3, and per-case failures.
3. If `cardiac_only` improves class_1 but removes scar, use it only as a diagnostic/upper-bound for anatomy. Implement a class_1-primary export candidate that preserves the best class_1 anatomy and overlays/keeps the pathology branch where possible.
4. If class_1 remains below nnU-Net, prepare one short fold0 training/calibration round targeting anatomy loss/BN stability, not a long epoch extension.

## 建议实现

Add or update a short export-only Slurm wrapper, for example:

- `jobs/CineMyoPS/sbatch_round6_fixed_inference_modes.sh`

It should run `jobs/CineMyoPS/sbatch_export_eval.sh` four times with:

```bash
FOLD=0
CINE_NNUNET_TASK=Task026_Cine_4D
CINE_NNUNET_TRAINER=CARECineMyoPSTrainerBNCalib
CINE_PRED_CHECKPOINT=model_final_checkpoint
CINE_BN_RECALIBRATE=1
CINE_BN_RECALIB_BATCHES=32
CINE_INFERENCE_TRAIN_MODE=0
CINE_COMBINE_MODE=<mode>
CINE_OUTPUT_MODEL=CineMyoPS_R6_<mode>
```

Expected metric dirs:

- `results/metrics/unified/CineMyoPS_R6_current/fold_0`
- `results/metrics/unified/CineMyoPS_R6_cardiac_only/fold_0`
- `results/metrics/unified/CineMyoPS_R6_myo_gated_scar/fold_0`
- `results/metrics/unified/CineMyoPS_R6_pathology_direct/fold_0`

If a simple class_1-primary overlay is implemented, write it to:

- `results/predictions/CineMyoPS_R6_class1_primary_overlay/fold_0`
- `results/metrics/unified/CineMyoPS_R6_class1_primary_overlay/fold_0`

Important paper-alignment guard:

- `cardiac_only` is not a paper-faithful final method because it drops the CineMyoPS pathology branch. It is allowed only to diagnose whether anatomy logits can beat nnU-Net class_1.
- Final candidates should remain consistent with the CineMyoPS idea: cine temporal/motion features + ED anatomy + pathology/scar branch. If the best local class_1 score comes from anatomy-only output, report it as an anatomy upper bound and prepare the next prompt to repair the pathology/anatomy combination rather than declaring the paper method solved.

## 结果判定

- Primary success: `class_1 > 0.6808` on fold0 protocol val while keeping outputs non-empty.
- Strong result: `class_1 > 0.6864` and `class_3 >= 0.2586`.
- If `class_1` improves but remains `0.63-0.68`, next prompt may allow one <=8h fold0 anatomy-focused training/calibration round.
- If no combine/export variant improves class_1 over `0.6067`, do not expand folds; inspect anatomy loss/training target next.

## 禁止事项

- 不要启动长训或 folds 1-4。
- 不要回到 all-background round4 output dirs.
- 不要把 class_3 scar improvement 当成 Cine 任务整体成功；当前主要短板是 class_1。
- 不要把 permanent `cardiac_only` 当成 CineMyoPS paper-faithful final model unless the official metric is confirmed to ignore pathology.
- 不要复用 stale `_tmp/CineMyoPS_*` cache unless the output model tag is unique and the log proves fresh/fixed inference.

## 交付物

- 代码/脚本改动（如有）。
- 新报告：`docs/notes/CineMyoPS_improvement_round6.md`
- 追加：`results/experiments/CineMyoPS_iteration_log.md`
- 所有 round6 variant 的 `evaluation_summary.json`

最终报告必须明确回答：fixed inference 后哪个 combine/export strategy 最接近或超过 nnU-Net；若仍未超过，下一轮训练应改 anatomy supervision、BN/calibration，还是 frame/ED policy。
