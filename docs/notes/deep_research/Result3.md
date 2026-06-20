# CARE 2026 Myocardium challenge 定向深度研究与冲刺决策报告

## CARE 数据机制与真正的瓶颈

这次 CARE 2026 myocardium 赛道公开时间表显示，测试集已经在 2026 年 6 月 10 日释放，结果提交截止到 2026 年 7 月 10 日；同时，CARE 系列 myocardium 赛道在公开规则里明确允许使用预训练模型。这一点很重要，因为它意味着你们最有价值的策略不是“重写一个全新系统”，而是在可控改动下，把已经有代码、有权重、能快速做最小实验的模块拼成一个解释自洽的方法故事。CARE 公开 myocardium 赛道也一直把三个难点写得很清楚：多中心、缺失序列、跨序列失配。前一届 CARE-MyoPS 公布的官方标签值还是病理/结构分离的医学语义值，而不是训练时常见的紧凑类标：scar 为 2221，edema 为 1220，LV 为 500，myocardium 为 200，RV 为 600。你们现在内部 wrapper 若把它 compact 成 $0\sim5$，核心不是“能不能训”，而是必须保证训练语义、后处理语义、导出语义和 official metric 语义完全可逆，否则会出现看似涨点、实际提交错类的伪收益。citeturn2view0turn2view1

真正的第一瓶颈，我判断不是“跨序列没有配准所以一切都不行”，而是“缺模态与标签机制耦合得太强”。你给出的当前 CARE 内部统计是：train 里大量 case 不是完整三模态，而 T2 的存在又与 edema 标注高度绑定；validation 和 held-out 却是完整三模态。这个结构与公开 CARE 2024/2025 predecessor 的机制是一致的：公开 MyoPS++ 数据被作者明确分成三组，缺 T2 的组同时缺 edema 标注，缺 T2 且缺 bSSFP 的组还进一步缺 RV 标注；他们还直接把缺失序列置零后送入网络。也就是说，数据生成机制本身已经告诉我们，$m_{\mathrm{T2}}=0$ 这件事不是一个普通缺失值，而是一个“会改变监督定义”的事件。如果把 no-T2 case 当作 edema-negative，你训练到的很可能是“中心/协议/模态缺失 shortcut”，而不是真正的 edema 表征。公开 challenge 页面也把 missing sequences 和 misalignments 并列列为赛题核心难点。citeturn22view0turn2view1

因此，冲刺期最值得押注的主线应当是“把 availability 当成模型显式输入，并且把 edema supervision 做成条件监督”，而不是继续把缺模态伪装成零强度。用形式化的语言说，应该把每个模态的可用性向量 $m=(m_{\mathrm{LGE}},m_{\mathrm{C0}},m_{\mathrm{T2}})$ 作为 routing 条件，而不是让网络自己从零填充值里“猜”缺失。一个最小可实现的写法可以是
$$
z=\sum_{k\in\{\mathrm{LGE},\mathrm{C0},\mathrm{T2}\}} m_k\,\phi_k(x_k),\qquad 
p_{\mathrm{scar}}=D_{\mathrm{scar}}([z,\pi_{\mathrm{myo}},m]),\qquad
p_{\mathrm{edema}}=D_{\mathrm{edema}}([z,\pi_{\mathrm{myo}},m]),
$$
其中 $\pi_{\mathrm{myo}}$ 是 anatomy prior，而 edema 的监督要再乘一个可用性掩码
$$
\mathcal L_{\mathrm{edema}}=m_{\mathrm{T2}}\cdot \ell(p_{\mathrm{edema}},y_{\mathrm{edema}}).
$$
这不是形式主义，而是把数据机制写进优化目标里。HeMIS 的核心思想就是不要先合成或均值填充缺失模态，而是在 latent space 上只聚合“当前可用”的模态；后续的 sequence dropout 与 modality dropout 论文又进一步说明，训练期随机丢模态能显著提高模型对缺失输入的鲁棒性。对于 CARE 这种 train/val missingness shift 很强的场景，这类方法的工程性远高于“先补模态再分割”的大工程。citeturn14search0turn15search1turn35search1

scar 侧的主要工程风险则和 edema 不同。scar 在公开 CARE-MyoPS 及其前身设置里始终高度依赖 LGE，且通常是小病灶；这意味着 Dice 提升不一定对应 leaderboard 提升，因为远端极小 false positive 会把 Hausdorff 类指标拖得很难看。边界/表面类损失文献正是为这类“小前景、边界敏感”的分割问题设计的，MONAI 里也已经原生有 HausdorffDTLoss，可以低成本并入现有训练。对 scar，更重要的是“减少离心肌很远的假阳性”和“保持病灶在 myocardium 内”，而不是盲目追求更重的 backbone。citeturn16search0turn16search1turn16search2turn16search5

