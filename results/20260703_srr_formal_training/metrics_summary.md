# Metrics Summary: 20260703 SRR Formal Training

status: `EXECUTED_UNAUDITED`
experiment_adequacy_decision: `FAIL`
route_promotion_decision: `NOT_EVALUABLE`
route_negative_decision: `STOP_NOT_SUPPORTED`
scientific_resolution_status: `SCIENTIFIC_UNDERTRAINED`

Same-split nnU-Net fold0 references:

| reference | path | value |
| --- | --- | ---: |
| nnU-Net fold0 class 5 scar Dice | `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation/summary.json` | 0.5602 |
| nnU-Net fold0 class 4 edema Dice in nnU-Net validation summary | same as above | 0.3944 |
| unified fold0 class 4 all-case sanity Dice | `results/metrics/unified/nnUNet501/fold_0/evaluation_summary.json` | 0.7798 |

Checkpoint-specific SRR local metrics:

| variant | checkpoint | decode | scar all-case Dice | edema GT-positive Dice | scar HD95 mean | edema HD95 mean | comparison |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `srr_propref_shared_dual_dict` | `checkpoint_best` | `argmax` | 0.1665 | 0.0403 | 130.80 | 163.21 | scar -0.3936 vs nnU-Net; edema -0.3541 vs nnU-Net val-summary |
| `srr_propref_shared_dual_dict` | `checkpoint_best` | `pathology_aware` | 0.1524 | 0.0652 | 143.42 | 193.82 | scar -0.4078 vs nnU-Net; edema -0.3293 vs nnU-Net val-summary |
| `srr_propref_shared_dual_dict` | `checkpoint_final` | `argmax` | 0.1665 | 0.0403 | 130.80 | 163.21 | scar -0.3936 vs nnU-Net; edema -0.3541 vs nnU-Net val-summary |
| `srr_propref_shared_dual_dict` | `checkpoint_final` | `pathology_aware` | 0.1524 | 0.0652 | 143.42 | 193.82 | scar -0.4078 vs nnU-Net; edema -0.3293 vs nnU-Net val-summary |
| `srr_propref_scar_precision` | `checkpoint_best` | `argmax` | 0.1447 | 0.0537 | 131.57 | 189.04 | scar -0.4155 vs nnU-Net; edema -0.3407 vs nnU-Net val-summary |
| `srr_propref_scar_precision` | `checkpoint_best` | `pathology_aware` | 0.1384 | 0.0625 | 140.48 | 206.39 | scar -0.4218 vs nnU-Net; edema -0.3319 vs nnU-Net val-summary |
| `srr_propref_scar_precision` | `checkpoint_final` | `argmax` | 0.1447 | 0.0537 | 131.57 | 189.04 | scar -0.4155 vs nnU-Net; edema -0.3407 vs nnU-Net val-summary |
| `srr_propref_scar_precision` | `checkpoint_final` | `pathology_aware` | 0.1384 | 0.0625 | 140.48 | 206.39 | scar -0.4218 vs nnU-Net; edema -0.3319 vs nnU-Net val-summary |
| `srr_propref_no_proto_cascade` | `checkpoint_best` | `argmax` | 0.1257 | 0.0624 | 126.31 | 147.97 | scar -0.4345 vs nnU-Net; edema -0.3321 vs nnU-Net val-summary |
| `srr_propref_no_proto_cascade` | `checkpoint_best` | `pathology_aware` | 0.1218 | 0.0868 | 140.14 | 157.23 | scar -0.4383 vs nnU-Net; edema -0.3077 vs nnU-Net val-summary |
| `srr_propref_no_proto_cascade` | `checkpoint_final` | `argmax` | 0.1257 | 0.0624 | 126.31 | 147.97 | scar -0.4345 vs nnU-Net; edema -0.3321 vs nnU-Net val-summary |
| `srr_propref_no_proto_cascade` | `checkpoint_final` | `pathology_aware` | 0.1218 | 0.0868 | 140.14 | 157.23 | scar -0.4383 vs nnU-Net; edema -0.3077 vs nnU-Net val-summary |

These comparisons are diagnostic only because `experiment_adequacy_decision` is `FAIL` on the explicit train-loop-seconds gate. They must not be used for route promotion or `STOP_NO_PROPREF_SIGNAL` without separate audit and adequacy resolution.
