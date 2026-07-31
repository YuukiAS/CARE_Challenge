# CARE-QIF v2：跨中心强度信号与病灶实例监督可行性审计

## 一、为什么本轮只审计两个事实

截至 2026-07-31，当前仓库已经排除以下主线：

- Batch0–6 的弱权限模块没有形成独立科学机制；
- Batch7 的复杂 retrieval/proposal/refiner 对 scar 平均有害，且 refiner 净收益接近零；
- MMRD 的 reliable-label/no-T2 规则可保留，但简单 residual student 无法保持成熟分割能力；
- Cascade/DG 的 bounded correction 实际增益约为 0.001–0.005，性能上限过低；
- ARC/PRISM 的新 decoder/direct reconstruction 丢失成熟能力，PRISM 在 44 例 outer 上系统伤害 scar 与 edema；
- MyoPath A0–A3 在 35 例 full-volume inner-select 上形成系统性伤害：scar Dice `0.608383 -> 0.415120`，pure-edema Dice `0.422034 -> 0.356724`，同时远端假阳性和 HD95 恶化；
- MyoWall hard coordinates 即使使用 GT anatomy 也仅 25/32 例通过，CenterH LGE-only 系统失败，因此 hard wall representation 不能作为唯一病理入口。

最新 full-volume 结果同时暴露了最重要的目标域缺口：在完整三模态 inner-select 中，CenterB 的 nnU-Net baseline 仍能达到 scar `0.6913`、pure edema `0.5908`，但 CenterC 两例 scar 与 pure edema 均为 `0`。因此，下一代设计不能再围绕弱 residual、hard geometry 或另一个随机 decoder；必须先验证两个新的信息源是否真实存在：

1. **病例内 LGE/T2 强度秩与局部对比，能否在 CenterB 与 CenterC 中都保持病理可分性。**
2. **Scar connected-component/set supervision，能否在 full-volume cross-center 评价中提高 lesion recall，同时 no-object queries 控制 remote false positive。**

这两个事实都成立，才允许后续设计完整 CARE-QIF v2。任一失败，均不得通过增加 router、prototype、refiner、第二 backbone 或长训练掩盖。

## 二、文献依据与本地吸收边界

### 2.1 I-MMSeg

Fang et al., *Incorporating modality-specific intensity prior as text prompt for multimodal myocardial pathology segmentation*, Medical Image Analysis, 2026, DOI `10.1016/j.media.2026.104072`。

可吸收：

- LGE/T2 的 modality-specific intensity order；
- 病理边界附近的强度特征；
- 强度先验用于提高跨模态病理可分性。

本轮不复制：

- GPT/CLIP 文本提示；
- 大型视觉语言模块；
- 新 MyoPS380 外部数据。

本轮只测试确定性、病例内、无额外权重的 rank/robust-z/local-contrast 特征。

### 2.2 APEx 与 Mask2Former

Jaus et al., *Anatomy-guided Pathology Segmentation*, MICCAI 2024；Cheng et al., *Masked-Attention Mask Transformer for Universal Image Segmentation*, CVPR 2022。

可吸收：

- pathology queries；
- lesion/no-object set prediction；
- mask-level Hungarian matching；
- anatomy 作为 soft query context，而不是 hard crop。

本轮不复制：

- 第二个完整 transformer backbone；
- hard anatomy support domain；
- 多任务大规模 generalist decoder。

### 2.3 MyoPS-Net

Qiu et al., *MyoPS-Net: Myocardial pathology segmentation with flexible combination of multi-sequence CMR images*, Medical Image Analysis, 2023。

可吸收：

- modality-aware fusion；
- scar/edema pathology-specific outputs；
- myocardium consistency 与 scar–edema relation。

本轮只审计 scar query；edema 仅做 intensity/injury-zone separability，不训练完整 edema field。

## 三、冻结数据真值

仓库：

```text
/users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
```

数据：

