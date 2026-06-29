# Result4 SRR Core Rebuild Selection

status: `CORE_REBUILD_DEFER`

## Reasons

- `20260629_loss_decode_calibration` did not rule out pipeline issues; it confirmed an ignore-label loss bug and a decode calibration signal.
- `20260629_pathology_checkpoint_selection` found that patch-loss best checkpoint was not pathology-optimal for `proposal_pos_neg_basic`.
- The formal `20260628_myops_proposal` jobs have completed, but the aggregate gate is `REVISE_PROPOSAL_AND_REPEAT`; SRR-v2 formal training should wait for an explicit repeat-route decision instead of competing with immediate repair planning.
- Current code review confirms the existing `ExpertBank` private experts operate on fused features, so SRR-v2 should be implemented as an isolated new route rather than editing current variants in place.

## Deferred Next Step

Implement `srr_v2_multiscale_private_sparse` only after the repeat-route planning decides whether the weak signal is primarily pipeline/decode/checkpoint driven or architecture driven.
