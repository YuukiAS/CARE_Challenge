# Batch 7 轻量 BR2 / SIP 全面架构审计与执行修订

## 结论

R2 / BR2 仍然适合作为 CARE 论文的核心方法思想，但当前刚制定的 `availability-pattern source + soft retrieval weight + optional image residual` 版本仍不够严谨，不能直接交给 Controller。

必须先修正四件事：

1. 论文中的 `source` 应对应不同采集中心或数据来源，不是简单的模态可用组合；CARE 中 CenterA/CenterH、CenterB/CenterC、CenterE/F/G 才是天然的数据源，availability 是每个 source 的 observation set。
2. 论文 learner coefficient 是 source-specific、可正可负、带稀疏约束的全局系数，不是 softmax 概率。若允许图像条件 residual，模型可以绕过这些系数，使 SIP 失去实际意义。
3. 神经 representer 输出与 learner coefficient 存在尺度不可辨识：放大 representer、缩小 coefficient 可以不改变预测，却任意改变 L1 和 SIP。必须先固定 representer 输出尺度。
4. 原论文假定每个 source 都有可靠 response；CARE 的 no-T2 病例没有可靠 edema 监督。Edema 的 source coefficient、SIP 和 pathology loss只能使用 T2-present、edema-supervised sources，不能把 no-T2 source 当作 edema negative 或计入 integrativeness。

因此，本任务仍保留六组 minimal / BR2-no-SIP / BR2-SIP 匹配实验，但实现必须改为 **中心分层、部署可用的轻量 BR2**，并明确限制论文主张。

## 一、原论文真正提供的思想

论文 `Representation Retrieval Learning for Heterogeneous Data Integration`（arXiv:2503.09494v3）同时讨论三种异质性：

- 不同数据源的输入分布不同；
- 不同数据源的输入到响应关系不同；
- 不同数据源只观察到部分模态。

R2 的核心是共享一组 representers，但每个 source 通过稀疏 learner coefficient `beta^(s)` 选择其中一部分。BR2 再为各模态建立 dictionary，并用 observation indicator 让缺失模态严格不进入预测。SIP 直接作用在跨 source 的 `beta_d^(s)` 上，鼓励少量 representer 被多个真正可观察该 representer 的 sources 共同使用。

值得保留的是：

```text
共享但可选择的 representer
+ source-specific sparse learner coefficients
+ 缺失模态 hard exclusion
+ 部分共享而非全部共享
+ SIP 的跨 source integrativeness
```

不必保留当前 M10 的 16-slot spatial dictionary、prototype maps、semantic negative memory、refiner、source arbiter 和多重 correction gate。

## 二、原论文需要批判和改造的地方

### 1. Source identity 在论文中默认已知

论文学习每个 source 自己的 learner。它没有解决测试病例来自新 source、source ID 未知时如何预测。CARE validation不能依赖中心 ID，因此中心只能作为训练期 source index，不能作为影像网络输入。部署时必须使用按 availability pattern 汇总的 source-agnostic coefficient。

### 2. Response 缺失没有被建模

论文处理的是 covariate/modalities 缺失，默认每个 source 的 response 可用于监督。CARE no-T2 病例的 edema label不能视为可靠阴性。因此：

- scar 可使用所有有可靠 scar label 的训练中心；
- edema 只允许 T2-present、edema-supervised中心进入 edema loss、edema coefficient和 edema SIP；
- no-T2中心不参与 edema integrativeness。

### 3. 理论不直接覆盖 3D 医学分割

论文理论依赖固定 dictionary size、bounded representers、Lipschitz/bounded loss和独立样本。其主要实验是模拟回归及 ADNI ROI级表格回归，不是强空间相关、严重类别不平衡的 3D 小病灶分割。因此可以说“受 R2 / BR2 / SIP 启发并做医学影像适配”，不能宣称原 excess-risk bound 已证明本模型。

### 4. BR2 主公式以模态加性主效应为主

论文指出交互 dictionary 或复杂 learner可以加入，但主要推导和 BR2 实验采用模态特异 dictionary及线性 learner。CARE 可以保留少量双模态 interaction representer，但必须作为明确扩展，不得把大量交互槽堆叠成未经验证的主张。

### 5. SIP 会带来负迁移风险

SIP 鼓励更多 sources 共用 representer，但 CARE 的中心、模态和病理监督高度绑定。若权重过大，它可能强迫 CenterB/CenterC 与 LGE-only中心共享不应共享的病灶表示。SIP 必须是 no-SIP 的严格消融，并接受 worst-center / complete-trimodal safety gate。

### 6. Neural representer 有尺度不可辨识

