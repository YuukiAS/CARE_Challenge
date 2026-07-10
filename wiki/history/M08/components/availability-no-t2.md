# 可用性与 no-T2 安全

> 历史快照：M08。本页只保存从 `TODO.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

# SRR-v3 / M8 实现审阅 TODO

---

## 1. 按模块逐项审计：哪些做到了，哪些没做到位

---

### 1.1 Availability / no-T2 safety：基本落实，但只解决了安全，不解决性能

这部分实现相对扎实。`t2_masked_edema_loss` 只在 T2-present 样本上计算 edema dense supervision；如果 batch 里没有 T2-present，就返回零损失而不是把 no-T2 当 edema-negative。 模型 forward 里也多次把 no-T2 的 edema proposal/logits 设为强负值 `-20.0`，例如 proposal dictionary 和最终 arbitration 都有 no-T2 block。

这说明 Codex 没有完全偷懒成 naive zero-fill。但 no-T2 safety 只能防止一种错误：不要把缺 T2 当作 edema negative。它不能自动学会 CenterB/CenterC 的 T2-present edema。M8 的失败恰好在 T2-present/edema-positive/CenterB/CenterC 上，所以这不是 safety 没做，而是**edema 表示、proposal 和 refiner 没学出有效增益**。

---

### 1.4 Anatomy prior：有实现，但仍然依赖内部 anatomy head 和 anchor context，没有被证明是强解剖定位器

`AnatomyDistanceROIPrior` 确实实现了 `p_union`、`p_lv`、`p_rv`、union/LV/RV distance、uncertainty、scar/edema soft gate，并且 no-T2 时把 edema gate 置零。 forward 里 proposal/refiner 都消费这些 anatomy context：scar/edema dictionary 接收 task-specific anatomy soft gate logits，refiner 接收 P_union/P_LV/P_RV、distance map、uncertainty 和 task gate channel。summary 里也把 anatomy distance ROI prior 标记为 runtime consumed。

但它的强度仍然有限。它不是 CineMA/CorSeg 这种外部强 anatomy teacher，也不是一个充分训练的独立 anatomy-first cascade。它是同一个小模型内部 anatomy head 预测出的 soft prior，再叠加 nnU-Net anchor uncertainty/context。这个设计比纯后处理强，但没有证明“anatomy prior 本身”解决了 lesion localization。M8 子组结果显示 edema-positive/T2-present 仍然下降，说明 anatomy prior 没有把 edema 支撑区域学好。

---

### 1.9 Checkpoint selection：实现与配置声明不一致

M8 config 里写了很具体的 checkpoint selection rule，例如 scar precision 变体写“best same-split scar Dice/HD95 guard”，T2 CenterC edema 变体写“best T2-present edema subgroup subject to no-T2 safety”。

但训练代码实际 checkpoint best 是根据 `val_patch_loss` 更新的。训练 loop 在 scheduled validation step 上跑 `validate_patch_loss`，然后如果 `val_loss < best_val` 就保存 `checkpoint_best.pt`。 这和 leaderboard-facing 的 Dice/HD95/hard subgroup guard 不是一回事。后面确实导出了 full-case eval，但 checkpoint selection 已经由 patch loss 决定了。

这也是一个关键偏差。我们要优化的是 scar/edema 的 final label、HD95、remote FP、component burden、CenterB/CenterC/T2-present hard subgroup，而不是 patch loss。Codex 这版在“训练选择机制”上没有完全按挑战赛目标实现。

---

## 2. 我对 Codex 当前实现的信任结论

我不认为 Codex 这次只是“随便写了个完全假的架构”。代码量和结构确实存在，M8 也不是纯烟测。它实现了不少 SRR-v3 图里的模块：availability-aware routing、多尺度 dictionary、prototype proposal、soft ROI refiner、anatomy distance prior、no-T2 safety、branch arbitration、训练日志、validator、自测。

但我也不认为它有资格说“路线没潜力”。原因是：它实现的是一个**过度保守、过度 anchor-centered、部分配置 miswired 的候选族**。尤其这几个问题非常关键：

第一，M8 的 loss-weight contract 很可能没有真正作用于 expanded loss。变体配置写得很漂亮，但 `srr_m6_expanded_total_loss` 没拿到这些 weights。这个问题不修，所有关于“loss 试过了”的结论都不可信。

第二，最终输出以 nnU-Net anchor 为中心：代码明确是 $z_{\text{final}}=z_{\text{anchor}}+\Delta z_{\text{branch}}$。这不是完全违背“anchor/context/safety”的规则，但已经太接近“nnU-Net 主角，SRR 修补”。

第三，checkpoint best 用 patch loss，而不是 hard subgroup Dice/HD95/remote-FP guard。这个选择会让训练目标和比赛目标错位。

第四，prototype bank 是一次性 fit 后作为 buffer 使用，不是强 memory bank；negative-space 有设计，但不是完整 iterative hard-negative mining。

第五，CineMA/registration 只是 diagnostic proxy，不是完整 Cine branch。

所以我会把当前状态定为：

**M8/M8 follow-up 不支持继续扩展当前候选；但不能作为 SRR-v3 科学路线失败证据。下一步必须是 implementation fidelity repair，而不是 route abandonment。**

---
