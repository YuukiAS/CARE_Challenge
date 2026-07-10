# loss 与优化目标

## 历史分析原文迁移

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
