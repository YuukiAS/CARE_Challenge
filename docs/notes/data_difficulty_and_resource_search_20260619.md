# CARE Myocardium 数据困难机制与外部资源落地审计

日期：2026-06-19  
范围：本报告只讨论 CARE Myocardium 数据机制、外部方法/代码/权重资源、以及未来七天可落地实验路线。它不以 validation submission、leaderboard forensic、旧 zip candidate、LCC calibration 或 MedNeXt 调参为中心。

## 0. 执行结论

当前需要继续找新的 paper/repo/预训练权重，但必须是窄范围、数据困难驱动的搜索，不应再泛化成“最新医学影像大模型”调研。

最值得继续找的资源类型有两类：

1. **cine CMR myocardium/LV/RV 解剖分割的成熟代码和预训练权重**，优先 short-axis cine、ACDC/M&Ms/UK Biobank CMR 相关资源。原因是 CARE 的 CineMyoPS 原始数据是真 4D cine，而当前 Dataset502/pipeline 实际只用了单帧，且 `myocardium_cinemyops` 的本地 proxy 与官方任务语义存在错配风险。
2. **MyoPS 的缺模态/T2-aware/LGE-aware 轻量方法**，优先 modality dropout、missingness mask、late fusion、T2-present edema expert、LGE scar expert。原因是训练集存在强中心相关缺模态，而 validation/held-out 是完整三模态；edema 与 T2 presence 完全绑定，scar 的强对比主要来自 LGE。

当前最值得马上 clone 或细读的三个候选：

| 优先级 | 资源 | 立即用途 | 主要任务 | 结论 |
|---:|---|---|---|---|
| 1 | CineMA, `https://github.com/mathpluscode/CineMA` | 复用 cine CMR 预训练/finetuned SAX myocardium-LV 分割，做 CARE CineMyoPS adapter smoke | `myocardium_cinemyops` | 代码、权重、MIT license 都较明确，是当前最值得推进的外部资源 |
| 2 | CAA-Seg, `https://github.com/yifangao112/CAA-Seg` | 阅读 SSA/nnU-Net-v2 适配方式，验证是否能用于完整三模态 MyoPS cases | `myops_scar`, `myops_edema` | 有代码和 MIT license，但没有确认权重；只能作为完整三模态/配准方向的 bounded smoke，不应直接当主线 |
| 3 | ModDrop++ / AWSnet 二选一细读 | ModDrop++ 用于缺模态设计参考；AWSnet 用于 MyoPS LGE/T2 scar/edema 旧挑战实现参考 | `myops_edema`, `myops_scar` | 更适合作为设计借鉴，不建议直接大规模接入旧工程 |

如果只能押注两个方向，建议押注：

1. **CineMA/成熟 cine 解剖预训练资源 -> CARE CineMyoPS adapter**。它直接对准当前最大结构性问题：真 4D cine 被当前 wrapper 降成单帧，且官方 `myocardium_cinemyops` 目标更像 anatomy proxy，而不是旧 wrapper 的 class_3 scar sanity。
2. **MyoPS T2-aware edema routing + LGE scar expert 的轻量实验**。它直接对准训练/validation 分布错配和模态-标签机制：80 个 complete T2 cases 全有 edema，140 个 no-T2 cases 无 edema；validation 15/15 complete 三模态。

暂时冻结的路线：LCC calibration 主线、MedNeXt 反复尝试、MyoPS-Net zero-filled mapping channel、U-MyoPS Stage1->Stage2 bridge、大规模修 CineMyoPS 单帧 compact wrapper、继续围绕旧 zip candidate 做 forensic。

## 1. 本轮只读证据来源

本轮检查了本地 raw data、nnU-Net 数据集结构、已有报告/PDF 摘要，并进行了轻量 NIfTI 统计。统计脚本只读取文件，不写预测、不训练、不生成 submission zip。

外部搜索围绕以下资源类型进行：cine CMR segmentation/pretraining、MyoPS scar/edema repo、missing-modality segmentation、small-lesion/boundary loss、cine temporal/motion feature。网络可用，已核验的公开链接在各表中列出。

## 2. CARE 数据困难机制诊断

### 2.1 MyoPS 数据结构与模态机制

本地训练集按 raw NIfTI 统计得到 220 个 MyoPS train cases，模态组合如下：

| 模态组合 | case 数 | 比例 | 中心分布 |
|---|---:|---:|---|
| `C0 + LGE + T2` | 80 | 36.4% | CenterB 35, CenterC 45 |
| `C0 + LGE` | 24 | 10.9% | CenterE 7, CenterF 9, CenterG 8 |
| `LGE only` | 116 | 52.7% | CenterA 81, CenterH 35 |

