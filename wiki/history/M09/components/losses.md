# loss 与优化目标

> 历史快照：M09。本页只保存从 `todo-m10.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

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

---

### 3.3 Pattern-SIP 目前更像后处理报告，不是真正优化目标

M9 loss 里加入了 `loss_pattern_sip_integrativeness` key，但代码中它与 `dict_loss` 绑定，仍主要是 semantic retrieval regularization 的别名，而不是真正的 group-conditioned integrativeness objective。M9 aggregator 生成 `m9_pattern_sip_usage_by_group.csv`、`m9_integrativeness_gamma_soft.csv` 等，但这更像 post-hoc summary，而不是训练时显式优化 `u_{task,slot,group}`。

M10 如果继续以 dictionary 为核心卖点，必须真正实现 pattern-conditioned SIP：

```text
u_{task,slot,availability_group}
u_{task,slot,center_or_style_group}
u_{task,slot,hard_subgroup}
```

并将其纳入 loss，而不是仅在 aggregation 阶段汇总。

---

### 5.2 Scar 与 edema 应分开优化目标

scar 是 focal / small ROI / high precision / HD95 / remote-FP 问题；edema 是 T2-present / larger ROI / recall+HD95 / CenterB-CenterC 问题。M10 不应再用一个统一 composite mean Dice 统治两者。需要两个独立门：

```text
scar_gate: scar Dice non-worse + HD95 non-worse + remote-FP lower or non-worse
edema_gate: T2-present edema-positive Dice/HD95/component improvement + no-T2 zero edema
```

只有同时满足或至少明确 trade-off，才允许 route candidate 进入下一步。

---

## 6. Loss / training 问题

---

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

---

### 6.2 Checkpoint selection 仍不够彻底

M9 post-hoc metric selection 比 M8 的 patch-loss-only 更好，但训练过程的 `checkpoint_best` 仍可能先由 patch loss 保存，然后 aggregator 只在已有 checkpoint outputs 中选择。M10 应该在 scheduled checkpoints 上做 metric-facing full-case or bounded-full-volume eval，并按 scar/edema hard gates 保存 best，而不是只在训练后从 `checkpoint_best` / `checkpoint_final` 中补救选择。

---

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
