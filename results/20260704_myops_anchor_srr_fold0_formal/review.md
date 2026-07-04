# Review 20260704 MyoPS Anchor SRR Fold0 Formal

audit_status: completed
auditor_role: separate read-only Codex auditor
experiment_adequacy_decision: PASS
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL_SUPPORTED_FOR_CURRENT_PACKET
diagnostic_publication_decision: AUDITED_DIAGNOSTIC_PUBLISH
scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED_FOR_CURRENT_ANCHORED_PACKET
next_state: STOP

## Scope And Boundary

This audit re-reviewed the current formal MyoPS fold0 packet after Slurm array
`57782211`, not the stale earlier undertrained packet. I did not edit
model/training/evaluation code, launch training, package or upload validation
outputs, run network commands, commit, or push.

`results/20260704_cine_temporal_motion_resume/review.md` remains current as a
diagnostic-only Cine review and was not changed by this pass.

## Key Findings

The prior audit finding that the formal runner did not consume nnU-Net anchors
is no longer correct. Current `scripts/training/run_srr_propref_myops_fold0.py`
loads nnU-Net probability anchors and hard-prediction component features,
passes `anchor_features` and `component_features` into training, validation,
one-batch overfit, and export/evaluation forwards, and records anchor-present
batch fractions in the training log.

The formal experiment adequacy gate now passes for all three variants:
`24000` / `22800` / `22800` optimizer steps, `3665.8` / `3514.3` / `9873.3`
train-loop seconds, `40` / `38` / `38` validation events, loss decrease, Stage0
overfit PASS, non-empty prediction sanity, checkpoint paths, and same-split
nnU-Net baselines.

The route still is not promotable. Best current fold0 anchored SRR evidence is
below the same-split nnU-Net baseline: scar all-case Dice `0.4183` versus
nnU-Net `0.5602`; edema GT-positive/T2-present Dice `0.1872` versus nnU-Net
`0.3944`. No-T2 edema safety holds diagnostically with `336` no-T2 rows,
maximum no-T2 edema voxels `0`, and no-T2 empty-GT edema subgroup component and
remote-FP means `0.0`.

## Required Decisions

| decision | audit result | evidence |
| --- | --- | --- |
| architecture compliance vs locked SRR-v2.5 contract | PARTIAL_FOR_PROMOTION | The formal runner now uses nnU-Net anchors/components, multi-slot retrieval, proposal/refinement, and no-T2 guardrails. Promotion remains blocked because the formal prototype path still relies on deterministic bootstrap/trained parameters plus hard-negative memory rather than a complete real train/OOF prototype cache, and because metrics do not beat nnU-Net. |
| nnU-Net anchor consumption | PASS | `summary.json` records `nnunet_anchor_manifest` with train/val anchor counts and OOF/fold0 provenance; `run_config.env` records `nnunet_anchor_root`; the runner passes `anchor_features` and `component_features` to `model(...)` in training/evaluation. |
| dictionary slot/gate/collapse sanity | PASS_DIAGNOSTIC | Prerequisite dictionary packet records multi-slot groups and no-T2 masking; formal `gate_usage_by_pattern.csv` has `200880` rows across anatomy/scar/edema scales with nonzero gate usage. This supports diagnostics, not promotion. |
| data-derived prototype and safe-negative policy | PARTIAL_DIAGNOSTIC | Preflight builder and safe-negative policy exist; formal hard-negative memory loads `5728` components from mined evidence and excludes unsafe no-T2 edema negatives. Formal prototype evidence does not show a complete real train/OOF prototype bank loaded before training. |
| no-T2 edema safety | PASS_DIAGNOSTIC | Parsed `no_t2_decode_sanity.csv`: `336` rows, max `no_t2_edema_voxels = 0`, nonzero rows `0`; no-T2 empty-GT subgroup Dice `1.0`, components `0.0`, remote FP `0.0`. |
| proposal/refinement sanity | PASS_DIAGNOSTIC_NEGATIVE | Proposal PR sweep, ROI/component/HD files, prediction sanity, and crop/no-T2 guardrail evidence exist. Proposal quality and final metrics remain weak, especially edema GT-positive/T2-present component and remote-FP burden. |
| experiment adequacy | PASS | `experiment_adequacy_report.md`: shared `24000` steps / `3665.8s` / `40` val events; scar_precision `22800` / `3514.3s` / `38`; no_proto `22800` / `9873.3s` / `38`; missing evidence `none`. |
| same-split nnU-Net comparison | PRESENT_AND_NEGATIVE | Baselines: scar all-case `0.5602`, edema GT-positive `0.3944`. Best anchored SRR: scar all-case `0.4183`; edema GT-positive/T2-present `0.1872`. |
| route promotion | NO_PROMOTION | Current fold0 evidence does not beat the same-split nnU-Net baseline and is not challenge-facing evidence. |
| route-negative stop support | STOP_SUPPORTED_FOR_CURRENT_PACKET | Adequacy PASS plus same-split negative comparison support stopping the current anchored SRR fold0 packet as a challenge-facing candidate. This does not prove every possible future SRR variant is scientifically exhausted. |
| diagnostic publication scope | ALLOW_REVIEWED_DIAGNOSTIC_MARKDOWN_ONLY | Publish only reviewed summaries/reviews needed by GPT planning; do not publish checkpoints, predictions, NIfTI outputs, upload packages, heavy logs, credentials, or raw result trees. |
| blocked actions | BLOCKED | Fold expansion, validation packaging/upload, hosted metric claims, route promotion, next-stage training, commit, and push remain blocked unless separately reauthorized. |

## Claim Ledger

claim.formal_jobs_completed: supported by `job_status.md` for array
`57782211` and per-variant summaries/checkpoints.

claim.adequacy_passed: supported by `experiment_adequacy_report.md`,
`one_batch_overfit.md`, `prediction_sanity.md`, `loss_stage_status.md`, and
`checkpoint_policy.md`.

claim.actual_anchor_consumption_evidenced: supported by `run_config.env`,
per-variant `summary.json`, and runner source paths that build anchor/component
tensors and pass them into `model(...)`.

claim.no_t2_guardrail_holds: supported by parsed `no_t2_decode_sanity.csv` and
no-T2 subgroup metrics.

claim.same_split_negative: supported by `metrics_summary.md` and
`subgroup_metrics.csv`.

claim.stop_current_packet_supported: supported by adequacy PASS plus same-split
underperformance versus nnU-Net; limited to the current anchored SRR fold0
packet.

## Final Audit Decision

This packet should be treated as `AUDITED_DIAGNOSTIC_PUBLISH` with
`STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL_SUPPORTED_FOR_CURRENT_PACKET`.

Validation packaging/upload remains blocked. Route promotion remains blocked.