核心事实：

- `LGE` 是所有训练样本共有模态。
- `T2` 只存在于 80/220 complete cases，并且高度 center-correlated。
- `C0` 存在于 104/220 cases；116 个 CenterA/H cases 是 LGE-only。
- validation/held-out 检查到 15/15 cases 都是 `C0 + LGE + T2` complete 三模态。
- 因此直接用 zero-filled missing channels 训练统一模型，很容易学习到 center/missingness shortcut，而不是病灶机制。

### 2.2 MyoPS label 与病灶稀疏性

本地 raw label 统计：

| label | 有阳性 case 数 | 全体 voxel fraction mean | 阳性 case median voxel fraction | 阳性 case p90 voxel fraction |
|---|---:|---:|---:|---:|
| myocardium | 185 | 0.00826 | 0.00936 | 0.01460 |
| edema | 80 | 0.00145 | 0.00337 | 0.00739 |
| scar | 212 | 0.00304 | 0.00291 | 0.00513 |

连通域统计：

| target | 阳性 case 数 | 每 case 连通域 median | 每 case 连通域 p90 | 每 case max | component mm3 median | component mm3 p90 |
|---|---:|---:|---:|---:|---:|---:|
| edema | 80 | 9.0 | 18.2 | 35 | 31.36 | 3814.32 |
| scar | 212 | 1.0 | 7.0 | 33 | 149.93 | 34281.85 |

解释：

- edema 和 scar 都是小目标，尤其 edema 的体素占比更低且多连通域。
- HD 对远端假阳性非常敏感；但这不意味着 LCC calibration 应继续作为主线。更根本的问题是先减少模态错配和远端病灶 hallucination。
- myocardium mask 可以作为强空间先验，但 raw label 中 pathology 会替换部分 myocardium label，所以不能简单用 pure myocardium label 判断病灶 containment；应构造 `myocardium + edema + scar` 的 union prior 或用解剖模型产生软 prior。

### 2.3 MyoPS 模态-病灶信号

以 lesion 区域与 myocardium 区域的 robust-z intensity 差值做快速 sanity check：

| 模态 | edema median contrast | scar median contrast | 解释 |
|---|---:|---:|---|
| C0 | 0.238 | 0.287 | 有弱信号，但不是主导 |
| LGE | 0.449 | 1.014 | scar 最强信号来自 LGE |
| T2 | 0.824 | 0.667 | edema 最强信号来自 T2 |

结论：

- `myops_scar` 应优先围绕 LGE scar expert、myocardium-space prior、小病灶/HD 约束，而不是强行让缺失 T2/C0 的统一网络贡献 scar 判断。
- `myops_edema` 的主要瓶颈是 T2 缺失与 label 机制绑定：80 个 T2-present complete cases 全有 edema；140 个 no-T2 cases 没有 edema label。训练所有 cases 且 zero-fill T2 会把“无 T2”学成“无 edema”的 center-confounded shortcut。
- validation/held-out 是 complete 三模态，因此 edema 的最小实验应优先限制在 T2-present/complete cases，或显式做 T2-aware routing，而不是继续把 missing T2 当真实零强度。

### 2.4 MyoPS geometry 与配准

MyoPS train 的 shape/spacing/direction 高度异质：

- 常见 shape 包括 `(256,256,20)`, `(192,256,8)`, `(256,256,9)` 等。
- spacing 包括 `(1.3281,1.3281,5.0)`, `(0.7291,0.7291,23.0)`, `(1.3281,1.3281,10.0)` 等。
- direction unique 约 81。

validation 则更稳定：15/15 complete 三模态，direction unique 1，spacing 主要为 `(1.3281,1.3281,10)` 和 `(1.7708,1.7708,10)`。

判断：

- 配准/几何确实是风险，但当前更大的瓶颈仍是 missing modality 与 label 机制错配。
- 若要引入 CAA-Seg/SSA，应先只在 complete三模态 subset 上做 bounded smoke，验证其是否解决真实 misalignment，而不是把它当全数据主线。

### 2.5 CineMyoPS 原始数据机制

CineMyoPS raw train 统计：

| 项 | 统计 |
|---|---|
| train case 数 | 64 |
| raw frame 数 | 64/64 为 30 frames |
| 常见 shape | `(256,256,12,30)`, `(256,256,11,30)`, `(256,256,14,30)`, `(320,320,3,30)` 等 |
| spacing | 常见 `(1.1685,1.1685,6.0,1.0)`, 也有 z spacing 23.0 等 |
| direction | unique 64 |
| label presence | myocardium 64, LV 64, scar 63 |

