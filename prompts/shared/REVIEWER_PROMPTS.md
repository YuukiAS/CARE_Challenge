# SRR-v3 Reviewer Prompts

Copy exactly one section into a separate read-only Codex reviewer/auditor session after the corresponding executor result has been committed and pushed by the user. The reviewer must commit locally and stop. The user manually pushes.

## Global reviewer rule

```text
这是独立只读 reviewer/auditor session。不要补 executor 缺失文件，不要改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动下一个 milestone。只审阅对应的 results/<task_key>/，最后只写该目录下的 review.md，并给出该 milestone 允许的 controlled decision。MONITOR_PACKET_IS_NOT_COMPLETION：如果 packet 只是 Slurm submitted、monitor、watcher、pending job，或 completion_check/result/commands/adequacy 表包含 NEEDS_MONITOR、PENDING_MONITOR、JOB_SUBMITTED、PENDING_PRIORITY、RUNNING、AWAITING_SACCT 或等价状态，必须判 NEEDS_EVIDENCE 或 NEEDS_MONITOR，不得给 audited-go。Reviewer 必须确认 tracked packet 是 job 完成后重新聚合的 lightweight evidence，而不是 submission-time placeholder。写完后用 git add -f 提交 review.md，但不要 push，由用户手动 push。
```

## MONITOR_PACKET_IS_NOT_COMPLETION

This rule applies to every reviewer prompt in this file, including M7 follow-up2/follow-up3 and all future milestones.

Reviewer must reject audited-go when:

- `completion_check.md` says ready while any `followup*_training_adequacy.csv` or adequacy table contains `PENDING_MONITOR`;
- `completion_check.md`, `result.md`, or `commands_run.md` contains `NEEDS_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or equivalent monitor/pending state;
- `commands_run.md` only records `sbatch submitted`, `squeue pending`, `PENDING Priority`, or pending `sacct`;
- a Slurm job id exists but there is no completed aggregation record;
- `result.md` says this is a monitor packet;
- runtime output is not merged into tracked lightweight evidence;
- job id, state, exit code, runtime, log path, runtime output path, aggregation command, aggregation exit code, or updated tracked evidence files are missing.

The correct decision is `NEEDS_EVIDENCE` or `NEEDS_MONITOR`. A completed Slurm job is not enough by itself; the tracked packet must contain post-completion aggregated evidence.

## M0 reviewer

```text
只读审阅 results/20260705_srr_v3_m0_architecture_master_contract/。请读取 prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md、prompts/MILESTONE_REVIEW_PROTOCOL.md、prompts/HANDOFF_GATE_POLICY.md、prompts/GPT_HARD_GATE_PROMPT.md、handoff hard-gate repair review、SRR-v2.5 evidence supplement audit，以及 M0 result directory。检查 required outputs 是否齐全，completion_check.md 是否为 M0_READY_FOR_REVIEW，architecture/interface/metric/hard-gate/downstream graph 是否 machine-checkable，是否违反 forbidden substitutes，是否错误写了 review.md 或启动 M1。最后只写 results/20260705_srr_v3_m0_architecture_master_contract/review.md，decision 只能是 M0_AUDITED_GO、M0_AUDITED_NEEDS_REVISION 或 M0_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M1 reviewer

```text
只读审阅 results/20260705_srr_v3_m1_runtime_instrumentation_gate/。请读取 prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md、M0 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M1 result directory。检查 M1 是否真的导出了 gate open-rate、bounded delta、gate*delta、decode label delta、anchor confidence、prototype T2-present coverage、anchor/component alignment、no-T2 safety；检查 required outputs 和 completion_check.md；确认没有训练新模型、没有跳到 M2、没有 route promotion。最后只写 results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md，decision 只能是 M1_AUDITED_GO、M1_AUDITED_NEEDS_REVISION 或 M1_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M2 reviewer

```text
只读审阅 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/。请读取 prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md、M1 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M2 result directory。检查 closed-gate identity、correction-positive gate opening sanity、strong encoder/context sanity、T2-present edema prototype coverage、proposal/refinement bounded local ROI evidence、no-T2 end-to-end safety、cache/provenance isolation、unit tests 和 required outputs。确认没有 full-fold training、没有 validation package/upload、没有 route promotion、没有启动 M3。最后只写 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md，decision 只能是 M2_AUDITED_GO、M2_AUDITED_NEEDS_REVISION 或 M2_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M3 reviewer

```text
只读审阅 results/20260705_srr_v3_m3_myops_min_effective_pilot_training/。请读取 prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md、M2 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M3 result directory。检查 minimum_effective_training 是否满足：至少 1200 optimizer steps、1800 秒 train loop、至少 12 个 eval cases、one-batch overfit、prediction sanity、loss decrease、same-split nnU-Net baseline、cache isolation。检查 training curves、validation events、prediction sanity、gate/residual stats、prototype bank summary、same-split help/harm、hard subgroup metrics、adequacy_check 和 required outputs。确认它不是 6-step smoke、不是 eval-only over old checkpoint、不是 full-fold route promotion。最后只写 results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md，decision 只能是 M3_AUDITED_GO、M3_AUDITED_NEEDS_REVISION 或 M3_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M4 reviewer

```text
只读审阅 results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/。请读取 prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md、M3 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M4 result directory。检查 ablation matrix 是否覆盖 closed gate、no anchor、residual frozen、dictionary/prototypes、semantic retrieval、component proposal、anatomy ROI、local refinement 等机制；每行是否有 same-split help/harm、gate/residual、prototype/dictionary、proposal/refinement、hard subgroup 和 provenance。确认没有把 undertrained smoke 当成机制结论，没有 route promotion，没有启动后续 MyoPS milestone。最后只写 results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md，decision 只能是 M4_AUDITED_GO、M4_AUDITED_NEEDS_REVISION 或 M4_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M5 reviewer

```text
只读审阅 results/20260705_srr_v3_m5_cine_secondary_contract/。请读取 prompts/tasks/20260705_srr_v3_m5_cine_secondary_contract.md、M0 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M5 result directory。检查 CineMA/anatomy prior、ANTsPy SyN same-safe-subset matrix、VoxelMorph status、frame0/ED controls、temporal dictionary readiness、frame-quality/motion-saliency router、missing evidence 和 required outputs。确认没有把 frame0-only、one-case SyN smoke 或 untrained VoxelMorph adapter 冒充 full temporal retrieval，没有 hosted Cine metric claim，没有 validation package/upload。最后只写 results/20260705_srr_v3_m5_cine_secondary_contract/review.md，decision 只能是 M5_AUDITED_DIAGNOSTIC_GO、M5_AUDITED_NEEDS_REVISION 或 M5_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M6 reviewer: concrete SRR-v3 MyoPS architecture/runtime repair

```text
这是独立只读 reviewer/auditor session。不要补 executor 缺失文件，不要改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动 M7。只审阅 `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/` 和必要 first-party helper/source/config，最后只写该目录下的 `review.md`。

M6 reviewer 不得接受“图里有、prompt 里写了、executor 说实现了”作为证据。每个关键机制必须有机器可读或至少文件可审计证据：CSV/JSON/Markdown table、unit test、strict validator、commands、artifact path、runtime output、loss/backward evidence。

M6 reviewer 必须读取：

