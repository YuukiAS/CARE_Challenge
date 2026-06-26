# SRR Fold0 Metrics Summary

## Variant Summaries

### srr_expert_dropout

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.028288748115`
- best_step: `105000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260625_srr_recovery/variants/srr_expert_dropout/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260625_srr_recovery/variants/srr_expert_dropout/predictions/fold_0/checkpoint_best`

### srr_soft_entropy

- stop_reason: `max_runtime_seconds`
- elapsed_seconds: `23400.02992877364`
- best_step: `105000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260625_srr_recovery/variants/srr_soft_entropy/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260625_srr_recovery/variants/srr_soft_entropy/predictions/fold_0/checkpoint_best`

### srr_task_tempered

- stop_reason: `max_steps`
- elapsed_seconds: `20946.673384759575`
- best_step: `105000`
- checkpoint_best: `/overflow/htzhu/CARE/results/20260625_srr_recovery/variants/srr_task_tempered/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- predictions: `/overflow/htzhu/CARE/results/20260625_srr_recovery/variants/srr_task_tempered/predictions/fold_0/checkpoint_best`

## Key Subgroups

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| srr_expert_dropout | myops_edema | all_cases | 44 | 0.27463882317995003 | 88.9728404782535 | 59.48467295598383 |
| srr_expert_dropout | myops_edema | gt_positive_only | 16 | 0.1927567637448626 | 146.1696664999879 | 97.72481985625915 |
| srr_expert_dropout | myops_edema | complete_modality | 16 | 0.1927567637448626 | 146.1696664999879 | 97.72481985625915 |
| srr_expert_dropout | myops_edema | LGE-only | 24 | 0.375 | 0.0 | 0.0 |
| srr_expert_dropout | myops_scar | all_cases | 44 | 0.09230958402923188 | 165.3667058224605 | 127.03165757912724 |
| srr_expert_dropout | myops_scar | gt_positive_only | 43 | 0.0944563185415396 | 165.3667058224605 | 127.03165757912724 |
| srr_expert_dropout | myops_scar | complete_modality | 16 | 0.1385877891808992 | 139.41144918381076 | 99.32991536108268 |
| srr_expert_dropout | myops_scar | LGE-only | 24 | 0.058514868944216446 | 180.85503435216 | 144.42717094689996 |
| srr_soft_entropy | myops_edema | all_cases | 44 | 0.24641795650418638 | 74.47277817723938 | 48.68634866820671 |
| srr_soft_entropy | myops_edema | gt_positive_only | 16 | 0.052649380386512554 | 124.12129696206564 | 81.1439144470112 |
| srr_soft_entropy | myops_edema | complete_modality | 16 | 0.052649380386512554 | 124.12129696206564 | 81.1439144470112 |
| srr_soft_entropy | myops_edema | LGE-only | 24 | 0.4166666666666667 | 0.0 | 0.0 |
| srr_soft_entropy | myops_scar | all_cases | 44 | 0.03339241229261475 | 159.64860148018113 | 102.85887886572773 |
| srr_soft_entropy | myops_scar | gt_positive_only | 43 | 0.03416898002034997 | 159.64860148018113 | 102.85887886572773 |
| srr_soft_entropy | myops_scar | complete_modality | 16 | 0.027384472758775386 | 138.90272753235877 | 87.60127166090145 |
| srr_soft_entropy | myops_scar | LGE-only | 24 | 0.04065377457075062 | 170.97919504263896 | 112.73496601448772 |
| srr_task_tempered | myops_edema | all_cases | 44 | 0.5846735352821196 | 59.597307578683775 | 44.730252171312564 |
| srr_task_tempered | myops_edema | gt_positive_only | 16 | 0.10785222202582893 | 148.99326894670943 | 111.8256304282814 |
| srr_task_tempered | myops_edema | complete_modality | 16 | 0.10785222202582893 | 148.99326894670943 | 111.8256304282814 |
| srr_task_tempered | myops_edema | LGE-only | 24 | 0.9583333333333334 | 0.0 | 0.0 |
| srr_task_tempered | myops_scar | all_cases | 44 | 0.08398902101464265 | 168.33627155739205 | 121.66269512529556 |
| srr_task_tempered | myops_scar | gt_positive_only | 43 | 0.0859422540614948 | 168.33627155739205 | 121.66269512529556 |
| srr_task_tempered | myops_scar | complete_modality | 16 | 0.0974752555627136 | 157.40718057178512 | 103.58067432076251 |
| srr_task_tempered | myops_scar | LGE-only | 24 | 0.07402481290928513 | 177.0254589741263 | 136.1494064222519 |

Decision: `GO_RESCUE_ABLATION`

Reasons:
- best_edema_gt_positive=srr_expert_dropout:0.1928
- best_scar_all_cases=srr_expert_dropout:0.0923
- srr_expert_dropout.anatomy.max_mean_weight=0.3437
- srr_expert_dropout.anatomy.max_logged_weight=1.0000
- srr_soft_entropy.anatomy.max_mean_weight=0.4188
- srr_soft_entropy.anatomy.max_logged_weight=0.6389
- srr_task_tempered.anatomy.max_mean_weight=0.4005
- srr_task_tempered.anatomy.max_logged_weight=0.6252
- srr_expert_dropout.scar.max_mean_weight=0.3311
- srr_expert_dropout.scar.max_logged_weight=1.0000
- srr_soft_entropy.scar.max_mean_weight=0.3978
- srr_soft_entropy.scar.max_logged_weight=0.5815
- srr_task_tempered.scar.max_mean_weight=0.3260
- srr_task_tempered.scar.max_logged_weight=0.6737
- srr_expert_dropout.edema.max_mean_weight=0.3262
- srr_expert_dropout.edema.max_logged_weight=1.0000
- srr_soft_entropy.edema.max_mean_weight=0.3003
- srr_soft_entropy.edema.max_logged_weight=0.5226
- srr_task_tempered.edema.max_mean_weight=0.3094
- srr_task_tempered.edema.max_logged_weight=0.5473
