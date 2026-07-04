---
task_key: "20260704_srr_v25_pathology_proposal_decoders"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "scar and edema proposal decoders / component-level pathology routing"
required_evidence: ["proposal_math", "component_level_metrics", "lesion_wise_recall", "remote_fp_report", "scar_edema_separate_policy", "ablation"]
forbidden_substitutes: ["single dense pathology head", "same proposal policy for scar and edema", "threshold tuning only", "proposal PR without final Dice link", "no component-level report"]
---

# Task: Pathology-Specific Proposal Decoders

## Goal

Build proposal decoders that respect the different nature of scar and edema. Scar is usually smaller, more scattered, LGE-dominant, and precision/remote-FP sensitive. Edema is larger, more diffuse, T2-conditioned, and missing-T2 sensitive. A single dense proposal formulation is insufficient.

## Required Work

Implement separate scar and edema proposal paths:

- scar proposal should emphasize LGE context, scar-positive prototypes, scar-safe negatives, nnU-Net scar components, small-lesion recall, high precision, and remote-FP suppression;
- edema proposal should emphasize T2 context, edema-positive prototypes, T2-present safe negatives, edema components, broader spatial support, and no-T2 blocking;
- both proposal heads must output component-level scores, voxel proposal maps, lesion-wise recall, proposal precision, and remote-FP metrics;
- add a component-level proposal loss or ranking objective, not only voxel BCE/Dice.

## Required Experiments

Evaluate proposal quality before refiner and after refiner. Report proposal recall/precision at thresholds, lesion-wise recall, component count, remote FP, outside-myocardium FP, and final Dice linkage. Include CenterC T2-present edema and scar CenterC as required subgroups.

## Required Outputs

Write `results/20260704_srr_v25_pathology_proposal_decoders/` with `result.md`, `proposal_math.md`, `component_level_loss.md`, `proposal_pr_sweep.csv`, `lesion_wise_recall.csv`, `remote_fp_report.csv`, `scar_edema_policy.md`, `ablation_report.md`, and `MANIFEST.md`.

## Completion Gate

Do not mark pass unless proposal quality improves in the hard subgroups or the report clearly identifies why the current proposal mechanism cannot support refinement.
