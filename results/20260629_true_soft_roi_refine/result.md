# Result 20260629 True Soft-ROI Refine

- selection: `REFINE_WAITING_FOR_PROPOSAL_SELECTION`
- source variant: `proposal_pos_neg_basic/checkpoint_best`
- action: geometry-only ROI extract/restore preflight.
- formal refinement: not launched; waiting for `results/20260628_myops_proposal/selection.md` to reach `SELECT_PROPOSAL_ROUTE`.

## Findings

- restoration invalid rows: `0`
- GT-positive low-coverage rows (<0.95): `0`
- edema GT-positive mean ROI coverage: `1.0`; scar GT-positive mean ROI coverage: `1.0`.
- mean ROI volume ratio is high (`~0.74` on GT-positive rows), so this scaffold is geometry-safe but not yet a focused/refinement-ready crop policy.
- ROI construction uses proposal dilation plus anatomy context and never hard-deletes evidence for training selection.