```text
Dataset501_CAREMyoPS
all training cases: 220
canonical T2-present complete tri-modal cases: 80
expected CenterB complete cases: 35
expected CenterC complete cases: 45
```

Controller 必须从 canonical metadata 重新验证 80、35、45。若不一致，停止为 `DATA_CONTRACT_MISMATCH`，不得按记忆继续。

标签：

```text
healthy myocardium: label 1
LV cavity: label 2
pure edema: label 4
scar: label 5
injury zone: label 4 or 5
myocardium union: label 1 or 4 or 5
```

本轮只使用 80 个完整三模态 CenterB/CenterC 病例作为 hosted-facing 机制人群。全部 220 例仅用于 scar component-count/volume 描述统计，不进入 query pilot 的训练或评价。

不访问 official validation，不访问 fold0/fold1 outer，不上传任何预测。

## 四、Fact A：跨中心强度信号审计

### 4.1 两种 anatomy context

每个病例必须同时计算：

1. `GT_CONTEXT`：使用 GT myocardium/LV，仅用于回答信号是否存在；
2. `DEPLOYABLE_CONTEXT`：使用该病例对应 clean-OOF nnU-Net checkpoint 的 soft myocardium/LV probability，不得使用见过该病例的 checkpoint。

GT context 不得进入 query pilot 或任何未来正式模型输入。

### 4.2 预声明特征

所有特征均在病例内计算，不使用 center ID。

Scar 特征：

```text
lge_raw_nnunet_normalized
lge_percentile_rank_in_myocardium
lge_robust_z_median_mad
lge_local_contrast_3mm
lge_local_contrast_6mm
lge_gradient_magnitude
lge_minus_lv_blood_pool_robust_z
soft_distance_to_endocardium
soft_distance_to_epicardium
```

Injury-zone 特征：

```text
t2_raw_nnunet_normalized
t2_percentile_rank_in_myocardium
t2_robust_z_median_mad
t2_local_contrast_3mm
t2_local_contrast_6mm
t2_gradient_magnitude
soft_distance_to_endocardium
soft_distance_to_epicardium
```

定义：

- percentile rank 在对应 context 的 myocardium support 内计算；
- robust z 使用 `1.4826 * MAD + 1e-6`；
- local contrast 为中心体素减去物理半径 3 mm/6 mm 邻域中位数；
- distance 必须为 soft distance feature，不构成 hard mask。

### 4.3 标签与负样本

Scar：

```text
positive = label 5
negative = label 1
ignore = labels 0,2,3,4
```

Injury：

```text
positive = labels 4 or 5
negative = label 1
ignore = labels 0,2,3
```

每例训练采样最多 4096 个 positive 与 4096 个 negative voxels；不足时全部使用。评价必须使用该病例全部有效 myocardium voxels，不得在平衡采样上计算 AUROC/AUPRC。

### 4.4 固定 probes

不调超参数。

Raw baseline：

```text
scar: logistic regression on lge_raw_nnunet_normalized
injury: logistic regression on t2_raw_nnunet_normalized
```

Rank composite：

```text
scar: L2 logistic regression, C=1.0, class_weight=balanced, max_iter=2000
features: rank, robust-z, contrast3, contrast6, gradient, blood-pool-relative, two soft distances

injury: same fixed logistic regression
features: rank, robust-z, contrast3, contrast6, gradient, two soft distances
```

所有 scaler/median/imputation 参数只在训练中心拟合。

Primary transfer：

```text
CenterB -> CenterC
CenterC -> CenterB
```

Secondary：固定 seed `20260731` 的 center-stratified five-fold patient-held-out probe，仅用于稳定性描述，不覆盖 primary transfer。

### 4.5 指标

分别报告 scar 与 injury：

```text
macro case AUROC
macro case AUPRC
AUPRC lift over prevalence
median per-case AUROC
25th-percentile per-case AUROC
CenterB/CenterC gap
GT_CONTEXT vs DEPLOYABLE_CONTEXT delta
raw vs rank-composite delta
```

