# Result5 Continuation Status

status: `IN_PROGRESS`

## Current Gate

- `SELECT_PROPOSAL_ROUTE`: not reached.
- Formal `20260628_myops_refine`: not started.
- Running formal jobs are still being monitored and have not been killed, restarted, or overwritten.

## Completed Since Continuation

- Synced `main` with `git pull --ff-only`.
- Completed `20260629_loss_decode_calibration` for the finished `proposal_pos_neg_basic` variant.
- Completed `20260629_pathology_checkpoint_selection` for the finished `proposal_pos_neg_basic` variant.
- Completed `20260629_proposal_memory_hardneg` as preflight mining only.
- Completed `20260629_true_soft_roi_refine` as geometry-only preflight.
- Confirmed and repaired the SRR ignore-label loss masking bug for future runs.

## Positive Signals

- Decode calibration status: `DECODE_CALIBRATION_SIGNAL`.
- Pathology checkpoint selection status: `FINAL_BETTER_THAN_PATCH_BEST`.
- Hard-negative memory status: `HARDNEG_PREFLIGHT_ONLY` with `7237` mined false-positive components and safe replay pools identified.
- Soft-ROI status: `REFINE_WAITING_FOR_PROPOSAL_SELECTION`; restore sanity passed with `0` invalid rows, but ROI volume ratio remains high.

## Remaining

- Wait for and evaluate `proposal_anatomy_distance`.
- Wait for and evaluate repaired `proposal_uncertainty_gate`.
- Aggregate `20260628_myops_proposal`.
- Decide whether any proposal route reaches `SELECT_PROPOSAL_ROUTE`; only then enter formal MyoPS refinement.