CineMyoPS 那个 leaderboard 的情况也类似。你给出的内部信息说明现有旧 pipeline 可能实际只取单帧、甚至还用了 compact label wrapper；这会直接把 cine 任务最值钱的信号——时序与运动——整个扔掉。CineMyoPS 论文非常明确：它不是“用 cine 图像替代普通静态 MRI 做单帧分割”，而是以 ED frame 为 reference，估计全心动周期的运动场，在 reference space 内融合 motion、warped anatomy 和 texture，并通过一致性损失在只有 ED anatomy label 的条件下把 anatomy 学到全周期。如果现在还只用单帧包装器，你们实际上没有使用 CineMyoPS 的中心思想。citeturn31view2turn31view3

## 三个 baseline 方法故事与 CARE 的错位

先看 MyoPS-Net。它真正做的事情并不是“把多模态拼成多通道，然后缺哪个就补零”。论文和官方代码都表明，它是一个 layer-level cross-modal fusion 框架：不同模态先各自编码，再通过 cross-modal feature fusion 模块在多尺度层内做来自“其他序列”的特征 max 聚合，并把这些跨模态特征送入 pathology-specific decoder。更关键的是，它不是一个统一病理头，而是显式允许 scar decoder 和 edema decoder 按临床语义绑定到不同模态，例如 scar decoder 主要连到 LGE，edema decoder 连到 T2；随后再用 myocardium prior and consistency 模块给 pathology localization 提供结构约束，并用 pathology inclusiveness loss 对 scar 与 edema 的空间关系加正则。它甚至明确讨论了 practical clinics 下不同模态组合的多种使用情景，而不是假设永远 full-sequence。citeturn5view0turn5view1turn34view0

这正好解释了为什么 MyoPS-Net 不能被简单等同于 CARE 里“zero-filled T1/T2* wrapper”那种做法。MyoPS-Net 当然也需要面对缺序列，但它的解决方式是“让病理特异性 decoder 与可用模态结构化耦合”，而不是把“模态缺失”编码成一个像素强度事件。换句话说，MyoPS-Net 的精神是 modality-specific routing 加 anatomy prior，而不是 naive zero-fill。对 CARE 来说，可借鉴的是两点：第一，scar 与 edema 不需要被迫共享完全同一个多类头；第二，myocardium prior 不是后处理修补，而应当在网络中作为 localization 约束。不能照搬的是它对五序列场景和固定 decoder 组合的原始设定，因为 CARE 当前公开/内部主战场是 $\mathrm{C0+LGE+T2}$ 三序列与部分缺失，而不是 $\mathrm{T1/T2^*}$ 扩展版。citeturn5view0turn5view1turn34view0

再看 U-MyoPS。它的核心故事是“先把未对齐多序列拉到同一个空间里，再做 anatomy extraction，再做 pathology segmentation”。方法里明确把 LGE 设为 common reference image，bSSFP 与 T2 通过 TPS 变换注册到 LGE，再把 warping 后的多序列特征送入 myocardium extraction decoder；在 pathology stage 里，又使用 spatial prior gate 把已经抽出的 myocardium 作为显式空间门控，限制 scar/edema 的搜索区域。更细一点说，U-MyoPS 不只是 image-level registration，它在 feature level 也做了 warping：不同 encoder 层的特征图会按 TPS 参数重标定之后再融合，这正是它区别于简单“先跑个配准软件再拼输入”的地方。citeturn6view0turn6view1turn26view0

但是，U-MyoPS 在 CARE 当前环境下有两个直接限制。第一个限制是训练数据形态。U-MyoPS 的公开实验建立在三模态成套样本上，而且 pathology label 会被先从原始 LGE/T2 空间对齐到共同空间后再联合训练；可你们当前 CARE train 中大量样本缺 T2 或缺 C0，这会让“Stage1 anatomy/registration → Stage2 pathology”这条桥在很多 case 上天然不完整。第二个限制是工程代价。完整复用 U-MyoPS 需要同时维护 registration、myocardium extraction 和 pathology segmentation 三部分，而且要处理 slice correspondence、header-based pairing、TPS 参数缩放与 feature warping。对于剩余窗口只有几周的比赛，这条路除非你已经有现成桥接代码，否则不适合作为主线重启。它最有价值的不是“全量照搬”，而是提醒我们：若 complete-case 子集验证显示 T2/C0 与 LGE 的空间错配确实明显，那么可以把“LGE reference + 轻量 feature warping + myocardium gate”作为 expert 分支插进 tri-modal subset，而不是作为全系统根基。citeturn6view0turn6view1turn25search1

