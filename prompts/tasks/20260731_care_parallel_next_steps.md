# CARE 2026-07-31 并行下一步执行总览

## 最新结论

前沿重置型 Deep Research 已返回：

```text
PR_DECISION: REPLACE_PR
PRIMARY_ARCHITECTURE: CARE-MyoWall-IF
FINAL_DECISION: GO_FRONTIER_REPLACEMENT
```

因此，原 `CARE-MyoPath-PR A0-A3` Prompt 不再是活跃训练主线。它保留为历史规划证据，不得与新的壁坐标场试验同时启动。

当前并行工作调整为：

1. **指标真值统一**：解决 D0 `0.922x`、clean OOF、outer、full-data diagnostic、hosted 等分数语义冲突。
2. **CARE-MyoWall-IF 机制试验**：使用完整 stock nnU-Net encoder+decoder、冻结解剖几何、matched Cartesian control 与三种 wall-field arm，验证坐标场是否改善 scar 与 pure edema 最终标签。
3. **前沿研究已完成**：研究报告只授权机制 pilot，不授权完整长训练。

## 冻结仓库与姿态

```text
repo: /users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
Route A/B/C: historical evidence only
```

## Lane A：指标真值统一

Prompt：

```text
prompts/tasks/20260731_care_metric_truth_reconciliation.md
```

主要结果：

```text
results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json
```

正式模型训练的依赖：

```text
metric_contract_status: PASS
canonical_t2_present_count: 80
```

此任务以 CPU 为主，只有 exact prediction replay 必须时才使用诊断 GPU。

## Lane B：CARE-MyoWall-IF 交互式机制试验

冻结设计：

```text
prompts/blueprints/CARE_MyoWall_IF_mechanism_pilot_20260731.md
```

Controller Prompt：

```text
prompts/tasks/20260731_care_myowall_if_interactive_controller.md
```

Executor plan：

```text
prompts/tasks/20260731_care_myowall_if_pilot_executor_plan.yaml
```

该任务在 `main` 上由一个 controller、一个 executor 和一个 mapper 顺序执行，使用 interactive GPU allocation，不使用 `sbatch` 训练 arm。

科学 arm：

```text
C0: matched Cartesian pathology head
W1: complete wall-coordinate scar/edema field
W2: W1 without component/guard losses
W3: W1 without rank/high-frequency signals
```

每 arm 固定 8000 optimizer steps；四 arm 使用相同病例、batch descriptor、augmentation seed、optimizer、评价和 decode。

正式训练前必须读取 Lane A 的 metric truth receipt。允许先完成 stock parity、geometry cache、实现、tests 和 zero-credit smoke。

## 已被替代的旧 Pilot

以下 Prompt 不得再作为活跃训练任务启动：

```text
prompts/tasks/20260731_care_myopath_pr_a0_a3_controller.md
```

替代原因：Deep Research 判断 Proposal-Refinement 仍属于候选依赖的 coarse-to-fine 完善，没有把病灶表示单位和搜索空间改写；新的 wall-coordinate field 是范式级机制试验。

旧 Prompt 只作历史对照，不删除。

## GPU 并行规则

- Lane A 优先 CPU。
- Lane B 最多一个 active interactive GPU step。
- 若 Lane A 必须 GPU replay，与 Lane B 串行共享 allocation，不并发争抢。
- 不启动 Cine 训练。
- 不启动多个完整 backbone。

## 合并与终态

Lane A 可独立完成并返回 Planner。

Lane B Controller 只有在：

```text
all interactive jobs/steps terminal
all 4 arms reach 8000 steps
aggregation complete
strict validators pass
terminal lightweight commit created
origin/main push verified
completion email sent
```

后才能结束。

Lane B 的允许科学终态：

```text
PILOT_PASS_DUAL_PATHOLOGY
PARTIAL_SIGNAL_NO_PROMOTION
STOP_GEOMETRY_NOT_RELIABLE
STOP_WALL_FIELD_NO_GAIN
OPERATIONALLY_BLOCKED
```

即使双病种 pilot 通过，也不自动授权完整 48k-step 训练、fold expansion、outer、validation 或 Docker；必须返回 Planner。

## 当前禁止动作

```text
启动旧 CARE-MyoPath-PR A0-A3
完整 CARE-MyoWall-IF 长训练
fold1 outer 访问
fold0 outer 二次选择
validation upload
Docker upload
hosted metric claim
多个完整 backbone 堆叠
直接切换 Cine 作为逃生路线
```