CineMyoPS val 统计：

| 项 | 统计 |
|---|---|
| val case 数 | 15 |
| frame 数 | 14 cases 为 30 frames，1 case 为 50 frames |
| shape/spacing | 变化较大 |
| direction | unique 6 |

label 稀疏性：

| label | 阳性 case 数 | 阳性 case median voxel fraction | median 连通域数 | median component mm3 |
|---|---:|---:|---:|---:|
| myocardium | 64 | 0.0130 | 15.0 | 21.87 |
| LV | 64 | 0.0154 | 1.0 | 96426 |
| scar | 63 | 0.00274 | 2.0 | 73.73 |

判断：

- CARE CineMyoPS raw data 是真正 4D cine，而当前 Dataset502/pipeline 实际是单帧抽取。
- 官方任务名是 `myocardium_cinemyops`，不能把本地 class_3 scar sanity 与官方 myocardium 指标混在一起解释。
- 当前最值得解决的不是再修单帧 compact wrapper，而是确认能否快速接入成熟 cine myocardium/LV segmentation 预训练资源，先把 anatomy proxy 做稳。

## 3. 三个任务瓶颈排序

### 3.1 `myops_scar`

瓶颈排序：

1. **小病灶与 HD 敏感性**：scar median voxel fraction 约 0.29%，远端 false positive 会严重影响 HD。
2. **LGE 依赖强**：所有 cases 都有 LGE，scar 在 LGE 上 contrast 最强。
3. **空间先验不足**：需要 myocardium/pathology union prior 限制远端假阳性。
4. **缺模态不是 scar 的最大障碍**：C0/T2 缺失会影响统一网络，但 scar 的核心信号来自 LGE。

建议方向：LGE scar expert + myocardium-space prior + 轻量 boundary/small-lesion loss smoke。不要把大模型替换或 LCC calibration 当主线。

### 3.2 `myops_edema`

瓶颈排序：

1. **T2 缺失与 label 机制完全绑定**：只有 T2-present complete 80 cases 有 edema，no-T2 140 cases 无 edema。
2. **训练/validation 分布错配**：validation 是 complete 三模态，训练多数是 LGE-only 或 C0+LGE。
3. **类别极不平衡**：edema 全体 voxel fraction mean 约 0.145%，且 median 9 个连通域。
4. **center-confounded shortcut**：zero-filled T2 容易把“无 T2/某中心”学成“无 edema”。

建议方向：T2-present edema expert、T2-aware routing、missingness mask 或 HeMIS/ModDrop-style fusion。不要继续默认所有 missing T2 是真实零强度。

### 3.3 `myocardium_cinemyops`

瓶颈排序：

1. **raw 4D cine 未被充分使用**：raw data 有 30/50 frames，当前 Dataset502 单帧抽取损失运动/相位信息。
2. **本地 proxy 与 hosted task 语义错配**：官方任务是 myocardium_cinemyops，当前本地 class_1 myocardium proxy 与 class_3 scar sanity 不能混为一谈。
3. **geometry/affine 异质**：shape、spacing、direction 分布复杂，adapter 必须严格检查 affine/resampling。
4. **缺少成熟 anatomy prior**：如果 myocardium/LV anatomy 不稳，scar sanity 或 postprocess 无法救主指标。

建议方向：成熟 cine SAX myocardium/LV segmentation 预训练资源优先，尤其 CineMA；再考虑轻量 2.5D/ED-ES frame pair/temporal mean-max，而不是继续修旧单帧 wrapper。

## 4. Deep Research 覆盖性与缺口

Deep Research 报告中列出了大量方法，但多数没有直接解决 CARE 当前数据机制，或者没有确认代码/权重/许可证。下面按落地性重评估。

### 4.1 可立即尝试或 bounded smoke

| 方法 | 是否解决 CARE 瓶颈 | 代码/权重状态 | 适配任务 | 三五天可落地性 | 结论 |
|---|---|---|---|---|---|
| CineMA | 直接对应 cine CMR anatomy/pretraining，可能修复 single-frame/semantic proxy 问题 | GitHub + HuggingFace 权重 + MIT license 已确认 | `myocardium_cinemyops` | 高 | 作为第一优先外部资源 |
| CAA-Seg / SSA | 可能对应三模态 alignment，但只对 complete cases 直接适用 | GitHub + MIT license 已确认，权重未确认 | `myops_scar`, `myops_edema` | 中 | 可做 complete-case bounded smoke，不应全量主线 |
| BoundaryDoU / boundary loss | 可能帮助小病灶边界/HD；不解决缺模态 | GitHub 有代码，license 未快速确认 | `myops_scar`, `myops_edema` | 中 | 可作为 loss/reference，不应先于数据机制实验 |