论文理论对 representer function class 有界；直接使用 neural feature maps 时，如果没有固定输出尺度，`theta_d -> c theta_d`、`beta_d -> beta_d / c` 不改变预测，却会改变 L1/SIP。正式实现必须把每个 representer 输出归一到固定 RMS，再对 signed beta 做稀疏和 SIP。

### 7. 论文使用全局 source coefficient，不是逐病例 router

逐病例 softmax router虽然灵活，但会把方法变成普通 mixture-of-experts，并让 source-level SIP 变成装饰。正式 BR2 实验禁止 image-conditioned residual和 softmax/simplex coefficient；病例内容只进入 representer输出，不进入 source coefficient。

## 三、CARE 数据的真实难点

训练集 220 例：

```text
LGE + T2 + C0: 80，主要 CenterB / CenterC
LGE + C0: 24，主要 CenterE / CenterF / CenterG
LGE-only: 116，主要 CenterA / CenterH
```

这带来四个问题：

1. availability 与 center几乎绑定，若把 availability pattern 当 source，会掩盖同一 pattern内部的 center heterogeneity；
2. 只有 T2-present病例能可靠监督 edema，no-T2不能当可靠负例；
3. 官方 validation是完整三模态，局部实验若只改善 LGE-only scar、却伤害 complete-trimodal病例，对挑战赛没有价值；
4. scar是小而离散的病灶，Dice易受少量漏检影响；edema较大、边界模糊，主要问题更偏召回。两个病种必须独立采样、独立系数、独立 SIP和独立保留门。

## 四、历史 Route B / Batch 失败脉络

### Batch 0

真实贡献是识别旧 B3-B8 中大量 proxy、placeholder、随机/确定性 fallback，并确定只继续 `SRRProposeRefineMyoPS`。失败根因是旧阶段链并非连续 checkpoint，也没有正式入口。

### Batch 1

接通真实 OOF anchor、prototype/memory、no-T2安全、final-output mode和 checkpoint roundtrip。问题是 validator、runner、inference仍有不同数据流，Pattern-SIP更多是“有梯度”而不是科学有效性。

### Batch 2

修正病例泄漏、空 memory slot、raw anchor / safety context和 checkpoint schema；建立公平评价。问题是早期 inference实际复制 nnU-Net标签，说明合同存在但生产入口没有真正消费模型。

### Batch 3

补齐真实模型推理和控制链，解决 identity bypass、checkpoint load和三模式语义。问题是模型仍未完成足额训练，工程真实性与科学性能尚未分开。

### Batch 4

第一次完成 176/44、1800步、full-4scale、完整 prototype/memory和44例全体积评价。工程闭环成功，但最终只比 nnU-Net约高 `+0.001`，证明“未训练”不是主要借口。

### Batch 5

定位 checkpoint decode、gate、loss和oracle问题。首次 packet仍有复制干预、空字段和错误 loss authority判断；后续代码复核才确认 final logits supervision和 production authority错位。

### Batch 6

修通 final pathology loss和 production gate corrective path，300步后平均仍只有 `+0.001699`。这证明过度保守和 final loss确实是问题，但不是唯一问题。

### Batch 7

重建 memory、接入 prototype maps、增加 discovery/confirmation、可微 refiner和 source arbiter。正式300步 edema小幅正、scar为负。原 intervention聚合复制同一结果，不能做机制结论；新模块同时随机启动、训练过短且目标混杂。

### Batch 7 repair

独立干预、identity、真实 category memory和 anchor-free code path终于可信，但 proposal 600步仍传入空 loss JSON，继承历史混合M10 loss；梯度检查对 logits均值 backward。与此同时，真实干预已显示 semantic negative memory无益、prototype maps杠杆极低、scar链持续有害。

### 反复出现的共同根因

```text
实现和合同不一致
不同阶段的数据流不统一
loss名称存在但权威不真实
复杂模块同时训练，无法归因
validator只查文件或连接，不查语义
source / supervision定义不符合CARE数据
工程修复成功后仍缺独立科学增益
```

## 五、修订后的轻量中心分层 BR2

### 1. Training source 与 deployment source 分开

训练期 source 定义为 metadata中的采集中心。Availability只是该中心的 observation set。Center ID只用于选择训练期 coefficient表和source-balanced sampling，禁止拼接到图像特征或 router输入。

对病种 `p`、representer `d`、中心 `c`：

$$
\beta_{p,d}^{(c)}=\bar\beta_{p,d}^{(a_c)}+\delta_{p,d}^{(c)},
$$

其中 `a_c` 是该中心的 availability pattern，且同一 pattern内约束：

