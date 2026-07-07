# M8 Route Objective

status: `M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE`

blocking_issues:
- `same_split_nnunet_candidate_control_incomplete_for_all_local_candidates`


SRR-MyoPS is availability-aware selective retrieval plus semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, explicit losses/objectives, and nnU-Net anchor/context/evidence/safety.

nnU-Net or another strong segmenter can be anchor/context/evidence/safety, but SRR cannot be reduced to optional post-processing or generic fallback.

Cine is registration-aware temporal retrieval with warped non-reference evidence. Current Cine evidence includes temporal dictionary execution from a selected usable non-reference registration method.