### 4.2 值得查询但未确认

| 方法 | 缺口 | 可能用途 | 查询标准 |
|---|---|---|---|
| CorSeg-CineSAX | 未确认可下载权重和清晰 repo | cine myocardium/LV prior | 找到代码、权重、许可证、SAX inference example 才能进入候选 |
| ViTa | GitHub/MIT 已确认，但依赖 UKBB multiview/tabular setup，接入复杂 | 4D cine/multiframe representation | 只有发现可直接 inference 的 SAX segmentation weights 才值得投入 |
| StrainNet | 有 repo 和 Dropbox pretrained model，但输入是 binarized LV myocardium series，不是 raw image segmentation | motion/strain feature 或 QC | 需要确认 license、能否从 CARE mask 快速产生 strain cue |
| MTI-MyoScarSeg | Deep Research 提到 motion-texture，但代码/权重未确认 | cine scar/motion cue | 无代码则只保留 optical-flow/temporal cue 概念 |
| nnU-Net Task114 / M&Ms weights | 需要确认是否有公开可用预训练 checkpoint | cine anatomy pretraining | 必须有权重和兼容 license，否则不作为主线 |

### 4.3 不建议本次冲刺投入

| 方法 | 停止原因 |
|---|---|
| YoloSAM / SAM-based 大方案 | 不直接解决 T2 缺失、CARE label 机制、4D cine anatomy proxy；prompt/adapter 成本高 |
| UniME / large unified medical foundation models | 资源和工程成本不确定，三五天内难以形成可信 local proxy |
| AdaMM / M3AE 等复杂 missing-modality transformer | 多为脑肿瘤或多模态 MRI 设定，迁移成本高于轻量 missingness mask/late fusion |
| Domain randomization 大规模训练 | 不解决标签机制错配，且需要大量训练时间 |
| InverseForm 主线接入 | 有代码和 BSD 类 license，但是自然图像 segmentation loss 框架，医学小病灶收益不确定且依赖旧 PyTorch/Apex |

### 4.4 Deep Research 可能夸大或证据不足

- 报告中多处把 2026/future-looking 方法写成可用候选，但没有同步给出可靠代码、权重、license 或复现实验。
- 对 CAA-Seg、MTI-MyoScarSeg、YoloSAM、StrainNet、CineMA、ViTa、CorSeg-CineSAX 的落地难度没有严格区分。
- 对 CARE 的核心问题“80 complete T2 cases vs 140 no-T2 no-edema cases”和“CineMyoPS raw 4D 被当前 pipeline 单帧化”覆盖不足。
- 报告倾向按方法先进性排序，而不是按 CARE 数据机制、三五天接入成本、失败可回滚性排序。

## 5. 为什么仍然需要新的外部搜索

需要继续搜索，但搜索目标应缩小为以下判断问题：

1. **有没有可直接 inference 的 cine SAX myocardium/LV segmentation 权重？**  
   若有，可快速为 `myocardium_cinemyops` 提供 anatomy prior 或 replacement branch。

2. **有没有 MyoPS scar/edema 的 LGE/T2 实现可借鉴？**  
   重点不是直接复现论文，而是找到 label mapping、LGE/T2 preprocessing、小病灶处理、multi-sequence fusion 的成熟细节。

3. **有没有轻量 missing-modality 实现可转成当前 nnU-Net/MONAI adapter？**  
   优先 missingness mask、modality dropout、late fusion、expert routing，而非复杂 transformer。

4. **有没有小病灶/HD-sensitive loss 可作为低风险 smoke？**  
   必须能嵌入现有 pipeline 或至少作为 bounded fold0 实验；不能引入大规模框架迁移。

## 6. 新外部资源搜索结果与快速落地评估

### 6.1 CineMA

| 字段 | 评估 |
|---|---|
| 链接 | `https://github.com/mathpluscode/CineMA` |
| 年份 | 2024-2025 公开资源；repo 页面提供 paper/模型说明 |
| 任务 | Cine CMR foundation/pretraining；SAX ventricle/myocardium segmentation 等 |
| 输入 | cine CMR，README 中 SAX segmentation task 使用 1 timeframe input；也支持多数据集训练/eval |
| 输出 | ventricle/myocardium segmentation；非 scar/edema |
| 代码 | 有 |
| 权重 | HuggingFace 上有 pretrained/fine-tuned models |
| license | MIT |
| 环境 | pip/conda/PyTorch；README 有 inference examples |
| CARE 匹配 | 高：直接对应 CineMyoPS anatomy proxy 和 cine CMR |
| 预计接入 | 1-3 天做 adapter smoke；3-5 天做小批量 proxy eval |
| 最小实验 | 取 3-5 个 CineMyoPS train/val cases，按 CineMA SAX inference example 做 frame/spacing adapter，输出 myocardium/LV mask，与 train labels 算 class_1 Dice/HD sanity |
| 最可能提升 | `myocardium_cinemyops` |
| 风险 | label schema/spacing/2D slice-frame layout 需要 adapter；CineMA 不直接预测 scar |
| 为什么优先于旧路线 | 它解决的是 current pipeline 未利用成熟 cine anatomy prior 的数据问题，而不是继续修单帧 wrapper 或 postprocess |

