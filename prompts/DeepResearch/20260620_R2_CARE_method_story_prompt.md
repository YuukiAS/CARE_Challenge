# GPT Deep Research Prompt: R2/BR2 驱动的 CARE Myocardium 正式方法设计

> 本提示词用于 ChatGPT Deep Research，不是 Codex 执行任务。请联网检索论文、官方代码、GitHub、HuggingFace 和许可证信息，并给出可核验引用。目标不是生成论文清单，而是设计一个可以在 CARE 2026 Myocardium 剩余时间内实现、能够处理缺模态与多中心异质性、并能像现有三篇 baseline 一样讲清楚完整故事的方法。

## 一、任务目标

我们需要判断能否以 `Representation Retrieval Learning for Heterogeneous Data Integration` 中的 R2/BR2 思想为统一原则，把 CARE MyoPS 的缺模态、中心偏移、病理特异性融合和条件标签监督组织成一个正式模型；同时判断同一 retrieval 原则能否延伸到 CineMyoPS 的多帧 anatomy/motion/texture 融合。

最终回答必须给出一个首选正式架构、一个降级最小架构、明确的数据流和损失函数、与三个 baseline 的区别、7-10 天实现计划、必要 ablation，以及每个模块对应的 CARE leaderboard metric。不要把“换 loss”“加一个 mask channel”或“换 backbone”单独包装成方法故事。

## 二、CARE 任务与数据背景

CARE Myocardium 关注三个 leaderboard metric：

- `myops_scar`
- `myops_edema`
- `myocardium_cinemyops`

MyoPS train 共有约 220 cases：

- `C0 + LGE + T2`: 80 cases
- `C0 + LGE`: 24 cases
- `LGE only`: 116 cases

LGE 在全部训练样本中存在。T2 只存在于 80 个 complete cases，而且 edema label 只出现在这些 T2-present cases；no-T2 cases 没有可靠 edema supervision，不能被简单解释成 edema-negative。当前 raw validation 15/15 是完整 `C0 + LGE + T2`，因此 train 与 validation 存在结构化 missingness shift。模态组合还与中心高度相关，意味着缺模态、中心风格和标签可用性纠缠在一起。

scar 主要依赖 LGE，是小病灶，远端 false positive 会显著恶化 HD/HD95。edema 主要依赖 T2，通常更多连通域且类别极不平衡。C0 更像 anatomy/结构信息来源。CARE label 在 raw 数据中使用医学语义值，内部 pipeline 常 compact 到 `0-5`，因此训练、评估和导出 mapping 必须可逆。

CineMyoPS raw train 有 64 个 4D cine cases，通常每例 30 frames；validation 有 15 cases，其中 14 例 30 frames，1 例 50 frames。raw label 对应一个 3D reference geometry。旧 Dataset502/pipeline 主要抽取单 frame，未真正利用 temporal/motion information。

## 三、必须理解的四篇核心论文

### 1. MyoPS-Net

Qiu et al., 2023, **“MyoPS-Net: Myocardial pathology segmentation with flexible combination of multi-sequence CMR images”**。

请准确解释：

- cross-modal feature fusion 如何工作；
- 为什么 scar 与 edema 使用 pathology-specific decoder；
- myocardium prior and consistency 的作用；
- pathology inclusiveness loss 的假设；
- missing-sequence practical scenarios；
- 为什么 CARE 中 zero-filled T1/T2* wrapper 不是论文方法的忠实复现。

### 2. U-MyoPS

Ding et al., 2023, **“Aligning Multi-Sequence CMR Towards Fully Automated Myocardial Pathology Segmentation”**。

请准确解释：

- 为什么用 LGE 作为 common reference；
- TPS registration、feature warping、myocardium extraction、spatial prior gate 的关系；
- registration-before-fusion 的方法故事；
- 为什么 CARE 大量缺 C0/T2、Stage1-to-Stage2 bridge 不完整，使完整复现不适合作为当前主线。

### 3. CineMyoPS

Ding et al., 2025, **“CineMyoPS: Segmenting Myocardial Pathologies from Cine Cardiac MR”**。

请准确解释：

- ED reference；
- motion estimation、anatomy segmentation、pathology segmentation 的联合关系；
- warped anatomy、warped texture、motion field 与 time-series aggregation；
- 为什么 single-frame wrapper 没有使用论文核心思想。

### 4. Representation Retrieval Learning

