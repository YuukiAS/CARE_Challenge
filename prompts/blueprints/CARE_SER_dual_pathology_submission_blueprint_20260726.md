# CARE-SER：面向 Scar 与 Edema 的可靠标签选择性错误检索与病种独立修正方案

**建议方法名：** CARE-SER  
**英文全称：** Reliable-Label Selective Error Retrieval for Myocardial Pathology Correction  
**建议副标题：** Pathology-Specific Scar Component Correction and T2-Conditioned Edema-Zone Correction Around a Strong Frozen Anchor  
**文档状态：** 冲刺期方法蓝图；尚未构成训练完成、validation 已验证或 Docker 已冻结的方法事实  
**适用任务：** CARE 2026 Myocardium，重点为 MyoPS scar 与 MyoPS edema；Cine 分支本轮冻结  
**开发边界：** main-only；不自动授权 validation 上传、Docker 上传、fold expansion 或新 Cine 训练

---

## 1. 总体判断

CARE-SER 不应继续保持上一版 scar-only 设计。Scar-only 适合作为低风险 submission 对照，却不能完整继承 MMRD 中最有价值的 T2 条件可靠监督，也不能解释 CARE 对 edema 的方法贡献。

修正后的 CARE-SER 同时处理 scar 与 edema，但二者不共享同一种错误模型、候选机制或修正规则：

- **Scar 分支**以 LGE 为主要证据，以 MoSAIC scar 为外部候选源，以连通组件为主要决策单位，重点处理小病灶漏检、血池误报、远端小岛和 exact-HD 风险。
- **Edema 分支**以 T2 为主要证据，只在 T2-present 且 edema 标签可靠的病例上学习，以 edema zone 为主要建模对象，重点处理弥散区域漏检、边界不确定和过度收缩。
- **nnU-Net 五折集成**继续提供稳定 anatomy、scar/edema 初始预测和安全回退，但不再拥有不可修改的病理最终权威。
- **MoSAIC**只提供 scar proposal，不提供最终 scar 决策，也不提供本轮 edema 决策。
- **CARE-SER**拥有最终病理修改权：它学习强锚点在哪里漏检、在哪里误报，并通过病种独立的有界修正生成最终 scar 与 edema zone。

完整数据流为：

```text
[LGE, T2, C0] + modality availability
        │
        ├── Frozen 5-fold nnU-Net
        │      ├── anatomy anchor
        │      ├── scar / edema probabilities and logits
        │      ├── ensemble uncertainty
        │      └── soft anatomy support
        │
        ├── Frozen MoSAIC scar path
        │      └── scar proposal probabilities and components
        │
        └── CARE-SER
               ├── ScarErrorNet
               │      ├── scar FN retrieval
               │      ├── scar FP retrieval
               │      └── component-level retain / suppress / recover
               │
               ├── EdemaZoneErrorNet
               │      ├── T2-conditioned edema-zone FN retrieval
               │      ├── T2-conditioned edema-zone FP retrieval
               │      └── region-level expand / suppress
               │
               ├── pathology-specific bounded correction
               └── pathology-specific exact fallback
```

---

## 2. 方法目标与明确边界

### 2.1 方法必须真正回答的问题

CARE-SER 不重新训练一个完整六类分割器。它专门回答：

1. nnU-Net 在哪些位置漏掉了 scar？
2. nnU-Net 在哪些位置错误预测了 scar？
3. 在 T2 证据可靠时，nnU-Net 在哪些位置漏掉了 edema zone？
4. 在 T2 证据可靠时，nnU-Net 在哪些位置错误扩张了 edema zone？
5. 哪些 MoSAIC scar 候选应当被 CARE 接受，哪些应当被拒绝？
6. 在什么情况下应当保持锚点完全不变？

最终输出不应是简单拼接：

$$
\hat{Y}
=
\operatorname{Merge}
\left(
\hat{Y}_{\mathrm{nnU\text{-}Net}},
\hat{Y}_{\mathrm{MoSAIC}}
\right),
$$

而应当是病种独立的选择性修正：

