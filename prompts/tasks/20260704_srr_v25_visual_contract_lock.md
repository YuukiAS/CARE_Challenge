---
task_key: "20260704_srr_v25_visual_contract_lock"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "medium"
allow_code_change: false
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "visual diagram contract / anti-name-only architecture lock"
required_evidence: ["image_read_evidence", "visual_block_contract", "diagram_to_task_trace", "missing_or_ambiguous_items"]
forbidden_substitutes: ["using only old audit prose", "claiming images were read without render or file evidence", "treating file presence as diagram comprehension", "skipping blocks that are inconvenient to implement"]
---

# Task: SRR-v2/v2.5 Visual Contract Lock

## Goal

Before implementation, lock the actual visual architecture contract from `images/SRR-v2.png` and `images/SRR-v2.5.png`. The two diagrams share the same core idea: SRR-MyoPS is availability-aware pathology-specific retrieval plus anatomy-guided lesion proposal plus soft-cascade refinement; Cine is registration-aware anatomy-first temporal retrieval. This task prevents later subtasks from treating simplified, name-compatible modules as full SRR-v2.5.

## Required Image Reading

Read both images directly from the repository path if available. Record file paths, hashes if obtainable, render/open method, and whether the diagram was visually inspected. If an execution environment cannot render the PNG files, mark the image read status as `PARTIAL_RENDER_BLOCKED`, use the visual contract below, and do not claim full image inspection.

## Visual Contract To Lock

The MyoPS chain must include these blocks:

1. Inputs and availability: LGE, C0/bSSFP, T2, plus explicit availability mask `m=(m_LGE,m_C0,m_T2)`. Missing modalities must be mathematically inert; zero-filled unavailable channels cannot be treated as observed evidence.
2. Encoder/router: modality-specific stems followed by a strong shared multi-scale encoder or nnU-Net-equivalent context path with intended scale capacity around 32/64/128/256. Each scale must expose a pooled feature query `q^l` plus availability embedding `e(m)` to task-specific routers.
3. Retrieval bank: at each scale `l`, there must be shared dictionary `D_sh^l`, LGE-private dictionary `D_LGE^l`, C0-private dictionary `D_C0^l`, T2-private dictionary `D_T2^l`, optional interaction dictionary `D_mix^l`, and pathology prototype groups for scar-positive, scar-negative, edema-positive, and edema-safe-negative evidence.
4. Routed outputs: retrieval must produce distinct routed anatomy, scar, and edema features. Nonzero gate logs alone are not enough; routed features must be consumed downstream and ablated.
5. Anatomy-guided proposal: an anatomy decoder must output `P_union`, `P_LV`, and `P_RV`, which then generate anatomy prior, distance map, and soft anatomy gate.
6. Pathology proposal: scar proposal must be LGE-dominant, high-precision, and component-aware. Edema proposal must be T2-conditioned, broader-context, and no-T2 safe.
7. Soft-ROI refinement: the ROI generator must use proposal, anatomy prior, distance, and uncertainty. Scar refinement must use a small high-resolution ROI and original LGE crop. Edema refinement must use a larger context-preserving ROI and original T2 crop when T2 is present. This is soft containment, not hard clipping.
8. Training objectives: the loss stack must include anatomy loss, scar proposal loss, T2-masked edema proposal loss, scar refinement loss, T2-masked edema refinement loss, negative-space/hard-negative discrimination, soft anatomy prior/ROI regularization, dictionary sparsity/coverage/load balancing/prototype diversity, and optional reference alignment on complete tri-modal cases.
9. Cine branch: cine is a secondary but serious branch using ED anchor/keyframes, reference-frame registration or warping, temporal representation dictionary, frame-quality/motion-saliency routing, frame-wise anatomy prior, and temporal aggregation.

## Required Outputs

Write `results/20260704_srr_v25_visual_contract_lock/` with:

- `result.md`
- `image_read_evidence.md`
- `visual_block_contract.md`
- `diagram_to_task_trace.md`
- `missing_or_ambiguous_items.md`
- `MANIFEST.md`

## Completion Gate

Do not mark `PASS` unless every visual block above is mapped to an existing or downstream task. If the executor cannot render/read the images, mark `PASS_WITH_RENDER_LIMITATION` only if the limitation is explicit and the visual contract above is carried forward exactly. This task is read-only and must not run training.
