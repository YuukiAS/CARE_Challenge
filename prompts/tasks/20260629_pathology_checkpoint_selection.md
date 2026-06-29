---
task_key: "20260629_pathology_checkpoint_selection"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "04:00:00"
max_parallel_gpu_jobs: 1
---

# Task 20260629 Pathology-Aware Checkpoint Selection

## Objective

Replace or augment patch-loss-based checkpoint choice with pathology-aware selection. The current runner saves `checkpoint_best.pt` using patch validation loss, which may not correlate with full-volume scar/edema Dice, HD95, component count, or remote FP. This task evaluates existing checkpoints first and then prepares a future-safe checkpoint strategy.

This task should not interrupt any running proposal jobs. It can run after a variant completes, using isolated outputs.

## Required reading

Read `docs/notes/20260629_result5_gap_audit.md`, `scripts/training/run_srr_myops_fold0.py`, `scripts/evaluation/evaluate_predictions.py`, `results/20260628_myops_proposal/progress.md`, and all available `summary.json` / `training_log.csv` files under completed Result5 variants.

## Non-conflict rule

Use `results/20260629_pathology_checkpoint_selection/`. Do not delete or overwrite existing checkpoints. Do not change the current jobs in flight. Future code changes must be opt-in via flags or new variants.

## Required actions

1. For each completed Result5 proposal variant, evaluate both `checkpoint_best.pt` and `checkpoint_final.pt` if available.

2. Compute full-volume metrics for scar and edema: Dice, HD, HD95, component count, small FP, remote FP, empty prediction rate, and pred/GT volume ratio.

3. Compare patch-loss best vs final. Identify whether patch-loss selection is harming pathology metrics.

4. If intermediate checkpoints exist, evaluate a small top-k subset by mtime/step if feasible. If only best/final exist, record that limitation.

5. Add a future-safe selection mode to the runner or a companion script: after training, export/evaluate candidate checkpoints and select by a pathology-aware scalar, not only patch loss. The scalar should prioritize scar/edema metrics, not foreground anatomy mean.

6. Do not select based on hosted validation. This is fold0 local validation only.

## Suggested pathology-aware scalar

Use a transparent proxy such as:

`score = scar_all_dice + edema_t2_or_gtpos_dice - 0.001 * scar_hd95 - 0.001 * edema_hd95 - 0.02 * remote_fp_mean - 0.01 * component_count_mean`

The exact weights may be adjusted, but the report must explain the choice. Do not hide failures behind a scalar; always report component metrics.

## Outputs

Write:

- `results/20260629_pathology_checkpoint_selection/result.md`
- `results/20260629_pathology_checkpoint_selection/MANIFEST.md`
- `results/20260629_pathology_checkpoint_selection/checkpoint_metrics.csv`
- `results/20260629_pathology_checkpoint_selection/selection.md`

Selection states:

- `PATCH_BEST_CONFIRMED_OK`
- `FINAL_BETTER_THAN_PATCH_BEST`
- `PATHOLOGY_SELECTION_NEEDED`
- `INSUFFICIENT_CHECKPOINTS`
- `EVALUATION_BLOCKED`

## Stop conditions

Stop only for missing checkpoint files, evaluator contract errors, or geometry/read errors. Do not stop because metrics are bad; bad metrics are the object of this task.
