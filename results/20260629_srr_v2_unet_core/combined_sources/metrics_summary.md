# SRR Fold0 Metrics Summary

## Variant Summaries

### srr_v2_multiscale_private_basic

- stop_reason: `recovered_export_from_checkpoint`
- elapsed_seconds: `607.2312626130879`
- best_step: `407500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/variants/srr_v2_multiscale_private_basic/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/variants/srr_v2_multiscale_private_basic/predictions/fold_0/checkpoint_best`

### srr_v2_multiscale_private_proposal

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23404.884205468`
- best_step: `200000`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core_htzhulab_fallback/variants/srr_v2_multiscale_private_proposal/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core_htzhulab_fallback/variants/srr_v2_multiscale_private_proposal/predictions/fold_0/checkpoint_best`

### srr_v2_proposal_uncertainty_hardneg

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.946123097092`
- best_step: `162500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core_htzhulab_fallback/variants/srr_v2_proposal_uncertainty_hardneg/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core_htzhulab_fallback/variants/srr_v2_proposal_uncertainty_hardneg/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| srr_v2_multiscale_private_basic | myops_edema | all_cases | 44 | 0.32474579320429175 | 63.762085986752325 | 49.35072006710968 |
| srr_v2_multiscale_private_basic | myops_edema | gt_positive_only | 16 | 0.14305093131180235 | 122.61939612836986 | 94.90523089828784 |
| srr_v2_multiscale_private_basic | myops_edema | complete_modality | 16 | 0.14305093131180235 | 122.61939612836986 | 94.90523089828784 |
| srr_v2_multiscale_private_basic | myops_edema | LGE-only | 24 | 0.4166666666666667 | 0.0 | 0.0 |
| srr_v2_multiscale_private_basic | myops_scar | all_cases | 44 | 0.1997778444841966 | 134.59368805210977 | 82.74902482345838 |
| srr_v2_multiscale_private_basic | myops_scar | gt_positive_only | 43 | 0.20442384086755 | 134.59368805210977 | 82.74902482345838 |
| srr_v2_multiscale_private_basic | myops_scar | complete_modality | 16 | 0.20680722281059627 | 119.73239390526574 | 95.0011652909253 |
| srr_v2_multiscale_private_basic | myops_scar | LGE-only | 24 | 0.21458151087424077 | 146.9820841153313 | 78.31406701201628 |
| srr_v2_multiscale_private_proposal | myops_edema | all_cases | 44 | 0.2719840546050328 | 96.55143916360768 | 68.07190997061072 |
| srr_v2_multiscale_private_proposal | myops_edema | gt_positive_only | 16 | 0.1854561501638402 | 150.861623693137 | 106.36235932907924 |
| srr_v2_multiscale_private_proposal | myops_edema | complete_modality | 16 | 0.1854561501638402 | 150.861623693137 | 106.36235932907924 |
| srr_v2_multiscale_private_proposal | myops_edema | LGE-only | 24 | 0.3333333333333333 | 0.0 | 0.0 |
| srr_v2_multiscale_private_proposal | myops_scar | all_cases | 44 | 0.2191583209563022 | 132.89432590557112 | 86.90174746817598 |
| srr_v2_multiscale_private_proposal | myops_scar | gt_positive_only | 43 | 0.22425502609482084 | 132.89432590557112 | 86.90174746817598 |
| srr_v2_multiscale_private_proposal | myops_scar | complete_modality | 16 | 0.24942385377690088 | 122.88682017719354 | 73.73280640726153 |
| srr_v2_multiscale_private_proposal | myops_scar | LGE-only | 24 | 0.20913318755485585 | 147.9221140723126 | 103.3124606335002 |
| srr_v2_proposal_uncertainty_hardneg | myops_edema | all_cases | 44 | 0.692776426668762 | 63.361863094121894 | 48.85656152802183 |
| srr_v2_proposal_uncertainty_hardneg | myops_edema | gt_positive_only | 16 | 0.15513517333909566 | 174.2451235088352 | 134.35554420206003 |
| srr_v2_proposal_uncertainty_hardneg | myops_edema | complete_modality | 16 | 0.15513517333909566 | 174.2451235088352 | 134.35554420206003 |
| srr_v2_proposal_uncertainty_hardneg | myops_edema | LGE-only | 24 | 1.0 | 0.0 | 0.0 |
| srr_v2_proposal_uncertainty_hardneg | myops_scar | all_cases | 44 | 0.24739216286759713 | 132.46708198955344 | 83.12905423557427 |
| srr_v2_proposal_uncertainty_hardneg | myops_scar | gt_positive_only | 43 | 0.25314546898079704 | 132.46708198955344 | 83.12905423557427 |
| srr_v2_proposal_uncertainty_hardneg | myops_scar | complete_modality | 16 | 0.2840461410447722 | 140.75693860304716 | 101.49210629787437 |
| srr_v2_proposal_uncertainty_hardneg | myops_scar | LGE-only | 24 | 0.25549470729855317 | 136.21779032674831 | 73.92350533414552 |

Decision: `GO_CONDITIONAL_ABLATION`

Reasons:
- best_edema_gt_positive=srr_v2_multiscale_private_proposal:0.1855
- best_scar_all_cases=srr_v2_proposal_uncertainty_hardneg:0.2474
- metric signal present but routing remains weak
