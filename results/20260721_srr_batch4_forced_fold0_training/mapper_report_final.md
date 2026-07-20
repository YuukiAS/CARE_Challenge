# Batch4 Mapper Final Report

status: `MAPPER_FINAL_COMPLETE`

The terminal packet maps the active Batch4 implementation to the planned SRR M10 D3 full-volume contract:

- Training model: `m10_d3_hierarchical_memory_propref`.
- Encoder profile: `full_4scale` with channels `[32, 64, 128, 256]`.
- Split: fold 0 with `176` training cases and `44` validation/evaluation cases.
- Prototype/memory source: frozen training-only prototype memory manifest is aggregated in `frozen_prototype_memory_manifest.json`; validator checks 176-case source coverage and no validation leakage through the manifest evidence path.
- Checkpoint path: schema-v2 checkpoint reload from `checkpoint_validation_step_1800.pt`.
- Same checkpoint controls: identity, anchor-bounded correction, and no-anchor modes all bind to checkpoint SHA256 `bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6`.
- Proposal/refiner/correction evidence: terminal packet includes `proposal_diagnostics.csv`, `roi_diagnostics.csv`, and `correction_gate_diagnostics.csv` from the selected step.

The root wiki was not promoted to a new scientific state in this controller packet. Batch4 remains pre-review, with `route_promotion_decision: NOT_REVIEWED`, `route_negative_decision: NOT_REVIEWED`, and `scientific_resolution_status: AWAITING_REVIEW`.
