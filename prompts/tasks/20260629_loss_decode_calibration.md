---
task_key: "20260629_loss_decode_calibration"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "02:00:00"
max_parallel_gpu_jobs: 1
---

# Task 20260629 Loss/Decode Calibration Audit

## Objective

Audit and repair the most likely pipeline-level reasons why the SRR/Result5 route stays near 0.1 Dice even after long jobs. This task is intentionally non-conflicting with the still-running `20260628_myops_proposal` formal jobs. It should not kill, restart, overwrite, or reinterpret those jobs. It should work from existing checkpoints and isolated outputs first.

The purpose is to determine whether the current model has hidden pathology evidence that is being destroyed by loss masking, final logit composition, raw argmax decoding, or patch-loss checkpoint selection.

## Required reading

Read `AGENTS.md`, `prompts/AGENT_RULES.md`, `prompts/CHATGPT_RULES.md`, `docs/notes/20260629_result5_gap_audit.md`, `prompts/tasks/20260628_result5_goal.md`, `prompts/tasks/20260628_myops_proposal.md`, `src/care_myocardium/losses/srr_losses.py`, `src/care_myocardium/models/pathology_heads.py`, `src/care_myocardium/models/srr_myops.py`, `scripts/training/run_srr_myops_fold0.py`, and the latest `results/20260628_myops_proposal/progress.md`.

## Non-conflict rule

Use outputs under `results/20260629_loss_decode_calibration/`. Do not modify or delete `results/20260628_myops_proposal/variants/*`. Do not submit validation packages. Do not launch a long formal training job unless a small export/preflight has already identified the exact issue being tested.

## Audit targets

1. Verify whether all core losses properly ignore `IGNORE_LABEL = -1`. The proposal auxiliary loss already uses `valid = labels != IGNORE_LABEL`; core anatomy, scar, and edema losses must be checked and fixed if they treat padding as background.

2. Compare final output decoding semantics. At minimum export these modes from an existing completed checkpoint, preferably `proposal_pos_neg_basic` first, then any other completed variant:

   - `raw_argmax_current`: current `argmax(outputs["logits"])`.
   - `original_evidence_priority`: use original scar/edema evidence logits if present, apply calibrated sigmoid thresholds, then overlay pathology on anatomy.
   - `proposal_priority`: use proposal logits only, threshold pathology, then overlay on anatomy.
   - `mixed_priority`: use the current mixed scar/edema logits but decode pathology by priority threshold, not raw argmax.
   - `threshold_sweep`: sweep scar and edema thresholds on validation fold0 to report the best and stable ranges separately for scar and edema. Do not tune on hosted validation.

3. Compare `checkpoint_best.pt` and `checkpoint_final.pt` when both exist. If both are available, export both under isolated directories and report whether patch-loss best is worse than final on full-volume scar/edema Dice, HD95, component count, and remote FP.

4. Report binary-head evidence quality separately from final label Dice. For each completed proposal variant, compute lesion Dice from sigmoid thresholded scar/edema logits before raw argmax. The point is to learn whether the model has pathology signal hidden by multiclass logit competition.

## Repair scope

If a confirmed bug is found, implement the smallest safe repair in first-party code:

1. Add ignore-mask support to core anatomy/scar/edema losses.
2. Add an explicit `--decode-mode` or export-time decode option for pathology-priority decoding.
3. Add metrics that distinguish original evidence, proposal, mixed logits, and final argmax.
4. Add a future-safe checkpoint selection option based on pathology-aware validation metrics, but do not disturb currently running jobs.

All code changes must be backward-compatible. Existing Result5 jobs may continue with old code; this task should not invalidate their artifacts.

## Evaluation requirements

Write:

- `results/20260629_loss_decode_calibration/result.md`
- `results/20260629_loss_decode_calibration/MANIFEST.md`
- `results/20260629_loss_decode_calibration/decode_metrics.csv`
- `results/20260629_loss_decode_calibration/checkpoint_comparison.csv` if both best and final checkpoints are available
- `results/20260629_loss_decode_calibration/selection.md`

Selection states:

- `PIPELINE_BUG_CONFIRMED`
- `DECODE_CALIBRATION_SIGNAL`
- `CHECKPOINT_SELECTION_BUG`
- `NO_HIDDEN_EVIDENCE`
- `INSUFFICIENT_ARTIFACTS`

## Decision rule

If any pathology-priority or threshold-sweep decode is substantially better than raw argmax, treat the 0.1 result as a decoding/calibration failure and prioritize repair before any new formal Result5 repeat. If all decode modes remain near 0.1, the bottleneck is likely evidence/proposal/trunk quality rather than final argmax alone.