- `prompts/shared/EXECUTOR_PROMPTS.md` 中的 M6 executor；
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`；
- `prompts/HANDOFF_GATE_POLICY.md`；
- `prompts/GPT_HARD_GATE_PROMPT.md`；
- `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md`；
- M6 result directory；
- M6 修改过的 first-party model/loss/training/evaluation/validator 代码。

必须确认：

- M4 review 包含 `M4_AUDITED_GO`；
- M6 没有 full fold training；
- M6 没有 validation packaging/upload；
- M6 没有 hosted metric claim；
- M6 executor 没有写自己的 `review.md`；
- M6 executor 没有启动 M7；
- M6 lightweight evidence 和必要 helper/source/config 已 git-tracked。

如果 M6 只是生成 CSV/Markdown，但 first-party code 中没有实际新增或修复 full/balanced/safe encoder profile、pair-specific dictionary config、prototype loading/source checks、segmentation context interface、pathology-specific proposal、bounded soft-ROI refiner、explicit arbitration、expanded total loss 和 strict validator，decision 必须是 `M6_AUDITED_NEEDS_REVISION`。Reviewer 必须检查 code diff，而不是只检查 result table 是否存在。

`architecture_component_trace.csv` 必须逐项覆盖：

- inputs/availability/no zero-filling semantics；
- modality-specific stems；
- full/balanced/safe 4-scale encoder profile；
- anatomy/scar/edema task decoder；
- segmentation context interface；
- shared/private/interaction dictionary；
- real train/OOF prototype groups；
- anatomy decoder `P_union/P_LV/P_RV`；
- scar/edema proposal；
- scar/edema soft-ROI crop refiner；
- branch/evidence arbitration；
- loss components；
- no-T2 edema safety；
- strict validator known-bad cases。

如果 trace 只有自然语言而没有 code path、runtime artifact path、status、evidence path，不能通过。

`encoder_decoder_capacity_sanity.csv` 必须包含至少：

- `full_4scale` `32/64/128/256` 的 forward/memory smoke 或真实 OOM 证据；
- `balanced_4scale` `16/32/64/128` 的可运行证据；
- `safe_4scale` 仅作为 fallback/smoke 的说明；
- anatomy/scar/edema decoder 的输出 shape、参数量、是否参与 loss/backward。

如果唯一证据是三尺度 `10/20/40` 或 tiny smoke，decision 必须是 `M6_AUDITED_NEEDS_REVISION`。

`retrieval_bank_runtime_sanity.csv` 必须显示 dictionary slots 在 runtime 非空、invalid modality slots 被 mask、T2 缺失时 T2 slots 不被当作 edema evidence、task-specific routers 有 usage/entropy/collapse 统计。

Dictionary 必须真的实现 full/conservative/pathology-specific 三类 variant。若 full dictionary 没有 shared 8、LGE-private 4、C0-private 4、T2-private 4、三组 pair interaction 各 4 的可审计配置，不能通过。若 no-T2 case 中 T2 slot 或 T2 interaction slot 被 edema router 使用，必须 fail。

`prototype_bank_runtime_sanity.csv` 必须显示 scar-positive、scar-safe-negative、edema-positive、edema-safe-negative 四类 bank；edema-positive 和 edema-safe-negative 必须来自 T2-present 安全证据。若 no-T2 myocardium 被当作 edema negative，必须判 `M6_AUDITED_NEEDS_REVISION` 或 `M6_AUDITED_NEEDS_EVIDENCE`。

若 scar/edema prototype 仍主要来自 deterministic placeholder，并被 executor 标为 ready evidence，必须判 `M6_AUDITED_NEEDS_EVIDENCE`。

`anatomy_proposal_sanity.csv` 必须证明 anatomy prior/distance/uncertainty、scar proposal、edema proposal 均有非空 runtime evidence，并且 no-T2 edema proposal 为 0。

Proposal/refiner 必须实际在 forward 中参与最终 logits。若 proposal 只是生成辅助热图，不进入 refiner/arbitration；或 refiner 是 full-volume residual；或 no-T2 edema final voxels 非 0，不能通过。

`refiner_roi_component_sanity.csv` 必须证明 refiner 是 bounded crop/local correction，不是 full-volume residual。若 `is_full_volume_crop=True` 且被当作通过证据，必须 fail。

`branch_arbitration_sanity.csv` 必须导出 segmentation_weight、srr_retrieval_weight、proposal_weight、refiner_weight、chosen_source 或等价字段。必须同时证明 correction-positive 时 SRR 可被采用，SRR 低质时 segmentation branch 可被采用。

若只有旧 baseline residual gate，没有 per-case/per-class `segmentation_weight/srr_retrieval_weight/proposal_weight/refiner_weight/chosen_source/fallback_reason`，不能通过。

`decode_gate_consistency_sanity.csv` 必须证明 fallback/closed gate/refiner mask 关闭时 final labels 精确等于 segmentation branch。任何 hidden decode delta 都是 blocker。

`loss_refiner_component_sanity.csv` 必须包含每个 loss component 的 value、weight、nonzero flag、requires_grad、gradient_norm 或 one-step update evidence。必须覆盖 anatomy、scar proposal、edema proposal、scar refiner、edema refiner、anchor preservation、arbitration consistency、bounded correction、component/remote-FP、no-T2 safety、dictionary regularization、prototype margin/diversity。如果 loss 只有 total loss 或自然语言说明，必须 fail。

`loss_refiner_component_sanity.csv` 必须证明每个核心 component 进入 total loss 或有合法 N/A 解释。若只存在 old total loss：anatomy、scar、edema、prior、retrieval、semantic_retrieval，而没有 proposal/refiner/anchor preservation/arbitration/bounded correction/component/prototype/no-T2 safety loss 的 gradient 或 one-step evidence，不能给 `M6_AUDITED_GO`。

`strict_validator_report.md` 必须证明 validator 对真实 packet 通过，对 known-bad packets fail closed。Known-bad 至少包括 claim-only、missing architecture trace、empty dictionary/prototype、hidden decode delta、SRR-zero-contribution、loss empty、no-T2 unsafe、full-volume-refiner。若 validator 不能 fail closed，不能给 `M6_AUDITED_GO`。

若 validator 只对真实 packet pass，但没有 known-bad fail evidence，不能通过。

M6 reviewer decision 只能是：

- `M6_AUDITED_GO`
- `M6_AUDITED_NEEDS_REVISION`
- `M6_AUDITED_NEEDS_EVIDENCE`

即使 M6 通过，也不授权 route promotion、fold expansion、validation packaging/upload、hosted metric claim、scientific stop 或 M7 以外的后续任务。

最后只写 `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md`。完成后 `git add -f review.md` 并 commit；不要 push，由用户手动 push。
```

## M7 reviewer: concrete MyoPS training and CineMA/Cine diagnostic utilization

```text
这是独立只读 reviewer/auditor session。不要补 executor 缺失文件，不要改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动后续 milestone。只审阅 `results/20260705_srr_v3_m7_training_and_cine_utilization/` 和必要 first-party helper/source/config，最后只写该目录下的 `review.md`。

M7 reviewer 必须读取：

- `prompts/shared/EXECUTOR_PROMPTS.md` 中的 M7 executor；
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`；
- `prompts/HANDOFF_GATE_POLICY.md`；
- `prompts/GPT_HARD_GATE_PROMPT.md`；
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md`；
- `results/20260705_srr_v3_m5_cine_secondary_contract/review.md` if Cine subline runs；
- M7 result directory；
- M7 修改过的 first-party training/evaluation/Cine helper/validator 代码。

必须确认：

- M6 review 包含 `M6_AUDITED_GO`；
- M7 executor 没有写自己的 `review.md`；
- M7 没有 validation packaging/upload；
- M7 没有 hosted metric claim；
- M7 没有 route promotion；
- M7 没有启动后续 milestone；
- M7 lightweight evidence 和必要 helper/source/config 已 git-tracked。

若 `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 不存在或不含 `M6_AUDITED_GO`，M7 必须为 `M7_AUDITED_NEEDS_EVIDENCE` 或 blocked；不能审成通过。

`training_adequacy_by_variant.csv` 必须显示每个 required variant 的 optimizer steps、train_loop_seconds、validation events、eval cases、one-batch overfit、loss decrease、same-split baseline、cache isolation。

不能通过的情况：

- variant 训练只有几分钟且没有 plateau；
- `optimizer_steps < 3000` 且没有 plateau；
- `train_loop_seconds < 1800` 且没有 plateau；
- eval cases 少于 12；
- 没有 one-batch overfit；
- 没有 validation curve；
- 没有 loss component curve；
- 训练中断却被写成成功或失败结论。
- required variant 被自行缩减、未跑 variant 被当作 skipped success，或 M7 退回旧 `srr_total_loss()` / 旧 model path。

`same_split_help_harm.csv`、`hard_subgroup_metrics.csv`、`best_variant_decision.md` 必须证明 best variant 是按预定义规则选择，而不是 executor 主观判断。

