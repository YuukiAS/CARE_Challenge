# 20260706 M7 continued blocker repair contract

status: `MERGE_INTO_SHARED_EXECUTOR_AND_REVIEWER_PROMPTS`
merge_target:
  - `prompts/shared/EXECUTOR_PROMPTS.md`
  - `prompts/shared/REVIEWER_PROMPTS.md`
source_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`
source_review_decision: `M7_AUDITED_NEEDS_REVISION`
planner: `ChatGPT/GPT thread`

## 0. Scope

This file defines a continued M7 repair task. It is not M8, not route promotion, and not a new research direction. It is a bounded repair of the M7 reviewer blockers:

1. `loss_component_gradient_sanity.csv` contains 75/75 `BACKWARD_FAILED:RuntimeError` rows.
2. hard subgroup evidence is all CenterA / LGE-only / no-T2 and does not cover T2-present, CenterB/CenterC, remote-FP-positive, small-lesion, or large-lesion cases.
3. Cine only preserved the M5 registration/temporal dictionary gap. M7 continued must attempt a real same-safe-subset non-reference registration repair before preserving that gap.
4. `completion_check.md`, `review_request.md`, and `MANIFEST.md` must be revised so a packet with unresolved hard blockers cannot claim ready-for-review.

## 1. Executor prompt: M7 continued reviewer-blocker repair

```text
只执行 M7 continued：reviewer-blocker repair for `results/20260705_srr_v3_m7_training_and_cine_utilization/`。

