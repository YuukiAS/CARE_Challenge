# Review 20260620 Cinema Adapter Pilot

decision: OPEN_NEXT_TASK

## 总结判断

该 task 已完成，权限边界和证据记录基本合格。CineMA 代码、公开权重和隔离环境均成功落地，全量覆盖 64 个 train 和 15 个 validation cases，证明外部 cine anatomy prior 在 CARE 上不是纸面方向。

但本结果只能支持“anatomy prior 值得继续”，不能支持“temporal CineMyoPS 正式路线已经验证”，也不能直接支持把 adapter 接入主训练或 submission。下一步需要把 reference-frame 语义、geometry-aware crop 和 temporal aggregation 分开验证。

## 完成度

- task 目标：建立并运行隔离 CineMA 到 CARE CineMyoPS anatomy adapter/pilot。
- 完成情况：代码、权重、license、输入输出 label、geometry round-trip、Slurm 全量 inference 和本地 anatomy metrics 均有记录。
- 未执行 official validation、主训练 pipeline 修改和 upload packaging，符合 task 禁止动作。
- result 与 `MANIFEST.md` 能追溯到脚本、job、日志和主要输出目录。

## 关键证据

- CineMA ACDC SAX seed0 checkpoint 成功加载。
- Slurm job `55524633` 完成，覆盖 64 train、15 validation、234 selected frames。
- train frame0：myocardium Dice mean/median `0.5723/0.6861`，LV Dice mean/median `0.7779/0.9092`。
- train all selected frames：myocardium Dice mean/median `0.4655/0.4866`，LV Dice mean/median `0.6775/0.7288`。
- raw train label 是单个 3D reference geometry，而不是每一帧均有独立 GT。

## 证据解释

frame0 上的结果足以说明外部 anatomy representation 在 CARE 上具有可迁移性，尤其 LV median Dice 已较高。它可以作为 anatomy teacher、soft prior 或初始化来源。

非 frame0 指标下降不能直接解释为 CineMA temporal generalization 失败，因为这些帧仍与单一 reference label 比较。该下降混合了真实运动、reference-frame mismatch、固定 crop/pad 和 domain shift，不能用来选择 temporal architecture。

当前 adapter 把 CARE volume 中心 crop/pad 到 `192x192x16`。这一操作满足 checkpoint shape，但不保证心脏居中，可能对特殊 spacing、少切片或 center_beta cases 造成前景截断。正式使用前必须改为 geometry-aware heart crop 或基于可靠 coarse anatomy 的 ROI。

现有 Dataset502 对比只含单 fold 弱参照，不足以证明 CineMA 已超过当前完整 baseline。

## 风险与遗漏

- reference frame 是否确实为 frame0/ED 尚未被可靠元数据或运动曲线确认。
- 没有对 `mnms`、`mnms2` 等 checkpoint 做域鲁棒性比较。
- 没有 temporal consistency、motion propagation 或多帧 aggregation 的有效评估协议。
- 没有完整 5-fold Dataset502 对照。
- 外部 anatomy label 与 CARE `200/500/600` 的映射需要继续保留单元测试。

## 对正式方法故事的意义

本结果支持 `anatomy-first temporal cine adaptation` 的第一个支点：先获取稳定 anatomy representation。它尚未验证第二个支点，即如何从多个时相检索并融合 motion、anatomy 和 texture。

结合 R2/BR2 方法设计研究，后续可以考虑把关键帧或 anatomy/motion/texture feature 视为 temporal representer dictionary，但在正式实现前必须先确定 reference frame 和可评估的 temporal supervision。

## 下一步状态

`OPEN_NEXT_TASK`，但不建议立即把 CineMA 接入主 pipeline。下一张执行 task 应在新的方法设计研究返回后，从以下范围中选择一个单一目标：

1. geometry-aware heart crop + ACDC/M&Ms checkpoint 对比；或
2. reference-frame identification + 关键帧 temporal consistency baseline。

禁止重新回到 single-frame wrapper、LCC 或仅更换 backbone 的路线。
