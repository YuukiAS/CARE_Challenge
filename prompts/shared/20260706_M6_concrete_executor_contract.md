# M6 具体 executor 合同：SRR-v3 MyoPS architecture/runtime repair

status: `MERGE_INTO_SHARED_EXECUTOR_PROMPTS`
merge_target: `prompts/shared/EXECUTOR_PROMPTS.md`
replaces_or_overrides: `M6 executor: SRR-v3 diagram-faithful MyoPS repair` 中过于抽象的部分
expected_result_dir: `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/`

## 1. 入口与边界

只执行 M6。开始前必须确认：

- `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md` 存在且包含 `M4_AUDITED_GO`；
- M6 不依赖 M5；M5 是 Cine 副线诊断，不是 MyoPS M6 的前置条件；
- 不允许 full fold training；不允许 validation packaging/upload；不允许 route promotion；不允许 hosted metric claim；不允许启动 M7；
- 必须提交 lightweight evidence packet 供独立 reviewer 审阅；不要 push。

如果 M4 prerequisite 不满足，停止并写 `M6_BLOCKED_BY_M4`，不得做科学任务。

## 2. M6 的科学任务

M6 的任务不是“再训练一下 M3”，也不是“把 SRR 变成 nnU-Net 后处理”。M6 必须把当前 SRR-v3 MyoPS path 修成一个可以进入 M7 最小有效训练的 architecture/runtime 系统。它必须同时满足：

- SRR retrieval/proposal/refiner/arbitration 在 forward 中实际被调用；
- loss components 不是空日志，而是有数值、梯度或 one-step update evidence；
- nnU-Net 作为 segmentation context/evidence/safety fallback，不是唯一最终答案；
- closed/fallback path 必须精确复现 nnU-Net；
- SRR 在 correction-positive synthetic/real smoke 中必须能产生非零贡献；
- no-T2 edema 在 proposal、refiner、loss、decode、export 全链路安全。

## 3. 必须实现的 concrete variants

Codex 不能自己设计 variant。M6 必须实现或明确保留以下三个 variant；如果某个 variant 由于真实 blocker 无法实现，必须写清 blocker，不得悄悄省略。

### 3.1 `m6_full_srr_context_arbitration`

这是最完整的 SRR-v3 修复候选。必须包含：

- encoder profile: 默认 `balanced_4scale`，channels `16/32/64/128`；另做 `full_4scale` `32/64/128/256` 的 forward/memory smoke；
- dictionary: `dict_full_interaction`，每尺度 shared 8、LGE-private 4、C0-private 4、T2-private 4、LGE-T2 interaction 4、LGE-C0 interaction 4、T2-C0 interaction 4；
- prototype: scar-positive、scar-safe-negative、edema-positive、edema-safe-negative 四组；edema-positive 和 edema-safe-negative 只能来自 T2-present 安全证据；
- proposal: scar/edema separate proposal decoder，`positive_similarity - negative_similarity + anchor_component + anatomy_distance + uncertainty + learned_residual`；
- refiner: scar small-ROI crop refiner、edema context-ROI crop refiner；
- arbitration: learnable or rule-initialized branch/evidence arbitration，输出 per-case/per-class weights。

### 3.2 `m6_conservative_component_arbitration`

这是稳定性候选。必须包含：

- encoder profile: `safe_4scale` 或 `balanced_4scale`；
- dictionary: `dict_conservative_private_shared`，shared 6、LGE-private 4、C0-private 2、T2-private 4，可选 LGE-T2 interaction 2；
- proposal: 强依赖 nnU-Net components 和 uncertainty，只允许 bounded correction；
- refiner: scar 更高 precision，edema no-T2 更强关闭；
- arbitration: component-level 或 class-level conservative rule，只有在 SRR evidence 高于阈值且 anchor uncertainty 高时打开。

### 3.3 `m6_scar_precision_edema_safe`

这是病理特异性候选。必须包含：

- scar 分支偏向 LGE-private、LGE-C0/LGE-T2 interaction、small ROI、remote-FP suppression；
- edema 分支偏向 T2-private、T2 interaction、larger context ROI、T2-present-only learning；
- no-T2 case 中 edema proposal/refiner/final decode/export 全部 inert；
- scar 不得因 edema safety 改动而退化为全空或大面积 FP。

