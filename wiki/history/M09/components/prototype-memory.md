# 原型与负样本记忆

## 历史分析原文迁移

## 4. Prototype / memory 问题

### 4.2 SafePrototypeMemoryBank 目前像孤立 helper

M9 新增了 `src/care_myocardium/models/srr_dictionary_memory.py`，实现了安全 EMA prototype memory，并在 update 时拒绝 no-T2 edema negative。这是正确方向。但目前需要确认它是否被正式训练链路实际调用。初步代码搜索只看到定义文件本身，未看到明确接入 `ProposalDictionary` 或 training loop 的调用路径。如果 M9 follow-up 后仍确认没有接入，则 M10 必须把 memory 真正连到 proposal dictionary 或 training loop。

M10 的 prototype/memory 目标不应只是“summary JSON 有 counts”，而应是：

```text
memory source -> proposal similarity -> proposal logits -> refiner logits -> final labels
```

每一步都要有可追踪 evidence。

### 4.3 Hard-negative replay 还没有形成闭环

当前 hard-negative memory 主要来自旧 mined CSV 或 prototype fitting 统计，不是 “当前模型误报 -> 安全过滤 -> 回灌 memory -> 再训练” 的闭环。M10 如果继续走 dictionary/prototype，必须加入至少一轮 bounded hard-negative refresh：

1. 用当前 candidate 在 same-split train/val proxy 上找 remote FP / component-burden FP；
2. 过滤 no-T2 unsafe edema negative；
3. 写入 memory ledger；
4. 重新训练或 fine-tune bounded steps；
5. 比较 refresh 前后 proposal/refiner/final label。

### Prototype memory 可能没有真正进入正式前向闭环

`ProposalDictionary` 里的 positive 和 negative prototypes 仍然是 `register_buffer`，不是可学习参数；模型初始化仍从 deterministic axis prototypes 开始，再由 `load_prototype_bank` 覆盖。

新增的安全 EMA memory helper 是正确方向，但目前最关键的问题不是“有没有这个文件”，而是：

```text
它是否在正式训练循环中被 update？
更新后的 memory 是否被 load 回 ProposalDictionary？
它是否改变 proposal similarity？
是否进一步改变 final labels？
```

如果缺少这条闭环，那么 M9 的“lesion proposal memory”更多是 prototype fitting + summary evidence，而不是持续学习的 memory system。这足以解释为什么 memory variant 没有明显改善。
