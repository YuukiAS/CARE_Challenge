# M8 Route Objective

status: `M8_READY_FOR_REVIEW`

blocking_issues:
- none


SRR-MyoPS is availability-aware selective retrieval plus semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, explicit losses/objectives, and nnU-Net anchor/context/evidence/safety.

nnU-Net or another strong segmenter can be anchor/context/evidence/safety, but SRR cannot be reduced to optional post-processing or generic fallback.

Cine is registration-aware temporal retrieval with warped non-reference evidence. Current Cine evidence includes temporal dictionary execution from a selected usable non-reference registration method.