结论：第一优先外部资源。

### 6.2 ViTa

| 字段 | 评估 |
|---|---|
| 链接 | `https://github.com/Yundi-Zhang/ViTa` |
| 任务 | UK Biobank cine CMR foundation model；segmentation、phenotype、classification |
| 输入 | 3D+T cine + tabular health data；repo 数据结构为 `.npz` keys `sax/lax/seg_sax/seg_lax` |
| 输出 | 多平面/multiframe segmentation 等 |
| 代码 | 有 |
| 权重 | repo 需要进一步确认具体可下载 segmentation checkpoint |
| license | MIT |
| CARE 匹配 | 中：概念匹配 4D cine，但工程形态比 CineMA 重 |
| 预计接入 | 3-7 天，取决于权重和 adapter |
| 最小实验 | 只在找到 SAX segmentation checkpoint 后，复用其 preprocessing 对 1-2 CARE cases 做 inference |
| 最可能提升 | `myocardium_cinemyops` |
| 风险 | UKBB/tabular/multiview 假设可能超出 CARE；接入复杂 |
| 结论 | CineMA 失败或不足时作为第二梯队 |

### 6.3 CAA-Seg

| 字段 | 评估 |
|---|---|
| 链接 | `https://github.com/yifangao112/CAA-Seg` |
| 任务 | MyoPS multi-sequence segmentation / cross-attention alignment 方向 |
| 输入 | 多序列 CMR；与 complete C0/LGE/T2 更匹配 |
| 输出 | myocardium pathology segmentation，需核对 label mapping |
| 代码 | 有，基于 nnU-Net-v2 结构 |
| 权重 | 未确认 |
| license | MIT |
| CARE 匹配 | 中：对 80 complete train cases 和 15 complete validation 可能有价值；对 140 no-T2/no-C0 cases 不自然 |
| 预计接入 | 2-5 天做 code reading + complete-case smoke |
| 最小实验 | 不改主训练代码，先阅读其 nnU-Net-v2 adapter；若接入，只做 fold0 complete-case overfit/smoke，验证 label mapping 和 inference 非空 |
| 最可能提升 | `myops_edema` 其次 `myops_scar` |
| 风险 | 无权重；如果完整依赖三模态，训练样本只有 80；无法自然处理 LGE-only majority |
| 为什么优先于旧路线 | 比 MyoPS-Net zero-filled channel 更接近当前 complete三模态 validation，但必须 bounded |

结论：值得 clone/read，但不应默认全量替代当前 baseline。

### 6.4 AWSnet / MyoPS2020 code

| 字段 | 评估 |
|---|---|
| 链接 | `https://github.com/soleilssss/AWSnet/tree/master` |
| 任务 | 2020 MyoPS Challenge multi-sequence myocardial pathology segmentation |
| 输入 | MyoPS2020 paired/pre-aligned multi-sequence CMR |
| 输出 | scar/edema/myocardium 等，需核对 raw label |
| 代码 | 有 |
| 权重 | 未发现 |
| license | 未快速确认 |
| 环境 | Python 3.6 + PyTorch；repo 自述代码较 messy |
| CARE 匹配 | 中低：任务相关，但 CARE 缺模态/中心分布不同 |
| 预计接入 | 仅阅读 0.5-1 天；直接运行不推荐 |
| 最小实验 | 提取其 LGE/T2 preprocessing、coarse-to-fine 或 attention 思路，和当前 nnU-Net/metadata 对照，不跑旧训练 |
| 最可能提升 | `myops_scar`, `myops_edema` |
| 风险 | 旧环境、无权重/许可证、代码整理成本 |
| 结论 | 作为 MyoPS 实现参考，不作为主线工程 |

### 6.5 ModDrop++

