# Batch 9 暴露问题修复：Planner 决定

## 结论

本轮不接回 nnU-Net 作为模型主体，不加载其 logits、checkpoint 或预测，也不允许 baseline fallback。继续保留 `CAREMMReliableDistillResEnc` / CARE-MMRD 的三模态独立 stem、availability hard mask、anatomy/scar/edema 分头和可靠标签逻辑。当前唯一授权工作是修复 Batch 9 已经暴露的训练与验收缺陷，再按同一模型重新训练；这不是 Batch 10，也不是恢复旧 SRR 长链。

Batch 9 原终态只能说明当前实现不可用，不能作为干净的科学负结果。原因不是训练步数不足，而是以下一阶缺陷会直接造成损失尺度失真、continuation 塌缩、采样偏置、no-T2 推理越权和错误终态判断：

1. `masked_mean` 只除以病例数，没有除以有效体素数；BCE、consistency 和 feature distillation 随 patch 体素数放大。
2. direct 与 continuation 使用恒定学习率；warm-start continuation 仍以过高学习率训练，两个 seed 已出现空预测或巨量远端假阳性。
3. patch sampler 按 `edema -> scar -> anatomy` 固定优先级取第一个前景点，没有显式平衡 scar、edema、anatomy 与背景。
4. no-T2 仅把 edema logit 设为 `-20`，并不能保证 argmax 永远不输出 edema。
5. 正式训练没有真实周期性全验证、best-checkpoint 选择和训练中途退化证据。
6. known-bad 只是自报 `injected/rejected=true`；finalizer 对两个 seed 求平均后判 gate，掩盖单 seed 塌缩。
7. Controller/finalizer 的 terminal 字段存在硬编码，未由真实 Slurm accounting、aggregation 和 validator 动态生成。

## 唯一修复范围

保持模型 forward 和方法故事不变，只允许：

- 把 case mask 展开到 loss tensor 后按真实有效体素归一化；
- direct 使用多项式学习率衰减，continuation 使用更低的 warm-start 学习率和同类衰减；
- 改成显式类别平衡 patch sampler，并输出逐步采样 manifest；
- 在 inference/evaluation argmax 前对 no-T2 edema 类做不可竞争 hard mask；
- 每 25 epoch 对固定 44 例完整评价，保存并 reload 候选 checkpoint；
- 用真实注入测试替代自报 known-bad，并按每个 seed 独立判定空预测、Dice、HD95、remote FP 和 no-T2 安全；
- 让 finalizer 从真实 job accounting、聚合结果和 validator 输出生成终态。

不得引入 nnU-Net anchor、旧 SRR、BR2/SIP、prototype/memory、proposal/refiner、外部数据、外部权重、Cine、fold expansion 或上传。

## 执行顺序

先完成代码修复、真实单元测试和 fixed-case overfit。随后并行重跑两个 direct seed，各 500 epoch / 125000 optimizer steps，使用周期性验证选出的 checkpoint，而不是固定 epoch500。只有两个 seed 都没有 GT-positive 空预测、no-T2 edema 预测精确为零，且 scar 与 edema 均相对原 Batch 9 direct 同 seed 改善，才允许继续 matched moddrop / distillation。Continuation 从对应 direct selected checkpoint warm-start，100 epoch / 25000 steps，初始学习率固定为 direct 的十分之一。

若任一 continuation seed 出现某一病种相对 matched control 下降、GT-positive 空预测、no-T2 edema 非零或远端假阳性爆炸，蒸馏判失败，不得用跨 seed 平均掩盖。

## 状态边界

```text
task_key: 20260723_care_myops_batch9_exposed_issues_repair
status: READY_FOR_CONTROLLER
architecture_change: false
nnunet_in_model: forbidden
baseline_fallback: forbidden
batch10_authorized: false
```
