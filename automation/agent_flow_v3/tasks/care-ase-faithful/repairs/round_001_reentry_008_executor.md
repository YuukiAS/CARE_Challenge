# Planner repair — round 001 reentry 008 — Executor

本轮只修 implementation。不得修改 Verifier、冻结合同或 Requirement Ledger；应在 Verifier 完成本轮独立 eligible-normalization oracle 后再按其公开失败标识修复。

## Blocking requirement

`REQ_LOSS_001` 与冻结合同第 9–10 节要求：每项 loss 按自身 eligible rows/voxels 归一化；no-T2 行的 edema-exclusive loss/gradient 为零，并且不得稀释 T2-present edema loss。

Planner 独立代码审阅发现两个实现问题：

### 1. Edema / injury Dice 被 no-T2 行稀释

当前 `src/care_myocardium/training/care_ase_trainer.py` 中：

- `binary_dice_focal(...)`
- `binary_dice_bce(...)`

都会对每一 batch row 先生成 `dice_values`，no-T2 行由于 `edema_valid=0` 得到 0，随后仍执行完整 batch 的 `.mean()`。因此在 T2-present 行完全不变时，仅加入 no-T2 行就会降低 edema dense / injury Dice contribution。

修复要求：Dice reduction 必须只在该 loss 的 eligible rows 上做平均。Eligibility 应由该 loss 的有效 mask 决定，而不是由整个 batch 大小决定。不要借修复之机改变冻结合同未规定的科学语义；特别是 T2-present 但 GT pathology 为空的行仍按当前既有 Dice 语义处理，只需排除真正 ineligible 的 no-T2 rows。

### 2. Conditional final competition 对两个条件子组固定等权

当前 `care_ase_loss(...)` 分别得到 T2-present 六类 loss 与 no-T2 五类 loss 后，把两个 subgroup scalar 放入 `final_terms`，最后直接 `torch.stack(final_terms).mean()`。当 mixed batch 中两个条件组大小不同，这相当于无条件 1:1 加权，违反按 eligible rows/voxels 归一化的合同语义。

修复要求：T2-present / no-T2 仍必须使用各自合法类别集合，但合并成一个 final competition 时必须显式按实际 eligible row/voxel 计数归一化，而不是固定 subgroup 等权。CE 与 Dice 可分别采用与其统计对象一致的 eligible voxel / eligible row 归一化，然后组成同一个 conditional final DiceCE；不要增加新的 loss 权重或阈值。

## Regression requirements

修复后必须满足 Verifier 新增的独立 oracle：

1. 固定同一 T2-present tensor，添加 1 个或多个 no-T2 rows，`edema_binary_dice_focal` 与 `injury_dice_bce` 不得因 ineligible rows 改变；
2. 1 个 T2-present + 3 个 no-T2 的 final competition 必须匹配独立 eligible-count reference；
3. no-T2 edema-owned module call count、edema-exclusive parameter gradient 仍严格为 0；
4. class 4 仍完全移出 no-T2 softmax/Dice/argmax competition；
5. 所有 loss sensitive reductions 继续 FP32；
6. 不得通过 test-aware branch、fixture ID、Verifier flag 或特殊输出绕过 oracle。

只运行必要的 zero-credit regression / runtime probe；不得 formal training、outer、Docker、upload 或 develop->main。