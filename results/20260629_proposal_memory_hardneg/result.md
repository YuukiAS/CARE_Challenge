# Result 20260629 Proposal Memory HardNeg

- selection: `HARDNEG_PREFLIGHT_ONLY`
- source variant: `proposal_pos_neg_basic/checkpoint_best`
- action: mined false-positive connected components from completed local predictions.
- formal replay training: not launched; this remained preflight-only after proposal aggregation because `SELECT_PROPOSAL_ROUTE` was not reached.

## Safety Counts

- `scar_remote_fp_safe`: `3919`
- `edema_t2_remote_fp_safe`: `980`
- `scar_near_gt_unsafe`: `924`
- `edema_no_t2_true_background_safe`: `450`
- `edema_t2_near_gt_unsafe`: `334`
- `edema_no_t2_unsafe_anatomy_or_scar`: `251`
- `scar_blood_pool_negative`: `146`
- `edema_t2_far_from_gt_anatomy_negative`: `131`
- `scar_anatomy_adjacent_negative`: `56`
- `scar_myocardium_or_edema_negative`: `46`

## Edema Safety Rule

No-T2 myocardium or scar components are excluded from edema replay. Only no-T2 true-background components and T2-present far-from-GT components are marked replay-safe.
