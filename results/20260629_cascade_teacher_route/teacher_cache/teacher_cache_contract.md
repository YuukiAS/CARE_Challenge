# Cascade Teacher Cache Preflight

Task: `prompts/tasks/20260629_cascade_teacher_route.md`

## Status

- This is a task-scoped cache/index preflight, not a formal cascade training result.
- Fold0 train cases: `176`.
- Fold0 validation cases: `44`.
- Train-side nnU-Net teacher predictions available: `176/176`.
- Validation nnU-Net teacher predictions available: `44/44`.
- Teacher mode: `oof5`.
- Train split cache rows use out-of-fold nnU-Net validation predictions when teacher mode is `oof5`.
- Validation split rows use existing `nnunet_fold0_validation_teacher` predictions.

## Decision

- Formal teacher/refiner training may use this cache only if train and validation teacher prediction coverage are both complete.
- Cropping logic must retain anatomy fallback/margins because validation teacher-derived ROIs miss some GT-positive scar rows.

## Artifacts

- `teacher_cache/case_index.csv`
- `teacher_cache/roi_coverage.csv`
- `teacher_cache/summary.json`
