# CARE-SER-Lite：面向最终 Docker Submission 的双病理选择性修正蓝图

**文档日期：** 2026-07-26  
**文档性质：** 对现有 `CARE_SER_dual_pathology_submission_blueprint_20260726(1).md` 的收缩版、修改版设计说明  
**目标任务：** CARE 2026 Myocardium，重点处理 MyoPS scar 与 edema；Cine 分支本轮冻结  
**证据边界：** 本文是一份冲刺期科学与工程蓝图，不代表模型已经训练完成、validation 已验证或 Docker 已冻结  

---

## 1. 总体判断

现有 CARE-SER 蓝图的科学方向是正确的，但不适合在最后 Docker 冲刺阶段原样完整实现。

它最值得保留的部分，是把任务从“再训练一个新的完整六类分割器”改写为“围绕成熟模型做病种专属错误识别与有界修正”。这比过去完整 SRR、MMRD 和第一版 SRR-Cascade 更符合当前证据：nnU-Net 仍然是稳定基线；MoSAIC 可能提供部分有价值的 scar 候选，但本地公平比较并不支持其整体替代 nnU-Net；已有有界修正器能够减少部分远端假阳性，却尚未稳定控制最坏边界点。

因此，本文建议将原方案收缩为 **CARE-SER-Lite**：

```text
Frozen 5-fold nnU-Net anchor
+ Frozen MoSAIC scar candidate source
+ CARE scar component selector
+ optional lightweight T2-conditioned edema-zone corrector
+ protected anatomy
+ unified bounded correction
+ pathology-specific exact identity
```

这不是放弃 CARE 的思想，而是删除当前没有独立证据支持、且在最后阶段风险过高的实现复杂度。

最终判断可以概括为：

```text
科学方向：保留
原样完整实现：不建议
收缩版 CARE-SER-Lite：建议作为最终 submission 主蓝图
```

---

## 2. 为什么必须修改原蓝图

原蓝图同时包含以下内容：

- 五折 nnU-Net 概率与不确定性；
- 完整 MoSAIC scar 推理；
- 独立 ScarErrorNet；
- 独立 EdemaZoneErrorNet；
- scar FN/FP 两类错误图；
- edema FN/FP 两类错误图；
- 四个正负 correction fields；
- scar 连通组件仲裁；
- edema 区域仲裁；
- 多组独立阈值；
- 多级病种回退；
- 可选 prototype 与 hard-negative 机制。

从长期论文系统看，这些组件并非没有道理；但从最后 Docker submission 看，它已经接近一个新的完整研究工程，而不是轻量级修正器。当前最重要的问题不是“有没有设计得足够全面”，而是能否在有限时间内证明某个最小机制确实提供病例外收益，并能稳定通过 geometry、label export、runtime、Docker equality 和 worst-case boundary 审计。

原方案的主要风险有三点。

第一，训练目标过多。多个 FN/FP 图、多个 correction field 和多个病种动作需要分别校准，容易再次出现中间输出看似合理、最终标签收益不稳定的问题。

第二，模型容量与数据规模不匹配。scar 和 edema 分支各自再训练一个四尺度三维 U-Net，会引入大量参数和超参数，但真正可用于严格监督的错误病例数量有限，尤其 edema 只应使用 T2-present 且标签可靠的病例。

第三，最终失败模式已经很明确：上一版 CARE-SRR-Cascade 并不是因为完全没有平均收益而失败，而是因为少数最坏边界点导致 exact HD 超过安全门。继续增加体素级网络深度，未必能解决“哪个具体组件值得修改”这一更离散、更病例特异的问题。

因此，修改原则不是简单删模块，而是把模型能力集中到当前真正尚未解决的决策上：

> 哪一个病理候选值得被接受，哪一个应当被拒绝，什么情况下应当完全保持成熟模型不变。

---

## 3. 修改后的核心科学问题

CARE-SER-Lite 不再试图回答“如何重新生成完整病理分割”，而是回答以下三个更窄的问题：

1. nnU-Net 的 scar 预测中，哪些已有组件应当保留或压制？
2. MoSAIC 提供的额外 scar 候选中，哪些可能是真实漏检，哪些只是远端假阳性或亮度伪影？
3. 在 T2 可靠时，nnU-Net 的 edema zone 是否存在能够被轻量区域修正器稳定识别的局部漏检或过扩张？

最终方法主张应当是：

