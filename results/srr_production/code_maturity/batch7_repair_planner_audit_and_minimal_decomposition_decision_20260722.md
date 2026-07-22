# Batch 7 repair Planner 初步审计（已由全面 BR2 / SIP 审计取代）

## 状态

本文件保留 Batch 7 repair 的直接代码复核和低分证据，但其中“availability pattern 直接作为论文 source”“允许 image-conditioned coefficient residual”的后续设计已被更深入审查修正。

当前权威审计为：

```text
results/srr_production/code_maturity/batch7_br2_sip_comprehensive_architecture_audit_20260722.md
```

当前权威计划和配置为：

```text
docs/plans/laneB_round04_active_srr_batch7_minimal_pathology_decomposition_execution.md
configs/srr_production/myops_batch7_minimal_decomposition.yaml
```

## 仍然有效的 Batch 7 repair 结论

Batch 7 repair 比原 Batch 7 真实：独立 44 例干预、identity 零变化、真实语义记忆、anchor-free discovery 代码检查和 600 步 proposal 训练均实际完成。但所谓 proposal-only stage 仍传入空 loss JSON，M10 历史混合损失继续参与；梯度验收对 proposal logits 均值反向传播，而不是验证正式 loss authority。因此该 600 步结果不能作为纯 proposal 或 R2/BR2 的最终否定。

真实干预仍表明：

- semantic negative memory 对 scar 无益，对 edema 略有伤害；
- prototype maps 对 edema 仅约有 `+0.0007` Dice 杠杆，对 scar 无稳定收益；
- scar proposal/refiner/source/gate 相关模式持续为负；
- edema 保留约 `+0.004～+0.006` 的小幅正信号；
- no-anchor 仍严重崩溃。

因此当前 M10 16-slot spatial dictionary、prototype maps 和 semantic negative memory 不再作为正式候选。

## 已修正的后续设计

Representation Retrieval Learning 的论文主线仍保留，但新的医学影像适配必须满足：

1. 训练 source 是采集中心，availability 是 source 的 observation set；
2. center 只能索引训练期 coefficient 和均衡采样，不得进入图像网络；
3. 验证和部署只使用 availability-pattern pooled coefficient；
4. learner coefficient 是 signed、空间全局的稀疏标量，不用 softmax/simplex/top-k；
5. 禁止 image-conditioned coefficient residual 绕开 source coefficient；
6. representer 输出固定 RMS，防止通过缩放 representer、反缩放 beta 绕开 L1/SIP；
7. no-T2 source 不建立 edema coefficient，不进入 edema SIP、loss 或 negative；
8. 旧 semantic regularization 和旧 Pattern-SIP 正式权重为零；
9. 新 SIP 只作用于拥有可靠病种监督且观察到所需模态的训练中心 coefficient；
10. 结果必须经过 complete-trimodal 与 worst-center 安全门。

## 当前六个实验

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

它们用于分别回答：普通 proposal 是否有效、轻量中心分层 BR2 是否提供独立增益、SIP 是否在 no-SIP 基础上真正有益。最终解释只能是 `R2/BR2/SIP-inspired medical imaging adaptation`，不得声称原论文理论界已直接适用于 3D 分割，也不得声称已因果分离 center 与 missingness。