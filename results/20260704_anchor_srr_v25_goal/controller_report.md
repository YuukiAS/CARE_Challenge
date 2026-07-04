# Controller Report: 20260704_anchor_srr_v25_goal

controller_task: `prompts/tasks/20260704_anchor_srr_v25_goal.md`
controller_state: `STOP`
updated_at: `2026-07-04T05:50:28-04:00`

## Executor Subtasks

| phase | task | result path | decision |
| --- | --- | --- | --- |
| 0 | `20260704_v25_contract_lock` | `results/20260704_v25_contract_lock/result.md` | `contract_decision: LOCKED` |
| 0B | `20260704_external_assets_cinema_registration` | `results/20260704_external_assets_cinema_registration/result.md` | `external_asset_decision: PARTIAL_ASSETS_FOUND` |
| 1 | `20260704_myops_anchor_inputs_decode_qc` | `results/20260704_myops_anchor_inputs_decode_qc/result.md` | revised to `anchor_contract_decision: PASS_PREFLIGHT` |
| 2 | `20260704_myops_dictionary_retrieval_bank_impl` | `results/20260704_myops_dictionary_retrieval_bank_impl/result.md` | `dictionary_decision: PASS_PREFLIGHT` |
| 3 | `20260704_myops_proposal_proto_hardneg_impl` | `results/20260704_myops_proposal_proto_hardneg_impl/result.md` | `proposal_proto_decision: PASS_PREFLIGHT` |
| 4 | `20260704_myops_soft_roi_no_t2_guardrails` | `results/20260704_myops_soft_roi_no_t2_guardrails/result.md` | `soft_roi_guardrail_decision: PASS_PREFLIGHT` |
| 5 | `20260704_myops_loss_variant_schedule` | `results/20260704_myops_loss_variant_schedule/result.md` | `loss_variant_decision: PASS_PREFLIGHT` |
| 6 | `20260704_myops_anchor_srr_fold0_formal` | `results/20260704_myops_anchor_srr_fold0_formal/result.md` | `experiment_adequacy_decision: PASS`; `self_assessed_status: EXECUTED_UNAUDITED` |
| 7 | `20260704_cine_temporal_motion_resume` | `results/20260704_cine_temporal_motion_resume/result.md` | `cine_temporal_decision: PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP` |
| 8 | `20260704_anchor_srr_readonly_audit` | `results/20260704_anchor_srr_v25_goal/audit_summary.md` | `route_promotion_decision: NO_PROMOTION`; `route_negative_decision: STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL_SUPPORTED_FOR_CURRENT_PACKET` |

## Formal Fold0 Final State

Phase 6 reran the formal MyoPS fold0 evidence after repairing actual nnU-Net
anchor/component consumption. Slurm array `57782211` completed on `htzhulab`;
no residual Slurm jobs were found for `57782211`, `57782213`, or `57782214`.

Formal MyoPS adequacy now passes:

- `srr_propref_shared_dual_dict`: 24000 optimizer steps, 3665.8 train-loop seconds, 40 validation events, stop `max_steps`.
- `srr_propref_scar_precision`: 22800 optimizer steps, 3514.3 train-loop seconds, 38 validation events, stop `validation_plateau_patience`.
- `srr_propref_no_proto_cascade`: 22800 optimizer steps, 9873.3 train-loop seconds, 38 validation events, stop `validation_plateau_patience`.
- All three variants record `nnunet_anchor_manifest`: train cases use their OOF nnU-Net fold validation probabilities, fold0 validation cases use fold0 validation anchors, and hard-prediction components provide scar/edema component evidence.
- no-T2 edema decode/export guardrail passes diagnostically: `no_t2_decode_sanity.csv` has max no-T2 edema voxels `0`.

Same-split nnU-Net comparison remains negative:

- nnU-Net reference: scar all-case Dice `0.5602`; edema GT-positive Dice `0.3944`.
- Best anchored SRR scar all-case Dice: `0.4183`.
- Best anchored SRR edema GT-positive/T2-present Dice: `0.1872`.

Therefore the current anchored SRR packet is adequate diagnostic evidence but is
not a route promotion candidate.

## Cine Final State

The Cine diagnostic packet still supports only
`PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP`. CineMA assets were partially usable,
but current-env import timed out; SimpleITK demons fallback provided a
non-reference comparator but had folding/Jacobian concerns and did not beat the
frame0 reference. No validated ANTs/SyN, VoxelMorph, hosted
`myocardium_cinemyops`, or challenge-facing Cine promotion evidence exists.

## Audit Status

Separate read-only auditor `019f2c81-937f-7bb2-9fff-9914dc513c1e` completed the
refreshed Phase 8 audit against current array `57782211` evidence and wrote:

- `results/20260704_myops_anchor_srr_fold0_formal/review.md`
- `results/20260704_anchor_srr_v25_goal/audit_summary.md`

The previous Cine review remains current:

- `results/20260704_cine_temporal_motion_resume/review.md`

Audit decision: diagnostic publication of reviewed Markdown/compact summaries is
allowed for GPT planning, route promotion remains blocked, and the current
anchored SRR fold0 packet has enough adequate same-split negative evidence to
support stopping this packet as a challenge-facing candidate. This stop is
limited to the current anchored packet and does not claim every possible future
SRR direction is exhausted.

## Controller Ending

controller_run_status: COMPLETE
operational_completion_status: COMPLETE_FOR_AUDIT
experiment_adequacy_decision: PASS
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL_SUPPORTED_FOR_CURRENT_PACKET
scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED_FOR_CURRENT_ANCHORED_PACKET
diagnostic_publication_decision: AUDITED_DIAGNOSTIC_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
  - none
blocked_actions:
  - validation upload remains blocked
  - validation packaging remains blocked
  - fold expansion remains blocked
  - route promotion remains blocked
  - hosted metric claims remain blocked
  - next-stage training remains blocked
next_required_action: GPT planner should use the reviewed diagnostic packet to decide whether to abandon this anchored SRR packet as challenge-facing work, publish only curated diagnostic summaries, or authorize a new route. Do not package/upload validation or expand folds from this controller run.
reason_if_not_published: Auto commit/push are disabled; publish only curated diagnostic-scope files if explicitly requested.
reason_if_no_route_promotion: The adequate audited fold0 run remains below same-split nnU-Net on scar and T2-present/GT-positive edema despite passing nnU-Net anchor consumption and no-T2 safety gates.