$$
\hat{Y}
=
\operatorname{Correct}
\left(
\hat{Y}_{\mathrm{nnU\text{-}Net}};
E_{\mathrm{MoSAIC}}^{\mathrm{scar}},
Q_{\mathrm{FN}}^{s},
Q_{\mathrm{FP}}^{s},
Q_{\mathrm{FN}}^{e},
Q_{\mathrm{FP}}^{e},
A_{\mathrm{soft}}
\right).
$$

### 2.2 当前明确不恢复的组件

本轮不恢复：

- 完整 SRR-v3；
- shared/private/interaction dictionary；
- SIP 或稀疏路由；
- 中心专属系数或中心 ID 推理；
- 大型正负 prototype memory；
- 多层 learned arbiter；
- CARE-MMRD 整个模型作为第三个完整分割器；
- MoSAIC EdemaNet；
- synthetic T2；
- 新配准系统；
- 新 Cine 训练；
- 根据 official validation 病例级标签调参。

这些内容不是永久否定，而是目前没有足够独立证据证明其收益能够覆盖复杂度与失败风险。

---

# 3. 模块一：几何、标签与来源统一

这一模块不参与学习，但属于所有后续结果的前置硬门。

nnU-Net、MoSAIC 与 CARE-SER 可能使用不同的预处理、裁剪、插值与工作网格。任何概率、标签、距离图和候选组件必须先恢复到同一原始物理空间，才允许进入后续修正。

每个病例必须核对：

- case ID；
- size；
- spacing；
- origin；
- direction；
- affine；
- 轴顺序；
- compact label 与官方 label value 的双向映射；
- scar、pure edema、edema zone、myocardium、LV、RV 的优先级；
- 输出文件名和目录结构；
- 每个来源的 prediction hash。

必须输出：

```text
geometry_audit.csv
label_mapping_audit.json
prediction_source_manifest.json
output_hash_manifest.csv
```

### 3.1 几何失败时的行为

如果任一模型来源无法恢复到相同物理空间，则：

```text
full-case exact fallback to 5-fold nnU-Net
```

禁止仅以数组 shape 相同代替物理几何一致性。

---

# 4. 模块二：冻结多源证据层

## 4.1 五折 nnU-Net 锚点

五折 nnU-Net 提供：

- 六类 logits；
- 六类 probabilities；
- myocardium、LV、RV anatomy；
- scar probability；
- pure-edema probability；
- scar + edema zone probability；
- fold-wise variance 或 entropy uncertainty；
- soft myocardium union；
- distance-to-union map。

五折概率均值为：

$$
\bar{p}_{k}(x)
=
\frac{1}{5}
\sum_{f=1}^{5}
p_{k,f}(x).
$$

nnU-Net 在本方案中的权限为：

- anatomy 最终权威；
- scar 与 edema 初始预测；
- error retrieval 的主要上下文；
- pathology-specific exact fallback；
- 无自定义机制通过时的最终安全基线。

nnU-Net 不再拥有不可修改的病理最终权威。

## 4.2 MoSAIC scar proposal source

MoSAIC 只保留：

- CoarseNet；
- FinePathNet scar expert；
- 与已知 hosted scar 路径一致的 TTA；
- scar proposal probability；
- connected scar candidates。

删除：

- historical edema coarse；
- EdemaNet；
- MoSAIC pure-edema merge；
- MoSAIC edema threshold；
- MoSAIC feature 直接决定最终标签；
- MoSAIC Cine 与本轮 MyoPS 路径耦合。

MoSAIC 输出：

$$
P_{\mathrm{scar}}^{\mathrm{MoSAIC}}(x)
$$

与候选集合：

$$
\mathcal{C}_{\mathrm{MoSAIC}}
=
\{c_1,\ldots,c_J\}.
$$

MoSAIC 只有 proposal authority，没有 final-label authority。

## 4.3 MoSAIC provenance 限制

在没有完整 MoSAIC 五折 OOF 预测前，full-data MoSAIC probability 不应直接进入 CARE-SER 的监督式 error network。

