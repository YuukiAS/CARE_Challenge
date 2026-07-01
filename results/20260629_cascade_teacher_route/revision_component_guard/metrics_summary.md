# Cascade Component-Guard Revision Metrics Summary

Status: `STOP_NO_COMPONENT_GUARD_SIGNAL`
Selected variant: `none`
Ready variants: `2/2`
Slurm job: `57274444_[0-1]`

| variant | eval decision | delta T2+ edema Dice | delta T2+ edema HD95 | delta edema component count improvement | delta edema remote FP improvement | delta all scar Dice | delta all scar HD95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `nnunet_pathology_teacher_srr_refiner_component_guard` | `watch_stop_no_clear_positive_signal` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `coarse_to_fine_srr_roi_component_guard` | `fail_stop_refiner_candidate` | 0.0002 | -0.0092 | 0.0625 | 0.0625 | 0.0000 | 0.0000 |

Values are read from each revision variant's `round10_decision_table.md`.
The table uses the T2-present GT-positive row for edema and the all-case row
for scar.

## Interpretation

The component-guard hypothesis did not produce a usable rescue signal. The
pathology-teacher guard made no measurable change. The coarse-to-fine guard
slightly reduced component/remote FP counts on the T2-positive subset, but Dice
gain was only `+0.0002`, HD95 worsened, scar remained unchanged, and case-level
component-worse reasons persisted.
