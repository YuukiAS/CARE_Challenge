# checkpoint 选择

## 历史分析原文迁移

### 6.2 Checkpoint selection 仍不够彻底

M9 post-hoc metric selection 比 M8 的 patch-loss-only 更好，但训练过程的 `checkpoint_best` 仍可能先由 patch loss 保存，然后 aggregator 只在已有 checkpoint outputs 中选择。M10 应该在 scheduled checkpoints 上做 metric-facing full-case or bounded-full-volume eval，并按 scar/edema hard gates 保存 best，而不是只在训练后从 `checkpoint_best` / `checkpoint_final` 中补救选择。
