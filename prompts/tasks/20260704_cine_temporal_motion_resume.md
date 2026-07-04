---
task_key: "20260704_cine_temporal_motion_resume"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "20260704_anchor_srr_v25_goal controller"
executor: "Codex executor session"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "cine_temporal / motion_or_warping / temporal aggregation diagnostic"
target_metric: "myocardium_cinemyops diagnostic proxy"
required_evidence: ["reference_frame_policy", "non_reference_frame_usage", "motion_or_warping_evidence", "temporal_aggregation_metrics", "frame0_baseline_comparison", "label_export_QC", "MANIFEST.md"]
forbidden_substitutes: ["frame0-only as temporal completion", "descriptor-only called registration", "Cine work blocking MyoPS GPU", "hosted metric claim without upload result", "validation packaging/upload"]
promotion_gate: "No route promotion from this subtask alone."
minimum_effective_training:
  min_optimizer_steps: 0
  min_train_loop_seconds: 0
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  allow_stop_without_training: false
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Resume Cine Secondary Route With Non-Reference Temporal Evidence

## Goal

Move Cine forward in parallel without blocking MyoPS. The task is not to chase cine pathology from scratch. It is to verify and improve `myocardium_cinemyops` diagnostic proxy using anatomy-first temporal evidence: ED/reference frame, selected non-reference frames, motion/warping/aggregation, and consistency.

## Required Reads

Read existing Cine diagnostics and code if present: `results/20260703_cine_motion/result.md` and `review.md` if present, `code/CineMyoPS/prepare_task026_cine_4d.py`, `scripts/diagnostics/cinemyops_raw_structure_audit.py`, `scripts/evaluation/debug_cinemyops_inference_semantics.py`, and any current frame0/topology baseline result paths named in README or recent results.

## Required Evidence

Report reference frame definition, which non-reference frames enter, whether a transform/warp exists or whether this is only a descriptor route, temporal aggregation rule, frame0/reference-only baseline comparison, class_1 myocardium proxy and class_3 sanity if available, label/raw mapping and export caveat, compute resource use, and proof it did not block MyoPS primary jobs.

## Allowed Work

You may implement small first-party temporal aggregation, motion descriptor, or warping sanity scripts. If true warping/registration is not implemented, say so. Do not call descriptor-only evidence completed registration. If the route needs external weights such as CineMA/CorSeg, stop for explicit evidence/permission if license or availability is unclear.

## Required Outputs

Write under `results/20260704_cine_temporal_motion_resume/`: `result.md` with `cine_temporal_decision: PASS_DIAGNOSTIC | CINE_REFERENCE_ONLY | NEEDS_REVISION | NEEDS_EVIDENCE`, `reference_frame_policy.md`, `temporal_evidence.md`, `metrics_summary.md` if metrics are computed, `label_export_qc.md`, and `MANIFEST.md`.

## Completion Definition

Completion requires non-reference frame evidence. If only reference/frame0 is used, set `CINE_REFERENCE_ONLY` and stop without claiming temporal method completion.