| 字段 | 评估 |
|---|---|
| 链接 | `https://github.com/han-liu/ModDropPlusPlus` |
| 任务 | Missing-modality segmentation；MICCAI 2022 |
| 输入 | 多模态 MRI，原始实现面向 MS lesion |
| 输出 | lesion segmentation |
| 代码 | 有 |
| 权重 | UMCL/ISBI pretrained models 有 Google Drive 链接 |
| license | repo 页面未快速确认 |
| 环境 | Python 3.8, PyTorch/CUDA10, nibabel 等 |
| CARE 匹配 | 概念高，代码直接匹配低 |
| 预计接入 | 1-2 天阅读设计；3-5 天实现轻量 CARE adapter |
| 最小实验 | 在现有 pipeline 外先做 missingness-aware data table：complete/T2-missing/LGE-only 分组；设计 missingness mask 或 modality dropout 训练配置，而不是直接移植 repo |
| 最可能提升 | `myops_edema` |
| 风险 | 原任务非心脏；直接移植会引入框架成本 |
| 为什么优先于旧路线 | 它直接对准 CARE 的 blockwise missingness，而不是假设三序列永远存在 |

结论：作为方法设计优先参考；直接 clone 运行不是第一步。

### 6.6 BoundaryDoU Loss

| 字段 | 评估 |
|---|---|
| 链接 | `https://github.com/sunfan-bvb/BoundaryDoULoss` |
| 任务 | Boundary Difference Over Union loss；含 ACDC/Synapse demo |
| 输入 | 2D/medical segmentation 网络输出 |
| 输出 | loss，不是完整模型 |
| 代码 | 有 |
| 权重 | 非核心 |
| license | 未快速确认 |
| CARE 匹配 | 中：可能帮助小病灶 boundary/HD，但不解决缺模态 |
| 预计接入 | 1-3 天做 fold0 loss smoke，前提是已有训练 pipeline 支持低风险插拔 |
| 最小实验 | 只在 `myops_scar` 或 complete-case edema fold0 上对比 CE/Dice baseline；停止条件是训练不稳定或 local HD 不降 |
| 最可能提升 | `myops_scar`，次要 `myops_edema` |
| 风险 | loss 不能修复 center-confounded missingness；过早接入会转移主线 |
| 结论 | 第三梯队辅助，不是七天第一实验 |

### 6.7 InverseForm

| 字段 | 评估 |
|---|---|
| 链接 | `https://github.com/Qualcomm-AI-research/InverseForm` |
| 任务 | Boundary-aware segmentation loss/framework |
| 输入 | 自然图像 segmentation pipeline |
| 输出 | loss/framework components |
| 代码 | 有 |
| 权重 | 有 module/checkpoint 资源 |
| license | BSD-3-Clause-Clear |
| CARE 匹配 | 低到中：boundary 概念相关，但不是医学 CMR |
| 预计接入 | 不建议本冲刺主线接入 |
| 风险 | 旧 PyTorch/Apex/HRNet/OCRNet 依赖，迁移成本大 |
| 结论 | 降级为概念参考 |

### 6.8 StrainNet

| 字段 | 评估 |
|---|---|
| 链接 | `https://github.com/EpsteinLabUVA/StrainNet` |
| 任务 | 从 cine MRI 的 LV myocardium mask 序列估计 strain/motion |
| 输入 | binarized LV myocardium series `[1,Nx,Ny,Nt]`，不是 raw cine image |
| 输出 | displacement/strain 相关结果 |
| 代码 | 有 |
| 权重 | Dropbox pretrained model 链接 |
| license | 未快速确认 |
| CARE 匹配 | 低到中：可作 motion cue/QC，但必须先有可靠 myocardium mask |
| 预计接入 | 3-7 天，且依赖前置 mask |
| 最小实验 | 若 CineMA 产出稳定 myocardium masks，再用 StrainNet 对 1-2 cases 做 motion sanity |
| 最可能提升 | 间接帮助 `myocardium_cinemyops` |
| 风险 | 不直接做 segmentation；license/adapter 未确认 |
| 结论 | 不作为当前优先实验 |

## 7. 旧路线冻结清单

| 路线 | 是否冻结 | 停止理由 |
|---|---|---|
| LCC calibration / LCC 后处理主线 | 冻结主线，仅保留辅助 sanity | 它只能处理部分远端 false positive，不能解决 T2 missingness、validation complete shift、cine single-frame 语义错配 |
| MedNeXt 反复尝试 | 冻结 | 训练成本和不确定性高；没有证据表明它解决当前最主要数据机制 |
| MyoPS-Net zero-filled mapping channel | 冻结 | 原设定与 CARE `C0/LGE/T2/gd` 不一致；zero-filled missing channel 可能强化 center shortcut |
| U-MyoPS Stage1->Stage2 bridge | 冻结 | 三序列对齐假设与 CARE 大量缺 T2/C0 不匹配；Stage1 到 Stage2 inference bridge 不完整 |
| CineMyoPS 单帧 compact wrapper 主线 | 冻结 | raw 数据是真 4D cine，单帧化丢失时间信息；class_1 myocardium proxy 与 class_3 scar sanity 容易混淆 |
| 旧 validation zip candidate forensic | 冻结 | 本轮目标不是 submission 调参；继续追旧 zip 不会解释数据困难 |
| 继续大规模修 third_party MyoPS-Net | 冻结 | 缺少低风险新证据；剩余时间内不应投入大规模旧工程修复 |

