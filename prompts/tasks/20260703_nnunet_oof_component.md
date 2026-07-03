---
task_key: "20260703_nnunet_oof_component"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session via prompts/tasks/20260703_srr_recovery_goal.md"
executor: "separate Codex executor session/subagent"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "nnU-Net anchored component scoring / OOF false-positive control"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "same-split nnU-Net fold0 plus audited 20260703 FP-control diagnostic evidence; evidence not found if unavailable"
required_subgroups: ["all-case", "scar-positive", "edema GT-positive", "T2-present/complete", "no-T2 empty-GT stability", "CenterB", "CenterC", "LGE-only"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "remote_FP", "small_FP", "volume_ratio", "calibration", "decision_features"]
required_evidence: ["result.md", "review.md", "MANIFEST.md", "train_oof_protocol.md", "component_feature_table.csv", "oof_training_summary.md", "metrics_summary.md", "subgroup_metrics.csv", "component_action_table.csv", "label_export_QC", "command_transcript.md"]
forbidden_substitutes: ["fold0 validation GT used for action selection", "fixed thresholds reported as learned OOF evidence", "compact-label result as hosted improvement", "validation upload or fold expansion", "hard deletion without full metrics"]
experiment_adequacy_gate: "OOF component scorer must train or select thresholds without fold0 validation GT and must report split provenance, features, actions, and baseline comparison."
promotion_gate: "Promote only as local fold0 OOF-controlled evidence if remote FP/component/HD metrics improve without unacceptable Dice/edema regression and auditor confirms no validation leakage."
failure_escalation_policy: "If OOF/train-side component evidence cannot be built, write NEEDS_EVIDENCE. If only deterministic fold0 rules are available, mark DIAGNOSTIC_ONLY."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: nnU-Net OOF Component Scorer

## Goal

Turn the small but real `scar_precision_component_score` fold0 signal into leak-free train/OOF component-scoring evidence. The prior FP-control review found lower scar remote FP, small FP, component count, and mean HD with negligible Dice change, but threshold provenance was only partial and the evidence was local fold0 diagnostic. This task tests whether that idea survives an OOF/train-side protocol without using fold0 validation labels for action selection.

## Required reads

- `results/20260703_myops_fp_control/result.md`
- `results/20260703_myops_fp_control/review.md`
- `results/20260703_myops_fp_control/component_action_table.csv` if available
- `results/20260703_myops_fp_control/baseline_vs_variant_metrics.csv` if available
- `results/20260703_myops_audit/review.md`
- same-split nnU-Net fold0 prediction/probability/cache paths
- Dataset501 split and metadata
- label/export/evaluator code

## Authorized scope

Allowed: create first-party evaluation/postprocess code under `scripts/evaluation/` or `src/care_myocardium/postprocess/`, generate local fold0 compact-label predictions/metrics under `results/20260703_nnunet_oof_component/`, and train a lightweight component scorer if it uses only train/OOF evidence.

Not allowed: validation upload, upload-ready package, fold expansion, evaluator/label mapping changes, or using fold0 validation GT to decide actions for the promoted scorer.

## Required protocol

1. Build component features from nnU-Net predictions/probabilities and image/anatomy support. Candidate features may include size, probability mean/max, distance-to-union/anatomy support, component location, class, volume ratio, local intensity summary, and availability.
2. Separate decision features from evaluation annotations. Any GT-derived fields must be named `evaluation_*` and computed only after prediction actions are frozen.
3. Use train/OOF evidence for scorer fitting or threshold selection. If true OOF caches are unavailable, write `NEEDS_EVIDENCE` or mark deterministic fixed rules as `DIAGNOSTIC_ONLY`; do not pretend learned OOF evidence exists.
4. Evaluate unchanged nnU-Net baseline and scorer outputs on fold0 using the same evaluator and label mapping.
5. Report scar and edema metrics, especially component count, remote FP, small FP, HD, HD95, Dice, volume ratio, CenterB/CenterC, LGE-only, T2-present, GT-positive, and no-T2 stability.

## Required outputs

Write:

- `results/20260703_nnunet_oof_component/result.md`
- `MANIFEST.md`
- `train_oof_protocol.md`
- `component_feature_table.csv`
- `component_action_table.csv`
- `oof_training_summary.md`
- `metrics_summary.md`
- `subgroup_metrics.csv`
- `component_hd_by_case.csv`
- `label_export_qc.md`
- `failure_interpretation.md`
- `command_transcript.md`

## Decision rules

Allowed decisions: `AUDIT_FOR_PROMOTION`, `DIAGNOSTIC_ONLY`, `NEEDS_EVIDENCE`, `NEEDS_REVISION`, `STOP_NO_OOF_COMPONENT_SIGNAL`.

Do not use `STOP_NO_OOF_COMPONENT_SIGNAL` unless the OOF protocol is adequate. If train/OOF evidence is missing, use `NEEDS_EVIDENCE`.

普通 executor 必须停在 `EXECUTED_UNAUDITED` and await review.