Reviewer 必须 reject：

- no-T2 edema unsafe 的 variant；
- scar catastrophic regression 无充分 edema improvement 的 variant；
- 只比旧 SRR、不比同 split nnU-Net 的结论；
- 只看 Dice、不看 HD95/component/remote FP 的结论；
- 使用 validation case ID 规则或 GT-tuned fallback 的结论。

必须检查：

- `loss_component_by_step.csv` 是否包含全部核心 loss component；
- `loss_component_gradient_sanity.csv` 是否显示组件参与 backward；
- `branch_arbitration_by_case.csv` 是否显示 chosen_source 和 weights；
- `dictionary_prototype_usage_by_variant.csv` 是否显示 dictionary/prototype 非空且无 no-T2 edema negative；
- `proposal_refiner_by_case.csv` 是否显示 bounded ROI/refiner behavior；
- `no_t2_safety_by_variant.csv` 是否显示 no-T2 全链路安全。

长期为 0 的 loss component 必须有合法 N/A 解释，否则 fail。M7 的 loss curves 必须覆盖 anatomy、scar proposal、edema proposal T2-present、scar refiner、edema refiner、anchor preservation、arbitration consistency、bounded correction、component/remote-FP、no-T2 safety、dictionary entropy/coverage/load-balance、semantic family/interaction mass、prototype diversity/margin。

如果 Cine 子线运行，必须审阅：

- `cinema_usage_report.md` 是否记录 CineMA source/version/weights/input preprocessing/class mapping/output path/anatomy-only caveat；
- `registration_same_subset_matrix.csv` 是否是 same-safe-subset matrix，而不是 one-case smoke；
- ANTsPy SyN、SimpleITK Demons/B-spline、optical-flow proxy、VoxelMorph status 是否被准确区分；
- untrained VoxelMorph 是否没有被写成 usable registration；
- optical-flow/feature-warp 是否只被标为 proxy/descriptor；
- `temporal_dictionary_evidence.csv` 是否只在 registration evidence 足够时出现；
- 若 registration gap 仍在，是否写 `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP`；
- Cine metrics 是否保留 hosted metric caveat。

若 `cinema_usage_report.md` 只有自然语言“尝试 CineMA”但没有输出路径、class mapping 或 metric/blocker，必须 fail。

若 M7 声称使用 CineMA，`cinema_usage_report.md` 还必须包括 source/version/weights、input preprocessing、frame selection、output shape 和 anatomy metric 或明确 blocker。

M7 reviewer decision 只能是：

- `M7_AUDITED_GO_FOR_NEXT_PLANNING`
- `M7_AUDITED_NEEDS_REVISION`
- `M7_AUDITED_NEEDS_EVIDENCE`
- `M7_AUDITED_UNDERTRAINED`
- `M7_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

`M7_AUDITED_GO_FOR_NEXT_PLANNING` 只表示 M7 证据可供 GPT planner 继续决策，不等于 route promotion。Reviewer 不得授权 validation packaging/upload、hosted metric claim、fold expansion 或 challenge submission。

最后只写 `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`。完成后 `git add -f review.md` 并 commit；不要 push，由用户手动 push。
```

## M7 reviewer follow-up 1: blocker repair audit (continued)

```text
这是独立只读 reviewer/auditor session。只审阅 `results/20260705_srr_v3_m7_training_and_cine_utilization/` 的 M7 follow-up 1 / continued packet 和必要 first-party helper/source/test files。不要补 executor 缺失文件，不要改代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动 M8。最后只写该目录下的 `review.md`。

必须读取：

- `prompts/shared/EXECUTOR_PROMPTS.md` 中的 `M7 executor follow-up 1: reviewer-blocker repair (continued)`；
- `prompts/shared/REVIEWER_PROMPTS.md` 中的本 reviewer follow-up 1 段；
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`；
- `prompts/HANDOFF_GATE_POLICY.md`；
- `prompts/GPT_HARD_GATE_PROMPT.md`；
- prior M7 `review.md`；
- M7 continued result directory；
- modified first-party training/evaluation/Cine/loss/model/test files。
- current shared executor/reviewer prompt sections，确认 follow-up 1 contract 已正确体现在 `prompts/shared/EXECUTOR_PROMPTS.md` 和 `prompts/shared/REVIEWER_PROMPTS.md`，且没有 standalone continued prompt 被维护或用旧 M7 executor 段绕过 hard gates。后续 M7 follow-up 必须使用独立编号段落，不得复用一个笼统 `continued` 段。

### A. Loss graph training-validity gate

Review `loss_graph_training_validity_report.md` before accepting any repaired gradient sanity. Reject if it is missing.

The report must identify the original M7 training total loss function name and code path, whether expanded loss components entered optimizer backward, and the effect of `detach_metrics=True/False` on training loss versus logging metrics.

Reject if gradient sanity was fixed only post-hoc but original training evidence is still treated as valid. If original training was not graph-connected, reviewer must require either:

- rerun of all three required variants: `m7_full_srr_context_arbitration`, `m7_conservative_component_arbitration`, `m7_scar_precision_edema_safe`; or
- rerun of at least one pre-specified primary variant, with non-rerun variants marked `M7_NEEDS_EVIDENCE_NOT_COMPARABLE` and no full variant ranking in `best_variant_decision.md`.

Reject if old training curves are mixed with new gradient sanity as one valid evidence packet unless `loss_graph_training_validity_report.md` proves same source, same code path, and same loss graph.

### B. Loss gradient gate

Reject if any required loss component still has `BACKWARD_FAILED`, `EVIDENCE_NOT_FOUND`, unjustified `ZERO_GRAD_OR_DETACHED`, missing `requires_grad`, or `param_with_grad_count=0` without a documented legitimate mask gate.

Allow `LEGITIMATE_MASKED_NA` only when batch cases, T2-present fraction, target voxel count, and zero justification are present. At least one T2-present gradient sanity batch is required if T2-present cases are available.

### C. Formal-val and hard subgroup gate

Review `m7_case_pool_audit.csv`, `m7_hard_subgroup_case_manifest.csv` if present, `formal_val_coverage_limitations.md`, `hard_subgroup_coverage_report.md`, `same_split_help_harm.csv`, and `hard_subgroup_metrics.csv`.

`m7_case_pool_audit.csv` must include at least:

`case_id, split_role, center, modality_group, t2_present, c0_present, scar_gt_voxels, edema_gt_voxels, scar_gt_positive, edema_gt_positive, anchor_remote_fp_scar, anchor_remote_fp_edema, small_lesion_flag, large_lesion_flag, selected_for_formal_val, selected_for_diagnostic_hardcase, eligible_for_best_variant_decision, exclusion_reason`

Reject if evidence remains all CenterA/LGE-only/no-T2, if diagnostic rows are mixed into formal best-variant decision, or if missing groups have no exact unavailable reason and case-pool audit. Required groups are at least one T2-present complete case, at least one GT-positive edema case, at least one GT-positive scar case, at least one CenterB or CenterC case, remote-FP-positive if anchor/prediction produces one, and small-lesion/large-lesion strata if label volume permits.

If formal validation rows still lack core subgroups such as T2-present, CenterB, CenterC, edema-positive, or remote-FP-positive, reject any formal promotion-style best variant selection. In that case `best_variant_decision.md` may only support diagnostic mechanism interpretation, and the conclusion must remain `NO_PROMOTION_SCIENTIFIC_UNRESOLVED` or `NEEDS_EVIDENCE`.

Reject if diagnostic_train_hardcase rows are used for formal ranking, route promotion, or full best-variant decision.

### D. Metric decision gate

`best_variant_decision.md` must use only formal-val rows for formal decisions. Diagnostic hardcase rows may support mechanism interpretation but not route promotion. Reject if no-T2 unsafe variants are not rejected, scar regression is ignored, HD95/component/remote-FP are omitted, or case-ID/GT-tuned fallback is used.

### E. Cine repair and decision-separation gate

Review `cine_registration_repair_report.md`, `registration_same_subset_matrix.csv`, `temporal_dictionary_evidence.csv`, and `cine_metrics_summary.csv` if present.