## 8. 七天最小实验计划

### Day 1-2：CineMA adapter smoke

| 项 | 设计 |
|---|---|
| 输入 | 3-5 个 CineMyoPS train cases + 1-2 个 val cases；raw 4D cine |
| 改动范围 | 新增独立 adapter/diagnostic 脚本，不能改主训练代码；输出放 `results/diagnostics/` 或临时目录 |
| 外部资源 | CineMA repo + HuggingFace weights |
| 预期指标 | train class_1 myocardium Dice/LV sanity；输出非空；shape/spacing/affine round-trip 正确 |
| 成功标准 | 至少在 train cases 上 myocardium/LV mask 与 GT 有合理 overlap，且不会把 scar sanity 当主指标 |
| 失败判据 | 权重不可下载、license/依赖不可用、adapter 输出维度/spacing 无法稳定还原、myocardium Dice 明显低于当前 nnU-Net proxy |
| 回滚方式 | 删除独立 adapter 输出；不触碰主 pipeline 和 submission |

### Day 2-3：MyoPS T2-present edema diagnostic

| 项 | 设计 |
|---|---|
| 输入 | 80 个 complete train cases；validation 15 complete cases 仅做 unlabeled structure check |
| 改动范围 | 只读统计/diagnostic；可新增 markdown/csv diagnostic，不改训练代码 |
| 方法 | 对 edema 统计 T2 robust-z、myocardium-union prior、component size；验证 simple intensity prior 是否能分离 edema |
| 预期指标 | edema 在 T2 上的 lesion-vs-myocardium contrast、空间 prior coverage、远端 false positive risk |
| 成功标准 | 明确 T2-present expert 的输入/label/filter 规则，形成可训练 fold0 配置 |
| 失败判据 | T2 contrast 与 edema 不稳定，或者 label/affine mismatch 过大 |
| 回滚方式 | 保留诊断报告；不改变模型 |

### Day 3-4：Missingness-aware MyoPS routing 设计 smoke

| 项 | 设计 |
|---|---|
| 输入 | MyoPS train metadata + existing nnU-Net predictions/metrics（若已有） |
| 改动范围 | 只读分析或独立 routing prototype |
| 方法 | 按 `complete`, `C0+LGE`, `LGE-only` 分组，对 scar/edema local proxy 分开评估；设计 `edema=T2-present expert only`, `scar=LGE expert all cases` |
| 预期指标 | 分组 Dice/HD proxy；T2-missing cases 是否应排除 edema supervision |
| 成功标准 | 产出明确训练/推理 routing 规则：complete validation 走 complete expert，LGE-only 不参与 edema positive supervision |
| 失败判据 | 分组指标无法复现或现有预测不足以支持判断 |
| 回滚方式 | 只保留规则说明 |

### Day 4-5：CAA-Seg/AWSnet code reading bounded decision

| 项 | 设计 |
|---|---|
| 输入 | CAA-Seg、AWSnet repo |
| 改动范围 | 不接入主代码；只读记录 adapter points |
| 方法 | 核对 preprocessing、label mapping、multi-sequence fusion、license、是否可提取为轻量模块 |
| 预期指标 | 是否能在 CARE complete subset 上跑 fold0 smoke |
| 成功标准 | 找到可复用的 1-2 个低风险点，如 SSA alignment 或 LGE/T2 preprocessing |
| 失败判据 | 无权重、代码太旧、label mapping 不清、接入需要大规模重写 |
| 回滚方式 | 决策冻结，不 clone 到主 repo 或不纳入主线 |

### Day 5-7：一个小训练/推理 smoke 的准备，不立即长训

候选 A：CineMA anatomy branch 小批量 inference + local proxy。  
候选 B：T2-present edema expert fold0 短训配置。  
候选 C：LGE scar expert + myocardium prior fold0 短训配置。

选择规则：

- 如果 CineMA inference 能在 1-2 天内稳定跑通，优先推进 CineMA branch。
- 如果 CineMA 卡在依赖/权重，转向 MyoPS T2-present edema expert。
- 只有在前两者都有明确阻塞时，才考虑 scar 小病灶/boundary loss smoke。

