# Domain adaptation 对 CARE2026 当前瓶颈的价值判断

Date: 2026-05-19

## 结论

Domain adaptation 对 CARE 当前挑战赛问题 **有用，但不能作为独立主线**。它最适合解决的是中心/扫描协议/强度风格带来的分布偏移，以及在官方 validation 无标签场景下做轻量 test-time 或 source-free 校准；但它不能直接补上 CARE MyoPS 训练集的核心缺口：**T2/完整模态监督不足、模态缺失与中心强相关、病灶标签缺失也与中心绑定**。

因此下一阶段不建议启动一个泛化的“大 DA 模型”或长训练。更合理的策略是把 DA 作为新 `src/` 模型的辅助机制：

- 显式模态 mask + center/modality-group aware sampling/reporting 是前提。
- DA 只对强度风格、BN/statistics、feature consistency、target-test-time normalization 做小步实验。
- scar 和 edema 必须分开处理：scar 主要 LGE 驱动，edema 必须 T2-aware。
- HD/HD95 和 connected-component diagnostics 必须和 Dice 同时作为 gate。

## 论文阅读范围

本轮阅读了 `docs/literature/domain_adaptation/` 下的论文：

| paper | 对 CARE 的相关性 |
| --- | --- |
| `Domain Adaptation for Medical Image Analysis A Survey - Guan.pdf` | 高。给出医学图像 DA 的问题设定：single/multi-source、single/cross-modality、supervised/semi/unsupervised、image-level/feature-level。 |
| `Source-free unsupervised domain adaptation A survey - Fang.pdf` | 中高。适合思考 validation 只有无标签数据时的 source-free/test-time adaptation，但风险是 pseudo-label confirmation bias。 |
| `Semi-Supervised Unpaired Medical Image Segmentation Through Task-Affinity Consistency - Chen.pdf` | 中高。对“少量有标签 + 无标签目标域”的 unpaired consistency 有启发，尤其是 class-specific structural/contextual feature consistency。 |
| `Unpaired Volumetric Harmonization of Brain MRI with Conditional Latent Diffusion - Wu.pdf` | 中。说明 3D image-level harmonization 可保留解剖并转移 style，但论文对象是健康脑 T1 MRI，不应直接照搬到 CMR 病灶分割。 |
| `DomainATM Domain adaptation toolbox for medical data analysis - Guan.pdf` | 中。更多是工具/方法目录，启发是先做快速 feature/image-level adaptation 对比，而不是直接重训练复杂模型。 |
| `Federated learning for medical image analysis A survey - Guan.pdf` | 低到中。CARE 当前数据已在本地，隐私式跨站训练不是主要瓶颈；可借鉴“center as client”的正则化思想，但不应作为近期主线。 |
| Tensor-train / Rosenblatt transport 三篇 | 低。它们面向高维概率密度、采样和贝叶斯反问题，不直接解决当前 CMR 分割的模态缺失、病灶小目标和 HD outlier。 |

## CARE 数据事实

### MyoPS

`MyoPS_train` 不是一个标准的完整多模态训练集，而是中心、模态、标签可用性纠缠在一起：

| modality group | cases | share | main centers | 对建模的影响 |
| --- | ---: | ---: | --- | --- |
| C0 + LGE + T2 | 80 | 36.4% | CenterB 35, CenterC 45 | 唯一能可靠学习三序列融合和 T2 edema cue 的子集。 |
| C0 + LGE, no T2 | 24 | 10.9% | CenterE/F/G | scar 可从 LGE 学，edema 基本无可靠监督。 |
| LGE only | 116 | 52.7% | CenterA/H | 训练主体是 LGE-only，和完整 validation 输入分布不一致。 |
| LGE + T2, no C0 | 0 | 0.0% | none | 没有自然的 C0-missing/T2-present 学习路径。 |

官方 MyoPS validation 15 例是完整 LGE+C0+T2，但训练集中完整模态只有 80/220。这个问题不是普通 scanner style shift；它是 **目标域完整模态、源域监督却被 LGE-only 主导** 的结构性错配。

