# CARE Model Architecture

This page records current architecture status for planning and mapper review. It does not promote a model route.

## MyoPS

Current first-party SRR-ProposeRefine code centers on `src/care_myocardium/models/srr_propref.py`, `src/care_myocardium/models/srr_blocks.py`, and `src/care_myocardium/losses/srr_losses.py`.

The target route remains SRR-v3: availability-aware selective retrieval, semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific scar/edema soft-ROI refinement, explicit objectives, and controlled use of nnU-Net as anchor/context/evidence/safety source. The route must not degrade into optional nnU-Net post-processing.

Current M9 follow-up evidence is reconciled and independently reviewed, but the route decision is `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`: formal SRR-main candidates trained for the required budget remained below the tracked M8 nnU-Net anchor.

## Cine

Cine remains a required secondary line. Current M9 review describes Cine as local proxy final-output evidence only. No validation upload, hosted metric claim, route promotion, fold expansion, scientific stop, or M10 launch is authorized by this wiki.

## Shared Runtime

Controller-supervised long tasks must separate operational completion from scientific route resolution. Monitor packets are not completion; Slurm terminal outputs must be aggregated into tracked lightweight evidence before review.

## Known Limitations

- This bootstrap wiki is generated from current committed protocol and M9 follow-up packet/review, not from a new mapper execution over every source symbol.
- Components marked `partial` or `unverified` require mapper final evidence before any architecture-changing milestone can claim closure.
- `docs/wiki/` remains historical/reference material until explicitly migrated or redirected by a later cleanup.
