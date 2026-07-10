# 病灶 proposal

> 历史快照：M08。本页只保存从 `TODO.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

### 1.3 Prototype / negative memory：有真实 train/OOF fitting，但不是我们想象中的强 memory bank

代码里有 prototype bank，不是完全假的。`build_prototype_bank_from_labeled_features` 会从 train/runtime features 中提取 scar positive/negative、edema positive/negative，并且明确限制 edema positive 和 safe-negative 只来自 T2-present 样本，no-T2 myocardium 不进入 edema negative。 它也区分 normal myocardium、blood pool、outside myocardium、hard FP、artifact 等 negative 类别。

训练脚本确实会在正式 model 上 fit and load runtime prototype bank：它选择 T2 edema-positive cases、lesion cases 或其他 train cases，取 `_evidence_features`，调用 `build_prototype_bank_from_labeled_features`，再把 scar/edema prototypes load 到 model dictionary。

但这里有一个很大的 fidelity 问题：`ProposalDictionary` 里的 positive/negative prototypes 是 `register_buffer`，不是 `nn.Parameter`；`load_prototype_bank` 只是把 fitted prototype 拷贝进去。 也就是说，prototype vectors 本身不是一个在线可训练 memory bank。它们更像初始化后固定的 class anchors。后续 prototype margin loss 主要推动 feature/embedding 去适配这些固定 prototypes，而不是让 prototype memory 自身持续学习。`prototype_parameters()` 试图跟踪 prototype 相关参数，但由于 positive/negative 是 buffer，不是 parameter，它真正能跟踪更新的主要是 embedding/conv_score 一类参数。

所以我会这样定性：**prototype bank 有，但不是强 memory/prototype learning；hard-negative memory 有类别设计和 replay 入口，但不是完整的 iterative hard-negative mining system。**

---

### 1.5 Proposal：有公式、有 logits、有 prototype similarity，但可能被 anchor/context 和保守 gate 稀释

`ProposalDictionary.forward` 的 proposal 不是空壳。它计算 positive similarity、negative similarity、memory negative similarity，然后组合 learned conv score、evidence logits、anchor evidence、component evidence、anatomy prior。核心形式接近：

$$
\begin{aligned}
z_{\text{proposal}} ={}&
r
+ 2.5(s_{+}-s_{-})
+ 0.45z_{\text{evidence}} \\
&+ 0.35\,\mathrm{logit}(a_{\text{anchor}})
+ 0.30\,\mathrm{logit}(c_{\text{component}})
+ 0.20 A_{\text{anatomy}} .
\end{aligned}
$$

代码上就是 `conv + 2.5*(pos_sim - neg_sim) + evidence_logits + anchor/component/anatomy terms`，并且 edema no-T2 直接 block。

问题是，proposal heavily consumes nnU-Net anchor/component evidence。它不是纯 SRR image evidence proposal。nnU-Net 在这里不仅是 context，它直接进入 proposal logits 的重要项。这样做安全，但容易让 SRR 成为“围绕 anchor 小幅修补”的系统，而不是主角。