### CineMyoPS

`CineMyoPS_train` 是 cine-only，Center α 40 例、Center β 24 例，标签只有 myocardium/LV blood/scar，没有 RV/edema。当前 hosted `myocardium_cinemyops` 更像对 raw `2221` pathology/scar 且 HD 很敏感的评价，而不是本地 `class_1` myocardium proxy。Round8 已经发现 validation candidate 的主要问题是 disconnected scar components，而不是大范围 anatomy bbox 漂移。

## 与当前 baseline 瓶颈的对应关系

### MyoPS-Net

MyoPS-Net 的核心假设是多序列特征提取和融合。但 CARE 中 52.7% 训练样本是 LGE-only，完整三序列只有 36.4%。Round8 完整模态 expert 只用 64 个 fold0 train cases，2D validation scar Dice `0.0996`、edema Dice `0.0566`，最终 3D all-case 也失败。

DA 能帮助的部分：

- 可以把 CenterA/H、CenterB/C、CenterE/F/G 当成 source domains 做 center-aware normalization 或 domain-specific BN/adapters。
- 可以做 style augmentation/harmonization，降低 LGE 不同中心的强度差异。
- 可以用 target validation 的无标签完整模态做轻量 BN/statistics adaptation 或 entropy-minimization test-time adaptation。

DA 不能解决的部分：

- 不能从 LGE-only 数据中凭空学到 T2 edema cue。
- 不能把缺失标签中心当成正常负样本，否则 edema 会被中心 shortcut 污染。
- 单纯 adversarial feature alignment 可能把 pathology cue 一起抹掉，尤其 scar/edema 是小目标。

判断：MyoPS-Net 不应继续作为 DA 改造对象。需要在 `src/` 新模型里吸收 DA 思想，而不是继续 patch `third_party/MyoPS-Net`。

### U-MyoPS

U-MyoPS 的 alignment/prior 思路对完整/T2-present cases 有帮助，但 Round8 证明 Stage1 prior 失败类型很杂：empty-GT false positive、prior/pathology overlap 低、under/over-segmentation、localization mixed 都存在。一个通用 DA gate 不会稳定修复这些问题。

DA 能帮助的部分：

- source-free 或 semi-supervised consistency 可用于验证 Stage1 anatomy/prior 在 validation target 上是否稳定。
- class-specific structural/contextual consistency 可以作为 soft regularizer，避免 prior hard gate 误删小 scar。

DA 不能解决的部分：

- prior 错了时，feature alignment 会把错误 prior 强化。
- pseudo-label self-training 对小病灶很危险；一个小 false positive/false negative 就会显著影响 Dice/HD。

判断：U-MyoPS 的 DA 价值主要是作为新模型中的 reliability-aware prior regularization，不适合继续独立扩 folds。

### CineMyoPS

CineMyoPS 当前最明确的问题是 hosted metric 语义和本地 proxy 不一致，以及 scar 输出多 connected components 导致 HD 爆炸。DA 的价值比 MyoPS 更有限，因为问题首先不是 center style，而是目标标签/评价语义和 pathology 输出形态。

DA 能帮助的部分：

- test-time BN/statistics adaptation 可能改善 cine center/style 差异。
- temporal/video domain adaptation 思路可作为后续 motion/strain route 的参考。

DA 不能解决的部分：

- 不能自动校准 hosted `myocardium_cinemyops` 到底如何解释 `2221`。
- 不能替代 connected-component、volume guard、HD-aware topology repair。

判断：CineMyoPS 短期继续用 Round8 LCC/HD repair 做 hosted calibration；若仍低，应转向 motion/strain-aware `src/` 模型，而不是做通用 DA。

## 推荐进入下一轮的小实验

### 1. Center/modality-aware normalization audit

目标：判断现有 nnU-Net/MyoPS predictions 的错误是否和中心/模态 group 的 intensity/style shift 相关。

