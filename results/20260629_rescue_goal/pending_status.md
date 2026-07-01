# 20260629 Rescue Goal Pending Status

This is a status snapshot, not a final route selection.

## Ready Rows

- ready_to_aggregate rows: `9`
- missing/pending rows: `2`

## Route Matrix

| route | variant | selection/status | summary | predictions | ready |
| --- | --- | --- | ---: | ---: | ---: |
| repaired_proposal | repaired_uncertainty_hardneg | status: `ROUTE_TO_CASCADE_TEACHER` | True | True | True |
| repaired_proposal | repaired_posneg_scar_hardneg | status: `ROUTE_TO_CASCADE_TEACHER` | True | True | True |
| repaired_proposal | repaired_joint_calibrated_proposal | status: `ROUTE_TO_CASCADE_TEACHER` | True | True | True |
| srr_v2 | srr_v2_multiscale_private_basic |  | True | True | True |
| srr_v2 | srr_v2_multiscale_private_proposal |  | False | False | False |
| srr_v2 | srr_v2_proposal_uncertainty_hardneg |  | False | False | False |
| cascade_teacher | nnunet_anatomy_prior_refiner | status: `STOP_NO_CASCADE_SIGNAL` | True | True | True |
| cascade_teacher | nnunet_pathology_teacher_srr_refiner | status: `STOP_NO_CASCADE_SIGNAL` | True | True | True |
| cascade_teacher | coarse_to_fine_srr_roi | status: `STOP_NO_CASCADE_SIGNAL` | True | True | True |
| cine_motion_alignment |  | status: `SELECT_MOTION_DESCRIPTOR_ONLY` |  |  | True |
| cine_motion_pathology |  | status: `SELECT_REFERENCE_CONTROL_ONLY` |  |  | True |

## Interpretation

- Repaired proposal rows ready: `3/3`.
- SRR-v2 rows ready: `1/3`.
- Cascade teacher formal rows ready: `3/3`.
- Cascade teacher artifact coverage is tracked separately in `results/20260629_cascade_teacher_route/metrics_summary.md`; formal cascade refiner rows remain pending until a GPU job is submitted and evaluated.
- Cine alignment/pathology rows already have selections and are ready as secondary-line evidence.
