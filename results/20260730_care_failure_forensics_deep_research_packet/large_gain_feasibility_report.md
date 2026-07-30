# 约 0.1 Dice 潜在上限分析

结论：`LOCAL_EVIDENCE_SUPPORTS_ONLY_MODEST_GAIN`。

病例 oracle 和 voxel/error overlap 是乐观上限，不是可部署模型性能。当前证据显示 scar 存在一定互补信号；pure edema 的 MoSAIC-clean 互补很弱，full-data/recipe 反转提示训练域和 recipe 影响较大。 因此后续 Deep Research 可以追求大机制上限，但必须以新的单模型机制和严格 held-out 验证证明，不能把 oracle 或 full-data probe 当成真实可实现增益。
