# M6: SRR-v3 Diagram-Faithful MyoPS Repair Prompts

This file supplements `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md` for the next MyoPS milestone. Use this version instead of the earlier abstract co-equal M6 prompt when starting M6.

## M6 executor

```text
只执行 M6：SRR-v3 diagram-faithful MyoPS repair。M5 是 Cine 副线，不是 M6 前置条件。开始前必须确认 `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md` 存在且包含 `M4_AUDITED_GO`，否则停止并写 `M6_BLOCKED_BY_M4`。

这是 MyoPS 主线的 architecture-faithfulness / runtime-repair milestone，不是 full fold，不是 route promotion，不是 validation packaging/upload。M6 不是发明新路线，也不是把 SRR 抽象成一个和 nnU-Net 竞争的黑盒分支。M6 必须回到 v2/v2.5/v3 图中的完整设计：availability-aware modality-specific retrieval、strong encoder、semantic representation retrieval bank、real train/OOF prototypes、anatomy-guided lesion proposal、pathology-specific soft-ROI refinement、显式 training objectives，以及 nnU-Net/强分割模型提供的 anchor/context/uncertainty/component/anatomy evidence。

核心原则：nnU-Net 或其他强分割模型可以作为同等重要的分割证据和安全上下文，但不能成为唯一主角；SRR 也不能成为可有可无的后处理。最终系统应是“分割证据 + SRR 检索证据 + 解剖 proposal + pathology-specific refiner + 显式损失/仲裁”的联合机制。closed-gate fallback 只是防止伤害 baseline 的安全刹车，不是论文方法本身。

背景证据来自 M3/M4：M3 最小有效训练通过但同 split 指标伤害 nnU-Net；M4 证明 closed-gate identity 中性，no-anchor 很伤，M3 trained gate 几乎关闭但 pathology-aware decode/proposal/refinement 仍会改标签。结论是：SRR-v3 思想本身没有被证明失败，失败更像是图里的关键约束没有被充分实现，尤其是 decode/gate consistency、proposal/refiner 校准、loss/refiner 中心性和分割上下文接口。

必须先写 `srr_v3_fidelity_contract.md`，逐项映射 v2/v2.5/v3 图中的模块到当前代码路径和 M6 修复目标。至少覆盖：

1. Inputs & availability：LGE/C0/T2 modality-specific stems、availability mask、no zero-filling semantics、no-T2 edema conditional supervision。
2. Strong encoder & segmentation context interface：shared/strong multi-scale encoder；nnU-Net/强分割模型的 probabilities/logits、hard prediction、scar/edema components、uncertainty/confidence、anatomy context。这里叫 context/evidence interface，不叫 final answer。
3. Semantic retrieval bank：每个尺度的 shared dictionary、LGE-private、C0-private、T2-private、optional interaction dictionary、router、anatomy/scar/edema routed features、dictionary slot usage、real train/OOF prototype source。
4. Anatomy-guided lesion proposal：anatomy decoder 输出 `P_union/P_LV/P_RV`；anatomy prior/distance/uncertainty soft gate；scar proposal decoder 和 edema proposal decoder；nnU-Net component/uncertainty 只作为 proposal evidence 之一。
5. Soft-ROI refinement & outputs：soft-ROI generator；scar small-ROI refiner；edema large-ROI refiner；refiner 必须消费 SRR proposal、anatomy prior、distance/uncertainty、segmentation context、prototype similarity、原始 LGE/T2 crop，并输出 bounded local correction。
6. Training objectives：anatomy loss、scar proposal loss、T2-masked edema proposal loss、scar refiner loss、T2-masked edema refiner loss、negative-space/hard-negative loss、prior/ROI loss、dictionary sparsity/coverage/load-balance/prototype-diversity loss、branch arbitration/decode consistency loss、optional alignment loss。

必须实现或重构以下机制，并用小规模 synthetic + explicit real-case smoke 证明它们真的运行：

1. SRR-v3 architecture fidelity：retrieval bank、prototype groups、anatomy proposal、scar/edema proposal、soft-ROI refiner 和 loss components 都必须在 forward/loss 中被调用，并导出非空 runtime evidence。
2. Segmentation context as evidence, not sole answer：nnU-Net/强分割模型以 logits/probabilities/components/uncertainty/anatomy context 进入 proposal/refiner/arbitration；final output 不能绕过 SRR/proposal/refiner 直接等于 nnU-Net，除非 explicit safety fallback 被触发并记录 reason。
3. Branch/evidence arbitration：仲裁器必须输出 per-class/per-case 的 segmentation_weight、srr_retrieval_weight、proposal_weight、refiner_weight、chosen_source 或等价字段。SRR 分支必须能在 synthetic known-error / high-uncertainty 区域被采用；分割分支必须能在 SRR 证据低质时被采用。
4. Decode/gate consistency：如果 explicit fallback、gate/refiner mask 关闭或仲裁选择纯分割分支，final labels 必须精确等于分割分支；不允许 gate 近零但 pathology-aware decode 仍大量改标签。所有 label delta 都必须能追溯到显式的 SRR/proposal/refiner/arbitration mask。
5. Loss/refiner centrality：loss function 必须显式包含 SRR retrieval/proposal/refiner 相关项，而不是只保留分割分支 DiceCE。必须导出每一项的非空数值、是否参与梯度、one-step update sanity 或 synthetic backward check。
6. Refiner as mechanism：local refiner 必须是 bounded soft-ROI correction，不是 full-volume residual。必须导出 scar/edema crop ratio、residual magnitude、proposal recall/precision proxy、component/remote-FP proxy。
7. No-T2 edema safety：no-T2 case 中 edema proposal、edema refiner、edema loss、final decode、export 全链路安全；no-T2 myocardium 不能作为 edema negative。
8. Strict validation：strict validator 必须 fail closed 于 claim-only packet、missing architecture trace、hidden-decode-delta packet、SRR-zero-contribution packet、loss-components-empty packet、no-T2 edema unsafe packet、full-volume-refiner packet。

结果写入 `results/20260705_srr_v3_m6_myops_diagram_faithful_repair/`，必须写齐：

`result.md`
`srr_v3_fidelity_contract.md`
`architecture_component_trace.csv`
`m4_failure_mapping.csv`
`segmentation_context_interface_sanity.csv`
`retrieval_bank_runtime_sanity.csv`
`anatomy_proposal_sanity.csv`
`branch_arbitration_sanity.csv`
`decode_gate_consistency_sanity.csv`
`loss_refiner_component_sanity.csv`
`refiner_roi_component_sanity.csv`
`no_t2_safety_sanity.csv`
`strict_validator_report.md`
`unit_test_report.md`
`completion_check.md`
`review_request.md`
`MANIFEST.md`

`completion_check.md` 只能写 `M6_READY_FOR_REVIEW`、`M6_NEEDS_REVISION` 或 `M6_NEEDS_EVIDENCE`。不能 mark ready 的情况包括：没有 `srr_v3_fidelity_contract.md`；`architecture_component_trace.csv` 没有逐项覆盖图中模块；SRR retrieval/proposal/refiner 在 runtime evidence 中全为空或未调用；segmentation context 绕过 SRR 直接成为最终输出且没有 explicit fallback reason；gate/refiner mask 关闭时 final labels 仍改变；loss/refiner 只有自然语言说明没有数值/梯度/one-step evidence；local refiner 是 full-volume；no-T2 edema 出现非零 decode；strict validator 不能 fail closed known-bad packet。

完成后用 `git add -f` 提交 M6 packet 供 reviewer 审阅所需的全部轻量文件和必要 helper/source/config；不要提交 checkpoints、NIfTI predictions、upload packages、大日志、raw data、敏感信息、environment dumps 或整个 runtime result tree；不要 push，由用户手动 push。不要写 `review.md`，不要批准自己，不要启动 M7。M6 是否给 `M6_AUDITED_GO` 由独立 reviewer 决定。
```