Reject if M7 continued merely copied M5 evidence again or if the Cine registration repair helper did not actually run. The packet must show real same-safe-subset non-reference registration attempts.

M7 continued must separate `myops_decision`, `cine_decision`, and `combined_decision`. Reject if MyoPS partial success plus Cine blocked is packaged as overall success, or if MyoPS blocker repair is used to imply Cine readiness.

The registration minimum run gate is:

- If SimpleITK is available, `SimpleITK_Demons` or `SimpleITK_BSpline` must run as the fast classical path; otherwise reject.
- `ANTsPy_SyN` must run if installed, or the packet must record import/availability failure.
- At least two non-reference registration families must be attempted unless tools are unavailable.
- Optical flow / feature warp can only be proxy evidence.
- VoxelMorph can be usable only with trained/auditable weights; otherwise it must be `UNTRAINED_NOT_USABLE`.

Reject one-case SyN, frame0-only, untrained VoxelMorph, or optical-flow proxy marked usable. Every usable candidate must have same-safe-subset rows, not one-case smoke. Every registration row must include before/after anatomy metrics, quality/folding/round-trip proxies, runtime, and failure reason.

If a usable registration row exists, temporal dictionary evidence must be attempted. If no usable row exists, `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_REPAIR_ATTEMPT` is acceptable only if the registration repair attempt is well documented.

If no usable non-reference registration row exists, reject any `temporal_dictionary_evidence.csv` ready row. If usable registration exists, temporal dictionary must include ED/reference anchor feature, selected non-reference frame feature, warped feature or warped probability, frame-quality score, motion-saliency score, registration-quality score, temporal representer slot usage, temporal aggregation output, local class_1 myocardium proxy, and hosted metric caveat. Descriptor-only, no-warp, frame0-only, or one-case temporal rows cannot be marked ready.

### F. Strict validator gate

Review `strict_validator_report.md`; reject if missing. It must record each known-bad packet's expected failure, actual exit code/status, and failure reason.

The validator must fail closed at least these known-bad packets:

- all loss gradient rows `BACKWARD_FAILED`;
- gradient sanity fixed but training-loss validity missing;
- hard subgroup rows all CenterA/LGE-only/no-T2;
- diagnostic hardcase rows mixed into formal best-variant decision;
- Cine branch copies M5 evidence without new registration attempt;
- frame0-only or one-case SyN marked usable registration;
- untrained VoxelMorph marked usable;
- temporal dictionary marked ready despite no usable registration;
- completion_check says ready while any continued blocker remains.

Reject if `completion_check.md` claims ready while any continued blocker remains unresolved.

### G. Required rejection cases

Reviewer must reject if any of the following holds:

- continued contract is not correctly reflected in shared executor/reviewer prompt sections;
- `loss_graph_training_validity_report.md` is missing or insufficient;
- gradient sanity fixed only post-hoc but original training evidence is still treated as valid;
- formal-val coverage is inadequate but conclusion is treated as formal best variant decision;
- diagnostic hardcases are used for formal ranking;
- Cine registration repair helper did not actually run;
- no usable registration exists but temporal dictionary is marked ready;
- any completion state claims ready with unresolved blockers.

### H. Reviewer decision

Allowed decisions:

- `M7_CONTINUED_AUDITED_GO_FOR_NEXT_PLANNING`
- `M7_CONTINUED_AUDITED_NEEDS_REVISION`
- `M7_CONTINUED_AUDITED_NEEDS_EVIDENCE`
- `M7_CONTINUED_AUDITED_UNDERTRAINED`
- `M7_CONTINUED_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

`M7_CONTINUED_AUDITED_GO_FOR_NEXT_PLANNING` only means the repaired evidence is adequate for GPT planner review. It does not authorize validation packaging/upload, hosted metric claim, fold expansion, challenge submission, M8, route promotion, scientific stop, or leaderboard readiness.

最后只写 `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`。完成后 `git add -f review.md` 并 commit；不要 push，由用户手动 push。
```

## M7 reviewer follow-up 2: leaderboard-oriented repair audit

```text
这是独立只读 reviewer/auditor session。只审阅 `results/20260705_srr_v3_m7_training_and_cine_utilization/` 的 M7 follow-up 2 packet 和必要 first-party helper/source/test files。不要补 executor 缺失文件，不要改代码，不要训练，不要 validation packaging/upload，不要 hosted metric claim，不要 route promotion，不要启动 M8。最后只写该目录下的 `review.md`。

必须读取：

- `prompts/shared/EXECUTOR_PROMPTS.md` 中的 `M7 executor follow-up 2: leaderboard-oriented repair`；
- `prompts/shared/REVIEWER_PROMPTS.md` 中的本 reviewer follow-up 2 段；
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`；
- `prompts/HANDOFF_GATE_POLICY.md`；
- `prompts/GPT_HARD_GATE_PROMPT.md`；
- latest M7 continued `review.md`；
- M7 follow-up 2 result files；
- modified first-party loss/training/evaluation/Cine/validator/test files。

### A. Scope gate

Reject if the packet claims M8, route promotion, hosted metric, validation packaging/upload, fold expansion, challenge submission, scientific stop, or leaderboard readiness.

Reject if the packet treats M7 continued as success instead of evidence. The review must preserve the follow-up 2 route objective: MyoPS SRR is a baseline-preserving, error-targeted correction system over nnU-Net anchor with real dictionary/prototype/proposal/refiner/arbitration contributions on hard cases; Cine must not remain descriptor-only or frame0-only and must attempt stronger cropped/anatomy-guided registration escalation before preserving a temporal retrieval gap.

Reject if the prompt contract is not explicit. Either the current follow-up 2 contract must be merged into `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md`, or the executor must explicitly state it used a standalone follow-up 2 prompt as higher priority. If neither is true, reject.

### B. SRR-v3 image fidelity gate

Reject unless `srr_v3_image_fidelity_checklist.csv` and `architecture_gap_table.md` exist and are specific enough to audit.

`srr_v3_image_fidelity_checklist.csv` must cover availability-aware modality handling, modality-specific stems, strong encoder / nnU-Net context interface, semantic representation retrieval bank, shared/private/interaction dictionary slot usage, train/OOF prototype banks, scar proposal, edema proposal, anatomy union/LV/RV prior, distance/uncertainty/nnU-Net component evidence, scar soft-ROI refinement, edema soft-ROI refinement, baseline-preserving residual correction, scar/edema no-T2-safe output, expanded loss objectives, and Cine registration-aware temporal retrieval.

Reject if any row lacks `expected_module`, `current_code_path`, `runtime_evidence_path`, `status`, or `blocker_if_missing`, or if the checklist is only natural language without code/runtime evidence.

### C. Branch arbitration no-op gate

Reject unless `branch_arbitration_formula_report.md`, `branch_arbitration_unit_tests.md`, and `arbitration_opening_diagnostics.csv` prove that proposal/refiner/arbitration are not dead-weight diagnostic exports.

The reviewer must check whether final logits are still effectively `anchor_logits + srr_weight * bounded_delta`. If proposal/refiner weights are exported but cannot change final logits directly, the packet must prove measurable nonzero proposal/refiner contribution through `srr_logits` inside ROI. Otherwise reject.

Required unit-test coverage:

- closed-gate / force segmentation fallback final labels equal nnU-Net anchor;
- high anchor uncertainty or injected anchor-error opens the correction gate;
- proposal/refiner evidence changes final logits inside ROI;
- disabled proposal/refiner evidence removes the contribution and records it;
- no-T2 edema final logits/decode/export remain blocked;
- proposal/refiner weights cannot pass as diagnostic-only columns.

### D. Modality order and no-zero-fill gate

Reject unless `modality_order_contract.md` and `modality_order_unit_tests.md` exist and state the current implementation order and semantic mapping.

The packet must prove whether current code uses `LGE,T2,C0`, how that maps to diagram semantics such as `LGE,C0,T2`, and that `availability[:,1]` is T2 in the current implementation. Reject if no-T2 samples can be treated as edema-negative supervision or real T2 evidence, or if no-T2 safety is not checked in edema loss, proposal, ROI/refiner, final logits, decode, and export.