> CARE-SER-Lite 利用强锚点、候选来源、原始病理模态、解剖支持和不确定性，对 scar 组件与 edema 区域进行病种专属的选择性修正；当证据不足时，修正量严格为零，因此最终输出与成熟锚点完全一致。

这种表述比“多模型融合”更准确，也比“完整新型检索分割网络”更可信。

---

## 4. 修改后的总体架构

### 4.1 冻结证据层

系统保留两个冻结来源。

第一个来源是五折 nnU-Net，负责：

- background、myocardium、LV、RV 的最终解剖输出；
- scar 与 edema 的初始预测；
- fold-wise probability；
- uncertainty；
- soft anatomy support；
- exact fallback。

第二个来源是 MoSAIC scar path，仅负责：

- scar probability；
- scar connected components；
- 作为 nnU-Net 漏检的候选来源。

MoSAIC 不负责：

- anatomy；
- edema；
- 最终 scar 标签；
- 最终病例级模型选择。

完整信息流为：

```text
[LGE, T2, C0] + modality availability
        │
        ├── Frozen 5-fold nnU-Net
        │      ├── anatomy
        │      ├── scar / edema anchor
        │      ├── uncertainty
        │      └── soft anatomy support
        │
        ├── Frozen MoSAIC scar path
        │      └── additional scar candidates
        │
        └── CARE-SER-Lite
               ├── scar component selector
               ├── optional edema-zone corrector
               ├── unified bounded correction
               └── pathology-specific exact identity
```

---

## 5. Scar 主分支：从体素级错误网络改为组件级选择器

### 5.1 为什么 scar 应成为主创新

Scar 是当前最适合做选择性仲裁的病种。

一方面，LGE 对 scar 具有明确病理证据；另一方面，scar 体积小、远端假阳性代价高，单个错误组件就可能显著恶化 HD 或 exact HD。当前 MoSAIC 的潜在价值也主要在 scar：它可能在部分病例中发现 nnU-Net 没有发现的候选，但本地公平比较又说明这种优势并不普遍。

因此，最合理的任务不是让新网络再生成一张 scar mask，而是让 CARE 判断每个候选组件是否值得进入最终标签。

### 5.2 候选集合

Scar 候选集合定义为：

$$
\mathcal{C}_{s}
=
\mathcal{C}_{\mathrm{NN}}
\cup
\mathcal{C}_{\mathrm{MoSAIC}}.
$$

每个候选组件 $$c\in\mathcal{C}_{s}$$ 具有以下来源类型：

```text
NN-only
MoSAIC-only
NN-and-MoSAIC agreement
```

这三个来源类型本身就具有重要含义：

- `NN-and-MoSAIC agreement` 通常是高可信候选；
- `NN-only` 需要判断是否为 anchor 中的误报；
- `MoSAIC-only` 需要判断是否为可恢复漏检，且必须重点防范远端假阳性。

### 5.3 组件级输入特征

每个组件只使用可解释、可审计的特征：

- nnU-Net scar mean/max probability；
- MoSAIC scar mean/max probability；
- 两个来源的 agreement ratio；
- nnU-Net ensemble uncertainty；
- LGE 组件内与邻域强度统计；
- 与 myocardium soft support 的 overlap；
- 到 myocardium union 的最大与平均距离；
- 到 LV/RV blood pool 的距离；
- 组件体积；
- slice continuity；
- compactness；
- surface-to-volume ratio；
- remote-island indicator；
- 修改后预估的 exact-HD 风险。

不建议在第一版中直接读取大规模冻结 feature map，也不建议默认加入 prototype similarity。原因是组件级可解释特征已经足以构成一个强校准器，并且更容易避免过拟合和 provenance 不清。

### 5.4 允许的动作

Scar 分支只允许三个动作：

```text
retain
suppress
recover
```

其中：

- `retain`：保留 nnU-Net 已有 scar；
- `suppress`：压制 nnU-Net 的明显误报；
- `recover`：接受 MoSAIC-only 候选，恢复 nnU-Net 漏检。

不建议保留泛化的 `replace` 动作，因为它会使候选边界和最终标签来源变得难以解释，也会增加 exact-HD 风险。

### 5.5 选择器形式

第一版优先使用轻量组件分类器或校准器，而不是三维 U-Net。可选实现包括：

- 小型多层感知机；
- 梯度提升树；
- 逻辑回归；
- 小型组件级神经网络。

