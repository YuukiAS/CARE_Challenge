# GPT Image Prompt — CARE-DG Publication Architecture Figure

请从空白画布重新生成一张可直接用于 MICCAI、Medical Image Analysis 或 IEEE TMI Methods 部分的 publication-quality 深度学习架构图。

## 参考材料使用规则

请参考当前 ChatGPT Project 背景材料中的以下旧图，只借鉴其出版级视觉质量、特征图画法、留白、箭头层级和颜色克制：

- SRR-v2
- SRR-v2.5
- SRR-v3
- CARE-MMRD
- CARE-SRR-Cascade
- MoSAIC

不得描摹或复刻旧图，不得把旧架构中的 dictionary、prototype memory、SIP、MoSAIC、完整 MMRD teacher、多个专家或复杂 arbiter 带入新图。必须从空白画布重新设计。

## 标题

**CARE-DG: Dual-Gated Residual Correction for Myocardial Scar and Edema Segmentation**

副标题：

**Frozen nnU-Net anchor + explicit false-negative / false-positive error gates + pathology-specific bounded competitive correction**

## 总体风格

- 白色背景。
- 横向超宽版式，约 18:9，适合论文双栏跨栏图。
- 论文级矢量风格，边缘清晰，字体统一，标签全部可读。
- 不要画成普通流程图；必须画真实 image/tensor flow、3D feature maps、encoder/decoder stages、error probability maps、logit correction 和 training supervision。
- 配色克制：
  - blue = frozen nnU-Net anchor and protected anatomy;
  - teal = compact CARE shared encoder;
  - red / magenta = scar branch;
  - orange / amber = edema-zone branch;
  - green = reliable-label supervision and target-aligned training;
  - purple = explicit FN/FP gates and correction magnitude;
  - gray = identity/fallback and components explicitly not used.
- 箭头要有层级：主推理流为实线粗箭头；训练监督为绿色虚线；fallback 为灰色回路；禁止路径为红色叉号。
- 使用适量半透明 3D feature-map blocks、概率热图、边界图和 pathology masks。
- 不拥挤，不使用大段文字，不加入无关图标。

## 画面组织

使用两个主 Panel。

# Panel A — Inference Architecture

Panel A 占画面约 70%，从左到右。

### 1. Complete tri-modal inputs

左侧展示同一病例的三张 cardiac MR slices：

- **LGE** — scar evidence
- **T2** — edema evidence
- **bSSFP / C0** — anatomy evidence

下方有一个小的 `Modality Availability [1,1,1]` 向量。标注：

**Official validation/test: all complete LGE + T2 + bSSFP**

### 2. Frozen nnU-Net anchor

三模态输入同时进入一个蓝色冻结模块：

**Frozen 5-fold nnU-Net Anchor**

内部画一个简化的 3D U-Net / Residual Encoder-Decoder，但不要展开过多。输出必须分成：

- six-class anchor logits / probabilities;
- ensemble uncertainty / disagreement;
- soft myocardium support;
- signed distance to myocardium shell;
- anchor segmentation showing myocardium, LV, RV, scar and edema.

在模块角落放锁图标，并写：

**Frozen · anatomy identity · exact fallback**

### 3. CARE-DG compact multimodal encoder

原始三模态分别进入三个浅层 stem：

- LGE stem — 8 ch
- T2 stem — 8 ch
- C0 stem — 8 ch

anchor logits、uncertainty、soft support 进入独立的：

**Anchor Context Stem — 16 ch**

四路 feature maps concatenate 后进入：

**Compact Shared 3-scale Encoder**

画三个尺度的 feature blocks，通道标注：

```text
32 → 64 → 96
```

标出：

- anisotropy-aware 3D residual blocks;
- in-plane downsampling `(1,2,2)`;
- early `(1,3,3)` kernels and deeper `(3,3,3)` context.

### 4. Two independent pathology decoders

共享 encoder 后明确分成两个平行、完全独立的 decoder。

#### Scar Decoder

红色 / magenta 分支，输入侧强调 LGE + anchor scar evidence。输出四张小 heatmap：

- `q_scar^FN` — missed scar probability
- `q_scar^FP` — false scar probability
- `m_scar^FN` — add magnitude
- `m_scar^FP` — remove magnitude

在旁边画 signed correction：

$$\delta_{scar}=q_{scar}^{FN}m_{scar}^{FN}-q_{scar}^{FP}m_{scar}^{FP}$$

#### Edema-Zone Decoder

橙色分支，输入侧强调 T2 + anchor edema-zone evidence。输出：