$$
\sum_{c:a_c=a}\delta_{p,d}^{(c)}=0.
$$

训练可使用 source-specific `beta^(c)`；验证和部署只能使用 `bar beta^(a)`，因此不依赖中心 ID。`delta` 使用显式 L2 shrinkage，防止记忆中心风格。

### 2. Signed coefficients，不使用 softmax

`beta` 是可正可负的全局标量，不做 softmax、top-k归一或和为1约束。Invalid representer通过 availability mask精确乘零。禁止 image-conditioned coefficient residual。

### 3. Representer 最小化并固定尺度

只在 proposal使用的单个全分辨率 pathology feature scale上增加7个小型 residual adapters：

```text
shared anatomy
LGE private
C0 private
T2 private
LGE-C0 interaction
LGE-T2 interaction
T2-C0 interaction
```

每个 adapter独立参数化、末层零初始化。Private adapter只读取本模态；interaction读取归一化后的两模态特征、逐点乘积和绝对差。输出在乘 beta前归一到固定 per-case RMS，避免 beta尺度被任意规避。

BR2 feature为：

$$
h_p^{BR2}=h_p^{minimal}+W_p\left(\sum_d I_d(a)\beta_{p,d}\widetilde\theta_{p,d}(x)\right),
$$

其中 `W_p` 零初始化。这样 BR2初始行为等于 minimal，400步实验不会因随机大扰动直接破坏 baseline。

### 4. 病种特异 supervision source

- scar：所有可靠 scar监督中心；
- edema：仅 T2-present且有可靠 edema监督的中心；
- no-T2 source不建立 edema beta，不参与 edema SIP，不进入 edema loss。

### 5. Source-balanced risk

原论文按 source平均风险。Batch size为1时，正式 sampler必须先在该病种合格中心中均匀选中心，再在中心内均匀选病例，然后选病灶/anchor-error patch。必须输出每个中心的采样次数，避免 CenterA因病例多而主导训练。

### 6. SIP 的医学影像适配

对病种 `p`、representer `d`，令 `O_{p,d}` 是同时满足“观察到所需模态”和“该病种监督可靠”的训练中心集合：

$$
\widetilde\gamma_{p,d}(\tau)=\sum_{c\in O_{p,d}}\min\left(1,\frac{|\beta_{p,d}^{(c)}|}{\tau}\right),
$$

$$
P_{SIP}^{(p)}=\sum_{d:|O_{p,d}|>1}\min\left(1,\frac{|O_{p,d}|-\widetilde\gamma_{p,d}(\tau)}{|O_{p,d}|-1}\right).
$$

SIP只作用于训练中心 coefficient；部署 coefficient仍为 `bar beta`。旧 `semantic_retrieval_regularization` 和 `pattern_sip_integrativeness_loss`正式权重必须为零。

### 7. 400步内的确定性训练顺序

每个 BR2 run总预算仍为400步：

```text
1-50: beta / pathology head warmup，representer adapter冻结
51-350: 交替更新 beta-block 与 representer/pathology-block
351-400: representer冻结，校准 beta / pathology head
```

no-SIP和SIP必须从完全相同初始化、sampler manifest和warmup状态开始，只允许 SIP weight不同。Minimal使用相同病例和patch序列训练对应 pathology heads。

## 六、评价与论文主张边界

除原 positive-case Dice、HD95、remote FP和help/harm外，必须增加：

- complete-trimodal subgroup；
- CenterB / CenterC及各有正例中心的 worst-center结果；
- proposal precision、recall、lesion-wise recall；
- anchor-missed lesion recovery和anchor false-positive suppression；
- source coefficient、pattern coefficient、center deviation和integrativeness分布；
- representer输出RMS与beta尺度；
- source-balanced sampler计数。

保留门必须同时保证官方部署匹配的 complete-trimodal子组不被伤害。任何结果只能支持：

```text
R2/BR2-inspired medical imaging adaptation
```

不得声称原论文理论界已在3D分割中成立，也不得声称因果上消除了center-missingness confounding。

## 七、当前决定

```text
保留：R2 / BR2作为论文核心候选
重写：source定义、learner coefficients、representer尺度和deployment规则
保留为消融：SIP
正式删除：旧Pattern-SIP、generic semantic regularization、prototype maps、semantic negative memory、M10 16-slot dictionary在本任务中的使用
禁止：image-conditioned residual、softmax/simplex beta、center作为网络输入、no-T2 source参与edema SIP
```

完成这一修订后，六组实验才具有真正的可解释性。若轻量中心分层BR2仍不优于minimal，则应退役本次医学影像BR2适配，但仍不能把结论写成否定原R2/BR2论文。