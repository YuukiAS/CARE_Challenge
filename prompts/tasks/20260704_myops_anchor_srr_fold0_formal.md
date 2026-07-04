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
required_secondary_metrics: ["Dice", "HD95", "component_count", "remote_FP", "volume_ratio", "dictionary_slot_usage", "gate_entropy", "proposal_recall", "proposal_precision", "outside_myocardium_FP", "no_T2_edema_voxels", "loss_plateau_or_convergence_status"]
required_evidence: ["one_batch_overfit", "training_log", "loss_curve", "validation_curve", "checkpoint", "prediction_path", "metric_csv", "subgroup_metrics", "component_hd_by_case", "dictionary_stats", "proposal_pr_sweep", "no_T2_decode_sanity", "label_export_QC", "loss_variant_schedule", "same_split_baseline", "MANIFEST.md"]
forbidden_substitutes: ["CPU smoke as formal training", "pending jobs marked complete", "one or two epochs used as adequate training", "arbitrary fixed short run used as route-negative stop", "8h timeout without plateau called convergence", "current tiny PropRef training", "stale cache", "compact-label-only promotion", "undertrained result marked STOP_NO_SIGNAL", "generic loss ignoring scar/edema differences", "unbounded variant grid"]
promotion_gate: "No route promotion without separate read-only audit."
minimum_effective_training:
  train_until: "validation/target loss plateau, justified early stopping, or <=8h budget exhaustion"
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  require_validation_curve: true
  allow_stop_without_training: false
experiment_adequacy_gate: "Formal training should follow normal model-training practice: use the staged schedule, monitor train and validation curves, keep best checkpoints, and run until losses/metrics plateau or early stopping is justified within the <=8h round budget. If the budget expires before plateau or if the curve is still moving materially, the result is UNDERTRAINED or NEEDS_MONITOR/REVISION, not route failure."
route_negative_gate: "No STOP_NO_* conclusion unless convergence/plateau evidence exists, same-split comparison is complete, forbidden substitutes are absent, and a separate auditor supports the decision."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_MONITOR", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Run Formal Fold0 Training/Evaluation For Anchored SRR-v2.5 Repair

## Goal

Run a formal fold0 train/evaluate cycle for the anchored SRR-v2.5 repair after the implementation, guardrail, loss, and variant tasks pass. This is the first task that may generate real performance evidence, but it must still stop at `EXECUTED_UNAUDITED`.

## Prerequisites

Before submitting or running training, verify PASS/PASS_PREFLIGHT from `results/20260704_v25_contract_lock/result.md`, `results/20260704_myops_anchor_inputs_decode_qc/result.md`, `results/20260704_myops_dictionary_retrieval_bank_impl/result.md`, `results/20260704_myops_proposal_proto_hardneg_impl/result.md`, `results/20260704_myops_soft_roi_no_t2_guardrails/result.md`, and `results/20260704_myops_loss_variant_schedule/result.md`. If any prerequisite is absent or `NEEDS_REVISION`, stop with `NEEDS_EVIDENCE` or `NEEDS_REVISION`.

## Training Budget And Adequacy

Use a controlled fold0 job on the CARE default GPU policy, normally capped at 8 hours or less per job. Do not use a fixed small number of steps as adequacy. Train like a normal segmentation paper implementation: run the planned stage schedule, validate regularly, keep best and final checkpoints, and stop only when validation/target losses plateau, early stopping is justified, or the budget is reached.

The report must show train loss curve, validation curve, validation events, best checkpoint selection, whether the curve plateaued, whether the run was still improving when stopped, and why the stop reason is adequate or not. If scheduler/logs fail, record exact job id and state; do not mark pending jobs complete. If the run reaches the time budget while still improving, write `SCIENTIFIC_UNDERTRAINED` or `NEEDS_MONITOR`, not `STOP_NO_SIGNAL`.

## Required Variants

Use the bounded matrix from `results/20260704_myops_loss_variant_schedule/variant_matrix.md`. At minimum, if prerequisites pass, run: `anchored_srr_v25_full`, `anchored_scar_precision_edema_safe`, and `anchored_conservative_cascade_no_proto_or_frozen_proto`. Do not run dictionary-only topology variants that do not connect anchor, proposal, negative space, crop refinement, and no-T2 guardrails. Do not run a broad temperature/threshold grid unless the controller explicitly narrows it after preflight.

## Required Metrics

Report against same-split nnU-Net fold0: scar Dice and HD95; edema all-case, T2-present/complete, GT-positive Dice and HD95; no-T2 empty-GT edema stability; CenterB/CenterC metrics; component count, remote FP, outside-myocardium FP, volume ratio; dictionary slot usage/gate entropy/collapse flags; proposal recall/precision/lesion-wise recall; raw/compact label QC and decode mode.

## Required Outputs

Write under `results/20260704_myops_anchor_srr_fold0_formal/`: `result.md`, `MANIFEST.md`, `job_status.md`, `experiment_adequacy_report.md`, `one_batch_overfit.md`, `checkpoint_policy.md`, `training_curves.csv`, `validation_curve.csv`, `prediction_sanity.md`, `dictionary_stats.csv`, `gate_usage_by_pattern.csv`, `proposal_pr_sweep.csv`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `no_t2_decode_sanity.csv`, `label_export_qc.md`, `loss_stage_status.md`, and `failure_interpretation.md` if not promoted.

## Completion Definition

End with `EXECUTED_UNAUDITED`. Do not write route promotion or route-negative stop without separate audit. If the training evidence is not converged or adequate, use `SCIENTIFIC_UNDERTRAINED`, `SCIENTIFIC_PIPELINE_BUG`, `NEEDS_MONITOR`, `NEEDS_REVISION`, or `NEEDS_EVIDENCE`, not `STOP_NO_SIGNAL`.
