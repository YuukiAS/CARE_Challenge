# `src/` — custom networks

Reserved for **your own** training code (not third-party clones). Third-party paper implementations live in `third_party/`.

## CARE myocardium transition rule

The current CineMyoPS, MyoPS-Net, and U-MyoPS implementations are treated as adapted baselines alongside nnU-Net. If these baselines do not clearly exceed nnU-Net or explain the hosted metric gap by round 10, new model development should move here instead of continuing small third-party baseline patches.

DeepResearch-derived starting points:

- CineMyoPS: motion/strain-aware cine model, CineMA/StrainNet/MTI-style motion-texture features.
- MyoPS scar/edema: CAA-Seg style sequence alignment, anatomy/pathology cascade, T2-aware edema expert, HD/boundary-aware loss.
- Shared: explicit Dice + HD/HD95 reporting and component/outlier diagnostics before validation packaging.
