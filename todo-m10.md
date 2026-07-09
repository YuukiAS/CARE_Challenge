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

## 2. nnU-Net 角色问题

M9 已经把 formal M9 variants 改成 `SRR_MAIN_NOT_ANCHOR_RESIDUAL`，代码里 M9 path 的 `final_logits = srr_logits`，不再是 M8 的 `nnunet_anchor_logits + bounded_delta`。这是正确方向。

但 nnU-Net 仍深度进入 SRR：

- `anchor_features` 仍进入 anatomy prior；
- proposal dictionary 仍使用 `anchor_map` 和 `component_map`；
- segmentation context 仍来自 nnU-Net anchor probabilities / hard prediction / component masks；
- loss 里仍有 anchor preservation / correction opportunity 相关项；
- 评估仍以 M8 nnU-Net anchor 为主要对照。

这不一定错，nnU-Net 可以作为 control / context / teacher / safety source，但 M10 必须继续防止它成为隐式主角。M10 中每个 formal candidate 必须报告：

```text
nnunet_role
anchor_feature_usage
anchor_context_weight
final_output_base
final_label_delta_vs_anchor_control
```

并且必须有一个 formal ablation：`SRR_MAIN_NO_NNUNET_CONTEXT` 或等价版本，用来确认 SRR 是否能在没有 nnU-Net context 的情况下形成基本 lesion evidence。这个 ablation 可以不作为 final candidate，但必须作为 scientific control。

## 3. Dictionary / representer 问题

### 3.1 True-BR2 骨架存在，但还没有证明 representer 的医学价值

当前 `SRRV2MyoPSUNet` / `SRRProposeRefineMyoPS` 的方向比 Lite 正确：它有真正的 modality-private encoders，`ScaleRetrieval` 接收 per-modality features，而不是旧 Lite 里 `[fused, fused, fused]` 的伪模态路径。这点应保留。

但是，当前 representer 更像 per-scale multi-slot MoE feature expert，而不是已经形成医学可解释 lesion representer 的 dictionary。现有 evidence 主要证明“slot 被使用过”，没有证明“某类 slot 对 scar/edema final label 有因果贡献”。M10 不能继续只报告 slot usage；必须做可解释和 causal 的 representer audit。

### 3.2 Router 仍偏 case/global，不够 lesion-local

`RetrievalRouter` 主要基于 fused feature global mean、availability、anchor summary 决定 expert weights。这更适合“这个 case 应该看哪类 source”，不适合“这个局部心肌区域是不是 edema/scar/hard FP”。

M10 需要把 dictionary query 从 case-level/global 改成 lesion-conditioned / spatial-conditioned，至少包括：

```text
local proposal score
local anatomy distance / p_union / p_lv / p_rv
local T2 intensity/statistics when T2-present
anchor uncertainty or teacher uncertainty, if used
component / remote-FP flags, if used
availability pattern
```

可以先做 lightweight spatial router，不一定一次性重写全模型；但 M10 必须避免继续把 dictionary 证明停留在全局 gate usage。

### 3.3 Pattern-SIP 目前更像后处理报告，不是真正优化目标

M9 loss 里加入了 `loss_pattern_sip_integrativeness` key，但代码中它与 `dict_loss` 绑定，仍主要是 semantic retrieval regularization 的别名，而不是真正的 group-conditioned integrativeness objective。M9 aggregator 生成 `m9_pattern_sip_usage_by_group.csv`、`m9_integrativeness_gamma_soft.csv` 等，但这更像 post-hoc summary，而不是训练时显式优化 `u_{task,slot,group}`。

M10 如果继续以 dictionary 为核心卖点，必须真正实现 pattern-conditioned SIP：

```text
u_{task,slot,availability_group}
u_{task,slot,center_or_style_group}
u_{task,slot,hard_subgroup}
```

并将其纳入 loss，而不是仅在 aggregation 阶段汇总。

### 3.4 Invalid-slot mask 证据仍偏弱

M9 aggregator 在 `m9_dictionary_invalid_slot_mask_report.csv` 中写 `invalid_slot_active_count = 0`，但这看起来更像根据 valid fraction 的汇总假设，而不是逐 step / 逐 case 检查 invalid slot weight 是否真的为 0。M10 前必须加强此项：对每个 batch、每个 task、每个 slot，检查 missing modality private/interaction slot 的 gate weight 是否为 0，并将 max invalid weight、mean invalid weight 写入 evidence。

## 4. Prototype / memory 问题

### 4.1 ProposalDictionary 仍以 buffer prototypes 为主

`ProposalDictionary` 里的 positive / negative prototypes 仍是 `register_buffer`，不是 `nn.Parameter`。`load_prototype_bank` 只是把 train/OOF fitted bank 拷贝进去。这样做比 deterministic axis fallback 强，但不等于在线可学习 prototype memory。

### 4.2 SafePrototypeMemoryBank 目前像孤立 helper

M9 新增了 `src/care_myocardium/models/srr_dictionary_memory.py`，实现了安全 EMA prototype memory，并在 update 时拒绝 no-T2 edema negative。这是正确方向。但目前需要确认它是否被正式训练链路实际调用。初步代码搜索只看到定义文件本身，未看到明确接入 `ProposalDictionary` 或 training loop 的调用路径。如果 M9 follow-up 后仍确认没有接入，则 M10 必须把 memory 真正连到 proposal dictionary 或 training loop。

M10 的 prototype/memory 目标不应只是“summary JSON 有 counts”，而应是：

