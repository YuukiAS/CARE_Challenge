---
task_key: "20260704_srr_v25_local_refinement_ablation"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "local ROI refinement / ablation"
---

# Task: Local ROI Refinement And Ablation

## Goal

Evaluate and strengthen the local ROI refinement module. The task must prove whether local refinement improves proposals and final metrics, rather than only proving that a local module exists.

## Required Work

Define separate scar and edema ROI policies, run input ablations, and report how local refinement affects Dice, HD95, component count, remote FP, and proposal-to-final changes. Include ablations for original modality input, anchor input, component input, prototype similarity, uncertainty, and anatomy support.

## Required Outputs

Write `results/20260704_srr_v25_local_refinement_ablation/` with `result.md`, `roi_contract.md`, `bounds_stats.csv`, `local_loss.md`, `ablation.csv`, `component_metrics.csv`, and `MANIFEST.md`.

## Completion Gate

Do not pass this task unless the report shows whether local refinement is helpful, neutral, or harmful in the hard subgroups.
