# U-MyoPS (CARE baseline)

All CARE-side U-MyoPS preparation, training wrappers, and **Stage 2 validation export** for unified evaluation live here. Slurm orchestration remains under [`jobs/U-MyoPS/`](../../jobs/U-MyoPS/).

## Typical flow

1. **`prepare_u_myops_from_care.py`** — CARE → upstream `jrs` dataloader layout.
2. **`run_stage1.sh`** — registration + myocardium (upstream `joint_registration_myocardium_segmentation.py`).
3. **`build_stage2_task_from_stage1.py`** + **`prepare_stage2_task.sh`** — fold-specific nnU-Net v1 **Task901** raw labels and preprocessing from Stage 1 outputs.
4. **`run_stage2.sh`** — Stage 2 pathology nnU-Net training (`pathology_segmentation_train.py`).
5. **`export_stage2_val_predictions.py`** — remap Stage 2 nnU-Net labels `{0,1,2}` → CARE Dataset501 compact `{0,4,5}` for `scripts/evaluation/evaluate_predictions.py` (`4` = myops_edema, `5` = myops_scar). Invoked by `scripts/evaluation/run_unified_eval_model.sh` when evaluating **U-MyoPS**.

If the nnU-Net `fold_*/validation_raw` folder is missing under `third_party/.../output`, the exporter runs fallback inference into `results/predictions/_tmp/U-MyoPS/fold_<k>/validation_raw/`. On a later run, if that cache already contains **all** val-case `Case*.nii.gz`, the script **reuses** it and only performs remap (no GPU re-inference). Delete `_tmp/U-MyoPS/fold_<k>` to force a fresh inference pass.

## Environment

See **`env.example.sh`** and `jobs/U-MyoPS/run.sh` / `env_nnunet.sh` for `CARE_ROOT`, `CARE_CineMyoPS_ENV`, and nnU-Net v1 paths under `third_party/U-MyoPS_myops/outputs/nnunet/`.

## Other utilities

- **`prepare_stage1_layout.sh`** — layout helper for Stage 1.
- **`clamp_stage2_plans_batch_size.py`** — optional batch-size clamp on generated plans.

There is **no** `scripts/U-MyoPS/` tree in this repository; do not reintroduce duplicate export paths.
