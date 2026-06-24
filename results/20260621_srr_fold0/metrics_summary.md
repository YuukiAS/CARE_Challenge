# SRR Fold0 Metrics Summary

## Variant Summaries

### conditional_dualhead_control

- stop_reason: `max_steps`
- elapsed_seconds: `14733.059205545112`
- best_step: `450000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260621_srr_fold0/variants/conditional_dualhead_control/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260621_srr_fold0/variants/conditional_dualhead_control/predictions/fold_0/checkpoint_best`

### srr_minimal

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `16229.626262340695`
- best_step: `105000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260621_srr_fold0/variants/srr_minimal/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260621_srr_fold0/variants/srr_minimal/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| conditional_dualhead_control | myops_edema | all_cases | 44 | 0.29011343886609364 | 104.86990369719896 | 81.85939535141786 |
| conditional_dualhead_control | myops_edema | gt_positive_only | 16 | 0.11031195688175752 | 176.96796248902325 | 138.13772965551766 |
| conditional_dualhead_control | myops_edema | complete_modality | 16 | 0.11031195688175752 | 176.96796248902325 | 138.13772965551766 |
| conditional_dualhead_control | myops_edema | LGE-only | 24 | 0.4166666666666667 | 0.0 | 0.0 |
| conditional_dualhead_control | myops_scar | all_cases | 44 | 0.0581369138129236 | 169.75105067615783 | 113.44915153919219 |
| conditional_dualhead_control | myops_scar | gt_positive_only | 43 | 0.05948893506438695 | 169.75105067615783 | 113.44915153919219 |
| conditional_dualhead_control | myops_scar | complete_modality | 16 | 0.1233858046529162 | 176.0644115214122 | 134.1515657992483 |
| conditional_dualhead_control | myops_scar | LGE-only | 24 | 0.010680921744731068 | 165.4112905076495 | 96.80573634347878 |
| srr_minimal | myops_edema | all_cases | 44 | 0.5972993985818298 | 69.92822674332142 | 49.07182579632985 |
| srr_minimal | myops_edema | gt_positive_only | 16 | 0.14257334610003203 | 174.82056685830352 | 122.67956449082462 |
| srr_minimal | myops_edema | complete_modality | 16 | 0.14257334610003203 | 174.82056685830352 | 122.67956449082462 |
| srr_minimal | myops_edema | LGE-only | 24 | 1.0 | 0.0 | 0.0 |
| srr_minimal | myops_scar | all_cases | 44 | 0.08315009518484238 | 168.36601466707666 | 120.86765620046349 |
| srr_minimal | myops_scar | gt_positive_only | 43 | 0.08508381832867594 | 168.36601466707666 | 120.86765620046349 |
| srr_minimal | myops_scar | complete_modality | 16 | 0.12271568025690657 | 160.84706195612154 | 104.2510707942192 |
| srr_minimal | myops_scar | LGE-only | 24 | 0.06375559576635123 | 173.72389442781898 | 138.61768160738066 |

Decision: `REVISE_ROUTING`

Reasons:
- edema_gt_positive_dice_delta_B_minus_A=0.0323
- scar_all_cases_dice_delta_B_minus_A=0.0250
- edema_gt_positive_hd95_delta_B_minus_A=-15.4582
- gate collapse: logged row-level expert weight > 0.98
