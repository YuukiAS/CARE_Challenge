# Result 20260703 SRR Formal Training

self_assessed_status: `EXECUTED_UNAUDITED`
executor_decision: `SCIENTIFIC_UNDERTRAINED`
experiment_adequacy_decision: `FAIL`
route_promotion_decision: `NOT_EVALUABLE`
route_negative_decision: `STOP_NOT_SUPPORTED`
scientific_resolution_status: `SCIENTIFIC_UNDERTRAINED`
diagnostic_publication_decision: `NOT_APPLICABLE_EXECUTOR_ONLY`

## Summary

Completed executor aggregation after Slurm array job `57655472` finished. All three variants completed with exit code `0:0`, wrote `summary.json`, best/final checkpoints, checkpoint-specific predictions, prediction sanity, proposal PR sweeps, ROI coverage, component/HD metrics, and subgroup metrics under `results/20260703_srr_formal_training/variants/`.

The evidence is ready for separate audit, but the experiment adequacy gate fails because all train loops are far below the task minimum of 1800 seconds. This result therefore does not support route promotion or `STOP_NO_PROPREF_SIGNAL`.

## Variant Evidence

| variant | Slurm state | optimizer_steps | train_loop_seconds | validation_events | loss_decrease | best_step | scar Dice best/pathology | edema GT+ Dice best/pathology | adequacy |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `srr_propref_shared_dual_dict` | `COMPLETED:0:0` | 1800 | 138.168 | 9 | 2.0985 | 1800 | 0.1524 | 0.0652 | `FAIL` |
| `srr_propref_scar_precision` | `COMPLETED:0:0` | 1800 | 138.574 | 9 | 2.0580 | 1800 | 0.1384 | 0.0625 | `FAIL` |
| `srr_propref_no_proto_cascade` | `COMPLETED:0:0` | 1800 | 151.525 | 9 | 2.0215 | 1800 | 0.1218 | 0.0868 | `FAIL` |

Same-split references: nnU-Net fold0 scar Dice `0.5602`; nnU-Net fold0 edema Dice in validation summary `0.3944`; unified fold0 class-4 all-case sanity Dice `0.7798`.

## Files Read

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `/users/a/e/aereinh/.codex-global/skills/core-codex-system-codex-workflow-protocol/SKILL.md`
- `prompts/tasks/20260703_srr_formal_training.md`
- `results/20260703_srr_formal_training/result.md`
- `results/20260703_srr_formal_training/job_status.md`
- all per-variant `summary.json`, `training_log.csv`, `validation_events.csv`, `prediction_sanity_checkpoint_*.csv`, `proposal_pr_sweep_checkpoint_*.csv`, `subgroup_metrics_checkpoint_*.csv`, `component_hd_by_case_checkpoint_*.csv`, and `roi_coverage_checkpoint_*.csv` files under `variants/`
- `results/20260703_srr_propref_repair/review.md`
- `results/20260703_srr_recovery_goal/controller_report.md`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `jobs/src/run_srr_propref_myops_fold0.sh`
- `jobs/src/run_srr_propref_formal_myops_fold0.sh`
- `scripts/evaluation/aggregate_srr_propref_repair_20260703.py`
- `scripts/evaluation/aggregate_srr_propref_20260703.py`
- nnU-Net same-split reference summaries under `data/nnUNet/.../fold_0/validation/summary.json` and `results/metrics/unified/nnUNet501/fold_0/evaluation_summary.json`

## Files Changed Or Written

- `results/20260703_srr_formal_training/result.md`
- `results/20260703_srr_formal_training/MANIFEST.md`
- `results/20260703_srr_formal_training/job_status.md`
- `results/20260703_srr_formal_training/experiment_adequacy_report.md`
- `results/20260703_srr_formal_training/checkpoint_policy.md`
- `results/20260703_srr_formal_training/prediction_sanity.md`
- `results/20260703_srr_formal_training/proposal_pr_sweep.csv`
- `results/20260703_srr_formal_training/metrics_summary.md`
- `results/20260703_srr_formal_training/subgroup_metrics.csv`
- `results/20260703_srr_formal_training/component_hd_by_case.csv`
- `results/20260703_srr_formal_training/roi_coverage.csv`
- `results/20260703_srr_formal_training/label_export_qc.md`
- `results/20260703_srr_formal_training/failure_interpretation.md`
- `results/20260703_srr_formal_training/command_transcript.md`
- `results/20260703_srr_formal_training/one_batch_overfit.md`

## Commands Run

- `git status --short --branch`
- `sacct -j 57655472 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,MaxRSS,AllocTRES` -> exit `0`
- read/aggregation commands recorded in `command_transcript.md`

## Blocked Actions

- no `review.md` written by this executor
- no validation packaging
- no validation upload or external upload
- no fold expansion
- no hosted metric claim
- no label/evaluator/fold split change
- no old SRR-v2 tuning route
- no learned anchor-refine training
- no git commit or push

## Required Next State

`EXECUTED_UNAUDITED`: separate read-only audit required.
