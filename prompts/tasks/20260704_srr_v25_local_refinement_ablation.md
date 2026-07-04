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
mechanism_class: "local ROI refinement / scar and edema crop ablation"
required_evidence: ["code_diff", "crop_bounds", "original_modality_crop_use", "roi_stats", "input_ablation", "component_metrics"]
forbidden_substitutes: ["full-volume residual called local", "ROI mask without bounded crop", "same ROI policy for scar and edema", "no original LGE/T2 crop", "threshold tuning only", "no hard subgroup analysis"]
---

# Task: Local ROI Refinement And Ablation

## Goal

Evaluate and strengthen the local ROI refinement module. The task must prove whether local refinement improves proposals and final metrics, rather than only proving that a local module exists.

## Required Work

Define separate scar and edema ROI policies:

- scar: small high-resolution ROI, original LGE crop, higher precision, stronger remote-FP suppression;
- edema: larger context-preserving ROI, original T2 crop when T2 is present, no-T2 blocked, higher recall and topology stability.

The refinement branch must use bounded crop evidence. If any residual branch sees the full volume and is called `local`, mark `NEEDS_REVISION` unless a bounded-crop variant is implemented and selected by the formal runner.

Run input ablations for:

- original modality crop;
- nnU-Net anchor input;
- component input;
- prototype similarity maps;
- uncertainty;
- anatomy support and distance map;
- ROI mask;
- residual scale.

## Required Metrics

Report how local refinement affects Dice, HD95, component count, remote FP, proposal-to-final changes, ROI GT coverage, ROI outside-myocardium ratio, and crop-volume ratio. Include CenterC edema, T2-present GT-positive edema, scar CenterC, and cases where SRR harms nnU-Net.

## Required Outputs

Write `results/20260704_srr_v25_local_refinement_ablation/` with:

- `result.md`
- `roi_contract.md`
- `bounds_stats.csv`
- `local_loss.md`
- `ablation.csv`
- `component_metrics.csv`
- `hard_subgroup_effect.md`
- `MANIFEST.md`

## Completion Gate

Do not pass this task unless the report shows whether local refinement is helpful, neutral, or harmful in the hard subgroups. It must not pass if the local module exists but the ablation shows it damages nnU-Net without a gate or rollback policy.
