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

Interim reporter signal: `GO_RESCUE_ABLATION`

Reasons:
- best_edema_gt_positive=multiscale_dictionary:0.1001
- best_scar_all_cases=multiscale_dictionary:0.0253
- multiscale_dictionary.anatomy.max_mean_weight=0.3762
- multiscale_dictionary.anatomy.max_logged_weight=1.0000
- multiscale_dictionary.scar.max_mean_weight=0.3503
- multiscale_dictionary.scar.max_logged_weight=1.0000
- multiscale_dictionary.edema.max_mean_weight=0.3400
- multiscale_dictionary.edema.max_logged_weight=1.0000