因此：

- ScarErrorNet 主要根据 LGE、nnU-Net 概率、不确定性和解剖支持学习 anchor 错误；
- MoSAIC 在 error map 产生后才作为 candidate source 进入组件级仲裁；
- 未来只有完成 MoSAIC fold1–4 且获得严格 OOF prediction 后，才允许把 MoSAIC probability 纳入 learned error network。

---

# 5. 模块三：ScarErrorNet——组件级瘢痕错误检索

ScarErrorNet 是 LGE-driven 的轻量病种专属网络，目标不是重新做完整 scar segmentation，而是显式识别 nnU-Net 的 scar 假阴性与假阳性。

## 5.1 Scar 错误标签

每个训练病例只使用 held-out nnU-Net fold 的 OOF prediction。

Scar 假阴性：

$$
Y_{\mathrm{FN}}^{s}(x)
=
\mathbf{1}
\left[
Y_{\mathrm{scar}}(x)=1,\,
\hat{Y}_{\mathrm{scar}}^{\mathrm{NN}}(x)=0
\right].
$$

Scar 假阳性：

$$
Y_{\mathrm{FP}}^{s}(x)
=
\mathbf{1}
\left[
Y_{\mathrm{scar}}(x)=0,\,
\hat{Y}_{\mathrm{scar}}^{\mathrm{NN}}(x)=1
\right].
$$

## 5.2 ScarErrorNet 输入

固定输入包括：

1. normalized LGE；
2. nnU-Net scar probability；
3. scar-vs-nonscar logit margin；
4. nnU-Net ensemble uncertainty；
5. soft myocardium union；
6. distance-to-union map；
7. nnU-Net scar binary mask；
8. modality availability embedding。

Scar margin 定义为：

$$
M_{\mathrm{scar}}(x)
=
z_{\mathrm{scar}}^{\mathrm{NN}}(x)
-
\log
\sum_{j\neq\mathrm{scar}}
\exp z_j^{\mathrm{NN}}(x).
$$

中心 ID 不进入网络。

## 5.3 ScarErrorNet 结构

建议使用独立轻量四尺度三维残差 U-Net：

```text
input projection
→ 16 channels
→ 32 channels
→ 64 channels
→ 128-channel bottleneck
→ 64
→ 32
→ 16
```

输出：

- scar FN probability $$Q_{\mathrm{FN}}^{s}$$；
- scar FP probability $$Q_{\mathrm{FP}}^{s}$$；
- positive correction field $$\Delta_{s,+}$$；
- negative correction field $$\Delta_{s,-}$$。

Scar 分支需要较高空间精度、较严格远端假阳性约束和组件级判定。

---

# 6. 模块四：EdemaZoneErrorNet——T2 条件水肿区域错误检索

Edema 不能简单复制 scar 的组件逻辑。它通常更弥散、边界更模糊、对 recall 更敏感，因此应先建模完整 edema zone，再在最终标签组合时扣除 scar。

## 6.1 Edema zone 定义

定义：

$$
Y_{\mathrm{zone}}
=
Y_{\mathrm{scar}}
\lor
Y_{\mathrm{pure\ edema}}.
$$

nnU-Net 初始 zone probability 为：

$$
P_{\mathrm{zone}}^{\mathrm{NN}}
=
P_{\mathrm{scar}}^{\mathrm{NN}}
+
P_{\mathrm{pure\ edema}}^{\mathrm{NN}}.
$$

为了做有界 logit 修正，可定义：

$$
z_{\mathrm{zone}}^{\mathrm{NN}}
=
\operatorname{logit}
\left(
\operatorname{clip}
\left(
P_{\mathrm{zone}}^{\mathrm{NN}},
\epsilon,
1-\epsilon
\right)
\right).
$$

## 6.2 Edema 错误标签

仅在 T2-present 且 edema label reliable 的病例上构造：

$$
Y_{\mathrm{FN}}^{e}(x)
=
\mathbf{1}
\left[
Y_{\mathrm{zone}}(x)=1,\,
\hat{Y}_{\mathrm{zone}}^{\mathrm{NN}}(x)=0
\right],
$$

