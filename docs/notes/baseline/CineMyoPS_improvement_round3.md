# CineMyoPS improvement round3: BN recalibration and fold0 budget run

Date: 2026-05-17

## Scope

- Followed the iterative model-improvement rule: fold0 only, no 5-fold expansion, no official validation submission, single Slurm jobs <= 8h.
- Main hypothesis: round2 eval-mode collapse is caused by stale/poor BatchNorm running statistics. Recalibrate BN on training batches, then predict in normal eval mode.

## Code changes

- `third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py`
  - Added `CINE_BN_RECALIBRATE=1` / `CINE_BN_RECALIB_BATCHES` eval-time BN recalibration.
  - The pass runs once per restored trainer, uses fold training batches, `torch.no_grad()`, no optimizer step, then restores eval-mode prediction.
  - Calibration input is center-cropped/padded to the trainer final `patch_size` to match the training forward shape.
- `third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainerBNCalib.py`
  - Added isolated trainer class so fold0 training writes to a separate checkpoint directory.
- `code/CineMyoPS/export_protocol_val_predictions.sh`
  - Added `CINE_OUTPUT_MODEL` so prediction directories are config-specific.
- `jobs/CineMyoPS/sbatch_export_eval.sh`, `jobs/CineMyoPS/run_task026_paper_steps.sh`, `jobs/CineMyoPS/sbatch_fold0_pipeline.sh`
  - Added `CINE_OUTPUT_MODEL` for config-specific metric and prediction directories.
  - Logged BN recalibration env vars.

## Checks

```bash
bash -n code/CineMyoPS/export_protocol_val_predictions.sh
bash -n jobs/CineMyoPS/sbatch_export_eval.sh
bash -n jobs/CineMyoPS/run_task026_paper_steps.sh
bash -n jobs/CineMyoPS/sbatch_fold0_pipeline.sh
./env_CARE_nnUNet_v1/bin/python -m py_compile \
  third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py \
  third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainerBNCalib.py
```

All checks passed.

## Export-only BN recalibration validation

First attempt:

```bash
FOLD=0 \
CINE_NNUNET_TASK=Task026_Cine_4D \
CINE_NNUNET_TRAINER=CARECineMyoPSTrainer \
CINE_OUTPUT_MODEL=CineMyoPS_BNRecalibExport \
CINE_PRED_CHECKPOINT=model_final_checkpoint \
CINE_BN_RECALIBRATE=1 \
CINE_BN_RECALIB_BATCHES=32 \
sbatch jobs/CineMyoPS/sbatch_export_eval.sh
```

- Job: `51264134`
- Log: `logs/CineMyoPS_export_eval_51264134_20260517_051828.log`
- Stop reason: failed during BN recalibration because the raw basic DataLoader batch used pre-augmentation patch size, causing motion decoder tensor-size mismatch.
- Action: canceled failed/stuck job and fixed calibration input crop/pad.

Second attempt:

```bash
FOLD=0 \
CINE_NNUNET_TASK=Task026_Cine_4D \
CINE_NNUNET_TRAINER=CARECineMyoPSTrainer \
CINE_OUTPUT_MODEL=CineMyoPS_BNRecalibExport_v2 \
CINE_PRED_CHECKPOINT=model_final_checkpoint \
CINE_BN_RECALIBRATE=1 \
CINE_BN_RECALIB_BATCHES=32 \
sbatch jobs/CineMyoPS/sbatch_export_eval.sh
```

- Job: `51264154`
- Log: `logs/CineMyoPS_export_eval_51264154_20260517_052113.log`
- Evidence: BN recalibration completed before eval-mode prediction:
  - requested batches: 32
  - actual batches: 32
  - BN layers: 56
  - elapsed: 2.57 s
- Prediction/metric output:
  - `results/predictions/CineMyoPS_BNRecalibExport_v2/fold_0`
  - `results/metrics/unified/CineMyoPS_BNRecalibExport_v2/fold_0/evaluation_summary.json`
- Stop reason: export/eval completed.
- Prediction labels: 13/13 predictions contain only label `0`.
- Metrics: `class_1=0.000000`, `class_2=0.000000`, `class_3=0.000000`, `foreground_mean=0.000000`.
- Interpretation: BN recalibration alone does not rescue the old 2026-05-12 checkpoint in normal eval mode.

## Fold0 budget train+export+eval

```bash
FOLD=0 \
CINE_NNUNET_TASK=Task026_Cine_4D \
CINE_NNUNET_TRAINER=CARECineMyoPSTrainerBNCalib \
CINE_OUTPUT_MODEL=CineMyoPS_BNCalib \
CINE_NNUNET_EPOCHS=200 \
CINE_SKIP_PREPARE=1 \
CINE_RUN_EXPORT_EVAL=1 \
CINE_BN_RECALIBRATE=1 \
CINE_BN_RECALIB_BATCHES=32 \
CINE_PRED_CHECKPOINT=model_final_checkpoint \
sbatch jobs/CineMyoPS/sbatch_fold0_pipeline.sh
```

- Job: `51264136`
- Log: `logs/CineMyoPS_e2e_51264136_20260517_051831.log`
- Walltime: 8h Slurm limit.
- Actual epochs: pending; job is running.
- Checkpoint directory: `data/nnUNet/nnUNet_results/nnUNet/2d/Task026_Cine_4D/CARECineMyoPSTrainerBNCalib__nnUNetPlansv2.1/fold_0`
- Prediction output after training: `results/predictions/CineMyoPS_BNCalib/fold_0`
- Metric output after training: `results/metrics/unified/CineMyoPS_BNCalib/fold_0/evaluation_summary.json`
- Early online eval evidence from the training log:
  - epoch 6 foreground Dice estimate `[0.5838495, 0.8609002, 0.30024827]`
  - epoch 18 foreground Dice estimate `[0.5591354, 0.8679081, 0.33099163]`
  - This is training-loop online eval only, not the final protocol metric.

## Pending update

When `51264136` finishes, record actual epochs, checkpoint used/exported, stop reason, final prediction label stats, and protocol fold0 metrics before considering any folds 1-4.
