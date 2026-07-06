# SRR-v3 Reviewer Prompts

Copy exactly one section into a separate read-only Codex reviewer/auditor session after the corresponding executor result has been committed and pushed by the user. The reviewer must commit locally and stop. The user manually pushes.

## Global reviewer rule

```text
这是独立只读 reviewer/auditor session。不要补 executor 缺失文件，不要改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动下一个 milestone。只审阅对应的 results/<task_key>/，最后只写该目录下的 review.md，并给出该 milestone 允许的 controlled decision。写完后用 git add -f 提交 review.md，但不要 push，由用户手动 push。
```

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

## M7 reviewer (continued): blocker repair audit

```text
这是独立只读 reviewer/auditor session。只审阅 `results/20260705_srr_v3_m7_training_and_cine_utilization/` 的 M7 continued packet 和必要 first-party helper/source/test files。不要补 executor 缺失文件，不要改代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动 M8。最后只写该目录下的 `review.md`。

必须读取：

- `prompts/shared/EXECUTOR_PROMPTS.md` 中的 `M7 executor (continued): reviewer-blocker repair`；
- `prompts/shared/REVIEWER_PROMPTS.md` 中的本 reviewer continued 段；
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`；
- `prompts/HANDOFF_GATE_POLICY.md`；
- `prompts/GPT_HARD_GATE_PROMPT.md`；
- prior M7 `review.md`；
- M7 continued result directory；
- modified first-party training/evaluation/Cine/loss/model/test files。

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

最后只写 `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`。完成后 `git add -f review.md` 并 commit；不要 push，由用户手动 push。
```
