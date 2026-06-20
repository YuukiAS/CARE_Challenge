# R2、CARE 深度研究与两个 pilot 的综合评估

日期：2026-06-20

## 结论

`docs/notes/deep_research/Result3.md` 的总体方向正确，但目前还不足以直接下发“正式版本实现”任务。它已经准确抓住两个主故事：MyoPS 侧的 availability-aware pathology-specific fusion，以及 Cine 侧的 anatomy-first temporal cine adaptation；也正确把完整 U-MyoPS 式配准降为条件触发模块。但它尚未把这些组件组织成一个足够鲜明、可验证且区别于已有 baseline 的统一方法原则。

新加入的 `Representation Retrieval Learning for Heterogeneous Data Integration` 提供了一个更强的统一视角：不要假设所有中心、所有模态组合和所有任务完全共享同一表示，也不要为每个数据组完全独立建模；应建立一个可部分共享的 representation dictionary，让不同数据源按需要检索共享和私有表示。其 BR2 扩展进一步用 modality-specific dictionary 和显式观测指示器处理 blockwise missingness，而且不要求先填补缺失模态。这与 CARE 的中心偏移、模态组合偏移和 T2/edema 标签机制耦合高度吻合。

因此，当前应该先补一轮针对 GPT Deep Research 的方法设计研究，把 Result3 的通用 availability-aware late fusion 提升为“selective representation retrieval for partially observed multi-sequence CMR”的正式架构候选。该研究返回后，再生成 Codex 的正式实现任务。当前不建议直接把 Result3 原样转成大规模实现任务。

## Representation Retrieval Learning 的主要思想

论文把异构数据集成拆成三类异质性：同一模态在不同来源中的 covariate shift、不同来源中 response conditional distribution 的 posterior drift，以及不同来源只观测到部分模态的 blockwise missingness。

普通 multi-task representation learning 往往假设所有任务共享一个表示器，再用 task-specific head 吸收差异。R2 不采用这种 full-sharing 假设。它建立一个 representer dictionary `Theta={theta_1,...,theta_D}`，每个来源通过稀疏系数只检索其中对自己有用的表示器，再由 source-specific learner 完成预测。因此，一个表示器可以只服务某个来源，也可以被若干来源共享，形成可学习的 partially shared structure。

论文把某个 representer 被多少来源共同检索定义为 integrativeness，并提出 Selective Integration Penalty（SIP）。普通稀疏项鼓励每个来源少选表示器，SIP 则鼓励真正有价值的表示器跨来源复用，避免系统退化成每个来源各学一套完全独立模型。其理论贡献是把 excess-risk bound 与 representer integrativeness 联系起来。

BR2 将上述框架扩展到 blockwise missing modalities。每种模态拥有独立 dictionary，来源只聚合实际观测到的模态表示；缺失指示器直接关闭缺失模态贡献，而不是先做均值填补或生成式插补。论文也指出，若不同模态间交互重要，可以加入 interaction dictionaries，或者使用能学习交互的 nonlinear learner。

## 对 CARE 的直接帮助

CARE MyoPS 具有非常典型的 blockwise missingness：`LGE` 全部存在，`C0` 和 `T2` 按中心/组别成块缺失；同时不同中心存在强度与几何分布偏移，edema 的监督定义又随 T2 availability 变化。R2/BR2 比单纯 modality mask 更有价值的地方，是它同时允许共享和私有表示：LGE scar 表示可以跨全部样本共享，T2 edema 表示只在 T2-present 来源中训练和检索，C0/anatomy 表示可服务完整和双模态组，中心或协议特有表示则不必被强制共享。

一个 CARE 版本可以把 representer 从标量函数改成多尺度 feature block。每个模态有若干 shared/private adapters 或 experts，availability vector 和输入特征共同决定检索权重；scar、edema 和 anatomy 使用不同 learner/decoder。edema loss 仍必须只在 T2-present cases 上启用。SIP 的思想可以转化成跨 modality-group 的 group-sharing regularizer，使部分 expert 被多个组共享，同时保留少量组特异 expert。

这一思想也可以解释为什么不应继续 zero-fill：缺失模态在 BR2 中是“该 dictionary 不参与本次预测”，不是强度为零的真实图像。它也能自然吸收 MyoPS-Net 的 pathology-specific decoder 思想，并比简单 late fusion 多出一个明确的方法贡献：学习哪些表示应跨来源共享、哪些应保持私有。

但 R2 不能直接照搬。论文主要验证分类/回归与 ROI-level 表格特征，不处理 dense segmentation、空间配准、部分像素标签、极小病灶或 4D cine。SIP 的原始优化也不适合未经简化就塞进 nnU-Net。后续研究必须明确 dense feature retrieval、空间交互、条件监督和可训练近似，而不能只把 R2 名称贴到 modality gating 上。

## domain_adaptation 文献的综合价值

`Domain Adaptation for Medical Image Analysis: A Survey` 对 CARE 的主要价值是提供 domain/source、监督等级和 image/feature-level adaptation 的分类框架。它支持把中心/协议偏移作为辅助问题，但不能解决 T2 信息和 edema 标签缺失。

`Source-Free Unsupervised Domain Adaptation: A Survey` 提供 BN statistics、entropy minimization、pseudo-label 和 source-model adaptation 等工具。对 CARE 而言，BN/statistics 或 adapter-only adaptation 可以作为后期辅助；直接 pathology pseudo-label self-training 风险很高，因为 scar/edema 小且 HD 对单个错误组件敏感。