$$
Y_{\mathrm{FP}}^{e}(x)
=
\mathbf{1}
\left[
Y_{\mathrm{zone}}(x)=0,\,
\hat{Y}_{\mathrm{zone}}^{\mathrm{NN}}(x)=1
\right].
$$

No-T2 病例：

- 不生成 edema FN/FP 标签；
- 不进入 edema positive；
- 不进入 edema negative；
- 不参与 edema correction loss；
- 只可参与 anatomy、scar 和其他合法共享监督。

## 6.3 EdemaZoneErrorNet 输入

固定输入包括：

1. normalized T2；
2. normalized LGE 作为结构与病理上下文；
3. 可选 C0 anatomy context；
4. modality availability；
5. nnU-Net edema-zone probability；
6. nnU-Net zone logit；
7. nnU-Net uncertainty；
8. soft myocardium union；
9. distance-to-union map；
10. low-threshold anchor edema-zone candidate region。

不使用中心 ID。

不使用 MoSAIC EdemaNet。

## 6.4 EdemaZoneErrorNet 结构

建议使用独立于 ScarErrorNet 的轻量四尺度网络。两条病理分支不共享最终 bottleneck 或 correction head，以避免 scar 的精度优先目标与 edema 的召回优先目标相互牵制。

建议通道：

```text
16 → 32 → 64 → 128 → 64 → 32 → 16
```

Edema 分支可采用：

- 较大的有效感受野；
- 更宽的 soft anatomy support；
- 更低的候选阈值；
- 更保守的 negative suppression；
- boundary uncertainty 辅助输出。

输出：

- edema-zone FN probability $$Q_{\mathrm{FN}}^{e}$$；
- edema-zone FP probability $$Q_{\mathrm{FP}}^{e}$$；
- positive zone correction $$\Delta_{e,+}$$；
- negative zone correction $$\Delta_{e,-}$$。

---

# 7. 模块五：病种专属候选与区域仲裁

## 7.1 Scar：连通组件级仲裁

Scar 候选集合：

$$
\mathcal{C}_{s}
=
\mathcal{C}_{\mathrm{NN,scar}}
\cup
\mathcal{C}_{\mathrm{MoSAIC}}.
$$

每个 scar component 计算：

- mean / max $$Q_{\mathrm{FN}}^{s}$$；
- mean / max $$Q_{\mathrm{FP}}^{s}$$；
- nnU-Net scar confidence；
- MoSAIC scar confidence；
- source agreement；
- myocardium overlap；
- distance to myocardium；
- component volume；
- compactness；
- surface-to-volume ratio；
- slice continuity；
- uncertainty；
- blood-pool proximity；
- remote-island indicator。

允许三类动作：

1. **retain anchor scar**；
2. **suppress anchor false positive**；
3. **recover MoSAIC candidate in predicted FN region**。

本轮不设置泛化的 replace 类。

## 7.2 Edema：区域级仲裁

Edema 不以小组件为主要单位，而以 soft zone 和连通区域为主要单位。

允许两类修改：

1. **expand / recover zone**：在高 $$Q_{\mathrm{FN}}^{e}$$、T2 证据明确、soft anatomy 支持充分时，恢复 anchor 漏掉的连续 zone；
2. **suppress unsafe zone**：仅对高 $$Q_{\mathrm{FP}}^{e}$$、远离 anatomy、T2 支持弱或明显远端区域做保守压制。

Edema 禁止：

- 用 component 数最少作为主要目标；
- 通过大幅收缩区域换取 HD；
- 将 no-T2 myocardium 当作负空间；
- 使用 scar 的高阈值、强负原型或极小组件规则直接复制到 edema。

---

# 8. 模块六：病种独立的有界双向修正

## 8.1 Scar correction

正向恢复门：

$$
g_{s,+}(x)
=
M_{\mathrm{MoSAIC}}(x)
\cdot
Q_{\mathrm{FN}}^{s}(x)
\cdot
A_{s,\mathrm{soft}}(x).
$$

