# SRR Fold0 Metrics Summary

## Variant Summaries

### repaired_uncertainty_hardneg

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.025174524635`
- best_step: `105000`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_repaired_proposal_repeat/variants/repaired_uncertainty_hardneg/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_repaired_proposal_repeat/variants/repaired_uncertainty_hardneg/predictions/fold_0/checkpoint_best`

### repaired_posneg_scar_hardneg

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.002703629434`
- best_step: `105000`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_repaired_proposal_repeat/variants/repaired_posneg_scar_hardneg/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_repaired_proposal_repeat/variants/repaired_posneg_scar_hardneg/predictions/fold_0/checkpoint_best`

### repaired_joint_calibrated_proposal

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.008788676932`
- best_step: `105000`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_repaired_proposal_repeat/variants/repaired_joint_calibrated_proposal/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_repaired_proposal_repeat/variants/repaired_joint_calibrated_proposal/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| repaired_uncertainty_hardneg | myops_edema | all_cases | 44 | 0.3971005530881493 | 90.61674764284643 | 66.3941206087098 |
| repaired_uncertainty_hardneg | myops_edema | gt_positive_only | 16 | 0.1545265209924105 | 175.56994855801497 | 128.63860867937524 |
| repaired_uncertainty_hardneg | myops_edema | complete_modality | 16 | 0.1545265209924105 | 175.56994855801497 | 128.63860867937524 |
| repaired_uncertainty_hardneg | myops_edema | LGE-only | 24 | 0.5833333333333334 | 0.0 | 0.0 |
| repaired_uncertainty_hardneg | myops_scar | all_cases | 44 | 0.07609619709791735 | 176.61099670238895 | 130.60301555789138 |
| repaired_uncertainty_hardneg | myops_scar | gt_positive_only | 43 | 0.07786587610019449 | 176.61099670238895 | 130.60301555789138 |
| repaired_uncertainty_hardneg | myops_scar | complete_modality | 16 | 0.08121587562303742 | 181.12092099542912 | 120.87863935624155 |
| repaired_uncertainty_hardneg | myops_scar | LGE-only | 24 | 0.06922494323781622 | 175.66349224785804 | 142.49316415970216 |
| repaired_posneg_scar_hardneg | myops_edema | all_cases | 44 | 0.2830486443391429 | 92.32237064287568 | 67.7495540266779 |
| repaired_posneg_scar_hardneg | myops_edema | gt_positive_only | 16 | 0.09088377193264295 | 155.79400045985273 | 114.32737242001896 |
| repaired_posneg_scar_hardneg | myops_edema | complete_modality | 16 | 0.09088377193264295 | 155.79400045985273 | 114.32737242001896 |
| repaired_posneg_scar_hardneg | myops_edema | LGE-only | 24 | 0.4583333333333333 | 0.0 | 0.0 |
| repaired_posneg_scar_hardneg | myops_scar | all_cases | 44 | 0.10382045485983601 | 173.8428081807887 | 136.0183433178336 |
| repaired_posneg_scar_hardneg | myops_scar | gt_positive_only | 43 | 0.10623488404262289 | 173.8428081807887 | 136.0183433178336 |
| repaired_posneg_scar_hardneg | myops_scar | complete_modality | 16 | 0.15299653210546033 | 165.15887328204428 | 132.76880071449756 |
| repaired_posneg_scar_hardneg | myops_scar | LGE-only | 24 | 0.06717318157877891 | 179.30778655552794 | 139.6818866817772 |
| repaired_joint_calibrated_proposal | myops_edema | all_cases | 44 | 0.3939853244713275 | 84.05628436646244 | 62.505545850033656 |
| repaired_joint_calibrated_proposal | myops_edema | gt_positive_only | 16 | 0.1459596422961507 | 162.85905096002097 | 121.10449508444022 |
| repaired_joint_calibrated_proposal | myops_edema | complete_modality | 16 | 0.1459596422961507 | 162.85905096002097 | 121.10449508444022 |
| repaired_joint_calibrated_proposal | myops_edema | LGE-only | 24 | 0.625 | 0.0 | 0.0 |
| repaired_joint_calibrated_proposal | myops_scar | all_cases | 44 | 0.09215481623875589 | 180.55308561862498 | 140.93932578423406 |
| repaired_joint_calibrated_proposal | myops_scar | gt_positive_only | 43 | 0.0942979515001223 | 180.55308561862498 | 140.93932578423406 |
| repaired_joint_calibrated_proposal | myops_scar | complete_modality | 16 | 0.12013630206573922 | 191.23249537224964 | 160.82504935974114 |
| repaired_joint_calibrated_proposal | myops_scar | LGE-only | 24 | 0.07457197346605986 | 176.233135283699 | 134.73563545908635 |

Decision: `GO_RESCUE_ABLATION`

Reasons:
- best_edema_gt_positive=repaired_uncertainty_hardneg:0.1545
- best_scar_all_cases=repaired_posneg_scar_hardneg:0.1038
- repaired_uncertainty_hardneg.anatomy.max_mean_weight=0.2743
- repaired_uncertainty_hardneg.anatomy.max_logged_weight=1.0000
- repaired_posneg_scar_hardneg.anatomy.max_mean_weight=0.2634
- repaired_posneg_scar_hardneg.anatomy.max_logged_weight=1.0000
- repaired_joint_calibrated_proposal.anatomy.max_mean_weight=0.2706
- repaired_joint_calibrated_proposal.anatomy.max_logged_weight=1.0000
- repaired_uncertainty_hardneg.scar.max_mean_weight=0.2328
- repaired_uncertainty_hardneg.scar.max_logged_weight=1.0000
- repaired_posneg_scar_hardneg.scar.max_mean_weight=0.2331
- repaired_posneg_scar_hardneg.scar.max_logged_weight=1.0000
- repaired_joint_calibrated_proposal.scar.max_mean_weight=0.2228
- repaired_joint_calibrated_proposal.scar.max_logged_weight=1.0000
- repaired_uncertainty_hardneg.edema.max_mean_weight=0.2286
- repaired_uncertainty_hardneg.edema.max_logged_weight=1.0000
- repaired_posneg_scar_hardneg.edema.max_mean_weight=0.2274
- repaired_posneg_scar_hardneg.edema.max_logged_weight=1.0000
- repaired_joint_calibrated_proposal.edema.max_mean_weight=0.2202
- repaired_joint_calibrated_proposal.edema.max_logged_weight=1.0000
