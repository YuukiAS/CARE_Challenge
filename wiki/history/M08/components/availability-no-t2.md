# 可用性与 no-T2 安全

## 历史分析原文迁移

### 1.1 Availability / no-T2 safety：基本落实，但只解决了安全，不解决性能

这部分实现相对扎实。`t2_masked_edema_loss` 只在 T2-present 样本上计算 edema dense supervision；如果 batch 里没有 T2-present，就返回零损失而不是把 no-T2 当 edema-negative。 模型 forward 里也多次把 no-T2 的 edema proposal/logits 设为强负值 `-20.0`，例如 proposal dictionary 和最终 arbitration 都有 no-T2 block。

这说明 Codex 没有完全偷懒成 naive zero-fill。但 no-T2 safety 只能防止一种错误：不要把缺 T2 当作 edema negative。它不能自动学会 CenterB/CenterC 的 T2-present edema。M8 的失败恰好在 T2-present/edema-positive/CenterB/CenterC 上，所以这不是 safety 没做，而是**edema 表示、proposal 和 refiner 没学出有效增益**。