### 4.6 Fact A 门

Scar intensity fact PASS 必须同时满足：

```text
rank composite cross-center macro AUROC >= 0.65 in both directions
rank composite AUPRC lift >= 2.0 in both directions
median per-case AUROC >= 0.70 in CenterB and CenterC
CenterC 25th-percentile per-case AUROC >= 0.60
deployable-context AUROC is no more than 0.05 below GT-context
rank composite improves raw AUROC by >=0.03 in at least one direction
and is not worse than raw by >0.02 in the other direction
```

Injury intensity fact使用相同门。

只允许结论：

```text
INTENSITY_SIGNAL_PASS_BOTH
INTENSITY_SIGNAL_PASS_SCAR_ONLY
INTENSITY_SIGNAL_PASS_INJURY_ONLY
INTENSITY_SIGNAL_FAIL_BOTH
```

## 五、Fact B：Scar component-query matched pilot

### 5.1 Clean OOF feature source

对 80 个完整三模态病例，每例必须使用其 clean-OOF nnU-Net checkpoint 提取：

```text
full-resolution decoder feature F0
penultimate decoder feature F1
soft myocardium probability
soft LV probability
LGE rank and local contrast channels
```

任何 evaluated case 的 feature extractor 都不得见过该病例。

Feature cache 存 runtime，禁止提交 Git。

### 5.2 Cross-center train/test

两个方向：

```text
Direction BC: train CenterB 35, test CenterC 45
Direction CB: train CenterC 45, test CenterB 35
```

每个训练中心内部按 scar burden 与 component count 分层，固定 seed `20260731` 划分 80% train / 20% selection。Held-out center 只在 checkpoint freeze 后评价一次。

### 5.3 Common feature stem

输入：

```text
F0
upsampled F1
soft myocardium probability
soft LV probability
LGE percentile rank
LGE local contrast 3mm
```

结构：

```text
F0 -> 1x1 Conv -> 64
F1 -> 1x1 Conv -> 32 -> trilinear upsample
concat -> 3x3 Conv 99-to-64 -> GroupNorm(8) -> SiLU
-> two residual blocks, 64 channels
```

Backbone 与 OOF features 全冻结。

### 5.4 Dense parameter-matched control

```text
common stem
-> four ConvNeXt-style 3D blocks, 64 channels
   depthwise 3x3 + pointwise expansion 64->192->64
-> 1x1 Conv -> dense scar logit
```

输出由 dense logit 独立形成，不使用 stock scar logit。

### 5.5 Query arm

Query arm 保留与 control 完全相同的 common stem和 dense scar head，并增加：

```text
Q = 32 learned lesion queries
F1 token projection: 1x1 Conv -> d_model 128
adaptive pooling token grid: min(D,8) x 16 x 16
2 TransformerDecoder layers
nhead = 8
d_model = 128
ffn_dim = 512
dropout = 0.1
query class head: lesion / no-object
query center head: normalized z,y,x
query mask embedding: 128 -> 64
full-resolution mask logits: dot(mask_embedding, common_mask_feature) / sqrt(64)
```

最终 scar 概率：

$$
p_s(x)=1-(1-\sigma(z_{dense}(x)))\prod_{q=1}^{32}[1-\sigma(o_q)\sigma(m_q(x))].
$$

不得与 stock scar logit做加法或 fallback。

### 5.6 Component targets

GT scar 使用 26-connectivity 3D connected components，不删除小组件。

Query capacity validator：至少 99% 的 220 个训练病例 scar component count 必须 `<=32`；否则停止为 `QUERY_CAPACITY_INVALID`，不得静默丢弃组件。

Small lesion 固定定义：

```text
GT component physical volume < 1000 mm3
```

Hungarian cost：

$$
C=2L_{dice}+2L_{focal}+L_{center}+L_{class}.
$$