```text
memory source -> proposal similarity -> proposal logits -> refiner logits -> final labels
```

每一步都要有可追踪 evidence。

### 4.3 Hard-negative replay 还没有形成闭环

当前 hard-negative memory 主要来自旧 mined CSV 或 prototype fitting 统计，不是 “当前模型误报 -> 安全过滤 -> 回灌 memory -> 再训练” 的闭环。M10 如果继续走 dictionary/prototype，必须加入至少一轮 bounded hard-negative refresh：

1. 用当前 candidate 在 same-split train/val proxy 上找 remote FP / component-burden FP；
2. 过滤 no-T2 unsafe edema negative；
3. 写入 memory ledger；
4. 重新训练或 fine-tune bounded steps；
5. 比较 refresh 前后 proposal/refiner/final label。

## 5. Refiner 问题

### 5.1 scar / edema refiner 的结构差异已经有，但科学证据不足

代码里 scar 和 edema 的 refiner 确实不同：scar 是小 ROI / LGE-oriented / tighter crop；edema 是大 ROI / T2-conditioned / larger crop / no-T2 blocking。这符合示意图方向。

但是，M9 的 refiner evidence 仍然主要来自 ROI coverage、component rows、same-split metrics等聚合表。`m9_refiner_causal_effect.csv` 在 aggregator 中本质上由 component rows 写出，并不是真正的 refiner-on/off causal ablation。

M10 必须做真实 toggles：

```text
refiner_off
proposal_only
scar_refiner_only
edema_refiner_only
both_refiners_on
```

每个 toggle 都需要同一 checkpoint、同一 eval cases、同一 decode rule 的 final-label delta、Dice、HD95、remote-FP、component count。不能再把普通 component metric 表命名为 causal effect。

### 5.2 Scar 与 edema 应分开优化目标

scar 是 focal / small ROI / high precision / HD95 / remote-FP 问题；edema 是 T2-present / larger ROI / recall+HD95 / CenterB-CenterC 问题。M10 不应再用一个统一 composite mean Dice 统治两者。需要两个独立门：

```text
scar_gate: scar Dice non-worse + HD95 non-worse + remote-FP lower or non-worse
edema_gate: T2-present edema-positive Dice/HD95/component improvement + no-T2 zero edema
```

只有同时满足或至少明确 trade-off，才允许 route candidate 进入下一步。

## 6. Loss / training 问题

### 6.1 M8 的 loss wiring bug 已修，但 M9 loss 仍可能是“名义丰富，优化不充分”

M9 已修复 `weights=collect_expanded_loss_weights(args)` 的传递问题。但新增的若干 loss key 仍可能只是 alias 或弱代理。例如 `loss_pattern_sip_integrativeness` 与 `dict_loss` 绑定，`loss_memory_bank_update_or_alignment` 与 `loss_proto` 绑定，Cine loss 当前为零占位。

M10 需要区分：

```text
real_optimized_loss
alias_loss
diagnostic_metric_only
placeholder_zero_loss
```

并写入 `m10_loss_component_contract.csv`。任何 placeholder loss 不能作为实现完成证据。

### 6.2 Checkpoint selection 仍不够彻底

M9 post-hoc metric selection 比 M8 的 patch-loss-only 更好，但训练过程的 `checkpoint_best` 仍可能先由 patch loss 保存，然后 aggregator 只在已有 checkpoint outputs 中选择。M10 应该在 scheduled checkpoints 上做 metric-facing full-case or bounded-full-volume eval，并按 scar/edema hard gates 保存 best，而不是只在训练后从 `checkpoint_best` / `checkpoint_final` 中补救选择。

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

## 8. Cine 分支问题

### 8.1 M9 Cine 有进步，但仍是 local proxy

M9 Cine 已经不只是下载 weight 或 frame0-only。它有 local temporal final-output prediction、non-reference frame、ANTsPy SyNOnly / Demons fallback、local Dice delta。这是比 M8 更实在的进展。

但它仍不是完整 Cine route：

- final output 是 deterministic temporal union compact-label proxy；
- registration 是 classical registration，不是训练出的 temporal model；
- CineMA predictions 是 frame-wise anatomy proxy，不是项目自己的 final temporal segmenter；
- 没有 hosted metric；
- 没有验证 temporal dictionary 对 learned model 的训练贡献；
- 没有明确处理 class label space 与 challenge metric 的完全一致性。

### 8.2 Cine 不能再 optional，但也不能拿来救 MyoPS

Cine 是 secondary line，但必须推进。M10 可以选择把 Cine 单独作为主任务，但不能让 Cine proxy 结果给 MyoPS dictionary 背书。

若 M10 选择 Cine，应目标化为：

```text
M10_CINE_TEMPORAL_MODEL_NOT_PROXY
```

最低要求：

1. frame-wise backbone / adapter 明确 provenance；
2. non-reference frames 进入 feature or prediction aggregation；
3. learned or calibrated temporal aggregation，而非简单 union；
4. final compact-label outputs；
5. frame0 control vs temporal model same-subset metrics；
6. geometry sanity / registration failure matrix；
7. hosted metric caveat。

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

### 10.3 若 MyoPS dictionary route 连续失败但 Cine proxy有正信号

可以规划：

```text
M10_B: Cine temporal model route
```

这不是 optional supplement，而是 secondary line 的正式实现。目标是从 deterministic temporal union proxy 升级为 learned/calibrated temporal model，并以 frame0 vs temporal model 的 same-subset metrics 审查。

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
