# SRR fold0 结果复盘与 recovery 计划

日期：2026-06-25

## 当前结论

上一轮 SRR goal 没有达到理想状态，但不应视为失败。`results/20260621_srr_spec/result.md` 已经完成 Result4 extraction、architecture contract、first-party skeleton、unit tests 和 one-batch smoke，状态为 `GO_FOLD0`。这说明 SRR 框架的 wiring、缺模态屏蔽、T2-conditioned edema loss、LGE-only scar gradient 和 gate finite/normalized 等基础条件已经通过。

`results/20260621_srr_fold0/result.md` 显示，两个 fold0 variants 均完成了正式运行：`conditional_dualhead_control` 运行约 4.1 小时，`srr_minimal` 运行约 4.5 小时。SRR 相对 conditional control 有正信号：edema GT-positive Dice 提升 `+0.0323`，scar all-case Dice 提升 `+0.0250`，edema GT-positive HD95 改善 `-15.4582`。这说明 Result4 的 dictionary/retrieval 思路不是纯粹无效。

但当前结果不能直接进入 fold expansion。核心问题是 routing collapse：logged row-level expert weights 达到 `1.0000`，scar routing 明显集中在 expert1，mean `0.9431`。这意味着 dictionary 已经“建起来并参与训练”，但还没有形成理想的 shared/private balanced representation usage。旧 goal 因此停在 `MYOPS_REVISE_SRR`。

## 为什么不应该停止

旧 gate 太保守：它把 routing collapse 当作阻止 ablation 的硬条件。现在应该改成 recovery 策略。原因是：

1. SRR 已经相对 conditional control 产生多个目标上的正向信号。
2. collapse 是可修的训练/regularization 问题，不是 label、fold、cache 或 no-T2 supervision 的根本错误。
3. 当前 fold0 指标绝对值仍低，说明训练预算、router温度、loss权重、sampling、expert regularization都还需要系统调整。
4. 若因为一次 collapse 就停止，会错过 Result4 方法真正训练成型的机会。

## 下一轮原则

下一轮应从 `strict gate` 改为 `rescue-and-continue gate`：只要 label/fold/cache/no-T2 supervision 正确，且 SRR 有非退化正信号，就继续修 router、重跑 fold0、并做有限 ablation。不要轻易 stop；只有以下情况才停止：

- 缺失模态仍影响有效 feature；
- no-T2 cases 仍作为 edema hard negative；
- predictions invalid 或 cache/evaluator 错误；
- SRR 在修正后同时伤害 scar 和 edema，且无可解释诊断；
- 单 job 需要超过 8 小时且无法截断。

## 需要优先修的问题

1. Router collapse：加入或调强 temperature、entropy floor、coverage/load balancing、expert dropout、task-specific anti-collapse、warmup schedule。
2. Dictionary usage：将 expert usage 从单纯报告转为训练目标的一部分，但避免强制完全均匀。
3. Scar/edema tradeoff：scar 当前绝对 Dice 很低，必须检查 LGE-only scar fallback、scar class weighting、sampling、loss balance。
4. Edema GT-positive：避免 all-case edema 被 no-T2 empty-GT 稳定性虚高掩盖；继续以 GT-positive/T2-present 为主 gate。
5. Training budget：上一轮已经不是 toy smoke，但仍只有 4-4.5 小时。下一轮允许每个 job 用满 6-8 小时预算，必要时增加 max steps、checkpoint cadence 和 early stopping。
6. Cine geometry：Cine 侧停在 `REVISE_GEOMETRY`，不是模型失败。应把 59/64 safe cases 与 5 个 mismatch cases 分开处理，先在 safe subset 建 temporal/reference control，再修 mismatch，而不是整个 Cine 线停掉。

## 建议新任务

- `20260625_srr_recovery`: 修 SRR router 并重跑 fold0 revised variants。
- `20260625_srr_rescue_ablate`: 在 SRR recovery 有任意非退化正信号时继续 ablation，不因单一 routing caveat 阻塞。
- `20260625_cine_geometry`: 修 Cine reference/geometry，并在 safe subset 上继续 reference/temporal control。
- `20260625_fast_goal`: goal-mode 调度入口，优先 MyoPS，Cine 同步但不阻塞。
