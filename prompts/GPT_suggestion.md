# CARE-Myocardium 项目判断与行动建议

> 来源：对挑战赛、baseline 报告与相关文献的综合性建议，供内部决策与对外部工具（Deep Research / Codex）的提示词复用。

---

## 1. 核心判断

**结论：值得做，但不宜作为未来几个月的主线。**

- 更适合作为**挑战赛型**项目：约 **2–4 周**做出强 baseline，再叠 **1–2 个**有解释性的改进。
- 若目标是**刷榜、练训练工程、积累 CMR 多模态分割经验** → 值得投入。
- 若目标是**与 UKB 下游生信强绑定的长期研究线** → 只能作**辅助**，不应挤占 Cardiac Nexus / UKB 表型提取与 PheWAS、MR 等主线。

---

## 2. 任务与数据概况

CARE-Myocardium 实质包含**两个子任务**：

| 子任务 | 输入 | 目标 |
|--------|------|------|
| **MyoPS** | LGE、T2、bSSFP 多序列 CMR | 分割 scar 与 edema |
| **CineMyoPS** | 仅 cine CMR | 在 **ED frame** 上分割 scar |

官网将真实挑战概括为：**多中心差异、缺序列、多序列空间不对齐**。数据规模并非“大数据”，价值在于真实世界中缺模态、跨中心、配准误差、病灶类极小且边界不稳等难点。

**数据量（整理自官网说明）**

- **MyoPS**：训练集多中心（有的中心仅 LGE，有的 LGE/T2/bSSFP，有的 LGE+bSSFP）；验证 15 例，测试 65 例。
- **CineMyoPS**：训练仅两中心共 64 例；验证 15 例，测试 45 例。

