# Result 20260629 Loss/Decode Calibration

- variants evaluated: `proposal_pos_neg_basic`
- selection: `DECODE_CALIBRATION_SIGNAL`
- outputs: `decode_metrics.csv`, `checkpoint_comparison.csv`, `selection.md`.
- This task reads completed local fold0 checkpoints only and does not modify running Slurm jobs.
- Core SRR losses were audited; ignored `-1` padding was confirmed as a bug in prior code and repaired for future runs.

## Key Findings

- `proposal_pos_neg_basic/best`: raw combo (`scar all_cases Dice + edema GT-positive Dice`) was `0.2754`; best calibrated combo was `0.2842` using `threshold_sweep_mixed_t0.30`.
- `proposal_pos_neg_basic/final`: raw combo was `0.2134`; best calibrated combo was `0.2794` using `threshold_sweep_mixed_t0.10`.
- The calibration signal is real for `final`, but absolute pathology Dice remains low; this does not by itself justify `SELECT_PROPOSAL_ROUTE`.
- This audit ran with `--fast-metrics`, so HD/HD95 columns are intentionally empty. Dice, component count, remote FP, volume ratio, and empty-prediction rates are present.