模型输出三个动作概率：

$$
P(a\mid c),\qquad
a\in\{\mathrm{retain},\mathrm{suppress},\mathrm{recover}\}.
$$

最终动作必须经过风险门：

$$
a_c^{\mathrm{final}}
=
\begin{cases}
a_c^{\mathrm{model}}, & \text{证据充分且风险通过},\\
\mathrm{anchor\ identity}, & \text{否则}.
\end{cases}
$$

这里的 `anchor identity` 对已有组件表示 retain，对新增候选表示 reject。

---

## 6. Edema 分支：从四输出错误网络改为单一有符号区域修正器

### 6.1 为什么 edema 不能复制 scar

Edema 与 scar 的统计特征不同。

Scar 通常更小、更离散、更适合组件级决策；edema 更弥散、边界更模糊、召回更重要，若照搬 scar 的高阈值和小组件规则，容易通过收缩区域换取表面上的 HD 改善，却损失真实病灶 recall。

因此 edema 应继续使用区域级修正，但结构必须大幅简化。

### 6.2 Edema zone 定义

定义完整 edema zone：

$$
Y_{\mathrm{zone}}
=
Y_{\mathrm{scar}}
\lor
Y_{\mathrm{pure\ edema}}.
$$

对应的 anchor probability 为：

$$
P_{\mathrm{zone}}^{\mathrm{NN}}
=
P_{\mathrm{scar}}^{\mathrm{NN}}
+
P_{\mathrm{pure\ edema}}^{\mathrm{NN}}.
$$

最终 pure edema 仍由 zone 扣除 scar 得到：

$$
\hat{E}_{\mathrm{pure}}^{\mathrm{final}}
=
\hat{E}_{\mathrm{zone}}^{\mathrm{final}}
\setminus
\hat{S}_{\mathrm{final}}.
$$

这意味着 scar 的任何变化都可能影响 pure-edema，因此必须进行联动审计。

### 6.3 可靠监督边界

Edema 分支只在以下病例上计算监督：

```text
T2-present
and
edema label reliable
```

No-T2 病例：

- 不作为 edema positive；
- 不作为 edema negative；
- 不参与 edema correction loss；
- 不进入 edema prototype 或 hard-negative bank；
- 推理时默认保持 anchor identity。

这部分完整保留 MMRD 最有价值的可靠标签思想。

### 6.4 单一有符号修正器

原蓝图中不再分别输出 edema FN、FP、positive correction 和 negative correction。修改为一个轻量区域网络，输出：

- 修正门 $$g_e(x)$$；
- 有符号修正量 $$\delta_e(x)$$。

最终形式为：

$$
z_{\mathrm{zone}}^{\mathrm{final}}
=
z_{\mathrm{zone}}^{\mathrm{NN}}
+
m_{\mathrm{T2}}
g_e(x)\delta_e(x),
$$

并限制：

$$
0\le g_e(x)\le 1,
\qquad
\left|\delta_e(x)\right|\le b_e.
$$

其中：

- $$\delta_e(x)>0$$ 表示恢复可能漏检的 edema zone；
- $$\delta_e(x)<0$$ 表示压制可能误报的 edema zone；
- $$g_e(x)=0$$ 表示精确保持 nnU-Net；
- $$m_{\mathrm{T2}}=0$$ 时整个修正项严格为零。

该形式已经能够表达双向修正，不需要四个相互独立的输出头。

### 6.5 Edema 输入

轻量 edema corrector 可读取：

- normalized T2；
- normalized LGE；
- nnU-Net zone probability；
- nnU-Net uncertainty；
- soft myocardium support；
- distance-to-anatomy；
- low-threshold edema candidate region；
- modality availability。

第一版不使用 MoSAIC edema，也不使用 MoSAIC feature。

---

## 7. 统一有界修正与回退机制

### 7.1 为什么回退不应写成大量补丁

回退本身不是不美观。对于医疗分割，一个模型知道何时不修改成熟基线，本身就是合理的安全设计。

真正不美观的是大量不透明的硬编码分支，例如：

```text
if geometry fails...
if uncertainty too high...
if component too remote...
if volume too large...
if score too low...
```

CARE-SER-Lite 应把这些规则统一成“修正门为零”。

一般形式为：

$$
z_k^{\mathrm{final}}
=
z_k^{\mathrm{anchor}}
+
g_k(x)\delta_k(x),
$$

