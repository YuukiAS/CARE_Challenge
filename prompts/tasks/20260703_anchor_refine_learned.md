---
task_key: "20260703_anchor_refine_learned"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session via prompts/tasks/20260703_srr_recovery_goal.md"
executor: "separate Codex executor session/subagent"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "CARE model refinement"
target_metric: "myops_scar, myops_edema"
required_evidence: ["result.md", "review.md", "MANIFEST.md", "training_summary.md", "checkpoint", "prediction_path", "metric_csv", "run_log", "same_split_baseline", "label_export_QC"]
forbidden_substitutes: ["deterministic postprocess labeled as learned refiner", "preflight-only completion", "fold expansion"]
minimum_effective_training: {min_optimizer_steps: 800, min_train_loop_seconds: 900, require_one_batch_overfit: true, require_prediction_sanity: true, require_loss_decrease: true, allow_stop_without_training: false}
experiment_adequacy_gate: "Conclusions require actual training, checkpoint evidence, overfit sanity, prediction sanity, and same-split baseline comparison."
route_negative_gate: "A stop decision requires training adequacy. Missing learned evidence means NEEDS_EVIDENCE or SCIENTIFIC_UNDERTRAINED."
promotion_gate: "Promotion requires audited improvement over unchanged same-split nnU-Net."
failure_escalation_policy: "If prerequisite evidence is missing, write NEEDS_EVIDENCE. If only deterministic postprocess is possible, classify diagnostic-only."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Learned Anchor Refine

Use this task only after reviewed prerequisite evidence exists from the SRR repair and component scorer tasks. The previous anchor-refine package was diagnostic postprocessing, not learned training. Produce a trained fold0 refinement artifact with audited metrics, or write `NEEDS_EVIDENCE`.

## Required work

Implement a small learned refiner anchored to the existing nnU-Net fold0 baseline, or document why prerequisite evidence is missing. The learned route must record one-batch overfit, optimizer-step count, training time, loss trend, checkpoint, predictions, same-split metrics, and label/export QC. A deterministic rule may only be a diagnostic baseline.

## Required outputs

Write outputs under `results/20260703_anchor_refine_learned/`: `result.md`, `MANIFEST.md`, `training_summary.md`, `one_batch_overfit.md`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `teacher_student_delta.csv`, `label_export_qc.md`, `failure_interpretation.md`, and `command_transcript.md`.

## Decision rules

Allowed decisions: `AUDIT_FOR_PROMOTION`, `DIAGNOSTIC_ONLY`, `NEEDS_EVIDENCE`, `NEEDS_REVISION`, `SCIENTIFIC_UNDERTRAINED`, `STOP_PIPELINE_BUG`, `STOP_NO_LEARNED_ANCHOR_SIGNAL`.

Do not use `STOP_NO_LEARNED_ANCHOR_SIGNAL` unless learned training evidence passes adequacy gates. Executor stops at `EXECUTED_UNAUDITED`.
