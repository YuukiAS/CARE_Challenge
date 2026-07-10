# 原型与负样本记忆

> 历史快照：M09。本页只保存从 `todo-m10.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

## 4. Prototype / memory 问题

---

### 4.2 SafePrototypeMemoryBank 目前像孤立 helper

M9 新增了 `src/care_myocardium/models/srr_dictionary_memory.py`，实现了安全 EMA prototype memory，并在 update 时拒绝 no-T2 edema negative。这是正确方向。但目前需要确认它是否被正式训练链路实际调用。初步代码搜索只看到定义文件本身，未看到明确接入 `ProposalDictionary` 或 training loop 的调用路径。如果 M9 follow-up 后仍确认没有接入，则 M10 必须把 memory 真正连到 proposal dictionary 或 training loop。

M10 的 prototype/memory 目标不应只是“summary JSON 有 counts”，而应是：

```text
memory source -> proposal similarity -> proposal logits -> refiner logits -> final labels
```

每一步都要有可追踪 evidence。
