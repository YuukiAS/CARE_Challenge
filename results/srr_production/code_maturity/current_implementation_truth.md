# SRR Batch 0 Current Implementation Truth

- Repository: `/users/a/e/aereinh/CARE`
- Branch: `main`
- Base HEAD audited before Batch 0 edits: `3f36a4ec62278ae097267d9c0eea14dd5e68a9e7`
- Scope: static/source audit, formal authority convergence, anti-bypass tests only
- Formal training status: `BLOCKED_PENDING_BATCH1_REPAIR`

Batch 0 did not run training, optimizer loops, Slurm, validation packaging, uploads, architecture search, or a second SRR implementation. The current authority decision is deliberately conservative: there is no trusted production training entrypoint yet.

## Formal Authority Summary

`configs/srr_production/entrypoints.yaml` is the only Batch 0 formal-entrypoint authority file. It declares no `formal_entrypoints` and marks the training status as `BLOCKED_PENDING_BATCH1_REPAIR`.

Candidate paths retained for Batch 1 repair are:

| Path | Current role | Batch 0 classification | Reason |
| --- | --- | --- | --- |
| `src/care_myocardium/models/srr_propref.py` | selected model class source | real but incomplete | Existing model includes encoder, dictionary/proposal, crop refiner, and variant-specific final outputs, but formal prototype/memory authority is not fully connected. |
| `scripts/training/run_srr_propref_myops_fold0.py` | MyoPS fold0 runner candidate | real but incomplete | Reads real Dataset501 cases and cached nnU-Net validation anchors, but lacks production authority gates, M10 CLI exposure, strict prototype provenance, and formal checkpoint continuity. |
| `scripts/evaluation/evaluate_predictions.py` | local metric recompute candidate | already real and reusable for local metrics | Reads prediction/GT NIfTI and recomputes Dice plus optional HD/HD95; not a training or hosted-score authority. |

Forbidden paths are listed in `configs/srr_production/entrypoints.yaml` and include all Round04 B3-B8 synthetic/proxy scripts plus their `jobs/route_B_round04/run_B*_*.sh` wrappers.

## Already Real and Reusable

- `scripts/evaluation/evaluate_predictions.py` recomputes metrics from prediction and ground-truth NIfTI files. Dice is prediction/GT based, and HD/HD95 are optional surface-distance calculations after prediction-to-GT resampling.
- `scripts/training/run_srr_propref_myops_fold0.py` has real Dataset501 data plumbing: it uses `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS`, `data/benchmarks/protocol/splits_MyoPS.json`, and cached nnU-Net fold validation `.npz`/`.nii.gz` anchors under `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres`.
- `SRRProposeRefineMyoPS` is an existing implementation, not created in Batch 0. It contains real forward logic for encoder features, retrieval/gates, proposal dictionary, local crop refiner, and multiple final-output regimes.
- `ProposalDictionary.load_prototype_bank` can load externally supplied prototype banks into the model buffers.
- `build_prototype_bank_from_labeled_features` and the runner's runtime prototype fitting path can fit prototypes from labeled features when real vectors are available.
- Pattern-SIP, proposal, scar-refiner, edema-refiner, anatomy, bounded-correction, and negative-space losses contain real differentiable terms when their required tensors and weights are present.

## Real but Incomplete

- The current MyoPS SRR runner consumes cached nnU-Net validation anchors rather than performing live nnU-Net checkpoint inference. Real checkpoints exist, but the SRR runner does not directly load them for anchor generation.
- Runtime prototype fitting exists, but formal mode does not yet reject all deterministic fallback conditions, prove fold-safe OOF construction, or record full source hashes/counts for the prototype banks.
- The M10 pure proposal-refinement variants are instantiable in model code, but the fold0 runner CLI does not expose them as training variants.
- `M10CrossFittedPrototypeMemory` and `SafePrototypeMemoryBank` exist, but the current `SRRProposeRefineMyoPS.forward` path does not use their query outputs as proposal logits or formal memory losses.
- Checkpoint save/load exists within one SRR runner execution, but optimizer state, prototype state, exact config, and parent-run continuity are not yet formalized for production authority.
- The local evaluator is real, but production fair-evaluation authority still needs explicit empty-GT semantics, fold binding, SRR-vs-nnU-Net parity config, component outputs, and subgroup reports.