## 4. encoder/decoder 要求

M6 必须把 encoder/decoder 容量写死为可审计 profile，而不是继续让 Codex 用 tiny 结构偷懒。

必需 profile：

- `full_4scale`: `32/64/128/256`，至少跑 synthetic 或 one real patch forward；如果 OOM，要记录 exact command、patch shape、error、memory context；
- `balanced_4scale`: `16/32/64/128`，默认 M7 候选；
- `safe_4scale`: `12/24/48/96` 或 `8/16/32/64`，只作为 OOM fallback 或 smoke，不得无理由作为最终设计。

每个 profile 必须导出：input shape、availability pattern、encoder scale shapes、decoder scale shapes、parameter count、activation/memory estimate、runtime seconds。decoder 必须是 anatomy/scar/edema task-specific decoder，不能把所有任务压成一个 shallow shared head。

## 5. segmentation context interface

M6 必须新增或明确修复 `segmentation_context_interface`，使 nnU-Net/强分割模型作为 evidence 进入 SRR，而不是绕过 SRR：

输入字段至少包括：

- `anchor_probabilities` 或 `anchor_logits`；
- `anchor_hard_prediction`；
- `scar_component_mask`、`edema_component_mask`；
- `anchor_entropy`、`anchor_margin`、`anchor_confidence`；
- `component_size`、`component_distance_to_union`、`remote_component_flag`；
- `anatomy_union_support` 或从 anchor/anatomy decoder 派生的 union/LV/RV context。

必须导出 `segmentation_context_interface_sanity.csv`，每行包含 case_id、class、anchor source path、tensor shapes、nonzero rates、component counts、uncertainty statistics、used_by_proposal、used_by_refiner、used_by_arbitration。

## 6. dictionary / prototype runtime 要求

M6 必须导出 `retrieval_bank_runtime_sanity.csv`，至少包含：

- variant；
- case_id；
- availability pattern；
- scale；
- task；
- group；
- slot_count；
- active_slot_count；
- mean_usage；
- entropy；
- max_weight；
- collapse_warning；
- masked_invalid_slot_usage；
- t2_private_usage_when_no_t2；
- gradient_norm 或 one-step update status。

M6 必须导出 `prototype_bank_runtime_sanity.csv`，至少包含：

- variant；
- bank_type: scar_positive / scar_safe_negative / edema_positive / edema_safe_negative；
- source split；
- source cases；
- component count；
- voxel count；
- feature stage；
- prototype count；
- no_t2_used_as_edema_negative: 必须为 false；
- leakage_check；
- empty_bank_status。

如果 edema-positive 或 edema-safe-negative 为空，M6 不能写 ready。

## 7. proposal/refiner 机制要求

M6 必须导出 `anatomy_proposal_sanity.csv` 和 `refiner_roi_component_sanity.csv`。

`anatomy_proposal_sanity.csv` 至少包含：

- `P_union/P_LV/P_RV` nonzero rate；
- distance/proximity map range；
- uncertainty range；
- scar proposal foreground rate；
- edema proposal foreground rate；
- positive/negative similarity means；
- anchor component evidence contribution；
- proposal recall/precision proxy；
- outside-myocardium FP proxy；
- no-T2 edema proposal voxels，必须为 0。

`refiner_roi_component_sanity.csv` 至少包含：

- refiner type: scar_small_roi / edema_context_roi；
- crop bounds；
- crop_volume_ratio；
- crop_mask_volume_ratio；
- `is_full_volume_crop`，必须为 false；
- original modality crop used: scar 必须 LGE，edema 必须 T2-present only；
- anchor/prototype/dictionary/anatomy/uncertainty inputs used；
- residual magnitude；
- bounded_delta max；
- component_count_delta proxy；
- remote_FP_delta proxy；
- no-T2 edema final voxels，必须为 0。

## 8. branch/evidence arbitration 与 decode consistency

M6 必须实现 explicit arbitration。每个 case/class 至少输出：

- `segmentation_weight`；
- `srr_retrieval_weight`；
- `proposal_weight`；
- `refiner_weight`；
- `chosen_source`；
- `fallback_reason`；
- `anchor_confidence`；
- `srr_confidence`；
- `correction_mask_rate`；
- `label_delta_vs_anchor`。

