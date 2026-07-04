# Exact Code Used By Slurm 57782211

## Head And Job

- reviewed `HEAD`: `39f9a573b1db33bbf99880d63c0d40a9cd7a1d8e`
- job script: `jobs/src/run_myops_anchor_srr_fold0_formal.sh`
- Slurm job name: `MyoPSAnchorSRRF0`
- parent/array job recorded by prior result: `57782211`
- observed completed task job IDs:
  - `57782213`: `srr_propref_shared_dual_dict`, array task 0
  - `57782214`: `srr_propref_scar_precision`, array task 1
  - `57782211`: `srr_propref_no_proto_cascade`, array task 2

## Job Script Contract

`jobs/src/run_myops_anchor_srr_fold0_formal.sh` sets:

- `CARE_ROOT=/users/a/e/aereinh/CARE`
- sources `.care-codex-env.sh` and `env_nnunet.sh`
- `MAX_STEPS=24000` default
- `VAL_EVERY=600` default
- `max_runtime_seconds=25200`
- `min_effective_optimizer_steps=1500`
- `min_effective_train_loop_seconds=1800`
- `nnunet_anchor_root=/users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres`

The script invokes:

```bash
python scripts/training/run_srr_propref_myops_fold0.py \
  --variant "${VARIANT}" \
  --fold 0 \
  --device cuda \
  --base-channels "${BASE_CHANNELS:-32}" \
  --patch-shape "${PATCH_SHAPE:-12,96,96}" \
  --batch-size "${BATCH_SIZE:-2}" \
  --max-steps "${MAX_STEPS_VALUE}" \
  --max-runtime-seconds 25200 \
  --val-every "${VAL_EVERY_VALUE}" \
  --early-stop-patience "${EARLY_STOP_PATIENCE:-8}" \
  --early-stop-min-delta "${EARLY_STOP_MIN_DELTA:-0.001}" \
  --min-optimizer-steps-for-plateau 1500 \
  --min-train-loop-seconds-for-plateau 1800 \
  --nnunet-anchor-root "${NNUNET_ANCHOR_ROOT:-${CARE_ROOT}/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres}" \
  --proposal-thresholds "${PROPOSAL_THRESHOLDS:-0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90}" \
  --scar-decode-threshold "${SCAR_DECODE_THRESHOLD:-0.50}" \
  --edema-decode-threshold "${EDEMA_DECODE_THRESHOLD:-0.50}" \
  --out-root "${OUT_ROOT}" \
  --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv
```

## Per-Variant Runtime Configs

- `results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_shared_dual_dict/configs/run_config.env`: `job_id=57782213`, `array_task_id=0`, `formal_variant=anchored_srr_v25_full`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_scar_precision/configs/run_config.env`: `job_id=57782214`, `array_task_id=1`, `formal_variant=anchored_scar_precision_edema_safe`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_no_proto_cascade/configs/run_config.env`: `job_id=57782211`, `array_task_id=2`, `formal_variant=anchored_conservative_cascade_no_proto_or_frozen_proto`

## Log Status

Found logs:

- `logs/MyoPSAnchorSRRF0_0_57782213_20260704_022627.log`
- `logs/MyoPSAnchorSRRF0_1_57782214_20260704_022627.log`
- `logs/MyoPSAnchorSRRF0_2_57782211_20260704_022627.log`

All three are 0 bytes. They do not contain command output or training transcript.

