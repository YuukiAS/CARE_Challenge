---
task_key: "20260704_v25_contract_lock"
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
allow_code_change: false
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: false
mechanism_class: "contract extraction from existing SRR-v2.5 audit / implementation spec lock"
target_metric: "myops_scar, myops_edema"
required_evidence: ["contract_lock.md", "blocked_old_route.md", "implementation_spec.md", "MANIFEST.md"]
forbidden_substitutes: ["re-auditing the completed v2.5 audit as the main work", "model edit", "training", "validation packaging", "fold expansion", "treating audit output as route promotion"]
promotion_gate: "No route promotion is allowed. This task only converts the existing audit into a binding implementation contract."
route_promotion_gate: "No route promotion from this subtask."
minimum_effective_training:
  min_optimizer_steps: 0
  min_train_loop_seconds: 0
  require_one_batch_overfit: false
  require_prediction_sanity: false
  require_loss_decrease: false
  allow_stop_without_training: true
experiment_adequacy_gate: "Not a training task. The only adequacy question is whether the implementation contract is explicit enough to block the old lazy route."
route_negative_gate: "No STOP_NO_* route-negative conclusion from this task."
failure_escalation_policy: "If existing audit files are missing or contradictory, write NEEDS_EVIDENCE. Otherwise do not spend time re-auditing; lock the contract and move to implementation."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Lock SRR-v2.5 Repair Contract From Existing Audit

## Goal

Do not re-audit the completed SRR-v2.5 compliance audit. The audit already answered the core question: the current formal route is not diagram-compliant and should not be trained longer as the main fix. This subtask must extract that conclusion into a binding implementation contract so later executors cannot repeat the lazy pattern of name-compatible code, tiny capacity, random prototypes, full-volume residual heads, unsafe no-T2 edema inference, or undertrained evidence.

## Required Reads

Read the existing evidence exactly once, then write the contract: `prompts/tasks/20260704_srr_v25_compliance_audit.md`, `results/20260704_srr_v25_compliance_audit/result.md`, `results/20260704_srr_v25_compliance_audit/diagram_contract_mapping.md`, `results/20260704_srr_v25_compliance_audit/failure_root_cause.md`, `results/20260704_srr_v25_compliance_audit/implementation_recommendation.md`, `results/20260704_srr_v25_compliance_audit/nnunet_anchor_gap.md` if present, `results/20260703_srr_formal_training/metrics_summary.md`, and `results/20260703_srr_formal_training/review.md`.

If an existing audit file is absent, write `evidence not found`. Do not create a new architecture audit unless two existing audit files directly contradict each other.

## Contract Items To Lock

The contract must explicitly block: continuing the current `SRRProposeRefineMyoPS` as a from-scratch final segmenter; using three-scale `10/20/40` or similar toy capacity as final SRR-v2.5 evidence; treating current `ScaleRetrieval` as a true dictionary when it is only one shared ConvBlock, one private ConvBlock per modality, optional pair blocks, and softmax gates; calling randomly initialized `nn.Parameter` positive/negative vectors a completed pathology dictionary; using full-volume residual refinement as a soft-ROI crop refiner; allowing edema output on no-T2 cases without explicit reviewed safety logic; claiming scientific failure from runs that fail the effective training budget or skip overfit, prediction sanity, proposal sanity, cache isolation, and same-split nnU-Net comparison.

The contract must also state the required repair direction: nnU-Net probabilities/logits/predictions/components must be consumable as anchor evidence; the segmentation retrieval bank must contain multiple representer slots per shared/private/interaction group and must report slot usage, gate entropy, collapse status, and SIP/load-balancing/coverage diagnostics; pathology prototype banks must be data-derived or explicitly initialized from train/OOF features, not only random trainable tensors; proposal logits must include positive-vs-negative similarity, nnU-Net component/evidence anchors, anatomy/distance priors, and no-T2 edema gating; scar and edema refinement must use true crop/ROI evidence from original LGE/T2 where available, with soft containment rather than hard deletion.

## Required Outputs

Write under `results/20260704_v25_contract_lock/`: `result.md` with `contract_decision: LOCKED | NEEDS_EVIDENCE | NEEDS_REVISION`, `contract_lock.md`, `blocked_old_route.md`, `implementation_spec.md`, and `MANIFEST.md`.

## Completion Definition

Completion is a read-only contract lock. It does not authorize training, fold expansion, validation packaging, upload, or route promotion. If the contract cannot be locked because evidence is missing, stop with `NEEDS_EVIDENCE` instead of filling gaps by speculation.
