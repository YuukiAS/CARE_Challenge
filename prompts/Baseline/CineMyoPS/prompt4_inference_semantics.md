# CineMyoPS round4 prompt: debug inference softmax semantics before any more training

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续改进 CineMyoPS。本轮不要先继续训练；只验证一个主要假设：

> round3 isolated training 的 online eval 有非零 Dice，但 post-training validation inference / export 仍全 0，说明失败发生在 `predict_preprocessed_data_return_seg_and_softmax`、sliding-window inference、softmax combination 或 export label path，而不是单纯训练不足。

## 必须先读

- `docs/notes/CineMyoPS_improvement_round3.md`
- `results/experiments/CineMyoPS_iteration_log.md`
- `results/metrics/unified/CineMyoPS_BNCalib/fold_0/evaluation_summary.json`
- `logs/CineMyoPS_e2e_51264136_20260517_051831.log`
- `third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py`
- `results/metrics/nnUNet.md`

## 当前事实

| result | class_1 | class_2 | class_3 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| nnU-Net Dataset502 5-fold | 0.6808 | - | 0.2586 scar sanity | - |
| round2 train-mode BN diagnostic | 0.0004 | 0.3091 | 0.0016 | 0.1037 |
| round3 BN recalib export-only | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| round3 BNCalib isolated train | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Training-loop online eval during round3 had nonzero estimates, for example epoch 18 `[0.5591, 0.8679, 0.3310]`, but validation inference and exported predictions are all background. Do not trust online eval as final metric until the inference path is calibrated.

## Round4 目标

Find the exact point where predictions collapse to background, then test export-only combination alternatives. No 5-fold, no official submission, no long training.

## Required diagnostics

Add a script, for example:

- `scripts/evaluation/debug_cinemyops_inference_semantics.py`

It should load the round3 BNCalib fold0 checkpoint and inspect 2-3 protocol validation cases plus 1 training case. For each selected case/slice, report:

1. raw/preprocessed input shape and label voxel counts;
2. direct network forward in eval mode:
   - `cardiac_seg` logits mean/min/max per channel;
   - `pathology_seg` logits mean/min/max per channel;
   - `torch.softmax(cardiac_seg[:, :, 0])` argmax counts;
   - `torch.softmax(pathology_seg)` argmax counts;
   - current `_combine_compact_softmax` argmax counts;
3. same direct forward in train mode, only as diagnostic;
4. `predict_preprocessed_data_return_seg_and_softmax(..., do_mirroring=False, use_gaussian=False)` channel stats and argmax counts;
5. exported NIfTI unique labels for the same case.

This diagnostic must answer:

- Does `cardiac_seg` alone predict class_1/class_2 non-background in eval mode?
- Does `pathology_seg` alone predict scar/non-background in eval mode?
- Does current `_combine_compact_softmax` suppress non-background even when branch logits contain signal?
- Is collapse introduced by sliding-window aggregation/mirroring rather than direct full-slice forward?

## Export-only ablation modes

Add a config flag such as `CINE_COMBINE_MODE` and implement at least these modes without retraining:

- `current`: existing product rule.
- `cardiac_only`: export compact classes from cardiac ED logits only; ignore pathology head except class_3 is zero. This tests whether anatomy branch can recover class_1.
- `myocardium_gated_scar`: keep cardiac class_1/class_2 from cardiac logits; set class_3 as myocardium probability times pathology scar probability.
- `pathology_direct`: export class_3 from pathology argmax/probability while class_1/class_2 come from cardiac logits.

Run fold0 export/eval for each mode into isolated dirs, for example:

- `results/predictions/CineMyoPS_R4_current/fold_0`
- `results/predictions/CineMyoPS_R4_cardiac_only/fold_0`
- `results/predictions/CineMyoPS_R4_myo_gated_scar/fold_0`
- `results/metrics/unified/CineMyoPS_R4_<mode>/fold_0`

Use the round3 checkpoint:

```bash
FOLD=0 \
CINE_NNUNET_TASK=Task026_Cine_4D \
CINE_NNUNET_TRAINER=CARECineMyoPSTrainerBNCalib \
CINE_PRED_CHECKPOINT=model_final_checkpoint \
CINE_BN_RECALIBRATE=1 \
CINE_BN_RECALIB_BATCHES=32 \
CINE_COMBINE_MODE=<mode> \
CINE_OUTPUT_MODEL=CineMyoPS_R4_<mode> \
sbatch jobs/CineMyoPS/sbatch_export_eval.sh
```

Walltime should be <= 2h per export job. You may run modes sequentially or create a single 4h Slurm script that loops over modes and logs clearly.

## Success criteria

- If `cardiac_only` gives nonzero class_1 and better Dice, round5 should fix compact combination / branch semantics, not retrain.
- If direct eval forward has non-background but sliding-window export is all background, round5 should fix `predict_preprocessed_data_return_seg_and_softmax`.
- If eval direct forward is all background but train-mode direct forward is not, BN/normalization remains the bottleneck; consider replacing BN with GroupNorm/InstanceNorm in a new isolated trainer.
- If all modes remain all 0, stop CineMyoPS training and report the model path as not yet viable versus nnU-Net.

## Deliverables

- Code changes.
- New report: `docs/notes/CineMyoPS_improvement_round4.md`.
- Append `results/experiments/CineMyoPS_iteration_log.md`.
- Metrics for each `CINE_COMBINE_MODE`.
- A clear recommendation for round5: combination fix, sliding-window fix, normalization replacement, or stop.
