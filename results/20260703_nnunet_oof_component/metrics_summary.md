# Metrics Summary

same_split_baseline: `baseline_nnunet501_fold0`
candidate: `oof_scar_component_score`

| variant | class | group | n | Dice | HD | HD95 | components | remote FP | small FP | empty rate |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_nnunet501_fold0 | myops_edema | all_cases | 44 | 0.779795 | 10.766868 | 7.276922 | 3.318182 | 0.045455 | 1.863636 | 0.636364 |
| baseline_nnunet501_fold0 | myops_edema | gt_positive_only | 16 | 0.394436 | 29.608887 | 20.011536 | 9.125000 | 0.125000 | 5.125000 | 0.000000 |
| baseline_nnunet501_fold0 | myops_edema | t2_present | 16 | 0.394436 | 29.608887 | 20.011536 | 9.125000 | 0.125000 | 5.125000 | 0.000000 |
| baseline_nnunet501_fold0 | myops_edema | complete_modality | 16 | 0.394436 | 29.608887 | 20.011536 | 9.125000 | 0.125000 | 5.125000 | 0.000000 |
| baseline_nnunet501_fold0 | myops_edema | CenterB | 7 | 0.502974 | 24.054494 | 15.933514 | 7.714286 | 0.000000 | 3.285714 | 0.000000 |
| baseline_nnunet501_fold0 | myops_edema | CenterC | 9 | 0.310017 | 33.928971 | 23.183331 | 10.222222 | 0.222222 | 6.555556 | 0.000000 |
| baseline_nnunet501_fold0 | myops_edema | LGE-only | 24 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 |
| baseline_nnunet501_fold0 | myops_edema | no_T2_empty_GT | 28 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 |
| baseline_nnunet501_fold0 | myops_scar | all_cases | 44 | 0.560169 | 25.970646 | 13.600533 | 4.681818 | 0.363636 | 2.545455 | 0.022727 |
| baseline_nnunet501_fold0 | myops_scar | gt_positive_only | 43 | 0.573196 | 25.970646 | 13.600533 | 4.627907 | 0.209302 | 2.465116 | 0.023256 |
| baseline_nnunet501_fold0 | myops_scar | t2_present | 16 | 0.693335 | 22.635526 | 9.267224 | 1.875000 | 0.187500 | 0.562500 | 0.000000 |
| baseline_nnunet501_fold0 | myops_scar | complete_modality | 16 | 0.693335 | 22.635526 | 9.267224 | 1.875000 | 0.187500 | 0.562500 | 0.000000 |
| baseline_nnunet501_fold0 | myops_scar | CenterB | 7 | 0.613182 | 22.295909 | 12.440137 | 2.285714 | 0.000000 | 0.857143 | 0.000000 |
| baseline_nnunet501_fold0 | myops_scar | CenterC | 9 | 0.755676 | 22.899672 | 6.799402 | 1.555556 | 0.333333 | 0.333333 | 0.000000 |
| baseline_nnunet501_fold0 | myops_scar | LGE-only | 24 | 0.501789 | 28.632546 | 16.875690 | 6.041667 | 0.250000 | 3.541667 | 0.041667 |
| baseline_nnunet501_fold0 | myops_scar | no_T2_empty_GT | 1 | 0.000000 | NA | NA | 7.000000 | 7.000000 | 6.000000 | 0.000000 |
| oof_scar_component_score | myops_edema | all_cases | 44 | 0.779795 | 10.766868 | 7.276922 | 3.318182 | 0.045455 | 1.863636 | 0.636364 |
| oof_scar_component_score | myops_edema | gt_positive_only | 16 | 0.394436 | 29.608887 | 20.011536 | 9.125000 | 0.125000 | 5.125000 | 0.000000 |
| oof_scar_component_score | myops_edema | t2_present | 16 | 0.394436 | 29.608887 | 20.011536 | 9.125000 | 0.125000 | 5.125000 | 0.000000 |
| oof_scar_component_score | myops_edema | complete_modality | 16 | 0.394436 | 29.608887 | 20.011536 | 9.125000 | 0.125000 | 5.125000 | 0.000000 |
| oof_scar_component_score | myops_edema | CenterB | 7 | 0.502974 | 24.054494 | 15.933514 | 7.714286 | 0.000000 | 3.285714 | 0.000000 |
| oof_scar_component_score | myops_edema | CenterC | 9 | 0.310017 | 33.928971 | 23.183331 | 10.222222 | 0.222222 | 6.555556 | 0.000000 |
| oof_scar_component_score | myops_edema | LGE-only | 24 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 |
| oof_scar_component_score | myops_edema | no_T2_empty_GT | 28 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 |
| oof_scar_component_score | myops_scar | all_cases | 44 | 0.560116 | 26.086109 | 13.991715 | 3.681818 | 0.272727 | 1.659091 | 0.022727 |
| oof_scar_component_score | myops_scar | gt_positive_only | 43 | 0.573142 | 26.086109 | 13.991715 | 3.627907 | 0.139535 | 1.581395 | 0.023256 |
| oof_scar_component_score | myops_scar | t2_present | 16 | 0.693352 | 22.343698 | 9.259109 | 1.812500 | 0.187500 | 0.500000 | 0.000000 |
| oof_scar_component_score | myops_scar | complete_modality | 16 | 0.693352 | 22.343698 | 9.259109 | 1.812500 | 0.187500 | 0.500000 | 0.000000 |
| oof_scar_component_score | myops_scar | CenterB | 7 | 0.613220 | 21.628875 | 12.421589 | 2.142857 | 0.000000 | 0.714286 | 0.000000 |
| oof_scar_component_score | myops_scar | CenterC | 9 | 0.755676 | 22.899672 | 6.799402 | 1.555556 | 0.333333 | 0.333333 | 0.000000 |
| oof_scar_component_score | myops_scar | LGE-only | 24 | 0.501717 | 29.046401 | 17.575968 | 4.416667 | 0.125000 | 2.041667 | 0.041667 |
| oof_scar_component_score | myops_scar | no_T2_empty_GT | 1 | 0.000000 | NA | NA | 6.000000 | 6.000000 | 5.000000 | 0.000000 |

## Fold0 Candidate Deltas

| class | group | delta Dice | HD improvement | HD95 improvement | component improvement | remote FP improvement | small FP improvement |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| myops_edema | CenterB | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_scar | CenterB | 0.000039 | 0.667034 | 0.018548 | 0.142857 | 0.000000 | 0.142857 |
| myops_edema | CenterC | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_scar | CenterC | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_edema | LGE-only | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_scar | LGE-only | -0.000073 | -0.413856 | -0.700278 | 1.625000 | 0.125000 | 1.500000 |
| myops_edema | all_cases | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_scar | all_cases | -0.000053 | -0.115463 | -0.391181 | 1.000000 | 0.090909 | 0.886364 |
| myops_edema | complete_modality | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_scar | complete_modality | 0.000017 | 0.291827 | 0.008115 | 0.062500 | 0.000000 | 0.062500 |
| myops_edema | gt_positive_only | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_scar | gt_positive_only | -0.000055 | -0.115463 | -0.391181 | 1.000000 | 0.069767 | 0.883721 |
| myops_edema | no_T2_empty_GT | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_scar | no_T2_empty_GT | 0.000000 | NA | NA | 1.000000 | 1.000000 | 1.000000 |
| myops_edema | t2_present | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_scar | t2_present | 0.000017 | 0.291827 | 0.008115 | 0.062500 | 0.000000 | 0.062500 |