负向抑制门：

$$
g_{s,-}(x)
=
M_{\mathrm{NN,scar}}(x)
\cdot
Q_{\mathrm{FP}}^{s}(x)
\cdot
A_{s,\mathrm{soft}}(x).
$$

最终 scar logit：

$$
z_{\mathrm{scar}}^{\mathrm{final}}
=
z_{\mathrm{scar}}^{\mathrm{NN}}
+
b_{s,+}
g_{s,+}(x)
\tanh\left(\Delta_{s,+}(x)\right)
-
b_{s,-}
g_{s,-}(x)
\tanh\left(\Delta_{s,-}(x)\right).
$$

其中 $$b_{s,+}$$ 与 $$b_{s,-}$$ 分开冻结。

## 8.2 Edema-zone correction

仅在 T2-present 时启用：

$$
g_{e,+}(x)
=
m_{\mathrm{T2}}
Q_{\mathrm{FN}}^{e}(x)
A_{e,\mathrm{soft}}(x),
$$

$$
g_{e,-}(x)
=
m_{\mathrm{T2}}
Q_{\mathrm{FP}}^{e}(x)
A_{e,\mathrm{soft}}(x).
$$

最终 zone logit：

$$
z_{\mathrm{zone}}^{\mathrm{final}}
=
z_{\mathrm{zone}}^{\mathrm{NN}}
+
b_{e,+}
g_{e,+}(x)
\tanh\left(\Delta_{e,+}(x)\right)
-
b_{e,-}
g_{e,-}(x)
\tanh\left(\Delta_{e,-}(x)\right).
$$

当 $$m_{\mathrm{T2}}=0$$ 时：

$$
z_{\mathrm{zone}}^{\mathrm{final}}
=
z_{\mathrm{zone}}^{\mathrm{NN}}.
$$

Edema 的 $$b_{e,-}$$ 应比 scar 的负向抑制更保守，防止通过收缩弥散病灶损害 recall。

## 8.3 Anatomy 保护

最终 anatomy logits 恒等：

$$
z_{0:3}^{\mathrm{final}}
=
z_{0:3}^{\mathrm{NN}}.
$$

## 8.4 最终标签组合

Scar 优先于 pure edema：

$$
\hat{E}_{\mathrm{pure}}^{\mathrm{final}}
=
\hat{E}_{\mathrm{zone}}^{\mathrm{final}}
\setminus
\hat{S}_{\mathrm{final}}.
$$

最终输出：

- background；
- myocardium；
- LV；
- RV；
- pure edema；
- scar。

---

# 9. 模块七：病种独立回退与安全门

回退不得设计成大量不透明分支。只保留：

1. geometry / label / runtime failure  
   → full-case exact fallback to nnU-Net；

2. scar safety failure  
   → scar-only fallback；

3. edema safety failure  
   → edema-only fallback；

4. no-T2 edema  
   → exact anchor identity；

5. Cine  
   → frozen existing branch。

每个病例、每个病种必须记录：

```text
case_id
pathology
mechanism_activated
changed_voxels
positive_correction_voxels
negative_correction_voxels
fallback_used
fallback_reason
anchor_hash
proposal_hash
final_hash
```

---

# 10. 训练协议

## 10.1 第一阶段：错误图学习

分别训练：

- ScarErrorNet 的 $$Q_{\mathrm{FN}}^{s}$$ 与 $$Q_{\mathrm{FP}}^{s}$$；
- EdemaZoneErrorNet 的 $$Q_{\mathrm{FN}}^{e}$$ 与 $$Q_{\mathrm{FP}}^{e}$$。

本阶段不修改最终 segmentation。

目标是先证明：

> anchor 错误具有病例外可预测性，而不是 error head 仅仅复制 anchor probability。

## 10.2 第二阶段：有界 correction 学习

启用：

