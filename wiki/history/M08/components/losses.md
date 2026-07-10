# loss 与优化目标

## 历史分析原文迁移

### 1.8 Loss：有很多 loss，但 M8 变体 loss weight 可能严重 miswired

这是我这次最重要的代码发现之一。M8 的 `m8_variant_config_contract.json` 给每个 variant 定义了不同 loss weights，比如 `baseline_preservation`、`component_proposal`、`edema`、`proposal`、`prototype_margin`、`roi`、`roi_remote`、`scar`、`semantic_retrieval` 等。 不同变体也确实有不同配置，例如 scar precision 变体和 T2/CenterC edema 变体的 loss weights 明显不同。

训练脚本的 `apply_variant_config_contract` 会把这些 JSON 里的 loss weights 写进 `args.scar_weight`、`args.edema_weight`、`args.proposal_weight`、`args.margin_weight` 等。 但问题在于：M8 变体走的是 `srr_m6_expanded_total_loss` 路径，而 `propref_loss` 调用它时**没有把这些 args weights 传进去**。源码是：

`total, m6_metrics = srr_m6_expanded_total_loss(outputs, labels, availability, detach_metrics=detach_m6_metrics)`

也就是没有传 `weights=...`。 而 `srr_m6_expanded_total_loss` 里面如果没有传 weights，就用默认 component weights。

这意味着一个很严重的可能性：**M8 JSON 里那些看起来很精细的 loss-weight variant 设计，可能大部分没有真正作用到 expanded loss。** 这不是小问题。它会让三个变体的“配置差异”主要落在 model variant / encoder / dictionary config / sampler / threshold 上，而不是预期的 loss schedule 上。Codex 如果据此说“loss 也试了，没潜力”，这个结论我不接受。先修这个 wiring，再谈 loss 有没有用。
