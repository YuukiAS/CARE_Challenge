# CARE 2026-07-31 并行下一步执行总览

## 结论

当前不再继续扩充大型取证 PDF，也不直接授权完整新架构长训练。下一步并行启动三条互不替代的工作：

1. **指标真值统一**：解决 D0 `0.922x`、clean OOF `0.56/0.43`、fold0 outer `0.534/0.559`、MoSAIC hosted 等数字的 population、标签和指标口径冲突。
2. **核心机制可行性实验**：只验证单主干模型能否在保留完整 decoder 能力的前提下，形成 scar 与 pure-edema 的独立候选；不直接训练完整 CARE-MyoPath-PR。
3. **前沿重置型 Deep Research**：暂时不从 Batch7/MMRD/Cascade/ARC 的结构出发，只把历史结果当安全边界，重新搜索具有大幅增益潜力的范式，并与 Proposal–Refinement 方案正面对比。

这三项可以同时启动，但代码写入必须隔离。指标任务与机制任务分别使用独立 task branch/worktree；Deep Research 为只读研究，不写仓库代码。

## 冻结仓库与姿态

```text
repo: /users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
base: origin/main
main-only scientific posture: preserved
Route A/B/C: historical evidence only
```

本轮并行不是恢复 Route A/B/C。两个 task branch 只用于避免并发写冲突，完成后由用户/Planner 决定是否依次合并回 `main`。

## 并行隔离设置

从主仓库执行：

```bash
cd /users/a/e/aereinh/CARE
git fetch --all --prune

mkdir -p /users/a/e/aereinh/CARE_worktrees

git worktree add \
  -b task/20260731-metric-truth \
  /users/a/e/aereinh/CARE_worktrees/task_metric_truth_20260731 \
  origin/main

git worktree add \
  -b task/20260731-myopath-a0-a3 \
  /users/a/e/aereinh/CARE_worktrees/task_myopath_a0_a3_20260731 \
  origin/main
```

不得使用或写入：

```text
/overflow/htzhu/CARE
/users/a/e/aereinh/CARE_worktrees/route_A
/users/a/e/aereinh/CARE_worktrees/route_B
/users/a/e/aereinh/CARE_worktrees/route_C
```

## Lane A：指标真值统一

Codex 工作目录：

```text
/users/a/e/aereinh/CARE_worktrees/task_metric_truth_20260731
```

Codex prompt：

```text
prompts/tasks/20260731_care_metric_truth_reconciliation.md
```

主要写入范围：

```text
scripts/forensics/metric_truth/**
tests/forensics/metric_truth/**
results/20260731_care_metric_truth_reconciliation/**
```

此任务以 CPU 为主，只有 exact prediction replay 确实必要时才使用一个诊断 GPU job。不得修改正式模型。

## Lane B：A0–A3 核心机制可行性

Codex 工作目录：

```text
/users/a/e/aereinh/CARE_worktrees/task_myopath_a0_a3_20260731
```

Codex prompt：

```text
prompts/tasks/20260731_care_myopath_pr_a0_a3_controller.md
```

该任务可立即并行完成代码映射、实现、A0 identity parity 和零信用 smoke。正式 A1–A3 训练前必须读取 Lane A 的：

```text
results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json
```

只有其中：

```text
metric_contract_status: PASS
```

才允许启动正式 GPU 训练。若 Lane A 尚未完成，Lane B 保持等待，不得自行猜测指标口径。

## Lane C：前沿重置型 Deep Research

研究 prompt：

```text
prompts/research/20260731_care_frontier_reset_deep_research_prompt.md
```

该任务可以与 Lane A/B 同时执行。它不以 CARE-MyoPath-PR 为默认答案，必须探索至少三种与旧路线结构不同的高增益范式，并明确判断是否应取代 Proposal–Refinement 方案。

研究必须同时读取：

```text
results/20260730_care_failure_forensics_deep_research_packet/CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v4.pdf
results/20260730_care_failure_forensics_deep_research_packet/v4_atlas_pages_a3_landscape.pdf
results/20260730_care_failure_forensics_deep_research_packet/DEEP_RESEARCH_MODEL_DESIGN_INPUT_20260730_v4.md
```

## 资源并行规则

- Lane A 与 Lane C 不占用正式训练 GPU。
- Lane B 最多一个 active GPU job。
- 若 Lane A 需要 prediction replay，优先使用 CPU；必须用 GPU 时，与 Lane B 串行，不得争抢同一 allocation。
- MyoPS 与 Cine 仍不允许在同一 controller 内并行写共享代码。

## 合并顺序

两个 Codex goal 均只在自己的 task branch 本地提交；默认不推送 runtime branch，不自动合并。

Planner 建议的审查顺序：

```text
Lane A metric truth
→ 确认唯一指标合同
→ Lane B A0–A3 terminal packet
→ Lane C frontier research conclusion
→ Planner 进行三方综合裁决
→ 决定是否合并代码或重新设计
```

若 Lane C 提出比 Proposal–Refinement 更强且可实现的新范式，Lane B 的 A0–A3 结果仍然有价值：A0 验证主干保持，A1 验证可靠监督，A2/A3 验证病种解耦与候选形成；但不得因为已投入实现而强行继续原方案。

## 当前禁止动作

```text
完整 52k-step CARE-MyoPath-PR 长训练
fold1 outer 访问
fold0 outer 二次选择
validation upload
Docker upload
hosted metric claim
多个完整 backbone 堆叠
直接切换到 Cine 作为逃生路线
```
