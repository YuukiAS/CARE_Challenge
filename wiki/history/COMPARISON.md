# M8 与 M9 组件级对比

| 组件 | M8 实现状态 | M9 实现状态 | M8 -> M9 实际代码变化 | 证据变化 | 修复了什么 | 仍缺什么 | 对 M10 的约束 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 可用性与 no-T2 安全 | 已有 availability/no-T2 safety，但偏安全约束 | 保留 no-T2 安全，仍需证明 edema 监督没有被当作 negative | 从 anchor-centered safety 进入 SRR-main 合同 | 证据从自然语言转向 tracked tables/review token | 防止 no-T2 edema 被误解为真实阴性 | T2-present edema gain 仍不足 | M10 必须把安全与性能分开验证 |
| 检索字典与表示槽 | 有 dictionary/slot 概念，但不等于完整语义检索 | true-BR2/private encoder 骨架更清楚，但 router 仍偏 global | 引入/强调 private encoders 和 SRR-main | dictionary fidelity evidence 更严格 | 修正了“有名字就算检索”的宽松判断 | lesion-local retrieval 和 representer 医学价值未闭环 | M10 不能只改名，必须证明局部病灶检索贡献 |
| 原型与负样本记忆 | prototype/negative memory 有拟合证据但弱 | SafePrototypeMemoryBank 更明确，但像 helper | 从 buffer prototype 走向 memory helper | 证据记录更细，但仍非闭环 | 明确 hard-negative replay 是缺口 | memory 未证明进入正式前向和训练闭环 | M10 若继续 SRR 必须让 memory 影响 logits/selection |
| 解剖先验 | 有 anatomy head/anchor context 依赖 | 仍是辅助证据，非强定位器 | 无决定性结构闭环变化 | 证据仍偏间接 | 保留 LV/RV/union prior 合同 | 解剖先验对 proposal recall 的贡献不足 | M10 必须量化 anatomy prior 对 ROI/proposal 的帮助 |
| 病灶 proposal | M8 的 proposal 可能被 anchor/context 稀释 | M9 proposal 仍需证明 recall/precision 与最终 logits 关系 | 从 proposal diagnostics 走向 SRR-main evidence | proposal 不再与 prototype 混放 | 修复迁移归档错误，单独建 proposal 页 | proposal recall 与 ROI coverage 仍弱 | M10 必须有 proposal -> refiner -> logits 因果链 |
| soft-ROI refiner | 小 crop residual，不是完整 lesion formation engine | scar/edema refiner 差异更清楚，但因果证据不足 | refiner 结构合同更强 | evidence 更关注 pathology-specific | 修复了 refiner 只当表格输出的风险 | 缺 scar/edema 分开优化与消融 | M10 必须证明 refiner 改变 ROI 内 logits/HD95 |
| 分支仲裁与最终输出 | anchor-centered residual arbitration 容易让 nnU-Net 做主角 | SRR-main final output 取消/弱化 anchor 底座，但主干不够强 | anchor-residual -> SRR-main | no-promotion evidence 更直接 | 修复“SRR 只是后处理”的部分风险 | SRR-main 未超过 anchor，主干能力不足 | M10 不能靠 Cine 或表格包装 MyoPS 失败 |
| loss 与优化目标 | M8 loss wiring 存在 bug 风险 | M9 loss wiring bug 已修，但优化仍可能不足 | loss wiring fixed | loss report 更可审计 | 修复配置声明与实际 loss 不一致 | loss 是否驱动 dictionary/refiner 仍不充分 | M10 必须把 loss 与机制指标绑定 |
| checkpoint 选择 | checkpoint selection 与配置声明不一致 | 仍不够彻底，未完全解决选择偏差 | 有更明确选择报告但未闭环 | 证据从配置审计扩展到训练决策 | 部分修复 best-variant 解释 | selection rule 仍需 strict validator | M10 formal decision 不能用不完整 checkpoint rule |
| 训练证据与指标 | 不是 smoke，但仍不足以路线晋级 | M9 metrics 负面，且 no-promotion diagnostic-only | formal SRR-main 负向证据更清楚 | review token 变为 M9 diagnostic ready | 修复 evidence reconciliation | 负向结论仍不是 scientific stop | M10 要先确认是机制修复还是路线收缩 |
| Cine temporal 分支 | CineMA/registration 只是 local proxy | M9 Cine 有进步但仍 local proxy | Cine 仍未成为 hosted-ready 路线 | local evidence 更清楚 | 明确 Cine 必做但不能救 MyoPS | temporal dictionary/hosted metric 缺口 | M10 不能用 Cine proxy 包装 overall success |

![M09 delta](M09/figures/delta-from-M08.png)
