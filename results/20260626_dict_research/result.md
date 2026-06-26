# Result 20260626 Dictionary Research

status: `COMPLETED_BOUNDED_SYNTHESIS`

## Summary

This task converted Result4/R2 ideas into CARE-executable dictionary designs. The key conclusion is that the next useful sprint should not ask whether dictionary retrieval has value; previous fold0 evidence already shows recovered SRR beats conditional, no-dictionary, and weak-SIP anchors on the primary pathology Dice checks. The useful question is which dictionary organization makes the representation more interpretable and less prone to false-positive/component burden.

I prioritized five designs that can be implemented in the current first-party SRR code within the 8-hour job limit: `task_specific_dictionary`, `multiscale_dictionary`, `cross_modal_interaction_dictionary`, `anchor_guided_dictionary`, and `hierarchical_router_dictionary`. A sixth design, `prototype_slot_dictionary`, is promising but deferred because it needs a separate prototype memory/loss/reporting layer and is more appropriate after the first bank identifies a stable route.

## Answers To Required Questions

1. **Where should the dictionary sit?** Put it in feature blocks, not complete encoders or token-level transformers. The current sprint should test full-resolution fused features plus a pooled context scale, and task-specific banks at the same feature level.
2. **What should drive the gate?** Use availability + feature summary + task-specific router. Availability-only gates are stable but degenerate into modality-pattern lookup.
3. **How to avoid collapse without forcing uniformity?** Combine entropy floor, coverage/load-balance proxy, max-weight penalty, expert dropout, and hierarchical availability prior. The target is interpretable specialization, not equal use.
4. **How to specialize scar/edema?** Scar should bias toward LGE-private/shared routes and preserve LGE-only fallback. Edema should bias toward T2-private plus shared anatomy/pathology routes and keep no-T2 cases out of dense edema negative supervision.
5. **What SIP approximations are practical?** Use usage coverage, entropy floor, max row weight, expert starvation checks, task usage diversity, and interaction/private expert usage by modality group.
6. **What can be verified in 1-2 days?** The five submitted bank variants above can run as independent fold0 jobs with existing evaluator, subgroup metrics, component metrics, and retrieval usage logs.
7. **What is too heavy now?** Token-dispatch sparse MoE, prototype memory as a first bank variant, external foundation models, generative missing-modality synthesis, and center-ID experts.

## External Anchors

- HeMIS supports no-imputation missing-modality segmentation using modality embeddings aggregated over available modalities: https://arxiv.org/abs/1607.05194
- ShaSpec supports shared-specific feature modelling for missing-modality settings and is directly relevant to shared/private decomposition: https://arxiv.org/abs/2307.14126
- Soft Merging of Experts motivates soft routing/anti-collapse alternatives to brittle discrete top-k routing: https://arxiv.org/abs/2306.03745
- Prototype medical segmentation work supports prototype/slot ideas but was deferred as heavier than the current bank: https://arxiv.org/abs/2406.18074

## Output Files

- `results/20260626_dict_research/dictionary_design_matrix.md`
- `results/20260626_dict_research/query_log.md`
- `results/20260626_dict_research/MANIFEST.md`

## Permissions And Non-Actions

No external data, external weights, repo clone, installation, validation upload, or Slurm submission was performed by this research task. The dictionary bank Slurm jobs were submitted under the separate `20260626_dict_bank` execution path authorized by the goal.
