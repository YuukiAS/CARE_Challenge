# SRR Fold0 Metrics Summary

## Variant Summaries

### srr_v2_capacity12_edema_t2_focus

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.010012976`
- best_step: `255000`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/capacity_targeted_extras/variants/srr_v2_capacity12_edema_t2_focus/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/capacity_targeted_extras/variants/srr_v2_capacity12_edema_t2_focus/predictions/fold_0/checkpoint_best`

### srr_v2_capacity12_scar_precision_nointeract

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.01459115185`
- best_step: `120000`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/capacity_targeted_extras/variants/srr_v2_capacity12_scar_precision_nointeract/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/capacity_targeted_extras/variants/srr_v2_capacity12_scar_precision_nointeract/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| srr_v2_capacity12_edema_t2_focus | myops_edema | all_cases | 44 | 0.13492643409953897 | 115.70265573095865 | 59.08547326864989 |
| srr_v2_capacity12_edema_t2_focus | myops_edema | gt_positive_only | 16 | 0.18354769377373215 | 138.8431868771504 | 70.90256792237987 |
| srr_v2_capacity12_edema_t2_focus | myops_edema | complete_modality | 16 | 0.18354769377373215 | 138.8431868771504 | 70.90256792237987 |
| srr_v2_capacity12_edema_t2_focus | myops_edema | LGE-only | 24 | 0.125 | 0.0 | 0.0 |
| srr_v2_capacity12_edema_t2_focus | myops_scar | all_cases | 44 | 0.19719648830229242 | 153.73469142313544 | 110.04447236871574 |
| srr_v2_capacity12_edema_t2_focus | myops_scar | gt_positive_only | 43 | 0.2017824531465318 | 153.73469142313544 | 110.04447236871574 |
| srr_v2_capacity12_edema_t2_focus | myops_scar | complete_modality | 16 | 0.2799104551777384 | 164.13043360730546 | 98.11356644207541 |
| srr_v2_capacity12_edema_t2_focus | myops_scar | LGE-only | 24 | 0.13700000998223394 | 156.52330216101012 | 124.8717325499692 |
| srr_v2_capacity12_scar_precision_nointeract | myops_edema | all_cases | 44 | 0.5705013540806446 | 74.7134043869571 | 52.95296385870038 |
| srr_v2_capacity12_scar_precision_nointeract | myops_edema | gt_positive_only | 16 | 0.19387872372177264 | 177.4443354190231 | 125.76328916441341 |
| srr_v2_capacity12_scar_precision_nointeract | myops_edema | complete_modality | 16 | 0.19387872372177264 | 177.4443354190231 | 125.76328916441341 |
| srr_v2_capacity12_scar_precision_nointeract | myops_edema | LGE-only | 24 | 0.75 | 0.0 | 0.0 |
| srr_v2_capacity12_scar_precision_nointeract | myops_scar | all_cases | 44 | 0.2643281847183718 | 149.54713608320864 | 107.15116512172774 |
| srr_v2_capacity12_scar_precision_nointeract | myops_scar | gt_positive_only | 43 | 0.27047535180484555 | 149.54713608320864 | 107.15116512172774 |
| srr_v2_capacity12_scar_precision_nointeract | myops_scar | complete_modality | 16 | 0.2579956255999684 | 162.61686918331404 | 126.74874877522377 |
| srr_v2_capacity12_scar_precision_nointeract | myops_scar | LGE-only | 24 | 0.2797754741214222 | 149.44742325648244 | 102.89487467666852 |

Decision: `GO_CONDITIONAL_ABLATION`

Reasons:
- best_edema_gt_positive=srr_v2_capacity12_scar_precision_nointeract:0.1939
- best_scar_all_cases=srr_v2_capacity12_scar_precision_nointeract:0.2643
- metric signal present but routing remains weak
