# Manifest Cascade Postprocess Sweep

- Result: `results/20260629_cascade_teacher_route/revision_postprocess_sweep/result.md`
- Selection: `results/20260629_cascade_teacher_route/revision_postprocess_sweep/selection.md`
- Metrics summary: `results/20260629_cascade_teacher_route/revision_postprocess_sweep/metrics_summary.md`
- Sweep script: `scripts/evaluation/postprocess_cascade_revision_sweep.py`
- Source summaries:
  - `results/20260629_cascade_teacher_route/revision_postprocess_sweep/nnunet_pathology_teacher_srr_refiner_signal_seek_postprocess_summary.csv`
  - `results/20260629_cascade_teacher_route/revision_postprocess_sweep/coarse_to_fine_srr_roi_signal_seek_postprocess_summary.csv`
- Status: completed, no selected mode.

Variant roots are under:

- `results/20260629_cascade_teacher_route/revision_postprocess_sweep/variants/`

Each mode directory contains:

- postprocessed predictions under `predictions/<mode>/validation/`
- `round10_decision_table.md`
- `baseline_vs_refiner_by_subset.csv`
- `case_level_failure_flags.csv`
- `postprocess_components.csv`
