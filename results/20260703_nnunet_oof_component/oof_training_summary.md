# OOF Training Summary

scorer_type: `OOF-selected threshold over predeclared scar component score`
selected_threshold: `1.30`
training_data: `fold0 train cases via existing folds 1-4 validation outputs`
fold0_validation_gt_for_selection: `not used`

## Selected Threshold OOF Metrics

| field | value |
| --- | ---: |
| `scar_delta_dice_mean` | -0.000526 |
| `scar_delta_hd_mean_improvement` | NA |
| `scar_delta_hd95_mean_improvement` | NA |
| `scar_delta_component_count_mean_improvement` | 0.965909 |
| `scar_delta_remote_fp_mean_improvement` | 0.096591 |
| `scar_delta_small_fp_mean_improvement` | 0.659091 |
| `objective` | 0.562440 |

## Threshold Grid

`oof_threshold_grid.csv` contains the full threshold sweep.