最后看 CineMyoPS。它最容易被误读的地方，就是把它以为成“cine 的 nnU-Net 版单帧分割器”。其实它是一个三模块联合系统：先做 motion estimation，用 ED frame 作为全周期的 reference image；再做 anatomy segmentation，并且只需要 ED 的 anatomy label；然后在 MyoPS module 里把 motion、anatomy 和 texture 融合，并把每一帧的相关特征都变换到 reference space 做时序聚合。论文的 ablation 很清楚，time-series aggregation 是有效的，而且随着使用帧数增加，性能先上升后在大约 $4/6$ 心动周期帧数处进入平台；一致性损失也确实提升了 motion 与 anatomy 联学效果。citeturn31view0turn31view2turn31view3

所以，在 CARE 当前 cine 侧，如果 pipeline 还只是“抽一个 ED 或随机单帧，再跑 2D/3D 分割”，那就不是“没完全实现 CineMyoPS”，而是“从问题定义上就换了一个更弱的任务”。能借鉴的核心不是非要复制它整套网络，而是三个原则：ED reference、先稳 anatomy、再用少量多帧聚合 motion/texture/anatomy。不能直接照搬的是它完整 motion module + joint training 结构，因为这对现有工程侵入较大，而且 repo 当前更像基于 nnUNet 的专用实现，权重通过网盘分发、许可证也不清晰，适合读思想和做对照，不适合赛末作为唯一主线。citeturn18view0turn19view0turn31view0turn31view3

## 可落地的正式方法故事

我建议把正式方法故事收束为两个主故事，再把“配准”降格为一个条件触发的局部增强，而不是第三条主线。

第一个正式故事，最适合 MyoPS 两个 metric，也最符合你们当前数据机制，可以命名为 **availability-aware pathology-specific fusion**。它的叙事核心是：CARE 不是一个“所有模态同权、所有病灶同分布”的任务，而是一个“LGE 几乎总在并主导 scar，T2 只在部分 case 出现但主导 edema，C0/cine 更像结构先验”的任务。因此模型应当把可用性向量 $m$ 显式输入到融合与解码层，把 scar 和 edema 建成两个病理专属头，把 myocardium/LV/RV 作为 anatomy 支路稳定提供结构先验。最小版本不需要复杂 mixture-of-experts，只要做到三件事：第一，encoder 分模态，fusion 做 late fusion 而不是所有序列原地 channel concatenate；第二，训练期对 full tri-modal case 做 modality dropout，让模型见过 $\{LGE\}$、$\{LGE,C0\}$、$\{LGE,T2\}$、$\{LGE,C0,T2\}$ 等组合；第三，edema loss 只在 T2-present case 上计算，不把 no-T2 case 视作 edema negative。这个故事在理论上受 MyoPS-Net、HeMIS、ModDrop/sequence dropout 支持，在工程上又能直接落到 nnU-Net 或 MONAI 现有 pipeline 上。citeturn5view0turn5view1turn14search0turn15search1turn35search1turn24view1turn20search3

这个故事为什么适合 CARE，而不是泛化到任何多模态医学影像任务？因为 CARE 的缺模态不是随机 MCAR，而更接近“与中心和标注机制绑定的结构化缺失”。当缺 T2 的样本几乎不带 edema 标注时，任何统一五类 softmax 如果不加可用性掩码，都容易把“看不到 T2”学成“绝不应该预测 edema”。availability-aware routing 恰恰是把这种偏差显式控制住。具体到 metric，$\mathrm{myops\_scar}$ 会受益于更稳定的 LGE 主分支和 anatomy containment；$\mathrm{myops\_edema}$ 会受益于不再把 no-T2 当负样本，以及只在真正有 T2 证据的样本上学习 edema；而 $\mathrm{myocardium\_cinemyops}$ 不直接从这个故事获益最大，但其中的 anatomy 分支和 availability logic 可以与第二个故事对接。citeturn2view1turn22view0turn5view0turn5view1

第二个正式故事，最适合 cine leaderboard，也能反哺 MyoPS 的 myocardium prior，可以命名为 **anatomy-first temporal cine adaptation**。它的叙事核心是：在 cine CMR 里，最稳、最可迁移、最容易借到外部资源的信号不是 scar/edema 本身，而是 LV/RV/myocardium anatomy；而 pathology 相关信息更多体现为 wall thinning、motion abnormality 与局部 texture 异常。所以，先用现成 SAX cine anatomy 模型把每帧的 LV/RV/MYO 稳住，再引入最轻量的时序聚合，往往比从零复现一个全功能 CineMyoPS 更符合冲刺期。最小可实现版本可以是：以 ED 为 reference，抽取固定少量关键帧，例如 $\{\mathrm{ED}, \mathrm{ED}+k, \mathrm{mid}, \mathrm{ES}, \mathrm{ES}+k\}$，先做 frame-wise anatomy segmentation，再把 anatomy mask、原始强度与简单 frame-difference 或 optical-flow-like cue 一起送入 pathology/anatomy refiners，并用 temporal consistency 约束相邻帧预测。这个故事与 CineMyoPS 一致，因为它同样承认 ED reference、motion/anatomy 联动和 time aggregation 的价值；但它避开了重型 joint-registration-style training，更能在 3–5 天内形成证据。citeturn31view0turn31view2turn31view3turn9view0turn32view2

