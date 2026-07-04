---
task_key: "20260704_myops_anchor_srr_fold0_formal"
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
mechanism_class: "formal MyoPS training / dictionary / proposal_refinement / missing_modality"
target_metric: "myops_scar, myops_edema"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB/CenterC if relevant"]
required_secondary_metrics: ["Dice", "HD95", "component_count", "remote_FP", "volume_ratio", "dictionary_slot_usage", "gate_entropy", "proposal_recall", "proposal_precision", "outside_myocardium_FP", "no_T2_edema_voxels"]
required_evidence: ["one_batch_overfit", "training_log", "checkpoint", "prediction_path", "metric_csv", "subgroup_metrics", "component_hd_by_case", "dictionary_stats", "proposal_pr_sweep", "no_T2_decode_sanity", "label_export_QC", "same_split_baseline", "MANIFEST.md"]
forbidden_substitutes: ["CPU smoke as formal training", "pending jobs marked complete", "short run below budget used as route-negative stop", "current tiny PropRef training", "stale cache", "compact-label-only promotion", "undertrained result marked STOP_NO_SIGNAL"]
promotion_gate: "No route promotion without separate read-only audit."
minimum_effective_training:
  min_optimizer_steps: 1800
  min_train_loop_seconds: 1800
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  allow_stop_without_training: false
experiment_adequacy_gate: "Formal training requires one-batch/tiny-overfit, train_loop_seconds, max_steps, actual_steps, optimizer_steps, validation_events, loss_decrease, prediction sanity, dictionary sanity, proposal sanity, logs/provenance, cache isolation, and same-split baseline comparability."
route_negative_gate: "No STOP_NO_* conclusion unless adequacy PASS, same-split comparison, no forbidden substitute, and explicit auditor support."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_MONITOR", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Run Formal Fold0 Training/Evaluation For Anchored SRR-v2.5 Repair

## Goal

Run a formal fold0 train/evaluate cycle for the anchored SRR-v2.5 repair after the implementation and guardrail tasks pass. This is the first task that may generate real performance evidence, but it must still stop at `EXECUTED_UNAUDITED`.

## Prerequisites

Before submitting or running training, verify PASS/PASS_PREFLIGHT from `results/20260704_v25_contract_lock/result.md`, `results/20260704_myops_anchor_inputs_decode_qc/result.md`, `results/20260704_myops_dictionary_retrieval_bank_impl/result.md`, `results/20260704_myops_proposal_proto_hardneg_impl/result.md`, and `results/20260704_myops_soft_roi_no_t2_guardrails/result.md`. If any prerequisite is absent or `NEEDS_REVISION`, stop with `NEEDS_EVIDENCE` or `NEEDS_REVISION`.

## Training Budget

Use a controlled fold0 job on the CARE default GPU policy. Do not exceed the normal round budget. The minimum adequacy target is 1800 optimizer steps and 1800 train-loop seconds, with validation events, loss decrease, one-batch overfit, checkpoints, prediction sanity, dictionary sanity, proposal sanity, no-T2 decode sanity, and same-split nnU-Net comparison. If scheduler/logs fail, record exact job id and state; do not mark pending jobs complete.

## Required Variants

Run at least these bounded variants unless a prerequisite blocks them: anchored dictionary plus scar/edema proposal prototypes; scar-focused high-precision proposal plus conservative edema proposal; conservative no-prototype cascade fallback. Do not run dictionary-only topology variants that do not connect proposal, negative space, and refinement.

## Required Metrics

Report against same-split nnU-Net fold0: scar Dice and HD95; edema all-case, T2-present/complete, GT-positive Dice and HD95; no-T2 empty-GT edema stability; CenterB/CenterC metrics; component count, remote FP, outside-myocardium FP, volume ratio; dictionary slot usage/gate entropy/collapse flags; proposal recall/precision/lesion-wise recall; raw/compact label QC and decode mode.

## Required Outputs

Write under `results/20260704_myops_anchor_srr_fold0_formal/`: `result.md`, `MANIFEST.md`, `job_status.md`, `experiment_adequacy_report.md`, `one_batch_overfit.md`, `checkpoint_policy.md`, `prediction_sanity.md`, `dictionary_stats.csv`, `gate_usage_by_pattern.csv`, `proposal_pr_sweep.csv`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `no_t2_decode_sanity.csv`, `label_export_qc.md`, and `failure_interpretation.md` if not promoted.

## Completion Definition

End with `EXECUTED_UNAUDITED`. Do not write route promotion or route-negative stop without separate audit. If under budget, use `SCIENTIFIC_UNDERTRAINED`, `SCIENTIFIC_PIPELINE_BUG`, `NEEDS_REVISION`, or `NEEDS_EVIDENCE`, not `STOP_NO_SIGNAL`.
