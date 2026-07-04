---
task_key: "20260704_myops_soft_roi_no_t2_guardrails"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "20260704_anchor_srr_v25_goal controller"
executor: "Codex executor session"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "proposal_refinement / soft cascade / crop-based local refinement / no-T2 guardrails"
target_metric: "myops_scar, myops_edema"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB/CenterC if relevant"]
required_secondary_metrics: ["HD95", "component_count", "remote_FP", "volume_ratio", "proposal_recall", "proposal_precision", "outside_myocardium_FP", "no_T2_edema_voxels", "roi_coverage"]
required_evidence: ["crop_refiner_code", "crop_geometry_sanity", "one_case_forward", "roi_coverage", "no_t2_decode_sanity", "label_export_QC", "MANIFEST.md"]
forbidden_substitutes: ["full-volume residual head as crop refinement", "hard clipping as soft containment", "T2 crop use when T2 is absent", "loss-only no-T2 safety without inference/export guard", "validation-label tuned crop thresholds", "compact-label-only promotion"]
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

# Task: Implement True Soft-ROI Crop Refiners And No-T2 Guardrails

## Goal

Implement the real soft-ROI refinement and inference/export safety missing from the failed route. Scar and edema need separate refinement behavior and crop geometry. The task must not accept the old full-volume residual head as sufficient, and it must not treat T2-masked training loss as no-T2-safe inference.

## Prerequisites

Verify that `results/20260704_myops_proposal_proto_hardneg_impl/result.md` is `PASS_PREFLIGHT` or explicitly accepted by the controller. If proposal/prototype evidence is absent, stop with `NEEDS_EVIDENCE` unless this task is only writing guardrail code with no refinement claim.

## Required Soft-ROI Behavior

Scar refiner must use proposal, anatomy, distance, and uncertainty maps to create a small high-resolution soft ROI, consume original LGE crop and relevant anchor/proposal/dictionary features, and bias toward high precision and remote-FP reduction. Edema refiner must use a larger context-preserving ROI, consume original T2 crop only when T2 is present, use context/anatomy support, and keep no-T2-safe inference.

Both refiners must expose ROI coverage, crop bounds, foreground rate, empty-rate sanity, and component sanity. They must use soft containment, not hard case-specific rules. If crop extraction fails for small/empty proposals, implement a reviewed fallback such as anatomy-neighborhood soft ROI, not case-id logic or validation-label tuning.

## Required No-T2 Guardrails

No-T2 safety must exist in inference, decode, and export, not only in the loss. The executor must define how edema logits/proposals/refinement are gated when T2 is absent. It must report no-T2 edema voxel counts before and after the guardrail. It must preserve scar and anatomy behavior for no-T2 cases and must not use no-T2 myocardium as edema negative.

## Required Label/Export QC

Report raw/compact label semantics, decode mode, output labels, and submission-facing caveat. This task does not authorize validation packaging/upload, but it must ensure later packaging cannot silently map a compact-label local improvement to the wrong raw label values.

## Required Outputs

Write under `results/20260704_myops_soft_roi_no_t2_guardrails/`: `result.md` with `soft_roi_guardrail_decision: PASS_PREFLIGHT | NEEDS_REVISION | NEEDS_EVIDENCE | NEEDS_GPT_PLANNER`, `crop_geometry_sanity.md`, `roi_coverage.csv`, `forward_sanity.md`, `no_t2_decode_sanity.csv`, `label_export_qc.md`, `code_paths.md`, and `MANIFEST.md`.

## Completion Definition

Completion is preflight evidence that crops are real original-modality/local-feature crops and that no-T2 edema safety exists at inference/decode/export. Do not claim route promotion from this task.