## 9. 最小可执行实验优先级

### 第一优先实验：CineMA -> CARE CineMyoPS adapter smoke

理由：

- 直接解决 raw 4D cine 未被当前 pipeline 充分利用的问题。
- 外部资源的代码、权重、license 相对清楚。
- 失败后回滚成本低，不影响当前训练代码。
- 对 `myocardium_cinemyops` 的潜在收益最大。

最小执行定义：

- clone/read CineMA；
- 下载或定位 fine-tuned SAX segmentation weights；
- 对 3-5 个 CARE CineMyoPS train cases 做 frame/slice adapter；
- 输出 myocardium/LV mask；
- 只算本地 class_1 myocardium 和 LV sanity，不解释成 hosted result。

### 第二优先实验：MyoPS T2-present edema expert/routing

理由：

- 直接解决 `myops_edema` 的最大数据机制：T2 missingness 与 edema label 完全绑定。
- validation 是 complete 三模态，因此 T2-present expert 与 hosted 分布更接近。
- 可以先做 diagnostic，再决定是否短训 fold0。
- 比继续修 MyoPS-Net/U-MyoPS 更低风险。

最小执行定义：

- 只用 80 complete train cases 构造 edema diagnostic；
- 以 T2 robust-z + myocardium/pathology union prior 检查可分性；
- 定义推理时 complete cases 走 edema expert 的 routing；
- 失败时保留统计，不改主线。

## 10. 后续外部查询清单

| 查询目标 | 推荐查询 | 判断标准 | 失败 fallback |
|---|---|---|---|
| cine SAX segmentation 权重 | `CineMA SAX segmentation pretrained weights HuggingFace`, `ACDC M&Ms nnUNet pretrained cardiac MRI weights` | 有权重、license、inference example、SAX myocardium/LV labels | 用当前 nnU-Net Cine branch 做 anatomy prior，不接复杂 foundation model |
| M&Ms/ACDC 可迁移权重 | `M&Ms cardiac MRI segmentation pretrained nnUNet checkpoint`, `ACDC myocardium LV RV pretrained model GitHub` | checkpoint 可下载，label mapping 清楚 | 只做 architecture/spacing preprocessing 参考 |
| CAA-Seg 可复现性 | `CAA-Seg GitHub SSA myocardium segmentation weights` | 有完整训练/inference 文档，license 可用，label mapping 清楚 | 只借鉴 SSA 思路，不接 repo |
| MyoPS LGE/T2 实现 | `MyoPS2020 scar edema segmentation GitHub LGE T2`, `AWSnet MyoPS challenge code` | 能确认 preprocessing、labels、loss，不要求直接权重 | 只抽取 LGE/T2 expert 设计 |
| missing modality light methods | `HeMIS missing modality segmentation PyTorch`, `modality dropout medical segmentation PyTorch` | 轻量 fusion/mask 可嵌入现有 pipeline | 自己实现 missingness mask/routing |
| small lesion / HD loss | `small lesion segmentation nnUNet focal clDice boundary loss`, `BoundaryDoU medical segmentation GitHub` | loss 可独立实现，训练稳定，license 可用 | 先不改 loss，仅用 spatial prior 和 component diagnostics |
| cine temporal cue | `short-axis cine MRI temporal segmentation ConvLSTM GitHub`, `cardiac cine optical flow segmentation GitHub` | 有代码/权重，输入 raw cine，不依赖私有数据 | 用 2.5D frame stack 或 ED/ES heuristic |

## 11. 最终判断

本轮结论不是“再找更多论文”，而是“必须找更少、更准、更能落地的资源”。

当前 CARE 的困难机制已经足够明确：

- `myops_scar`：LGE-driven 小病灶 + HD-sensitive false positive。
- `myops_edema`：T2-present label mechanism + train/validation missingness shift + severe imbalance。
- `myocardium_cinemyops`：raw 4D cine 与当前 single-frame proxy mismatch + anatomy segmentation prior 不足。

因此，后续七天不应继续围绕 LCC/MedNeXt/旧 zip/旧 wrapper 消耗时间。应优先执行：

1. CineMA adapter smoke；
2. MyoPS T2-present edema expert/routing diagnostic；
3. 若前两项跑通，再考虑 CAA-Seg complete-case smoke 或 BoundaryDoU/small-lesion loss 的 fold0 bounded experiment。

这一路线的优点是每一步都有清晰输入、低改动范围、可量化 local proxy、失败判据和回滚方式，并且每一步都对应 CARE 数据本身的一个明确困难，而不是方法名驱动。
