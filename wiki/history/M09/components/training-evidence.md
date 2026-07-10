# 训练证据与指标

## 历史分析原文迁移

# TODO M10：M9 follow-up 期间的路线级代码审计与下一轮规划

本文档记录在 M9 follow-up 执行期间，对当前 CARE / SRR-v3 / Cine 代码与结果包的横向审计。它不是 M10 prompt，也不是 route promotion。当前结论必须等 `prompts/shared/M9_followup_evidence_reconciliation_reaudit.md` 执行并独立 re-audit 后才能用于正式 M10 设计。

## 0. 当前总判断

M9 不能直接进入 M10。当前独立 review 是 `M9_AUDITED_NEEDS_REVISION`，原因不是 Slurm 仍在跑，而是 evidence packet 内部不一致：`completion_check.md` 和 `result.md` 声称 `M9_READY_FOR_REVIEW`，但核心 tracked evidence 里仍有 `PENDING_RUNTIME`、`PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE`、`PARTIAL_ONE_BATCH_PROTOTYPE_EVIDENCE_FORMAL_TRAINING_RUNNING` 等 stale 状态。这个问题必须通过 M9 follow-up 修复 validator 和证据文件后再决定 M10。

科学方向上，M9 的 no-promotion 是有一定证据的。三个 formal SRR-main candidates 都明显低于 tracked M8 nnU-Net anchor：`m9_srr_main_true_br2_pattern_sip`、`m9_srr_main_lesion_proposal_memory`、`m9_srr_main_t2_edema_recall_focus` 的 mean Dice delta 均为负，HD95 和 remote-FP 也更差。训练也不是 smoke：M9 有三个 formal SRR-main candidate 各自超过 7200 train-loop seconds。但是，这些结果仍不能作为“SRR dictionary 路线失败”的最终科学结论，因为 M9 仍存在一批实现与证据缺陷，尤其是 causal ablation、Pattern-SIP、prototype memory、refiner causal effect、Cine temporal output 的真实性不足。

因此当前状态应写作：

```text
M9 executor scientific direction: NO_PROMOTION_DIAGNOSTIC_ONLY, directionally supported
M9 audited packet state: NEEDS_REVISION
M10 status: BLOCKED_UNTIL_M9_FOLLOWUP_REAUDIT
SRR-v3 route status: NOT_PROMOTED, NOT_SCIENTIFICALLY_DISPROVEN
```

## 1. 协议和证据层问题

### 1.1 M9 packet ready 状态与证据文件冲突

`m9_dictionary_fidelity_matrix.csv` 仍有 `PENDING_RUNTIME`，包括 true-BR2 runtime slot usage、invalid-slot mask runtime、final metric causal effect。与此同时，`completion_check.md` 和 `result.md` 声称 ready。这是当前最直接 blocker。

M9 follow-up 必须做两件事：如果 runtime evidence 已经存在，就将这些 pending rows 改成 runtime-derived status，并提供明确 evidence path；如果 runtime evidence 不存在，就把 completion 改为 `M9_FOLLOWUP_NEEDS_EVIDENCE`，不能继续 ready。

### 1.2 Validator 不是 fail-closed

当前 M9 validator 对 ready packet 的 pending 状态扫描不充分。它主要扫描 top-level Markdown，不能可靠拒绝 required CSV/JSON 内的 unresolved 状态。M9 follow-up prompt 已经要求修复这一点：validator 必须扫描 Markdown、CSV、JSON，并且新增 stale-pending known-bad self-tests。

M10 前置门槛：任何 M10 prompt 之前，必须确认 M9 follow-up reviewer 判定 validator 已能 fail closed。

### 6.3 Patch-based training 可能限制 lesion formation

当前训练以 patch sampling 为主，batch size 小，foreground/hard-negative oversampling 虽有设计，但 final full-volume behavior 很容易出现 component explosion / remote FP / HD95 失控。M10 如继续 MyoPS，应考虑：

```text
larger context patch or two-stage proposal crop
full-volume calibration pass
post-hoc threshold calibration per pathology using train/val split only
component-aware decode not based on GT
```

## 7. Metrics / aggregation 问题

### 7.1 M9 metrics 负面，且问题不只在 edema

M8 主要是 scar 小涨、edema 变差；M9 SRR-main 反而 scar 和 edema 都显著低于 anchor。说明从 anchor-residual 改成 SRR-main 后，模型没有形成足够稳定的 segmentation basis。当前不是简单调 threshold 能解决的问题。

### 7.2 Aggregator 的一些 evidence 文件名称过强

