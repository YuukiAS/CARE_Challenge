# Diagram Contract Mapping

Status vocabulary: `IMPLEMENTED`, `PARTIAL`, `NAME_ONLY`, `MISSING`.

## Overall Finding

The formal route is not diagram-compliant SRR-v2/v2.5. It reuses several names from the diagram, but substitutes lighter modules for the core mechanisms.

## Mapping Table

| Diagram block | Current code | Status | Evidence | Impact |
| --- | --- | --- | --- | --- |
| Inputs plus availability mask for LGE/C0/T2 | Model accepts 3 channels and an availability tensor; unavailable modality features are multiplied by availability. | PARTIAL | `srr_propref.py:196-200`; `srr_v2_unet.py:49-55`; channel docs say LGE,T2,C0 not LGE,C0,T2. | Availability exists, but channel order differs from diagram wording and downstream no-T2 inference is not safe. |
| Multi-scale encoder 32/64/128/256 | Formal route uses 3 scales only: base, 2x, 4x. Job defaults `base_channels=10`, so 10/20/40. | NAME_ONLY | `srr_propref.py:148-156`; `srr_v2_unet.py:33-55`; `run_srr_propref_myops_fold0.py:984-987`; `run_srr_propref_formal_myops_fold0.sh:63-65`. | Capacity is far below diagram intent and far below nnU-Net-class baseline. |
| Availability-aware router with pooled features and availability embedding | Router exists and uses `fused.mean` plus availability. | PARTIAL | `srr_v2_unet.py:70-79`, `srr_v2_unet.py:101-120`. | This part is close in spirit, but it routes convolutional experts rather than dictionary retrieval slots. |
| Representation retrieval bank at each scale with shared/LGE/C0/T2/interaction dictionaries | `ScaleRetrieval` has shared/private/interaction ConvBlocks and softmax gates. It is not a dictionary bank with keyed memory/prototypes per scale. | NAME_ONLY | `srr_v2_unet.py:58-120`. | The model is ordinary routed convolution, not segmentation-native selective retrieval. |
| Data-derived pathology prototype groups | Prototypes are randomly initialized trainable `nn.Parameter`s; no code derives scar-positive, scar-negative, edema-positive, edema-safe-negative prototypes from data. | NAME_ONLY | `srr_propref.py:34-47`; `srr_myops.py:147-152`; runner only tracks gradients/updates at `run_srr_propref_myops_fold0.py:573-621`. | Prototype signal begins uncalibrated and can flood proposals. |
| Routed anatomy, scar, edema features | Separate task decoders exist for anatomy, scar, edema. | PARTIAL | `srr_propref.py:181-194`; `srr_v2_unet.py:123-138`. | Routed features exist, but they are not retrieved from diagram-level banks. |
| Anatomy decoder produces P_union, P_LV, P_RV | Anatomy head outputs 4 logits and derives only `union_prior_logits` with logsumexp over classes 1..3. No named P_LV/P_RV priors are used downstream. | PARTIAL | `pathology_heads.py:15-30`. | Scar/edema get a coarse union bias, not full anatomy-guided geometry. |
| Distance map and soft anatomy gate | No distance transform map or explicit uncertainty gate in formal PropRef path; soft ROI uses average pooling of proposal and union prior. | MISSING | `srr_propref.py:99-120`; older `PathologyProposalHead` has local confidence/uncertainty but is not the formal PropRef path. | Cannot localize lesion candidates relative to myocardium geometry; remote FP burden remains high. |
| Scar proposal LGE-dominant high-precision candidate selection | Scar proposal is conv score plus prototype similarity plus evidence/prior bias. No LGE-dominant candidate selection from original LGE. | NAME_ONLY | `srr_propref.py:56-79`, `srr_propref.py:203-207`. | Proposal precision at threshold 0.5 is only about 0.08-0.10 with many remote FPs. |
| Edema proposal T2-conditioned and missing-T2 safe | Edema loss is T2-masked, but proposal/decode can still emit edema without T2. | PARTIAL | `srr_losses.py:36-49`; `run_srr_propref_myops_fold0.py:259-275`; `prediction_sanity.md` reports no-T2 edema voxels. | No-T2 false edema is a direct CARE contract violation. |
| Soft-ROI scar crop refiner using original LGE crop | Formal refiner is full-volume Conv3d over decoder features, evidence logits, proposal logits, and ROI. It never crops original LGE. | NAME_ONLY | `srr_propref.py:82-120`; `run_srr_propref_myops_fold0.py:278-319`. | Does not provide high-resolution local scar correction. |
| Soft-ROI edema crop refiner using original T2 crop | Same full-volume residual head; no original T2 crop and no T2-present inference gate. | NAME_ONLY | `srr_propref.py:82-120`; `run_srr_propref_myops_fold0.py:259-275`. | Cannot be trusted for edema under missing T2. |
| Training objectives: anatomy, proposal, refinement, negative space, prior/ROI, dictionary regularizers | Some anatomy/scar/edema/proposal/margin/ROI/retrieval losses exist. Boundary/HD surrogate, true dictionary sparsity/load balancing/prototype diversity, and alignment are missing. | PARTIAL | `srr_losses.py:120-145`; `run_srr_propref_myops_fold0.py:105-206`. | Losses do not enforce diagram-level mechanism quality. |
| nnU-Net-equivalent backbone or nnU-Net anchor | No nnU-Net logits/probs/preds/components/teacher features are consumed by formal PropRef. | MISSING | `rg` over model/runner/loss paths found no nnU-Net anchor path; runner constructs `SRRProposeRefineMyoPS` from scratch at `run_srr_propref_myops_fold0.py:769-770`. | Explains failure to approach nnU-Net baseline. |

## Compliance Decision

architecture_compliance_decision: NOT_COMPLIANT

The current implementation should be treated as a small experimental proxy, not as a completed SRR-v2/v2.5 implementation.
