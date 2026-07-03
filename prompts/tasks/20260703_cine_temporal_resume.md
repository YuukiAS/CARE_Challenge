---
task_key: "20260703_cine_temporal_resume"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session via prompts/tasks/20260703_mainline_resume_goal.md"
executor: "separate Codex executor session/subagent"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "Cine temporal geometry / non-reference frame recovery"
target_metric: "myocardium_cinemyops local proxy only unless hosted evidence exists"
same_split_baseline: "reference-only/frame0 Cine control plus prior Cine diagnostic packets; evidence not found if unavailable"
required_evidence: ["result.md", "review.md", "MANIFEST.md", "safe_cases_used.csv", "reference_frame_contract.md", "motion_or_warp_metrics.csv", "temporal_metrics_summary.md", "case_metrics.csv", "label_export_QC"]
forbidden_substitutes: ["frame0-only completion", "translation-only stop", "descriptor-only registration claim", "MyoPS GPU blockage", "validation upload or fold expansion"]
experiment_adequacy_gate: "Cine temporal conclusions require non-reference frame use, reference-control comparison, geometry/mismatch caveat, prediction sanity, and local proxy metric evidence."
promotion_gate: "Cine can only be diagnostic unless hosted/official metric evidence exists."
failure_escalation_policy: "If only frame0/reference evidence exists, write NEEDS_EVIDENCE. If non-reference proxy is diagnostic-only, publish diagnostic evidence but do not promote."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_MONITOR", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Cine Temporal Resume

## Goal

Resume Cine only as a secondary route after MyoPS formal training is launched or while MyoPS jobs are waiting. This task must not block the SRR formal-training primary task.

The goal is to produce a clean temporal diagnostic packet for `myocardium_cinemyops`: reference frame contract, safe/mismatch split, non-reference frame evidence, motion/warping or descriptor temporal aggregation, and reference-only comparison.

## Required reads

Read `prompts/EXPERIMENT_ADEQUACY_GATE.md`, `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`, `results/20260703_cine_motion/result.md`, `results/20260703_cine_motion/review.md`, prior Cine geometry/safe-case evidence if present, and current Cine data loader/evaluator/proxy code.

## Required execution

1. Confirm 59 safe cases and 5 mismatch cases or write `NEEDS_EVIDENCE` if the split cannot be reproduced.
2. Recheck reference-only/frame0 baseline.
3. Use at least one non-reference frame route: optical-flow/feature-warp proxy, temporal descriptor aggregation, or reviewed local anatomy-prior temporal adapter.
4. Report reference dominance, temporal consistency, geometry caveats, and local proxy metrics.
5. Do not call descriptor output registration. Do not use translation-only negative evidence as completion.
6. Do not use GPU resources needed by MyoPS formal training.

## Required outputs

Write under `results/20260703_cine_temporal_resume/`: `result.md`, `MANIFEST.md`, `safe_cases_used.csv`, `mismatch_cases_heldout.csv`, `reference_frame_contract.md`, `motion_or_warp_metrics.csv`, `temporal_metrics_summary.md`, `case_metrics.csv`, `label_export_qc.md`, `failure_interpretation.md`, and `command_transcript.md`.

## Decision rules

Allowed decisions: `AUDIT_FOR_PROMOTION`, `DIAGNOSTIC_ONLY`, `NEEDS_EVIDENCE`, `NEEDS_REVISION`, `TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC`, `STOP_CINE_NO_TEMPORAL_SIGNAL`.

Do not use `STOP_CINE_NO_TEMPORAL_SIGNAL` unless non-reference frame evidence was actually evaluated. Executor stops at `EXECUTED_UNAUDITED` and awaits review.
