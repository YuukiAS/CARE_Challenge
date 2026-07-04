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
mechanism_class: "training objectives / ablation"
---

# Task: SRR-v2.5 Training Objectives And Ablation

## Goal

Current training objectives are partial. This task must connect each SRR-v2.5 block to an active objective and an ablation.

## Required Work

Cover anatomy prior, scar proposal, edema proposal, local refinement, component behavior, lesion-wise behavior, boundary behavior, dictionary coverage and diversity, prototype separation, no-T2 safety, and context consistency where appropriate. Each objective must have code, a config switch, a sanity check, and an ablation.

## Required Outputs

Write `results/20260704_srr_v25_training_objectives_ablation/` with `result.md`, `objective_mapping.md`, `code_paths.md`, `sanity_report.md`, `ablation.csv`, `metric_impact.md`, and `MANIFEST.md`.

## Completion Gate

Do not pass this task unless active objectives and their metric effects are documented for scar, edema, CenterC, component count, remote FP, and HD95.
