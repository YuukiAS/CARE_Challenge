# Manifest 20260629 Cascade Teacher Route

- Task: `prompts/tasks/20260629_cascade_teacher_route.md`
- Result: `results/20260629_cascade_teacher_route/result.md`
- Selection: `results/20260629_cascade_teacher_route/selection.md`
- Metrics summary: `results/20260629_cascade_teacher_route/metrics_summary.md`
- Failure interpretation: `results/20260629_cascade_teacher_route/failure_interpretation.md`

## Scripts And Entrypoints

- Cache preflight script: `scripts/evaluation/preflight_cascade_teacher_cache.py`
- Train teacher inference wrapper: `jobs/src/run_cascade_teacher_train_inference.sh`
- OOF cascade refiner wrapper: `jobs/src/run_cascade_oof_refiner.sh`
- Component-guard revision wrapper:
  `jobs/src/run_cascade_oof_refiner_revision_component_guard.sh`
- Cascade finalizer: `scripts/evaluation/finalize_cascade_teacher_route.py`

## Teacher Cache

- Teacher artifact contract:
  `results/20260629_cascade_teacher_route/teacher_artifact_contract.md`
- Resource audit: `results/20260629_cascade_teacher_route/resource_audit.md`
- Cache contract:
  `results/20260629_cascade_teacher_route/teacher_cache/teacher_cache_contract.md`
- Cache case index:
  `results/20260629_cascade_teacher_route/teacher_cache/case_index.csv`
- Cache ROI coverage:
  `results/20260629_cascade_teacher_route/teacher_cache/roi_coverage.csv`
- Cache summary:
  `results/20260629_cascade_teacher_route/teacher_cache/summary.json`
- Teacher cache metrics:
  `results/20260629_cascade_teacher_route/teacher_cache_metrics.csv`
- Teacher cache metrics summary:
  `results/20260629_cascade_teacher_route/teacher_cache_metrics_summary.md`

## Formal Outputs

- Aggregation status:
  `results/20260629_cascade_teacher_route/aggregation_status.md`
- Aggregation status CSV:
  `results/20260629_cascade_teacher_route/aggregation_status.csv`
- Subgroup metrics:
  `results/20260629_cascade_teacher_route/subgroup_metrics.csv`
- Component/HD case table:
  `results/20260629_cascade_teacher_route/component_hd_by_case.csv`
- Teacher-student delta:
  `results/20260629_cascade_teacher_route/teacher_student_delta.csv`
- ROI coverage:
  `results/20260629_cascade_teacher_route/roi_coverage.csv`
- Variant matrix:
  `results/20260629_cascade_teacher_route/variant_matrix.md`

Formal variant roots:

- `results/20260629_cascade_teacher_route/variants/nnunet_anatomy_prior_refiner/`
- `results/20260629_cascade_teacher_route/variants/nnunet_pathology_teacher_srr_refiner/`
- `results/20260629_cascade_teacher_route/variants/coarse_to_fine_srr_roi/`

Formal Slurm evidence:

- job: `57272502_[0-2]`
- partition: `htzhulab`
- result: `COMPLETED`
- each variant exported `44/44` validation predictions.

## Revision Outputs

- Revision plan:
  `results/20260629_cascade_teacher_route/revision_component_guard/README.md`
- Revision root:
  `results/20260629_cascade_teacher_route/revision_component_guard/`
- Revision job: `57274444_[0-1]`
- Revision status: completed, selection `STOP_NO_COMPONENT_GUARD_SIGNAL`
- Signal-seek revision root:
  `results/20260629_cascade_teacher_route/revision_signal_seek/`
- Signal-seek revision job: `57275246_[0-1]`
- Signal-seek revision status: completed, selection `STOP_NO_SIGNAL_SEEK_ROUTE`
- Postprocess sweep root:
  `results/20260629_cascade_teacher_route/revision_postprocess_sweep/`
- Postprocess sweep status: completed, selection `STOP_NO_POSTPROCESS_ROUTE`

## Current State

The formal cascade route is complete but not selected:

- route status: `STOP_NO_CASCADE_SIGNAL`
- selected variant: `none`
- reason: all formal variants reported `fail_stop_refiner_candidate`; tiny
  positive deltas are not route-selection evidence.

The component-guard, signal-seek, and postprocess revisions are follow-up
failure-recovery attempts and do not overwrite the formal cascade artifacts.
