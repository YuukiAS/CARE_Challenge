# Result5 Continuation Status

status: `PROPOSAL_REVISE_REPEAT_WITH_REPAIRS`

## Current Gate

- `SELECT_PROPOSAL_ROUTE`: not reached.
- Formal `20260628_myops_refine`: not started.
- All formal proposal jobs completed naturally; none were killed, restarted, or overwritten after launch except the explicitly repaired uncertainty resubmission for the failed zero-byte checkpoint run.

## Completed Since Continuation

- Synced `main` with `git pull --ff-only`.
- Completed `20260629_loss_decode_calibration` for the finished `proposal_pos_neg_basic` variant.
- Completed `20260629_pathology_checkpoint_selection` for the finished `proposal_pos_neg_basic` variant.
- Completed `20260629_proposal_memory_hardneg` as preflight mining only.
- Completed `20260629_true_soft_roi_refine` as geometry-only preflight.
- Completed `20260629_result4_srr_core_rebuild` as architecture preflight/defer package.
- Confirmed and repaired the SRR ignore-label loss masking bug for future runs.

## Positive Signals

- Decode calibration status: `DECODE_CALIBRATION_SIGNAL`.
- Pathology checkpoint selection status: `FINAL_BETTER_THAN_PATCH_BEST`.
- Hard-negative memory status: `HARDNEG_PREFLIGHT_ONLY` with `7237` mined false-positive components and safe replay pools identified.
- Soft-ROI status: `REFINE_WAITING_FOR_PROPOSAL_SELECTION`; restore sanity passed with `0` invalid rows, but ROI volume ratio remains high.
- SRR-v2 core rebuild status: `CORE_REBUILD_DEFER`; current private experts operate on fused features, but formal rebuild should wait until current proposal jobs finish.

## Remaining

- Design a repeat proposal route integrating the repaired loss masking, decode calibration, pathology checkpoint selection, hard-negative memory, and uncertainty gating evidence.
- Do not enter formal MyoPS refinement until a repeat proposal route reaches `SELECT_PROPOSAL_ROUTE`.

## Latest Formal Proposal Readout

- `proposal_pos_neg_basic`: completed; weak pathology signal.
- `proposal_anatomy_distance`: completed; no credible route improvement, with worse no-T2 edema stability.
- `proposal_uncertainty_gate`: completed; best edema/no-T2 signal but not enough to select proposal route.

## Proposal Selection

- `results/20260628_myops_proposal/selection.md`: `REVISE_PROPOSAL_AND_REPEAT`
- Best edema signal: `proposal_uncertainty_gate`
- Best scar signal: `proposal_pos_neg_basic`
- `SELECT_PROPOSAL_ROUTE`: not reached

## Audit Failure and Capacity Note

- Three-variant decode/checkpoint rerun job `56949174` failed after `00:57:06` with exit code `1:0`; the log contained startup lines only and no Python traceback.
- The failed rerun temporarily truncated `results/20260629_loss_decode_calibration/decode_case_metrics.csv`; it has been restored to the last committed valid single-variant audit artifact (`1602608` bytes).
- No completed formal proposal job was restarted, killed, overwritten, or deleted.
- Because `/overflow/htzhu/CARE` hit a local write/quota limit during restore, future commits should stay small and avoid committing checkpoints, predictions, preflight scratch, or large logs.