其中：

$$
g_k(x)=0
\quad\Longrightarrow\quad
z_k^{\mathrm{final}}=z_k^{\mathrm{anchor}}.
$$

于是，回退不再是系统外补丁，而是模型定义中的自然零修正状态。

### 7.2 只保留三条显式系统回退

最终只保留：

1. geometry、label mapping 或 runtime failure  
   → full-case exact fallback；

2. 某病种安全门失败  
   → pathology-specific exact fallback；

3. no-T2 edema  
   → exact anchor identity。

其余风险应尽量通过 $$g_k(x)$$ 控制，而不是继续增加显式分支。

---

## 8. Anatomy 的角色

Anatomy 继续由五折 nnU-Net 提供最终权威：

$$
z_{0:3}^{\mathrm{final}}
=
z_{0:3}^{\mathrm{NN}}.
$$

但 anatomy 对病理修正只作为软支持，而不是硬裁剪。

合理的作用包括：

- 提供病理相对空间坐标；
- 降低远离心肌的假阳性；
- 区分血池、正常心肌和远端背景；
- 构造距离特征；
- 评估新增组件的 exact-HD 风险。

不建议将 anchor myocardium mask 直接乘成零，因为 anchor 自己可能在病灶边界存在解剖误差。硬裁剪会让真正的漏检永远无法恢复。

---

## 9. Prototype 与 dictionary 的处理

### 9.1 不进入默认主路径

Prototype、shared/private dictionary、interaction dictionary、SIP 和稀疏路由均不进入 CARE-SER-Lite 默认 Docker 路径。

删除这些组件并不意味着否定其长期价值，而是因为当前证据尚未证明它们能够在病例外提供独立增益。

### 9.2 Prototype 重新进入系统的前提

Prototype 只有通过以下两个门才允许进入：

第一，先证明冻结特征具有病例外可分性。应使用独立病例上的线性探针检查：

- scar positive vs safe negative；
- edema positive vs T2-present safe negative。

第二，必须进行真正的 matched control：

```text
Control:
prototype input = 0

Prototype:
real positive-minus-safe-negative similarity
```

两组必须保持：

- 相同初始化；
- 相同病例；
- 相同 patch；
- 相同 augmentation；
- 相同 optimizer；
- 相同训练预算；
- 相同 decode；
- 相同 evaluator。

Prototype 只能作为组件 selector 或 edema gate 的一个输入，不能直接决定最终标签。

若没有稳定改善病例级 help/harm、远端假阳性或漏检恢复，应直接删除。

---

## 10. exact HD 必须从最终否决门升级为设计目标

上一版 CARE-SRR-Cascade 已说明：平均 Dice 和 HD95 可以改善，但少数最坏边界点仍能让候选失去提交资格。

因此，新方案不能只在最后查看 exact HD，而应在候选决策阶段估计以下风险：

- 新组件到当前 anatomy support 的最大物理距离；
- 新组件引入的最远表面点；
- 修改前后 exact-HD proxy 的变化；
- 组件是否创建新的 remote island；
- 单病例最大伤害；
- scar 修改对 pure-edema 边界的连锁影响。

对 MoSAIC-only scar 候选，`recover` 应是最高风险动作。只有在以下条件同时满足时才允许：

```text
high proposal confidence
high LGE support
low anatomy distance
acceptable component morphology
low predicted exact-HD risk
```

这种风险前置比“网络先改完，最后整体回退”更符合当前失败机制。

---

## 11. 训练策略

### 11.1 第一阶段：构建无泄漏证据

训练任何 learned selector 前，必须先完成严格病例外证据。

Scar 若使用 MoSAIC 作为 learned input，原则上需要 MoSAIC fold1–4 OOF prediction。full-data submission 权重只能用于 hosted deployment 或推理 smoke，不能直接给训练病例生成监督式 selector 输入。

需要生成：

```text
nnunet_oof_manifest
mosaic_oof_manifest
component_evidence_table
geometry_audit
label_mapping_audit
source_hash_manifest
```

### 11.2 第二阶段：只训练 scar component selector

先不训练 edema corrector，优先验证最有潜力的 scar 仲裁机制。

成功标准不是训练 loss 下降，而是：

- MoSAIC-only 候选中真实漏检恢复率提高；
- remote FP 明显下降；
- positive-case Dice 不下降；
- exact HD 不出现灾难性离群；
- help cases 多于 harm cases；
- activation rate 非零但不过度。

