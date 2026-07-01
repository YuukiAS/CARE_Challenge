# SRR Fold0 Metrics Summary

## Variant Summaries

### srr_v2_capacity12_proposal

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.03579254076`
- best_step: `207500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/capacity_extras/variants/srr_v2_capacity12_proposal/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/capacity_extras/variants/srr_v2_capacity12_proposal/predictions/fold_0/checkpoint_best`

### srr_v2_capacity12_hardneg

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.028369053267`
- best_step: `477500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/capacity_extras/variants/srr_v2_capacity12_hardneg/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/capacity_extras/variants/srr_v2_capacity12_hardneg/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| srr_v2_capacity12_proposal | myops_edema | all_cases | 44 | 0.539549798740777 | 53.00661255818984 | 34.73805731491043 |
| srr_v2_capacity12_proposal | myops_edema | gt_positive_only | 16 | 0.17126194653713678 | 132.5165313954746 | 86.84514328727606 |
| srr_v2_capacity12_proposal | myops_edema | complete_modality | 16 | 0.17126194653713678 | 132.5165313954746 | 86.84514328727606 |
| srr_v2_capacity12_proposal | myops_edema | LGE-only | 24 | 0.7916666666666666 | 0.0 | 0.0 |
| srr_v2_capacity12_proposal | myops_scar | all_cases | 44 | 0.2547286752871202 | 135.1994423324343 | 68.9793026967753 |
| srr_v2_capacity12_proposal | myops_scar | gt_positive_only | 43 | 0.260652597968216 | 135.1994423324343 | 68.9793026967753 |
| srr_v2_capacity12_proposal | myops_scar | complete_modality | 16 | 0.23706957743408835 | 136.0314102695859 | 73.4615187951537 |
| srr_v2_capacity12_proposal | myops_scar | LGE-only | 24 | 0.2824322091246637 | 140.92225243958518 | 66.1752081707899 |
| srr_v2_capacity12_hardneg | myops_edema | all_cases | 44 | 0.09158262974311714 | 147.40680146442836 | 102.47067016692463 |
| srr_v2_capacity12_hardneg | myops_edema | gt_positive_only | 16 | 0.1893522317935721 | 156.6197265559551 | 108.87508705235743 |
| srr_v2_capacity12_hardneg | myops_edema | complete_modality | 16 | 0.1893522317935721 | 156.6197265559551 | 108.87508705235743 |
| srr_v2_capacity12_hardneg | myops_edema | LGE-only | 24 | 0.041666666666666664 | 0.0 | 0.0 |
| srr_v2_capacity12_hardneg | myops_scar | all_cases | 44 | 0.308968638594002 | 112.48356895979988 | 70.34681927355437 |
| srr_v2_capacity12_hardneg | myops_scar | gt_positive_only | 43 | 0.2928981418171183 | 115.09946591235337 | 71.98279181479982 |
| srr_v2_capacity12_hardneg | myops_scar | complete_modality | 16 | 0.2677225948712384 | 119.61668802691995 | 85.10594822046886 |
| srr_v2_capacity12_hardneg | myops_scar | LGE-only | 24 | 0.3159451136792804 | 119.01751842319494 | 67.88958919152711 |

Decision: `GO_CONDITIONAL_ABLATION`

Reasons:
- best_edema_gt_positive=srr_v2_capacity12_hardneg:0.1894
- best_scar_all_cases=srr_v2_capacity12_hardneg:0.3090
- metric signal present but routing remains weak