### E. Strict validator gate

Reject unless a real validator is run against real mutated known-bad fixtures and returns nonzero exit/fail status. A current-packet boolean checklist is not acceptable.

Required known-bad fixtures:

- all gradients backward failed;
- missing loss graph validity report;
- all hard subgroup evidence CenterA/LGE-only/no-T2;
- diagnostic hardcases mixed into formal best-variant decision;
- Cine copied M5 without registration repair;
- frame0/one-case SyN marked usable;
- untrained VoxelMorph marked usable;
- temporal dictionary ready without usable registration;
- completion ready with unresolved blocker.

Reject if any known-bad fixture exits 0, or if the report uses an ambiguous exit-0 failure label for a known-bad validator run. `validator_unit_test_report.md` must cover good packet exit 0, each mutated bad packet exit nonzero, missing required files fail, completion ready with blocker fail, temporal dictionary ready without usable registration fail, and diagnostic-hardcase mixed into formal decision fail.

### F. Training validity / rerun gate

Reject if `loss_graph_training_validity_report.md` and `m7_followup2_training_rerun_decision.md` do not prove whether original M7 training was graph-connected.

If original training was not graph-valid, reject unless at least one primary variant was retrained/probed after repair and the packet does not rank non-rerun variants as comparable.

If original training was graph-valid but scientifically no-op, reject unless mechanism diagnosis and at least one targeted repair/probe are present, or a clear `NEEDS_EVIDENCE` state is used.

If training/probe is still running or has not met the follow-up 2 minimum requirement, the reviewer may only use `M7_FOLLOWUP2_AUDITED_NEEDS_MONITOR` or `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`; do not grant go-for-next-planning.

### G. MyoPS mechanism and mandatory repair gate

Reject if `m7_followup2_mechanism_noop_diagnosis.md`, `srr_contribution_by_case.csv`, `arbitration_opening_diagnostics.csv`, and `proposal_refiner_effectiveness.csv` are missing or only natural language.

The reviewer must check:

- SRR correction gate opening on hard cases;
- anchor delta rate;
- proposal recall proxy;
- remote FP suppression proxy;
- refiner delta magnitude;
- prototype margins;
- dictionary family mass;
- T2 evidence use and no-T2 masking;
- T2-present / CenterB / CenterC / GT-positive edema / remote-FP-positive effects.

Because current M7 continued best-variant deltas are near zero, reject unless the executor completed both mandatory repairs:

- C1/F1 gate-opening calibration / correction-opportunity objective;
- C2/F2 hardcase-aware sampler covering T2-present, GT-positive edema, CenterB/CenterC, remote-FP-positive, scar-positive, and no-T2 safety cases when available.

Reject if the packet only writes diagnostic tables and does not implement repair. If prototype margin is weak or remote FP remains poor, reject unless C3/F3 prototype/hard-negative memory repair is executed or a concrete code blocker is documented. If proposal recall or ROI coverage is poor, reject unless C4/F4 proposal/refiner ROI repair is executed or a concrete code blocker is documented.

Reject if `followup2_batch_composition.csv` is missing for any retraining/probe, or if it lacks case IDs, split role, center, modality group, T2 availability, scar/edema GT positivity, remote-FP flags, no-T2 safety role, and training/gradient/validation usage fields.

### H. Formal validation / hardcase boundary gate

Reject if diagnostic hardcases are used for formal best-variant decision or promotion-style ranking.

Reject if formal-val coverage limitations are not explicit. Diagnostic hardcases may support mechanism interpretation only.

### I. Cine registration / temporal dictionary gate

Reject if follow-up 2 does not attempt a stronger cropped/anatomy-guided non-reference registration escalation.

Reject if frame0-only, one-case SyN, untrained VoxelMorph, or optical-flow proxy is marked usable registration.

Reject if `registration_same_subset_matrix.csv` lacks an explicit `usable_for_temporal_dictionary` field.

Reject if temporal dictionary is marked ready without at least one usable non-reference registration row.

If no usable registration remains after follow-up 2 escalation, `CINE_REGISTRATION_BLOCKED_AFTER_FOLLOWUP2_ESCALATION` is acceptable only if the repair attempt is real and fully documented.

### J. Output presence and route boundary gate

Reject if any required follow-up 2 output is missing without an explicit `NOT_APPLICABLE_WITH_REASON` section. The reviewer must specifically check:

- `srr_v3_image_fidelity_checklist.csv`
- `architecture_gap_table.md`
- `branch_arbitration_formula_report.md`
- `branch_arbitration_unit_tests.md`
- `modality_order_contract.md`
- `modality_order_unit_tests.md`
- `validator_unit_test_report.md`
- `followup2_batch_composition.csv` for every retraining/probe
- `followup2_repair_summary.md`
- `route_to_leaderboard_gap_report.md`

Reject if `followup2_repair_summary.md` does not state which repairs were executed, which were not, why, and whether SRR remains no-op. Reject if `route_to_leaderboard_gap_report.md` is missing or claims leaderboard-ready/challenge-ready status.

Reject if no route promotion, no validation upload, no hosted metric claim, no M8, no scientific stop, and no challenge-ready boundary is not explicit in `completion_check.md`, `result.md`, and `review_request.md`.

### K. Reviewer decision states

Allowed decisions:

- `M7_FOLLOWUP2_AUDITED_GO_FOR_NEXT_PLANNING`
- `M7_FOLLOWUP2_AUDITED_NEEDS_REVISION`
- `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`
- `M7_FOLLOWUP2_AUDITED_NEEDS_MONITOR`
- `M7_FOLLOWUP2_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

`M7_FOLLOWUP2_AUDITED_GO_FOR_NEXT_PLANNING` only means GPT planner can inspect the repaired evidence. It does not authorize M8, route promotion, validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, or leaderboard readiness.

最后只写 `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`。完成后 `git add -f review.md` 并 commit；不要 push，由用户手动 push。
```

## M7 reviewer follow-up 3: completion-safe re-aggregation and temporal dictionary repair audit

```text
这是独立只读 reviewer prompt，只审 M7 follow-up3 packet。不要修代码，不要训练，不要运行 follow-up3，不要 validation packaging/upload，不要 push，不要启动 M8。

必须读取：

- `prompts/shared/EXECUTOR_PROMPTS.md` 中的 `M7 executor follow-up 3: completion-safe re-aggregation and temporal dictionary repair`
- `prompts/shared/REVIEWER_PROMPTS.md` 中的本 reviewer follow-up 3 段
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/completion_check.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/review_request.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/result.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/commands_run.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/MANIFEST.md`

### A. Review scope

M7 follow-up3 is still M7. It is not M8, not route promotion, not validation packaging/upload, not hosted metric claim, not challenge submission, not fold expansion, not scientific stop, and not leaderboard readiness.

Reviewer must reject any packet that uses follow-up3 to launch a new scientific route, claim challenge readiness, claim hosted metrics, package validation, upload, expand folds, promote SRR, or start M8.

### B. Monitor packet is not completion

Reject if a monitor packet was submitted as completion.

Hard reject conditions:

