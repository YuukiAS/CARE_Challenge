# Cine temporal 分支

> 历史快照：M09。本页只保存从 `todo-m10.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

# TODO M10：M9 follow-up 期间的路线级代码审计与下一轮规划

本文档记录在 M9 follow-up 执行期间，对当前 CARE / SRR-v3 / Cine 代码与结果包的横向审计。它不是 M10 prompt，也不是 route promotion。当前结论必须等 `prompts/shared/M9_followup_evidence_reconciliation_reaudit.md` 执行并独立 re-audit 后才能用于正式 M10 设计。

---

## 8. Cine 分支问题

---

### 8.1 M9 Cine 有进步，但仍是 local proxy

M9 Cine 已经不只是下载 weight 或 frame0-only。它有 local temporal final-output prediction、non-reference frame、ANTsPy SyNOnly / Demons fallback、local Dice delta。这是比 M8 更实在的进展。

但它仍不是完整 Cine route：

- final output 是 deterministic temporal union compact-label proxy；
- registration 是 classical registration，不是训练出的 temporal model；
- CineMA predictions 是 frame-wise anatomy proxy，不是项目自己的 final temporal segmenter；
- 没有 hosted metric；
- 没有验证 temporal dictionary 对 learned model 的训练贡献；
- 没有明确处理 class label space 与 challenge metric 的完全一致性。

---

### 8.2 Cine 不能再 optional，但也不能拿来救 MyoPS

Cine 是 secondary line，但必须推进。M10 可以选择把 Cine 单独作为主任务，但不能让 Cine proxy 结果给 MyoPS dictionary 背书。

若 M10 选择 Cine，应目标化为：

```text
M10_CINE_TEMPORAL_MODEL_NOT_PROXY
```

最低要求：

1. frame-wise backbone / adapter 明确 provenance；
2. non-reference frames 进入 feature or prediction aggregation；
3. learned or calibrated temporal aggregation，而非简单 union；
4. final compact-label outputs；
5. frame0 control vs temporal model same-subset metrics；
6. geometry sanity / registration failure matrix；
7. hosted metric caveat。

---

## 9. M10 不应做什么

在 M9 follow-up re-audit 前，不要做：

```text
M10 training
fold expansion
validation packaging
hosted claim
route promotion
继续当前 M9 三个 SRR-main variants 盲目加长训练
只调 threshold / decode rule 试图救 M9
只扩大 dictionary slot 数量
只把 nnU-Net 重新放回 final logits base
只把 Cine temporal union proxy 当完整 Cine 模型
```

这些都会重复 M8/M9 的问题。

---

### 10.3 若 MyoPS dictionary route 连续失败但 Cine proxy有正信号

可以规划：

```text
M10_B: Cine temporal model route
```

这不是 optional supplement，而是 secondary line 的正式实现。目标是从 deterministic temporal union proxy 升级为 learned/calibrated temporal model，并以 frame0 vs temporal model 的 same-subset metrics 审查。

---

## 12. M10 prompt 编写前必须确认的问题

1. M9 follow-up reviewer 是否已经给出 clean audited state？
2. M9 follow-up 是否修复了 stale CSV/JSON pending scan？
3. `SafePrototypeMemoryBank` 是否确实接入训练和 proposal dictionary？
4. `m9_ablation_matrix.csv` 和 `m9_refiner_causal_effect.csv` 是否仍是 proxy rename？
5. Pattern-SIP 是否仍只是 post-hoc usage summary？
6. M10 是继续 MyoPS dictionary，还是切到 Cine temporal model？
7. M10 是否允许新训练，预算多少？
8. nnU-Net 的角色是否继续限制为 control/context/teacher/safety，绝不作为 final-logit base？

在这些问题回答前，不应写可执行 M10 prompt。
