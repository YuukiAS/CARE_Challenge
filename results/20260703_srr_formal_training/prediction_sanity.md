# Prediction Sanity: 20260703 SRR Formal Training

status: `COMPLETED_DIAGNOSTIC`; adequacy still fails on train-loop seconds.

| variant | checkpoint | decode | rows | mean foreground_rate | mean pathology_rate | empty_prediction_rate | no_T2_edema_voxels | compact labels observed |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `srr_propref_no_proto_cascade` | `checkpoint_best` | `argmax` | 44 | 0.115772 | 0.033017 | 0.000000 | 488696 | `0,1,2,3,4,5; 0,1,2,4,5` |
| `srr_propref_no_proto_cascade` | `checkpoint_best` | `pathology_aware` | 44 | 0.128109 | 0.062632 | 0.000000 | 886192 | `0,1,2,3,4,5; 0,1,2,4,5` |
| `srr_propref_no_proto_cascade` | `checkpoint_final` | `argmax` | 44 | 0.115772 | 0.033017 | 0.000000 | 488696 | `0,1,2,3,4,5; 0,1,2,4,5` |
| `srr_propref_no_proto_cascade` | `checkpoint_final` | `pathology_aware` | 44 | 0.128109 | 0.062632 | 0.000000 | 886192 | `0,1,2,3,4,5; 0,1,2,4,5` |
| `srr_propref_scar_precision` | `checkpoint_best` | `argmax` | 44 | 0.106345 | 0.027508 | 0.000000 | 69447 | `0,1,2,3,4,5; 0,1,2,4,5` |
| `srr_propref_scar_precision` | `checkpoint_best` | `pathology_aware` | 44 | 0.128581 | 0.060148 | 0.000000 | 275336 | `0,1,2,3,4,5; 0,1,2,4,5` |
| `srr_propref_scar_precision` | `checkpoint_final` | `argmax` | 44 | 0.106345 | 0.027508 | 0.000000 | 69447 | `0,1,2,3,4,5; 0,1,2,4,5` |
| `srr_propref_scar_precision` | `checkpoint_final` | `pathology_aware` | 44 | 0.128581 | 0.060148 | 0.000000 | 275336 | `0,1,2,3,4,5; 0,1,2,4,5` |
| `srr_propref_shared_dual_dict` | `checkpoint_best` | `argmax` | 44 | 0.111379 | 0.020476 | 0.000000 | 101959 | `0,1,2,3,4,5; 0,1,2,4,5; 0,2,4,5` |
| `srr_propref_shared_dual_dict` | `checkpoint_best` | `pathology_aware` | 44 | 0.137117 | 0.061033 | 0.000000 | 445011 | `0,1,2,3,4,5; 0,1,2,4,5; 0,2,4,5` |
| `srr_propref_shared_dual_dict` | `checkpoint_final` | `argmax` | 44 | 0.111379 | 0.020476 | 0.000000 | 101959 | `0,1,2,3,4,5; 0,1,2,4,5; 0,2,4,5` |
| `srr_propref_shared_dual_dict` | `checkpoint_final` | `pathology_aware` | 44 | 0.137117 | 0.061033 | 0.000000 | 445011 | `0,1,2,3,4,5; 0,1,2,4,5; 0,2,4,5` |

Decode modes are compact-label local predictions (`argmax` and `pathology_aware`). Raw-label validation export was not generated; validation packaging/upload is forbidden by task scope.
