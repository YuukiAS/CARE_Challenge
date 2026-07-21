# CARE SRR Batch 5：Final-loss authority 与 oracle headroom 增补

Plan metadata:
- Type: binding addendum to `laneB_round04_active_srr_batch5_post_batch4_diagnostic_repair.md`
- Status: READY_FOR_CONTROLLER
- Planning review: not required
- Independent reviewer: not required
- Training: forbidden
- Backbone replacement/comparison: forbidden

## 一、为什么需要增补

Batch 5 原计划已经正确覆盖 checkpoint selection、正式 argmax decode、proposal/refiner 干预和 `production_correction_gate`。但 Batch 4 的 near-identity 结果还存在一个更上游的解释：当前总 loss 可能没有直接奖励最终 `outputs["logits"]` 修正 GT，反而通过 correction/residual magnitude penalty 鼓励修正趋近于零。

这比更换 U-Mamba、MedSAM、MedNeXt 或 nnU-Net 骨干更应该先查清。Batch 5 不比较骨干，也不改变模型权重。

本增补与以下机器合同共同生效：

```text
configs/srr_production/myops_batch5.yaml
prompts/tasks/20260721_srr_batch5_post_batch4_diagnostic_repair_executor_plan.yaml
```

若原 Batch 5 计划的 Batch 6 decision 枚举与本增补冲突，以更新后的 config、executor plan 和本增补为准。

## 二、新增 blocking 任务：final-loss authority audit

必须从正式训练 runner 的 `propref_loss` 解析实际调用的 loss、别名和有效权重，并读取：

```text
scripts/training/run_srr_propref_myops_fold0.py
src/care_myocardium/losses/srr_losses.py
```

必须回答：

1. 是否存在直接以 GT 监督最终 `outputs["logits"]` 的 scar/edema segmentation loss；
2. `production_correction_gate` 是否得到纠正 anchor 错误的任务梯度；
3. `loss_correction_opportunity` 连接的是 production gate，还是旧的 segmentation/arbitration path；
4. `loss_bounded_correction` 的正权重是否偏好 `correction -> 0`；
5. `loss_refiner_final_label_effect` 的正权重是奖励有效 refiner，还是惩罚 residual magnitude；
6. proposal/refiner/dictionary loss 到各模块和最终 production gate 的真实梯度路径。

允许 `backward()` 诊断，但：

```text
optimizer_steps = 0
optimizer.step() forbidden
parameter updates forbidden
checkpoint/parameter hashes must remain unchanged
```

必须输出：

```text
results/20260721_srr_batch5_post_batch4_diagnostic_repair/loss_authority_audit.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/loss_parameter_gradient_matrix.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/loss_directionality_audit.csv
```

每个 active loss 至少记录：resolved weight、source symbol、consumed output tensors、parameter-group gradient norm、是否直接监督 final pathology、以及优化方向 `repair | preserve | shrink | auxiliary`。

参数组至少包括：

```text
production_correction_gate
scar_refiner
edema_refiner
scar_dictionary
edema_dictionary
retrieval_router
```

## 三、新增 blocking 任务：oracle headroom

在同一 checkpoint、同一 44 cases、同一 argmax decode 下，对以下模式计算仅用于诊断的病例级 GT-aware best mode：

```text
anchor_identity_control
anchor_bounded_full
anchor_bounded_proposal_only
anchor_bounded_refiner_only
production_gate_open_bounded_control
```

输出：

```text
results/20260721_srr_batch5_post_batch4_diagnostic_repair/oracle_headroom.csv
```

至少包含：

```text
case_id
pathology
anchor_dice
best_mode
best_mode_dice
oracle_dice_gain
correctable_anchor_error_voxels
harmful_correction_voxels_avoided
diagnostic_only=true
deployable_candidate=false
```

该 oracle 只估计现有组件的可兑现上界，禁止把它变成 case-wise oracle ensemble、submission candidate 或 hosted claim。

## 四、更新后的唯一 Batch 6 方向

最终只能选择一个：

```text
B5_FINAL_OBJECTIVE_ALIGNMENT_BOTTLENECK
B5_OUTPUT_AUTHORITY_BOTTLENECK
B5_PROPOSAL_PRECISION_BOTTLENECK
B5_REFINER_EFFECTIVENESS_BOTTLENECK
B5_EVALUATION_SEMANTICS_ONLY_ISSUE
B5_INSUFFICIENT_MECHANISM_EVIDENCE
```

固定优先级：

1. 若 proposal/refiner/gate-open 的 oracle 平均增益至少 `+0.01`，full 仍接近 identity，且 production gate 缺少直接 final-pathology repair loss，或 active magnitude penalty 明确偏好零修正，选择 `B5_FINAL_OBJECTIVE_ALIGNMENT_BOTTLENECK`。
2. 若 loss 路径合理，但 gate-open 相对 full 的平均 positive-case Dice 至少改善 `+0.005`，选择 `B5_OUTPUT_AUTHORITY_BOTTLENECK`。
3. 若 proposal-only 无可用信号或 remote/component FP 明显恶化，选择 `B5_PROPOSAL_PRECISION_BOTTLENECK`。
4. 若 proposal-only 有信号，但 refiner-only/full 相对 proposal 平均下降至少 `0.002`，选择 `B5_REFINER_EFFECTIVENESS_BOTTLENECK`。
5. 若只有 selection/decode 修复改变结论，选择 `B5_EVALUATION_SEMANTICS_ONLY_ISSUE`。
6. 其余选择 `B5_INSUFFICIENT_MECHANISM_EVIDENCE`。

Batch 5 不得选择 backbone replacement，不得启动 Batch 6 训练。
