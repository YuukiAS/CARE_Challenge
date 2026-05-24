# Lane A Round03 Next Edema Trainable Smoke Execution Plan

Plan metadata:
- Type: next execution plan
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round03
- Status: ready for implementation pass
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round03plus_controller_myops_modality_aware_src_plan.md`
- Function: convert Round2 negative edema postprocess diagnosis into CARE-native trainable edema smoke: loss unit tests, gradient smoke, tiny overfit, then optional fold0 short train
- Do not: run full 5-fold training, create validation submissions, download pretrained weights, pull large external repos, use external data, use validation pseudo-labels, or use foreground_mean as a success criterion

## 1. Strategic Decision

Lane A should move from Round2 inference/postprocess diagnostics into Round3 trainable edema smoke.

Round2 showed that postprocess-only edema cleanup is not a viable mainline. Removing 1-voxel edema islands reduced component count from `3.3182` to `1.7273`, but GT-positive edema HD95 slightly worsened from `20.0115` to `20.0234`, and Dice fell from `0.3944` to `0.3935`. This is a diagnostic negative result, not a trainable gain.

Round3 decisions:

- `stop`: postprocess-only edema component deletion, ROI thresholding, and inference-side suppression as the main route.
- `stop/watch`: T2-aware inference suppression. In fold0, all edema GT-positive cases are T2-present, no-T2 cases are edema empty-GT, and the current nnU-Net has no no-T2 edema false positive.
- `go/watch`: training-side T2-aware edema loss masking or downweighting, but only as a smoke test and never treating no-T2 empty-GT as strong negative edema evidence.
- `go`: class_4 edema-specific trainable loss, HD-aware diagnostics, small-lesion-aware logging, and explicit scar class_5 interference checks.

The current bottleneck is T2-present complete-modality edema quality, especially CenterC complete cases, not inference cleanup.

## 2. Round3 Execution Boundary

Round3 must run in this order:

1. Loss unit tests.
2. Gradient smoke.
3. Tiny-overfit smoke.
4. Optional fold0 short train only if the first three gates pass.

Hard limits:

- Do not run full 5-fold training.
- Do not create or upload CARE validation packages.
- Do not treat foreground mean or aggregate mean as a success metric.
- Do not integrate AdaMM, UniME, BiomedParse, I-MMSeg, diffusion, harmonization, or foundation model pipelines.
- Do not download pretrained weights.
- Do not train with external data, pseudo-labeled external data, generated external samples, or validation pseudo-labels.

Deep Research is used in this round only as a mechanism source: focal/Tversky losses, unified focal losses, HD-aware or boundary-aware losses, small-lesion diagnostics, and missing-modality-aware loss weighting. This round must not reproduce full external repositories.

All Round3 Lane A outputs must be written under:

```text
results/diagnostics/care_myocardium/laneA_myops/round03_trainable_smoke/
```

Expected outputs:

- `loss_config_candidates.yaml`
- `edema_loss_gradient_smoke.csv`
- `edema_loss_gradient_smoke.md`
- `t2_aware_training_strategy_smoke.csv`
- `t2_aware_training_strategy_smoke.md`
- `tiny_overfit_case_table.csv`
- `round3_laneA_decision_table.md`

## 3. Task 1: `edema_loss_gradient_smoke`

Purpose: compare small first-party class_4 edema loss candidates before any meaningful training run.

Candidates:

| candidate | intended role | class_4 scope | scar class_5 protection | empty-GT handling |
| --- | --- | --- | --- | --- |
| `edema_only_weighted_dice_ce` | edema-only weighted Dice+CE auxiliary loss | Applies only to class_4 logits and class_4 target mask; added to normal base loss with a small smoke weight. | Keep scar class_5 in the unchanged base segmentation loss; log class_5 gradient norm and interference ratio. | Compute and report separately for empty-GT cases; do not let empty-GT suppression define success. |
| `edema_focal_tversky` | imbalance and small-lesion auxiliary loss inspired by focal/Tversky and CATMIL-style lesion sensitivity | Applies only to class_4 soft probability and binary edema target. | Do not alter class_5 target or combine scar with edema; fail if class_5 gradient changes materially. | Use explicit empty-target branch with stable epsilon; report whether it behaves as background-only pressure. |
| `edema_unified_focal` | unified focal-style class_4 auxiliary objective | Applies only to class_4, preferably as a binary one-vs-rest edema auxiliary term. | Keep class_5 supervised only by base loss; record class_5 logit gradient and loss delta. | Empty-GT cases must be logged separately and cannot be the main improvement source. |
| `edema_surface_or_distance_loss` | boundary/HD-aware auxiliary signal inspired by InverseForm, ST-Loss, and differentiable HD/boundary losses | Applies only to class_4 foreground boundary/distance representation from CARE labels. | No scar boundary term in this smoke; fail on class_5 interference. | Empty-GT cases should produce zero or stable bounded auxiliary loss, not NaN/Inf or unbounded background pressure. |

Implementation constraints:

- Run on CARE Dataset501 fold0-compatible tensors only.
- Do not write predictions as replacements for baseline outputs.
- Use compact label semantics: `4 = edema / myops_edema`, `5 = scar / myops_scar`.
- If a candidate needs distance transforms, derive them only from CARE labels already available in the training split.
- Keep candidate code minimal and local to the smoke implementation path in the later implementation pass.

Required `edema_loss_gradient_smoke.csv` columns:

- `candidate`
- `case_id`
- `center`
- `modality_group`
- `t2_present`
- `edema_gt_positive`
- `loss_value`
- `base_loss_value`
- `aux_loss_value`
- `total_grad_norm`
- `class4_logit_grad_norm`
- `class5_logit_grad_norm`
- `class5_interference_ratio`
- `nan_or_inf`
- `empty_gt_behavior`
- `pass_fail`
- `fail_reason`

Required Markdown summary in `edema_loss_gradient_smoke.md`:

- setup table: data split, fold, label semantics, candidate loss weights, sample counts.
- candidate table: pass/fail, NaN/Inf status, class_4 gradient health, class_5 interference.
- subgroup notes: T2-present GT-positive edema, complete-modality edema, CenterC edema, no-T2 empty-GT stability.
- decision: which candidates may enter tiny-overfit smoke.

Fail-fast criteria:

- Any NaN/Inf loss or gradient.
- Class_4 logit gradient is zero or numerically negligible on GT-positive edema cases.
- Class_5 interference is obvious in gradient norm, loss value, or early prediction sanity.
- Empty-GT behavior is the only apparent positive signal.
- Candidate requires external data, external repo reproduction, or pretrained weights.
- Candidate cannot be expressed as a small first-party CARE loss wrapper.

## 4. Task 2: `t2_aware_edema_training_strategy_smoke`

Purpose: compare training-side T2-aware edema strategies without using no-T2 empty-GT cases as strong negative edema evidence.

Strategies:

| strategy | behavior | decision intent |
| --- | --- | --- |
| `report_only` | Record `t2_present`, center, and modality group; do not change loss. | Control condition. |
| `no_t2_edema_loss_masking` | Mask the class_4 edema auxiliary loss on no-T2 cases; keep base segmentation loss and scar/anatomy learning active. | Tests whether no-T2 empty-GT should be excluded from edema auxiliary supervision. |
| `no_t2_edema_loss_downweighting` | Downweight class_4 edema auxiliary loss on no-T2 cases, for example smoke weights `0.1` or `0.25`; keep T2-present edema weight at `1.0`. | Softer alternative when full masking removes useful regularization or creates instability. |

Rules:

- No-T2 empty-GT cases are not strong negative edema labels.
- T2-present GT-positive edema cases remain the primary optimization target.
- Scar class_5 remains supervised and reported separately.
- Modality groups must be reported separately: C0+LGE+T2, C0+LGE, LGE-only.
- CenterC complete-modality edema must be explicitly shown.

Required `t2_aware_training_strategy_smoke.csv` columns:

- `strategy`
- `case_id`
- `center`
- `modality_group`
- `t2_present`
- `edema_gt_positive`
- `edema_loss_weight`
- `class4_loss_value`
- `class5_loss_value`
- `class4_grad_norm`
- `class5_grad_norm`
- `no_t2_empty_gt_stability`
- `pass_fail`
- `fail_reason`

Required Markdown summary in `t2_aware_training_strategy_smoke.md`:

- setup table with strategy weights and sample counts.
- per-strategy gradient table.
- no-T2 empty-GT stability table.
- T2-present GT-positive edema table.
- scar class_5 interference table.
- recommendation for tiny-overfit: `report_only`, `masking`, `downweighting`, or no T2-aware strategy.

Fail-fast criteria:

- A strategy improves only by suppressing no-T2 empty-GT artifacts.
- T2-present GT-positive edema gradients weaken materially.
- CenterC complete edema is ignored or worsens in early smoke.
- Scar class_5 gradient/loss is damaged.
- Strategy creates hidden inference-time suppression logic.

## 5. Task 3: `tiny_overfit_or_fold0_short_train_gate`

Purpose: verify whether candidate losses can learn edema structure on a tiny CARE subset before any fold0 short train.

Prerequisite:

- At least one Task 1 loss candidate passes gradient smoke.
- One Task 2 strategy is selected as either `report_only`, `no_t2_edema_loss_masking`, or `no_t2_edema_loss_downweighting`.
- No candidate shows scar class_5 interference.

Tiny-overfit subset requirements:

- Include T2-present edema GT-positive cases.
- Include complete-modality cases.
- Include CenterC complete cases.
- Include at least one no-T2 empty-GT group for monitoring only.
- Preserve independent scar class_5 evaluation.

Allowed training scope:

- Tiny subset overfit first.
- Optional short fold0 smoke only if tiny-overfit passes.
- Use strict epoch/runtime caps.
- This is a trend and wiring validation, not a leaderboard attempt.

Required `tiny_overfit_case_table.csv` columns:

- `candidate`
- `strategy`
- `case_id`
- `center`
- `modality_group`
- `t2_present`
- `edema_gt_positive`
- `myops_edema_dice`
- `myops_edema_hd`
- `myops_edema_hd95`
- `myops_scar_dice`
- `myops_scar_hd`
- `myops_scar_hd95`
- `edema_component_count`
- `edema_small_fp_count`
- `edema_remote_fp_count`
- `edema_pred_gt_volume_ratio`
- `scar_component_count`
- `scar_pred_gt_volume_ratio`
- `pass_fail`
- `fail_reason`

Optional fold0 short train gate:

- Only run after tiny-overfit success.
- Compare against the nnU-Net fold0 local reference, not against foreground mean.
- Treat the short train as a directional signal only.
- Do not expand to folds 1-4 in Round3.

Pass criteria:

- T2-present GT-positive edema improves in trend without HD95 or component regression.
- Complete-modality edema improves or stays neutral with better boundary/component behavior.
- CenterC edema does not worsen.
- no-T2 empty-GT stability remains intact.
- scar class_5 Dice/HD/HD95 does not materially degrade.

Fail criteria:

- Edema Dice improves while HD95 or component count worsens.
- Any apparent gain is mainly from empty-GT artifact handling.
- Scar class_5 is damaged.
- Prediction volume ratio indicates overgrowth or over-pruning.
- Tiny-overfit cannot fit class_4 edema at all.
- Candidate requires longer training to show any non-degenerate signal.

## 6. Metrics And Reporting Gates

All reports must keep `myops_edema` and `myops_scar` separate. Do not collapse into foreground mean.

Required subgroup reporting:

- T2-present GT-positive edema.
- Complete-modality edema.
- CenterC complete-modality edema.
- no-T2 empty-GT stability.
- CenterB versus CenterC when sample size permits.
- C0+LGE+T2, C0+LGE, and LGE-only modality groups.

Required metrics:

- Dice.
- HD.
- HD95.
- component count.
- small FP count.
- remote FP count.
- pred/GT volume ratio.
- empty-GT artifact flag.
- scar class_5 interference flag.

Hard fail conditions:

- Any Dice gain paired with worse HD95 or worse component behavior.
- Any gain caused by empty-GT handling rather than GT-positive edema quality.
- Any clear damage to scar class_5.
- Any result reported only as aggregate foreground mean.
- Any method that hides inference suppression inside the training strategy.

`round3_laneA_decision_table.md` must end with one of these decisions:

- `advance_to_fold0_short_train`
- `revise_loss_and_repeat_gradient_smoke`
- `keep_report_only_t2_strategy`
- `stop_candidate_due_to_scar_interference`
- `stop_round3_trainable_route`

## 7. Next Implementation Prompt Draft

请在 `/overflow/htzhu/CARE` 中执行 Lane A Round3 的 trainable edema smoke。严格限制为 loss unit test、gradient smoke、T2-aware training-side strategy smoke、tiny-overfit smoke；只有这些通过后才允许一个短 fold0 smoke。不要 full 5-fold，不要提交长训练 Slurm，不要创建 validation zip，不要下载权重，不要拉大型外部 repo，不要接入 foundation model，不要使用外部数据或 validation pseudo-label。

先读取：

- `docs/plans/laneA_round03_next_edema_trainable_smoke_execution.md`
- `docs/plans/laneA_round02_completed_myops_edema_targeted_smoke_addendum.md`
- `docs/notes/baseline/care_myocardium_diagnostics_execution_results.md`
- `docs/notes/domain_adaptation/domain_adaptation_relevance_20260519.md`

所有输出写入：

```text
results/diagnostics/care_myocardium/laneA_myops/round03_trainable_smoke/
```

必须生成：

- `loss_config_candidates.yaml`
- `edema_loss_gradient_smoke.csv`
- `edema_loss_gradient_smoke.md`
- `t2_aware_training_strategy_smoke.csv`
- `t2_aware_training_strategy_smoke.md`
- `tiny_overfit_case_table.csv`
- `round3_laneA_decision_table.md`

重点评估 `myops_edema` 和 `myops_scar`，不要使用 foreground_mean。必须按 T2-present GT-positive edema、complete-modality edema、CenterC edema、no-T2 empty-GT stability 分组报告 Dice、HD、HD95、component count、small/remote FP、pred/GT volume ratio。任何只来自 empty-GT artifact 的提升、任何 Dice 提升但 HD95/component 变差、任何明显损伤 scar class_5 的方案都必须判 fail。