开始前确认：
- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md` 包含 `M7_AUDITED_NEEDS_REVISION`；否则写 `M7_CONTINUED_BLOCKED_BY_REVIEW_STATE` 并停止。
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 包含 `M6_AUDITED_GO`。
- 如果继续 Cine 子线，`results/20260705_srr_v3_m5_cine_secondary_contract/review.md` 包含 `M5_AUDITED_DIAGNOSTIC_GO`。

不要 validation packaging/upload，不要 hosted metric claim，不要 route promotion，不要 scientific stop，不要启动 M8，不要写 `review.md`。

### A. 修复 loss gradient sanity

当前 75/75 `BACKWARD_FAILED` 是硬 blocker。不能通过重命名或改表格文字修复，必须修代码。

具体实现决定：

1. 修改 `src/care_myocardium/losses/srr_losses.py` 的 `srr_m6_expanded_total_loss`，增加类似参数：
   `detach_metrics: bool = True`。
   - 默认 `True` 保持日志安全。
   - M7 gradient sanity 使用 `False`，返回 graph-connected component tensors。
   - 必须让以下 component 在 gradient sanity mode 下保持 graph：`loss_anatomy_union_lv_rv`、`loss_scar_proposal`、`loss_edema_proposal_t2_present_only`、`loss_scar_refiner_roi`、`loss_edema_refiner_t2_present_roi`、`loss_anchor_preservation_outside_roi`、`loss_branch_arbitration_consistency`、`loss_bounded_correction`、`loss_component_remote_fp`、`loss_no_t2_edema_safety`、`loss_dictionary_entropy_coverage_load_balance`、`loss_prototype_diversity_margin`、`m6_expanded_total_loss`。

2. 修改 `scripts/training/run_srr_propref_myops_fold0.py`：
   - step-1 gradient sanity 必须在 main training `loss.backward()` 之前执行；
   - 对每个 component 单独 `model.zero_grad(set_to_none=True)`，再 `component.backward(retain_graph=True)`；
   - 记录 `requires_grad`、`grad_l2_norm`、`param_with_grad_count`、`status`；
   - 只有真实 mask-gated 的 component 才允许 `LEGITIMATE_MASKED_NA`，并必须写 `zero_justification`、`batch_cases`、`t2_present_batch_fraction`、`target_voxel_count`。

3. 重新运行 M7 continued gradient sanity。可以使用已有 M7 checkpoint，也可以做一个短的 gradient-sanity-only run，但必须使用真实 M7 model、真实 patch、真实 label、真实 availability、真实 anchor/context，不得使用 M6 synthetic tensors。

4. 更新：
   - `loss_component_gradient_sanity.csv`
   - `loss_component_gradient_fix_report.md`
   - relevant unit tests and `unit_test_report.md`

不得写 ready，如果任何 required component 仍是 `BACKWARD_FAILED`、`EVIDENCE_NOT_FOUND`、无解释 `ZERO_GRAD_OR_DETACHED`、或 `param_with_grad_count=0`。

### B. 修复 hard subgroup coverage

实现确定性的 hard subgroup case selector，不允许临场挑 case。

新增或修改 first-party helper，例如 `select_m7_hard_subgroup_eval_cases`。它必须读取 fold split、case metadata、labels、nnU-Net anchor availability，并优先覆盖：

- `T2_present_complete`：C0+LGE+T2，优先 edema-labeled / GT-positive edema；
- `CenterB` / `CenterC`；
- `no_T2_empty_GT`；
- `remote_FP_positive`：nnU-Net anchor 或现有 M7 prediction remote FP count > 0；
- `small_lesion`：pathology GT voxel volume lower tertile；
- `large_lesion`：pathology GT voxel volume upper tertile；
- `GT_positive_scar` / `GT_positive_edema`。

Formal best-variant metrics must prefer fold validation cases. If fold validation lacks a subgroup, create a separate `diagnostic_hardcase_eval` stratum from same-split train/hardcase cases, with explicit fields:

- `split_role=formal_val` or `diagnostic_train_hardcase`
- `eligible_for_best_variant_decision=true/false`
- `leakage_caveat`
- `reason_if_not_formal_val`

Diagnostic hardcase rows may support mechanism interpretation only. They must not be used for route promotion or formal best-variant selection.

Required outputs:

- `m7_hard_subgroup_case_manifest.csv`
- updated `same_split_help_harm.csv`
- updated `hard_subgroup_metrics.csv`
- `hard_subgroup_coverage_report.md`

Do not write ready if coverage remains all CenterA/LGE-only/no-T2. If required groups are genuinely unavailable, write `M7_NEEDS_EVIDENCE` or `M7_NEEDS_REVISION`, not ready.

### C. Cine registration repair: implement before preserving the gap

Do not only copy M5 evidence. Implement and run a M7 continued Cine registration repair helper, for example:

`scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py`

The helper must discover or generate CineMA/equivalent frame-wise anatomy outputs. If existing CineMA outputs are available, use them. If repo-local inference and local weights exist, run them. If not, record `CINEMA_OUTPUT_UNAVAILABLE` with exact missing paths.

Build a same-safe-subset with at least 3 cases and at least 2 non-reference frame pairs per case when data allow. Use ED/frame0 as reference and mid/ES or nearest available non-reference frames.

Run actual non-reference registration options:

- `CineMA_anatomy_distance_SimpleITK_BSpline`
- `CineMA_anatomy_distance_SimpleITK_Demons`
- `ANTsPy_SyN` if installed
- optical-flow/feature-warp only as proxy, never as usable registration
- VoxelMorph only if trained/auditable weights exist; otherwise `UNTRAINED_NOT_USABLE`

Each registration row must report myocardium Dice before/after, LV Dice before/after, HD95 before/after when computable, image NCC before/after, Jacobian/fold or displacement smoothness proxy, inverse/round-trip proxy where feasible, runtime seconds, and failure reason.

A row is usable only if it is non-reference and not one-case smoke, not frame0-only, not untrained VoxelMorph, and not optical-flow-only proxy, and it satisfies the helper's stated Dice/HD95/folding/round-trip thresholds. Use these default thresholds unless data force a documented revision:

- myocardium Dice improves by at least 0.02 on average, or is already >= 0.80 and HD95 does not worsen by more than 2 units;
- LV Dice does not worsen by more than 0.05;
- no severe folding/Jacobian warning;
- finite round-trip/inverse proxy within the helper threshold.

Required outputs:

- `cine_registration_repair_report.md`
- updated `registration_same_subset_matrix.csv`
- local runtime artifacts under a non-tracked runtime directory

### D. Temporal dictionary after registration gate

If at least one usable non-reference registration option exists, attempt a minimal diagnostic temporal dictionary build. It must include ED/reference anchor features, selected non-reference frame features, warped features, frame-quality score, motion-saliency score, temporal representer slot usage, temporal aggregation output, local class_1 myocardium proxy, class_3 sanity, and hosted metric caveat.

If no usable registration row exists after the repair attempt, write `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_REPAIR_ATTEMPT`. This is acceptable only if the registration helper actually ran and recorded failures.

### E. Aggregation and completion state

Update `scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py` so completion is fail-closed. It must explicitly check:

- no required loss component has failed/missing gradient evidence;
- hard subgroup coverage report exists and is not all missing;
- formal-val and diagnostic hardcase rows are separated;
- Cine registration repair was attempted if Cine subline is enabled;
- temporal dictionary is ready only if registration gate passes.

Update these files in `results/20260705_srr_v3_m7_training_and_cine_utilization/`:

- `result.md`
- `m7_execution_plan.md`
- `loss_component_gradient_sanity.csv`
- `loss_component_gradient_fix_report.md`
- `m7_hard_subgroup_case_manifest.csv`
- `hard_subgroup_coverage_report.md`
- `same_split_help_harm.csv`
- `hard_subgroup_metrics.csv`
- `best_variant_decision.md`
- `best_variant_decision_table.csv`
- `cine_registration_repair_report.md`
- `registration_same_subset_matrix.csv`
- `temporal_dictionary_evidence.csv`
- `cine_metrics_summary.csv` if Cine metrics are computed
- `failure_interpretation.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`
- `commands_run.md`

`completion_check.md` may contain only:

- `M7_CONTINUED_READY_FOR_REVIEW`
- `M7_NEEDS_REVISION`
- `M7_NEEDS_EVIDENCE`
- `M7_NEEDS_MONITOR`
- `M7_BLOCKED_BY_M6`
- `M7_CONTINUED_BLOCKED_BY_REVIEW_STATE`

Do not write `M7_CONTINUED_READY_FOR_REVIEW` if any blocker above remains unresolved.

Finish by force-adding and locally committing only the lightweight M7 continued packet plus necessary first-party helper/source/test files. Do not write `review.md` and do not start M8.
```

