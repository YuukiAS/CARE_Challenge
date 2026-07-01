# Cascade Component-Guard Revision Selection

status: `STOP_NO_COMPONENT_GUARD_SIGNAL`
selected_variant: `none`

## Reasons

- `nnunet_pathology_teacher_srr_refiner_component_guard` produced zero metric
  deltas and was evaluated as `watch_stop_no_clear_positive_signal`.
- `coarse_to_fine_srr_roi_component_guard` produced only a tiny edema Dice
  delta (`+0.0002`) and was evaluated as `fail_stop_refiner_candidate`.
- The coarse-to-fine guard still had component-worse cases (`Case3034`,
  `Case3044`).

No validation upload, upload-ready package, fold expansion, evaluator change, or
label mapping change was performed.
