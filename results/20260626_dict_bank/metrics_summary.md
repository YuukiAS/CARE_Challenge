# Dictionary Bank Interim Metrics Summary

Status: `PARTIAL`

This is an interim aggregate for completed formal variants only. It is not the final dictionary-bank selection. Do not treat the reporter's recovery-mode label below as `results/20260626_dict_bank/selection.md`.

## Variant Summaries

### multiscale_dictionary

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.02421424724`
- best_step: `600000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260626_dict_bank/variants/multiscale_dictionary/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260626_dict_bank/variants/multiscale_dictionary/predictions/fold_0/checkpoint_best`

### task_specific_dictionary

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.041554960422`
- best_step: `105000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260626_dict_bank/variants/task_specific_dictionary/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260626_dict_bank/variants/task_specific_dictionary/predictions/fold_0/checkpoint_best`

### cross_modal_interaction_dictionary

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.008836789057`
- best_step: `105000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260626_dict_bank/variants/cross_modal_interaction_dictionary/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260626_dict_bank/variants/cross_modal_interaction_dictionary/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| multiscale_dictionary | myops_edema | all_cases | 44 | 0.5591174904894196 | 26.949614826098106 | 9.618350216414026 |
| multiscale_dictionary | myops_edema | gt_positive_only | 16 | 0.10007309884590404 | 130.2564716594742 | 46.48869271266779 |
| multiscale_dictionary | myops_edema | complete_modality | 16 | 0.10007309884590404 | 130.2564716594742 | 46.48869271266779 |
| multiscale_dictionary | myops_edema | LGE-only | 24 | 0.7916666666666666 | 0.0 | 0.0 |
| multiscale_dictionary | myops_scar | all_cases | 44 | 0.025286218621437796 | 171.87943856432582 | 109.2367890584214 |
| multiscale_dictionary | myops_scar | gt_positive_only | 43 | 0.0026184562637968146 | 185.10093383850474 | 117.63961898599226 |
| multiscale_dictionary | myops_scar | complete_modality | 16 | 0.0038015243327258206 | 165.08875154481476 | 58.170698915212185 |
| multiscale_dictionary | myops_scar | LGE-only | 24 | 0.0021570512508187457 | 191.10458852661174 | 135.4802950072263 |
| task_specific_dictionary | myops_edema | all_cases | 44 | 0.03520867895237242 | 165.2098270451535 | 119.21921847391216 |
| task_specific_dictionary | myops_edema | gt_positive_only | 16 | 0.09682386711902415 | 165.2098270451535 | 119.21921847391216 |
| task_specific_dictionary | myops_edema | complete_modality | 16 | 0.09682386711902415 | 165.2098270451535 | 119.21921847391216 |
| task_specific_dictionary | myops_edema | LGE-only | 24 | 0.0 |  |  |
| task_specific_dictionary | myops_scar | all_cases | 44 | 0.09561766794724402 | 170.6192147529711 | 126.25229860179701 |
| task_specific_dictionary | myops_scar | gt_positive_only | 43 | 0.09784133464369156 | 170.6192147529711 | 126.25229860179701 |
| task_specific_dictionary | myops_scar | complete_modality | 16 | 0.11442544655722832 | 165.46871859282976 | 117.60531183320144 |
| task_specific_dictionary | myops_scar | LGE-only | 24 | 0.08237688719283286 | 175.65481296432296 | 136.89927583621616 |
| cross_modal_interaction_dictionary | myops_edema | all_cases | 44 | 0.23994869706333144 | 101.51440822333258 | 74.36721321722843 |
| cross_modal_interaction_dictionary | myops_edema | gt_positive_only | 16 | 0.15985891692416143 | 155.6554259424433 | 114.0297269330836 |
| cross_modal_interaction_dictionary | myops_edema | complete_modality | 16 | 0.15985891692416143 | 155.6554259424433 | 114.0297269330836 |
| cross_modal_interaction_dictionary | myops_edema | LGE-only | 24 | 0.3333333333333333 | 0.0 | 0.0 |
| cross_modal_interaction_dictionary | myops_scar | all_cases | 44 | 0.10535811273740621 | 169.9451829140726 | 129.21992993978034 |
| cross_modal_interaction_dictionary | myops_scar | gt_positive_only | 43 | 0.10780830140571798 | 169.9451829140726 | 129.21992993978034 |
| cross_modal_interaction_dictionary | myops_scar | complete_modality | 16 | 0.14178064646329053 | 165.7270510341087 | 123.96425934921442 |
| cross_modal_interaction_dictionary | myops_scar | LGE-only | 24 | 0.079252934783832 | 173.23942987723638 | 137.2008749180651 |

Interim reporter signal: `GO_RESCUE_ABLATION`

Reasons:
- best_edema_gt_positive=cross_modal_interaction_dictionary:0.1599
- best_scar_all_cases=cross_modal_interaction_dictionary:0.1054
- multiscale_dictionary.anatomy.max_mean_weight=0.3762
- multiscale_dictionary.anatomy.max_logged_weight=1.0000
- task_specific_dictionary.anatomy.max_mean_weight=0.2446
- task_specific_dictionary.anatomy.max_logged_weight=0.7722
- cross_modal_interaction_dictionary.anatomy.max_mean_weight=0.2951
- cross_modal_interaction_dictionary.anatomy.max_logged_weight=1.0000
- multiscale_dictionary.scar.max_mean_weight=0.3503
- multiscale_dictionary.scar.max_logged_weight=1.0000
- task_specific_dictionary.scar.max_mean_weight=0.2511
- task_specific_dictionary.scar.max_logged_weight=0.8061
- cross_modal_interaction_dictionary.scar.max_mean_weight=0.2740
- cross_modal_interaction_dictionary.scar.max_logged_weight=1.0000
- multiscale_dictionary.edema.max_mean_weight=0.3400
- multiscale_dictionary.edema.max_logged_weight=1.0000
- task_specific_dictionary.edema.max_mean_weight=0.2640
- task_specific_dictionary.edema.max_logged_weight=0.8053
- cross_modal_interaction_dictionary.edema.max_mean_weight=0.2304
- cross_modal_interaction_dictionary.edema.max_logged_weight=1.0000
