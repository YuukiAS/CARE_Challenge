---
task_key: "20260703_srr_formal_training"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session via prompts/tasks/20260703_mainline_resume_goal.md"
executor: "separate Codex executor session/subagent"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "SRR-ProposeRefine adequate formal training"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "same-split nnU-Net fold0 reference plus reviewed SRR repair code; evidence not found if unavailable"
required_evidence: ["result.md", "review.md", "MANIFEST.md", "experiment_adequacy_report.md", "one_batch_overfit", "checkpoint_policy", "prediction_sanity", "proposal_pr_sweep", "metric_csv", "run_log", "same_split_baseline", "cache_isolation", "label_export_QC"]
forbidden_substitutes: ["CPU smoke as formal training", "pending Slurm job marked complete", "STOP_NO_SIGNAL without adequacy", "step1 checkpoint as formal conclusion", "old SRR-v2 tuning route", "validation upload or fold expansion"]
minimum_effective_training: {min_optimizer_steps: 1500, min_train_loop_seconds: 1800, require_one_batch_overfit: true, require_prediction_sanity: true, require_loss_decrease: true, require_post_warmup_validation: true, allow_stop_without_training: false}
experiment_adequacy_gate: "Formal conclusions require actual GPU training, adequate optimizer steps/time, overfit sanity, post-warmup validation, best/final checkpoint comparison, prediction/decode sanity, proposal PR sanity, and provenance."
route_negative_gate: "A route-negative stop is allowed only if adequacy passes and metrics remain poor after pipeline bugs are excluded."
promotion_gate: "Promotion requires audited same-split improvement over nnU-Net or critical secondary metric improvement without unacceptable regression."
failure_escalation_policy: "If jobs are pending/running, report INCOMPLETE/NEEDS_MONITOR rather than COMPLETE. If launch fails, report NEEDS_REVISION or BLOCKED with logs."
allowed_next_states: ["EXECUTOR_RUNNING", "EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_MONITOR", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: SRR-ProposeRefine Formal Adequate Training

## Goal

Use the repaired SRR-ProposeRefine runner to run actual fold0 formal training. This task explicitly authorizes the adequate GPU run that the recovery controller did not complete. It is not a new research route and not old SRR-v2 tuning.

## Required reads

Read `prompts/EXPERIMENT_ADEQUACY_GATE.md`, `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`, `prompts/CONTROLLER_TASK_PROTOCOL.md`, `results/20260703_srr_propref_repair/review.md`, `results/20260703_srr_recovery_goal/controller_report.md`, `scripts/training/run_srr_propref_myops_fold0.py`, `jobs/src/run_srr_propref_myops_fold0.sh`, and same-split nnU-Net reference paths.

## Required execution

1. Run syntax/config checks, but do not count them as formal evidence.
2. Launch formal GPU training under `results/20260703_srr_formal_training/` using the repaired runner and `htzhulab` when available.
3. Run at least `srr_propref_shared_dual_dict` adequately. Run all three variants if resources allow: `srr_propref_shared_dual_dict`, `srr_propref_scar_precision`, `srr_propref_no_proto_cascade`.
4. Use `MAX_STEPS>=1800`, no `MAX_STEPS=120` override. Keep `VAL_EVERY<=300`. Do not use CPU smoke as a substitute.
5. If jobs are still pending or running when the session must end, write a monitor packet and set status `NEEDS_MONITOR` or `EXECUTOR_RUNNING`, not complete.
6. After completed jobs, aggregate best and final checkpoint metrics, prediction sanity, PR sweep, label/export QC, and same-split comparison.

## Required outputs

Write under `results/20260703_srr_formal_training/`: `result.md`, `MANIFEST.md`, `job_status.md`, `experiment_adequacy_report.md`, `checkpoint_policy.md`, `prediction_sanity.md`, `proposal_pr_sweep.csv`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `roi_coverage.csv`, `label_export_qc.md`, `failure_interpretation.md`, and `command_transcript.md`.

## Decision rules

Allowed decisions are `AUDIT_FOR_PROMOTION`, `DIAGNOSTIC_ONLY`, `NEEDS_MONITOR`, `NEEDS_EVIDENCE`, `NEEDS_REVISION`, `SCIENTIFIC_UNDERTRAINED`, `STOP_PIPELINE_BUG`, and `STOP_NO_PROPREF_SIGNAL`.

Do not use `STOP_NO_PROPREF_SIGNAL` unless experiment adequacy passes. Do not mark the task complete while formal jobs are still pending or running. Executor stops at `EXECUTED_UNAUDITED` only after artifacts are ready for audit.
