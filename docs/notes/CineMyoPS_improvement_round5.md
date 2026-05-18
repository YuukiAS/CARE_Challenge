# CineMyoPS improvement round5: fixed inference semantics

Date: 2026-05-17

## Scope

- Followed prompt5: no new training, fold0 only, no official validation submission.
- Main hypothesis: round4 all-background exports were caused by inference semantics, not necessarily by unusable branch logits.

## Inputs reviewed

- `docs/notes/CineMyoPS_improvement_round4.md`
- `results/experiments/CineMyoPS_iteration_log.md`
- `prompts/CineMyoPS/prompt4_inference_semantics.md`
- `prompts/Baseline_report.md`
- `results/metrics/nnUNet.md`
- `jobs/CineMyoPS/README.md`

## Diagnostic

Command:

```bash
sbatch jobs/CineMyoPS/sbatch_round5_debug_fixed.sh
```

- Job: `51354672`
- Log: `logs/CineMyoPS_r5_debug_51354672_20260517_232602.log`
- Output: `results/diagnostics/CineMyoPS_round5/inference_semantics_fixed.json`
- BN recalibration: 32 batches, 56 BN layers, 3.23 s.

Key finding:

- Direct eval forward predicted non-background myocardium/LV/scar-like compact outputs on selected slices.
- Direct train-mode forward was also non-empty and similar to eval mode.
- Current compact combination also produced non-background on direct slices.
- Sliding-window `predict_preprocessed_data_return_seg_and_softmax(... do_mirroring=False, use_gaussian=False)` was all background.
- Exported NIfTI predictions before the fix were all background.

Conclusion: this was a **sliding-window inference axis bug**, not direct logits collapse and not export label collapse.

## Code fix

File: `third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py`

- `predict_preprocessed_data_return_seg_and_softmax` previously assumed the 2D slice axis was the last spatial axis.
- Task026 preprocessed data is shaped `(T, X, Y, Z)` and the network patch is `(T, H, W)`, so the correct fold0 slice axis is `X` for the common `(T, small_slices, 256, 256)` cases.
- Added `_infer_slice_and_inplane_axes(...)` and now slice axis is inferred from `data.shape[1:]` and `trainer.patch_size`.

Checks:

```bash
./env_CARE_nnUNet_v1/bin/python -m py_compile \
  third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py \
  scripts/evaluation/debug_cinemyops_inference_semantics.py
bash -n jobs/CineMyoPS/sbatch_export_eval.sh
```

Both checks passed.

## Fixed export/eval

Command:

```bash
FOLD=0 \
CINE_NNUNET_TASK=Task026_Cine_4D \
CINE_NNUNET_TRAINER=CARECineMyoPSTrainerBNCalib \
CINE_OUTPUT_MODEL=CineMyoPS_R5_fixed_inference \
CINE_PRED_CHECKPOINT=model_final_checkpoint \
CINE_BN_RECALIBRATE=1 \
CINE_BN_RECALIB_BATCHES=32 \
CINE_COMBINE_MODE=current \
sbatch jobs/CineMyoPS/sbatch_export_eval.sh
```

- Job: `51354763`
- Log: `logs/CineMyoPS_export_eval_51354763_20260517_232845.log`
- Prediction dir: `results/predictions/CineMyoPS_R5_fixed_inference/fold_0`
- Metric JSON: `results/metrics/unified/CineMyoPS_R5_fixed_inference/fold_0/evaluation_summary.json`
- Global prediction label counts: `{0: 7267139, 1: 59011, 2: 123664, 3: 58438}` over 13 fold0 protocol val cases.

## Metrics

| variant | class_1 myocardium | class_2 LV | class_3 scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| nnU-Net Dataset502 5-fold reference | 0.6808 | 0.8874 | 0.2586 | - |
| round4 `current` before fix | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| round5 fixed inference, fold0 | 0.6067 | 0.9305 | 0.3942 | 0.6438 |

## Recommendation

Round5 proves the existing round3 BNCalib checkpoint can produce useful fold0 protocol predictions once inference slicing is fixed. Next round may continue with export/inference validation and cache isolation; training is allowed only after confirming the fixed inference path remains stable and comparing the right checkpoint/mode. Do not expand folds 1-4 until fixed fold0 outputs and label semantics are accepted as the new baseline.
