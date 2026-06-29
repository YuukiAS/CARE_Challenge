# MyoPS Proposal Selection

status: `REVISE_PROPOSAL_AND_REPEAT`

## Decision

Do not enter formal `20260628_myops_refine`; `SELECT_PROPOSAL_ROUTE` was not reached.

## Best Partial Signals

- best edema GT-positive Dice: `proposal_uncertainty_gate` (`0.2034`)
- best edema all-case Dice: `proposal_uncertainty_gate` (`0.4376`)
- best scar all-case Dice: `proposal_pos_neg_basic` (`0.1017`)
- best scar LGE-only Dice: `proposal_uncertainty_gate` (`0.0813`)

## Why Not Selected

- The best edema GT-positive Dice improves over the selected D4 dictionary reference (`0.2034` vs `0.1599`), but HD95 remains high (`121.9`) and GT-positive component/remote-FP burden remains high.
- Scar does not improve over the selected D4 dictionary reference (`0.1017` best proposal scar all-case Dice vs D4 `0.1054`).
- `proposal_anatomy_distance` did not reduce no-T2 edema false positives; it made no-T2 empty-GT Dice `0.0000`.
- `proposal_uncertainty_gate` improves no-T2 stability relative to the other proposal variants, but no-T2 edema is still not fully stable.
- Separate continuation audits found loss masking, decode calibration, and pathology checkpoint-selection issues, so repeating after those repairs is more defensible than selecting this proposal route now.

## Next Route

Use the completed continuation outputs before repeating:

- `results/20260629_loss_decode_calibration/selection.md`
- `results/20260629_pathology_checkpoint_selection/selection.md`
- `results/20260629_proposal_memory_hardneg/selection.md`
- `results/20260629_true_soft_roi_refine/selection.md`
- `results/20260629_result4_srr_core_rebuild/selection.md`
