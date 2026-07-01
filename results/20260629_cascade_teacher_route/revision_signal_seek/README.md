# Cascade Signal-Seek Revision

This isolated revision follows two negative cascade results:

- Formal cascade route: `STOP_NO_CASCADE_SIGNAL`
- Component-guard revision: `STOP_NO_COMPONENT_GUARD_SIGNAL`

Hypothesis:

The formal cascade variants may be under-editing the nnU-Net teacher, while the
component-guard revision was too conservative. This revision deliberately tests
a bounded signal-seeking setting with wider hidden channels, larger allowed
residual magnitude, and lower pathology thresholds.

Planned array tasks:

| task | base variant | revision label | key change |
| --- | --- | --- | --- |
| 0 | `nnunet_pathology_teacher_srr_refiner` | `nnunet_pathology_teacher_srr_refiner_signal_seek` | wider residual head, larger residual cap, lower thresholds |
| 1 | `coarse_to_fine_srr_roi` | `coarse_to_fine_srr_roi_signal_seek` | wider residual head, larger residual cap, lower thresholds |

Outputs stay under `results/20260629_cascade_teacher_route/revision_signal_seek/variants/`.
They do not overwrite the formal cascade or component-guard artifacts.

This revision is not a route selection. It is a bounded failure-recovery probe to
distinguish under-editing from component-control failure.
