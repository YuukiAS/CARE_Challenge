# Audit Summary 20260704 Anchor SRR-v2.5 Goal

audit_status: completed
auditor_role: separate read-only Codex auditor
controller_run_status: AUDITED_DIAGNOSTIC_PUBLISH
operational_completion_status: COMPLETE_FOR_AUDIT
experiment_adequacy_decision: PASS
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL_SUPPORTED_FOR_CURRENT_PACKET
scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED_FOR_CURRENT_ANCHORED_PACKET
diagnostic_publication_decision: AUDITED_DIAGNOSTIC_PUBLISH

## Summary

This audit reviewed the current formal MyoPS evidence after Slurm array
`57782211`, not the stale earlier undertrained state.

The formal MyoPS anchored SRR packet now satisfies the experiment adequacy gate
and evidences actual nnU-Net anchor/component consumption. The runner loads
case-aligned nnU-Net probability anchors and hard-prediction component features,
passes them into model forwards during training/evaluation, and records an
`nnunet_anchor_manifest` with OOF/fold0 provenance.

The packet still does not support route promotion. Best current fold0 results
remain below same-split nnU-Net: scar all-case Dice `0.4183` versus `0.5602`;
edema GT-positive/T2-present Dice `0.1872` versus `0.3944`. No-T2 edema safety
passes diagnostically with maximum no-T2 edema voxels `0`.

The audit supports stopping the current anchored SRR fold0 packet as a
challenge-facing candidate due to adequate same-split underperformance. This is
not a claim that every possible future SRR direction is exhausted.

The Cine packet remains diagnostic-only with a registration gap; its existing
review remains current and was not modified in this pass.

## Required Decisions

| decision | result |
| --- | --- |
| architecture compliance vs locked SRR-v2.5 contract | `PARTIAL_FOR_PROMOTION` |
| nnU-Net anchor consumption | `PASS` |
| dictionary slot/gate/collapse sanity | `PASS_DIAGNOSTIC` |
| data-derived prototype and safe-negative policy | `PARTIAL_DIAGNOSTIC` |
| no-T2 edema safety | `PASS_DIAGNOSTIC` |
| proposal/refinement sanity | `PASS_DIAGNOSTIC_NEGATIVE` |
| experiment adequacy | `PASS` |
| same-split nnU-Net comparison | `PRESENT_AND_NEGATIVE` |
| route promotion | `NO_PROMOTION` |
| route-negative stop support | `STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL_SUPPORTED_FOR_CURRENT_PACKET` |
| diagnostic publication scope | `reviewed diagnostic Markdown/CSV summaries only; no heavy outputs` |
| blocked actions | `fold expansion, validation packaging/upload, hosted metric claims, route promotion, next-stage training, commit, push` |

## Evidence Anchors

- `results/20260704_myops_anchor_srr_fold0_formal/review.md`
- `results/20260704_myops_anchor_srr_fold0_formal/result.md`
- `results/20260704_myops_anchor_srr_fold0_formal/experiment_adequacy_report.md`
- `results/20260704_myops_anchor_srr_fold0_formal/subgroup_metrics.csv`
- `results/20260704_myops_anchor_srr_fold0_formal/no_t2_decode_sanity.csv`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/summary.json`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/configs/run_config.env`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `results/20260704_cine_temporal_motion_resume/review.md`

## Diagnostic Publication Scope

Allowed, if the strategic controller chooses to publish a packet:

- `results/20260704_anchor_srr_v25_goal/audit_summary.md`
- `results/20260704_myops_anchor_srr_fold0_formal/review.md`
- `results/20260704_cine_temporal_motion_resume/review.md`
- small reviewed Markdown/CSV summaries required for planner review.

Blocked from publication:

- checkpoints;
- prediction/NIfTI outputs;
- upload packages;
- heavy logs;
- raw result trees;
- external credentials or environment dumps.

## Final State

next_state: `STOP`

scientific route state: `SCIENTIFIC_STOP_SUPPORTED_FOR_CURRENT_ANCHORED_PACKET`

Validation packaging/upload remains blocked. Route promotion remains blocked.