Loss：

```text
L_dense = Dice + Focal
L_query_mask = Dice + Focal for matched queries
L_center = L1 normalized coordinate
L_class = cross entropy, no-object weight 0.2
L_total_query = L_dense + L_query_mask + 0.5*L_center + L_class
```

Dense control只用 `L_dense`。

### 5.7 Full-volume hard negatives

No-object supervision必须覆盖：

```text
unmatched queries
high-LGE voxels in LV blood pool
high-LGE voxels outside soft myocardium
clean-OOF nnU-Net remote false-positive components
high-intensity components >5mm away from any GT scar
```

不得把普通背景全量重复采样造成类别捷径。

### 5.8 Training contract

四个正式 run：

```text
BC_DENSE
BC_QUERY
CB_DENSE
CB_QUERY
```

每个 run：

```text
optimizer: AdamW
lr: 3e-4
weight_decay: 1e-4
optimizer steps: 4000
physical batch: 1 full volume
accumulation: 4
effective batch: 4
warmup: 250
cosine minimum lr: 1e-6
bf16 on H100/A100
gradient clip: 12
checkpoint/eval every 500 steps
seed: 20260731
```

同方向 dense/query 必须重放相同病例顺序、augmentation seed 和 batch manifest。

Selection score只在训练中心内部 selection cases计算：

$$
S=Dice+0.2R_{lesion}+0.2R_{small}-0.1\min(V_{remoteFP}/5000,1).
$$

选择 checkpoint 后必须 reload，再对 held-out center full-volume evaluation。

### 5.9 指标

```text
scar Dice
HD95 mm
exact HD mm
precision
recall
lesion-wise recall
small-lesion recall
component count
remote FP count/volume
blood-pool-adjacent FP
volume ratio
case-wise help/harm
query precision
matched-query recall
duplicate-query rate
no-object false activation rate
```

Fact B PASS 必须同时满足 pooled 80 例与两个方向：

```text
pooled query-vs-dense lesion recall >= +0.08
pooled small-lesion recall >= +0.12
pooled Dice delta >= -0.01
pooled HD95 delta <= +2mm
pooled remote FP volume <= dense * 1.10
pooled remote FP count delta <= +0.20 per case
each direction lesion recall delta >= +0.05
each direction harm fraction < 0.40
query intervention changes final labels
query precision >= 0.50
duplicate-query rate <= 0.20
```

只允许结论：

```text
COMPONENT_QUERY_FACT_PASS
COMPONENT_QUERY_RECALL_ONLY_FP_FAIL
COMPONENT_QUERY_NO_GAIN
COMPONENT_QUERY_SYSTEMATIC_HARM
```

## 六、联合裁决

```text
GO_QIF_V2_MODEL_PILOT
```

仅当：

```text
Fact A = INTENSITY_SIGNAL_PASS_BOTH
Fact B = COMPONENT_QUERY_FACT_PASS
```

```text
GO_SCAR_ONLY_REDESIGN
```

当 scar intensity 与 query 通过，但 injury intensity失败。

```text
GO_INTENSITY_DENSE_ONLY
```

当 Fact A 双病种通过，但 query 不通过。

```text
NO_GO_QIF_V2
```

当 scar intensity失败，或 query系统伤害，或两个事实均不成立。

本任务无论结论如何，都不授权完整 CARE-QIF v2、fold expansion、official validation、Docker、第二 backbone、ROI/refiner、prototype、alignment 或 hosted claim。

## 七、禁止解释

以下内容不能作为成功：

- 训练 loss下降；
- gradient非零；
- query存在；
- patch recall上升；
- GT-context signal但 deployable-context失败；
- 只在 CenterB 有效；
- recall提高但 remote FP爆炸；
- 仅 aggregate mean 改善而某一 transfer direction系统失败；
- 使用见过病例的 backbone feature；
- 使用 test center调 checkpoint或阈值。
