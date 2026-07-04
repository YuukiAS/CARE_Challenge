---
task_key: "20260704_myops_anchor_inputs_decode_qc"
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
mechanism_class: "input inventory / label decode QC / nnU-Net anchor contract"
target_metric: "myops_scar, myops_edema"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB/CenterC if relevant"]
required_secondary_metrics: ["raw_label_values", "compact_label_values", "anchor_channel_shapes", "anchor_component_counts", "cache_isolation", "no_T2_edema_decode_policy"]
required_evidence: ["anchor_inventory.md", "decode_contract.md", "cache_policy.md", "one_case_io_sanity.md", "MANIFEST.md"]
forbidden_substitutes: ["using stale nnU-Net predictions without path/version", "compact-label proxy as challenge-facing proof", "missing availability mask", "no-T2 edema treated as negative", "starting model code before label/anchor contract is locked"]
promotion_gate: "No route promotion from this subtask alone."
minimum_effective_training:
  min_optimizer_steps: 0
  min_train_loop_seconds: 0
  require_one_batch_overfit: false
  require_prediction_sanity: true
  require_loss_decrease: false
  allow_stop_without_training: true
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Lock MyoPS Anchor Inputs, Decode, Label, And Cache QC

## Goal

Before any model repair, locate the exact nnU-Net fold0 anchor inputs and lock the decode/label/cache contract. This prevents Codex from using stale predictions, wrong compact/raw mapping, or incomplete no-T2 logic and then reporting artificial gains.

## Required Reads

Read `README.md`, `prompts/CARE_OVERLAY_GATES.md`, `results/20260704_v25_contract_lock/contract_lock.md` if present, `results/20260703_srr_formal_training/metrics_summary.md`, `results/20260703_srr_formal_training/review.md`, current Dataset501 nnU-Net fold0 validation summaries if present, and any script that loads nnU-Net predictions/probabilities/components such as `scripts/evaluation/run_nnunet_oof_component_20260703.py`.

## Required Checks

The executor must find or explicitly mark missing: nnU-Net fold0 prediction paths, probability/logit/npz paths, component masks or code to derive components, same-split baseline summary, original LGE/C0/T2 channel order, availability mask order, train/val split source, raw-to-compact and compact-to-raw mapping, cache naming policy, and no-T2 edema decode policy.

The no-T2 policy must distinguish training supervision from inference. T2-masked loss alone is not enough. If T2 is absent, edema proposal/refinement/decode must be blocked, zeroed, or explicitly marked diagnostic with a reviewed reason; no-T2 myocardium cannot be used as edema negative.

## Required Outputs

Write under `results/20260704_myops_anchor_inputs_decode_qc/`: `result.md` with `anchor_contract_decision: PASS_PREFLIGHT | NEEDS_EVIDENCE | NEEDS_REVISION`, `anchor_inventory.md`, `decode_contract.md`, `cache_policy.md`, `one_case_io_sanity.md`, optional `anchor_component_summary.csv`, and `MANIFEST.md`.

## Completion Definition

Completion means later code can consume anchor tensors and labels without ambiguity. If nnU-Net anchor artifacts are absent or the decode contract cannot be made leakage-safe, stop with `NEEDS_EVIDENCE` rather than implementing around the gap.