- `q_edema^FN`
- `q_edema^FP`
- `m_edema^FN`
- `m_edema^FP`

公式：

$$\delta_{edema}=q_{edema}^{FN}m_{edema}^{FN}-q_{edema}^{FP}m_{edema}^{FP}$$

两个 decoder 的 feature maps 形状相似，但参数独立。中央写：

**Shared image representation, pathology-specific error semantics**

### 5. Bounded competitive logit correction

两个病种分支分别进入紫色 correction block：

**Bounded Competitive Logit Correction**

图中清楚显示不仅改变 pathology logit，也反向改变当前最高 non-pathology competitor logit：

$$z_k^{final}=z_k^{anchor}+s_k\,clip(\delta_k,-M_k,M_k)$$

$$z_{c_k}^{final}=z_{c_k}^{anchor}-s_k\,clip(\delta_k,-M_k,M_k)$$

画一个小型 before/after logit bar chart，展示错误 anchor margin 被翻转。

标注：

- soft myocardium support, not hard crop;
- scar shell 6 mm;
- edema-zone shell 10 mm;
- adaptive bound from train-side anchor error margins.

### 6. Protected composition and final output

右侧展示：

- protected background / myocardium / LV / RV anatomy;
- corrected scar mask;
- corrected edema-zone mask;
- scar-priority subtraction producing pure edema;
- final six-class segmentation.

公式：

$$E_{pure}^{final}=E_{zone}^{final}\setminus S^{final}$$

在最右侧画一个最终 segmentation overlay，scar 用红色，pure edema 用橙色，myocardium 用蓝色轮廓。

### 7. Pathology-specific exact fallback

从 scar correction 和 edema correction 各自画独立灰色 safety loop 回到 anchor pathology channel：

- geometry / NaN / checkpoint failure;
- no-T2 edema change violation;
- OOF safety envelope violation;
- extreme remote component / exact-HD sentinel.

写：

**Scar failure does not cancel edema correction**

**Edema failure does not cancel scar correction**

不要画一个全模型 fallback 大开关。

# Panel B — Training and Anti-Identity Mechanism

Panel B 占右下或下方约 30%。

### 1. Leakage-safe anchor errors

画训练 GT 与 held-out nnU-Net OOF prediction 的比较，生成：

- scar FN map;
- scar FP map;
- edema FN map;
- edema FP map.

写：

**Each training case uses only its held-out nnU-Net fold prediction**

### 2. Error-centric sampling

画一个 patch sampler 圆环或四格图：

- 50% FN/FP error-centered;
- 25% pathology/boundary-centered;
- 25% hard-negative/random anatomy.

强调：

**Prevents zero-correction identity collapse**

### 3. Reliable-label supervision

用绿色监督路径：

- scar: all reliable scar-labelled cases;
- edema: T2-present reliable cases only;
- no-T2 edema loss = 0;
- complete-trimodal cases receive target weight ×4;
- Stage B target calibration uses complete tri-modal cases only.

### 4. Losses

画五个简短 loss tags：

- final segmentation Dice + CE;
- FN/FP focal-BCE;
- error-margin improvement;
- identity loss on anchor-correct voxels;
- remote-positive / soft-support safety.

### 5. Cross-validation and deployment

画一个简洁的 five-fold ring：

- 220-case leakage-safe OOF;
- primary target report: 80 complete tri-modal cases;
- all-220 robustness report;
- freeze architecture / decode / safety thresholds;
- all-data CARE-DG deployment fit;
- validation/test inference with frozen 5-fold nnU-Net anchor.

## Explicitly excluded box

在图角落放一个很小的灰色框：

**Not used in CARE-DG runtime**

内部以灰色小标签列出并加叉号：

- MoSAIC
- full CARE-MMRD teacher
- prototype dictionary / memory
- SIP / Transformer
- multiple experts / learned arbiter
- full SRR-v3

不要让这个框抢占主视觉。

## 核心视觉信息

研究者看图后必须立即理解：

1. CARE-DG 不是重新分割，而是修正冻结 nnU-Net 的明确 FN/FP 错误；
2. scar 和 edema 使用共享图像表征，但拥有独立错误语义和 decoder；
3. correction 足够强，因为同时改变 pathology 与竞争类别 logits；
4. correction 仍然安全，因为有 soft anatomy、adaptive bound 和逐病种 fallback；
5. no-T2 不会产生 edema 修正；
6. 运行时只有 nnU-Net + 一个 CARE-DG 网络，没有多模型拼装。

输出应达到顶会论文正式架构图质量：高分辨率、精确、简洁、专业，不要生成卡通图、普通商业流程图或低密度信息图。