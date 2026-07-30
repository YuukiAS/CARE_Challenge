# CARE Myocardium 前沿重置型高增益 Deep Research Prompt

你是 CARE Challenge Myocardium 项目的 Deep Research Lead、医学影像架构研究员和反路径依赖设计审查者。

本轮不是继续完善 CARE-MyoPath-PR，也不是从 Batch7、MMRD、Cascade、ARC、PRISM 中拼出一个折中方案。当前历史证据只用于冻结数据真值、安全规则和已知失败模式；**不得把旧架构当作下一代设计模板**。

你的任务是重新从医学信号、错误空间和 2024–2026 年前沿方法出发，寻找一种真正可能改变性能档位的单主干范式，并判断它是否应取代 Proposal–Refinement 方案。

最终产出中文 Markdown 文档：

```text
CARE_FRONTIER_RESET_HIGH_GAIN_DESIGN_20260731.md
```

本轮不写代码、不训练、不修改仓库、不提交 Slurm、不上传 validation 或 Docker。

---

## 一、必须读取的本地证据

仓库：

```text
YuukiAS/CARE_Challenge
branch: main
local reference: /users/a/e/aereinh/CARE
```

先同步并阅读：

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
```

必须读取：

```text
results/20260730_care_failure_forensics_deep_research_packet/CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v4.pdf
results/20260730_care_failure_forensics_deep_research_packet/v4_atlas_pages_a3_landscape.pdf
results/20260730_care_failure_forensics_deep_research_packet/DEEP_RESEARCH_MODEL_DESIGN_INPUT_20260730_v4.md
results/20260730_care_failure_forensics_deep_research_packet/v4_component_survival_ledger.csv
results/20260730_care_failure_forensics_deep_research_packet/v4_large_gain_bounds.csv
results/20260730_care_failure_forensics_deep_research_packet/standardized_casewise_metrics.csv
results/20260730_care_failure_forensics_deep_research_packet/v4_mosaic_m0_m10_summary.csv
```

同时读取当前 Deep Research 结果：

```text
当前对话/项目背景中的 deep-research-report.md
```

但不得直接接受其中 CARE-MyoPath-PR 为默认答案。必须把它当作一个候选方案进行反驳、比较和可能淘汰。

若仓库已合并指标真值任务，还必须读取：

```text
results/20260731_care_metric_truth_reconciliation/metric_truth_table.csv
results/20260731_care_metric_truth_reconciliation/metric_semantics_contract.json
results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json
```

若尚未生成，所有 baseline 数字必须标记为 provisional，不得混用 D0 parity、clean OOF、outer、full-data 和 hosted validation。

---

## 二、视觉阅读是强制步骤

必须视觉阅读 Project 背景中的：

```text
SRR-v2
SRR-v2.5
SRR-v3
CARE-MMRD
CARE-SRR-Cascade
CARE-ARC
MoSAIC
```

视觉阅读这些图的目的不是继承其结构，而是理解历史路线在信息流、权限分配和复杂度上的局限。

必须完整视觉阅读独立病例图册：

```text
results/20260730_care_failure_forensics_deep_research_packet/v4_atlas_pages_a3_landscape.pdf
```

至少精读 24 例，并列出 case ID。必须覆盖：

- CenterB/CenterC complete tri-modal；
- LGE-only；
- LGE+C0；
- 小 scar；
- 多连通 scar；
- diffuse pure edema；
- remote FP；
- blood-pool confusion；
- nnU-Net 与 MoSAIC 分歧；
- 可能的 alignment 错误。

对每例写明：

```text
主要错误类型
现有模型共同错误还是互补错误
需要的是更强表征、病灶实例建模、边界生成、域泛化还是对齐
哪种新范式可能处理
```

若无法访问 atlas，停止为：

```text
BLOCKED_VISUAL_ATLAS_UNAVAILABLE
```

---

## 三、重置原则

本轮只保留以下历史事实，不保留历史架构模板：

1. scar 与 pure edema 是不同任务，必须独立建模；
2. no-T2 病例不得作为 pure-edema 阴性监督；
3. 完整成熟 decoder 不能被随意重置；
4. 模块存在、梯度非零、logit 微变不是有效机制证据；
5. 简单 selector、ensemble、阈值、TTA 和弱 residual correction 不具备约 0.1 Dice 的上限；
6. 一个完整 backbone 是复杂度上限；
7. nnU-Net/MoSAIC 可以作为初始化、backbone、teacher 或 baseline，但不能垄断 final prediction；
8. scar 和 edema 都必须有实质提升路径，不能只优化 scar。

除这些边界外，允许完全放弃：

```text
SRR dictionary
prototype memory
anchor correction
传统 two-stage U-Net cascade
PRISM/ARC 结构
CARE-MyoPath-PR 的 proposal/refiner 形式
```

如果前沿证据支持更好的范式，应明确取代它们。

---

## 四、必须探索的四类范式

至少深入研究以下四类范式。每类必须查一手论文、官方代码、许可证、消融和增益量级。

### 范式 A：病灶实例集合预测

研究 scar/edema 是否应从体素分类改写为“病灶实例集合 + mask”问题，例如：

- lesion queries；
- DETR/Mask2Former 风格 set prediction；
- connected-component aware matching；
- lesion center/extent/mask 联合预测；
- false-positive query suppression；
- 小病灶实例召回；
- edema 是否适合用少量大区域 query，而 scar 使用多小 query。

核心问题：

> 将 scar 从一个极小语义类别改写成实例集合，是否能真正突破 nnU-Net 的小病灶与多组件漏检？

不得因为 Transformer 流行就直接选择。必须评估 3D 小样本、计算量、query collapse 和 edema diffuse region 的适配性。

### 范式 B：解剖坐标系中的隐式轮廓/场生成

研究是否可以先把心肌映射到标准化极坐标或壁厚坐标，再预测病理场：

- endocardium–epicardium normalized coordinates；
- polar myocardium unfolding；
- implicit neural field；
- signed-distance/level-set decoder；
- contour generation；
- topology-aware mask generation；
- wall-segment conditional prediction。

核心问题：

> 当前失败是否主要来自笛卡尔全图中的搜索空间过大，而不是 backbone 不够强？

必须评估它对 scar 弧段、transmural extent、edema 带状区域、远端 FP 和跨中心几何差异的作用。

### 范式 C：条件生成式病灶分割

研究 diffusion、energy-based 或 iterative mask denoising 是否能成为病灶形成机制：

- conditional mask diffusion；
- anatomy-conditioned segmentation diffusion；
- discrete diffusion on masks；
- energy-based refinement；
- iterative denoising decoder；
- uncertainty-aware multiple hypotheses。

核心问题：

> 生成式 mask prior 是否能解决边界、连通域和病灶形态，而不是再做一个普通 dense head？

必须评估小数据稳定性、推理成本、是否需要第二完整 backbone、是否只是高成本后处理。

### 范式 D：强度/纹理先验与病种专属表征

研究 I-MMSeg、intensity prompt、contrastive pathology representation、self-supervised lesion pretraining、frequency/texture cues：

- modality-specific intensity prior；
- prompt-conditioned segmentation；
- LGE/T2 histogram or rank normalization；
- lesion-vs-normal myocardium contrastive pretraining；
- hard-negative representation learning；
- domain generalized intensity encoding；
- external cardiac foundation model only if rules and license allow。

核心问题：

> CARE 真正缺失的是新的空间生成机制，还是现有特征根本没有把 LGE/T2 病理信号分开？

必须区分“更强表征”与“更复杂 backbone”。

---

## 五、允许额外探索的范式

可以增加但不能替代上述四类：

- neural cellular automata / morphological recurrent refinement；
- graph neural network over myocardial segments；
- hypernetwork conditioned on modality availability；
- domain-specific normalization without center ID；
- test-time adaptation；
- active contour network；
- mixture-of-experts with one shared backbone；
- weakly supervised lesion detection；
- uncertainty-calibrated multi-hypothesis decoding。

不得为了“天马行空”堆叠多个完整系统。

---

## 六、针对性文献检索要求

必须联网检索 2024–2026 最新文献，优先：

```text
Medical Image Analysis
IEEE TMI
MICCAI
MIDL
CVPR/ICCV/ECCV
NeurIPS/ICLR 中的医学或 dense prediction 工作
官方 arXiv 与官方 GitHub
```

至少覆盖：

1. myocardial scar/edema segmentation；
2. small lesion instance-aware segmentation；
3. lesion set prediction；
4. anatomy-coordinate or polar myocardial modeling；
5. implicit contour/level-set segmentation；
6. diffusion segmentation；
7. intensity prior / prompt-based pathology segmentation；
8. incomplete multimodal segmentation；
9. cross-center domain generalization；
10. component-level loss and hard-negative mining。

每篇候选论文记录：

```text
title
year/venue
official paper
code
license
pretrained weights
input/output assumptions
dataset size
reported baseline
reported absolute gain
ablation quality
single or multiple backbones
CARE scar relevance
CARE edema relevance
integration cost
failure risk
```

不得以二手博客、ResearchGate 摘要或模型宣传代替原论文。

---

## 七、必须对 CARE-MyoPath-PR 做反方审查

将当前 Proposal–Refinement 方案作为候选 P0，逐项质疑：

1. 它是否只是更完善的 coarse-to-fine，而不是性能档位变化？
2. proposal 是否仍依赖已有 decoder feature，因此无法发现 baseline 完全缺失的信号？
3. ROI refinement 是否会重复 Batch7/Cascade 的候选错误放大？
4. scar 小 ROI 与 edema 大 ROI 是否只是工程经验，而非新科学机制？
5. 它是否真的能为 edema 提供与 scar 同等级的创新？
6. 单主干 + proposal/refiner 的上限是否仍被 global backbone 限制？
7. 为什么它可能达到约 0.1，而不是约 0.02？
8. 哪一种前沿范式能在同复杂度下提供更强的新信息路径？

最终必须给出：

```text
KEEP_PR
REPLACE_PR
HYBRIDIZE_WITH_PR
NO_HIGH_GAIN_DESIGN_SUPPORTED
```

不得因为 PR 已经有详细合同就默认保留。

---

## 八、候选方案比较

最终至少形成四个 paradigm-level candidate：

```text
C1 病灶实例集合预测
C2 解剖坐标隐式场/轮廓生成
C3 条件生成式 mask 模型
C4 强度/纹理先验的单主干病种模型
P0 CARE-MyoPath-PR
```

用统一标准比较：

```text
new information source
scar large-gain mechanism
edema large-gain mechanism
small-lesion recall
remote FP control
boundary/HD95
missing modality safety
center generalization
single-backbone compliance
parameter/FLOP budget
training stability
implementation time
causal ablation clarity
novelty
paper story
```

必须淘汰至少三个方案，只保留：

- 一个首选高增益架构；
- 一个更保守备选。

---

## 九、首选设计硬约束

首选架构必须：

1. 只有一个完整 backbone；
2. scar 与 pure edema 拥有不同的病灶形成机制；
3. no-T2 edema loss/output 行为精确定义；
4. 不以 nnU-Net/MoSAIC prediction 为唯一输入或最终 authority；
5. 不依赖多个完整模型 ensemble 形成主性能；
6. 新增参数原则上不超过主 backbone 的 50%；
7. 推理成本原则上不超过主 backbone的 2 倍；
8. 能解释为什么不是约 0.005–0.02 的修补；
9. 能写成可直接交给 Codex 的无空白合同；
10. 每个组件都有独立因果对照。

可以突破 Proposal–Refinement 的具体结构。

---

## 十、约 0.1 Dice 的高增益逻辑

不要求虚假承诺，但必须针对 scar 与 edema 分别建立性能预算：

```text
current fair baseline
current hosted baseline
main error pools
new paradigm attacks which errors
optimistic gain
plausible gain
conservative gain
non-overlap assumption
failure conditions
```

不得将：

```text
voxel oracle
train-on-case full-data probe
threshold/TTA/postprocess
a small paper gain on another dataset
```

直接当作 CARE 可实现增益。

一个方案只有在以下情况下才可称为“高增益候选”：

- 它引入现有模型没有的新空间/实例/生成机制；
- scar 与 edema 都有明确机制路径；
- 预期主要收益不是 recipe；
- 文献至少有两个独立来源支持类似机制；
- 本地 atlas 中存在对应错误池；
- 可以设计短机制实验进行证伪。

---

## 十一、输出首选架构时必须写到实现级

必须给出：

```text
model name
scientific claim
input modalities
availability contract
working space
backbone exact class
pretrained coverage
module graph
scale/channel/tensor shapes
scar mechanism
edema mechanism
anatomy/context permissions
final logits composition
loss formulas
sampler
training stages
optimizer/lr/steps
checkpoint selection
decode/postprocess
parameter/FLOP estimate
failure branches
```

禁止：

```text
TBD
optional
if needed
choose suitable
Codex decide
reasonable module
```

若存在可选组件，必须给出默认关闭/开启、触发门和失败分支。

---

## 十二、最小可证伪实验

首选方案必须给出一个 12–24 小时内可运行的机制实验，不要求完整候选性能，但必须直接验证核心假设。

实验必须回答：

```text
新范式是否真的改善其目标中间指标
是否进入 final labels
是否改善对应病种
是否没有依赖后续组件救回
```

例如：

- instance-set 方法：lesion recall、query precision、duplicate query、final mask Dice；
- implicit field：boundary HD95、thin scar continuity、remote FP；
- diffusion：mask topology、multi-hypothesis recall、runtime；
- intensity prior：跨中心 AUROC、scar/edema separability、final-label gain。

必须给出继续/停止阈值。

---

## 十三、必须吸取的执行教训

最终文档专门写一章“如何防止设计再次被 Codex 简化”。至少冻结：

```text
exact classes
module wiring
final-logit authority
loss to parameter mapping
trainable/frozen list
split/case lists
budget
Slurm strategy
intermediate metrics
on/off controls
validator
known-bad
stop/continue rules
```

known-bad 必须拒绝：

1. 新范式被降级成普通卷积 head；
2. 只实现论文名字，没有核心计算；
3. module 不进入 final logits；
4. scar 和 edema 共用同一机制；
5. no-T2 被当 edema negative；
6. decoder reset；
7. 多 backbone 偷渡；
8. smoke 冒充正式证据；
9. outer 调参；
10. 只靠 gradient/nonzero delta；
11. 中间指标失败后仍进入长训练；
12. postprocess 冒充架构增益；
13. hosted/train-on-case 冒充 clean；
14. 架构空白留给执行者。

---

## 十四、最终文档结构

用自然中文写作，建议 15,000–30,000 字：

1. 执行摘要；
2. 为什么需要一次前沿重置；
3. 本地证据与 atlas 重新归因；
4. 当前 PR 方案的反方审查；
5. 2024–2026 前沿文献图谱；
6. 病灶实例集合预测；
7. 解剖坐标隐式场/轮廓；
8. 条件生成式分割；
9. 强度/纹理先验；
10. 候选比较与淘汰；
11. 唯一首选高增益架构；
12. scar 完整设计；
13. edema 完整设计；
14. 训练和推理合同；
15. 约 0.1 Dice 增益预算；
16. 最小可证伪实验；
17. Codex 防简化合同；
18. 更保守备选；
19. GO/NO-GO；
20. 参考文献和官方代码。

---

## 十五、最终裁决

只能输出以下之一：

```text
GO_FRONTIER_REPLACEMENT
GO_PR_WITH_MAJOR_PARADIGM_UPGRADE
GO_PR_MECHANISM_PILOT_ONLY
NO_GO_FOR_HIGH_GAIN_MODEL
```

含义：

- `GO_FRONTIER_REPLACEMENT`：发现比 PR 更强、可落地的新范式，应停止把 PR 当主线；
- `GO_PR_WITH_MAJOR_PARADIGM_UPGRADE`：PR 只保留骨架，核心病灶机制由前沿范式替换；
- `GO_PR_MECHANISM_PILOT_ONLY`：没有更可信替代，只允许 A0–A3 短实验，不批准完整长训；
- `NO_GO_FOR_HIGH_GAIN_MODEL`：当前无可信高增益设计，应停止架构开发。

不得为了乐观而虚构 GO，也不得因为历史失败而默认 NO-GO。
