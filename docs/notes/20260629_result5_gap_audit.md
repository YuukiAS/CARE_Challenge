# 2026-06-29 Result5 Gap Audit

status: `TASK_PREPARED_BY_CHATGPT`

This note records the audit conclusions that motivated the 20260629 continuation tasks. It is intentionally task-scoped documentation only; no training code or Git branch was changed by this note.

## Executive conclusion

Do not stop the current `20260628_myops_proposal` formal jobs. They should finish and be aggregated because they can still show whether the current proposal head has any weak proposal signal. However, do not wait idle for them. The current implementation does not yet equal the Result4/Result5 design in the figure or in `Result5`: it is a lightweight SRR/proposal head, not a complete SRR-ProposeRefine system.

The completed `proposal_pos_neg_basic` result should be interpreted as weak first-stage evidence, not as a proof that the Result5 idea is invalid. The more important risk is that the current code has loss/decoding/checkpoint and architecture gaps that can keep results near the 0.1 Dice regime even if more epochs are spent.

## What waiting for the running Result5 jobs can still answer

1. It can test whether `proposal_anatomy_distance` or `proposal_uncertainty_gate` rescues the weak `proposal_pos_neg_basic` readout by adding stronger anatomy pressure, remote penalty, or uncertainty pressure.

2. It can verify that the repaired uncertainty job no longer fails from zero-byte checkpoint writing.

3. It can produce the required proposal diagnostics: proposal recall, proposal precision, component count, remote FP, small FP, prototype usage, and subgroup metrics.

4. It can decide whether the current proposal route reaches `SELECT_PROPOSAL_ROUTE`, `REVISE_PROPOSAL_AND_REPEAT`, `STOP_PIPELINE_BUG`, or `STOP_NO_PROPOSAL_SIGNAL`.

5. It cannot by itself produce true soft-cascade refinement, hard-negative replay, multi-scale SRR, pathology-aware checkpointing, or calibrated final decoding.

## Result5 gaps that the running jobs will not fix

1. No actual soft-ROI refinement exists in the current implementation. The proposal head directly mixes proposal logits back into final scar/edema logits instead of producing candidate regions for a separate pathology-specific refiner.

2. Proposal is currently final-logit shaping, not a candidate generator. The current code mixes `0.40 * original + 0.60 * proposal`; if proposal logits are uncalibrated, this can degrade the final mask even if the original evidence has weak signal.

3. There is no hard-negative replay or memory bank. Result5 explicitly calls for false-positive components and safe negative spaces to be mined and fed back; current loss only uses current-batch positive/negative similarity margins.

4. The `proposal_uncertainty_gate` route does not implement the scar-edema soft relation described in the task. It only uses uncertainty penalties on positive and safe background regions.

5. The so-called anatomy distance route uses local averaged union-prior confidence, not a true myocardium-neighborhood distance map, endo/epi distance, or dilated soft ROI distance.

6. The training schedule is not staged. Evidence trunk, proposal head, retrieval regularization, and auxiliary losses are optimized together. Result5 called for evidence warmup, proposal learning, refinement learning, and only then low-LR joint fine-tuning.

7. Checkpoint selection is patch-loss based, not pathology-metric based. The current best checkpoint is not selected by full-volume scar/edema Dice, HD95, remote FP, or component burden.

8. Final output composition is not calibrated. Anatomy is trained by multiclass CE, scar/edema by binary losses, then all logits are concatenated and decoded by raw argmax.

## Result4 SRR gaps that also remain

1. No four-scale encoder/retrieval bank exists. The current `SRRMyoPSLite` is essentially single-scale.

2. Modality-private experts are not truly modality-private because experts operate on the already masked-averaged fused feature map, not on modality-specific feature streams.

3. The router is dense softmax, not sparse top-k/entmax/sparsemax retrieval.

4. The regularizer is entropy/coverage balancing, not a segmentation-native SIP/integrativeness regularizer across availability or style groups.

5. Scar and edema are not structurally tied to LGE and T2 private evidence banks, respectively. Availability enters the router, but the pathology streams do not truly retrieve from LGE-only or T2-only feature dictionaries.

6. No component-aware inference or pathology-aware full-volume decoding rule exists.

## High-probability causes for the persistent 0.1 regime

1. The selected D4 dictionary route was already near the 0.1 Dice regime; Result5 inherited a weak evidence trunk.

2. Main losses likely do not mask `IGNORE_LABEL = -1` padding consistently. Proposal auxiliary loss uses a valid mask, but core anatomy/scar/edema losses should be re-audited and fixed if needed.

3. Binary pathology heads and multiclass anatomy logits are decoded by raw argmax without scale calibration.

4. The proposal logit can numerically dominate the final pathology logit after division by a low temperature and 0.60 final mixing.

5. Prototype dictionaries are too shallow and not memory-based; they are unlikely to model normal myocardium, blood pool, artifacts, remote false positives, or T2 noise robustly.

6. Dense softmax router plus uniform coverage regularization may average experts rather than select reliable representers.

7. The current private experts consume fused features, weakening the claimed LGE-driven scar and T2-driven edema mechanisms.

8. Best-checkpoint selection is patch-loss based and may select a checkpoint that is poor on full-volume lesion metrics.

9. Proposal metrics and final prediction use different decoding semantics: proposal uses sigmoid threshold, final segmentation uses argmax over mixed anatomy/pathology logits.

## Parallel work policy

The current `20260628_myops_proposal` jobs should continue. Parallel work should not kill, overwrite, or restart them. New work must be isolated under `results/20260629_*` and should first run audit/export/preflight tasks that do not require a new long GPU job. Formal new training should only start after pipeline bugs are fixed or after the current proposal selection state is known.
