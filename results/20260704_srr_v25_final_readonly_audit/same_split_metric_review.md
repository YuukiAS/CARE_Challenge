# Same-Split Metric Review

Source: `results/20260704_srr_v25_training_ablation_matrix/full_fold0_eval/full_fold0_eval_summary.md`.

Full fold0 pathology-aware deltas versus same-split nnU-Net:

| variant | edema Dice delta | scar Dice delta | edema remote-FP delta | scar remote-FP delta | audit note |
| --- | ---: | ---: | ---: | ---: | --- |
| `srr_propref_shared_dual_dict` | -0.000023 | +0.000044 | 0.000 | 0.000 | near identity |
| `srr_propref_no_proto_cascade` | +0.001480 | -0.000410 | +0.045 | 0.000 | tiny mixed signal |
| `srr_propref_scar_precision` | -0.000026 | +0.000038 | 0.000 | 0.000 | near identity |
| `srr_v25_no_local_refine` | 0.000000 | +0.000015 | 0.000 | 0.000 | identity-like |
| `srr_v25_no_anatomy_roi` | -0.000036 | +0.000032 | 0.000 | 0.000 | near identity |
| `srr_v25_no_anchor` | -0.142051 | -0.558659 | +2073.727 | +856.932 | strongly harmful |

Conclusion: the matrix supports the need for a baseline-preserving anchor gate,
but does not show a useful improvement over nnU-Net.
