---
task_key: "20260704_srr_v25_anatomy_distance_roi_prior"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "P_union/P_LV/P_RV anatomy decoder / distance map / soft ROI prior"
required_evidence: ["code_diff", "anatomy_outputs", "distance_map_sanity", "roi_generator_contract", "ablation", "unit_tests"]
forbidden_substitutes: ["union_prior_logits only", "hard clipping pathology to myocardium", "distance map placeholder", "ROI from proposal only", "no LV/RV outputs", "no spatial sanity"]
---

# Task: Anatomy Distance Prior And Soft-ROI Generator

## Goal

Replace weak anatomy biasing with the visual SRR-v2.5 anatomy mechanism. The anatomy branch must output `P_union`, `P_LV`, and `P_RV`; these outputs must generate anatomy prior, distance maps, uncertainty, and soft ROI gates used by scar and edema proposal/refinement.

## Required Work

Implement or verify:

- anatomy decoder outputs for union/anatomy support, LV, and RV;
- differentiable or cached distance context from the anatomy support and LV/RV boundaries;
- uncertainty/confidence maps from nnU-Net and/or SRR anatomy prediction;
- scar soft gate emphasizing small high-precision LGE-supported ROI near anatomy;
- edema soft gate emphasizing broader T2-supported ROI without treating no-T2 as edema-negative;
- soft containment regularization, not hard clipping;
- export of anatomy prior maps, distance maps, ROI maps, and crop bounds for overlay review.

## Required Tests

- Toy test where `P_union` empty triggers safe fallback but does not hallucinate full-volume ROI.
- Toy test where a remote proposal outside anatomy is downweighted rather than hard-deleted.
- Shape test confirming distance maps match model logits and image tensors.
- No-T2 test confirming edema ROI/refinement are blocked or safely inert.
- Ablation showing `union_prior_logits` only versus full `P_union/P_LV/P_RV + distance + uncertainty`.

## Required Metrics

Report ROI GT coverage, outside-myocardium ROI ratio, crop-volume ratio, scar/edema remote FP, component count, HD95, and final Dice linkage. Include CenterC T2-present edema and scar harmed-by-SRR cases.

## Required Outputs

Write `results/20260704_srr_v25_anatomy_distance_roi_prior/` with:

- `result.md`
- `anatomy_output_contract.md`
- `distance_map_sanity.csv`
- `roi_generator_contract.md`
- `roi_ablation.csv`
- `overlay_manifest.md`
- `unit_test_report.md`
- `MANIFEST.md`

## Completion Gate

Do not mark `PASS` if the implementation only renames `union_prior_logits`, uses hard myocardium clipping as the main mechanism, or cannot show that distance/uncertainty changes ROI behavior on hard cases.