- $$\Delta_{s,+},\Delta_{s,-}$$；
- $$\Delta_{e,+},\Delta_{e,-}$$；
- final scar loss；
- final edema-zone loss；
- remote-FP penalty；
- bounded correction penalty。

两个 pathology 分支独立训练、独立 checkpoint、独立 selection 和独立 fallback。

## 10.3 第三阶段：组件/区域校准与冻结

冻结：

- $$b_{s,+},b_{s,-}$$；
- $$b_{e,+},b_{e,-}$$；
- scar FN/FP thresholds；
- edema FN/FP thresholds；
- MoSAIC candidate threshold；
- anatomy support parameters；
- pathology-specific risk thresholds；
- component / zone post-processing parameters。

Official validation 不用于重新搜索这些参数。

---

# 11. 损失函数

## 11.1 Scar

$$
\mathcal{L}_{s}
=
\lambda_{s,\mathrm{FN}}\mathcal{L}_{s,\mathrm{FN}}
+
\lambda_{s,\mathrm{FP}}\mathcal{L}_{s,\mathrm{FP}}
+
\lambda_{s,\mathrm{final}}\mathcal{L}_{s,\mathrm{final}}
+
\lambda_{s,\mathrm{remote}}\mathcal{L}_{s,\mathrm{remote}}
+
\lambda_{s,\mathrm{bound}}\mathcal{L}_{s,\mathrm{bound}}.
$$

Scar 重点：

- GT-positive Dice；
- precision；
- recall；
- remote FP；
- component count；
- HD95；
- exact HD。

## 11.2 Edema

$$
\mathcal{L}_{e}
=
m_{\mathrm{T2}}
\left[
\lambda_{e,\mathrm{FN}}\mathcal{L}_{e,\mathrm{FN}}
+
\lambda_{e,\mathrm{FP}}\mathcal{L}_{e,\mathrm{FP}}
+
\lambda_{e,\mathrm{final}}\mathcal{L}_{e,\mathrm{zone}}
+
\lambda_{e,\mathrm{boundary}}\mathcal{L}_{e,\mathrm{boundary}}
+
\lambda_{e,\mathrm{bound}}\mathcal{L}_{e,\mathrm{bound}}
\right].
$$

Edema 重点：

- T2-present reliable subset；
- edema-zone recall；
- pure-edema Dice；
- HD95；
- boundary quality；
- no-T2 identity；
- zone volume ratio；
- scar subtraction 后的 pure-edema 变化。

---

# 12. 原型与负空间的条件启用

Prototype 不进入默认主路径。

只有基础双病理 CARE-SER 已经安全后，才允许测试 safe-negative retrieval。

## 12.1 Scar 可测试的安全负空间

- LV/RV blood pool；
- myocardium 外背景；
-正常 myocardium；
- LGE bright artifact；
- 高频 remote false-positive components。

## 12.2 Edema 可测试的安全负空间

只允许来自 T2-present reliable cases：

- myocardium 外背景；
- blood pool；
- 离 GT edema zone 足够远的可靠 myocardium；
- 明确 T2 artifact。

No-T2 myocardium 永远不得进入 edema negative bank。

## 12.3 matched control

```text
Control:
prototype margin = 0

Retrieval:
real positive-minus-safe-negative margin
```

两组必须相同：

- initialization；
- cases；
- patch schedule；
- augmentation；
- optimizer；
- training budget；
- decode；
- evaluator。

Prototype 未提供独立病例级收益时直接删除，不影响主体方法。

---

# 13. 必须报告的评价指标

## 13.1 Scar

- GT-positive Dice；
- precision / recall；
- lesion-wise recall；
- HD95；
- exact HD；
- remote false-positive ratio；
- component count；
- volume ratio；
- empty prediction；
- changed voxels；
- case-wise help / harm。

## 13.2 Edema

- T2-present reliable-subset Dice；
- pure-edema Dice；
- edema-zone Dice；
- precision / recall；
- HD95；
- exact HD；
- boundary error；
- zone volume ratio；
- no-T2 identity violation count；
- scar correction 对 pure edema 的影响；
- case-wise help / harm。

## 13.3 系统安全

