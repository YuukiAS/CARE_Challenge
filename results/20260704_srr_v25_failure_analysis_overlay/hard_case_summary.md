# Hard Case Summary

task_key: `20260704_srr_v25_failure_analysis_overlay`

## Current Spatial Evidence

Generated overlays:

- `overlays/Case1002_myops_scar_failure_overlay.png`
- `overlays/Case2002_myops_scar_failure_overlay.png`
- `overlays/Case2002_myops_edema_failure_overlay.png`
- `overlays/Case3004_myops_scar_failure_overlay.png`
- `overlays/Case3004_myops_edema_failure_overlay.png`
- `overlays/Case3011_myops_scar_failure_overlay.png`
- `overlays/Case3011_myops_edema_failure_overlay.png`

Smoke/hard-subgroup cases:

- `Case1002`: CenterA, LGE-only, no-T2 safety.
- `Case2002`: CenterB, T2-present GT-positive scar/edema.
- `Case3004`: CenterC, T2-present GT-positive scar/edema.
- `Case3011`: CenterC, T2-present GT-positive scar/edema.

## Observed Failure And Fix

Same-split nnU-Net is stable on scar for this case: Dice `0.616740`,
HD95 `4.323466`, component count `3`, remote FP `0`.

SRR argmax is close to nnU-Net on this smoke case: Dice `0.616153`,
HD95 `4.323466`, component count `3`, remote FP `0`.

The initial SRR pathology-aware decode was catastrophic: Dice `0.004395`,
HD95 `181.018476`, component count `9185`, remote FP `7697`. The overlay
showed large remote scar FP away from the scar ROI/crop region.

After the decode guard fix, SRR pathology-aware matches SRR argmax on this
smoke case: Dice `0.616153`, HD95 `4.323466`, component count `3`, remote FP
`0`. The remaining delta versus nnU-Net is a small Dice drop of about
`0.000587`, not remote FP flooding.

## Mechanism Triage

Initial one-case taxonomy:

- `remote_island`
- `proposal_flooding_or_decode_export`
- `refiner_overcorrection`

The proposal table at threshold `0.5` has scar proposal recall `0.506305`,
precision `0.784373`, lesion-wise recall `1.0`, and proposal remote FP `0`.
This means the final pathology-aware catastrophe is not explained by the
threshold-0.5 proposal table alone; it is more consistent with the
pathology-aware decode/export path or a refiner/gate interaction that floods
scar outside the bounded crop.

Post-fix taxonomy is `neutral_or_minor` for both argmax and pathology-aware on
this case. The corrected decoder uses proposal-supported or already-argmax
pathology voxels for pathology-aware overrides; ROI/crop support alone is no
longer allowed to create final pathology labels.

## Hard Subgroup Findings

The hard-subgroup packet no longer shows remote-FP flooding. Across
`Case1002`, `Case2002`, `Case3004`, and `Case3011`, all SRR scar/edema rows
have remote FP count `0`. Pathology-aware output usually matches argmax or makes
tiny anchor-level changes.

The strongest remaining visible failure is CenterC edema boundary/coverage:

- `Case3011` edema Dice `0.266909`, HD95 `34.266133`, component count `6`,
  remote FP `0`, crop-volume ratio `0.835181`.
- `Case3004` edema Dice `0.452563`, HD95 `9.222045`, component count `4`,
  remote FP `0`, crop-volume ratio `0.800542`.

Same-split nnU-Net help/harm deltas are tiny on this 1-step smoke packet:
pathology-aware edema Dice mean delta `-0.0000599`, scar Dice mean delta
`-0.000153`, with remote-FP deltas neutral. This means the current bounded
residual gate is preserving nnU-Net but not yet improving hard edema cases.

## Bounded Matrix Overlay Extension

The completed 8-row bounded matrix has now been routed through the same
overlay/taxonomy machinery for the six non-identity variants:

- `srr_propref_shared_dual_dict`
- `srr_propref_no_proto_cascade`
- `srr_propref_scar_precision`
- `srr_v25_no_local_refine`
- `srr_v25_no_anatomy_roi`
- `srr_v25_no_anchor`

The matrix-level packet writes 42 PNG overlays and 96 taxonomy rows under
`bounded_matrix_overlay/`. Anchor-enabled rows mostly remain `neutral_or_minor`
or CenterC edema boundary/extent failures. `srr_v25_no_anchor` is the clear
harm row: scar remote-island taxonomy appears in all 8 scar rows and edema
remote-island taxonomy appears in 6 of 8 edema rows, matching the same-split
help/harm remote-FP regression.

## Remaining Missing Evidence

This packet still does not cover:

- spatial dictionary gate maps or proposal probability maps.
- full fold0 subgroup metrics.
- final read-only audit.

Current status: `HARD_SUBGROUP_AND_BOUNDED_MATRIX_OVERLAYS_VERIFIED_NEEDS_FULL_FOLD0_AND_AUDIT`.
