# MyoPS Proposal Architecture Note

status: `FORMAL_JOBS_SUBMITTED`

## Result5 Mapping

This task implements the Result5 direction by keeping D4 `cross_modal_interaction_dictionary` as the SRR evidence trunk and adding an explicit pathology proposal head.

The first-stage SRR now still produces anatomy, scar, and edema evidence, but proposal variants add:

- `scar_proposal_logits` and `edema_proposal_logits`
- pathology-specific positive and negative prototype similarity maps
- local anatomy neighborhood confidence from the soft anatomy union prior
- uncertainty maps derived from evidence confidence

The proposal logit follows the Result5 mechanism in implementation form:

```text
proposal = positive_similarity - negative_similarity
         + evidence_logit
         + soft anatomy neighborhood confidence
         - remote anatomy penalty
         - optional uncertainty penalty
```

This is a soft proposal gate, not a hard myocardium deletion. Voxels outside the anatomy prior are penalized but not removed.

## No-T2 Contract

Dense edema proposal BCE/Dice supervision is applied only to T2-present samples. For no-T2 samples, edema hard-negative margin supervision only uses true background voxels (`label == 0`) as safe negatives. Myocardium/pathology voxels in no-T2 cases are intentionally excluded from edema hard-negative supervision.

## Variants

- `proposal_pos_neg_basic`: positive-vs-negative prototype proposal without explicit distance or uncertainty pressure.
- `proposal_anatomy_distance`: adds stronger soft anatomy neighborhood confidence and remote distance penalty.
- `proposal_uncertainty_gate`: adds uncertainty penalty to reduce over-confident proposal gates.

The optional hard-negative replay variant is not claimed yet. It should only be added after these three formal routes show whether proposal recall/remote-FP behavior is worth mining from.
