# Cine temporal 分支

## 历史分析原文迁移

## 8. Cine 分支问题

### 8.1 M9 Cine 有进步，但仍是 local proxy

M9 Cine 已经不只是下载 weight 或 frame0-only。它有 local temporal final-output prediction、non-reference frame、ANTsPy SyNOnly / Demons fallback、local Dice delta。这是比 M8 更实在的进展。

但它仍不是完整 Cine route：

- final output 是 deterministic temporal union compact-label proxy；
- registration 是 classical registration，不是训练出的 temporal model；
- CineMA predictions 是 frame-wise anatomy proxy，不是项目自己的 final temporal segmenter；
- 没有 hosted metric；
- 没有验证 temporal dictionary 对 learned model 的训练贡献；
- 没有明确处理 class label space 与 challenge metric 的完全一致性。

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