## 2. Reviewer prompt: M7 continued blocker repair audit

```text
这是独立只读 reviewer/auditor session。只审阅 `results/20260705_srr_v3_m7_training_and_cine_utilization/` 的 M7 continued packet 和必要 first-party helper/source/test files。不要补 executor 缺失文件，不要改代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动 M8。最后只写该目录下的 `review.md`。

必须读取：

- `prompts/shared/20260706_M7_continued_blocker_repair_contract.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- prior M7 `review.md`
- M7 continued result directory
- modified first-party training/evaluation/Cine/loss/model/test files

### A. Loss gradient gate

Reject if any required loss component still has `BACKWARD_FAILED`, `EVIDENCE_NOT_FOUND`, unjustified `ZERO_GRAD_OR_DETACHED`, missing `requires_grad`, or `param_with_grad_count=0` without a documented legitimate mask gate.

Allow `LEGITIMATE_MASKED_NA` only when batch cases, T2-present fraction, target voxel count, and zero justification are present. At least one T2-present gradient sanity batch is required if T2-present cases are available.

### B. Hard subgroup gate

Review `m7_hard_subgroup_case_manifest.csv`, `hard_subgroup_coverage_report.md`, `same_split_help_harm.csv`, and `hard_subgroup_metrics.csv`.

Reject if evidence remains all CenterA/LGE-only/no-T2, if diagnostic rows are mixed into formal best-variant decision, or if missing groups have no exact reason. Required groups are T2-present/complete, CenterB or CenterC, no-T2 empty-GT, GT-positive scar, GT-positive edema when available, remote-FP-positive, small-lesion, and large-lesion.

### C. Metric decision gate

`best_variant_decision.md` must use only formal-val rows for formal decisions. Diagnostic hardcase rows may support mechanism interpretation but not route promotion. Reject if no-T2 unsafe variants are not rejected, scar regression is ignored, HD95/component/remote-FP are omitted, or case-ID/GT-tuned fallback is used.

### D. Cine repair gate

Review `cine_registration_repair_report.md`, `registration_same_subset_matrix.csv`, `temporal_dictionary_evidence.csv`, and `cine_metrics_summary.csv` if present.

Reject if M7 continued merely copied M5 evidence again. The packet must show a real same-safe-subset non-reference registration attempt. One-case SyN, frame0-only, untrained VoxelMorph, and optical-flow proxy cannot be marked usable. Every registration row must include before/after anatomy metrics, quality/folding/round-trip proxies, runtime, and failure reason.

If a usable registration row exists, temporal dictionary evidence must be attempted. If no usable row exists, `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_REPAIR_ATTEMPT` is acceptable only if the registration repair attempt is well documented.

### E. Reviewer decision

Allowed decisions:

- `M7_CONTINUED_AUDITED_GO_FOR_NEXT_PLANNING`
- `M7_CONTINUED_AUDITED_NEEDS_REVISION`
- `M7_CONTINUED_AUDITED_NEEDS_EVIDENCE`
- `M7_CONTINUED_AUDITED_UNDERTRAINED`
- `M7_CONTINUED_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

`M7_CONTINUED_AUDITED_GO_FOR_NEXT_PLANNING` only means the repaired evidence is adequate for GPT planner review. It does not authorize validation packaging/upload, hosted metric claim, fold expansion, challenge submission, M8, route promotion, or scientific stop.
```

## 3. Merge notes

When merging into shared prompts, place the executor block after the current M7 executor section and the reviewer block after the current M7 reviewer section. Keep the original M7 section because it documents the first M7 run. Do not weaken the Cine gate into a copied-gap report; M7 continued must attempt registration repair before preserving a gap.
