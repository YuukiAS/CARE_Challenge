# SRR Fold0 Metrics Summary

## Variant Summaries

### srr_v2_edema_t2_focus

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.024516370147`
- best_step: `297500`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/targeted_extras/variants/srr_v2_edema_t2_focus/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/targeted_extras/variants/srr_v2_edema_t2_focus/predictions/fold_0/checkpoint_best`

### srr_v2_scar_precision_nointeract

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.003452174366`
- best_step: `320000`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/targeted_extras/variants/srr_v2_scar_precision_nointeract/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/users/a/e/aereinh/CARE/results/20260629_srr_v2_unet_core/targeted_extras/variants/srr_v2_scar_precision_nointeract/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| srr_v2_edema_t2_focus | myops_edema | all_cases | 44 | 0.10876217985691804 | 150.27010168327658 | 105.68442154511087 |
| srr_v2_edema_t2_focus | myops_edema | gt_positive_only | 16 | 0.17409599460652458 | 170.30611524104677 | 119.77567775112564 |
| srr_v2_edema_t2_focus | myops_edema | complete_modality | 16 | 0.17409599460652458 | 170.30611524104677 | 119.77567775112564 |
| srr_v2_edema_t2_focus | myops_edema | LGE-only | 24 | 0.041666666666666664 | 0.0 | 0.0 |
| srr_v2_edema_t2_focus | myops_scar | all_cases | 44 | 0.1858424053923809 | 141.39992408301742 | 106.5340320472246 |
| srr_v2_edema_t2_focus | myops_scar | gt_positive_only | 43 | 0.19016432179685486 | 141.39992408301742 | 106.5340320472246 |
| srr_v2_edema_t2_focus | myops_scar | complete_modality | 16 | 0.1931994649490445 | 134.78872277486687 | 97.30486844757466 |
| srr_v2_edema_t2_focus | myops_scar | LGE-only | 24 | 0.18608262835022402 | 154.52282478350273 | 119.24838497501237 |
| srr_v2_scar_precision_nointeract | myops_edema | all_cases | 44 | 0.06809403499987834 | 158.87327760299053 | 106.37707725952755 |
| srr_v2_scar_precision_nointeract | myops_edema | gt_positive_only | 16 | 0.18725859624966543 | 158.87327760299053 | 106.37707725952755 |
| srr_v2_scar_precision_nointeract | myops_edema | complete_modality | 16 | 0.18725859624966543 | 158.87327760299053 | 106.37707725952755 |
| srr_v2_scar_precision_nointeract | myops_edema | LGE-only | 24 | 0.0 |  |  |
| srr_v2_scar_precision_nointeract | myops_scar | all_cases | 44 | 0.2377212504428482 | 132.70917899581283 | 87.0840399602216 |
| srr_v2_scar_precision_nointeract | myops_scar | gt_positive_only | 43 | 0.2432496516159377 | 132.70917899581283 | 87.0840399602216 |
| srr_v2_scar_precision_nointeract | myops_scar | complete_modality | 16 | 0.26156474964690296 | 118.99883847802266 | 77.66818361999734 |
| srr_v2_scar_precision_nointeract | myops_scar | LGE-only | 24 | 0.2308867718049091 | 152.8375343060467 | 101.025356621821 |

Decision: `GO_CONDITIONAL_ABLATION`

Reasons:
- best_edema_gt_positive=srr_v2_scar_precision_nointeract:0.1873
- best_scar_all_cases=srr_v2_scar_precision_nointeract:0.2377
- metric signal present but routing remains weak
