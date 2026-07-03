# Checkpoint Policy Audit

task: `prompts/tasks/20260703_srr_failure_audit.md`

## Decision

checkpoint_policy_decision: NEEDS_REVISION
route_negative_decision: STOP_NOT_SUPPORTED

The previous package exported and evaluated `checkpoint_best`, but `checkpoint_best` was selected at step 1 for every formal variant. Because `val_every=300` and the formal run used `max_steps=120`, no post-warmup, proposal-stage, soft-ROI-stage, or low-LR-stage validation event could replace the step-1 checkpoint.

## Findings

| question | finding | evidence |
| --- | --- | --- |
| Did `val_every` exceed `max_steps`? | Yes. Formal configs used `max_steps=120`; code default uses `val_every=300`. | `run_config.env`; `scripts/training/run_srr_propref_myops_fold0.py:592-593` |
| Was `checkpoint_best` selected at step 1? | Yes, all three `summary.json` files record `best_step: 1`. | `variants/*/summary.json` |
| Were exported predictions based on `checkpoint_best`? | Yes. Evaluation writes to `predictions/fold_0/checkpoint_best` after loading `checkpoint_best` when it exists. | `scripts/training/run_srr_propref_myops_fold0.py:541-549` |
| Was `checkpoint_final` evaluated for comparison? | Evidence not found. The summary records a final checkpoint path, but the prediction directory and metrics are `checkpoint_best`. | `variants/*/summary.json`; `variant_matrix.csv` |
| Did low-LR calibration influence selected checkpoint? | Unsupported. The low-LR path is implemented but no low-LR validation/log row is present in the formal runs. | `training_schedule.md:22-26` |

## Impact

The fold0 full-volume metrics are real metrics for the saved step-1 `checkpoint_best`, not evidence that a trained PropRef route failed after adequate optimization. This is sufficient to block `STOP_NO_PROPREF_SIGNAL` as a scientific stop. A repair task must either validate frequently enough for `checkpoint_best` to reflect post-warmup training or explicitly evaluate `checkpoint_final` and post-warmup checkpoints.

## Required Checkpoint Policy For Repair

- Record `actual_steps`, `optimizer_steps`, `validation_events`, `best_step`, `best_metric`, and `checkpoint_source`.
- Set `val_every <= max_steps` and ensure at least one validation after each active stage, or explicitly evaluate `checkpoint_final`.
- Export separate prediction and metric directories for `checkpoint_best`, `checkpoint_final`, and any named post-warmup checkpoint.
- Do not use step-1 `checkpoint_best` as route-negative evidence unless the task is explicitly a smoke test.
