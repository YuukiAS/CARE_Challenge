# Result 20260629 Cascade Teacher Route

Status: formal cascade route completed; no formal variant selected.

## What Was Done

- Built and verified an OOF-5 nnU-Net teacher cache for Dataset501 fold0:
  `176/176` train rows and `44/44` validation rows have teacher predictions.
- Added `jobs/src/run_cascade_oof_refiner.sh` with three isolated formal
  variants:
  - `nnunet_anatomy_prior_refiner`
  - `nnunet_pathology_teacher_srr_refiner`
  - `coarse_to_fine_srr_roi`
- Added the cascade finalizer at
  `scripts/evaluation/finalize_cascade_teacher_route.py`.
- Submitted the formal cascade array on `htzhulab` as job `57272502_[0-2]`.
- All three formal tasks completed successfully on 2026-07-01 with `44/44`
  validation predictions per variant.
- Re-ran the route finalizer after completion. It wrote route-level metrics,
  selection, and case/component evidence under
  `results/20260629_cascade_teacher_route/`.

## Result

The formal cascade route did not produce a material improvement over the
teacher/reference baseline.

| variant | eval decision | delta T2+ edema Dice | delta T2+ edema HD95 | delta all scar Dice | delta all scar HD95 |
| --- | --- | ---: | ---: | ---: | ---: |
| `nnunet_anatomy_prior_refiner` | `fail_stop_refiner_candidate` | 0.0014 | -0.0276 | 0.0000 | 0.0000 |
| `nnunet_pathology_teacher_srr_refiner` | `fail_stop_refiner_candidate` | 0.0006 | 0.0033 | 0.0000 | 0.0000 |
| `coarse_to_fine_srr_roi` | `fail_stop_refiner_candidate` | 0.0019 | -0.0626 | 0.0028 | -0.4037 |

The route selection is:

- `selection.md` status: `STOP_NO_CASCADE_SIGNAL`
- selected variant: `none`

The small positive deltas are not treated as selection evidence because all
formal variants reported `fail_stop_refiner_candidate` and the component/HD
evidence does not show a robust rescue signal.

## Failure Interpretation

The OOF teacher cache and export/evaluation path are no longer blockers. The
negative result points to the refiner behavior itself: with the current residual
training/thresholding, the model mostly preserves the teacher and only produces
tiny changes. Where it changes pathology, the gain is too small to justify the
added component burden risk.

This is not a reason to stop the overall goal. It narrows the next hypothesis:
the cascade refiner needs stricter component control or a different residual
calibration, not more blind fold expansion.

## Follow-Up Results

After this formal route failed to provide a usable signal, three isolated
follow-ups were run:

- component-guard revision:
  - wrapper: `jobs/src/run_cascade_oof_refiner_revision_component_guard.sh`
  - job: `57274444_[0-1]`
  - status: `STOP_NO_COMPONENT_GUARD_SIGNAL`
  - output root:
  `results/20260629_cascade_teacher_route/revision_component_guard/`
- signal-seek revision:
  - wrapper: `jobs/src/run_cascade_oof_refiner_revision_signal_seek.sh`
  - job: `57275246_[0-1]`
  - status: `STOP_NO_SIGNAL_SEEK_ROUTE`
  - output root:
    `results/20260629_cascade_teacher_route/revision_signal_seek/`
- postprocess sweep:
  - script: `scripts/evaluation/postprocess_cascade_revision_sweep.py`
  - status: `STOP_NO_POSTPROCESS_ROUTE`
  - output root:
    `results/20260629_cascade_teacher_route/revision_postprocess_sweep/`

Revision variants included:

  - `nnunet_pathology_teacher_srr_refiner_component_guard`
  - `coarse_to_fine_srr_roi_component_guard`
  - `nnunet_pathology_teacher_srr_refiner_signal_seek`
  - `coarse_to_fine_srr_roi_signal_seek`

The follow-ups tested stricter residual magnitude, stronger residual
signal-seeking, and component pruning. None produced a selectable signal. The
mechanism is now clearer: tighter settings produce near-zero changes, while
looser settings increase harmful components/remote false positives faster than
they improve Dice.

No validation upload, upload-ready package, fold expansion, evaluator change, or
label mapping change was performed.
