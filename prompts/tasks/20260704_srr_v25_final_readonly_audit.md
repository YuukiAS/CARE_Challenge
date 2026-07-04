---
task_key: "20260704_srr_v25_final_readonly_audit"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "medium"
allow_code_change: false
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: false
mechanism_class: "separate read-only final audit / promotion or stop decision"
required_evidence: ["claim_table", "source_line_evidence", "runtime_evidence", "same_split_metrics", "ablation_review", "anti_laziness_report"]
forbidden_substitutes: ["executor self-approval", "promotion without ablation", "stop without mechanism diagnosis", "ignoring failed acceptance tests", "validation upload"]
---

# Task: Final Read-Only SRR-v2.5 Audit

## Goal

After all implementation and bounded experiment tasks finish, run a separate read-only audit. The auditor must decide whether the resulting packet is a real SRR-v2.5 implementation, a partial diagnostic, a baseline-preserving nnU-Net correction system, or a failed route. The auditor must not edit code, rerun training, package validation, upload, or promote based on executor claims alone.

## Required Audit Questions

1. Were `images/SRR-v2.png` and `images/SRR-v2.5.png` read or explicitly render-blocked with the visual contract carried forward?
2. Did anti-laziness acceptance tests pass, including required-file consistency and unused-utility detection?
3. Does the final model implement a baseline-preserving nnU-Net residual/gated correction or a justified alternative?
4. Are real train/OOF data-derived prototype banks loaded at runtime?
5. Are dictionary slots semantically constrained and ablated?
6. Are scar and edema proposal/refinement paths pathology-specific and component-aware?
7. Does anatomy guidance include `P_union/P_LV/P_RV`, distance/uncertainty, and soft ROI behavior?
8. Are no-T2 edema loss, inference, decode, and export all safe?
9. Did same-split metrics beat or at least selectively improve nnU-Net without unexplained widespread harm?
10. Are hard subgroup failures explained spatially with overlays or traces?
11. Is Cine evidence full, diagnostic, or still blocked by registration/CineMA limitations?

## Required Outputs

Write `results/20260704_srr_v25_final_readonly_audit/` with:

- `review.md`
- `claim_table.md`
- `source_line_evidence.md`
- `runtime_evidence.md`
- `same_split_metric_review.md`
- `ablation_review.md`
- `hard_subgroup_review.md`
- `anti_laziness_report.md`
- `promotion_or_stop_decision.md`
- `MANIFEST.md`

## Decision Labels

Use one of:

- `PROMOTE_CHALLENGE_CANDIDATE`
- `PROMOTE_DIAGNOSTIC_ONLY`
- `NEEDS_REVISION`
- `STOP_CURRENT_ROUTE_ONLY`
- `STOP_SRR_DIRECTION_NOT_SUPPORTED`

The last label requires unusually strong evidence and must not be used merely because one partial implementation failed.

## Completion Gate

No promotion, stop, fold expansion, packaging, or upload is allowed without this audit. If evidence is missing, mark `NEEDS_REVISION` rather than inferring success.
