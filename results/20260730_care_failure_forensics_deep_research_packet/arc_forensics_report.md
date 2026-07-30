# ARC 专项取证

本文件由 `aggregate_historical_replay_binding_v2.py` 生成。结论基于当前仓库可绑定的 source、checkpoint、prediction、metric、controller packet 和 git history 证据；缺少 exact checkpoint 或 prediction 的项目按 `BLOCKED_BY_MISSING_BOUND_ASSET` 处理。

核心结论：旧模型长期未稳定超过 nnU-Net，主要不是单一想法全部错误，而是强基线继承、decoder 完整性、final-mask 组件进入路径、病例级 help/harm 选择和可靠标签规则没有同时闭合。未来可保留数据/监督/安全门控经验，但不能复制这些历史实现。