Qi Xu and Annie Qu, 2025, **“Representation Retrieval Learning for Heterogeneous Data Integration”**, arXiv:2503.09494。

请重点解释并评估：

- R2 的 representer dictionary 与 source-specific sparse learner；
- partially shared structure 相比 full sharing 和完全独立模型的意义；
- integrativeness 与 Selective Integration Penalty（SIP）；
- BR2 如何用 modality-specific dictionary 和 observation indicator 处理 blockwise missingness；
- interaction dictionaries 或 nonlinear learner 如何恢复跨模态 interaction；
- 理论和实验成立的范围；
- 为什么论文当前主要是 regression/classification 和 ROI/tabular data，不能直接宣称适用于 dense CMR segmentation。

## 四、现有深度研究与 pilot 证据

现有 `docs/notes/deep_research/Result3.md` 提出两个故事：

1. `availability-aware pathology-specific fusion`
2. `anatomy-first temporal cine adaptation`

它还建议把 registration 降为 complete-case 条件 expert。这个判断方向基本正确，但目前只是 separate encoder、late fusion、modality dropout、conditional loss、anatomy prior 等已知组件的组合，缺少一个足够鲜明的 shared/private representation selection 原则。

当前两个本地 pilot 已完成：

### CineMA adapter pilot

- CineMA 代码、MIT license 和 ACDC SAX 权重可用；
- 已处理全部 64 train 和 15 validation cases；
- frame 0 上 myocardium Dice mean/median `0.5723/0.6861`；
- frame 0 上 LV Dice mean/median `0.7779/0.9092`；
- 非 frame-0 指标下降，但 raw label 仅对应一个 reference frame，不能直接当 temporal performance；
- 当前 adapter 使用 center crop/pad 到 `192x192x16`，尚未做 geometry-aware heart crop；
- 结论：外部 anatomy prior 有价值，但 temporal branch 尚未验证。

### T2-present edema pilot

- 完整复核 80 complete cases 和 140 no-T2 cases 的标签机制；
- T2 edema-vs-myocardium contrast 明显；
- T2 robust-z + oracle anatomy/scar prior + component filter 在 fold0 complete val 上 Dice `0.2910`、HD95 `24.0819`；
- 结论：conditional supervision 和 T2-aware expert 的数据机制成立，但简单规则不够，需要 trainable fusion/retrieval model。

## 五、核心研究问题

### A. R2/BR2 如何变成 dense segmentation 架构

请寻找最接近的工作和开源实现，包括但不限于：

- shared/private representation learning for segmentation；
- sparse mixture-of-experts 或 top-k/entmax routing for dense prediction；
- modality-specific experts with missing modalities；
- HeMIS、ModDrop、sequence dropout、late fusion；
- partially shared multi-task segmentation；
- block-missing multi-modal medical segmentation；
- conditional computation 或 expert retrieval；
- source/domain-specific adapters 与 shared backbone。

请明确回答以下设计问题：

1. representer 应是 encoder、adapter、multi-scale feature block、token dictionary 还是 decoder expert？
2. retrieval gate 应只由 availability mask 决定，还是由 availability + image feature 共同决定？
3. 如何在不依赖 validation center identity 的情况下吸收 center covariate shift？
4. 如何把 SIP 转成可稳定训练的 soft/group regularizer？是否可用 group lasso、entropy/coverage regularization、load balancing、shared-expert encouragement 或 differentiable top-k 近似？
5. 如何避免 SIP 过度共享，把 center-specific artifact 或 pathology-specific cue强行混在一起？
6. 如何在 spatial feature maps 上实现 retrieval，而不是只在 global vector 上做 MoE？

### B. CARE MyoPS 正式故事

请设计一个首选方法，暂称 **Selective Representation Retrieval for Partially Observed Multi-sequence CMR**。名称可以调整，但必须给出完整架构。

至少讨论以下组件：

- LGE、C0、T2 modality-specific stems/encoders；
- shared 与 modality-private representer/expert dictionary；
- availability-aware sparse retrieval；
- scar-specific、edema-specific、anatomy-specific learner/decoder；
- T2-conditioned edema supervision；
- myocardium/pathology union anatomy prior；
- scar containment；
- modality dropout；
- center/style adapter 或 normalization；
- 跨模态 interaction；
- optional LGE-reference feature alignment。

请写出数据流、tensor shape 层级、伪代码和总损失。总损失必须区分：

