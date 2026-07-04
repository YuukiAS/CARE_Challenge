---
task_key: "20260704_srr_v25_completion_check"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "medium"
allow_code_change: false
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: false
mechanism_class: "read-only completion check"
required_evidence: ["claim_table", "metric_review", "ablation_review", "missing_evidence", "final_audit_readiness"]
forbidden_substitutes: ["file-exists pass", "executor self-promotion", "ignoring anti-laziness failures", "no same-split nnU-Net comparison"]
---

# Task: Read-Only Completion Check

## Goal

After the implementation and experiment tasks finish, check whether the full SRR-v2.5 packet is complete or still partial. This is a readiness check before the separate final read-only audit, not a route promotion.

## Required Checks

Check visual contract lock, anti-laziness tests, gap matrix, failure overlays, encoder/context, baseline-preserving residual gate, anatomy distance/ROI prior, dictionary semantics, prototype bank, proposal quality, local refinement, training objectives, same-split metrics, hard subgroups, Cine registration, Cine temporal dictionary, and all required ablations.

## Required Outputs

Write `results/20260704_srr_v25_completion_check/` with:

- `review.md`
- `claim_table.md`
- `metric_review.md`
- `ablation_review.md`
- `missing_evidence.md`
- `final_audit_readiness.md`
- `decision.md`
- `MANIFEST.md`

## Completion Gate

Mark `READY_FOR_FINAL_AUDIT` only if all required task files exist, all implementation claims have runtime evidence, same-split nnU-Net comparison is available, and no anti-laziness validator failures remain unresolved. Otherwise mark `NEEDS_REVISION` or `NEEDS_EVIDENCE`.
