# nnU-Net Anchor Gap

## Decision

nnunet_anchor_present: NO

The formal `SRRProposeRefineMyoPS` route does not use nnU-Net logits, probabilities, compact predictions, components, or teacher features.

## Evidence

`rg` over these files found no nnU-Net anchor input path:

- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/models/srr_v2_unet.py`
- `src/care_myocardium/models/srr_myops.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_propref_myops_fold0.py`

The formal runner creates the model from scratch:

```text
model = SRRProposeRefineMyoPS(base_channels=args.base_channels, variant=args.variant).to(device)
```

Evidence path: `scripts/training/run_srr_propref_myops_fold0.py:769-770`.

The only `load_state_dict` in the formal runner reloads PropRef's own checkpoint for evaluation, not nnU-Net weights or features: `scripts/training/run_srr_propref_myops_fold0.py:913-916`.

## Why It Matters

The same-split nnU-Net fold0 reference is much stronger:

- scar Dice: `0.5602`;
- edema Dice in nnU-Net validation summary: `0.3944`;
- unified fold0 class-4 all-case sanity Dice: `0.7798`.

The formal PropRef best values are much lower:

- best scar Dice: `0.1665` argmax or `0.1524` pathology-aware for shared dual;
- best edema GT-positive Dice: `0.0868` for no-proto pathology-aware.

Without an anchor, the current route throws away the existing nnU-Net representation and asks a small 10/20/40-channel model to learn the full segmentation problem, proposal problem, and refinement problem at once.

## Contrast: Existing OOF Component Path

`scripts/evaluation/run_nnunet_oof_component_20260703.py` does consume nnU-Net predictions and probabilities. It builds case payloads from `pred_path` and `prob_path`, extracts scar components, and applies a component score. That is an actual nnU-Net-anchored postprocess/refinement path. The PropRef route does not share this anchor mechanism.

## Required Fix

Minimum viable anchor choices:

1. nnU-Net probability/logit residual head: input image channels plus nnU-Net class probabilities/logits, with residual edits bounded to scar/edema.
2. nnU-Net component refiner: use nnU-Net components/probabilities as proposals and learn small component-wise suppression/addition.
3. nnU-Net checkpoint/backbone initialization: preserve baseline anatomy/scar representation before adding SRR/proposal logic.

Do not treat longer training of the current scratch PropRef model as the primary fix.