`m9_ablation_matrix.csv` 当前由 checkpoint selection rows 写出，不是实际 ablation matrix。`m9_refiner_causal_effect.csv` 当前由 component rows 写出，不是真正 refiner causal effect。这类文件名会误导 reviewer 和 GPT。M10 必须把 evidence 文件命名和实际内容对齐：如果只是 proxy summary，就叫 proxy；如果叫 causal effect，就必须是真 ablation。

### 7.3 Same-split anchor 对照需要保留，但不能变成主角

nnU-Net anchor 作为 same-split control 仍有必要，否则无法判断 SRR 是否带来增益。但 M10 中评价应包括：

```text
anchor_only_control
SRR_without_anchor_context
SRR_with_anchor_context
SRR_with_teacher_loss_only
SRR_with_safety_fallback_only
```

这能区分“SRR 自身是否有效”和“SRR 是否只是借用 anchor”。

## 9. M10 不应做什么

在 M9 follow-up re-audit 前，不要做：

```text
M10 training
fold expansion
validation packaging
hosted claim
route promotion
继续当前 M9 三个 SRR-main variants 盲目加长训练
只调 threshold / decode rule 试图救 M9
只扩大 dictionary slot 数量
只把 nnU-Net 重新放回 final logits base
只把 Cine temporal union proxy 当完整 Cine 模型
```

这些都会重复 M8/M9 的问题。

## 10. M10 的可能路线

M10 必须根据 M9 follow-up reviewer 结论选择。

### 10.1 若 M9 follow-up 仍是 NEEDS_REVISION / NEEDS_EVIDENCE

不写 M10。继续修 M9 packet、validator、aggregation、evidence naming。没有干净审计状态，不允许下一轮科学任务。

### 10.2 若 M9 follow-up 是 READY_NO_PROMOTION_DIAGNOSTIC_ONLY

这时可以承认：当前 `SRRProposeRefineMyoPS` 的 SRR-main dense segmentation route 不值得直接扩展。M10 不应继续同架构长训，而应 pivot。

优先候选：

```text
M10_A: Dictionary-led lesion proposal route
```

核心思想：把 dictionary 从 dense final segmentation 主干中剥离出来，先做高召回、低远端 FP 的 scar/edema lesion proposal engine，然后再接 pathology-specific refiner / selector。也就是说，dictionary 的主要卖点不是“直接输出完整 segmentation”，而是“在异质模态缺失下检索医学可解释 lesion evidence”。

M10_A 成功门：

```text
scar proposal lesion-wise recall improves or non-worse with lower remote-FP
T2-present edema proposal recall improves on CenterB/CenterC
no-T2 edema remains zero
refiner improves final label over proposal-only
SRR_without_anchor_context has nontrivial lesion signal
```

### 10.4 若 M9 follow-up 发现 evidence 缺失导致 M9 科学结论不可靠

规划：

```text
M10_BLOCKED_NEEDS_M9_EVIDENCE_REPAIR
```

不要强行解释负结果。

## 11. 我建议的 M10 优先级

如果 M9 follow-up 修复后仍然是 no-promotion，我建议 M10 先做 MyoPS 的 `Dictionary-led lesion proposal route`，而不是立即转 Cine。理由：dictionary 是项目核心卖点，M9 虽然 SRR-main dense route 失败，但还没有真正验证“dictionary 作为 lesion proposal engine”的版本。

M10 的最小任务不应该是三条大训练并跑 leaderboard，而应该是一个更干净的机制实验：

```text
M10_dictionary_proposal_engine_mechanism_test
```

包含三组：

```text
control: anchor_only + current M9 SRR-main negative reference
candidate_1: dictionary_proposal_without_anchor_context
candidate_2: dictionary_proposal_with_teacher_context_but_not_anchor_base
candidate_3: dictionary_proposal + pathology-specific refiner
```

每组必须有真实 ablation，不能再用 proxy matrix 冒充 causal effect。

## 12. M10 prompt 编写前必须确认的问题

1. M9 follow-up reviewer 是否已经给出 clean audited state？
2. M9 follow-up 是否修复了 stale CSV/JSON pending scan？
3. `SafePrototypeMemoryBank` 是否确实接入训练和 proposal dictionary？
4. `m9_ablation_matrix.csv` 和 `m9_refiner_causal_effect.csv` 是否仍是 proxy rename？
5. Pattern-SIP 是否仍只是 post-hoc usage summary？
6. M10 是继续 MyoPS dictionary，还是切到 Cine temporal model？
7. M10 是否允许新训练，预算多少？
8. nnU-Net 的角色是否继续限制为 control/context/teacher/safety，绝不作为 final-logit base？

