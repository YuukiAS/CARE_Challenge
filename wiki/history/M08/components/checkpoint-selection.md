# checkpoint 选择

## 历史分析原文迁移

### 1.9 Checkpoint selection：实现与配置声明不一致

M8 config 里写了很具体的 checkpoint selection rule，例如 scar precision 变体写“best same-split scar Dice/HD95 guard”，T2 CenterC edema 变体写“best T2-present edema subgroup subject to no-T2 safety”。

但训练代码实际 checkpoint best 是根据 `val_patch_loss` 更新的。训练 loop 在 scheduled validation step 上跑 `validate_patch_loss`，然后如果 `val_loss < best_val` 就保存 `checkpoint_best.pt`。 这和 leaderboard-facing 的 Dice/HD95/hard subgroup guard 不是一回事。后面确实导出了 full-case eval，但 checkpoint selection 已经由 patch loss 决定了。

这也是一个关键偏差。我们要优化的是 scar/edema 的 final label、HD95、remote FP、component burden、CenterB/CenterC/T2-present hard subgroup，而不是 patch loss。Codex 这版在“训练选择机制”上没有完全按挑战赛目标实现。
