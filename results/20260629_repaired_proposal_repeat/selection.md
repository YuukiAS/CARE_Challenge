# Repaired Proposal Repeat Selection

status: `ROUTE_TO_CASCADE_TEACHER`

selected_variant: `none`

best_repaired_scar_signal: `repaired_posneg_scar_hardneg`

best_repaired_edema_signal: `repaired_uncertainty_hardneg`

## Decision

Do not select the repaired SRRMyoPSLite proposal route for fold expansion or refinement. The three repaired variants completed formal fold0 training and exported full-volume predictions, but the route did not improve enough over the D4 dictionary reference, the previous proposal route, or the nnU-Net fold0 reference.

The strongest repaired scar readout is `repaired_posneg_scar_hardneg` with scar all-case Dice `0.1038` and HD95 `136.0183`, which does not exceed the D4 dictionary scar all-case Dice `0.1054` and remains far below nnU-Net fold0 scar Dice `0.5602`.

The strongest repaired edema GT-positive readout is `repaired_uncertainty_hardneg` with edema GT-positive Dice `0.1545` and HD95 `128.6386`, which is below both the D4 edema GT-positive Dice `0.1599` and the previous `proposal_uncertainty_gate` edema GT-positive Dice `0.2034`. nnU-Net fold0 edema Dice is `0.3944`.

## Why This Routes Away From Repaired Proposal

- The intended repairs were executable: ignore-label masking, no-T2 edema masking, hard-negative replay input, configurable proposal mixing, checkpoint export, and full-volume aggregation all ran.
- The failure mode remains architectural and spatial: scar stays in the `0.1` Dice regime, while edema GT-positive HD95 and component burden remain high.
- Hard-negative replay reduced some component/remote-FP pressure in selected rows, but not enough to produce a route-level improvement.
- Continuing to patch the shallow SRRMyoPSLite proposal head is less justified than continuing SRR-v2 and running the nnU-Net anchored cascade route.

## Next Route

Use this result as negative evidence for the current lightweight proposal head. Continue the active rescue goal with:

- `results/20260629_srr_v2_unet_core/` for the multi-scale SRR-v2 route.
- `results/20260629_cascade_teacher_route/` for the nnU-Net anchored cascade/refiner route.

No validation upload, fold expansion, split change, label mapping change, or evaluator change was performed.
