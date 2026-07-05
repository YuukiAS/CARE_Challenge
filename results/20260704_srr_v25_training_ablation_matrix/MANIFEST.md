# MANIFEST: 20260704 SRR-v2.5 Training Ablation Matrix

task: `prompts/tasks/20260704_srr_v25_training_ablation_matrix.md`
result: `results/20260704_srr_v25_training_ablation_matrix/result.md`
review: `results/20260704_srr_v25_training_ablation_matrix/review.md` (not created)

## Artifacts

| path | purpose |
| --- | --- |
| `result.md` | Executor summary and evidence status. |
| `variant_matrix.md` | Required formal matrix rows and current evidence state. |
| `bounded_matrix_summary.csv` | Per-variant stop reason, steps, eval cases, and loss summary for the bounded matrix. |
| `training_curves.csv` | Bounded matrix training/validation rows with active SRR objective columns. |
| `same_split_metrics.md` | Human-readable same-split help/harm summary for the bounded matrix. |
| `help_harm_vs_nnunet.csv` | Case/metric help-harm table comparing bounded matrix rows to fold0 nnU-Net anchor. |
| `ablation_summary.csv` | Grouped help/harm counts and mean deltas from the bounded matrix. |
| `subgroup_metrics.csv` | Hard-subgroup metrics from the bounded matrix checkpoint_final exports. |
| `mechanism_decision.md` | Explicit no-promotion/no-stop decision and missing formal evidence list. |
| `bounded_matrix/` | Raw 8-row bounded matrix outputs, predictions, metrics, and per-variant help/harm packets. |
| `full_fold0_eval/full_fold0_eval_summary.md` | Complete eval-only full fold0 summary for six existing bounded checkpoints. |
| `full_fold0_eval/manifest.json` | Complete full-fold0 eval manifest. |
| `full_fold0_eval/variants/*/` | Complete full fold0 metrics and predictions for all six non-identity rows. |
| `full_fold0_eval/help_harm/*/` | Same-split nnU-Net help/harm for all six full-fold0 rows. |
| `help_harm_smoke_after_decode_guard/help_harm_vs_nnunet.csv` | Current raw output from the guarded help/harm smoke command. |
| `help_harm_smoke_after_decode_guard/ablation_summary.csv` | Current raw grouped output from the guarded help/harm smoke command. |
| `help_harm_smoke_after_decode_guard/help_harm_manifest.json` | Current guarded help/harm smoke input/output manifest. |
| `help_harm_smoke/` | Historical pre-guard smoke output retained for traceability, not current evidence. |

## Status

`EXECUTED_UNAUDITED`; an 8-row bounded hard-subgroup matrix now exists with exact
nnU-Net/context identity rows and isolated no-local-refine, no-ROI/anatomy, and
no-anchor rows. Full fold0 eval-only metrics are complete for all six
non-identity rows. The final read-only audit remains required before any
promotion/stop decision.