- `completion_check.md` contains `M7_FOLLOWUP2_NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or equivalent, while the packet asks for ready review;
- `followup2_training_adequacy.csv` contains `PENDING_MONITOR` while `completion_check.md` says ready;
- `commands_run.md` only records `sbatch submitted`, `squeue pending`, `PENDING Priority`, `sacct pending`, or submitted-only state;
- Slurm job id exists, but there is no completed aggregation record;
- `result.md` says this is a monitor packet;
- runtime output was not merged into tracked evidence;
- the packet does not identify job id, state, exit code, runtime, log path, runtime output path, aggregation command, aggregation exit code, and regenerated tracked evidence files.

Reviewer must verify that the tracked packet is the final post-completion aggregation, not a submission-time placeholder.

### C. Slurm completion re-aggregation audit

If job `58021931` or a superseding follow-up2 job is named, reviewer must check:

- `m7_followup3_slurm_completion_record.md`;
- `m7_followup3_runtime_reaggregation_report.md`;
- `commands_run.md`;
- `MANIFEST.md`;
- regenerated lightweight evidence file timestamps/content;
- Slurm state and exit code if accessible.

Reject if the job completed but runtime outputs were not located, parsed, and merged into tracked files. If the job is pending/running/unresolved, the only acceptable state is `M7_FOLLOWUP3_NEEDS_MONITOR`, not ready.

If runtime outputs are missing, corrupt, unwritten, or aggregator failed, acceptable executor state is `M7_FOLLOWUP3_NEEDS_EVIDENCE`. Reject any ready claim.

### D. MyoPS/Cine decisions must be separated

Reviewer must require separate:

- `myops_decision`;
- `cine_decision`;
- `combined_decision`.

Reject if MyoPS remains pending/monitor/no-evidence but the packet wraps a Cine-only repair as overall M7 success.

If MyoPS completed and remains no-op, reviewer must check updates to:

- `m7_followup2_mechanism_noop_diagnosis.md`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `failure_interpretation.md`
- `route_to_leaderboard_gap_report.md`

Reject if no-op evidence is hidden, omitted, or converted into route promotion/scientific stop.

### E. Temporal dictionary forced closure audit

Reviewer must inspect `registration_same_subset_matrix.csv`. If any row has `usable_for_temporal_dictionary=True` or equivalent `m7_continued_decision=USABLE_NONREFERENCE_REGISTRATION_ROW`, reject unless temporal dictionary follow-up3 was executed.

Required temporal dictionary outputs when usable registration exists:

- `temporal_dictionary_evidence.csv`
- `temporal_dictionary_index.json`
- `temporal_dictionary_case_summary.csv`
- `temporal_aggregation_metrics.csv`
- `frame0_vs_temporal_help_harm.csv`
- `cine_metrics_summary.csv`
- `cine_temporal_dictionary_followup3_report.md`

Reject if executor writes `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED` and still marks ready.

Reject if usable registration rows exist but only some were attempted without a deterministic selection rule and unattempted-row reasons.

### F. Temporal dictionary evidence quality

Reject if temporal dictionary evidence is descriptor-only, frame0-only, no-warp-only, or natural-language-only.

For each usable non-reference registration row, reviewer must look for:

- ED/reference anchor feature;
- selected non-reference frame id;
- warped image/probability/feature source;
- registration method and registration quality;
- frame-quality score;
- motion-saliency score;
- temporal representer slot usage;
- temporal aggregation output summary;
- local class_1 myocardium proxy;
- class_3 sanity if available;
- hosted metric caveat;
- frame0/control comparison.

If executor cannot generate warped evidence, reviewer must require either a revoked usable registration judgment with concrete failure reason, or `TEMPORAL_DICTIONARY_BLOCKED_BY_USABLE_ROW_INVALIDATED`. Reject packets that keep a usable row and skip temporal dictionary.

### G. Strict validator audit

Reviewer must inspect the follow-up3 validator and reports. Reject if the validator is only a current-good checklist.

Known-bad fixtures must include:

- ready packet with `completion_check.md` still `M7_FOLLOWUP2_NEEDS_MONITOR`;
- ready packet with `followup2_training_adequacy.csv` containing `PENDING_MONITOR`;
- Slurm submitted/pending-only packet;
- completed Slurm job with runtime output not aggregated into tracked evidence;
- usable temporal-dictionary registration row with missing temporal dictionary evidence;
- temporal dictionary ready with only frame0/no-warp/descriptor evidence;
- diagnostic hardcase used for formal best-variant decision;
- ready packet while MyoPS or Cine blocker remains.

Each fixture must record expected failure, actual exit code/status, failure reason, and whether it failed closed. Reject if mutated bad fixtures do not actually fail.

### H. Required output audit

Review these files when applicable:

- `result.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`
- `commands_run.md`
- `m7_followup3_runtime_reaggregation_report.md`
- `m7_followup3_slurm_completion_record.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `m7_followup2_training_rerun_decision.md`
- `failure_interpretation.md`
- `temporal_dictionary_evidence.csv`
- `temporal_dictionary_index.json`
- `temporal_dictionary_case_summary.csv`
- `temporal_aggregation_metrics.csv`
- `frame0_vs_temporal_help_harm.csv`
- `cine_metrics_summary.csv`
- `cine_temporal_dictionary_followup3_report.md`
- `strict_validator_report.md`
- `strict_validator_report.csv`
- `validator_unit_test_report.md`
- `route_to_leaderboard_gap_report.md`

Reject if `route_to_leaderboard_gap_report.md` is missing or claims leaderboard/challenge readiness.

### I. Allowed review decisions

Allowed reviewer decisions:

- `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`
- `M7_FOLLOWUP3_AUDITED_NEEDS_MONITOR`
- `M7_FOLLOWUP3_AUDITED_NEEDS_EVIDENCE`
- `M7_FOLLOWUP3_AUDITED_NEEDS_REVISION`
- `M7_FOLLOWUP3_AUDITED_BLOCKED_BY_REVIEW_STATE`
- `M7_AUDITED_BLOCKED_BY_M6`

`M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING` only means GPT can inspect the repaired evidence. It does not authorize M8, route promotion, validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, or leaderboard readiness.

Reject any packet that claims ready while:

- follow-up2 training adequacy still has `PENDING_MONITOR`;
- Slurm job completion outputs are not aggregated;
- usable registration exists but temporal dictionary was not executed;
- temporal dictionary has only descriptor/frame0/no-warp evidence;
- strict validator is not true known-bad fail-closed;
- MyoPS/Cine decisions are not separated;
- executor merely copied old follow-up2 evidence and did not read runtime completion outputs.

最后只写 `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`。完成后 `git add -f review.md` 并 commit；不要 push，由用户手动 push。
```

## M8 reviewer: editor-grade leaderboard sprint audit

```text
这是独立只读 reviewer/auditor session。只审阅 `results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/` 的 M8 packet 和必要 first-party helper/source/test files。不要补 executor 缺失文件，不要改代码，不要训练，不要 validation packaging/upload，不要 hosted metric claim，不要 route promotion，不要启动 M9。最后只写该目录下的 `review.md`。

必须读取：

- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- latest M7 follow-up3 `review.md`
- all M8 required result files
- modified first-party model/training/evaluation/validator/test files

### A. Scope and shared-prompt merge gate

Reject if the M8 executor section is not present in `prompts/shared/EXECUTOR_PROMPTS.md` or the M8 reviewer section is not present in `prompts/shared/REVIEWER_PROMPTS.md`.

Reject if M8 claims validation upload, hosted metric, challenge submission, leaderboard readiness, scientific stop, route promotion, fold expansion, or M9. Reject if SRR is reduced to postprocessing or fallback instead of the full SRR-v3 route. Verify `m8_route_objective.md` and `m8_architecture_gap_closure_table.csv` against SRR-v2/v2.5/v3 design intent.

### B. Training budget and monitor gate

Reject any ready packet if total included MyoPS `train_loop_seconds` in `m8_training_budget_ledger.csv` is below `28800` without `M8_RESOURCE_BLOCKED` or user-approved exception. Reject if `m8_training_budget_ledger.csv` is missing.

Reject if a formal decision uses a minutes-long smoke: each decision training/probe must have `train_loop_seconds >= 900` and at least 3 validation events, or explicit plateau/early-stop evidence. Reject if there is no serious long primary candidate, recommended `train_loop_seconds >= 7200` or `optimizer_steps >= 6000`, without resource blocker.