- mechanism activation rate；
- pathology-specific fallback rate；
- full-case fallback rate；
- maximum single-case harm；
- CenterB / CenterC；
- complete tri-modal subgroup；
- geometry audit；
- label export audit；
- Docker equivalence。

不得用 foreground mean 掩盖 scar 或 edema 的失败。

---

# 14. 本地保留门

一个病种只有同时满足以下条件，才可进入 validation submission：

1. correction 非零激活；
2. 不等于纯 anchor；
3. scar 分支不等于纯 MoSAIC；
4. mean Dice 不明显退化；
5. HD95 不明显恶化；
6. exact HD 无灾难性离群；
7. remote FP / component burden / boundary 至少一项明确改善；
8. case-wise help/harm 可解释；
9. fallback 不是绝大多数病例；
10. geometry 与 label export PASS。

Scar 与 edema 独立判定：

```text
scar PASS, edema FAIL
→ CARE scar + nnU-Net edema

scar FAIL, edema PASS
→ nnU-Net/MoSAIC-safe scar choice + CARE edema

scar PASS, edema PASS
→ dual-pathology CARE-SER

scar FAIL, edema FAIL
→ deterministic hybrid or nnU-Net baseline
```

---

# 15. 三次 validation submission 计划

## 15.1 第一次提交：`CARE-Hybrid-Control-v1`

### MyoPS 内容

```text
Anatomy:
5-fold nnU-Net

Scar:
full-data MoSAIC hosted scar path

Edema zone:
5-fold nnU-Net

Pure edema:
nU-Net edema zone minus MoSAIC scar

Final priority:
scar overrides pure edema
```

### Cine 内容

```text
frozen current best Cine prediction tree
```

### 不包含

- ScarErrorNet；
- EdemaZoneErrorNet；
- prototype；
- learned gate；
- MoSAIC edema；
- new Cine training。

### 目的

只检验：

> MoSAIC hosted scar 与 nnU-Net anatomy/edema 是否互补。

这次提交是最重要的低风险对照，应优先完成。

---

## 15.2 第二次提交：`CARE-SER-Dual-v1`

第二次提交使用病种独立保留门，不要求两个分支同时通过。

### Scar 通过时提交

```text
5-fold nnU-Net scar anchor
+ MoSAIC scar proposals
+ ScarErrorNet
+ component retain / suppress / recover
+ bounded scar correction
```

Scar 未通过时：

```text
fallback to the better frozen scar source selected before upload
```

不得在上传后根据 hosted score 回填规则。

### Edema 通过时提交

```text
5-fold nnU-Net edema-zone anchor
+ EdemaZoneErrorNet
+ T2-conditioned region expand / suppress
+ bounded edema-zone correction
+ no-T2 exact identity
```

Edema 未通过时：

```text
exact fallback to 5-fold nnU-Net edema
```

### Anatomy 与 Cine

```text
Anatomy:
exact 5-fold nnU-Net

Cine:
exact same frozen tree as Submission 1
```

### 目的

检验：

> CARE 自己学习的 scar 与 edema 错误模型，是否能在病种独立安全门下优于简单的模型拼接。

---

## 15.3 第三次提交：`CARE-SER-Final-Docker`

第三次提交用于病种定向冻结与 Docker 等价验证，不用于发明新架构。

### Hosted 分项决策

#### 情况 A：scar 与 edema 都改善或持平

- 冻结双病理 CARE-SER；
- 只修 runtime、geometry、label、packaging；
- 不新增 backbone、dictionary、SIP 或新 Cine。

#### 情况 B：scar 改善，edema 下降

- 冻结 CARE scar；
- edema exact fallback 到 nnU-Net；
- 检查 pure-edema subtraction 与 label merge；
- 不重新训练大型 edema 模型。

#### 情况 C：edema 改善，scar 下降

- 冻结 CARE edema；
- scar 回退到 Submission 1 的 scar 策略或 nnU-Net；
- 只允许收紧 recover / suppress bounds；
- 不新增新 proposal model。

