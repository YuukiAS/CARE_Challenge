---
task_key: "20260704_srr_v25_training_ablation_matrix"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "formal training / mechanism ablation / same-split evaluation"
required_evidence: ["variant_matrix", "training_curves", "same_split_metrics", "mechanism_ablation", "stop_reason", "audit_packet"]
forbidden_substitutes: ["single variant only", "no ablation", "undertrained stop", "metrics without subgroup breakdown", "comparison only against previous SRR packet"]
---

# Task: Formal Training And Mechanism Ablation Matrix

## Goal

Run a bounded but decisive training/evaluation matrix after the full implementation tasks pass. The aim is to identify which mechanisms matter, not to hide behind one large mixed model.

## Required Variants

At minimum compare:

- full SRR-v2.5 implementation;
- no dictionary semantic objective;
- no data-derived prototypes;
- no component-level proposal objective;
- no local refinement;
- no nnU-Net context;
- nnU-Net context only with no SRR correction.

Use the same split and report against the same nnU-Net baseline. Do not expand folds or package validation.

## Required Metrics

Report scar Dice/HD95/component/remote FP, edema all-case, edema GT-positive, edema T2-present, CenterB, CenterC, no-T2 empty-GT safety, proposal recall/precision, lesion-wise recall, and dictionary usage.

## Required Outputs

Write `results/20260704_srr_v25_training_ablation_matrix/` with `result.md`, `variant_matrix.md`, `training_curves.csv`, `same_split_metrics.md`, `ablation_summary.csv`, `subgroup_metrics.csv`, `mechanism_decision.md`, and `MANIFEST.md`.

## Completion Gate

No promotion, no stop, and no scientific claim may be made without a read-only audit. If the full model is worse than nnU-Net, identify the mechanism that causes harm.