## Declared but Disconnected

- Memory-enabled M10 statuses can be surfaced through spatial dictionary configuration, but memory query outputs are not connected to final proposal/refinement logits in the current selected model path.
- `SafePrototypeMemoryBank` implements EMA-style memory behavior and no-T2 edema-negative safeguards, but it is not used by `SRRProposeRefineMyoPS.forward`.
- B7's official CineMA interaction is an isolated probe and does not feed official CineMA logits/features/uncertainty into downstream CineMyoPS export.
- B8 records registration receipts, but it does not connect real 4D Cine fixed/moving frame loading, transform application, temporal aggregation, and ED-space export into an executable downstream path.

## Synthetic or Proxy

- `scripts/training/route_B_round04/myops/B3/run_B3_representation.py` uses synthetic tensors/random anchors and independent `RouteBRound03MyoPS` initialization.
- `scripts/training/route_B_round04/myops/B4/run_B4_proposal.py` uses synthetic tensors and hard-coded proposal proxy metrics.
- `scripts/training/route_B_round04/myops/B5/run_B5_refiner.py` uses synthetic tensors and hard-coded `dice_proxy` rows.
- `scripts/training/route_B_round04/myops/B6/run_B6_joint.py` uses synthetic tensors/random anchors and fixed-formula casewise proxy metrics.
- `scripts/training/route_B_round04/cine/B7/run_B7_cinema_control.py` trains/probes on synthetic frame tensors and synthetic targets; official CineMA is not downstream authority.
- `scripts/training/route_B_round04/cine/B8/run_B8_registration.py` builds fixed/moving pairs from random tensors and `torch.roll`; manifest access supplies case IDs only.
- `jobs/route_B_round04/run_B3_representation.sh` through `run_B8_registration.sh` are forbidden as formal entrypoints because they launch the synthetic/proxy scripts with `--formal`.

## Historical Only

- Route B Round04 B3-B8 remain useful as historical evidence of what must not be promoted to formal authority.
- Route B Round03 model/Cine utilities remain historical or helper code unless a future Batch 1+ repair explicitly binds them to real data, checkpoints, and evaluator authority.
- Route A/C worktrees, route controllers, Round05 planning, and route promotion are out of scope for this Batch 0 task.

## Variant and Final-Output Truth

The full matrix is in `variant_final_output_matrix.csv`. The essential grouping is:

| Family | Variants | Final-output truth | Status |
| --- | --- | --- | --- |
| Legacy baseline residual | `baseline_srr`, `baseline_srr_t2_aware`, `baseline_srr_t2_noedema` | anchor logits plus bounded residual/gate correction | legacy baseline residual; not production formal |
| M6 branch arbitration | `m6_arbitrated`, `m7_arbitrated_sip`, `m8_arbitrated_sip_bounded` | anchor logits plus clipped weighted deltas | M6/M7/M8 branch-arbitration lineage; not final Batch 0 authority |
| M9 pure SRR-main | `m9_srrmain`, `m9_srrmain_sip`, `m9_srrmain_bounded` | final logits are `srr_logits`, not anchor residual output | real candidate family; needs formal gates |
| M10 pure proposal-refinement | `m10_pure_propref`, `m10_pure_propref_d1`, `m10_pure_propref_d2`, `m10_pure_propref_d3` | `outputs["logits"]` is still `srr_logits`; `m10_final_probabilities` is diagnostic only | instantiable model variants, but runner exposure/memory wiring incomplete |
| Baseline-preserving gate | legacy/M6 gate paths | preserves anchor unless bounded evidence supports correction | useful safety mechanism, not proof of production readiness |

## Anchor, Prototype, Loss, Checkpoint, and Metrics Truth