`Semi-Supervised Unpaired Medical Image Segmentation Through Task-Affinity Consistency` 的可借鉴点是 class-specific structural/contextual consistency。它更适合作为 anatomy 或高置信区域上的 soft regularizer，不应成为主故事，也不应让不可靠 pathology pseudo-label主导训练。

`Unpaired Volumetric Harmonization of Brain MRI with Conditional Latent Diffusion` 说明 image-level harmonization 可以显式保留 anatomy 并转换 style，但其 3D diffusion 工程和脑 T1 场景与 CARE 差距较大，且存在把 LGE/T2 病灶对比当作 style 消掉的风险。

`DomainATM` 是用于快速比较 image/feature-level DA 的工具箱，不提供 CARE 所需的完整模型故事。`Federated Learning for Medical Image Analysis: A Survey` 的隐私式分布训练不适用于当前本地集中数据，但 shared/private、client personalization 的思想可以帮助理解 center-specific representers。Tensor-train 与 Rosenblatt transport 论文主要服务高维概率密度、采样和贝叶斯反问题，对当前分割主线没有直接价值。

总体上，domain adaptation 应被放在 retrieval/fusion 主架构的外围：用于 normalization、center/style adapter 或可靠性一致性，而不是独立主线。

## 对 Result3 的评估

Result3 的优点是问题判断基本正确。它把 missingness/label mechanism 放在 registration 之前；提出 scar/edema 分头、T2-masked edema loss、anatomy prior；Cine 侧强调 ED reference、anatomy first 和多帧；并且给出了推进门、换资源门和冻结门。这些已经显著优于 loss-only 或 backbone-only 的建议。

其不足主要有五点。第一，Story A 目前仍是 separate encoders、late fusion、modality dropout、masked loss 的组合，方法辨识度不足。第二，它没有同时形式化 center covariate shift、posterior drift 和 blockwise missingness。第三，它没有规定 shared/private representation 如何选择和正则化。第四，跨模态 interaction 与 misalignment 只被放进模糊的 optional alignment，没有定义触发和插入位置。第五，Cine Story 与 MyoPS Story 是两条并列路线，尚未说明能否由同一个“从可用证据中检索可靠表示”的原则统一。

R2/BR2 正好能补前三点，并有可能统一第四、第五点，但需要新的定向研究完成 dense segmentation adaptation。

## 两个 Codex pilot 对故事的影响

CineMA pilot 已成功覆盖全部 64 个 train 和 15 个 validation cases。frame 0 上 myocardium Dice mean/median 为 `0.5723/0.6861`，LV Dice mean/median 为 `0.7779/0.9092`，说明外部 anatomy prior 有实际价值。非 frame-0 结果明显下降，但当前 raw label 只对应一个 3D reference geometry，因此这不能直接证明 temporal generalization 失败。更重要的问题是 adapter 使用固定中心 crop/pad 到 `192x192x16`，尚未完成 geometry-aware heart crop，也没有建立有效的 temporal supervision/evaluation。结论是 Story B 的 anatomy 支点成立，但 temporal branch 尚未得到证据。

T2 edema pilot 覆盖全部 80 个 complete cases，验证了 edema 监督与 T2 availability 的完全耦合，并显示 CenterB/CenterC 的 feature baseline 差异明显。规则 baseline 在 fold0 complete validation 上 Dice `0.2910`、HD95 `24.0819`，说明 T2 信号真实存在，但简单 threshold、oracle prior 和 component filter 不足。结论是 conditional supervision 的数据机制成立，但 trainable retrieval/fusion 模型仍未验证。

因此两个 pilot 都支持继续设计正式方法，却都不支持直接宣称 Result3 已经形成可实现完成版。

## 需要补充的定向深度研究

下一轮 GPT Deep Research 不应再搜通用“大模型”，而应回答以下具体问题：

1. 如何把 R2/BR2 的 dictionary、sparse retrieval、integrativeness/SIP 转成 dense segmentation 的多尺度 feature blocks，并找到最接近的 segmentation/MoE/shared-private repo。
2. CARE 的 source 应定义为 center、modality pattern，还是 center × modality pattern；如何避免匿名/未知中心导致 inference 依赖不可用元数据。
3. 如何把 T2-conditioned edema supervision、scar/edema pathology-specific decoders、anatomy prior 与 retrieval gate 放进同一损失和数据流。
4. 如何学习 modality interaction，而不是退化为各模态预测求和；应采用 interaction expert、cross-attention、late spatial fusion，还是 LGE-reference feature alignment。
5. registration 应处于 image level、feature level还是只作为 complete-case expert；需要什么定量 gate 才值得开启。
6. Cine 侧能否使用同一 retrieval 原则，把关键帧/运动/anatomy/texture视为 representer dictionary，而不是独立拼装 temporal module。
7. 在 7-10 天和单 job 8 小时限制下，正式版本、最小版本和可删除模块分别是什么；需要哪些 ablation 才能讲出 baseline 级别的完整故事。

## 当前决策

当前状态是 `NEEDS_FOCUSED_RESEARCH`，不是停止，也不是继续泛化调研。先运行一轮 R2/BR2 到 CARE dense segmentation 的定向 GPT Deep Research。研究返回后，应只选择一个 MyoPS 主方法故事，并决定 Cine 是同一 retrieval 原则的第二实例，还是独立但共享 anatomy prior 的第二分支。之后再生成 Codex 正式实现任务。
