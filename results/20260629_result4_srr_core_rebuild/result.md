# Result 20260629 Result4 SRR Core Rebuild

- selection: `CORE_REBUILD_DEFER`
- action: architecture preflight only; no formal GPU job launched.
- current variants were not changed or overwritten.

## Findings

- Prior D4 `cross_modal_interaction_dictionary` remains the selected dictionary-bank reference, but it is not submission-ready and still has high HD95/component/remote-FP burden.
- Current `ExpertBank` masks unavailable experts, but its private experts receive fused features. SRR-v2 should keep modality-private feature streams private through expert computation.
- Current sprint audits found pipeline-level blockers first: ignore-label loss masking, decode calibration, and pathology checkpoint selection.

## Decision

Defer SRR-v2 formal training until the two remaining `20260628_myops_proposal` formal jobs complete and proposal selection is aggregated.

## Next Implementation Target

Implement an isolated `srr_v2_multiscale_private_sparse` route with modality-private inputs, at least two scales, sparse valid-expert routing, and task-specific scar/edema router priors.
