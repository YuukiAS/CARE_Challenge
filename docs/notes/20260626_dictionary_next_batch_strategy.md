# 20260626 下一批任务策略：从 SRR 路线选择进入 dictionary 大规模构建

当前阶段不应再问“dictionary 有没有价值”。上一轮已经给出 fold0 相对证据：修复后的 SRR 路线在 edema GT-positive Dice 和 scar all-case Dice 上优于 conditional control、无 dictionary 的 late fusion 和弱化 SIP retrieval。这个结果说明 dictionary/retrieval 不是装饰，但绝对分数仍低，病灶定位、远端假阳性、component burden 和 scar/LGE fallback 仍然不足。

下一批任务的目标是进入真正的 dictionary construction 阶段，而不是继续单点小修。所谓 dictionary construction，不是只把一个 gate 放进网络，而是系统比较多种 shared/private representer 的组织方式：多尺度字典、任务专属字典、跨模态交互字典、原型/slot 字典、anchor-guided 字典、hierarchical dictionary 与 task-conditioned retrieval。每条路线都要用足够训练预算形成证据，并用同一 fold0、同一 evaluator、同一 subgroup 和 component 诊断比较。

MyoPS 是主线。下一批 goal 应该至少包含三个大任务：第一，联网做一次 bounded dictionary literature/design synthesis，重点不是泛泛大模型，而是 MoE、shared-private representation、routing anti-collapse、dictionary/prototype learning、missing-modality segmentation 和 medical dense prediction 中可落地的机制；第二，在 MyoPS 上跑 dictionary bank，至少比较 5-6 种 dictionary/retrieval 设计，允许多 GPU 并行，每个 formal job 尽量使用 6-7 小时有效训练预算；第三，在 dictionary bank 中选出的 1-2 条最有信号路线之上，继续做 lesion localization/compactness package，集中解决 false positives、component burden、scar/LGE fallback 和 T2-positive edema localization。

CineMyoPS 仍作为次线同步推进。上一轮已把 geometry 阻塞拆成 59 个 safe cases 和 5 个 mismatch cases，下一步应在 safe subset 上跑 temporal/anatomy retrieval preflight，并把 mismatch cases 放进单独 repair queue。Cine 任务不能阻塞 MyoPS，但也不应完全停掉。

后续 Codex 结论不能因为几个 case、几个 epoch 或一个 variant 失败就下判断。除非出现 label/fold/cache/no-T2 supervision 错误、预测无效、单 job 超过 8 小时且无法截断、或需要未授权外部数据/上传，否则应继续完成同一 task 中的其他 variants。失败报告必须解释失败来自数据机制、dictionary 设计、routing、loss、sampling、center split、component morphology 还是训练预算，而不是只写“结果不好”。
