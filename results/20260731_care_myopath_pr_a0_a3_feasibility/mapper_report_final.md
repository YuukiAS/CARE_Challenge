# Mapper Report Final

当前 pilot 代码已接入完整 stock encoder/decoder/output head。A0/A1 保持 stock final logits；A2 的 scar/edema global head 参数独立并进入 final logits；A3 proposal 以冻结系数 `0.5` 进入 final logits。正式训练和 intervention 证据因 metric truth receipt 缺失仍为 missing。

wiki update: not authorized.