在这些问题回答前，不应写可执行 M10 prompt。




可以解释相当一部分，但不能把 M9 的差表现全部归因于 packet/validator 问题。需要把问题分成三层：**会直接拉低模型性能的问题、使结果难以解释的问题、只影响审计可信度而不影响模型预测的问题**。

## 1. 哪些问题确实可以解释 M9 为什么表现差

最直接的信号是：M9 从 M8 的 anchor-residual 模式切换到了 SRR-main，三个候选的 scar 和 edema 都下降，而不再只是 edema 拖累。这说明问题不是某个阈值或单一 pathology，而是 **SRR 自身的 segmentation basis 还不够强**。M9 formal path 的确执行了 `final_logits = srr_logits`，nnU-Net 不再作为最终 logits 底座。 这次失败反而暴露出：过去 M8 的成绩很大程度上由 nnU-Net anchor 托住，去掉它以后，dictionary、proposal、refiner 和 anatomy trunk 没有独立撑起完整分割能力。

以下几项很可能是直接性能原因。

### SRR-main 去掉了 anchor 底座，但没有同时增强主干

M9 的三个 formal variants 主要修改了 dictionary config、prototype 数量、ROI kernel、crop margin 和 loss weights；底层 modality encoder 仍然是相对普通的多尺度 3D convolutional encoder，decoder 也是标准 U-Net-style decoder。

M8 时 nnU-Net 提供强 segmentation basis，SRR 只做残差。M9 把 nnU-Net 降级后，却没有给 SRR 一个与 nnU-Net 相当成熟的 backbone、训练策略、深监督、augmentation、normalization 和 full-resolution recipe。于是实验实际上近似比较：

```text
成熟 nnU-Net pipeline
vs
自定义 SRR research architecture + 较简化训练 pipeline
```

而不是只比较“有无 dictionary”。因此 M9 的落后不能全部归咎于 dictionary，它也包含主干和训练 recipe 的差距。

### Patch training 与 full-volume lesion topology 不匹配

M9 的主要困难是 remote FP、component explosion、HD95 和 CenterB/CenterC edema。这些都是 full-volume spatial topology 问题，而当前训练主要基于小 patch。局部 patch 内的 BCE/Dice/prototype margin 即使下降，也不能保证全图不会在远处生成多个 lesion islands。

这可以直接解释为什么训练 loss 稳定、optimizer steps 很多，但 full-case HD95 和 remote FP 仍显著恶化。

## 2. 哪些问题不能解释性能，只能解释为什么结论不可信

M9 packet 中残留 `PENDING_RUNTIME`、validator 没扫描 CSV/JSON、ready 状态与 evidence 冲突，这些问题**不会改变已经生成的模型预测**。它们不能解释 Dice 为什么低。

它们解释的是：

* 为什么 executor 没资格说 M9 已完整结束；
* 为什么我们不能确定所有 formal mechanisms 都有 runtime evidence；
* 为什么一些所谓 causal / fidelity 结论可能只是文件命名，而不是实际实验；
* 为什么下一轮不能直接根据 executor 总结设计 M10。

所以应区分：

```text
模型性能差：主要由 architecture / optimization / causal wiring 问题造成。
M9 无法被正式接受：由 evidence reconciliation / validator 问题造成。
```

## 3. 我现在认为 M9 最可能的根本原因

如果要压缩成一句话：

**M9 一次性把 nnU-Net 最终底座拿掉，却没有先证明 dictionary、proposal 和 refiner 中的任何一个模块能够独立形成稳定的 lesion evidence；同时若干所谓新机制仍是旧 loss 的别名或 post-hoc 报告。**

换句话说，M9 改动过大：

```text
anchor-residual → SRR-main
旧 dictionary → true-BR2
旧 regularizer → Pattern-SIP
fixed prototype → memory
普通 refiner → pathology-specific refiner
Cine proxy → temporal final output
```

这些变化同时发生，最终指标下降以后，我们不知道是：

* backbone 不够强；
* dictionary 无效；
* router 无效；
* prototype memory 没接上；
* proposal 失败；
* refiner 破坏 proposal；
* loss trade-off 错误；
* checkpoint 不合适；
* full-volume topology 失控。

这是典型的“模块都加了，但缺乏逐层可替代性验证”。因此下一轮必须按机制逐步验证，不能再一口气跑三个“大而全”的 variant。
