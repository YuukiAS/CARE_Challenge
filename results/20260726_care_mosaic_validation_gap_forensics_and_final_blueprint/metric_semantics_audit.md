
本轮把 compact scar `5` 和 raw scar `2221` 统一视为 MyoPS scar mask；把 compact edema `4` 和 raw edema `1220` 统一视为 edema mask。当前 MoSAIC prediction tree 观察到 mixed raw/compact 标签，因此 evaluator 已按标签集合修复后重跑。`class_4` edema 没有 5-fold MoSAIC OOF 全量预测，因此没有用 edema component F1 或任何 full-data 指标替代 scar 结论。所有 OOF 行均来自 `mosaic_oof_no_leakage_audit.json` 声明的 220 例 held-out fold 预测；validation leaderboard 的 15 例没有本地 GT，不能反推出 casewise Dice。

本地 evaluator 只用于解释 clean OOF 与 hosted row 的差距。hosted score 仍以 leaderboard 行为准；本地 OOF 不能被写成 hosted 指标。
