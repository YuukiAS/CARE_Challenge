# 检索字典与表示槽

## 历史分析原文迁移

### 1.2 Modality encoder + retrieval dictionary：有实现，但不等于完整 SRR 语义检索系统

代码里确实有多尺度 shared/private/interaction dictionary。`dictionary_slot_config` 定义了 shared slots、LGE/T2/C0 private slots，以及 LGE-T2、LGE-C0、T2-C0 interaction slots；`GroupedExpertBank` 里这些 slot 都是 trainable conv expert；router 输入包含 pooled features、availability 和 nnU-Net anchor summary，并且会 mask invalid modality slots。

这部分说明“dictionary 骨架”是真有的，不是纯 CSV。但问题在于它目前更像一个 **MoE-style multi-slot fusion block**，而不是完全实现了我们图里的“semantic representation retrieval bank”。它的 semantic prior 是软正则；slot usage 有诊断；但是目前没有证明这些 slots 学到了稳定的、可解释的 lesion-forming representation，也没有证明禁用/启用 dictionary 会在最终 label 上产生预期差异。M8 review 只是说 architecture gap closure table 全部 closed with runtime evidence，但最后同一划分候选仍不能超过 anchor。

更重要的是，当前 route 评估没有做一个真正强的 causal ablation：例如 “same architecture without dictionary / without interaction / without semantic regularizer / without prototype memory / without refiner” 在同一 split、同一训练预算下逐项比较。这意味着我们现在只能说 dictionary 参与了 forward 和 training，不能说 dictionary 的科学价值被充分检验。