至于 **registration-before-fusion only where justified**，我不建议把它写成主故事，而应定位成 Story A 的“条件触发 expert”。判断逻辑很简单：如果 complete $\mathrm{C0+LGE+T2}$ 子集上，你们可视化发现 scar/edema 失败主要发生在明显 slice shift、心肌边界位置偏移、或 T2 edema 区域与 LGE/C0 解剖不对位，那么就上一个轻量 LGE-reference alignment expert；如果失败主要出现在 no-T2 shortcut、edema 过抑制、或远端 scar false positive，那么继续加配准几乎一定是次优投入。结合公开 CARE 赛题描述与当前内部统计，我的判断是：**CARE 现在的主瓶颈优先级应当是 missingness/label mechanism，高于 registration**。配准不是不重要，而是不值得在当前窗口里全量重启 U-MyoPS。citeturn2view1turn22view0turn6view0turn6view1

## 外部资源分级与取舍

下面这部分不是“论文清单”，而是面向你们决策的资源分级。为了满足冲刺可执行性，我把每个资源都按同一套字段压缩整理：名称与年份、链接、任务、输入/输出、代码与权重、许可证、是否需要私有数据、环境负担、能否在 3–5 天做 CARE 最小实验、最可能提升哪个 metric、失败风险，以及它和 CARE 数据机制的关系。

**立即值得尝试**

| 资源 | 任务与输入输出 | 工程状态 | CARE 最小实验、最可能收益与风险 |
|---|---|---|---|
| **MyoPS-Net repo 与论文，2023** citeturn34view0turn4view0 | 任务是多序列 CMR 病理分割；输入原始论文支持 $\mathrm{C0/LGE/T2/T1/T2^*}$，核心思想对 $\mathrm{C0/LGE/T2}$ 直接适配；输出 scar/edema，并在网络中显式使用 myocardium/LV prior。citeturn5view0turn34view0 | 有代码，无公开权重信息；MIT 许可证；公开 repo 用 PyTorch，训练命令与数据组织清楚；不需要私有数据才能读懂和改写。citeturn34view0 | 这是最适合直接“借思想、借结构、不照搬全仓库”的资源。3–5 天内完全可以在 nnU-Net/MONAI 现有框架里实现“LGE 主 scar 头 + T2 主 edema 头 + myocardium prior + availability mask”。最可能提升 $\mathrm{myops\_scar}$ 和 $\mathrm{myops\_edema}$。主要风险是原始代码面向五序列，直接复现价值不高，但迁移思想的性价比极高。citeturn5view0turn5view1turn24view1turn20search3 |
| **CineMA repo 与模型，2025–2026** citeturn9view0turn8search17 | 任务是 cine CMR foundation model；对 SAX 分割，输入为单时间帧 SAX，输出 ventricle 与 myocardium segmentation；repo 还支持 ACDC、M\&Ms、M\&Ms2、Myops2020 等数据文档。citeturn13view0turn13view4 | 有代码，有 Hugging Face 预训练 backbone 和 fine-tuned 模型；MIT 许可证；安装流程与 inference script 明确；不需要私有数据即可做推理与轻量微调。citeturn11view0turn13view0turn13view4 | 这是当前最值得拿来做 **cine anatomy 先验** 的资源。3–5 天内可以完成两件事：其一，直接在 CARE 4D cine 上跑 frame-wise myocardium/LV/RV 先验；其二，把 ED frame 的 anatomy encoder 迁移到 $\mathrm{myocardium\_cinemyops}$。最可能提升 $\mathrm{myocardium\_cinemyops}$，并间接提升 MyoPS 的 anatomy prior。风险是其官方 segmentation 入口默认单帧，不会自动吃掉完整时序，所以必须由你们自己再加 temporal aggregation。citeturn13view4turn31view2 |
| **CorSeg-CineSAX repo，2026** citeturn9view2turn8search1 | 任务是短轴 cine cardiac MRI 全自动 anatomy segmentation；输入单张 2D slice 或 NIfTI/DICOM；输出 LV myocardium、LV cavity、RV。citeturn9view2turn11view5 | 有代码，有预训练权重；MIT 许可证；依赖轻，Python $\ge 3.9$、PyTorch $\ge2.0$、MONAI $\ge1.3$ 即可；推理显存大约 2–4GB。citeturn11view4turn32view2turn32view3 | 这是最快能落地的 **cine anatomy sanity check**。1–2 天就能验证当前 CARE cine 的 label 语义、affine、方向和 slice 选取是否存在隐藏 bug。最可能给 $\mathrm{myocardium\_cinemyops}$ 提供一个可解释起点，也能给 MyoPS 的 C0/ED anatomy prior 做弱监督。主要风险是当前仓库本质上是 2D slice-wise inference，甚至默认对 3D volume 只取 representative 2D slice，因此它更适合作“先验证，再决定是否 adapter 微调”，不适合作最终时序方案。citeturn32view2turn32view3 |
| **nnU-Net v2，2024+** citeturn24view1 | 任务是 supervised biomedical segmentation 框架；支持 2D/3D、多通道输入；不限定模态与标签。citeturn24view1 | 有稳定代码，Apache-2.0 许可证；安装简单；没有通用“现成权重能直接解决 CARE”的承诺，但非常适合二次开发。citeturn24view1 | 如果你们当前 CARE pipeline 已经在 nnU-Net 附近，那么最小改动路线就应继续基于它：加 availability channels、损失 mask、scar/edema 双头、myocardium extra channel、expert ensemble，都是 3–5 天级别。最可能帮助三个 metric 的统一工程落地。风险不在框架本身，而在你们是否克制住不去做大改重写。citeturn24view1turn20search3 |