Reject any ready packet containing `PENDING_MONITOR`, `NEEDS_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or submitted-only `commands_run.md`. Reviewer must confirm completed jobs were re-aggregated into tracked lightweight evidence after completion.

### C. Variant config and architecture closure gate

Reject if `m8_variant_config_contract.yaml/json` is missing, only natural language, not read/enforced by code, or if variants differ only by name. Check that V1, V2, and V3 have distinct encoder profile, dictionary slots, router/gate strategy, prototype source, hard-negative source, proposal thresholds, ROI policy, loss weights, sampler quotas, stages, optimizer/LR/scheduler, checkpoint rule, inference arbitration, and no-T2 safety.

Reject if `m8_architecture_gap_closure_table.csv` uses bare `CLOSED`; allowed closure statuses are `CLOSED_WITH_RUNTIME_EVIDENCE`, `CLOSED_BY_PREVIOUS_AUDITED_EVIDENCE`, `RESOURCE_BLOCKED_WITH_COMMANDS`, `NEEDS_REVISION`, and `NEEDS_EVIDENCE`. Reject code-path-only closure without runtime evidence, validator/test path, and reviewer reproduction command.

### D. Hardcase, mechanism, and contribution gate

Reject if `m8_batch_composition.csv` lacks per-step evidence or shows batches dominated by LGE-only/no-T2/easy cases. Reject if T2-present or edema-positive cases do not appear or are clearly below available-data proportion. Reject if no-T2 cases are used as edema negatives.

Reject if `m8_srr_contribution_by_case.csv` lacks per-case `anchor_delta_rate`, `final_delta_rate`, gate opening, SRR/proposal/refiner/fallback weights, final/ROI logit deltas, proposal recall/precision proxy, refiner delta magnitude, no-T2 edema voxels, Dice/HD95/remote-FP/component deltas, and source prediction path. `EVIDENCE_NOT_EXPORTED_PER_CASE` is a hard failure.

Reject if prototype, hard-negative, proposal, refiner, branch arbitration, or loss-gradient evidence is stale, synthetic-only, or not connected to final logits.

### E. Formal MyoPS evidence and local candidate assembly gate

Reject if formal evaluation is narrow/easy-only, lacks T2-present/CenterB/CenterC/GT-positive/remote-FP/no-T2 coverage when available, or uses foreground mean/empty-GT edema to hide failure.

Reject if `m8_local_inference_recipe.md`, `m8_candidate_assembly_matrix.csv`, or `m8_export_dry_run_qc.md` is missing. The candidate matrix must compare nnU-Net anchor control, best single SRR, anchor-preserving SRR correction, SRR plus component/remote-FP postprocessing, feasible TTA/flip ensemble, feasible SRR variant/checkpoint ensemble, and no-T2 safety enforced export rule.

### F. Cine mature registration and temporal dictionary gate

Reject if Cine is skipped. Reject if Cine is only a 3-case smoke, optical-flow-only proxy, descriptor-only proxy, untrained VoxelMorph, or one-case SyN.

Reviewer must confirm at least 12 Cine cases or maximum available same-safe subset, at least 3 non-reference frame pairs per case when possible, at least two mature registration families, quantitative before/after metrics, runtime/failure reason, and a best-registration selection.

If fewer than 12 cases are available, require `CINE_RESOURCE_OR_DATA_BLOCKED` with the available case pool. If no method is usable after mature attempts, require `CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT`; do not allow `myocardium_cinemyops` ready.

If any usable non-reference registration exists, reject unless temporal dictionary was executed. Temporal dictionary must include at least 3 usable cases or all usable cases; ED/reference anchor feature; at least 2 warped non-reference frame features per case; registration quality; frame quality; motion saliency; temporal representer slot usage; aggregation output; frame0 comparison; local class-1 Dice/HD95 proxy; class-3 sanity if available; hosted metric caveat.

### G. Decision separation and export QC gate

Reject if `m8_myops_decision.md`, `m8_cine_decision.md`, or `m8_combined_decision.md` is missing. MyoPS ready cannot imply Cine ready; Cine diagnostics cannot hide MyoPS no-promotion; skipped Cine fails M8.

Reject if `m8_label_export_dry_run_qc.md` or `m8_official_label_mapping_qc.csv` is missing. Check official label values scar `2221`, edema `1220`, LV `500`, myocardium `200`, RV `600`, invalid labels, folder schema, and explicit no-upload/no-hosted-metric caveat.

### H. Strict validator gate

Reject unless the M8 strict validator exits 0 on the real packet and nonzero on real mutated known-bad fixtures covering: under-8h ready packet; missing budget ledger; pending monitor ready packet; completed job not re-aggregated; config contract not used; renamed-only variants; missing per-case contribution; easy-only formal eval; no-T2 violation; missing candidate assembly; Cine smoke/proxy-only; no best-registration selection; usable registration without temporal dictionary; missing export dry-run QC; placeholder/synthetic-only final proof; unauthorized validation/upload/hosted claim.

### I. Reviewer decision states

Allowed decisions:

- `M8_AUDITED_LOCAL_PROMOTION_CANDIDATE`
- `M8_AUDITED_GO_FOR_FOLD_EXPANSION_PLANNING`
- `M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`
- `M8_AUDITED_NEEDS_REVISION`
- `M8_AUDITED_NEEDS_EVIDENCE`
- `M8_AUDITED_RESOURCE_BLOCKED`
- `M8_AUDITED_NEEDS_MONITOR`

`M8_AUDITED_LOCAL_PROMOTION_CANDIDATE` does not authorize validation upload, hosted metric claim, leaderboard-ready status, challenge submission, or M9. It only authorizes GPT/user planning for fold expansion, packaging design, or a separate human-approved validation submission milestone.
```

## M8 reviewer follow-up: no-promotion repair decision audit

You are the separate read-only reviewer/auditor for the M8 follow-up no-promotion repair decision milestone.

Required protocol sentence: This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, and do not start the next milestone. Review only the completed result directory, write review.md with the controlled milestone decision, then force-add/commit review.md. Do not push automatically.

### 1. Review scope

Review only:

```text
prompts/shared/EXECUTOR_PROMPTS.md
prompts/shared/REVIEWER_PROMPTS.md
scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_route_promotion_decision.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_best_variant_decision_table.csv
```

