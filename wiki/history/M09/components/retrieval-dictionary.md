# 检索字典与表示槽

## 历史分析原文迁移

## 3. Dictionary / representer 问题

### 3.1 True-BR2 骨架存在，但还没有证明 representer 的医学价值

当前 `SRRV2MyoPSUNet` / `SRRProposeRefineMyoPS` 的方向比 Lite 正确：它有真正的 modality-private encoders，`ScaleRetrieval` 接收 per-modality features，而不是旧 Lite 里 `[fused, fused, fused]` 的伪模态路径。这点应保留。

但是，当前 representer 更像 per-scale multi-slot MoE feature expert，而不是已经形成医学可解释 lesion representer 的 dictionary。现有 evidence 主要证明“slot 被使用过”，没有证明“某类 slot 对 scar/edema final label 有因果贡献”。M10 不能继续只报告 slot usage；必须做可解释和 causal 的 representer audit。

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

### 3.3 Pattern-SIP 目前更像后处理报告，不是真正优化目标

M9 loss 里加入了 `loss_pattern_sip_integrativeness` key，但代码中它与 `dict_loss` 绑定，仍主要是 semantic retrieval regularization 的别名，而不是真正的 group-conditioned integrativeness objective。M9 aggregator 生成 `m9_pattern_sip_usage_by_group.csv`、`m9_integrativeness_gamma_soft.csv` 等，但这更像 post-hoc summary，而不是训练时显式优化 `u_{task,slot,group}`。

M10 如果继续以 dictionary 为核心卖点，必须真正实现 pattern-conditioned SIP：

```text
u_{task,slot,availability_group}
u_{task,slot,center_or_style_group}
u_{task,slot,hard_subgroup}
```

并将其纳入 loss，而不是仅在 aggregation 阶段汇总。

### 3.4 Invalid-slot mask 证据仍偏弱

M9 aggregator 在 `m9_dictionary_invalid_slot_mask_report.csv` 中写 `invalid_slot_active_count = 0`，但这看起来更像根据 valid fraction 的汇总假设，而不是逐 step / 逐 case 检查 invalid slot weight 是否真的为 0。M10 前必须加强此项：对每个 batch、每个 task、每个 slot，检查 missing modality private/interaction slot 的 gate weight 是否为 0，并将 max invalid weight、mean invalid weight 写入 evidence。

### 4.1 ProposalDictionary 仍以 buffer prototypes 为主

`ProposalDictionary` 里的 positive / negative prototypes 仍是 `register_buffer`，不是 `nn.Parameter`。`load_prototype_bank` 只是把 train/OOF fitted bank 拷贝进去。这样做比 deterministic axis fallback 强，但不等于在线可学习 prototype memory。

### 10.3 若 MyoPS dictionary route 连续失败但 Cine proxy有正信号

可以规划：

```text
M10_B: Cine temporal model route
```

这不是 optional supplement，而是 secondary line 的正式实现。目标是从 deterministic temporal union proxy 升级为 learned/calibrated temporal model，并以 frame0 vs temporal model 的 same-subset metrics 审查。

### Dictionary 仍是全局 MoE，而不是局部病灶检索

当前 private/shared/interaction representer 的骨架是真实存在的，但 router 主要依据全局池化 feature、availability 和 anchor summary 分配 expert 权重。这能决定“这个病例应该看 T2 还是 LGE”，却不能精确决定“这一块心肌是否像 edema、这一小块高信号是不是 remote FP”。

这会导致 dictionary 对全图风格、中心和模态组合敏感，却不能稳定形成局部 lesion proposal。M9 的结果中 component count、remote FP 和 HD95 同时明显恶化，正符合这种情况：模型知道“大概要输出什么”，但空间定位和病灶形成不稳定。

### Pattern-SIP 目前不是真正的 pattern-conditioned 优化目标

M9 新增了 `loss_pattern_sip_integrativeness`，但当前 loss 实现中它仍然复用了同一个 `dict_loss`；`loss_memory_bank_update_or_alignment` 也复用了 prototype margin loss。

也就是说，一些看起来独立的新机制在数学上并没有对应独立 loss：

```text
loss_pattern_sip_integrativeness = dict_loss
loss_memory_bank_update_or_alignment = loss_proto
```

这属于实质实现不足，而不只是命名问题。它意味着 M9 并没有真正优化“不同 availability / center / hard subgroup 对同一 representer 的稳定复用”，只是继续优化原来的 semantic retrieval regularizer，然后在 aggregation 阶段生成 group usage 报告。

所以 M9 不能证明 Pattern-SIP 无效，因为真正的 Pattern-SIP 还没有独立实现。
