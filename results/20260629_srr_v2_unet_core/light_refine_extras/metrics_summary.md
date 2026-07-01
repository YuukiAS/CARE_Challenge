# SRR Fold0 Metrics Summary

## Variant Summaries

### srr_v2_light_refine_lowmix

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.022998882458`
- best_step: `467500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/light_refine_extras/variants/srr_v2_light_refine_lowmix/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/light_refine_extras/variants/srr_v2_light_refine_lowmix/predictions/fold_0/checkpoint_best`

### srr_v2_light_refine_hardneg

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.03492167592`
- best_step: `407500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/light_refine_extras/variants/srr_v2_light_refine_hardneg/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/light_refine_extras/variants/srr_v2_light_refine_hardneg/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| srr_v2_light_refine_lowmix | myops_edema | all_cases | 44 | 0.2728546866416253 | 67.55670312166481 | 51.583830621846865 |
| srr_v2_light_refine_lowmix | myops_edema | gt_positive_only | 16 | 0.18785038826446968 | 110.98601227130648 | 84.74486459303414 |
| srr_v2_light_refine_lowmix | myops_edema | complete_modality | 16 | 0.18785038826446968 | 110.98601227130648 | 84.74486459303414 |
| srr_v2_light_refine_lowmix | myops_edema | LGE-only | 24 | 0.20833333333333334 | 0.0 | 0.0 |
| srr_v2_light_refine_lowmix | myops_scar | all_cases | 44 | 0.24307010999537523 | 122.42182061734684 | 76.70388864358858 |
| srr_v2_light_refine_lowmix | myops_scar | gt_positive_only | 43 | 0.22546708929759327 | 125.56084165881727 | 78.67065501906522 |
| srr_v2_light_refine_lowmix | myops_scar | complete_modality | 16 | 0.22996758860135805 | 114.57426016117132 | 72.92192103316849 |
| srr_v2_light_refine_lowmix | myops_scar | LGE-only | 24 | 0.24047097797759928 | 138.6590811190495 | 85.38909082466046 |
| srr_v2_light_refine_hardneg | myops_edema | all_cases | 44 | 0.3314401511076868 | 81.68436868931036 | 61.63666860895483 |
| srr_v2_light_refine_hardneg | myops_edema | gt_positive_only | 16 | 0.16146041554613874 | 142.94764520629312 | 107.86417006567095 |
| srr_v2_light_refine_hardneg | myops_edema | complete_modality | 16 | 0.16146041554613874 | 142.94764520629312 | 107.86417006567095 |
| srr_v2_light_refine_hardneg | myops_edema | LGE-only | 24 | 0.5 | 0.0 | 0.0 |
| srr_v2_light_refine_hardneg | myops_scar | all_cases | 44 | 0.2327688430675957 | 104.03326697773369 | 70.00260855598576 |
| srr_v2_light_refine_hardneg | myops_scar | gt_positive_only | 43 | 0.23818207197614444 | 104.03326697773369 | 70.00260855598576 |
| srr_v2_light_refine_hardneg | myops_scar | complete_modality | 16 | 0.21871236438291342 | 129.74434923324907 | 114.9891030546718 |
| srr_v2_light_refine_hardneg | myops_scar | LGE-only | 24 | 0.26846322901726033 | 92.29737648605231 | 43.47515754838751 |

Decision: `GO_CONDITIONAL_ABLATION`

Reasons:
- best_edema_gt_positive=srr_v2_light_refine_lowmix:0.1879
- best_scar_all_cases=srr_v2_light_refine_lowmix:0.2431
- metric signal present but routing remains weak
