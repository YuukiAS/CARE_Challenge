# Cascade Teacher Artifact Contract

Task: `prompts/tasks/20260629_cascade_teacher_route.md`

## Current Teacher Artifacts

- `results/predictions/nnUNet501/fold_0/` exists as fold0 validation predictions only.
- `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation/` also contains fold0 validation predictions only.
- Dataset501 fold0 split has `176` train cases and `44` validation cases.
- Available teacher coverage checked this turn:
  - train predictions from fold0-only teacher: `0/176`
  - train predictions from OOF-5 teacher cache: `176/176`
  - validation predictions: `44/44`
- Task-scoped cache preflight now exists under `results/20260629_cascade_teacher_route/teacher_cache/`.
- Cache preflight rows:
  - `case_index.csv`: `220` cases plus header (`176` train, `44` validation)
  - `roi_coverage.csv`: `1100` class rows plus header
  - teacher mode: `oof5`
  - train prior source: `nnunet_oof5_validation_teacher`
  - validation prior source: `nnunet_fold0_validation_teacher`
- ROI audit found `26` GT-positive class rows with coverage `<0.95`, mostly scar teacher-mask misses. Formal cascade crops must include anatomy fallback/margins and cannot hard crop only to teacher pathology masks.

## Safety Decision

Do not launch formal cascade/refiner training using `nnUNet501/fold_0` as the sole teacher cache, because it is validation-only. The task-scoped OOF-5 cache is the safe teacher source for fold0 train/refiner work: fold0 train rows use folds 1-4 validation exports, and fold0 validation rows use fold0 validation exports.

## Allowed Next Steps

1. Launch an OOF-5 teacher-cache mechanism smoke or formal fold0 cascade variant using `teacher_cache/case_index.csv`.
2. Keep ROI/crop logic teacher-safe: use soft probabilities/anatomy support and margins; do not hard-delete pathology outside teacher masks.
3. Formal variants to launch when GPU capacity is available:
   - `nnunet_anatomy_prior_refiner`
   - `nnunet_pathology_teacher_srr_refiner`
   - `coarse_to_fine_srr_roi`

## Reference Metrics

- nnU-Net501 fold0 Dice reference: edema class_4 `0.7798`, scar class_5 `0.5602` from `results/metrics/unified/nnUNet501/fold_0/evaluation_summary.json`.

This contract blocks only premature formal cascade training; it does not block repaired proposal or SRR-v2 jobs.