必须有两个 sanity：

1. correction-positive sanity：在 synthetic known-error 或 explicit high-uncertainty real patch 中，SRR/proposal/refiner contribution 必须非零；
2. low-quality SRR sanity：当 SRR evidence 被置空、prototype bank 为空或 proposal confidence 低时，arbitration 必须选择 segmentation branch，final labels 必须精确等于 anchor。

`decode_gate_consistency_sanity.csv` 必须证明：当 explicit fallback、closed gate 或 refiner mask 关闭时，final labels 与 segmentation branch 完全一致。若出现 hidden decode delta，strict validator 必须失败。

## 9. loss implementation 要求

M6 必须新增或改造 loss，使 `loss_refiner_component_sanity.csv` 至少覆盖以下组件：

- `loss_anatomy_union_lv_rv`；
- `loss_scar_proposal`；
- `loss_edema_proposal_t2_present_only`；
- `loss_scar_refiner_roi`；
- `loss_edema_refiner_t2_present_roi`；
- `loss_anchor_preservation_outside_roi`；
- `loss_branch_arbitration_consistency`；
- `loss_bounded_correction`；
- `loss_component_remote_fp`；
- `loss_no_t2_edema_safety`；
- `loss_dictionary_entropy_coverage_load_balance`；
- `loss_prototype_diversity_margin`。

每个 loss 组件必须导出 value、weight、nonzero flag、requires_grad flag、gradient_norm 或 synthetic backward/one-step update evidence。不能只有自然语言说明。

## 10. strict validator known-bad cases

M6 必须新增或加严 strict validator，使以下 known-bad packet fail closed：

- claim-only architecture trace；
- missing `srr_v3_fidelity_contract.md`；
- dictionary slot usage 全空；
- prototype bank 空或 no-T2 myocardium 被当作 edema negative；
- segmentation context 直接绕过 SRR 成为 final output 且无 explicit fallback reason；
- closed/fallback gate 下 final labels 仍改变；
- refiner 是 full-volume residual；
- loss components 为空或无 backward evidence；
- SRR contribution 在 correction-positive sanity 中全为 0；
- no-T2 edema 在 proposal/refiner/final decode/export 任一环节非零。

## 11. 必需输出文件

M6 结果写入 `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/`，必须写齐：

- `result.md`
- `srr_v3_fidelity_contract.md`
- `architecture_component_trace.csv`
- `m4_failure_mapping.csv`
- `code_diff_summary.md`
- `encoder_decoder_capacity_sanity.csv`
- `segmentation_context_interface_sanity.csv`
- `retrieval_bank_runtime_sanity.csv`
- `prototype_bank_runtime_sanity.csv`
- `anatomy_proposal_sanity.csv`
- `branch_arbitration_sanity.csv`
- `decode_gate_consistency_sanity.csv`
- `loss_refiner_component_sanity.csv`
- `refiner_roi_component_sanity.csv`
- `no_t2_safety_sanity.csv`
- `strict_validator_report.md`
- `unit_test_report.md`
- `commands_run.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`

## 12. completion gate

`completion_check.md` 只能写：

- `M6_READY_FOR_REVIEW`
- `M6_NEEDS_REVISION`
- `M6_NEEDS_EVIDENCE`
- `M6_BLOCKED_BY_M4`

不能写 `M6_READY_FOR_REVIEW` 的情况：

- 没有逐项 architecture trace；
- 使用 tiny three-scale 结构作为唯一证据；
- dictionary/prototype/proposal/refiner/loss/arbitration 任一核心模块没有 runtime evidence；
- no-T2 edema 不安全；
- local refiner 是 full-volume；
- closed/fallback 下 final labels 改变；
- SRR contribution 在 correction-positive sanity 中为 0；
- loss components 没有数值/梯度/one-step sanity；
- strict validator 不能 fail closed known-bad packets；
- reviewer 需要的轻量证据没有 git-tracked。

完成后必须 `git add -f` 并本地 commit M6 轻量证据和必要 first-party helper/source/config；不要提交 checkpoint、NIfTI、upload package、大日志、raw data、secrets、environment dump 或整棵 runtime tree；不要 push；不要写 `review.md`；不要启动 M7。
