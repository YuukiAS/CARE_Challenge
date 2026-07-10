# 可用性与 no-T2 安全

> 历史快照：M09。本页只保存从 `todo-m10.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

### 3.2 Router 仍偏 case/global，不够 lesion-local

`RetrievalRouter` 主要基于 fused feature global mean、availability、anchor summary 决定 expert weights。这更适合“这个 case 应该看哪类 source”，不适合“这个局部心肌区域是不是 edema/scar/hard FP”。

M10 需要把 dictionary query 从 case-level/global 改成 lesion-conditioned / spatial-conditioned，至少包括：

```text
local proposal score
local anatomy distance / p_union / p_lv / p_rv
local T2 intensity/statistics when T2-present
anchor uncertainty or teacher uncertainty, if used
component / remote-FP flags, if used
availability pattern
```

可以先做 lightweight spatial router，不一定一次性重写全模型；但 M10 必须避免继续把 dictionary 证明停留在全局 gate usage。

---

### 4.3 Hard-negative replay 还没有形成闭环

当前 hard-negative memory 主要来自旧 mined CSV 或 prototype fitting 统计，不是 “当前模型误报 -> 安全过滤 -> 回灌 memory -> 再训练” 的闭环。M10 如果继续走 dictionary/prototype，必须加入至少一轮 bounded hard-negative refresh：

1. 用当前 candidate 在 same-split train/val proxy 上找 remote FP / component-burden FP；
2. 过滤 no-T2 unsafe edema negative；
3. 写入 memory ledger；
4. 重新训练或 fine-tune bounded steps；
5. 比较 refresh 前后 proposal/refiner/final label。

---

### 5.1 scar / edema refiner 的结构差异已经有，但科学证据不足

代码里 scar 和 edema 的 refiner 确实不同：scar 是小 ROI / LGE-oriented / tighter crop；edema 是大 ROI / T2-conditioned / larger crop / no-T2 blocking。这符合示意图方向。

但是，M9 的 refiner evidence 仍然主要来自 ROI coverage、component rows、same-split metrics等聚合表。`m9_refiner_causal_effect.csv` 在 aggregator 中本质上由 component rows 写出，并不是真正的 refiner-on/off causal ablation。

M10 必须做真实 toggles：

```text
refiner_off
proposal_only
scar_refiner_only
edema_refiner_only
both_refiners_on
```

每个 toggle 都需要同一 checkpoint、同一 eval cases、同一 decode rule 的 final-label delta、Dice、HD95、remote-FP、component count。不能再把普通 component metric 表命名为 causal effect。

---

### 10.1 若 M9 follow-up 仍是 NEEDS_REVISION / NEEDS_EVIDENCE

不写 M10。继续修 M9 packet、validator、aggregation、evidence naming。没有干净审计状态，不允许下一轮科学任务。

---

### 10.2 若 M9 follow-up 是 READY_NO_PROMOTION_DIAGNOSTIC_ONLY

这时可以承认：当前 `SRRProposeRefineMyoPS` 的 SRR-main dense segmentation route 不值得直接扩展。M10 不应继续同架构长训，而应 pivot。

优先候选：

```text
M10_A: Dictionary-led lesion proposal route
```

核心思想：把 dictionary 从 dense final segmentation 主干中剥离出来，先做高召回、低远端 FP 的 scar/edema lesion proposal engine，然后再接 pathology-specific refiner / selector。也就是说，dictionary 的主要卖点不是“直接输出完整 segmentation”，而是“在异质模态缺失下检索医学可解释 lesion evidence”。

M10_A 成功门：

```text
scar proposal lesion-wise recall improves or non-worse with lower remote-FP
T2-present edema proposal recall improves on CenterB/CenterC
no-T2 edema remains zero
refiner improves final label over proposal-only
SRR_without_anchor_context has nontrivial lesion signal
```

---

### 10.4 若 M9 follow-up 发现 evidence 缺失导致 M9 科学结论不可靠

规划：

```text
M10_BLOCKED_NEEDS_M9_EVIDENCE_REPAIR
```

不要强行解释负结果。
