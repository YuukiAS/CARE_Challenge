# M6/M7 具体 reviewer gate addendum

status: `MERGE_INTO_SHARED_REVIEWER_PROMPTS`
merge_target: `prompts/shared/REVIEWER_PROMPTS.md`

## 1. Reviewer 总原则

M6/M7 reviewer 是独立只读 auditor。不得补 executor 缺失文件，不得修改模型代码，不得训练，不得 validation packaging/upload，不得 route promotion，不得启动后续 milestone。Reviewer 只审阅对应 result directory 和必要 first-party helper/source/config，最后只写 `review.md`。

M6/M7 reviewer 不得接受“图里有、prompt 里写了、executor 说实现了”作为证据。每个关键机制必须有机器可读或至少文件可审计证据：CSV/JSON/Markdown table、unit test、strict validator、commands、artifact path、runtime output、loss/backward evidence。

## 2. M6 reviewer 必查项

M6 result directory 应为：

`results/20260705_srr_v3_m6_myops_concrete_architecture_repair/`

M6 reviewer 必须读取：

- `prompts/shared/20260706_M6_M7_concrete_design_review.md`；
- `prompts/shared/20260706_M6_concrete_executor_contract.md`；
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`；
- `prompts/HANDOFF_GATE_POLICY.md`；
- `prompts/GPT_HARD_GATE_PROMPT.md`；
- `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md`；
- M6 result directory；
- M6 修改过的 first-party model/loss/training/evaluation/validator 代码。

### 2.1 M6 prerequisite 与 scope

必须确认：

- M4 review 包含 `M4_AUDITED_GO`；
- M6 没有 full fold training；
- M6 没有 validation packaging/upload；
- M6 没有 hosted metric claim；
- M6 executor 没有写自己的 `review.md`；
- M6 executor 没有启动 M7；
- M6 lightweight evidence 和必要 helper/source/config 已 git-tracked。

### 2.2 M6 architecture trace

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

### 2.3 M6 encoder/decoder gate

`encoder_decoder_capacity_sanity.csv` 必须包含至少：

- `full_4scale` `32/64/128/256` 的 forward/memory smoke 或真实 OOM 证据；
- `balanced_4scale` `16/32/64/128` 的可运行证据；
- `safe_4scale` 仅作为 fallback/smoke 的说明；
- anatomy/scar/edema decoder 的输出 shape、参数量、是否参与 loss/backward。

如果唯一证据是三尺度 `10/20/40` 或 tiny smoke，decision 必须是 `M6_AUDITED_NEEDS_REVISION`。

### 2.4 M6 dictionary/prototype gate

`retrieval_bank_runtime_sanity.csv` 必须显示 dictionary slots 在 runtime 非空、invalid modality slots 被 mask、T2 缺失时 T2 slots 不被当作 edema evidence、task-specific routers 有 usage/entropy/collapse 统计。

`prototype_bank_runtime_sanity.csv` 必须显示 scar-positive、scar-safe-negative、edema-positive、edema-safe-negative 四类 bank；edema-positive 和 edema-safe-negative 必须来自 T2-present 安全证据。若 no-T2 myocardium 被当作 edema negative，必须判 `M6_AUDITED_NEEDS_REVISION` 或 `M6_AUDITED_NEEDS_EVIDENCE`。

### 2.5 M6 proposal/refiner/arbitration gate

`anatomy_proposal_sanity.csv` 必须证明 anatomy prior/distance/uncertainty、scar proposal、edema proposal 均有非空 runtime evidence，并且 no-T2 edema proposal 为 0。

`refiner_roi_component_sanity.csv` 必须证明 refiner 是 bounded crop/local correction，不是 full-volume residual。若 `is_full_volume_crop=True` 且被当作通过证据，必须 fail。

`branch_arbitration_sanity.csv` 必须导出 segmentation_weight、srr_retrieval_weight、proposal_weight、refiner_weight、chosen_source 或等价字段。必须同时证明 correction-positive 时 SRR 可被采用，SRR 低质时 segmentation branch 可被采用。

`decode_gate_consistency_sanity.csv` 必须证明 fallback/closed gate/refiner mask 关闭时 final labels 精确等于 segmentation branch。任何 hidden decode delta 都是 blocker。

### 2.6 M6 loss gate

`loss_refiner_component_sanity.csv` 必须包含每个 loss component 的 value、weight、nonzero flag、requires_grad、gradient_norm 或 one-step update evidence。必须覆盖 anatomy、scar proposal、edema proposal、scar refiner、edema refiner、anchor preservation、arbitration consistency、bounded correction、component/remote-FP、no-T2 safety、dictionary regularization、prototype margin/diversity。

如果 loss 只有 total loss 或自然语言说明，必须 fail。

### 2.7 M6 strict validator gate

`strict_validator_report.md` 必须证明 validator 对真实 packet 通过，对 known-bad packets fail closed。Known-bad 至少包括 claim-only、missing architecture trace、empty dictionary/prototype、hidden decode delta、SRR-zero-contribution、loss empty、no-T2 unsafe、full-volume-refiner。若 validator 不能 fail closed，不能给 `M6_AUDITED_GO`。

### 2.8 M6 reviewer decision

M6 reviewer decision 只能是：

- `M6_AUDITED_GO`
- `M6_AUDITED_NEEDS_REVISION`
- `M6_AUDITED_NEEDS_EVIDENCE`

即使 M6 通过，也不授权 route promotion、fold expansion、validation packaging/upload、hosted metric claim、scientific stop 或 M7 以外的后续任务。

## 3. M7 reviewer 必查项

M7 result directory 应为：

`results/20260705_srr_v3_m7_training_and_cine_utilization/`

M7 reviewer 必须读取：

- `prompts/shared/20260706_M6_M7_concrete_design_review.md`；
- `prompts/shared/20260706_M7_concrete_executor_contract.md`；
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`；
- `prompts/HANDOFF_GATE_POLICY.md`；
- `prompts/GPT_HARD_GATE_PROMPT.md`；
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md`；
- `results/20260705_srr_v3_m5_cine_secondary_contract/review.md` if Cine subline runs；
- M7 result directory；
- M7 修改过的 first-party training/evaluation/Cine helper/validator 代码。

### 3.1 M7 prerequisite 与 scope

必须确认：

- M6 review 包含 `M6_AUDITED_GO`；
- M7 executor 没有写自己的 `review.md`；
- M7 没有 validation packaging/upload；
- M7 没有 hosted metric claim；
- M7 没有 route promotion；
- M7 没有启动后续 milestone；
- M7 lightweight evidence 和必要 helper/source/config 已 git-tracked。

### 3.2 M7 training adequacy gate

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

### 3.3 M7 metric and selection gate

`same_split_help_harm.csv`、`hard_subgroup_metrics.csv`、`best_variant_decision.md` 必须证明 best variant 是按预定义规则选择，而不是 executor 主观判断。

Reviewer 必须 reject：

- no-T2 edema unsafe 的 variant；
- scar catastrophic regression 无充分 edema improvement 的 variant；
- 只比旧 SRR、不比同 split nnU-Net 的结论；
- 只看 Dice、不看 HD95/component/remote FP 的结论；
- 使用 validation case ID 规则或 GT-tuned fallback 的结论。

### 3.4 M7 loss/arbitration/prototype gate

必须检查：

- `loss_component_by_step.csv` 是否包含全部核心 loss component；
- `loss_component_gradient_sanity.csv` 是否显示组件参与 backward；
- `branch_arbitration_by_case.csv` 是否显示 chosen_source 和 weights；
- `dictionary_prototype_usage_by_variant.csv` 是否显示 dictionary/prototype 非空且无 no-T2 edema negative；
- `proposal_refiner_by_case.csv` 是否显示 bounded ROI/refiner behavior；
- `no_t2_safety_by_variant.csv` 是否显示 no-T2 全链路安全。

### 3.5 M7 CineMA/Cine gate

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

### 3.6 M7 reviewer decision

M7 reviewer decision 只能是：

- `M7_AUDITED_GO_FOR_NEXT_PLANNING`
- `M7_AUDITED_NEEDS_REVISION`
- `M7_AUDITED_NEEDS_EVIDENCE`
- `M7_AUDITED_UNDERTRAINED`
- `M7_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

`M7_AUDITED_GO_FOR_NEXT_PLANNING` 只表示 M7 证据可供 GPT planner 继续决策，不等于 route promotion。Reviewer 不得授权 validation packaging/upload、hosted metric claim、fold expansion 或 challenge submission。