建议做法：

- 按 `C0+LGE+T2`、`C0+LGE`、`LGE` 分组报告 intensity histogram、label prevalence、Dice/HD。
- 对 LGE、C0、T2 分别做 z-score、percentile clipping、histogram matching 的离线对比。
- gate：不能降低 complete/T2-present scar 和 edema Dice；HD/HD95 不得恶化。

### 2. Domain-specific BN/adapters，而不是全模型 adversarial DA

目标：让模型学习中心/模态风格差异，同时保留 pathology head。

建议做法：

- backbone 共享，使用 center/modality-group specific BN 或轻量 adapter。
- scar/edema heads 分离，edema head 只在 T2-present/GT-positive 子集上被主要优化。
- validation target adaptation 时只更新 normalization/adapters，不更新 final pathology classifier。

理由：SFUDA 论文中的 BN statistics、surrogate source、pseudo-label/self-training 有参考价值，但 CARE 小病灶和无标签 validation 太容易被 confirmation bias 带偏。

### 3. Semi-supervised unpaired consistency 只作为 soft loss

目标：利用 official validation 的无标签完整模态样本，不直接相信 pseudo-label。

建议做法：

- teacher 固定为当前 nnU-Net 或新模型 EMA。
- 对 validation target 只使用 augmentation consistency、feature consistency、class-specific structural/contextual consistency。
- 只在高置信 myocardium/anatomy 区域使用 consistency；scar/edema lesion 区域采用高阈值或 uncertainty mask。

不建议：直接把 validation pseudo-label 混入 supervised loss 训练 pathology head。

### 4. Image-level harmonization 从轻量版开始

HCLD 这类 3D diffusion harmonization 说明“style translation + anatomy preservation”方向有理论价值，但直接用于 CARE 不现实：

- 需要大量 3D CMR 训练和目标 style 定义；
- 病灶对比度可能被 harmonization 模型当作 style 消掉；
- 当前 leaderboard 差距更大来自模态/标签/HD，而不是单纯 scanner style。

建议先做轻量 harmonization：

- per-modality percentile clipping + z-score/robust z-score；
- LGE/T2 histogram matching to complete-case reference；
- Fourier style augmentation 或 AdaIN-style feature perturbation；
- 严格检查 lesion volume、component count、HD 是否变化。

### 5. Federated / tensor-train 不进入近期模型路线

Federated learning 的主要价值是隐私保护下多中心协同训练；CARE 当前数据已在本地，近期不用搭 FL 系统。可以借鉴 `center as client` 的个性化/regularization 思想，但不做工程主线。

Tensor-train / Rosenblatt transport 更偏高维概率采样、密度近似和贝叶斯反问题。除非后续做 uncertainty quantification 或 Bayesian calibration，否则不应占用当前分割模型改进预算。

## 推荐路线

短期：

1. MyoPS 继续以 nnU-Net 为 operational baseline。
2. 新模型进入 `src/`，不是继续改 MyoPS-Net/U-MyoPS。
3. 先做 center/modality-aware audit 和轻量 normalization/adaptation 消融。
4. 所有实验按 `myops_scar`、`myops_edema`、`myocardium_cinemyops` 分开判断，不看 foreground_mean 做主结论。

中期：

1. 构建 modality-mask-aware backbone。
2. scar/edema 双 head 或双 route。
3. center/modality-group BN/adapters + target BN/statistics adaptation。
4. anatomy/prior 作为 soft reliability constraint，而不是 hard deletion。
5. 每轮仍限制为小实验：fold0 或 protocol validation loop，<=8h，预测非空、label semantics、cache isolation、HD diagnostics 先过 gate 再扩 folds。

最终判断：

DA 是下一阶段模型设计的 **配套机制**，不是当前 CARE2026 的单独解法。最值得做的是“数据分组 + normalization/adapters + conservative target adaptation”；最不值得做的是直接套 adversarial DA、重型 diffusion harmonization、或用 pseudo-label 自训练小病灶 head。
