# 分支仲裁与最终输出

## 历史分析原文迁移

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
