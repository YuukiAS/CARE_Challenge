# MyoPS Proposal Failure Interpretation

status: `REVISE_PROPOSAL_AND_REPEAT`

## What Worked

- `proposal_uncertainty_gate` improved edema all-case Dice to `0.4376` and no-T2 empty-GT Dice to `0.5714`, which is a real sign that uncertainty gating can suppress some no-T2 edema false positives.
- `proposal_uncertainty_gate` also produced the best edema GT-positive Dice (`0.2034`) among the three proposal variants.
- The continuation audit found that calibrated decoding and final checkpoint selection can recover additional signal from `proposal_pos_neg_basic`.

## What Failed

- Scar did not improve. The best proposal scar all-case Dice was `0.1017`, below the selected D4 dictionary reference (`0.1054`).
- Edema GT-positive HD95 stayed high (`121.9` for `proposal_uncertainty_gate`), so improved all-case Dice is not enough to claim lesion localization.
- Component and remote-FP burden remained high across all variants.
- Anatomy-distance did not provide the intended containment benefit and destabilized no-T2 edema empty-GT behavior.

## Likely Root Causes

- The first run trained with an ignore-label masking bug in SRR losses; this has now been repaired for future runs.
- Raw argmax decoding is not the right final surface for proposal logits.
- Patch-loss checkpoint selection is not pathology-optimal.
- The proposal head lacks replayed hard negatives from mined remote false positives.
- Existing SRR private experts are route-private but not truly modality-input-private.

## Recommended Repeat

Repeat a small proposal round before refinement:

- use repaired ignore-label losses;
- use pathology-aware checkpoint selection or evaluate `checkpoint_final.pt` explicitly;
- decode pathology logits with calibrated threshold/proposal priority rather than raw argmax;
- add hard-negative replay from `results/20260629_proposal_memory_hardneg/mined_components.csv`;
- keep uncertainty gating for edema/no-T2 stability;
- do not start formal soft-cascade refinement until a repeated route reaches `SELECT_PROPOSAL_ROUTE`.
