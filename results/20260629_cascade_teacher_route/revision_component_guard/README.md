# Cascade Component-Guard Revision

This isolated revision follows the failed formal cascade selection in
`results/20260629_cascade_teacher_route/selection.md`.

Status before launch:

- Formal cascade variants completed, but selection is `STOP_NO_CASCADE_SIGNAL`.
- The best formal positive deltas were tiny and component burden worsened.
- This revision tests a single follow-up hypothesis: more conservative
  residual magnitude and pathology thresholds may reduce remote/component false
  positives without relying on fold expansion or validation upload.

Planned array tasks:

| task | base variant | revision label | key change |
| --- | --- | --- | --- |
| 0 | `nnunet_pathology_teacher_srr_refiner` | `nnunet_pathology_teacher_srr_refiner_component_guard` | lower residual magnitude, higher edema/scar thresholds, wider hidden channels |
| 1 | `coarse_to_fine_srr_roi` | `coarse_to_fine_srr_roi_component_guard` | lower residual magnitude than formal ROI refiner, higher scar threshold, wider hidden channels |

Outputs stay under `results/20260629_cascade_teacher_route/revision_component_guard/variants/`.
They do not overwrite the formal cascade route artifacts.
