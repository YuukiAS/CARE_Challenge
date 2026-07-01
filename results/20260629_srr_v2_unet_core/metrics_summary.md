# SRR Fold0 Metrics Summary

## Variant Summaries

### srr_v2_multiscale_private_basic

- stop_reason: `recovered_export_from_checkpoint`
- elapsed_seconds: `607.2312626130879`
- best_step: `407500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/variants/srr_v2_multiscale_private_basic/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/variants/srr_v2_multiscale_private_basic/predictions/fold_0/checkpoint_best`

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

Decision: `GO_CONDITIONAL_ABLATION`

Reasons:
- best_edema_gt_positive=srr_v2_multiscale_private_basic:0.1431
- best_scar_all_cases=srr_v2_multiscale_private_basic:0.1998
- metric signal present but routing remains weak