## M6 reviewer

```text
只读审阅 `results/20260705_srr_v3_m6_myops_diagram_faithful_repair/`。请读取本文件的 M6 executor、`prompts/MILESTONE_REVIEW_PROTOCOL.md`、`prompts/HANDOFF_GATE_POLICY.md`、`prompts/GPT_HARD_GATE_PROMPT.md`、M4 review，以及 M6 result directory。不要补 executor 缺失文件，不要改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动 M7。

重点检查 M6 是否回到 v2/v2.5/v3 图中的完整 SRR-MyoPS 路线，而不是把 SRR 抽象成普通后处理，也不是把 nnU-Net/分割模型当成唯一主角。必须审阅：

1. `srr_v3_fidelity_contract.md` 与 `architecture_component_trace.csv` 是否逐项覆盖图中模块：inputs/availability、modality-specific stems、strong encoder、segmentation context interface、semantic retrieval bank、shared/private/interaction dictionaries、real train/OOF prototypes、anatomy decoder、scar/edema proposal、soft-ROI refinement、training objectives。
2. `segmentation_context_interface_sanity.csv` 是否证明 nnU-Net/强分割模型以 logits/probabilities/hard prediction/components/uncertainty/anatomy context 进入 proposal/refiner/arbitration，而不是绕过 SRR 直接成为最终答案。
3. `retrieval_bank_runtime_sanity.csv` 是否证明 retrieval bank、router、dictionary slot usage、prototype source、anatomy/scar/edema routed features 在 runtime 中非空、可追踪。
4. `anatomy_proposal_sanity.csv` 是否证明 `P_union/P_LV/P_RV`、anatomy prior/distance/uncertainty gate、scar/edema proposal decoder 都产生有效证据。
5. `branch_arbitration_sanity.csv` 是否导出 segmentation_weight、srr_retrieval_weight、proposal_weight、refiner_weight、chosen_source 或等价字段，并证明 SRR 在 correction-positive sanity 中能被采用，分割分支在 SRR 证据低质时也能被采用。
6. `decode_gate_consistency_sanity.csv` 是否证明 explicit fallback、gate/refiner mask 关闭或仲裁选择纯分割分支时 final labels 精确等于分割分支；不能允许 hidden decode delta。
7. `loss_refiner_component_sanity.csv` 是否有非空 loss component 数值、梯度或 one-step update sanity，覆盖 SRR retrieval/proposal/refiner、分割分支保持、仲裁一致性、bounded correction、component/remote-FP、no-T2 edema、local refiner ROI、dictionary/prototype regularization。
8. `refiner_roi_component_sanity.csv` 是否证明 local refiner 是 bounded soft-ROI correction，不是 full-volume residual，并导出 scar/edema crop ratio、residual magnitude、proposal recall/precision proxy、component/remote-FP proxy。
9. `no_t2_safety_sanity.csv` 是否证明 no-T2 edema 在 proposal、loss、refiner、final decode、export 上全链路安全，且 no-T2 myocardium 没有被当作 edema negative。
10. `strict_validator_report.md` 和 `unit_test_report.md` 是否 fail closed 于 claim-only、missing architecture trace、hidden-decode-delta、SRR-zero-contribution、loss-components-empty、no-T2 unsafe、full-volume-refiner 等 known-bad cases。

如果图中关键模块没有 runtime evidence，或者 SRR retrieval/proposal/refiner 全为空，或者 segmentation context 绕过 SRR 直接成为最终输出，或者 gate/refiner mask 关闭时 final labels 仍改变，或者 loss/refiner 只有自然语言说明没有数值/梯度/one-step evidence，或者 no-T2 edema 不安全，decision 必须是 `M6_AUDITED_NEEDS_REVISION` 或 `M6_AUDITED_NEEDS_EVIDENCE`。最后只写 `results/20260705_srr_v3_m6_myops_diagram_faithful_repair/review.md`，decision 只能是 `M6_AUDITED_GO`、`M6_AUDITED_NEEDS_REVISION` 或 `M6_AUDITED_NEEDS_EVIDENCE`。完成后 `git add -f review.md` 并 commit；不要 push，由用户手动 push。
```
