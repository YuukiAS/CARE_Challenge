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
mechanism_class: "cine_temporal / registration_or_warping_option_matrix / temporal dictionary diagnostic"
target_metric: "myocardium_cinemyops diagnostic proxy"
required_evidence: ["reference_frame_policy", "non_reference_frame_usage", "registration_option_matrix", "motion_or_warping_evidence", "temporal_dictionary_evidence", "frame0_baseline_comparison", "label_export_QC", "MANIFEST.md"]
forbidden_substitutes: ["frame0-only as temporal completion", "descriptor-only called registration", "translation-only alignment as registration completion", "one optical-flow proxy with folding burden as validated registration", "Cine work blocking MyoPS GPU", "hosted metric claim without upload result", "validation packaging/upload"]
promotion_gate: "No route promotion from this subtask alone."
minimum_effective_training:
  min_optimizer_steps: 0
  min_train_loop_seconds: 0
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  allow_stop_without_training: false
failure_escalation_policy: "If real registration/warping cannot be run, compare the available options and mark missing evidence honestly. Do not call weak alignment completed registration."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Resume Cine With Registration Options And Temporal Dictionary Evidence

## Goal

Move Cine forward in parallel without blocking MyoPS. The task is to strengthen `myocardium_cinemyops` diagnostic evidence using an anatomy-first temporal route. It must compare meaningful motion/registration/warping options and must not stop at frame0, reference-only, descriptor-only, or translation-only evidence.

## Required Reads

Read existing Cine diagnostics and code if present: `results/20260703_cine_motion/result.md` and `review.md`, `results/20260703_cine_motion/temporal_metrics_summary.md`, `results/20260703_cine_motion/motion_or_warp_summary.csv`, `code/CineMyoPS/prepare_task026_cine_4d.py`, `scripts/diagnostics/cinemyops_raw_structure_audit.py`, `scripts/evaluation/debug_cinemyops_inference_semantics.py`, `scripts/evaluation/cine_motion_hardmode_20260703.py`, and any current frame0/topology baseline result paths named in README or recent results.

## Registration / Warping Option Matrix

Write a ranked option matrix before coding or running. At minimum consider:

1. `frame0_reference_control`: baseline only, not temporal completion.
2. `current_optical_flow_or_feature_warp_proxy`: may reuse prior code, but must report warp sanity and folding proxy burden.
3. `CineMyoPS_or_U-MyoPS_style_TPS_if_code_available`: use repo/third-party TPS-style code only if available and label/space assumptions are clear; otherwise mark `evidence not found`.
4. `SyN_or_ANTs_if_installed`: classical deformable registration option; run only if installed and cheap enough. Otherwise record missing environment evidence.
5. `VoxelMorph_or_learning_based_registration_if_available`: use only if code/weights/license/environment are clear; otherwise record as future option, not completion.
6. `temporal_dictionary_aggregation`: ED anchor plus selected non-reference frames, motion/quality features, and frame-wise anatomy/texture representers.

The executor must compare at least two non-reference options if available. Translation-only may be listed as a baseline but cannot be the completed registration route. If no robust registration option is available, the task should still produce a useful matrix and a temporal dictionary diagnostic, but set the decision to `NEEDS_EVIDENCE` or `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP` rather than validated registration.

## Temporal Dictionary Requirement

Cine should share the SRR story at the principle level: MyoPS retrieves over modalities; Cine retrieves over temporal evidence. A valid Cine diagnostic should define ED/reference anchor features, non-reference warped or descriptor features, frame-quality/motion-saliency gates, and temporal representer usage. This does not need to be the same model as MyoPS, but it must be narratively compatible as selective representation retrieval under partial observation.

If CineMA, CorSeg, or another anatomy prior is used, report code path, weight source, license/compliance caveat, class mapping, and whether it is only anatomy support or a pathology head. Current evidence that CineMA-style anatomy improves local proxy is useful, but it cannot be called a hosted challenge improvement without hosted results.

## Required Evidence

Report reference frame definition, non-reference frame indices, option matrix, transform type, registration/warp sanity, temporal aggregation rule, temporal dictionary gate/usage if implemented, frame0/reference baseline comparison, class_1 myocardium proxy and class_3 sanity if available, label/raw mapping and export caveat, runtime/resource use, and proof it did not block MyoPS primary jobs.

## Required Outputs

Write under `results/20260704_cine_temporal_motion_resume/`: `result.md` with `cine_temporal_decision: PASS_DIAGNOSTIC | PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP | CINE_REFERENCE_ONLY | NEEDS_REVISION | NEEDS_EVIDENCE`, `reference_frame_policy.md`, `registration_option_matrix.md`, `temporal_dictionary_contract.md`, `temporal_evidence.md`, `motion_or_warp_sanity.csv` if computed, `metrics_summary.md` if metrics are computed, `label_export_qc.md`, and `MANIFEST.md`.

## Completion Definition

Completion requires non-reference frame evidence and an honest registration option matrix. If only reference/frame0 is used, set `CINE_REFERENCE_ONLY`. If non-reference evidence exists but validated registration is still missing, say so and do not claim registration completion.
