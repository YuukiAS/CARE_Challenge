# Metric Summary

Audit basis commit: `3f30e0ee4b8c951f700fe50de8810bac8e196c23`.

Threshold used here: mean Dice delta with absolute value `< 0.005` is `near_identity / not meaningful` unless hard-subgroup evidence shows a clear material gain. No such hard-subgroup material gain was found in the committed full-fold0 summaries.

| variant | class | Dice delta | HD95 delta | remote-FP delta | verdict |
| --- | --- | ---: | ---: | ---: | --- |
| `srr_propref_no_proto_cascade` | `myops_scar` | 3.3816938457257884e-05 | 0.003127809282809884 | 0.0 | `near_identity_not_meaningful` |
| `srr_propref_no_proto_cascade` | `myops_edema` | -1.4321846323941703e-05 | -1.3359184475980612e-05 | 0.0 | `near_identity_not_meaningful` |
| `srr_propref_scar_precision` | `myops_scar` | 4.608205594205434e-05 | 0.003957435054601295 | 0.0 | `near_identity_not_meaningful` |
| `srr_propref_scar_precision` | `myops_edema` | -2.5997956972779885e-05 | 2.9633139506657358e-05 | 0.0 | `near_identity_not_meaningful` |
| `srr_propref_shared_dual_dict` | `myops_scar` | 5.497634884262349e-05 | 0.001840107398469462 | 0.0 | `near_identity_not_meaningful` |
| `srr_propref_shared_dual_dict` | `myops_edema` | -2.3248135711161708e-05 | 2.9633139506657358e-05 | 0.0 | `near_identity_not_meaningful` |
| `srr_v25_no_anatomy_roi` | `myops_scar` | 4.0638925660208247e-05 | 0.003928535912099486 | 0.0 | `near_identity_not_meaningful` |
| `srr_v25_no_anatomy_roi` | `myops_edema` | -3.614192942984396e-05 | 0.00018630055269957586 | 0.0 | `near_identity_not_meaningful` |
| `srr_v25_no_anchor` | `myops_scar` | -0.5586587758556688 | 142.90620577611296 | 856.9318181818181 | `harmful` |
| `srr_v25_no_anchor` | `myops_edema` | -0.14205075659560573 | 59.37790448740292 | 2073.7272727272725 | `harmful` |
| `srr_v25_no_local_refine` | `myops_scar` | 1.3212173769238717e-05 | 0.0019644096682978804 | 0.0 | `near_identity_not_meaningful` |
| `srr_v25_no_local_refine` | `myops_edema` | 0.0 | 0.0 | 0.0 | `near_identity_not_meaningful` |

Conclusion: no anchor-enabled row shows meaningful average Dice improvement over same-split nnU-Net. The no-anchor row is a strong negative control, not a positive SRR result.
