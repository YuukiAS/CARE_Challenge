# Result Cascade Component-Guard Revision

Status: completed; no component-guard variant selected.

## What Was Done

- Submitted `jobs/src/run_cascade_oof_refiner_revision_component_guard.sh` as
  Slurm job `57274444_[0-1]` on `htzhulab`.
- Ran two isolated follow-up variants under
  `results/20260629_cascade_teacher_route/revision_component_guard/variants/`:
  - `nnunet_pathology_teacher_srr_refiner_component_guard`
  - `coarse_to_fine_srr_roi_component_guard`
- Both jobs completed with exit code `0:0` in `00:02:46`.
- Both variants exported validation predictions and wrote summary, metrics, and
  decision tables.

## Result

The component-guard revision did not rescue the cascade route.

- `nnunet_pathology_teacher_srr_refiner_component_guard` produced zero deltas.
- `coarse_to_fine_srr_roi_component_guard` produced only `+0.0002` T2-positive
  edema Dice, worsened T2-positive edema HD95 by `-0.0092`, and left scar Dice
  unchanged.
- The coarse-to-fine guard still had component-worse cases (`Case3034`,
  `Case3044`).

Selection: `STOP_NO_COMPONENT_GUARD_SIGNAL`.

## Implication

The formal cascade route and this narrower component-guard revision both failed
to produce a material MyoPS rescue signal. Current mainline completion still
depends on the SRR-v2 missing variants and their aggregation.

No validation upload, upload-ready package, fold expansion, evaluator change, or
label mapping change was performed.
