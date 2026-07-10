# 检索字典与表示槽

> 历史快照：M09。本页只保存从 `todo-m10.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

### 1.1 M9 packet ready 状态与证据文件冲突

`m9_dictionary_fidelity_matrix.csv` 仍有 `PENDING_RUNTIME`，包括 true-BR2 runtime slot usage、invalid-slot mask runtime、final metric causal effect。与此同时，`completion_check.md` 和 `result.md` 声称 ready。这是当前最直接 blocker。

M9 follow-up 必须做两件事：如果 runtime evidence 已经存在，就将这些 pending rows 改成 runtime-derived status，并提供明确 evidence path；如果 runtime evidence 不存在，就把 completion 改为 `M9_FOLLOWUP_NEEDS_EVIDENCE`，不能继续 ready。

---

## 3. Dictionary / representer 问题

---

### 3.1 True-BR2 骨架存在，但还没有证明 representer 的医学价值

当前 `SRRV2MyoPSUNet` / `SRRProposeRefineMyoPS` 的方向比 Lite 正确：它有真正的 modality-private encoders，`ScaleRetrieval` 接收 per-modality features，而不是旧 Lite 里 `[fused, fused, fused]` 的伪模态路径。这点应保留。

但是，当前 representer 更像 per-scale multi-slot MoE feature expert，而不是已经形成医学可解释 lesion representer 的 dictionary。现有 evidence 主要证明“slot 被使用过”，没有证明“某类 slot 对 scar/edema final label 有因果贡献”。M10 不能继续只报告 slot usage；必须做可解释和 causal 的 representer audit。

---

### 3.4 Invalid-slot mask 证据仍偏弱

M9 aggregator 在 `m9_dictionary_invalid_slot_mask_report.csv` 中写 `invalid_slot_active_count = 0`，但这看起来更像根据 valid fraction 的汇总假设，而不是逐 step / 逐 case 检查 invalid slot weight 是否真的为 0。M10 前必须加强此项：对每个 batch、每个 task、每个 slot，检查 missing modality private/interaction slot 的 gate weight 是否为 0，并将 max invalid weight、mean invalid weight 写入 evidence。
