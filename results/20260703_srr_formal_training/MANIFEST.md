# Manifest 20260703 SRR Formal Training

task: `prompts/tasks/20260703_srr_formal_training.md`
controller_task: `prompts/tasks/20260703_mainline_resume_goal.md`
result: `results/20260703_srr_formal_training/result.md`
review: `results/20260703_srr_formal_training/review.md` (not written by executor; separate audit required)
output_root: `results/20260703_srr_formal_training/`

## Top-Level Artifacts

| path | purpose |
| --- | --- |
| `result.md` | Executor result and self-assessment. |
| `MANIFEST.md` | Artifact index. |
| `job_status.md` | Slurm completion states, exit codes, elapsed times, logs, and config guards. |
| `experiment_adequacy_report.md` | Adequacy gate report showing failure on train_loop_seconds. |
| `one_batch_overfit.md` | One-batch overfit sanity summary. |
| `checkpoint_policy.md` | Best/final checkpoint policy and exported checkpoint paths. |
| `prediction_sanity.md` | Aggregated prediction sanity report for best/final and both decode modes. |
| `proposal_pr_sweep.csv` | Concatenated checkpoint-specific proposal recall/precision sweep rows. |
| `metrics_summary.md` | Same-split comparison and checkpoint metrics summary. |
| `subgroup_metrics.csv` | Concatenated subgroup metric rows. |
| `component_hd_by_case.csv` | Concatenated case-level Dice/HD/HD95/component rows. |
| `roi_coverage.csv` | Concatenated ROI coverage rows. |
| `label_export_qc.md` | Compact-label local QC and explicit no raw export/package note. |
| `failure_interpretation.md` | Executor interpretation with controlled decisions and no route-negative stop. |
| `command_transcript.md` | Commands and exit statuses. |

## Variant Artifacts

| variant | output path | summary | predictions |
| --- | --- | --- | ---: |
| `srr_propref_shared_dual_dict` | `results/20260703_srr_formal_training/variants/srr_propref_shared_dual_dict/` | `summary.json` | 176 |
| `srr_propref_scar_precision` | `results/20260703_srr_formal_training/variants/srr_propref_scar_precision/` | `summary.json` | 176 |
| `srr_propref_no_proto_cascade` | `results/20260703_srr_formal_training/variants/srr_propref_no_proto_cascade/` | `summary.json` | 176 |

## Publication Boundary

This result tree contains local evidence. Do not publish checkpoints, predictions, NIfTI outputs, heavy logs, full result trees, upload packages, credentials, or environment dumps. A separate read-only audit is required before any promotion or diagnostic publication decision.