**需要先查证**

| 资源 | 任务与输入输出 | 工程状态 | CARE 最小实验、最可能收益与风险 |
|---|---|---|---|
| **U-MyoPS repo 与论文，2023** citeturn26view0turn4view1 | 任务是未对齐多序列 CMR 的 registration + myocardium extraction + pathology segmentation；输入是 bSSFP、LGE、T2；输出 myocardium、scar、edema。citeturn6view0turn6view1 | 有代码，Apache-2.0；未看到公开权重与清晰环境脚本；repo 说明 prior-aware sub-network 基于 nnUNet。citeturn26view0turn27view0 | 只有在 complete tri-modal 子集上明确证明“空间错配是主故障源”时，才值得在 2–3 天内做一个 **LGE-reference expert** 的最小复用。最可能提升 $\mathrm{myops\_edema}$，其次是 scar。失败风险是桥接成本高，且 CARE 当前的主问题可能不是 misalignment，而是 conditional supervision。citeturn6view0turn6view1turn22view0 |
| **CineMyoPS repo 与论文，2025** citeturn18view0turn2view2 | 任务是从 cine CMR 直接分割 scar/edema；输入完整心动周期 cine；输出 pathology，并隐式需要 motion/anatomy modules。citeturn31view2turn31view3 | 有代码，权重通过百度网盘发放；未见清晰许可证；实现依赖 nnUNet 自定义 trainer。citeturn18view0turn19view0 | 值得阅读与对照，但不建议未经验证直接主线复现。先查证两件事再决定是否局部借用：一是它的 repo 是否真的使用完整时序而不是近似包装；二是你们数据转换到其输入格式是否会再次引入 label semantic mismatch。若能打通，最可能提升 $\mathrm{myocardium\_cinemyops}$。风险是许可证与工程边界不够清楚。citeturn18view0turn31view0turn31view3 |
| **ViTa repo，2025** citeturn9view1turn8search13 | 任务是 cardiac MRI foundation model，融合 3D+T cine 与 tabular；支持 segmentation、phenotype prediction、disease classification。输入数据结构默认包含 SAX、LAX 以及分割标签。citeturn9view1turn12view4 | 有代码，有 Hugging Face 权重；MIT 许可证；但 repo 默认数据组织含 tabular 与多视图，多数脚本围绕 UK Biobank 预训练与下游任务。citeturn12view3turn12view4 | 如果 CineMA adapter 失败，才值得查证 ViTa 是否能仅用 SAX imaging-only segmentation 轻改接入 CARE。最可能帮助 $\mathrm{myocardium\_cinemyops}$。主要风险是数据组织和任务头远重于当前冲刺需求。citeturn9view1turn12view4 |
| **q-cardIA self-supervised cine segmentation repo，2024** citeturn9view3 | 任务是 2D cine segmentation 的自监督预训练比较；输入是 cine CMR，输出 anatomy segmentation。citeturn9view3 | 有代码；大部分代码 MIT，但含一部分来自 DINO 的 Apache 2.0 代码；没有公开 release 或权重；还依赖自家的 qcardia-data 与 qcardia-models 包。citeturn33view2turn33view3turn33view4 | 这更像“如果你们要自己做 cine 自监督”的第二备选，不适合当前 7–10 天窗口。只有在现成 anatomy 预训练都失败时再考虑。最可能帮 $\mathrm{myocardium\_cinemyops}$，但启动成本偏高。citeturn9view3turn33view0 |