- anatomy loss；
- scar loss；
- T2-masked edema loss；
- retrieval sparsity；
- SIP-inspired integrativeness；
- optional consistency/alignment；
- pathology spatial prior。

请回答：source/task 在 CARE 中应定义为 center、modality pattern、center × modality pattern，还是 pathology objective？推荐方案必须能在匿名或新中心 inference，不依赖已知中心 ID。

### C. 配准是否进入正式版本

请查找有代码、可插拔的 feature-level STN/TPS/cross-attention alignment 方法，并回答：

- late fusion 是否足以降低未对齐风险；
- 若需要 alignment，应放在 raw image、encoder feature、bottleneck 还是 decoder skip；
- 如何只对 complete tri-modal cases 启用，而不破坏 missing-modality inference；
- 什么定量诊断足以证明 alignment 值得进入正式故事；
- 在 7-10 天内，alignment 是 must-have、optional ablation 还是应该冻结。

不要因为 U-MyoPS 有 registration 就默认必须配准。

### D. Cine 是否能被同一 retrieval 原则统一

请判断是否可把 4D cine 的关键帧、motion cue、anatomy prediction 和 texture feature 看成 temporal representer dictionary：

- frame-wise anatomy encoder；
- ED/reference representation；
- 关键帧 sparse retrieval；
- temporal consistency；
- motion/frame-difference expert；
- shared/private temporal experts。

请比较两种写法：

1. MyoPS 与 Cine 各自独立故事；
2. 统一为“从当前可用的模态或时相中检索可靠表示”。

必须判断哪一种在比赛剩余时间、代码风险和论文叙事上更合理。不要为了统一而过度设计。

## 六、外部资源审计要求

每个关键资源都必须给出：

- 论文名、年份、venue；
- 官方论文链接；
- 官方 GitHub/HuggingFace；
- 是否有预训练权重；
- license；
- 输入输出与 CARE label/mode 的匹配；
- 是否需要外部训练数据；
- 3-5 天能否形成最小实现；
- 主要风险；
- 是直接复用、借模块、借损失，还是只借思想。

最多保留 10 个高价值资源。不要用方法名数量代替判断。重点寻找 R2/BR2 到 segmentation 的最近邻实现，而不是再列大批 foundation models。

## 七、必须产出的正式方法规格

最终报告必须包含以下内容：

1. **一句话问题定义**：CARE 为什么不是普通多通道分割。
2. **一句话方法主张**：新方法解决什么，核心操作是什么。
3. **架构图的文字版**：每个 branch、dictionary、gate、decoder、prior 和 alignment 的关系。
4. **数学定义**：retrieval、availability gating、conditional supervision、SIP-inspired regularization 和总损失。
5. **与 MyoPS-Net、U-MyoPS、CineMyoPS、HeMIS/ModDrop 的逐点区别**。
6. **最小版本与正式版本**：哪些模块第一轮必须实现，哪些是 optional。
7. **7-10 天工程计划**：每轮单 job 不超过 8 小时；写明输入、预期证据、停止门和回滚。
8. **ablation matrix**：至少包含 unified channel concat、conditional loss only、modality-specific encoders、retrieval gate、SIP-inspired regularizer、anatomy prior、optional alignment。
9. **metric mapping**：每个模块预期影响 `myops_scar`、`myops_edema`、`myocardium_cinemyops` 中哪一个。
10. **失败模式**：gate collapse、expert under-training、T2 expert overfit、center leakage、misalignment、scar false positive、temporal label mismatch。
11. **最终 GO/NO-GO 判断**：是否值得把 R2/BR2 作为正式故事主轴；若不值得，最强替代故事是什么。

## 八、明确禁止的回答方式

- 不要只建议换 loss、换 backbone、增加 channel 或做 LCC。
- 不要把原始 R2 的线性 learner 直接宣称成 segmentation solution。
- 不要只说“可以使用 MoE”，必须给出适合 CARE 的 routing unit、训练方式和 collapse 防护。
- 不要默认外部 repo 可用，必须核查代码、权重和 license。
- 不要建议完整重写 U-MyoPS Stage1-to-Stage2 或引入超出 7-10 天预算的大型 foundation framework。
- 不要回到泛化 arXiv 大模型综述。

最终目标是得到一份可以直接转写为 Codex implementation task 的正式方法蓝图，而不是另一份资源清单。
