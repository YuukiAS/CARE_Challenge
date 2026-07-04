---
task_key: "20260704_myops_dictionary_retrieval_bank_impl"
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
mechanism_class: "missing_modality / segmentation-native retrieval dictionary / SRR-v2.5 repair"
target_metric: "myops_scar, myops_edema"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB/CenterC if relevant"]
required_secondary_metrics: ["HD95", "component_count", "remote_FP", "volume_ratio", "dictionary_slot_usage", "gate_entropy", "gate_collapse_rate", "availability_pattern_coverage"]
required_evidence: ["code_diff", "one_case_forward", "dictionary_stats.csv", "gate_usage_by_pattern.csv", "regularizer_sanity.md", "parameter_count", "MANIFEST.md"]
forbidden_substitutes: ["leaving ScaleRetrieval as one shared block plus one block per modality and calling it a dictionary", "random prototypes as retrieval dictionary", "softmax router without usage/collapse diagnostics", "missing-modality zero filling as evidence", "from-scratch final segmenter without nnU-Net anchor", "no SIP/load-balance/coverage diagnostic"]
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

# Task: Implement Segmentation-Native SRR Dictionary Bank

## Goal

Repair the main architectural shortcut in the current SRR implementation. The current route has names that resemble dictionary retrieval, but a valid SRR-v2.5 implementation must have a real multi-slot shared/private/interaction retrieval bank with measurable routing behavior. This task is a code-and-preflight task, not a performance-claim task.

## Required Reads

Read `results/20260704_v25_contract_lock/contract_lock.md` if present, `results/20260704_srr_v25_compliance_audit/diagram_contract_mapping.md`, `src/care_myocardium/models/srr_v2_unet.py`, `src/care_myocardium/models/srr_propref.py`, `src/care_myocardium/losses/srr_losses.py`, and `results/figures/srr_myops_architecture.py` or `images/SRR-v2.5.png` if accessible.

## Required Dictionary Behavior

Implement first-party code under `src/care_myocardium/` or adjacent first-party modules. A valid solution must satisfy these requirements unless a deviation is explicitly marked `NEEDS_REVISION` for review.

Per scale, expose a bank with multiple representer slots, not one ConvBlock per category. Suggested Lite defaults are `K_shared >= 4`, `K_lge >= 2`, `K_c0 >= 2`, `K_t2 >= 2`, and optional `K_mix >= 2` for available interaction pairs. The code must distinguish shared, LGE-private, C0-private, T2-private, and optional interaction slots. The router must be conditioned on both availability and pooled image/anchor features; availability-only lookup is insufficient. Missing modality private and interaction slots must be masked out when the modality is absent. Anatomy, scar, and edema must have task-specific gates. Scar should be able to prefer LGE/private and high-precision evidence; edema should be able to prefer T2/private evidence and must respect no-T2 gating.

Gating may use sparsemax, entmax, annealed soft top-k, or a temperature-controlled softmax with explicit top-k/entropy diagnostics. Plain softmax is allowed only for warmup and only if the task records why sparsity was deferred. Add at least a lightweight SIP/load-balancing/coverage diagnostic or regularizer. It must report slot usage by task, scale, and availability pattern; gate entropy; inactive slot count; and collapse warnings. Integrate nnU-Net anchor evidence if the anchor inventory exists. If anchor integration is deferred to proposal code, write the exact integration point and do not claim the dictionary is the final anchored route.

## Required Anti-Laziness Checks

The result must explicitly answer whether the old `ScaleRetrieval` remains on the active path, how many representer slots exist per scale and group, whether any slots are permanently unused in forward sanity, whether T2 slots are disabled when T2 is absent, whether gate usage and entropy are written to disk, and whether the dictionary path consumes nnU-Net anchor evidence or exactly where that integration occurs.

## Required Evidence

Run a small CPU or short GPU forward sanity on one or a few cases. Do not run formal training in this task. Record input names/shapes, availability patterns including complete and no-T2 if available, output feature shapes per task/scale, parameter counts and memory, dictionary slot usage by task/scale, gate entropy and collapse warnings, proof that missing T2 masks T2 slots, and cache/output path isolation.

## Required Outputs

Write under `results/20260704_myops_dictionary_retrieval_bank_impl/`: `result.md` with `dictionary_decision: PASS_PREFLIGHT | NEEDS_REVISION | NEEDS_EVIDENCE | NEEDS_GPT_PLANNER`, `code_paths.md`, `dictionary_contract.md`, `forward_sanity.md`, `dictionary_stats.csv`, `gate_usage_by_pattern.csv`, `regularizer_sanity.md`, and `MANIFEST.md`.

## Completion Definition

Completion requires a real multi-slot dictionary bank with measurable gate/slot behavior. If the implementation still amounts to previous `ScaleRetrieval` plus renamed variables, write `NEEDS_REVISION`. Do not claim route promotion or scientific success from this task.