The detailed matrix is in `anchor_prototype_loss_checkpoint_matrix.csv`.

- Anchor source in the current candidate runner is real cached nnU-Net validation probability/prediction files, not placeholder tensors and not live checkpoint inference.
- The default `ProposalDictionary` buffer initialization is deterministic axis prototypes. This is acceptable as module initialization but forbidden as formal prototype evidence.
- Real train-fitted prototype construction exists in the runner, but formal production mode must require real positive/negative coverage, provenance hashes, fold-safe OOF semantics, and rejection of deterministic fallback.
- Memory losses are effectively placeholder-zero for the current selected SRR output because memory outputs are not emitted by `SRRProposeRefineMyoPS.forward`.
- B3 -> B4 -> B5 -> B6 continuity is token/file existence continuity, not parent model/optimizer/prototype/config state continuity.
- B4/B5/B6 metric outputs include hard-coded constants or fixed proxy formulas and are forbidden from formal authority.

## Cine Truth

The Cine-specific call graph is in `cine_call_graph.md`.

- B7 does not provide downstream official CineMA authority. It performs an isolated official-model probe and a synthetic adapter/control check.
- B8 does not load real 4D fixed/moving frame pairs or produce ED-space exported predictions. It uses synthetic pairs and records registration receipts.
- Real Cine repair in Batch 1 must connect actual 4D Cine files, ED/reference/key frames, official CineMA weights/logits/features/uncertainty, downstream adapter, real registration transform/warp, temporal aggregation, and ED-space output/export.

## Must Repair in Batch 1

Batch 1 should modify existing files/functions only:

| File | Functions | Required repair |
| --- | --- | --- |
| `scripts/training/run_srr_propref_myops_fold0.py` | `main`, `train_variant`, `fit_and_load_runtime_prototype_bank`, `propref_loss` | Add production-mode authority gates, expose the selected M10 variant if chosen, reject deterministic prototype fallback in formal mode, and record exact anchor/prototype/checkpoint hashes. |
| `src/care_myocardium/models/srr_propref.py` | `SRRProposeRefineMyoPS.forward`, `ProposalDictionary.forward`, `ProposalDictionary.load_prototype_bank` | Make final-output mode explicit; require real loaded prototype banks for formal proposal authority; connect or block memory-enabled variants. |
| `src/care_myocardium/models/srr_dictionary_memory.py` | `M10CrossFittedPrototypeMemory.update`, `M10CrossFittedPrototypeMemory.query`, `SafePrototypeMemoryBank.update`, `SafePrototypeMemoryBank.query` | Wire memory query outputs into proposal logits/losses or keep memory variants non-formal. |
| `src/care_myocardium/losses/srr_losses.py` | `expanded_srr_loss`, `prototype_memory_alignment_loss`, `semantic_retrieval_regularization`, `negative_space_consistency_loss` | Add formal dependency checks so zero/disconnected terms cannot pass as optimized losses. |
| `scripts/evaluation/evaluate_predictions.py` | `main`, `dice_per_class`, `hd_class`, `hd95_class` | Bind fair fold evaluation, empty-GT semantics, component/remote-FP outputs, and nnU-Net comparison parity. |
| `scripts/training/route_B_round04/cine/B7/run_B7_cinema_control.py` | `main`, `train_adapter`, `probe_official_cinema` | Either demote permanently or rewrite as a real Cine adapter using official outputs as downstream inputs; no synthetic formal path. |
| `scripts/training/route_B_round04/cine/B8/run_B8_registration.py` | `main`, `run_registration`, `make_pair` | Replace synthetic pairs with real 4D frame loading, real registration, transform/warp, temporal aggregation, and ED-space export before any formal status. |

## Batch 0 Conclusion

Batch 0 establishes current implementation truth and closes the formal-authority bypass that could promote B3-B8 synthetic/proxy artifacts or their wrappers as production entrypoints. It does not prove SRR model maturity, training readiness, leaderboard performance, or superiority over nnU-Net.
