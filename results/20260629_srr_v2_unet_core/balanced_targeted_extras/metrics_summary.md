# SRR Fold0 Metrics Summary

## Variant Summaries

### srr_v2_capacity12_balanced_lowmix

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.11534600053`
- best_step: `307500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/balanced_targeted_extras/variants/srr_v2_capacity12_balanced_lowmix/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/balanced_targeted_extras/variants/srr_v2_capacity12_balanced_lowmix/predictions/fold_0/checkpoint_best`

### srr_v2_capacity12_scar_precision_interact

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.026278064586`
- best_step: `142500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/balanced_targeted_extras/variants/srr_v2_capacity12_scar_precision_interact/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/balanced_targeted_extras/variants/srr_v2_capacity12_scar_precision_interact/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| srr_v2_capacity12_balanced_lowmix | myops_edema | all_cases | 44 | 0.21624973427765093 | 72.76761995108008 | 60.96528907803204 |
| srr_v2_capacity12_balanced_lowmix | myops_edema | gt_positive_only | 16 | 0.15718676926354008 | 109.15142992662012 | 91.44793361704807 |
| srr_v2_capacity12_balanced_lowmix | myops_edema | complete_modality | 16 | 0.15718676926354008 | 109.15142992662012 | 91.44793361704807 |
| srr_v2_capacity12_balanced_lowmix | myops_edema | LGE-only | 24 | 0.16666666666666666 | 0.0 | 0.0 |
| srr_v2_capacity12_balanced_lowmix | myops_scar | all_cases | 44 | 0.24076762557114123 | 111.46155246749122 | 82.41916454034116 |
| srr_v2_capacity12_balanced_lowmix | myops_scar | gt_positive_only | 43 | 0.24636687267744684 | 111.46155246749122 | 82.41916454034116 |
| srr_v2_capacity12_balanced_lowmix | myops_scar | complete_modality | 16 | 0.24632034775324435 | 91.74092155686282 | 73.21019551582968 |
| srr_v2_capacity12_balanced_lowmix | myops_scar | LGE-only | 24 | 0.25407424644963894 | 133.9360617692427 | 94.82230079466203 |
| srr_v2_capacity12_scar_precision_interact | myops_edema | all_cases | 44 | 0.4841096609505475 | 70.63323208226713 | 41.93467339655861 |
| srr_v2_capacity12_scar_precision_interact | myops_edema | gt_positive_only | 16 | 0.20630156761400575 | 150.09561817481764 | 89.11118096768705 |
| srr_v2_capacity12_scar_precision_interact | myops_edema | complete_modality | 16 | 0.20630156761400575 | 150.09561817481764 | 89.11118096768705 |
| srr_v2_capacity12_scar_precision_interact | myops_edema | LGE-only | 24 | 0.7083333333333334 | 0.0 | 0.0 |
| srr_v2_capacity12_scar_precision_interact | myops_scar | all_cases | 44 | 0.2677616521055202 | 115.70264687885476 | 78.73715816855136 |
| srr_v2_capacity12_scar_precision_interact | myops_scar | gt_positive_only | 43 | 0.2739886672707649 | 115.70264687885476 | 78.73715816855136 |
| srr_v2_capacity12_scar_precision_interact | myops_scar | complete_modality | 16 | 0.2708794452770438 | 94.62835126280422 | 76.89153785042632 |
| srr_v2_capacity12_scar_precision_interact | myops_scar | LGE-only | 24 | 0.2889171313396325 | 137.66173763592369 | 84.89091015407192 |

Decision: `GO_CONDITIONAL_ABLATION`

Reasons:
- best_edema_gt_positive=srr_v2_capacity12_scar_precision_interact:0.2063
- best_scar_all_cases=srr_v2_capacity12_scar_precision_interact:0.2678
- metric signal present but routing remains weak
