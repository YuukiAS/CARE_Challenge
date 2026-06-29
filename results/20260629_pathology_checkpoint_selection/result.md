# Result 20260629 Pathology Checkpoint Selection

- variants evaluated: `proposal_pos_neg_basic`
- selection: `FINAL_BETTER_THAN_PATCH_BEST`
- outputs: `checkpoint_metrics.csv`, `selection.md`.
- Pathology-aware score uses scar all-case Dice plus edema GT-positive Dice, penalized by HD95, remote FP, and component burden.

## Key Findings

- For calibrated/proposal-priority decode modes, `checkpoint_final.pt` scored higher than `checkpoint_best.pt` under the pathology-aware penalty score.
- The largest observed improvements were `threshold_sweep_proposal_t0.10` (`final_minus_best_score=0.8200`) and `threshold_sweep_mixed_t0.10` (`final_minus_best_score=0.6091`).
- The raw argmax mode moved in the wrong direction (`final_minus_best_score=-0.6013`), which supports separating checkpoint selection from raw multiclass argmax decoding.
- This audit used fast metrics; HD/HD95 penalties were not included because the immediate registry question was checkpoint/decode direction, not final heavy-metric ranking.
