# Implementation Recommendation

## Recommendation

current_training_recommendation: DO_NOT_CONTINUE_CURRENT_PROPREF

Do not make more step/time-only training of the current PropRef implementation the primary next action. The current route is not diagram-compliant and lacks the nnU-Net anchor needed to approach the baseline.

## Minimal Plausible Repair Plan

### Option A: nnU-Net-anchored residual/component refiner

This is the most pragmatic path toward `0.4+`-class local evidence.

Required pieces:

- Inputs: original modalities plus nnU-Net fold0 probabilities/logits or compact prediction.
- Proposals: use nnU-Net scar/edema components as anchors, not randomly initialized prototype logits.
- Refiner: small residual/component module that can suppress remote FP components and add bounded missed pathology.
- Safety: enforce no-T2-safe edema output at inference.
- Guardrails: scar non-regression, HD95/component/remote-FP checks, CenterB/CenterC and T2-present subgroup reporting.

Why: it preserves the strong nnU-Net representation instead of rebuilding segmentation from scratch.

### Option B: Strong backbone first, then SRR modules

If the planner wants a true SRR-v2.5 model rather than an anchored refiner:

- replace 10/20/40 three-scale trunk with a strong U-Net/nnU-Net-equivalent 32/64/128/256 backbone;
- add four-scale routed features;
- initialize from nnU-Net where possible or prove one-case/tiny overfit plus initial baseline reproduction;
- only then add retrieval/proposal/refinement modules.

### Option C: Full SRR-v2.5 diagram-compliant build

Required before calling it SRR-v2.5:

- per-scale shared, modality-specific, and interaction dictionary banks;
- data-derived scar-positive, scar-negative, edema-positive, edema-safe-negative prototype groups;
- anatomy decoder outputs `P_union`, `P_LV`, `P_RV`;
- distance-map and uncertainty soft gates;
- LGE-dominant scar proposal and T2-conditioned edema proposal;
- soft ROI generator with original LGE/T2 crop refiners;
- no-T2 inference gate for edema;
- dictionary sparsity, coverage, load-balancing, and prototype diversity losses.

This is larger than a quick patch. It should be a new GPT-authored implementation task if selected.

## What Not To Do

- Do not launch another formal run of the same `SRRProposeRefineMyoPS` as the main fix.
- Do not claim SRR-v2.5 is implemented because class names mention retrieval or proposal.
- Do not use no-T2 cases as edema negatives.
- Do not run validation packaging/upload or fold expansion from this audit.

## Suggested Next Required Action

Ask GPT planner to choose between:

1. bounded nnU-Net-anchored residual/component refiner, or
2. true SRR-v2.5 architecture build with strong backbone and data-derived retrieval banks.

This audit does not create that task.
