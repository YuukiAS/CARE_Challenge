# checkpoint 选择

> 历史快照：M09。本页只保存从 `todo-m10.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

### 7.2 Aggregator 的一些 evidence 文件名称过强

`m9_ablation_matrix.csv` 当前由 checkpoint selection rows 写出，不是实际 ablation matrix。`m9_refiner_causal_effect.csv` 当前由 component rows 写出，不是真正 refiner causal effect。这类文件名会误导 reviewer 和 GPT。M10 必须把 evidence 文件命名和实际内容对齐：如果只是 proxy summary，就叫 proxy；如果叫 causal effect，就必须是真 ablation。
