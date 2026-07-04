---
task_key: "20260704_myops_proposal_proto_hardneg_impl"
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
mechanism_class: "proposal_refinement / data-derived prototype memory / negative-space learning"
target_metric: "myops_scar, myops_edema"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB/CenterC if relevant"]
required_secondary_metrics: ["proposal_recall", "proposal_precision", "lesion_wise_recall", "outside_myocardium_FP", "remote_FP", "component_count", "HD95", "volume_ratio"]
required_evidence: ["prototype_bank_paths", "safe_negative_policy", "prototype_summary", "proposal_math.md", "hard_negative_summary", "unit_or_forward_sanity", "MANIFEST.md"]
forbidden_substitutes: ["random nn.Parameter prototypes as completed retrieval", "proposal logits from random prototype only", "proposal over old ScaleRetrieval without the new dictionary bank", "using no-T2 myocardium as edema negative", "using fold0 validation labels for train-time prototype fitting", "ignoring nnU-Net components", "unreviewed external data"]
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

# Task: Implement Anchored Proposals, Data-Derived Prototypes, And Hard-Negative Mining

## Goal

Build the pathology-specific proposal layer on top of nnU-Net anchors and the new dictionary bank. SRR should act as an evidence organizer and proposal/refinement system, not as a weak full-image dense head. Scar and edema must have separate proposal behavior because scar is LGE-dominant and high-precision oriented, while edema is T2-conditioned and missing-T2 sensitive.

## Prerequisites

Before editing proposal/prototype code, verify that `results/20260704_myops_anchor_inputs_decode_qc/result.md` and `results/20260704_myops_dictionary_retrieval_bank_impl/result.md` exist and are `PASS_PREFLIGHT` or explicitly accepted by the controller. If the dictionary task is missing or `NEEDS_REVISION`, stop with `NEEDS_EVIDENCE`.

## Required Proposal Behavior

The forward path must receive original LGE/C0/T2 tensors with availability mask, nnU-Net scar/edema probabilities or compact prediction channels, component masks/features derived from nnU-Net predictions when available, anatomy/union support from anchor prediction or anatomy logits, and dictionary-routed features. It must output scar and edema proposal logits/maps separately.

Proposal logits should be explicitly interpretable as positive-vs-negative pathology evidence. A valid formulation is a documented variant of `positive similarity - negative similarity + nnU-Net/component evidence + anatomy/distance prior`, not an unexplained one-layer dense head. Scar proposal must be LGE-dominant and high-precision oriented. Edema proposal must be T2-conditioned and missing-T2 safe.

## Required Prototype And Negative-Space Behavior

Replace random-only prototypes with data-derived scar and edema groups extracted from train/OOF dictionary-routed or anchor features. Build scar-positive prototypes; scar-safe-negative prototypes including normal myocardium, blood pool, outside myocardium, LGE artifact or hard FP where available; edema-positive prototypes only from T2-present labeled evidence; edema-safe-negative prototypes only from outside myocardium, blood pool, T2-present myocardium far from edema GT, reviewed artifact/hard FP. Do not use no-T2 myocardium as edema negative.

Hard-negative mining should sample high-confidence FP components from train/OOF evidence, not fold0 validation labels used for tuning. The task must record leakage policy and feature source. If data-derived banks cannot be built safely, stop with `NEEDS_EVIDENCE` rather than falling back to random prototypes and claiming completion.

## Required Evidence

Run CPU or small GPU forward sanity on one or a few cases. Report input tensor shapes and channel names, anchor channels consumed, dictionary features consumed, proposal foreground rates, proposal recall/precision if labels are available, lesion-wise recall where measurable, outside-myocardium FP ratio, no-T2 edema proposal volume under the reviewed policy, prototype feature source, prototype counts, and hard-negative source categories.

## Required Outputs

Write under `results/20260704_myops_proposal_proto_hardneg_impl/`: `result.md` with `proposal_proto_decision: PASS_PREFLIGHT | NEEDS_REVISION | NEEDS_EVIDENCE | NEEDS_GPT_PLANNER`, `code_paths.md`, `proposal_math.md`, `prototype_feature_source.md`, `safe_negative_policy.md`, `prototype_bank_summary.json`, `hard_negative_summary.csv`, `leakage_safety.md`, `forward_sanity.md`, `proposal_sanity.csv`, and `MANIFEST.md`.

## Completion Definition

Completion is implementation preflight, not scientific improvement. It is complete only if random prototype initialization is no longer the only proposal/prototype signal and if no-T2 edema safety is explicit. Do not claim route promotion from this task.
