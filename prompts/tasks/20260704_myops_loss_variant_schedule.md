---
task_key: "20260704_myops_loss_variant_schedule"
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
mechanism_class: "loss design / training schedule / controlled variant matrix / pathology-specific objectives"
target_metric: "myops_scar, myops_edema"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB/CenterC"]
required_secondary_metrics: ["Dice", "HD95", "component_count", "remote_FP", "outside_myocardium_FP", "volume_ratio", "proposal_recall", "proposal_precision", "lesion_wise_recall", "dictionary_slot_usage", "gate_entropy", "no_T2_edema_voxels"]
required_evidence: ["loss_contract.md", "variant_matrix.md", "training_schedule.md", "loss_unit_sanity.md", "overfit_plan.md", "metric_decision_table.md", "MANIFEST.md"]
forbidden_substitutes: ["one generic DiceCE loss for all heads without pathology-specific rationale", "recall-heavy edema loss reused as scar loss", "compactness-only or containment-only repair", "no-T2 samples contributing edema negative loss", "too many variants without a decision gate", "variant success judged only against old SRR rather than nnU-Net same split"]
promotion_gate: "No route promotion from this subtask alone."
minimum_effective_training:
  min_optimizer_steps: 0
  min_train_loop_seconds: 0
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  allow_stop_without_training: false
experiment_adequacy_gate: "This task must define losses and schedule and run only tiny loss/overfit sanity if needed. Formal performance evidence belongs to the fold0 formal task."
route_negative_gate: "No route-negative stop from loss/schedule design alone."
failure_escalation_policy: "If a loss cannot be computed without GT leakage, no-T2 misuse, or unstable gradients, mark that loss blocked and choose a safer variant. Do not silently drop the loss and claim the variant is complete."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: MyoPS Loss, Variant Matrix, And Training Schedule For Anchored SRR-v2.5

## Goal

Define and sanity-check the loss stack, variant matrix, and staged training schedule before formal fold0 training. The point is to prevent Codex from implementing architecture pieces but then training them with a generic loss, a one-phase unstable schedule, or an unbounded set of weak variants.

## Required Reads

Read `README.md` Lane A evidence, especially stopped routes around no-T2 edema, residual refiner, component/HD, and remote FP. Read `results/20260704_srr_v25_compliance_audit/implementation_recommendation.md`, `results/20260703_srr_formal_training/review.md`, `results/20260704_myops_dictionary_retrieval_bank_impl/result.md`, `results/20260704_myops_proposal_proto_hardneg_impl/result.md`, and `results/20260704_myops_soft_roi_no_t2_guardrails/result.md` if present.

## Loss Contract

The loss design must reflect scar and edema differences.

Scar is small, scattered, LGE-dominant, and HD/remote-FP sensitive. Scar losses should prioritize high precision, lesion-wise recall, boundary/HD sensitivity, component sanity, and negative-space discrimination. Candidate terms include DiceCE or DiceFocal for scar, positive/negative prototype margin, outside-myocardium FP penalty, weak boundary or distance-transform/HD surrogate, and optional lesion/component-aware term. Do not use a recall-heavy edema setting unchanged for scar.

Edema is larger, more diffuse, T2-conditioned, and missing-T2 sensitive. Edema losses should prioritize T2-present recall and localization while avoiding no-T2 false positives. Edema dense loss must be multiplied by T2 availability and label availability. No-T2 myocardium must not enter edema negative loss. Candidate terms include T2-masked DiceCE or DiceFocal, uncertainty-weighted boundary/context term, prototype margin using only safe negatives, soft anatomy support, and no-T2 inference/export guardrail loss or calibration term if implemented.

The dictionary/retrieval terms should include slot sparsity or entropy control, load-balancing, coverage across availability patterns, and collapse warnings. SIP-inspired regularization may be a soft coverage/load-balance surrogate; it does not need to copy the original R2/BR2 formula literally, but it must be documented.

The refinement terms should be applied after proposal sanity exists. Avoid compactness-only training on an unreliable proposal map. If using containment or distance priors, make them soft and uncertainty-aware rather than hard deletion.

## Training Schedule

Use a staged schedule unless the executor proves a simpler schedule is safer.

Stage 0: one-case/one-batch overfit and loss-gradient sanity for anatomy, scar, edema, dictionary gates, proposal margins, and refiner outputs. Stage 1: evidence/dictionary warmup, with nnU-Net anchors and anatomy/evidence heads stable. Stage 2: proposal/prototype and hard-negative learning, partially freezing lower trunk if needed. Stage 3: soft-ROI refiner training, with proposal kept fixed or slowly updated. Stage 4: low-learning-rate joint calibration, with no-T2 decode sanity and same-split nnU-Net comparison.

Each stage must define stop conditions, minimum evidence, and what to do if a component fails. Undertraining must be marked as such, not as a scientific failure.

## Variant Matrix

Keep the formal matrix small enough to run but rich enough to answer the mechanism question. At minimum define:

1. `anchored_srr_v25_full`: nnU-Net anchors + true dictionary + data-derived prototypes + soft-ROI crop refiners + no-T2 guardrails.
2. `anchored_scar_precision_edema_safe`: stronger scar negative/proposal precision, conservative T2-conditioned edema.
3. `anchored_conservative_cascade_no_proto_or_frozen_proto`: conservative fallback using nnU-Net anchor/components and soft ROI, with prototype learning reduced or frozen.

Optional ablations are allowed only if compute remains available and the controller approves: no SIP/load-balance, no hard-negative replay, or no crop refiner. Do not launch a large grid of temperature/threshold/router tweaks.

## Required Outputs

Write under `results/20260704_myops_loss_variant_schedule/`: `result.md` with `loss_variant_decision: PASS_PREFLIGHT | NEEDS_REVISION | NEEDS_EVIDENCE | NEEDS_GPT_PLANNER`, `loss_contract.md`, `variant_matrix.md`, `training_schedule.md`, `loss_unit_sanity.md`, `overfit_plan.md`, `metric_decision_table.md`, and `MANIFEST.md`.

## Completion Definition

Completion means formal training has a specific loss contract, a bounded variant matrix, and a staged schedule. It does not authorize validation packaging or route promotion.
