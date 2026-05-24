# CineMyoPS improvement round4: inference semantics and combine-mode ablations

Date: 2026-05-17

## Scope

- Followed the prompt4 constraint: no new training in this round.
- Fold0 only, no 5-fold expansion, no official validation submission.
- Main hypothesis: round3 online eval was nonzero while exported validation predictions were all background, so the failure may be in inference semantics, sliding-window aggregation, softmax combination, or export label mapping.

## Round3 completed context

- Round3 BNCalib isolated train job: `51264136`
- Log: `logs/CineMyoPS_e2e_51264136_20260517_051831.log`
- Actual train+export+eval pipeline seconds: `7667`
- Export checkpoint: `data/nnUNet/nnUNet_results/nnUNet/2d/Task026_Cine_4D/CARECineMyoPSTrainerBNCalib__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model`
- Fold0 protocol eval output: `results/metrics/unified/CineMyoPS_BNCalib/fold_0/evaluation_summary.json`
- Result: `class_1=0.000000`, `class_2=0.000000`, `class_3=0.000000`, `foreground_mean=0.000000`.
- Interpretation: training-loop online eval cannot be trusted until the inference path is debugged.

## Code changes

- `third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py`
  - Added `CINE_COMBINE_MODE`.
  - Supported modes:
    - `current`: existing product rule.
    - `cardiac_only`: compact class 1/2 from cardiac ED logits, class 3 zero.
    - `myocardium_gated_scar`: cardiac myocardium split by pathology scar probability.
    - `pathology_direct`: class 1/2 from cardiac logits, class 3 from pathology scar probability.
- `code/CineMyoPS/export_protocol_val_predictions.sh`
  - Logs `CINE_COMBINE_MODE`.
- `jobs/CineMyoPS/sbatch_export_eval.sh`
  - Logs `CINE_COMBINE_MODE`.
- `scripts/evaluation/debug_cinemyops_inference_semantics.py`
  - New diagnostic script to load round3 BNCalib fold0 checkpoint and inspect 3 protocol-val cases plus 1 train case.
  - Reports raw/preprocessed shapes, label counts, direct eval/train forward branch stats, current and ablation combine argmax counts, sliding-window no-TTA/no-gaussian output, and exported NIfTI unique labels.
- `jobs/CineMyoPS/sbatch_round4_debug.sh`
  - Short GPU Slurm wrapper for the diagnostic script.
- `jobs/CineMyoPS/sbatch_round4_ablation.sh`
  - 4-hour export-only Slurm wrapper that runs all combine modes sequentially.

## Checks

```bash
./env_CARE_nnUNet_v1/bin/python -m py_compile \
  third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py \
  scripts/evaluation/debug_cinemyops_inference_semantics.py
bash -n code/CineMyoPS/export_protocol_val_predictions.sh
bash -n jobs/CineMyoPS/sbatch_export_eval.sh
bash -n jobs/CineMyoPS/sbatch_round4_debug.sh
bash -n jobs/CineMyoPS/sbatch_round4_ablation.sh
```

All checks passed.

## Local diagnostic attempt

```bash
./env_CARE_nnUNet_v1/bin/python scripts/evaluation/debug_cinemyops_inference_semantics.py
```

- Stop reason: killed with exit code `137` after model restore started.
- Additional issue: local shell did not source `env_nnunet.sh`, so nnU-Net path warnings were emitted.
- Action: moved the diagnostic to a GPU Slurm job, consistent with AGENTS compute guidance.

## Submitted Slurm jobs

### Debug inference semantics

```bash
sbatch jobs/CineMyoPS/sbatch_round4_debug.sh
```

- Job: `51268602`
- Walltime: `02:00:00`
- Status at note time: `PENDING (Resources)`
- Expected output: `results/diagnostics/baseline_paper_models/CineMyoPS/round04_inference_semantics/inference_semantics.json`

### Combine-mode export-only ablations

```bash
sbatch jobs/CineMyoPS/sbatch_round4_ablation.sh
```

- Job: `51268612`
- Walltime: `04:00:00`
- Status at note time: `PENDING (Priority)`
- Uses:
  - `FOLD=0`
  - `CINE_NNUNET_TASK=Task026_Cine_4D`
  - `CINE_NNUNET_TRAINER=CARECineMyoPSTrainerBNCalib`
  - `CINE_PRED_CHECKPOINT=model_final_checkpoint`
  - `CINE_BN_RECALIBRATE=1`
  - `CINE_BN_RECALIB_BATCHES=32`

Expected output dirs:

| Combine mode | Prediction dir | Metric JSON |
| --- | --- | --- |
| `current` | `results/predictions/CineMyoPS_R4_current/fold_0` | `results/metrics/unified/CineMyoPS_R4_current/fold_0/evaluation_summary.json` |
| `cardiac_only` | `results/predictions/CineMyoPS_R4_cardiac_only/fold_0` | `results/metrics/unified/CineMyoPS_R4_cardiac_only/fold_0/evaluation_summary.json` |
| `myocardium_gated_scar` | `results/predictions/CineMyoPS_R4_myo_gated_scar/fold_0` | `results/metrics/unified/CineMyoPS_R4_myo_gated_scar/fold_0/evaluation_summary.json` |
| `pathology_direct` | `results/predictions/CineMyoPS_R4_pathology_direct/fold_0` | `results/metrics/unified/CineMyoPS_R4_pathology_direct/fold_0/evaluation_summary.json` |

## Completed interpretation

Round4 combine-mode ablations completed, but every export-only mode still produced all-background validation metrics:

| mode | class_1 myocardium | class_2 LV | class_3 scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| `current` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `cardiac_only` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `myocardium_gated_scar` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `pathology_direct` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

This means compact-combination choice alone is not the fix. The remaining blocker is whether useful logits exist before sliding-window/export. The first debug script failed due a wrong 2D slice/patch selection, so a fixed diagnostic is now prepared:

```bash
sbatch jobs/CineMyoPS/sbatch_round5_debug_fixed.sh
```

Expected output:

- `results/diagnostics/baseline_paper_models/CineMyoPS/round05_fixed_inference/inference_semantics_fixed.json`

Do not launch another CineMyoPS training run until this diagnostic separates direct-logit collapse from inference/export collapse.
