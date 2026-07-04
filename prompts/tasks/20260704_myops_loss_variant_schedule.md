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
mechanism_class: "SRR-v2/v2.5 loss design / training schedule / controlled variant matrix / pathology-specific objectives"
target_metric: "myops_scar, myops_edema"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB/CenterC"]
required_secondary_metrics: ["Dice", "HD95", "component_count", "remote_FP", "outside_myocardium_FP", "volume_ratio", "proposal_recall", "proposal_precision", "lesion_wise_recall", "dictionary_slot_usage", "gate_entropy", "no_T2_edema_voxels", "loss_plateau_or_convergence_status"]
required_evidence: ["loss_contract.md", "diagram_loss_mapping.md", "variant_matrix.md", "training_schedule.md", "loss_unit_sanity.md", "overfit_plan.md", "metric_decision_table.md", "MANIFEST.md"]
forbidden_substitutes: ["one generic DiceCE loss for all heads without SRR-v2/v2.5 mapping", "inventing unrelated losses not tied to anatomy/proposal/refinement/dictionary/prior", "recall-heavy edema loss reused as scar loss", "compactness-only or containment-only repair", "no-T2 samples contributing edema negative loss", "too many variants without a decision gate", "variant success judged only against old SRR rather than nnU-Net same split", "training plan based only on a fixed tiny number of steps"]
promotion_gate: "No route promotion from this subtask alone."
minimum_effective_training:
  train_until: "formal task must train until plateau/early stopping/budget, not a hard small step count"
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  allow_stop_without_training: false
experiment_adequacy_gate: "This task must define losses and schedule and run only tiny loss/overfit sanity if needed. Formal performance evidence belongs to the fold0 formal task."
route_negative_gate: "No route-negative stop from loss/schedule design alone."
failure_escalation_policy: "If a loss cannot be computed without GT leakage, no-T2 misuse, or unstable gradients, mark that loss blocked and choose a safer diagram-consistent variant. Do not silently drop the loss and claim the variant is complete."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: SRR-v2/v2.5 Loss, Variant Matrix, And Training Schedule

## Goal

Define and sanity-check the loss stack, variant matrix, and staged training schedule before formal fold0 training. The loss implementation must follow the SRR-v2/v2.5 architecture contract, not an ad hoc collection of convenient segmentation losses. This prevents Codex from implementing the architecture pieces but then training them with a generic loss, a one-phase unstable schedule, or an unbounded set of weak variants.

## Required Reads

Read the SRR-v2/v2.5 diagram contract from `prompts/tasks/20260704_srr_v25_compliance_audit.md`, `results/20260704_srr_v25_compliance_audit/diagram_contract_mapping.md`, `results/20260704_srr_v25_compliance_audit/implementation_recommendation.md`, and `results/figures/srr_myops_architecture.py` or `images/SRR-v2.5.png` if accessible. Also read `README.md` Lane A evidence, especially stopped routes around no-T2 edema, residual refiner, component/HD, and remote FP.

## Diagram-Loss Mapping

Write `diagram_loss_mapping.md` before coding. It must map each SRR-v2/v2.5 block to a loss or diagnostic:

- anatomy decoder: Dice/CE or DiceCE for `P_union`, `P_LV`, `P_RV` when labels exist;
- scar proposal: LGE-dominant proposal loss, positive-vs-negative prototype margin, safe hard-negative loss, and weak boundary/HD or distance surrogate;
- edema proposal: T2-conditioned proposal loss and prototype margin only on T2-present labeled evidence;
- scar refinement: local crop refinement loss with precision/remote-FP/HD sensitivity;
- edema refinement: larger-context T2-present refinement loss with boundary/context/uncertainty support;
- negative space: outside-myocardium, blood pool, normal myocardium, artifact, and hard-FP categories with edema-safe negative policy;
- soft anatomy prior and ROI: soft containment/ROI regularizer, not hard deletion;
- dictionary/retrieval: sparsity or entropy control, load balancing, coverage across availability patterns, slot collapse warnings, prototype diversity;
- optional alignment: only if alignment evidence supports it; otherwise do not invent an alignment loss.

If a diagram loss cannot be implemented safely, mark it blocked with a reason. Do not replace it with an unrelated loss and claim v2/v2.5 completion.

## Scar And Edema Differences

Scar is small, scattered, LGE-dominant, and HD/remote-FP sensitive. Scar losses should prioritize high precision, lesion-wise recall, boundary/HD sensitivity, component sanity, and negative-space discrimination. Do not use a recall-heavy edema setting unchanged for scar.

Edema is larger, more diffuse, T2-conditioned, and missing-T2 sensitive. Edema dense/proposal/refinement losses must be multiplied by T2 availability and label availability. No-T2 myocardium must not enter edema negative loss. Edema should use safe negatives only and maintain explicit no-T2 inference/export guardrails.

## Training Schedule

Use a staged schedule unless the executor proves a simpler schedule is safer. Stage 0 is one-case/one-batch overfit and loss-gradient sanity for anatomy, scar, edema, dictionary gates, proposal margins, and refiner outputs. Stage 1 is evidence/dictionary warmup with nnU-Net anchors. Stage 2 is proposal/prototype and hard-negative learning. Stage 3 is soft-ROI refiner training. Stage 4 is low-learning-rate joint calibration with no-T2 decode sanity and same-split nnU-Net comparison.

The formal task should train like a normal segmentation paper implementation: validate regularly, keep best checkpoints, use early stopping or plateau evidence, and stay within the 8h round budget. Do not define success or failure from a fixed tiny step count.

## Variant Matrix

Keep the formal matrix small enough to run but rich enough to answer the mechanism question. At minimum define: `anchored_srr_v25_full`, `anchored_scar_precision_edema_safe`, and `anchored_conservative_cascade_no_proto_or_frozen_proto`. Optional ablations are allowed only if compute remains available and the controller approves: no SIP/load-balance, no hard-negative replay, or no crop refiner. Do not launch a large grid of temperature/threshold/router tweaks.

## Required Outputs

Write under `results/20260704_myops_loss_variant_schedule/`: `result.md` with `loss_variant_decision: PASS_PREFLIGHT | NEEDS_REVISION | NEEDS_EVIDENCE | NEEDS_GPT_PLANNER`, `loss_contract.md`, `diagram_loss_mapping.md`, `variant_matrix.md`, `training_schedule.md`, `loss_unit_sanity.md`, `overfit_plan.md`, `metric_decision_table.md`, and `MANIFEST.md`.

## Completion Definition

Completion means formal training has a diagram-consistent loss contract, a bounded variant matrix, and a staged schedule. It does not authorize validation packaging or route promotion.
