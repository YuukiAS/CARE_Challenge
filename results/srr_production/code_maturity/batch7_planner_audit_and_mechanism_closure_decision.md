# Batch 7 Planner 审计与机制闭环修复决定

## 总体判断

Batch 7 的正式 300 步训练确实完成，并得到 edema 正例 Dice `+0.0054302188`、scar 正例 Dice `-0.0048258512`、平均 `+0.0003021838`。这证明当前联合模型没有达到继续训练门槛，但不能据此判定完整 SRR 思想失败，因为终态最关键的组件干预并未真实执行，部分 dictionary 和 discovery 实现也没有满足 Planner 合同。

当前状态应改为：

```text
BATCH7_OPERATIONALLY_RAN_BUT_MECHANISM_CLOSURE_INVALID_NEEDS_SAME_SCOPE_REPAIR
```

## 已确认的阻断问题

### 1. 终态干预表复制同一组 formal300 指标

`scripts/evaluation/aggregate_srr_batch7_interventions.py` 只读取一次 `casewise_metrics.csv`，然后把相同结果循环写给所有 intervention mode。以下模式没有各自独立的推理输出：

```text
anchor_identity
old_batch4_asset
rebuilt_batch7_asset
prototype_maps_off
semantic_negative_memory_off
zero_anchor_pathology_context
proposal_only
refiner_only
learned_source
gt_oracle_source_diagnostic_only
production_gate_closed
production_gate_learned
production_gate_one
no_anchor_diagnostic
```

因此 `final_mechanism_interventions.csv` 不是干预证据。`anchor_identity` 相对 anchor 不为零尤其证明语义错误。

### 2. proposal/refiner/source 关键指标为空或占位

`proposal_refiner_metrics.csv` 的 proposal-only 和 scar refiner-only 字段为空，来源明确写为 placeholder；`source_arbiter_metrics.csv` 只记录 softmax 归一化单元测试，没有 44 例实际效果。

### 3. Validator 检查文件存在而不检查机制真实性

当前 validator 没有检查：

- identity 与 gate-closed 是否逐病例严格等于 anchor；
- 每种 mode 是否拥有独立 prediction root、命令和 manifest；
- 不同干预是否错误复用同一 prediction hash；
- placeholder、空值和复制指标是否存在；
- proposal-only/refiner-only/source-arbiter 的正式指标是否实际生成。

### 4. 语义负记忆没有按合同分组落地

资产只记录 scar/edema positive 与粗粒度 safe-negative。六组 named negative buffers 仍以 deterministic axis 初始化，正式 loader 没有逐组替换为真实训练病例特征。manifest 对“人为向量贡献为零”的声明没有被正式前向路径和干预证明。

### 5. Discovery 仍间接读取 nnU-Net context

虽然 proposal 层可以把 anchor probability 置零，但 `_evidence_features` 的 retrieval 仍接收 anchor context。所谓 `zero_anchor_pathology_context` 没有重算真正 anchor-free 的 discovery feature path，因此不能证明 discovery 能独立发现 nnU-Net 漏检。

### 6. 联合训练无法判断哪一环失败

Batch 7 同时训练 spatial dictionary、proposal、scar/edema refiner、source arbiter 和 production gate。新模块由 architecture-extension 方式随机初始化，300 步不足以作为完整架构否定证据，也无法确定 scar 下降来自 proposal、refiner、arbiter、gate 还是损失冲突。

### 7. 机器真值和 wiki 过时

最新 terminal commit 已记录 Batch 7 stop-at-300，但 `CURRENT.md` 仍写 READY_FOR_CONTROLLER，root wiki 仍停留在 Batch 6。后续执行必须先修正状态。

## 修复决定

不启动 Batch 8，不启动 monolithic 1200-step 延长。执行一个 Batch 7 同范围机制闭环修复：

1. 真正运行同 checkpoint、同 44 例、同 decode 的独立干预；
2. 修复 semantic validator 和 known-bad；
3. 将六类 named negative memory 变为真实 category bank，并对不足类别使用 valid-mask 关闭，禁止 deterministic/random/repeat 填充；
4. 将 discovery routing 改为真正 anchor-free，confirmation 单独读取 anchor context；
5. 采用 proposal → scar refiner / edema refiner → source arbiter → production gate 的分阶段训练；
6. 每个阶段先证明自身独立有效，失败模块不得被后续平均或 gate 掩盖；
7. 只有最终同一 checkpoint 的真实干预和 44 例评价闭环后，才返回 Planner 判断是否继续。

## 科学边界

- 保留 SRR-v2/v2.5/v3 的 availability-aware retrieval、prototype/memory、anatomy proposal、pathology-specific refinement 和 bounded nnU-Net correction。
- 不换 backbone，不扩 fold，不做 Cine，不使用外部数据或权重。
- 如果 proposal-only 在真实分阶段训练后仍不能达到平均 `+0.003` 且每个病种不低于 `-0.001`，停止当前复杂 dictionary 路线并返回 Planner；不得继续训练 refiner 或 gate。
- 如果某个 refiner 不能优于本病种 proposal，正式最终路径必须禁用该 refiner，而不是继续平均。
