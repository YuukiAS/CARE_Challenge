# SRR-v2 Architecture Audit

Task: `prompts/tasks/20260629_srr_v2_unet_core.md`

## Current SRRMyoPSLite Facts

- `ModalityStem` in `src/care_myocardium/models/srr_myops.py` is one `Conv3d -> GroupNorm -> LeakyReLU` block per modality.
- Private experts in `src/care_myocardium/models/srr_blocks.py` operate on `fused`, not on modality-specific feature streams.
- `SRRMyoPSLite` has no true multi-scale encoder/decoder, no downsample/upsample path, and no U-Net skip decoder.
- `multiscale_dictionary` pools the fused feature once and upsamples context; it is not a multi-scale representation bank.
- `AnatomyPathologyHeads` uses 1x1 Conv3d heads.
- `PathologyProposalHead` exports evidence/proposal logits, but prior to this task the final logits used a fixed 0.40/0.60 evidence/proposal mixture.

## New Isolated SRR-v2 Route

- Added `src/care_myocardium/models/srr_v2_unet.py`.
- `SRRV2MyoPSUNet` keeps LGE/T2/C0 as separate modality-private encoder streams through three scales.
- Each scale has shared, modality-private, and optional interaction experts.
- Private experts consume modality-specific feature maps, not an already fused map.
- Anatomy, scar, and edema have separate routed features and separate U-Net-like decoders with upsampling and skip fusion.
- Proposal variants keep evidence/proposal/final logits separable through the existing proposal-head output contract.

## Formal Variants

- `srr_v2_multiscale_private_basic`
- `srr_v2_multiscale_private_proposal`
- `srr_v2_proposal_uncertainty_hardneg`

The optional `srr_v2_light_refine` is intentionally not launched in the first array; it should run only if the first three variants show proposal signal.
