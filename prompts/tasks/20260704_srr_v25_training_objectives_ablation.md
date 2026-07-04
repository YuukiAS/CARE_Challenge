---
task_key: "20260704_srr_v25_training_objectives_ablation"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "training objectives / active loss mapping / ablation"
required_evidence: ["objective_mapping", "code_paths", "loss_switches", "sanity_report", "metric_impact", "ablation"]
forbidden_substitutes: ["generic DiceCE-only loss", "loss function exists but not used", "no config switch", "no hard subgroup impact", "no component-level objective", "no boundary or HD-sensitive term for scar"]
---

# Task: SRR-v2.5 Training Objectives And Ablation

## Goal

Current training objectives are partial. This task must connect each SRR-v2.5 visual block to an active objective and an ablation.

## Required Objective Mapping

Cover at minimum:

- anatomy loss on `P_union/P_LV/P_RV`;
- scar proposal loss with weak boundary/HD surrogate;
- T2-masked edema proposal loss, active only when T2 is present;
- scar local refinement loss;
- T2-masked edema local refinement loss;
- baseline-preserving residual/gate objective that penalizes unnecessary harm to nnU-Net while allowing bounded correction;
- component-level proposal/ranking objective;
- lesion-wise recall or MIL-style term for small scar components;
- negative-space/hard-negative discrimination;
- soft anatomy prior and ROI regularization;
- dictionary sparsity, coverage, load balancing, SIP-style integrativeness, and prototype diversity/separation;
- optional alignment loss only on complete tri-modal subset;
- no-T2 safety loss/check for train, inference, decode, and export.

## Required Work

Each objective must have code, a config switch, a sanity check, and an ablation. If an objective is impossible in the current time budget, explicitly mark it `DEFERRED_WITH_REASON` rather than silently replacing it with DiceCE.

## Required Outputs

Write `results/20260704_srr_v25_training_objectives_ablation/` with:

- `result.md`
- `objective_mapping.md`
- `code_paths.md`
- `loss_switches.md`
- `sanity_report.md`
- `ablation.csv`
- `metric_impact.md`
- `MANIFEST.md`

## Completion Gate

Do not pass this task unless active objectives and their metric effects are documented for scar, edema, CenterC, component count, remote FP, and HD95. Losses defined but not called by the formal runner count as `UTILITY_ONLY`, not implemented.
