# Decode Sanity Audit

task: `prompts/tasks/20260703_srr_failure_audit.md`

## Decision

decode_sanity_decision: PARTIAL_NEEDS_REVISION

The available evidence does not show an all-background collapse: all reported scar and edema subgroup rows have `empty_prediction_rate: 0.0`. The failure pattern is instead noisy pathology output with near-zero Dice, hundreds to thousands of components, large remote-FP burden, and fixed full-volume argmax decoding from `outputs["logits"]`.

## Findings

| item | finding | evidence |
| --- | --- | --- |
| full-volume decode path | Uses `torch.argmax(outputs["logits"], dim=1)` on final logits. | `scripts/training/run_srr_propref_myops_fold0.py:227-250` |
| compact-label QC | Predictions contain compact labels `0..5` only; no raw-label validation package was generated. | `label_export_qc.md:3-7` |
| raw-label challenge export | Evidence not found and not authorized for this task. | `label_export_qc.md:3-7`; task frontmatter forbids upload/packaging |
| empty prediction collapse | Not found in aggregate subgroup rows; empty rate is `0.0`. | `subgroup_metrics.csv` |
| pathology-aware decode alternatives | Evidence not found. There is no separate proposal-aware decode, threshold sweep decode, or per-head calibrated decode in the packet. | code and metrics review |
| final full-volume behavior | Near-zero Dice with many components and remote FPs, especially edema and scar in CenterB/CenterC/T2-present slices. | `subgroup_metrics.csv`; `component_hd_by_case.csv` |

## Selected Metric Evidence

| variant | metric | group | Dice | components mean | remote FP mean | empty rate |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `srr_propref_shared_dual_dict` | scar | all_cases | 0.0007 | 522.27 | 477.61 | 0.0 |
| `srr_propref_shared_dual_dict` | edema | gt_positive_only | 0.0070 | 524.56 | 473.12 | 0.0 |
| `srr_propref_scar_precision` | scar | all_cases | 0.0011 | 789.05 | 708.93 | 0.0 |
| `srr_propref_scar_precision` | edema | gt_positive_only | 0.0069 | 455.44 | 434.94 | 0.0 |
| `srr_propref_no_proto_cascade` | scar | all_cases | 0.0038 | 6129.68 | 5614.80 | 0.0 |
| `srr_propref_no_proto_cascade` | edema | gt_positive_only | 0.0066 | 849.88 | 768.94 | 0.0 |

## Interpretation

The decode evidence is not enough to claim a pure decode bug, but it is enough to require revision before a stop decision. A repaired run should report per-class volumes, foreground/pathology rates, compact label sets, raw-vs-compact decode path, prediction empty rate, component count, remote-FP count, and compare argmax decode against at least one pathology-aware thresholded or proposal-gated decode on the same checkpoint.