**概念可借鉴但不适合本次冲刺**

| 资源 | 核心思想 | 为什么可借鉴 | 为什么这次不适合主投入 |
|---|---|---|---|
| **HeMIS，2016** citeturn14search0 | 在 latent space 对当前可用模态求统计聚合，而不是补缺模态。 | 对 CARE 的 availability-aware fusion 非常贴切，尤其适合把缺 T2 从“像素事件”变成“结构化输入”。citeturn14search0 | 论文老、心肌专用代码并不现成；最好的用法是自己实现“可用模态均值/方差聚合 + mask embedding”，而不是去复刻原仓库。 |
| **Sequence Dropout，2023** citeturn15search1 | 训练时随机移除 MRI 序列，让模型学会在缺序列下工作。 | 对 CARE 尤其重要，因为 train/val 的 missingness shift 很强；实现成本很低。citeturn15search1 | 它本身不是现成心肌方法故事，应该作为 Story A 的训练策略，而不是单独路线。 |
| **ModDrop，2014** citeturn35search1 | 通过随机 dropping separate channels 保留 modality-specific 表征并学 cross-modality correlation。 | 很适合支持“scar 头靠 LGE、edema 头靠 T2、C0 做 anatomy prior”的叙事。citeturn35search1 | 原始任务不是医学分割，不值得单独追代码。 |
| **CARE 2024 partial-modality RSN 章节，2025** citeturn30search0turn30search2 | two-stage + multi-model ensemble + region specific normalization 处理 partial modalities。 | 它证明“按部分模态设计模型/归一化”已经出现在 CARE 系列赛题中，方向是对的。citeturn30search0 | 没有清晰公开代码，且多模型 ensemble 在当前时间窗不划算，更适合作为写作与 ablation 参考。 |

**不建议投入**

| 资源或路线 | 不建议投入的原因 | 与 CARE 当前机制的冲突 |
|---|---|---|
| **把缺 T2 缺 C0 一律 zero-fill，然后统一五类监督到底** | 公开 CARE 2024 方法自己就写明会把缺序列置零，但同时也承认缺 T2 的组缺 edema 标签；这说明 zero-fill 会把 missingness 和标签缺失绑定在一起。citeturn22view0 | 它最容易学到 center/missingness shortcut，直接伤害 $\mathrm{myops\_edema}$。 |
| **完整重跑 MS-CaRe-CNN 类两阶段 3D 多折 ensemble** citeturn22view0 | 公开实现用 5-fold ensemble，单模型训练约 38 小时；而且它把缺模态置零，并且重型 3D end-to-end 两阶段对冲刺期不友好。citeturn22view0 | 训练/回滚成本过高，不符合你们“8 小时内拿证据、失败容易回撤”的约束。 |
| **直接复刻 MyoPS2020 winner 仓库** citeturn24view0 | 它依赖 PyMIC、GeodisTK、老版 nnUNet 工作流，且 coarse-to-fine 设计面向完整三模态输入与旧 challenge 数据格式。citeturn24view0 | 对当前 CARE 的 partial modality 与 cine 4D 适配都不顺手，环境债很大。 |
| **把 ViTa 当成这次冲刺的主 backbone** citeturn9view1turn12view4 | 它很强，但 repo 与数据组织明显更偏向多视图、多任务、含 tabular 的大一统框架。citeturn9view1turn12view4 | 当前目标不是搭 foundation model story，而是剩余时间内涨榜。ViTa 更像赛后路线。 |

如果现在还要新增搜索，我认为**不需要再广泛找“更新的大模型”**。真正值得补搜的，只剩两类非常窄的资源：其一，是“有权重、许可证清晰、能直接输出 SAX myocardium/LV/RV 的轻量 cine 模型”；其二，是“有现成 PyTorch 代码、能作为模块插入而不是重写全系统的 LGE-reference STN/TPS feature-warp block”。除此之外，再搜更多新 paper 的边际价值已经很低。citeturn2view0turn9view0turn32view2

## 三个 leaderboard metric 的工程抓手与应停路线