You may also read the required protocol files if needed:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
```

### 2. Required checks

Check that the executor did not convert M8 into route promotion, fold expansion, validation packaging, hosted metric claim, leaderboard readiness, scientific stop, or M9.

Check that `results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/` includes:

```text
result.md
completion_check.md
review_request.md
MANIFEST.md
commands_run.md
m8_followup_route_objective.md
m8_review_findings_ledger.csv
m8_candidate_failure_matrix.csv
m8_proxy_feature_schema.csv
m8_proxy_arbitration_help_harm.csv
m8_hard_subgroup_help_harm.csv
m8_no_t2_safety_report.csv
m8_repair_contract.md
m8_next_required_action.md
m8_followup_strict_validator_report.csv
m8_followup_strict_validator_report.md
m8_followup_validator_selftest_report.csv
m8_followup_validator_selftest_report.md
```

Check that the policy feature schema marks these as forbidden for selected deployable policies: case ID, GT metric values as decision inputs, hosted feedback, manual case lists, foreground_mean-only selection, and center-ID-only routing.

Check that the same-split nnU-Net anchor is included and that scar and edema are reported separately. Do not accept a foreground mean as route evidence.

Check no-T2 edema safety. Any selected policy with nonzero no-T2 edema voxels must be rejected unless it is clearly diagnostic-only and not selected.

Check hard subgroups. The packet must not be easy-only. It must include T2-present, no-T2 safety, CenterB/CenterC or the strongest available equivalents, scar-positive/edema-positive, and remote-FP/component-burden analysis where available.

Check repair-contract readiness. Treat a policy as diagnostic-only, not repair-contract-ready, if its benefit comes mainly from anchor-only fallback, uses SRR on only a negligible fraction of cases, improves only a single easy metric while leaving edema/remote-FP/component hard subgroups unresolved, or cannot explain why the deployable proxy selects SRR in terms of the SRR-v3 mechanism. A valid repair contract must show that SRR contributes a nontrivial, mechanism-consistent, same-split help signal under allowed non-GT proxy features; otherwise the correct next action is `GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR`, not a repair-ready decision.

Check validator behavior. The real packet validator must pass with zero errors only for a valid packet, and known-bad self-tests must fail closed. If a known-bad mutation passes, return `M8_FOLLOWUP_AUDITED_NEEDS_REVISION`.

Check evidence quality. Monitor packets, pending Slurm jobs, smoke-only evidence, synthetic evidence, placeholder evidence, old summaries, executor self-review, or missing aggregation cannot support audited-go.

### 3. Review decision states

Write `results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md` with exactly one of these controlled decisions:

```text
M8_FOLLOWUP_AUDITED_REPAIR_CONTRACT_READY
M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED
M8_FOLLOWUP_AUDITED_NEEDS_EVIDENCE
M8_FOLLOWUP_AUDITED_NEEDS_REVISION
M8_FOLLOWUP_AUDITED_PROTOCOL_BLOCKED
```

`M8_FOLLOWUP_AUDITED_REPAIR_CONTRACT_READY` means only this: GPT may plan a future bounded repair implementation milestone using the reviewed repair contract. It does not authorize Codex to start that implementation automatically, and it does not authorize route promotion, fold expansion, validation packaging, upload, hosted metric claims, leaderboard claims, scientific stop, or M9.

Use `M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED` if the executor produced a valid diagnostic packet but no deployable non-GT arbitration/repair contract improves the situation enough to justify implementation.

Use `M8_FOLLOWUP_AUDITED_NEEDS_EVIDENCE` if required M8 inputs or follow-up outputs are missing, if runtime/proxy evidence is insufficient, or if the packet relies only on natural-language claims.

Use `M8_FOLLOWUP_AUDITED_NEEDS_REVISION` if code, schema, validator, leakage prevention, no-T2 safety, same-split comparison, or hard-subgroup reporting is broken.

Use `M8_FOLLOWUP_AUDITED_PROTOCOL_BLOCKED` if the executor violated role boundaries by writing `review.md`, starting the next milestone, claiming M9, packaging validation, uploading, or claiming hosted metrics.

### 4. Commit policy

Commit only the review file:

```bash
git add -f results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md
git commit -m "Add M8 follow-up repair decision review"
```

Do not push automatically.

## M9 reviewer: SRR dictionary fidelity repair + pathology-specific refiner + Cine final-output training evidence


You are the separate read-only reviewer/auditor for M9 SRR dictionary fidelity repair + pathology-specific refiner + Cine final-output training evidence.

Required protocol sentence: This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, and do not start the next milestone. Review only the completed result directory, write review.md with the controlled milestone decision, then force-add/commit review.md. Do not push automatically.

### 1. Review scope

Review only:

```text
prompts/shared/EXECUTOR_PROMPTS.md
prompts/shared/REVIEWER_PROMPTS.md
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/losses/srr_losses.py
src/care_myocardium/cine/
scripts/training/run_srr_propref_myops_fold0.py
scripts/training/run_cine_temporal_output_m9.py
scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
jobs/src/run_srr_v3_m9_dictionary_fidelity_training_htzhulab.sh
jobs/src/run_srr_v3_m9_dictionary_fidelity_training.sh
jobs/src/run_srr_v3_m9_cine_temporal_output_htzhulab.sh
jobs/src/run_srr_v3_m9_cine_temporal_output.sh
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md
TODO.md
TODO-dictionary.md
prompts/tasks/20260703_cine_motion.md
```

You may read protocol files as needed:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
```

### 2. Required review checks

Check M9 did not claim validation packaging, validation upload, hosted metrics, leaderboard readiness, fold expansion, scientific stop, or M10.

Check loss-weight wiring. The review must inspect both code and `m9_loss_weight_wiring_test_report.md`. If component weights do not reach the actual M9 total loss, return `M9_AUDITED_NEEDS_REVISION`.

Check checkpoint selection. If best checkpoint is selected only by patch loss, return `M9_AUDITED_NEEDS_REVISION`.

Check nnU-Net role. If formal M9 candidate outputs normally use `nnunet_anchor_logits + bounded_delta` as final logits, or if anchor-only / M8 anchor-residual controls are treated as SRR candidate wins, return `M9_AUDITED_PROTOCOL_BLOCKED` or `M9_AUDITED_NEEDS_REVISION`.

Check True-BR2 dictionary fidelity. Formal M9 candidates must use real per-modality features and invalid-slot masks. `[fused,fused,fused]` pseudo-modality paths may appear only in legacy controls, never formal M9 candidates.

Check Pattern-SIP. The packet must report pattern-conditioned soft integrativeness across availability/style/hard-subgroup groups. Uniform entropy/coverage alone is insufficient.

Check prototype memory. Deterministic axis prototypes alone cannot support formal evidence. Edema negatives must be T2-present safe negatives only, and no-T2 myocardium must not enter edema negative memory.

Check pathology-specific refiner fidelity. Scar must have small-ROI high-resolution LGE-dominant precision refinement evidence. Edema must have large-ROI T2-conditioned context-preserving refinement evidence. Identical scar/edema refiner behavior is not acceptable for a formal candidate.

Check refiner causal effect. The refiner must be evaluated by final-label/logit effect and ablations. A residual tensor without final-label impact is not enough.

Check training adequacy. M9 must meet its MyoPS training budget or use a controlled undertrained/monitor/resource-blocked state. Monitor packets, pending Slurm jobs, smoke-only evidence, or synthetic evidence cannot be audited-go.

Check metrics. Same-split comparison must report scar and edema separately, hard subgroups, no-T2 safety, remote FP, component count, HD95, proposal recall/precision, and refiner causal effect. Do not accept foreground mean as evidence.

Check Cine final-output branch. Cine must not be optional. The review must reject weight-download-only, single SyN/Demons smoke, descriptor-only temporal retrieval, frame0-only output, unverified VoxelMorph claims, registration-only evidence without final labels, and temporal dictionary evidence without final output. A valid M9 Cine packet must include final local predictions under ignored runtime, tracked manifests/QC/metrics, non-reference-frame evidence, frame0/reference comparison, and no hosted metric claim.

Check validator. The strict validator must pass the real packet with zero errors and fail all known-bad self-tests. If known-bad passes, return `M9_AUDITED_NEEDS_REVISION`.

### 3. Review decisions

Write `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md` with exactly one of:

```text
M9_AUDITED_REPAIR_CONTRACT_READY
M9_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED
M9_AUDITED_SCIENTIFIC_UNDERTRAINED
M9_AUDITED_NEEDS_EVIDENCE
M9_AUDITED_NEEDS_REVISION
M9_AUDITED_NEEDS_MONITOR
M9_AUDITED_RESOURCE_BLOCKED
M9_AUDITED_PROTOCOL_BLOCKED
```

`M9_AUDITED_REPAIR_CONTRACT_READY` means only this: GPT may plan a future M10 dictionary iteration, Cine temporal route expansion, or combined repair continuation based on reviewed M9 evidence. It does not authorize validation packaging/upload, hosted claims, leaderboard claims, fold expansion, scientific stop, or automatic M10 execution.

Use `M9_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED` if M9 validly repairs fidelity and trains adequately but still does not show enough SRR-main/dictionary/Cine final-output signal for the next implementation step.

Use `M9_AUDITED_SCIENTIFIC_UNDERTRAINED` if implementation fidelity is improved but training did not meet adequacy or loss/metrics are too immature for scientific judgment.

Use `M9_AUDITED_NEEDS_EVIDENCE` if required output files, runtime evidence, same-split controls, hard subgroup metrics, or Cine final-output evidence are missing.

Use `M9_AUDITED_NEEDS_REVISION` if code, loss wiring, checkpoint selection, dictionary fidelity, prototype memory, scar/edema refiner asymmetry, refiner causal effect, no-T2 safety, Cine architecture, or validator behavior is broken.

Use `M9_AUDITED_NEEDS_MONITOR` if any required Slurm-derived evidence is still pending/running/awaiting aggregation.

Use `M9_AUDITED_RESOURCE_BLOCKED` if the packet honestly documents a resource/dependency blocker and does not claim completion.

Use `M9_AUDITED_PROTOCOL_BLOCKED` if the executor wrote review.md, started M10, packaged validation, uploaded, claimed hosted metrics, omitted Cine while marking M9 ready, or made nnU-Net the formal candidate protagonist.

### 4. Commit policy

Commit only the review file:

```bash
git add -f results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md
git commit -m "Add M9 SRR dictionary fidelity and Cine output review"
```

Do not push automatically.