若 scar selector 无法通过这些门，不应继续通过增加网络深度修补。

### 11.3 第三阶段：可选 edema-zone corrector

只有 scar 分支已完成或并行资源允许时，才训练轻量 edema corrector。

Edema 成功标准包括：

- T2-present edema-zone Dice；
- pure-edema Dice；
- recall；
- HD95；
- exact HD；
- boundary error；
- no-T2 identity；
- scar subtraction 后 pure-edema 的病例级变化；
- help/harm。

Edema 若无稳定收益，最终 Docker 直接保留 nnU-Net edema。

### 11.4 第四阶段：统一冻结与 Docker equality

最终冻结：

- component thresholds；
- action calibration；
- correction bounds；
- anatomy support parameters；
- pathology-specific safety thresholds；
- TTA；
- label merge；
- export mapping。

Docker 必须使用与本地候选完全相同的：

- weights；
- thresholds；
- preprocessing；
- TTA；
- post-processing；
- label mapping；
- case naming；
- output geometry。

必须进行逐病例 voxel equality 或 hash equality。

---

## 12. 本地评价与保留门

### 12.1 Scar

Scar 分支必须报告：

- positive-GT Dice；
- precision；
- recall；
- lesion-wise recall；
- HD95；
- exact HD；
- remote FP；
- component count；
- volume ratio；
- empty prediction；
- changed voxels；
- action counts；
- case-wise help/harm；
- maximum single-case harm。

保留条件应至少包括：

```text
non-zero activation
positive-GT Dice non-worse
help >= harm
HD95 non-worse
exact HD no catastrophic outlier
remote FP or component burden improved
```

### 12.2 Edema

Edema 分支必须报告：

- T2-present edema-zone Dice；
- pure-edema Dice；
- precision；
- recall；
- HD95；
- exact HD；
- boundary error；
- zone volume ratio；
- no-T2 identity violation；
- scar correction 对 pure edema 的影响；
- case-wise help/harm。

保留条件必须独立于 scar。

### 12.3 病种独立决定

最终允许四种状态：

```text
scar PASS, edema PASS
→ dual-pathology CARE-SER-Lite

scar PASS, edema FAIL
→ CARE scar + nnU-Net edema

scar FAIL, edema PASS
→ frozen scar source + CARE edema

scar FAIL, edema FAIL
→ deterministic hybrid or nnU-Net baseline
```

不得强制两个病种一起晋级或一起回退。

---

## 13. 修改后的三次 submission 逻辑

### 13.1 Submission 1：确定性互补对照

目的不是证明 CARE 已成功，而是回答：

> MoSAIC scar 与 nnU-Net anatomy/edema 直接组合，是否在 hosted validation 上具有互补性？

组成：

```text
Anatomy:
5-fold nnU-Net

Scar:
frozen full-data MoSAIC hosted scar

Edema zone:
5-fold nnU-Net

Pure edema:
nU-Net edema zone minus final scar

Cine:
frozen existing branch
```

这次提交不包含 learned selector。

### 13.2 Submission 2：CARE scar 选择性仲裁

只有本地 scar component selector 通过保留门时才提交。

组成：

```text
5-fold nnU-Net scar anchor
+ MoSAIC scar candidates
+ CARE component retain/suppress/recover
+ exact pathology identity
```

Edema 继续使用 nnU-Net，除非轻量 corrector 已独立通过。

### 13.3 Submission 3：最终 Docker 等价候选

第三次提交不再发明新架构，只进行：

- 病种定向冻结；
- runtime 修复；
- geometry 修复；
- label export 修复；
- Docker equality；
- benchmark。

若某个 custom 病种未通过，则回退到已验证来源，不再新增 prototype、dictionary、SIP、新 backbone 或新 Cine 训练。

---

## 14. 论文式叙事

最终论文不应把 CARE-SER-Lite 写成普通模型拼接，也不应夸大为通用新型 backbone。

更可信的核心叙事是：

> 现有强分割器在大部分区域可靠，但在小病灶、远端假阳性和边界极值上仍存在病例特异错误。CARE-SER-Lite 不重新学习完整分割，而是利用交叉拟合的模型预测、病理模态证据、解剖支持和不确定性，学习何时接受、拒绝或恢复病理候选，并通过有界修正和零修正恒等状态保护成熟锚点。

