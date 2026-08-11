# Planner repair — round 001 reentry 008 — Verifier

本轮只修 Verifier。不得修改 implementation、冻结合同或 Requirement Ledger，不得重新引入已废弃的 moving-SHA / immutable-transaction 阻断逻辑。

## Blocking requirement

`REQ_LOSS_001` 明确要求每项损失按自身 eligible rows/voxels 归一化，no-T2 行不得稀释 edema-exclusive loss。

Planner 独立代码审阅发现，当前 `binary_dice_focal` 与 `binary_dice_bce` 的 Dice 部分先把 no-T2 行通过全零 mask 变成 `dice_value=0`，随后仍对完整 batch 做 `.mean()`。因此在 mixed batch 中，加入任意 no-T2 行会机械降低 T2-present edema Dice / injury Dice，即使 T2-present tensor 完全不变。当前 Verifier 的 mixed-T2/no-T2 probe 只检查 class-4 competition、edema-owned call/gradient isolation；loss semantic oracle 也未验证这种 eligible-row invariance。

另外，`care_ase_loss` 的 conditional final competition 分别计算 T2-present 和 no-T2 子组后直接对两个 subgroup loss 等权平均。对于不等规模 mixed batch，这不是按 eligible row/voxel 数量归一化。

## Required verifier repair

1. 新增独立于 implementation loss helper 的 eligible-normalization oracle。至少构造一个真实/确定性 mixed batch，使 T2-present 行保持完全相同，并比较：
   - 仅 T2-present 行；
   - 同一 T2-present 行 + 1 个 no-T2 行；
   - 同一 T2-present 行 + 多个 no-T2 行。

   对 `edema_binary_dice_focal` 和 `injury_dice_bce`，新增 no-T2 行不得改变该 loss 的 eligible-row Dice 部分或总未加权值，允许的浮点容差只能用于数值累积误差。

2. 对 `conditional_final_dice_ce` 增加不等组大小的 reference oracle，例如 1 个 T2-present + 3 个 no-T2；reference 必须按冻结合同的 eligible rows/voxels 语义独立计算，禁止把两个 subgroup mean 固定 1:1 平均。

3. 增加实际执行的 known-bad / mutation，至少覆盖：
   - edema/injury Dice 对完整 batch `.mean()` 导致 no-T2 dilution；
   - conditional final competition 对 T2-present/no-T2 subgroup 固定等权平均。
   两类 mutation 都必须 fail closed，并绑定 `REQ_LOSS_001`。

4. 保留现有 no-T2 子图零调用、零梯度、class-4 完全移出 competition 的检查；不要用新的 loss oracle 替换这些检查。

5. 当前 Stable Review Snapshot 已明确 supersede 旧 runtime-manifest moving-target transaction gate。旧 transaction receipt 的历史 failures 不得重新升级为 blocking；receipt/state-only 变化只允许轻量验证。

## Required evidence

返回 Verifier commit、更新后的 verifier semantic fingerprint，以及：

- eligible-row invariance probe PASS；
- unequal mixed-batch conditional final loss reference PASS；
- 两类新 mutation 均被拒绝；
- 现有语义 probes 无回归。

不要运行 formal training、outer、Docker 或 upload。