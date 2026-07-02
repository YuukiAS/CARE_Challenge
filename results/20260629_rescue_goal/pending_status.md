# 20260629 Rescue Goal Pending Status

This is a status snapshot, not a final route selection.

## Ready Rows

- ready_to_aggregate rows: `21`
- missing/pending rows: `4`

## Route Matrix

| route | variant | selection/status | summary | predictions | ready |
| --- | --- | --- | ---: | ---: | ---: |
| repaired_proposal | repaired_uncertainty_hardneg | status: `ROUTE_TO_CASCADE_TEACHER` | True | True | True |
| repaired_proposal | repaired_posneg_scar_hardneg | status: `ROUTE_TO_CASCADE_TEACHER` | True | True | True |
| repaired_proposal | repaired_joint_calibrated_proposal | status: `ROUTE_TO_CASCADE_TEACHER` | True | True | True |
| srr_v2 | srr_v2_multiscale_private_basic | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2 | srr_v2_multiscale_private_proposal | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2 | srr_v2_proposal_uncertainty_hardneg | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_light_refine_extras | srr_v2_light_refine_lowmix | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_light_refine_extras | srr_v2_light_refine_hardneg | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_capacity_extras | srr_v2_capacity12_proposal | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_capacity_extras | srr_v2_capacity12_hardneg | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_targeted_extras | srr_v2_edema_t2_focus | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_targeted_extras | srr_v2_scar_precision_nointeract | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_capacity_targeted_extras | srr_v2_capacity12_edema_t2_focus | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_capacity_targeted_extras | srr_v2_capacity12_scar_precision_nointeract | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_balanced_targeted_extras | srr_v2_capacity12_balanced_lowmix | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_balanced_targeted_extras | srr_v2_capacity12_scar_precision_interact | status: `STOP_NO_SRR_V2_SIGNAL` | True | True | True |
| srr_v2_targeted_extras_a100 | srr_v2_edema_t2_focus |  | False | False | False |
| srr_v2_targeted_extras_a100 | srr_v2_scar_precision_nointeract |  | False | False | False |
| srr_v2_targeted_extras_volta | srr_v2_edema_t2_focus |  | False | False | False |
| srr_v2_targeted_extras_volta | srr_v2_scar_precision_nointeract |  | False | False | False |
| cascade_teacher | nnunet_anatomy_prior_refiner | status: `STOP_NO_CASCADE_SIGNAL` | True | True | True |
| cascade_teacher | nnunet_pathology_teacher_srr_refiner | status: `STOP_NO_CASCADE_SIGNAL` | True | True | True |
| cascade_teacher | coarse_to_fine_srr_roi | status: `STOP_NO_CASCADE_SIGNAL` | True | True | True |
| cine_motion_alignment |  | status: `SELECT_MOTION_DESCRIPTOR_ONLY` |  |  | True |
| cine_motion_pathology |  | status: `SELECT_REFERENCE_CONTROL_ONLY` |  |  | True |

## Interpretation

- Repaired proposal rows ready: `3/3`.
- Required SRR-v2 rows ready: `3/3`.
- Cascade teacher formal rows ready: `3/3`.
- SRR-v2 light-refine and capacity extras are tracked as separate rows because they are post-required-route improvement probes.
- Targeted extra rows remain pending until full GPU training/export/evaluation writes summaries, predictions, and subgroup metrics under their isolated roots.
- Cine alignment/pathology rows already have selections and are ready as secondary-line evidence.
