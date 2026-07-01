# Cascade Signal-Seek Revision Selection

status: `STOP_NO_SIGNAL_SEEK_ROUTE`
selected_variant: `none`

## Reasons

- `nnunet_pathology_teacher_srr_refiner_signal_seek` remained
  `fail_stop_refiner_candidate`.
- `coarse_to_fine_srr_roi_signal_seek` remained `fail_stop_refiner_candidate`.
- The stronger residual settings produced only tiny Dice movement while
  worsening HD95, edema component burden, and remote false positives.
- The failure mode is not under-editing alone; relaxing thresholds and residual
  limits increases harmful components faster than useful pathology signal.

No validation upload, upload-ready package, fold expansion, evaluator change, or
label mapping change was performed.
