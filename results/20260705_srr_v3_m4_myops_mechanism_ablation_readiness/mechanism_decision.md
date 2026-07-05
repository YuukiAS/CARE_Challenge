# Mechanism Decision

route_promotion_decision: `NO_PROMOTION`
route_negative_decision: `STOP_NOT_CLAIMED_BY_EXECUTOR`
scientific_resolution_status: `SCIENTIFIC_UNRESOLVED_MECHANISM_ABLATION_READY`

## Bounded Inference Finding

- M3 trained mean Dice delta across scar/edema rows: `-0.12502222426237394`.
- Closed-gate identity mean Dice delta: `0.0`; this verifies the anchor fallback is neutral versus nnU-Net.
- Mean trained gate value: `1.9009998316240246e-06`.
- No-anchor mean Dice delta: `-0.31825760478682236`.
- No-local-refinement mean Dice delta: `-0.1303016853605136`.

## Interpretation

The M3 pilot is harmful versus nnU-Net on this controlled subset. The closed-gate row is neutral, so the harm is not caused by the identity fallback itself. The trained gate/residual statistics are near closed, while pathology-aware decode and proposal/refinement rows still change labels; this points to weak or miscalibrated proposal/refinement/decode behavior rather than a clean helpful SRR correction.

Rows requiring a separately trained checkpoint, including semantic retrieval off and component proposal ranking off, are explicitly marked `NOT_RUN_WITH_REASON` in `ablation_config_table.csv`.

This is mechanism evidence only. It is not route promotion, not fold expansion, not validation packaging/upload, and not a challenge candidate.
