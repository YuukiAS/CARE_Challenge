# Dictionary Design Matrix

Task: `prompts/tasks/20260626_dict_research.md`

## Priority Designs

| priority | design | core mechanism | CARE adaptation | code touchpoints | expected signal | main risk | bank status |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `task_specific_dictionary` | Separate lightweight shared/private expert banks for anatomy, scar, and edema. | Scar can specialize on LGE while edema can use T2-private + shared anatomy/pathology evidence without forcing the same bank to serve all heads. | `src/care_myocardium/models/srr_blocks.py`, `src/care_myocardium/models/srr_myops.py`, `scripts/training/run_srr_myops_fold0.py` | Better scar all-case Dice or edema GT-positive Dice through less head competition. | More parameters may overfit fold0 or starve private experts. | implemented/submitted |
| 2 | `multiscale_dictionary` | Apply dictionary retrieval at full-resolution features plus pooled context features. | Adds coarse context for pathology localization while keeping the current fold0 patch and evaluator contract. | same SRR model/runner files | Lower component burden or HD95 by letting dictionary influence localization, not only global semantics. | Context retrieval may be dominated by reference/full-resolution route. | implemented/submitted |
| 3 | `cross_modal_interaction_dictionary` | Add legal interaction experts, e.g. LGE-T2 and LGE-C0, masked off when either modality is absent. | Tests Result4/BR2 note that modality-specific dictionaries capture main effects and interaction dictionaries may be needed for cross-modal disease evidence. | `ExpertBank.interaction_pairs`, runner variant | Better complete-modality edema/scar by learning interactions instead of independent modality addition. | Complete cases are limited; interaction experts may be weakly supervised. | implemented/submitted |
| 4 | `anchor_guided_dictionary` | Add task-specific router bias toward interpretable anchors: LGE-scar, T2-edema, C0/anatomy, shared prior. | Uses medical evidence anchors without center ID, external weights, or pseudo-labels. | `RetrievalRouter.expert_bias`, `SRRMyoPSLite.dictionary_mode` | More interpretable usage and stronger LGE-only scar fallback / T2 edema route. | Bias can over-constrain routing if imaging evidence contradicts the anchor. | implemented/submitted |
| 5 | `hierarchical_router_dictionary` | First mask to legal availability subset, then mix feature-conditioned routing with an availability prior. | Reduces invalid expert competition and row-level collapse while preserving feature-conditioned retrieval. | `RetrievalRouter.hierarchical_prior_strength` | More stable usage entropy and no-T2 contract with comparable Dice. | Availability prior can become too uniform and weaken specialization. | implemented/submitted |
| 6 | `prototype_slot_dictionary` | Learn per-task prototype/slot memory and retrieve channel/spatial prototypes. | Useful for lesion compactness and prototype diversity, especially after the first bank identifies which route is stable. | new prototype memory module, loss/reporting extensions | Better small lesion localization and diversity diagnostics. | Heavier implementation; easy to create toy prototypes without fold0 signal. | deferred |

## Mechanism Notes

- **Where to place dictionary:** current sprint should favor feature-block dictionaries at bottleneck/full-resolution fused features plus one pooled context scale. Token-level or transformer dictionaries are too heavy for the 8-hour fold0 sprint.
- **Gate inputs:** availability-only gates are stable but collapse to modality-pattern lookup. The current implementation keeps availability + feature summary, matching Result4's dense segmentation adaptation.
- **Anti-collapse without forced uniformity:** use entropy floor, coverage/load-balance proxy, max-weight penalty, expert dropout, and hierarchical availability prior. The goal is interpretable specialization, not equal use of every expert.
- **Scar/edema specialization:** scar needs LGE-private and LGE-only fallback; edema must remain T2-conditioned and cannot treat no-T2 cases as hard negatives.
- **SIP approximation:** current runnable proxies are usage coverage, entropy floor, max row weight, task usage diversity, and interaction/private expert starvation diagnostics.

## Designs Not Recommended For This Sprint

- Full sparse top-k MoE with token dispatch: too much routing infrastructure for the current 3D patch trainer.
- External foundation/foundation-segmentation models: outside task scope and not a substitute for CARE fold0 evidence.
- Generative imputation or external missing-modality synthesis: conflicts with the no external data/weights constraint and risks inventing T2 evidence.
- Center-ID conditioned experts: may overfit center shortcuts and is unavailable/unsafe for validation inference.
