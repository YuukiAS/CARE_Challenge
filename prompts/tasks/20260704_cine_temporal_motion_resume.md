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
allow_network: true
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "cine_temporal / CineMA anatomy prior / registration option matrix / temporal dictionary diagnostic"
target_metric: "myocardium_cinemyops diagnostic proxy"
required_evidence: ["reference_frame_policy", "CineMA_or_blocker_evidence", "non_reference_frame_usage", "registration_option_matrix", "motion_or_warping_evidence", "temporal_dictionary_evidence", "frame0_baseline_comparison", "label_export_QC", "MANIFEST.md"]
forbidden_substitutes: ["skipping CineMA without attempt or blocker evidence", "frame0-only as temporal completion", "descriptor-only called registration", "translation-only alignment as registration baseline", "single weak warp proxy with bad sanity as validated registration", "Cine work blocking MyoPS GPU", "hosted metric claim without upload result", "validation packaging/upload"]
promotion_gate: "No route promotion from this subtask alone."
minimum_effective_training:
  train_until: "diagnostic route must run enough frames/cases to compare options or report resource blocker"
  require_prediction_sanity: true
failure_escalation_policy: "If CineMA or stronger registration cannot be run, use the external asset registry and command errors as evidence. Do not call weak alignment completed registration."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Resume Cine With CineMA, Registration Options, And Temporal Dictionary Evidence

## Goal

Move Cine forward in parallel without blocking MyoPS. The task is to strengthen `myocardium_cinemyops` diagnostic evidence using an anatomy-first temporal route. It must make a serious attempt to use CineMA or a documented blocker from `20260704_external_assets_cinema_registration`. It must compare meaningful registration or warping options and avoid stopping at frame0, descriptor-only, or translation-only evidence.

## Required Reads

Read `results/20260704_external_assets_cinema_registration/usable_asset_matrix.md` if present. Also read existing Cine diagnostics and code: `results/20260703_cine_motion/result.md` and `review.md`, `results/20260703_cine_motion/temporal_metrics_summary.md`, `results/20260703_cine_motion/motion_or_warp_summary.csv`, `code/CineMyoPS/prepare_task026_cine_4d.py`, `scripts/diagnostics/cinemyops_raw_structure_audit.py`, `scripts/evaluation/debug_cinemyops_inference_semantics.py`, `scripts/evaluation/cine_motion_hardmode_20260703.py`, and any current frame0/topology baseline result paths named in README or recent results.

## CineMA Requirement

Try CineMA first for frame-wise cine anatomy support unless the external asset task records a hard blocker. If CineMA cannot be used, try the next usable cine anatomy prior from the asset registry. Report source path, version, local path, class mapping, input preprocessing, output labels, and whether the model is anatomy-only or pathology-capable.

## Registration / Warping Option Matrix

Write a ranked option matrix before coding or running. Translation is not a valid registration baseline for this task. At minimum consider: frame0 reference control, SyN/ANTs, TPS-style code from repo or available third-party code, VoxelMorph or equivalent learning-based registration, current optical-flow or feature-warp proxy, and temporal dictionary aggregation.

The executor must compare at least two non-reference options if available. If no robust registration option can run, produce the matrix and a temporal dictionary diagnostic, but set the decision to `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP` or `NEEDS_EVIDENCE`, not validated registration.

## Temporal Dictionary Requirement

Cine should share the SRR story at the principle level: MyoPS retrieves over modalities; Cine retrieves over temporal evidence. Define ED/reference anchor features, non-reference warped or descriptor features, frame-quality or motion-saliency gates, and temporal representer usage.

## Required Outputs

Write under `results/20260704_cine_temporal_motion_resume/`: `result.md` with `cine_temporal_decision: PASS_DIAGNOSTIC | PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP | CINE_REFERENCE_ONLY | NEEDS_REVISION | NEEDS_EVIDENCE`, `reference_frame_policy.md`, `cinema_adapter_status.md`, `registration_option_matrix.md`, `temporal_dictionary_contract.md`, `temporal_evidence.md`, `motion_or_warp_sanity.csv` if computed, `metrics_summary.md` if metrics are computed, `label_export_qc.md`, and `MANIFEST.md`.

## Completion Definition

Completion requires a CineMA/equivalent attempt, non-reference frame evidence, and an honest registration option matrix. If only reference/frame0 is used, set `CINE_REFERENCE_ONLY`. If non-reference evidence exists but validated registration is still missing, say so and do not claim registration completion.
