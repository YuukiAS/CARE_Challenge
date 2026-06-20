# Review 20260620 T2 Edema Pilot

decision: OPEN_NEXT_TASK

## 总结判断

该 task 已完成其数据机制验证目标，并且严格覆盖全部 80 个 T2-present complete cases。结果强烈支持“no-T2 cases 不能作为 edema hard negative”这一建模前提，也支持继续做 trainable T2-aware expert/routing。

但本轮没有训练模型，使用的是 T2 robust-z、oracle anatomy/scar prior 和 component filter 的规则 baseline。fold0 complete validation Dice `0.2910`、HD95 `24.0819` 说明简单阈值方案不足，不能把本结果写成 T2 expert 已经优于现有 baseline。下一步需要一个真正可训练、baseline-preserving 的 conditional supervision 与 retrieval/fusion 实验。

## 完成度

- task 目标：判断 `myops_edema` 是否应从统一 zero-filled missing-channel 训练转向 complete-case T2-aware expert/routing。
- 已完成：220 train 和 15 validation 的模态/标签复核；80 complete cases 的全量 feature baseline；fold0 train/val、中心分组和 HD/HD95 指标；脚本、输出和 manifest。
- 未完成：GPU training、trainable edema expert、正式 pipeline 和 submission。result 已说明这是任务允许的 fallback，不构成越权或漏报。

## 关键证据

- train modality pattern：complete 80、`C0+LGE` 24、`LGE-only` 116。
- validation：15/15 complete。
- edema-positive：complete 80/80，no-T2 groups 0/140；scar 在 no-T2 groups 中仍大量存在。
- T2 edema-vs-myocardium contrast mean `0.9209`。
- rule baseline fold0 complete val：Dice `0.2910`、precision `0.2982`、recall `0.4643`、HD `38.6553`、HD95 `24.0819`。
- CenterB all-complete Dice `0.3711`，CenterC `0.2732`，显示额外 center/protocol heterogeneity。

## 证据解释

本结果验证的是监督机制，而不是架构优越性。edema 标签与 T2 availability 完全耦合，因此统一多类模型若把 no-T2 样本作为 class-4 negative，会同时学习中心、模态和标签缺失 shortcut。conditional edema loss 应成为后续正式模型的硬约束。

规则 baseline 即使使用 oracle anatomy/scar prior 仍表现有限，说明问题不能靠阈值、component filter 或 anatomy containment 单独解决。需要 trainable T2 representation，并且要学习 T2 与 LGE/C0/anatomy 的 interaction。

CenterB/CenterC 差异提示正式模型不能只做 availability mask；还需要考虑 center/style shift 或 shared/private representation。该证据与 R2/BR2 的部分共享 representer 思想一致：应允许跨中心共享 T2 edema representation，同时保留少量协议特异表示，而不是强制全共享或完全分开。

## 风险与遗漏

- 当前 prior 使用 oracle information，不能直接用于真实 inference。
- 没有与现有 nnU-Net fold0 complete-subset edema 指标做严格同 split 对照。
- 没有验证 conditional loss only、modality-specific encoder、late fusion、retrieval gate 各自贡献。
- 没有诊断 complete cases 内 C0/T2/LGE 的空间错配是否足以影响 fusion。
- 粗阈值网格限制了规则 baseline 上限，但不影响其“不足以成为正式方案”的结论。

## 对正式方法故事的意义

本结果支持 `availability-aware pathology-specific fusion` 的核心前提，但 Result3 中的普通 late fusion 还不够形成鲜明方法。R2/BR2 提供了更完整的解释：用 modality-specific representer dictionary、显式 availability indicator 和部分共享 retrieval 同时处理 blockwise missingness 与中心异质性；edema decoder 只在 T2-present cases 接收 dense supervision。

正式版本应至少比较：

1. unified concat baseline；
2. conditional edema loss only；
3. modality-specific encoders + late fusion；
4. availability/feature-conditioned retrieval；
5. SIP-inspired shared/private regularizer；
6. anatomy prior；
7. optional complete-case alignment。

## 下一步状态

`OPEN_NEXT_TASK`，但不建议现在直接写一个大而全的 implementation task。应先完成 R2/BR2 到 dense CMR segmentation 的定向 GPT Deep Research，明确 retrieval unit、shared/private regularization、interaction 和 alignment 位置。

研究返回后，下一张 Codex task 应是一个 8 小时以内的 trainable fold0 implementation，优先实现：T2-conditioned edema loss、modality-specific representation 和最简 retrieval gate；no-T2 cases 不参与 class-4 hard-negative supervision。只有该任务取得同 split 的正向证据后，才扩展到完整 formal model。
