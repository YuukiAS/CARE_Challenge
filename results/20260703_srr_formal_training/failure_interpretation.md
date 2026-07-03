# Failure Interpretation

experiment_adequacy_decision: `FAIL`
route_promotion_decision: `NOT_EVALUABLE`
route_negative_decision: `STOP_NOT_SUPPORTED`
scientific_resolution_status: `SCIENTIFIC_UNDERTRAINED`

The formal array completed and produced checkpoints, predictions, PR sweeps, ROI coverage, component/HD metrics, label QC, and same-split local comparisons for all three variants. However, the task required `min_train_loop_seconds=1800`, and the completed summaries report only 138.168, 138.574, and 151.525 seconds. This violates the explicit experiment adequacy gate.

Metric signal is poor relative to same-split nnU-Net, but this executor does not claim `STOP_NO_PROPREF_SIGNAL` because adequacy failed. The appropriate route-negative decision is `STOP_NOT_SUPPORTED`, and the scientific status remains `SCIENTIFIC_UNDERTRAINED` pending separate audit or a revised adequacy policy.

## Proposal Sweep Highlights

| variant | checkpoint | metric | best_threshold_by_mean_F1 | mean_recall | mean_precision | mean_lesion_recall | mean_outside_myocardium_fp_ratio |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `srr_propref_shared_dual_dict` | `checkpoint_best` | `myops_scar` | 0.9 | 0.3429 | 0.1704 | 0.7383 | 0.6288 |
| `srr_propref_shared_dual_dict` | `checkpoint_best` | `myops_edema` | 0.9 | 0.2415 | 0.0416 | 0.1930 | 0.7878 |
| `srr_propref_shared_dual_dict` | `checkpoint_final` | `myops_scar` | 0.9 | 0.3429 | 0.1704 | 0.7383 | 0.6288 |
| `srr_propref_shared_dual_dict` | `checkpoint_final` | `myops_edema` | 0.9 | 0.2415 | 0.0416 | 0.1930 | 0.7878 |
| `srr_propref_scar_precision` | `checkpoint_best` | `myops_scar` | 0.9 | 0.2600 | 0.1863 | 0.6345 | 0.6149 |
| `srr_propref_scar_precision` | `checkpoint_best` | `myops_edema` | 0.9 | 0.1319 | 0.1224 | 0.1249 | 0.8252 |
| `srr_propref_scar_precision` | `checkpoint_final` | `myops_scar` | 0.9 | 0.2600 | 0.1863 | 0.6345 | 0.6149 |
| `srr_propref_scar_precision` | `checkpoint_final` | `myops_edema` | 0.9 | 0.1319 | 0.1224 | 0.1249 | 0.8252 |
| `srr_propref_no_proto_cascade` | `checkpoint_best` | `myops_scar` | 0.9 | 0.3937 | 0.1739 | 0.7675 | 0.5769 |
| `srr_propref_no_proto_cascade` | `checkpoint_best` | `myops_edema` | 0.8 | 0.1734 | 0.0396 | 0.1731 | 0.7060 |
| `srr_propref_no_proto_cascade` | `checkpoint_final` | `myops_scar` | 0.9 | 0.3937 | 0.1739 | 0.7675 | 0.5769 |
| `srr_propref_no_proto_cascade` | `checkpoint_final` | `myops_edema` | 0.8 | 0.1734 | 0.0396 | 0.1731 | 0.7060 |

No old SRR-v2 tuning route, learned anchor-refine training, fold expansion, validation packaging/upload, hosted metric claim, label/evaluator change, or fold split change was performed.