方法贡献可压缩为三点：

1. **病种专属决策尺度**  
   scar 使用组件级仲裁，edema 使用 T2 条件区域修正。

2. **可靠监督与无泄漏证据**  
   no-T2 不作为 edema negative，learned selector 使用 OOF evidence。

3. **统一有界修正与精确恒等**  
   证据不足时修正门为零，最终输出严格等于成熟锚点。

优秀论文标准要求每个贡献都能通过最小消融回答：

```text
没有 MoSAIC candidate 时怎样？
没有 CARE selector 时怎样？
没有 T2-conditioned correction 时怎样？
没有 bounded identity 时怎样？
```

最终主对照链建议为：

```text
5-fold nnU-Net
→ deterministic MoSAIC-scar hybrid
→ + CARE scar component selector
→ + optional T2-conditioned edema correction
→ final Docker candidate
```

---

## 15. CARE 思想的继承关系

CARE-SER-Lite 仍然保留了过去 CARE 中最有证据支持的思想。

### 来自 SRR

- 证据不是无条件融合，而是选择性使用；
- scar 与 edema 依赖不同病理证据；
- 正证据与安全负空间应分开；
- 检索或候选只能在证据充分时影响最终结果。

### 来自 MMRD

- modality availability 显式存在；
- no-T2 不作为 edema negative；
- edema 只使用可靠标签监督；
- 中心 ID 不进入推理；
- scar 与 edema 独立处理。

### 来自 SRR-Cascade

- strong frozen anchor；
- anatomy identity；
- bounded correction；
- pathology-specific fallback；
- case-wise help/harm；
- exact-HD safety audit；
- calibration freeze 后再审计。

删除完整 dictionary、SIP、interaction memory 和多层 arbiter，并不是放弃 CARE，而是承认这些组件当前尚未通过独立病例外证据门。

CARE 的核心不应被定义为“必须存在字典”，而应被定义为：

> 只从当前可靠来源提取病种相关证据，只在能够解释和审计的条件下修改成熟预测。

---

## 16. 最终推荐实现

最终 Docker 推荐形态如下：

```text
Input:
LGE + T2 + C0 + availability

Frozen sources:
5-fold nnU-Net
MoSAIC scar path

CARE scar:
component evidence extraction
→ retain / suppress / recover selector
→ exact-HD risk gate
→ bounded scar correction

CARE edema:
optional lightweight T2-conditioned zone corrector
→ unified signed correction
→ no-T2 exact identity

Protected outputs:
background / myocardium / LV / RV exact nnU-Net

Final:
scar priority
pure edema = corrected zone minus corrected scar
pathology-specific exact identity
```

第一优先级是 scar component selector。  
第二优先级是 geometry、label、export 和 Docker equality。  
第三优先级才是 edema-zone corrector。  
Prototype、dictionary、SIP、复杂 memory 和新 Cine 训练全部后置。

---

## 17. 最终决策摘要

| 问题 | 修改版判断 |
|---|---|
| 原蓝图是否值得保留 | 值得保留科学方向 |
| 是否应原样实现 | 不建议 |
| 是否过于繁复 | 对最后 Docker 冲刺明显过重 |
| 最有潜力的部分 | scar component-level selective arbitration |
| edema 是否保留 | 保留为独立、可失败的轻量分支 |
| MoSAIC 的角色 | scar candidate source，不是最终权威 |
| nnU-Net 的角色 | anatomy、anchor、uncertainty、fallback |
| 回退是否不美观 | 回退合理，但应统一成零修正恒等 |
| prototype 是否默认进入 | 否 |
| 是否保留 CARE 思想 | 是，保留可靠证据、病种专属、选择性修正和安全恒等 |
| 推荐最终方法名 | CARE-SER-Lite |
| 推荐最终形态 | strong anchor + scar component selector + optional edema correction |

---

## 18. 当前边界

本文不授权：

- validation upload；
- Docker upload；
- hosted metric claim；
- fold expansion；
- 新 Cine 训练；
- 使用 full-data MoSAIC prediction 训练无泄漏 selector；
- 在没有 matched control 的情况下加入 prototype；
- 根据 hosted score 反向修改阈值。

本文仅作为最终冲刺期的科学与工程设计蓝图。任何 custom 分支只有通过同一划分、病例级、病种独立和 Docker 等价审计后，才值得进入最终 submission。
