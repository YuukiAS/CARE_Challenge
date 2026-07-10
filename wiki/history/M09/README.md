# M09 历史架构分析

analysis_as_written: 本目录从 `TODO-M10.md` 迁移，保留当时的路线级判断和批评，不把后续结果静默覆盖到原判断中。

later_status_update: M9 follow-up 后 evidence/validator blocker 已修复，但最终 token 为 `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`，表示 no-promotion diagnostic-only，不授权 M10。

## 组件入口

- [可用性与 no-T2 安全](components/availability-no-t2.md)
- [检索字典与表示槽](components/retrieval-dictionary.md)
- [原型与负样本记忆](components/prototype-memory.md)
- [解剖先验](components/anatomy-prior.md)
- [病灶 proposal](components/proposal.md)
- [soft-ROI refiner](components/refiner.md)
- [分支仲裁与最终输出](components/arbitration.md)
- [loss 与优化目标](components/losses.md)
- [checkpoint 选择](components/checkpoint-selection.md)
- [训练证据与指标](components/training-evidence.md)
- [Cine temporal 分支](components/cine-temporal.md)

## 图

- [architecture](figures/architecture.png)
- [gap](figures/gap.png)
- [delta-from-M08](figures/delta-from-M08.png)