对 $\mathrm{myops\_scar}$，我建议把目标明确定义成“LGE-driven scar expert + myocardium containment + HD-sensitive false-positive suppression”。scar 的主信息源仍然应该是 LGE，这一点在 CARE 赛题说明、MyoPS-Net 的 decoder 设计和 U-MyoPS 的 LGE-reference 设定里都很一致。工程上可以把 scar 做成 binary 或 one-vs-rest 头，而不是依赖统一五类 softmax 去学一个极小病灶。最小损失组合建议是
$$
\mathcal L_{\mathrm{scar}}
=
\mathcal L_{\mathrm{DiceCE}}
+\lambda_b\mathcal L_{\mathrm{boundary}}
+\lambda_h\mathcal L_{\mathrm{HD}}
+\lambda_c\mathcal L_{\mathrm{contain}},
$$
其中 $\mathcal L_{\mathrm{contain}}$ 用来惩罚 scar 跑到 myocardium 之外，$\mathcal L_{\mathrm{boundary}}$ 和 $\mathcal L_{\mathrm{HD}}$ 分别对应边界与 Hausdorff 敏感性。实现上完全没必要自创 loss：boundary loss 有现成官方实现，MONAI 也已有 HausdorffDTLoss。后处理则应优先做 myocardium-mask 内裁剪与小连通域抑制，因为 scar 的 leaderboard 常常死在远端 FP，而不是死在局部漏一毫米。citeturn2view1turn5view0turn6view1turn16search0turn16search2turn16search3

对 $\mathrm{myops\_edema}$，最重要的不是更复杂的 backbone，而是**T2-present only supervision**。U-MyoPS 与 CARE 数据页面都清楚表明 edema 标签本身就来自 T2 侧；公开 CARE 2024 方法也把缺 T2 的组单独建模，因为它们同时缺 edema 标注。于是，你们最该冻结的旧路线就是“no-T2 样本按 edema-negative 喂给统一分类头”。正式实现里应当把 edema 头做成条件头，只在 $m_{\mathrm{T2}}=1$ 的案例上回传病理监督；对于 no-T2 样本，能用的监督只剩 anatomy、一致性、甚至 scar/正常心肌相关约束，但不是 edema-negative。若你们还想用 scar–edema 空间关系，可以借 MyoPS-Net 的 pathology inclusiveness 思路，但要把它当作数据集建模 prior，而不是医学绝对真理；在 U-MyoPS 的公共实现里，scar 与 edema overlap 甚至会被直接归并为 scar，这也提示你们在 label merge/export 阶段必须一致。citeturn5view1turn6view1turn22view0

对 $\mathrm{myocardium\_cinemyops}$，核心不是直接做病理，而是先把 anatomy 这件事做对。CineMyoPS 已经证明，仅用 ED frame 的 anatomy 标注，通过 motion–segmentation consistency 也能把 anatomy 学到整个心动周期；同时它的 ablation 还显示，多帧时序聚合比单帧更好，并在使用大约 $4/6$ 帧时进入效率–性能平衡区。因此，这个 metric 的最小强基线不该是 single-frame wrapper，而应该是“外部 anatomy 预训练 + 关键帧聚合 + temporal consistency”。如果外部 anatomy 模型已经能把 LV/MYO/RV 在多帧上稳定输出，那么你们甚至可以先不碰 pathology，先保证 label 语义、空间方向、时间轴排序、frame selection 与 affine 一致；对 cine leaderboard，这些工程正确性往往比“换大模型”更能快速带来真实提升。citeturn31view0turn31view2turn31view3turn9view0turn32view2

这里也能顺手回答“哪些旧路线不该继续投”。第一，**zero-fill missing modality 并把 no-T2 当 edema negative** 应冻结。第二，**single-frame cine wrapper 冒充 CineMyoPS** 应冻结。第三，**把配准当第一优先级重做整条 Stage1→Stage2 管线** 应冻结，除非 complete-case 分析已经明确显示错位比缺模态更致命。第四，**忽视 label compact/official map 不一致** 应立即冻结并补单元测试。公开 CARE 页面给出的官方 label values 与你们当前 compact wrapper 本就不一致，这不是论文问题，而是提交正确性问题。citeturn2view1turn22view0

## 未来七到十天执行路线与决策门

下面这条路线默认以 2026 年 7 月 10 日提交截止为约束，目标不是做出“最全路线图”，而是在 7–10 天内把不确定性打穿，并把主线固定到可提交版本。citeturn2view0

