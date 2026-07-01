# Cascade Teacher Metrics Summary

Status: `STOP_NO_CASCADE_SIGNAL`
Selected variant: `none`
Ready variants: `3/3`

| variant | ready | eval decision | delta T2+ edema Dice | delta T2+ edema HD95 | delta all scar Dice | delta all scar HD95 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| nnunet_anatomy_prior_refiner | True | fail_stop_refiner_candidate | 0.0014 | -0.0276 | 0.0000 | 0.0000 |
| nnunet_pathology_teacher_srr_refiner | True | fail_stop_refiner_candidate | 0.0006 | 0.0033 | 0.0000 | 0.0000 |
| coarse_to_fine_srr_roi | True | fail_stop_refiner_candidate | 0.0019 | -0.0626 | 0.0028 | -0.4037 |

## Reasons

- all formal variants reported fail_stop_refiner_candidate
- tiny positive deltas are not treated as route selection evidence