参考：[CARE-Myocardium 赛道说明](https://zmic.org.cn/care_2026/track_myocardium/)

---

## 3. Baseline 报告的关键结论

- **Paper setting ≠ CARE 当前 nnU-Net 六标签设定。** MyoPS-Net、U-MyoPS 论文侧重点多为 **scar/edema 病理指标**；CineMyoPS 为 **cine 空间** 的 scar/edema，而非统一的 background、myocardium、LV blood、RV blood、edema、scar 六类 benchmark。
- **CARE wrapper 是 adapter**，不是原论文完整复现，例如：
  - MyoPS-Net：对缺失 T1/T2\* mapping 做 **zero-filled placeholder**；
  - U-MyoPS：**stage bridge 不完整**；
  - CineMyoPS wrapper：导出 **single-frame compact task**，且当前保留结构 vs 原论文 **joint scar-and-edema、cine-only** 目标不完全一致。

**推论**

- 若仅跑 third-party baseline 并声称“复现论文并提升 Dice”，**风险高**。
- 若将问题表述为：在 CARE **多中心、缺模态、弱对齐**数据上构建**统一、公平、可复现**的 MyoPS/CineMyoPS pipeline，则**方法学上更有意义**。

---

## 4. Dice 与提升空间（文献 / 报告中的量级）

| 来源 / 设定 | Scar Dice（约） | Edema Dice（约） |
|-------------|-----------------|------------------|
| MyoPS-Net-L（MICCAI2020 public） | 0.647 | 0.722 |
| MyoPS-Net-L ensemble | 0.661 | 0.742 |
| U-MyoPS（MYOPS2020） | 0.647 | 0.726 |
| CineMyoPS（cine-only，论文） | ~0.53 | ~0.57 |

**解读**

- **MyoPS 多序列**：整体仍有空间，但多为**百分点级**，尤其 scar。
- **CineMyoPS**：相对 multi-sequence、对比增强任务**低不少**，提升潜力更大，但**不确定性与泛化风险**也更大（从 cine 推 scar 属于更强的 surrogate 推断）。

---

## 5. 临床叙事（为何不只是“刷 Dice”）

- MI 相关死亡率与致残率高；**心肌活性 / 瘢痕与水肿**评估与诊断、管理相关；LGE 看 scar，T2 看 edema；**无对比剂的 cine** 有吸引力但更难。
- 评估层面 challenge 仍以 **Dice、HD** 为主；短期内产出多为**算法与工程贡献**，不宜过度承诺直接临床转化。

参考：[CARE-Myocardium](https://zmic.org.cn/care_2026/track_myocardium/) · [CineMyoPS（arXiv）](https://arxiv.org/html/2507.02289v1)

---

## 6. 建议投入强度与阶段

定位为**中等投入**，避免 all-in。

| 阶段 | 时长（建议） | 内容 |
|------|----------------|------|
| **一** | 3–5 天 | 官方数据结构、label mapping、nnU-Net v2 baseline、per-label Dice/HD、按 center 的 validation 梳理干净 |
| **二** | ~1 周 | MyoPS 强 baseline：模态预处理、缺失模态 mask、2D/3D/2.5D ensemble、TTA、连通域 / 后处理 |
| **三** | 1–2 周 | 一项“像论文”的改进，例如 anatomy-constrained pathology + missing-modality-aware fusion + scar-inside-edema 类先验 |

**止损线（示例）**

若约 **2 周后**验证集上没有明显超过 nnU-Net，例如：

- MyoPS scar 未见约 **+0.02～0.04**；
- CineMyoPS scar 未见约 **+0.03～0.06**；

则不宜在无上限下调参，避免只剩 leaderboard 小数点后第三位的差异。

---

## 7. 保守的提升预估（相对“干净的”nnU-Net v2）

**MyoPS（多序列）**

- 若 baseline 已正常：单模型结构创新大致 **scar +0.02～0.04**，**edema +0.01～0.03**。
- 若 baseline 未处理好缺模态 / 配准：可见更大增益（如 **+0.05+**），但更多来自 **pipeline 修正** 而非纯模型创新。

**CineMyoPS**

- 训练集小、任务难；若从 single-frame nnU-Net 走向 **full cine 时序聚合**、motion/strain proxy、ED-ES 一致性等，scar Dice **有机会 +0.03～0.08**，泛化风险大。
- 近期方向：motion、解剖分割与时序聚合利用动态信息；full 3D+T 与多视图时序表征（如 CineMA、ViTa 等趋势）。
- **ScarNet** 等 LGE foundation 结果不能直接迁移到 CARE 多序列/跨中心设定，但 **MedSAM encoder + U-Net decoder + attention** 等 hybrid 思路可作参考。

参考：[CineMyoPS](https://arxiv.org/html/2507.02289v1) · [ScarNet](https://arxiv.org/abs/2501.01372)

---

## 8. 与其他 CARE 赛道对比（节选）

### CARE-Whole Heart

- **任务**：CT/MRI **七结构**（LV、RV、LA、RA、LV myocardium、升主动脉、肺动脉等）；数据量约 246 例（训练 106 / 验证 50 / 测试 90）；允许预训练与公开数据。
- **特点**：更稳、更工程，易做出完整 pipeline；与 Cardiac Nexus **腔室解剖、体积、几何、下游表型**衔接顺；易陷入强 nnU-Net + ensemble + 后处理，方法新意需靠 **域泛化 / foundation 适配** 等拉开。

参考：[CARE-Whole Heart](https://zmic.org.cn/care_2026/track_wholeheart/)

### CARE-Left Atrium

- **叙事**：AF、LA 腔室、LA scar、digital twin、消融规划等临床故事强；数据侧 LGE MRI **200+**、CT **300+**，多中心；含 LA scar quantification、LA cavity、LA CT multi-structure 等任务。
- **限制**：外部数据与预训练模型**不允许**（以官网当期规则为准）；奖项侧重 **LA scar quantification** 与 **CT multi-structure**。
- **与你当前主线**：AF/LA 方向强，但与 **心肌 / CMR 病理主线** 贴合度不如 MyoPS；foundation 叙事受限。

参考：[CARE-Left Atrium](https://zmic.org.cn/care_2026/track_leftatrium/)

---

## 9. 如何选择赛道（小结）

| 目标 | 建议优先级 |
|------|------------|
| 短期挑战赛 + CMR pathology 研究故事 | **CARE-Myocardium**，侧重 **CineMyoPS 或 MyoPS scar**，勿平均用力刷所有榜 |
| 最易衔接 Cardiac Nexus / UKB **形态学表型** | **Whole Heart**（七结构可直接对应表型管线） |
| 临床叙事最强（AF、digital twin） | **LA**，但易偏离当前心肌/UKB 主线 |

**执行建议**：先做 **CARE-Myocardium 约两周**，看官方 validation 是否出现**可解释**增益；若无，转 **Whole Heart**，避免在 MyoPS 上长期消耗。

---

## 10. 最终一句话建议

**可以做，但给固定预算**：用 CARE-Myocardium 作短期 **challenge sprint**，打磨 nnU-Net / CMR 多模态工程并尝试一个小而清晰的临床动机创新；**不要**升格为博士主线。若两周内 MyoPS/CineMyoPS validation 无清晰 Dice 与叙事增益，**转向 Whole Heart**。

---

## 附录 A：给 Deep Research / Codex 的英文 Prompt

将下文整体复制给研究型助手或代码代理使用。

```text
You are helping me decide and design a competitive method for the CARE-Myocardium 2026 challenge.

Context:
The challenge has two subtasks:
1. MyoPS: input LGE, T2, and bSSFP CMR sequences; segment myocardial scar and edema. Real-world complications include multi-center variation, missing sequences, and spatial misalignment across multi-sequence CMR.
2. CineMyoPS: input cine CMR only; segment scar at the end-diastolic cine frame.

I have a baseline technical report in Markdown summarizing MyoPS-Net, U-MyoPS, and CineMyoPS, including their paper-reported Dice values and the mismatch between paper settings and the current CARE repository wrappers. Treat that report as the starting point, not as ground truth replication.

Please conduct a deep literature and method-design review with the following goals.

First, read the baseline report carefully and extract:
- The exact task formulation differences between MyoPS-Net, U-MyoPS, and CineMyoPS.
- Their reported scar Dice and edema Dice.
- Any mismatch between paper protocol and CARE wrapper implementation.
- Which parts are reusable ideas and which parts are unsafe to claim as direct replication.

Second, search the latest arXiv and recent papers from 2024 to 2026 on:
- myocardial pathology segmentation from LGE/T2/bSSFP CMR,
- cine-only myocardial scar or edema segmentation,
- cardiac MRI foundation models such as CineMA, ViTa, CMR foundation models, and cardiac 3D+T representation learning,
- MedSAM/SAM-style adaptation for LGE scar segmentation,
- missing-modality multi-sequence medical image segmentation,
- multi-modal registration plus segmentation for cardiac MRI,
- topology/anatomy-constrained myocardial pathology segmentation,
- robust learning under noisy scar labels and class imbalance.

Third, propose a practical competition method for CARE-Myocardium, separated into two tracks.

For MyoPS:
Design a strong nnU-Net v2-based baseline first. Then propose improvements:
- modality-aware preprocessing for LGE/T2/bSSFP;
- missing-modality mask or modality dropout;
- LGE-centered scar branch and T2-centered edema branch;
- anatomy-constrained pathology prediction using myocardium/LV/RV priors;
- scar-inside-edema or pathology-in-myocardium consistency loss if compatible with CARE labels;
- optional registration or feature-level alignment if images are visibly misaligned;
- ensemble and test-time augmentation strategy;
- post-processing rules that are clinically defensible.

For CineMyoPS:
Design a baseline and an improved model:
- single-frame ED nnU-Net baseline;
- ED/ES or full cine temporal model;
- motion estimation or optical-flow / deformation proxy;
- temporal aggregation of texture, anatomy, and motion features;
- optional self-supervised pretraining on cine frames;
- optional use of public/pretrained models only if challenge rules allow it;
- robust validation plan to avoid overfitting the small training set.

Fourth, estimate the likely Dice improvement over a clean nnU-Net baseline:
- Give separate estimates for MyoPS scar, MyoPS edema, and CineMyoPS scar.
- Use conservative ranges, e.g. +0.01 to +0.03, +0.03 to +0.08, and explain the assumptions.
- Distinguish improvements due to pipeline correctness from genuine model innovation.

Fifth, produce an implementation plan for Codex:
- exact repository inspection steps;
- expected data layout;
- scripts to create standardized nnU-Net datasets;
- validation split strategy;
- metrics extraction from Dice and HD;
- ablation table design;
- expected output files and figures;
- what to stop doing if validation Dice does not improve after two weeks.

The final answer should be a structured Markdown report with:
1. Executive recommendation.
2. Literature synthesis with citations.
3. Proposed methods for MyoPS and CineMyoPS.
4. Expected Dice improvement table.
5. Implementation checklist.
6. Risk assessment.
7. A clear go/no-go decision rule after the first two weeks.
```

---

## 参考文献与链接

1. [CARE-Myocardium | CARE](https://zmic.org.cn/care_2026/track_myocardium/)
2. [CineMyoPS: Segmenting Myocardial Pathologies from Cine Cardiac MR](https://arxiv.org/html/2507.02289v1)
3. [ScarNet: Foundation Model for Myocardial Scar from LGE CMR](https://arxiv.org/abs/2501.01372)
4. [CARE-Whole Heart | CARE](https://zmic.org.cn/care_2026/track_wholeheart/)
5. [CARE-Left Atrium | CARE](https://zmic.org.cn/care_2026/track_leftatrium/)