#### 情况 D：scar 与 edema 都下降

- 停止 CARE-SER 扩展；
- 第三次使用已验证最好的先前候选：
  1. Submission 1 deterministic hybrid；
  2. 或 5-fold nnU-Net baseline。

### Docker 内容

最终 Docker 必须默认运行第三次所选的真实候选，包括：

- 5-fold nnU-Net inference；
- MoSAIC scar proposal inference，仅当最终 scar 需要；
- ScarErrorNet，仅当 scar 分支保留；
- EdemaZoneErrorNet，仅当 edema 分支保留；
- pathology-specific bounded correction；
- exact fallback；
- official raw label export；
- frozen Cine branch。

必须满足：

- 无 `/users/...` 或 `/overflow/...` 绝对依赖；
- 相同 weights；
- 相同 thresholds；
- 相同 TTA；
- 相同 post-processing；
- 相同 Cine；
- 本地与 Docker 逐病例 voxel equality 或 hash equality；
- 完整 15 MyoPS + 15 Cine benchmark；
- 峰值显存、内存和时间实测；
- 第三次 hosted score 不再用于调参。

---

# 16. 三次提交的科学关系

```text
Submission 1
Mature-source complementarity control
MoSAIC scar + nnU-Net anatomy/edema
        ↓
Submission 2
CARE-owned dual-pathology error retrieval
Scar component correction + T2-conditioned edema-zone correction
        ↓
Submission 3
Pathology-specific freeze or fallback
Final Docker-equivalent candidate
```

| 提交 | 回答的问题 | 新增变量 |
|---|---|---|
| 第一次 | 两个成熟来源能否互补 | 只改变病种来源 |
| 第二次 | CARE 自研错误检索是否提供独立价值 | ScarErrorNet 与 EdemaZoneErrorNet |
| 第三次 | 哪些病种分支值得冻结，Docker 是否一致 | 只做病种定向冻结或回退 |

---

# 17. 方法归属与论文式叙事

CARE-SER 不是通用的新 backbone，也不是 nnU-Net 与 MoSAIC 的普通集成。

核心贡献是：

> 利用强锚点的 cross-fitted predictions 构造病种专属错误监督，在可靠标签与模态可用性约束下，分别学习 LGE-driven scar 错误和 T2-conditioned edema-zone 错误；随后通过组件级 scar 候选检索、区域级 edema 修正、软解剖支持与有界双向 correction，只在证据充分时修改成熟锚点，并为每个病种保留 exact fallback。

三条自研路线的继承关系：

### 来自 MMRD

- modality-specific evidence；
- availability 显式输入；
- no-T2 不作为 edema negative；
- reliable-label masking；
- scar / edema 独立监督；
- center ID 不进入推理。

### 来自 SRR

- 选择性使用证据；
- pathology-specific retrieval；
- 正证据与安全负空间分离；
- optional prototype 必须通过 matched intervention 才能保留。

### 来自 SRR-Cascade

- strong frozen anchor；
- anatomy identity；
- bounded correction；
- pathology-specific fallback；
- case-wise help/harm；
- exact-HD safety audit。

最终方法可浓缩为：

```text
Strong frozen anchor
→ cross-fitted pathology error supervision
→ LGE-driven scar error retrieval
→ T2-conditioned edema-zone error retrieval
→ component/region-specific arbitration
→ bounded bidirectional correction
→ protected anatomy
→ pathology-specific exact fallback
```

---

# 18. 最终决策摘要

最新 CARE-SER 应有两个病理分支：

1. **ScarErrorNet**
   - LGE-driven；
   - MoSAIC proposal-assisted；
   - component-level；
   - precision 与 remote-FP 优先。

2. **EdemaZoneErrorNet**
   - T2-conditioned；
   - reliable-label only；
   - region-level；
   - recall、boundary 与 no-T2 safety 平衡。

MoSAIC edema 仍然删除。删除它并不意味着删除 CARE edema；相反，edema 的方法贡献应由 CARE 自己的 T2 条件错误检索与区域修正承担。
