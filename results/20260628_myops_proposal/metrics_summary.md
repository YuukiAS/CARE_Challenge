# SRR Fold0 Metrics Summary

## Variant Summaries

### proposal_pos_neg_basic

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.001209797338`
- best_step: `105000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260628_myops_proposal/variants/proposal_pos_neg_basic/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260628_myops_proposal/variants/proposal_pos_neg_basic/predictions/fold_0/checkpoint_best`

### proposal_anatomy_distance

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.039483407512`
- best_step: `105000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260628_myops_proposal/variants/proposal_anatomy_distance/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260628_myops_proposal/variants/proposal_anatomy_distance/predictions/fold_0/checkpoint_best`

### proposal_uncertainty_gate

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.04505234398`
- best_step: `105000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260628_myops_proposal/variants/proposal_uncertainty_gate/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260628_myops_proposal/variants/proposal_uncertainty_gate/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| proposal_pos_neg_basic | myops_edema | all_cases | 44 | 0.17678745952285205 | 124.43835424210981 | 92.77718076618305 |
| proposal_pos_neg_basic | myops_edema | gt_positive_only | 16 | 0.17366551368784316 | 163.32533994276912 | 121.77004975561526 |
| proposal_pos_neg_basic | myops_edema | complete_modality | 16 | 0.17366551368784316 | 163.32533994276912 | 121.77004975561526 |
| proposal_pos_neg_basic | myops_edema | LGE-only | 24 | 0.20833333333333334 | 0.0 | 0.0 |
| proposal_pos_neg_basic | myops_scar | all_cases | 44 | 0.1016864494638484 | 175.82709857432226 | 140.4493071312635 |
| proposal_pos_neg_basic | myops_scar | gt_positive_only | 43 | 0.10405125061417046 | 175.82709857432226 | 140.4493071312635 |
| proposal_pos_neg_basic | myops_scar | complete_modality | 16 | 0.14647169690041925 | 164.91323432788994 | 130.96499591919962 |
| proposal_pos_neg_basic | myops_scar | LGE-only | 24 | 0.07218857329125145 | 184.39735331273567 | 149.88980316160686 |
| proposal_anatomy_distance | myops_edema | all_cases | 44 | 0.06346604300589194 | 155.01503507308058 | 117.43236517786022 |
| proposal_anatomy_distance | myops_edema | gt_positive_only | 16 | 0.17453161826620284 | 155.01503507308058 | 117.43236517786022 |
| proposal_anatomy_distance | myops_edema | complete_modality | 16 | 0.17453161826620284 | 155.01503507308058 | 117.43236517786022 |
| proposal_anatomy_distance | myops_edema | LGE-only | 24 | 0.0 |  |  |
| proposal_anatomy_distance | myops_scar | all_cases | 44 | 0.09560962874284694 | 174.61797299739652 | 143.51918257471405 |
| proposal_anatomy_distance | myops_scar | gt_positive_only | 43 | 0.09783310848105269 | 174.61797299739652 | 143.51918257471405 |
| proposal_anatomy_distance | myops_scar | complete_modality | 16 | 0.12360161815820483 | 167.22131208079492 | 143.10153705156816 |
| proposal_anatomy_distance | myops_scar | LGE-only | 24 | 0.07830663326575264 | 180.49801629600233 | 145.56437248498906 |
| proposal_uncertainty_gate | myops_edema | all_cases | 44 | 0.4375933176629537 | 82.92712164330827 | 60.96216172598964 |
| proposal_uncertainty_gate | myops_edema | gt_positive_only | 16 | 0.2033816235731226 | 165.85424328661654 | 121.92432345197928 |
| proposal_uncertainty_gate | myops_edema | complete_modality | 16 | 0.2033816235731226 | 165.85424328661654 | 121.92432345197928 |
| proposal_uncertainty_gate | myops_edema | LGE-only | 24 | 0.6666666666666666 | 0.0 | 0.0 |
| proposal_uncertainty_gate | myops_scar | all_cases | 44 | 0.09689849967560282 | 173.3919855900641 | 131.5380435501494 |
| proposal_uncertainty_gate | myops_scar | gt_positive_only | 43 | 0.0991519531564308 | 173.3919855900641 | 131.5380435501494 |
| proposal_uncertainty_gate | myops_scar | complete_modality | 16 | 0.12357517441848662 | 160.4542347431844 | 120.75481755551222 |
| proposal_uncertainty_gate | myops_scar | LGE-only | 24 | 0.08129046853761046 | 179.16665577854118 | 139.21375460735933 |

Decision: `GO_RESCUE_ABLATION`

Reasons:
- best_edema_gt_positive=proposal_uncertainty_gate:0.2034
- best_scar_all_cases=proposal_pos_neg_basic:0.1017
- proposal_pos_neg_basic.anatomy.max_mean_weight=0.2835
- proposal_pos_neg_basic.anatomy.max_logged_weight=1.0000
- proposal_anatomy_distance.anatomy.max_mean_weight=0.2640
- proposal_anatomy_distance.anatomy.max_logged_weight=1.0000
- proposal_uncertainty_gate.anatomy.max_mean_weight=0.2854
- proposal_uncertainty_gate.anatomy.max_logged_weight=1.0000
- proposal_pos_neg_basic.scar.max_mean_weight=0.2697
- proposal_pos_neg_basic.scar.max_logged_weight=1.0000
- proposal_anatomy_distance.scar.max_mean_weight=0.2378
- proposal_anatomy_distance.scar.max_logged_weight=1.0000
- proposal_uncertainty_gate.scar.max_mean_weight=0.2347
- proposal_uncertainty_gate.scar.max_logged_weight=1.0000
- proposal_pos_neg_basic.edema.max_mean_weight=0.2421
- proposal_pos_neg_basic.edema.max_logged_weight=1.0000
- proposal_anatomy_distance.edema.max_mean_weight=0.2363
- proposal_anatomy_distance.edema.max_logged_weight=1.0000
- proposal_uncertainty_gate.edema.max_mean_weight=0.2219
- proposal_uncertainty_gate.edema.max_logged_weight=1.0000