| 时间窗 | 要做的事 | 推进门 | 换资源门 | 冻结门 |
|---|---|---|---|---|
| **第一个阶段** | 先做两条最小证据链。其一，跑你们正在做的 **CineMA adapter pilot**，至少验证 ED frame 与少量关键帧上的 myo/LV/RV 质量、时间轴排序、label map、affine。其二，跑 **T2-present edema pilot**，比较“只在 T2-present 上做 edema supervision”与“所有样本统一训练”的差异。citeturn9view0turn13view4turn22view0 | 若 CineMA pilot 在内部 val 或 leaderboard proxy 上让 myocardium 稳定提升，哪怕只是 $+1.5$ Dice 左右，或明显减少 frame-to-frame jitter，就推进 Story B；若 edema pilot 在 T2-present fold 上相对旧路线有稳定收益，哪怕只是 $+2$ Dice 或显著减少远离心肌的 edema FP，就推进 Story A。 | 如果 CineMA 只在单帧好、跨帧不稳，则立刻换成“CineMA/CorSeg 输出 anatomy 先验 + 你们自己的 temporal smoother”，而不是继续深挖 adapter；如果 edema pilot 不涨而且 loss mask 实现无误，则说明你们现有 T2 分支表征不足，需要改 fusion 而不是继续纠结 supervision。 | 如果 pilot 的任何收益都只存在于 compact-label 内部指标，而一映射回 official 语义就消失，说明是 wrapper 问题，先冻结模型开发，修 label/export。 |
| **第二个阶段** | 正式实现 Story A 的最小版：LGE 主 scar 头、T2 主 edema 头、共享 anatomy 头、availability embedding 或二进制 mask 通道、T2-masked edema loss、myocardium containment。scar 损失加入 boundary/HD 项，但先只对 scar 类开，不要一口气改全部标签。citeturn5view0turn5view1turn16search0turn16search2 | 如果 scar expert 相对当前基线能在内部验证中减少明显远端 FP，或者 HD proxy 下降而 Dice 不退步太多，就保留边界项进入正式版本。 | 如果加入 boundary/HD 后优化不稳，就退回 DiceCE + containment + 后处理，不要和 loss 死磕。 | 如果 availability-aware 版本在 scar 和 edema 二者上都不如你们当前统一模型，先检查是否因为 no-T2 样本仍在错误参与 edema loss；若逻辑无误仍失败，则冻结复杂 fusion，只保留条件监督。 |
| **第三个阶段** | 正式实现 Story B 的最小版：ED reference、关键帧集、frame-wise anatomy prior、时序一致性或多帧投票。先把目标限制在 $\mathrm{myocardium\_cinemyops}$，不要先追 scar/edema from cine。citeturn31view0turn31view2turn31view3 | 如果多帧版本相对 single-frame wrapper 在 myocardium 上有稳定提升，哪怕只是 1–2 点，也应直接替换旧 wrapper，因为这说明你们终于开始用 cine 的时序信息了。 | 如果多帧聚合增益很小，但 anatomy 先验本身好，就把 Story B 收缩成“外部 anatomy teacher + 单帧 student + time-consistency 正则”，避免过度加模块。 | 如果 CineMA/CorSeg 输出和 CARE 标签语义始终对不上，先冻结外部预训练路线，改用你们自己的 anatomy 头，但保留 temporal aggregation 逻辑。 |
| **最后阶段** | 只做条件触发的 alignment 检查。挑 complete tri-modal 子集，人工看最差的 edema/scar 例子，判断错误是不是明显来自跨序列错位。若是，再做一个局部 LGE-reference alignment expert；若不是，直接收敛主线，不再加 registration。citeturn6view0turn6view1 | 只有当可视化明确看到“同一病灶在 T2/LGE/C0 上位置错开导致融合误导”时，才推进 expert。 | 如果只是少数 case 有错位，但总体错误仍是 missingness shortcut 或远端 FP，就不需要新 paper/repo，继续主线。 | 若 1 天内不能做出 alignment expert 的可运行版本，立即冻结该路线。 |

更具体地说，**当前正在跑的两个 pilot 出结果后，应该这样决策**。如果 **CineMA adapter pilot** 给出的结论是“单帧 anatomy 已明显稳于现有 cine wrapper，但多帧还没接起来”，那就不要再找新 backbone，直接推进 Story B 的轻量 temporal aggregation；如果它的结论是“外部 anatomy 在 CARE 上语义映射混乱，连 ED 都不稳”，那就冻结预训练迁移主线，只保留其产出的数据检查价值，并转向自训 anatomy 头。相反，如果 **T2-present edema pilot** 证明“只在 T2-present 样本上做 edema supervision 明显更干净”，那 Story A 就应该被立刻升级为正式实现的中心；如果它不涨，但错误主要变成 recall 下降而 precision 变高，那么问题通常不是思路错，而是 T2 分支容量/融合深度不足，此时该加的是 pathology-specific late fusion，而不是把 no-T2 又塞回 edema-negative。citeturn5view0turn5view1turn14search0turn15search1

把这些门合起来，最后的总判断其实很明确：**现在最值得推进的正式方法故事，是“availability-aware pathology-specific fusion”作为 MyoPS 主线，加上“anatomy-first temporal cine adaptation”作为 Cine 主线；配准只在 complete-case 明确证实必要时，作为 tri-modal expert 局部引入。** 这两条线都能解释清楚、都能在 1–2 周内接入、都能在 8 小时级别 job 内得到证据，而且失败后容易回滚。相反，凡是要求你们重写全套 registration–segmentation pipeline、重新搭多折重型 ensemble、或把 foundation model 框架整体搬进来再适配 CARE 的路线，都应该降级。citeturn2view0turn2view1turn6view0turn31view3turn24view1