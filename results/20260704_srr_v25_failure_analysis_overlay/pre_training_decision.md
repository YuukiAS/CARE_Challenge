# Pre-Training Decision

task_key: `20260704_srr_v25_failure_analysis_overlay`

decision: `HARD_SUBGROUP_AND_BOUNDED_MATRIX_OVERLAYS_VERIFIED_NEEDS_FULL_FOLD0_AND_AUDIT`

## Decision

Do not use this smoke packet to authorize route promotion, scientific stop,
fold expansion, validation packaging, or upload. It verifies that the
pathology-aware decode guard prevents the prior remote-FP flooding on a small
hard-subgroup packet, and it identifies CenterC/T2-present edema coverage as the
main visible weakness. The subsequent bounded matrix overlay pass adds
row-complete hard-subgroup taxonomy for the six non-identity variants, but it
is still only a 6-step bounded matrix and not full formal fold0 evidence.

## Current Root-Cause Hypothesis

For `Case1002`, the initial leading failure was not simple absence of a local
crop:

- scar crop is bounded, crop-volume ratio `0.041961669921875`;
- full-volume crop flag is `False`;
- nnU-Net and SRR argmax had similar scar metrics;
- pathology-aware decode flooded scar remotely until final pathology overrides
  were constrained by proposal-supported or already-argmax pathology voxels.

Most likely next mechanisms to isolate after the hard-subgroup smoke:

1. whether formal training improves or worsens CenterC/T2-present edema coverage;
2. whether the residual gate is too conservative to improve nnU-Net anchor errors;
3. whether proposal/ROI undercoverage explains the low-edema Dice cases;
4. dictionary/prototype misroute, pending spatial gate maps.

## Completed Bounded Overlay Evidence

The bounded matrix overlay/taxonomy pass now covers:

- `srr_propref_shared_dual_dict`
- `srr_propref_no_proto_cascade`
- `srr_propref_scar_precision`
- `srr_v25_no_local_refine`
- `srr_v25_no_anatomy_roi`
- `srr_v25_no_anchor`

It writes 42 overlays and 96 taxonomy rows under `bounded_matrix_overlay/`.
Anchor-enabled rows do not show remote-FP flooding on this packet.
`srr_v25_no_anchor` does show remote-island/proposal-flooding taxonomy, matching
its same-split help/harm degradation.

## Required Next Evidence

Before formal route promotion or stop, run full fold0 subgroup metrics and the
required final read-only audit. Spatial proposal/dictionary maps remain useful
if mechanism attribution stays ambiguous.

The next implementation task should prioritize formal input ablations and
same-split hard-subgroup metric impact, not more step-only training. If formal
variants still only preserve nnU-Net without improving hard edema, the likely
next repair is proposal/ROI coverage or residual-gate opening under strict
help/harm rollback checks.
