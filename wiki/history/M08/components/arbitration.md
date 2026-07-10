# 分支仲裁与最终输出

> 历史快照：M08。本页只保存从 `TODO.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

### 1.7 Branch arbitration / final output：这是当前最接近“nnU-Net 做主角”的地方

这部分是我最不满意的实现。代码里有 `BaselinePreservingResidualGate` 和 `BranchArbitrationGate`。最终形式本质上是：

$$
z_{\text{final}} =
z_{\text{anchor}} + \Delta z_{\text{branch}} ,
$$

其中 $z_{\text{anchor}}$ 是 nnU-Net anchor logits，$\Delta z_{\text{branch}}$ 是 SRR/proposal/refiner 的 bounded delta。`BranchArbitrationGate` 里明确先构造 bounded delta，然后 `final = anchor_logits + branch_delta`。 SRRProposeRefineMyoPS forward 里 M6/M8 变体最终选择的是 arbitration 的 `final_logits`，否则是 baseline gate。

这比“静默 fallback”好，因为它确实导出 branch weights、correction mask、proposal/refiner delta 等证据。但从路线精神看，这已经把 nnU-Net 放得太中心了。尤其 `BranchArbitrationGate` 的 gate 初始化是 closed-biased：`context_gate.weight` 初始化为 0，bias 为 `-1.2` 或 `-2.0`，也就是一开始就倾向小开口。 再加上 anchor preservation、bounded correction、patch loss selection，SRR 很容易永远只做很小的残差修补。这样得出“SRR 没潜力”是不公平的；更准确是：**当前实现把 SRR 放在 anchor 的笼子里，没证明它能独立形成 lesion mask。**

这直接触碰你说的底线：nnU-Net 不能是主角。当前 repo 规则也要求 SRR 不能退化为普通 nnU-Net 后处理或隐藏 identity。 当前实现不是普通后处理，但它仍然是“anchor-first residual correction”。下一轮必须把 nnU-Net 从 final decision 主体降级为 context/teacher/safety source。
