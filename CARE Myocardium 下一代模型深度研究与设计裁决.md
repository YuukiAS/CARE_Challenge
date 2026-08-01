# CARE Myocardium 下一代模型深度研究与设计裁决

## 执行摘要与研究边界

这轮研究的结论不是一个乐观的“继续加训即可翻盘”，而是一个更严格的裁决：**NO_GO_FOR_HIGH_GAIN_MODEL**。原因并不在于“完全没有改进空间”，而在于当前可核验本地证据、公开仓库状态、独立视觉图册和针对性一手文献，**不足以支持“在 CARE official validation 口径下，以单-backbone 新模型可信地显著超过当前 nnU-Net，并同时在 scar 与 pure edema 上形成约 $$0.1$$ Dice 量级的可兑现上限”**。V4 证据包明确把“取证完成”“科学证据充分”“当前模型成功”“可进入深研设计”四件事拆开；其中科学证据状态是 $$\text{SUFFICIENT}$$，但当前模型状态仍然是 $$\text{FAILED\_GATE}$$，PRISM W3 也仍然是失败状态，这一点没有被 strict validator 的 $$\text{VERIFIED\_COMPLETE}$$ 覆盖。fileciteturn12file0

我同时采用了项目自身规定的优先级：**当前项目运营边界以最新 main 可见状态与 CURRENT.md 为准，历史取证数字以 V4 证据包为准**。当前公开 main 可见的最新提交是 2026-07-22 的通知类更新，CURRENT.md 明确写到：Route A/B/C 仍是证据路线，不是被晋升的解决方案；Batch8 的最新 official hosted validation 仍低于 nnU-Net anchor，scar 约为 $$0.9097$$、edema 约为 $$0.9185$$，而 anchor 大约是 scar $$0.92$$、edema $$0.923$$；运营完成不等于科学成功。citeturn13view0turn12view0 V4 则把强基线绑定得更清楚：完整 decoder 保留的 nnU-Net 变体 $$\text{D0\_IDENTITY}$$ 在 official validation 上的 label-5 scar Dice 为 $$0.9224$$，official pure-edema label-4 Dice 为 $$0.9231$$；而 decoder reset 立刻把 scar 拉到 $$0.547$$、edema 拉到 $$0$$，只训顶层也只能到 scar $$0.7108$$、edema $$0.2664$$，短程修复完整 decoder 又能回到约 $$0.923$$。这说明当前问题首先不是“缺一个花哨高层模块”，而是**不能再破坏完整 decoder 与成熟训练 recipe 所承载的能力**。fileciteturn12file0

就当前本地证据而言，真正稳固的事实主要有四类。第一，数据语义必须冻结为：总训练病例 $$220$$；官方 pure edema 的可靠评价分母是 **真实 T2-present 且可靠标注的 $$80$$ 例**；scar 对应内部 label $$5$$，official pure edema 对应内部 label $$4$$；no-T2 病例不能充当 pure-edema 阴性监督。V4 主报告中确实残留一处过期文本把 $$t2\_present$$ 写成了 $$220$$，但同一证据包在 pure-edema brief 与 design input 页面都把 official denominator 绑定为 $$80$$，因此应采纳 $$80$$ 而不是过期 prose。fileciteturn12file0 第二，强基线是 nnU-Net，不是历史 CARE 路线；本地标准化 OOF 结果里，nnU-Net 的 scar 均值 Dice 为 $$0.5610$$，pure edema 为 $$0.4308$$，而 MoSAIC clean OOF 只有 scar $$0.3782$$、pure edema $$0.0528$$。fileciteturn12file0 第三，V4 的 large-gain 结论已经排除了“靠 selector、threshold、TTA、弱 residual correction 或简单 recipe 复用拿到 $$\approx 0.1$$ Dice”的路径：相对 nnU-Net，scar 的 case-oracle 上界只有 $$0.0220$$，pure edema 只有 $$0.0023$$；虽然 voxel oracle 仍显示 scar $$0.2375$$、pure edema $$0.1730$$ 的理论可恢复量，但那要求**引入新的病灶形成/判别机制**，而不是再做弱 anchor correction。fileciteturn12file0 第四，V4 还明说 alignment 现在最多是可选诊断或安全模块，不是主机制。fileciteturn12file0

因此，本报告给出的不是“授权长训练”的 GO，而是：**给出一套最值得实现、且不留设计空白的下一代单-backbone 研究合同；同时明确指出，它目前只配得上“有边界的研究性原型”，还配不上“高增益主航道”**。换句话说，本文中我仍然会给出**一个首选架构**与**一个更保守备选**，因为这是后续 Codex 实现所需要的；但最终项目裁决仍是 **NO_GO_FOR_HIGH_GAIN_MODEL**。这一结论来自本地证据包、CURRENT.md、独立 atlas 视觉判读和外部一手文献的一致指向，而不是主观保守。fileciteturn12file0 citeturn12view0turn39search0turn39search4

## 本地证据复盘与失败归因

先看数据与任务本体。CARE MyoPS++ 官方任务本来就不是 MyoPS 2020 那种“每例三序列齐全、预对齐”的干净设置，而是 **多中心、缺模态、存在失配** 的真实任务；官方页面明确把这些都列为主要挑战。公开的 CARE 2024/2025 官方任务页面都把 missing sequences 与 misalignments 列为核心难点，而 MS-CaRe-CNN 的 MyoPS++ 论文也给出了七中心训练/验证/测试划分，说明 Center A 以 LGE-only 为主，B/C/D 才是 trimodal 主体，训练中本来就存在强烈的不均衡缺模态分布。citeturn39search0turn39search4turn39search6 V4 证据又进一步把本地训练可用总体绑定为 $$220$$ 例、T2-present official pure edema denominator 为 $$80$$、C0-present 为 $$104$$。因此，**scar 与 pure edema 从监督语义、可用样本量到可用模态，都是两类真正不同的问题**。fileciteturn12file0

再看历史路线到底留下了什么“可以保留的经验”，以及什么“必须禁止复用”。V4 对 Batch7 的判定非常清晰：可以保留的是**病种专属 candidate/proposal supervision 的方向**、scar 与 edema 分开度量、help/harm 与 remote-FP 安全门；但历史实现的均值非 anchor 增量是 scar $$-0.036915$$、edema $$-0.006767$$，而且还存在“模块存在、梯度存在、却没有进入 final logits 或没有形成 meaningful refiner-minus-proposal 增量”的问题，所以**只能保留思想，不能复用实现**。fileciteturn12file0 MMRD 留下的可保留经验更窄：**reliable-label/no-T2 hygiene 是正确的数据规则**，modality dropout 可以保留为训练策略待测，但不是模型增益证据；distillation 相比 direct 的均值 Dice 还是 $$-0.175652$$，simple residual head 则被明确列为不得按原样复用。fileciteturn12file0 Cascade 留下的是 teacher-cache provenance、ROI coverage、bounded-correction safety accounting 和 help/harm 审计，而不是“prototype 已被证伪”这种旧结论；V4 反而重申了 prototype control 没有被完整隔离，所以历史 prototype negative conclusion 已经不能再当定论，但 bounded correction 的实际 ceiling 很低，不能再被包装成高增益主机制。fileciteturn12file0 ARC 的价值在于**单一共享编码主体、显式 modality gate、no-T2 exact zero 与输入合同**，而不是其具体实现恢复了 nnU-Net 的能力；V4 直接指出 ARC clean fold1 只证明了若干 implementation property，不证明它是成功模型。fileciteturn12file0

把这些证据放在一起，失败归因就非常集中，而不是“到处都差一点”。Scar 的失败主轴是：**小病灶与多连通域漏检、边界欠分割、remote FP、blood-pool / normal-myocardium confusion，以及 decoder 能力损失**。Pure edema 的失败主轴则是：**T2 依赖但只有 $$80$$ 例可靠监督、diffuse region 边界模糊、跨中心表征不稳，以及被 no-T2 伪负类污染的历史风险**。V4 的 scar 与 pure-edema scientific brief 明确要求两者独立处理，不能拿 scar 的机制直接迁移到 edema，也不能用 edema-zone 冒充 official pure edema。fileciteturn12file0

还需要特别强调 MoSAIC 的边界。V4 已经把 MoSAIC 的 clean evidence、M0/M1 的 clean OOF、以及 M2-M10 的 full-data mechanism probe 做了 population gate 绑定；可核验结论是：**MoSAIC clean OOF 不构成比 nnU-Net 更强的公平基线**，scar 只有 $$0.3782$$、pure edema 只有 $$0.0528$$，并且 pure edema 有大量 empty prediction。V4 同时警告，M2-M10 是训练过病例上的 recipe decomposition，不得当成 fair validation superiority。fileciteturn12file0 这里还有一处需要做版本卫生：V4 第 13 页的 prose 还残留一句 “M2-M10 recipe decomposition is only six cases”，但同一证据包之前已经写明 “MoSAIC V4 population gate: PASS；M2-M10 病例数 80”，按项目自己的规则，应以 population-audited 数字 $$80$$ 为准，把“六例”视为过期自然语言。fileciteturn12file0 这件事很关键，因为它再次说明：**我不能把 V4 PDF prose 当作绝对真理，只能把它当导读**。

基于这些本地证据，我对“什么算真实可继承经验”给出一张收束表，便于后续 Codex 无歧义执行。下表不是泛泛总结，而是后续实现的强约束。

| 历史来源 | 允许保留的思想 | 在新设计中的重新实现方式 | 必须避免的旧错误 |
|---|---|---|---|
| Batch7 | 病种专属 proposal/candidate supervision；case-wise help/harm | scar 与 edema 各自独立 proposal，且 proposal 直接进入 refiner 与 final logits | router/dictionary/prototype 只参与 loss 或可视化而不进入 final output；refiner-minus-proposal 近零 |
| MMRD | reliable-label / no-T2 hygiene；modality dropout 作为训练策略 | edema loss 只在 $$a_{T2}=1$$ 时激活；缺模态按 availability 融合，不把 no-T2 当 edema negative | simple residual pathology head；把 hygiene 误说成架构成功 |
| Cascade | exact fallback 思维、ROI coverage、安全审计、remote-FP 审计 | proposal 覆盖率、remote-FP、help/harm 进入晋级门；fallback 只能回落到本模型 global head | 弱 bounded correction 围绕 anchor 逐体素小修小补；prototype 控制不隔离 |
| ARC | 单共享主体、显式 availability/gate、no-T2 exact zero、输入合同 | 单 backbone + availability-aware fusion + edema no-T2 hard zero | 随机/不完整 decoder 恢复；“实现了模块”就当作“恢复了能力” |
| PRISM 反例 | decoder preservation 与 final-output tracing 规则 | 从第一天就要求 refiner 与 proposal 必须进入 final logits；freeze/trainable 清单显式写死 | decoder reset 后还宣称继承强基线；靠 threshold/校准解释系统性失败 |

这张表背后的约束，与 V4 component survival report 完全一致：**可以直接复用的是数据规则与安全规则，不能直接复用的是具体失败实现**。fileciteturn12file0

## 视觉病例归因

我实际逐页阅读了独立 atlas 的 **全部 40 页**，而不仅是主报告里的 contact sheet；V4 也明确说明 atlas 单独保存、共有 40 页，主 PDF 里的 contact sheet 只用于证明未裁切，不能替代人工视觉判断。fileciteturn11file0 fileciteturn12file0 需要先说明一个客观限制：用户提出“CenterB 至少 8 例、CenterC 至少 8 例”，但 atlas 冻结页中可见的 CenterC 只包含 Case3010、3036、3012、3017、3006 共 **5 例**；因此我阅读了 **全部 5 例 CenterC**，同时补足了 **全部 12 例 CenterB** 与若干其他中心病例。这个限制来自 atlas 构成，而不是我跳读。fileciteturn11file0

整体视觉结论非常一致。第一，**alignment 不是多数病例的第一失败源**。绝大多数失败更像是“病种形成错误”与“边界/连通域错误”，而不是粗暴的 slice mis-registration：同一 myocardial ring 的位置通常是对的，错的是 scar 与 edema 的 class composition、局部薄层边界、以及 remote extracardiac bright region 的误检。第二，**nnU-Net 与 MoSAIC 的互补是真实但很窄的**。nnU-Net 在 scar 的边界与小弧段保留上经常更稳，MoSAIC 则更容易给出大面积 edema-like fill-in；但这种互补更像“同一病灶的两种偏差”，不是天然足够形成 $$+0.1$$ 的 case selector 上限。V4 的 large-gain error budget 之所以把 case-oracle bound 压到 scar $$0.0220$$、pure edema $$0.0023$$，与 atlas 中肉眼可见的“互补窄、重叠大”是吻合的。fileciteturn11file0 fileciteturn12file0

下面给出 24 例重点归因案例。它们覆盖了全部 5 例 CenterC、12 例 CenterB，以及其他中心的 scar-only/no-T2 病例；同时覆盖了 small scar、明显 pure-edema、nnU-Net 与 MoSAIC 分歧、remote FP、边界欠分割、多连通域漏检等子群。表中“视觉/定量”一栏里，若写“视觉”，表示判断来自 atlas 直接目视；若写“视觉+定量”，表示该视觉模式与 V4 failure taxonomy、help/harm 或 error budget 叙述一致。

| Case ID | 中心与模态 | 主要失败病种 | 主要失败形态 | nnU-Net 与 MoSAIC 是否互补 | alignment 可能性 | 可能有效的新机制 | 证据性质 |
|---|---|---|---|---|---|---|---|
| 3010 | CenterC，T2-present | pure edema | MoSAIC 更大范围 edema fill-in，伴心外 remote FP 倾向；nnU-Net scar 更克制 | 有，但窄 | 低 | edema 专属 T2 proposal + safe-negative remote FP | 视觉 |
| 3036 | CenterC，T2-present | pure edema | diffuse edema 边界宽、MoSAIC 过平滑；nnU-Net 欠召回 | 有 | 低 | edema 大 ROI refiner + boundary uncertainty loss | 视觉 |
| 3012 | CenterC，T2-present | scar | 小弧段 scar 欠分割，边界偏薄 | 中等 | 低 | scar small-lesion proposal + surface loss | 视觉 |
| 3017 | CenterC，T2-present | scar+edema 组合 | class composition 偏差，scar/edema 边界互相吞并 | 有 | 中 | anatomy-conditioned dual pathology heads | 视觉 |
| 3006 | CenterC，likely no-T2/weak T2 | scar | 小病灶、多连通域不稳 | 中等 | 低 | component-aware scar supervision | 视觉 |
| 2017 | CenterB，T2-present | pure edema | myocardium 内 diffuse edema 明显，nnU-Net 边界薄，MoSAIC 更厚但更糊 | 有 | 低 | edema 专属 proposal + one large-ROI refiner | 视觉 |
| 2004 | CenterB，T2-present | pure edema | broad edema band，MoSAIC 接近填满心肌环 | 有但偏粗糙 | 低 | edema boundary-aware refinement | 视觉 |
| 2023 | CenterB，T2-present | scar | 多连通小 scar，部分组件漏掉 | 中等 | 低 | lesion-level MIL + connected-component weighting | 视觉 |
| 2050 | CenterB，T2-present | pure edema | edema 边界模糊，scar/edema 互相侵占 | 有 | 低 | scar-priority official decode + dual proposal | 视觉 |
| 2019 | CenterB，T2-present | scar | 远端 FP 明显，尤其 MoSAIC 类输出更容易跑到心外亮区 | 互补有限 | 低 | safe hard-negative for extracardiac bright regions | 视觉 |
| 2042 | CenterB，T2-present | scar | 边界偏移，薄层 scar 断裂 | 中等 | 低 | high-res scar refiner | 视觉 |
| 2025 | CenterB，T2-present | pure edema | diffuse edema 欠/过分割并存，局部疑似轻微对位误差 | 有 | 中 | edema ROI refiner，alignment 只作可选诊断 | 视觉 |
| 2035 | CenterB，T2-present | scar | 明显小病灶漏检 | 互补窄 | 低 | proposal recall gate + lesion-center supervision | 视觉 |
| 2014 | CenterB，T2-present | scar | 多组件边缘被吃掉 | 中等 | 低 | component-aware scar loss | 视觉 |
| 2012 | CenterB，T2-present | pure edema | 心肌环内过平滑扩张，边界不可信 | 有 | 低 | edema uncertainty-aware boundary loss | 视觉 |
| 2009 | CenterB，T2-present | scar | 小弧段/点状 scar 欠召回 | 中等 | 低 | small-lesion oversampling | 视觉 |
| 2043 | CenterB，T2-present | scar+edema | 病种组合关系错误，scar 被 edema 化 | 有 | 低 | separate official conflict mapping | 视觉 |
| 1054 | CenterA/other，no-T2 | scar | 心外 remote FP 与血池混淆 | 互补很小 | 低 | blood-pool / remote FP hard negatives | 视觉 |
| 1011 | no-T2 | scar | 小灶 scar 召回差 | 中等 | 低 | scar component proposal | 视觉 |
| 1022 | no-T2 | scar | 小病灶边界薄、局部断裂 | 中等 | 低 | scar ROI refiner | 视觉 |
| 1014 | no-T2 | scar | 血池邻近 FP 与边界欠分割同时存在 | 互补有限 | 低 | anatomy distance channels + hard negatives | 视觉 |
| 5005 | no-T2 | scar | 多连通域漏检，次级小组件易丢 | 中等 | 低 | lesion-level MIL | 视觉 |
| 6004 | no-T2 | scar | 小弧段+远端 FP 混合 | 中等 | 低 | proposal + remote-FP gate | 视觉 |
| 7002 | no-T2 | scar | 细薄 scar 与正常心肌混淆 | 互补有限 | 低 | high-res local texture refinement | 视觉 |

上述 24 例汇聚出的模式可以压缩成五个“真正值得建模”的 failure pool。**其一，小病灶 scar**：这不是单纯阈值问题，而是 lesion formation 问题。小弧段、点状、薄层 scar 在 shared global head 上天然被 class imbalance 淹掉，需要明确的 lesion proposal 与 component-aware 监督。**其二，多连通域 scar**：现有模型容易保住主组件、丢掉次级组件，说明需要组件级召回约束，而不是只看体素平均 Dice。**其三，remote FP**：多见于心外亮区与血池邻近区，这要求 safe hard-negative 机制，而且 scar 与 edema 的 hard-negative 定义不能共用。**其四，edema 的 diffuse boundary uncertainty**：这不是 scar 那样的“小目标检测”，更像 T2 驱动的大尺度模糊区域形成，需要大 ROI refinement 与边界不确定性损失。**其五，class composition 错误**：几个典型病例里，同一病灶区域会在不同模型中被“scar 化”“edema 化”或“合并成 lesion union”，这正是为什么 scar 与 pure edema 必须有不同 proposal、不同 refiner、不同阈值与不同官方映射。fileciteturn11file0 fileciteturn12file0

视觉 atlas 还给出一个对新设计很关键、但容易被忽视的事实：**no-T2 safety 必须是硬规则，不是 soft regularization**。在若干 no-T2 scar-only atlas 页中，历史 MoSAIC 风格输出会出现明显的 edema-like cyan 区域；这与 V4 中“no-T2 不能作为 pure-edema negative，也不能放任 edema 路径自由外推”的规则是完全一致的。换言之，edema 路径在 no-T2 inference 上必须是 **hard zero or hard off**，否则你永远分不清它是在做 pathology transfer，还是在做 hallucination。fileciteturn11file0 fileciteturn12file0

## 针对性文献综述与候选机制淘汰

把本地失败图谱与一手文献对齐后，能真正进入候选池的机制并不多。**第一类**是“缺模态鲁棒的共享主干融合”，核心问题是如何在训练分布本来就不均衡缺模态的情况下，避免某个模态把别的模态训练死。HeMIS 的经典结论是：把每个模态先映射到共同隐空间，再对可用模态做统计融合，可以在缺模态场景中稳健退化；PASSION 则进一步把“不完整多模态且缺失率不均衡”当作核心问题，提出 preference-aware self-distillation 与 task-wise / gradient-wise balancing，并且作者给出了官方代码；MyoPS-Net 则证明 flexible combination of multi-sequence CMR 在心肌病灶任务中是有效方向，但其原生设定是五序列完整/半完整组合，不直接等于 CARE 的真实 missing-not-at-random 机制。citeturn31search0turn31search12turn31search3turn33search1turn32search3turn26search8

**第二类**是“anatomy–pathology 交互”。U-MyoPS 的价值不在于我今天要重做注册，而在于它清楚利用了 myocardium prior，把 pathology 限定在 anatomically plausible space 中；APEx 则更明确地把 anatomy-guided pathology exchange 建模成 pathology decoder 对 anatomy query 的利用。对 CARE 来说，V4 已经判定 alignment 不是主瓶颈，但 anatomy support 是真需求，因此最合理的借鉴不是“再加一个完整 registration backbone”，而是**在单一主干内部做轻量 anatomy-conditioned pathology exchange**。citeturn33search0turn28search2turn26search15turn32search2

**第三类**是“scar 小病灶与多连通域监督”。这部分对我最有启发的，不是任何一个心脏论文单独宣称“我们很强”，而是跨数据集的两个思路高度一致。一个是 Lesion-Harvester / ULDor 这类 proposal + selective classifier + hard-negative suppression 路线，它们的共识是：要先拿高召回 proposal，再用更强先验做 FP reduction，而不是试图让一个体素损失一口气同时解决召回与 FP。citeturn29search0turn29search1turn29search4turn29search20 另一个是 2026 年的 CATMIL，它把 connected-component 自适应重加权与 lesion-level MIL 合并到统一目标中，直接针对 small lesion recall 和 false-negative 控制。虽然它不是心脏任务，但它给出的正是 scar 在 CARE 中缺失的那类因果监督：**让每个 lesion instance 都“必须被看到”**。citeturn30search0turn30search1

相反，有三类路线我明确淘汰。**其一，多完整 backbone / 重型 ensemble 作为方法主体。** CARE 本地证据已经把这条路基本堵死：历史实现没有任何证据支持“再堆一套完整 U-Net、再并一套 foundation model”能够带来因果上可解释的长进，相反会进一步掩盖 error attribution；项目约束也明确限制为一个完整 backbone。fileciteturn12file0 **其二，以 nnU-Net 或 MoSAIC 预测为唯一主体的弱 residual correction。** V4 的 scar / edema case-oracle 上界已经说明：如果新模型只是围绕现有 anchor 做 bounded correction，那么能吃到的增益只有 modest range，不具备 $$\approx 0.1$$ 的机制上限。fileciteturn12file0 **其三，把 alignment 升级成主方法。** CAA-Seg 在新数据集上确实展示了 selective slice alignment + hierarchical alignment network 的价值，而且开源代码是 MIT；但 V4 本地 alignment 结论已经把它定性为 optional diagnostic/safety module，而非 primary Deep Research mechanism，因此它最多只能成为一个 A8 级别、默认关闭的轻量附加模块。citeturn26search6turn26search10turn32search1 fileciteturn12file0

基于上述证据，三类候选机制可以被压缩成下面的比较。

| 候选机制 | 预期解决的真实问题 | 与 CARE 本地失败匹配度 | 复杂度 | 是否保留 |
|---|---|---|---|---|
| 多 backbone / ensemble 主体 | 试图覆盖所有模态与所有病种 | 低；会遮蔽因果归因，且与 V4 结论冲突 | 高 | 淘汰 |
| anchor residual correction | 继续修补 nnU-Net / MoSAIC 输出 | 中低；与 small lesion / diffuse edema formation 不匹配 | 低 | 淘汰 |
| 单 backbone + 病种专属 proposal/refinement + anatomy exchange | scar 的小灶/多组件/FP、edema 的 T2 依赖与 diffuse boundary | 高 | 中 | 保留为首选 |
| 单 backbone + 病种专属 heads，但不做 ROI refinement | 追求更稳的 moderate gain | 中 | 低 | 保留为保守备选 |
| alignment-aware 轻模块 | 只处理明显失配子群 | 低到中 | 低 | 仅作默认关闭的未来附加项 |

最后还要对几篇指定论文做明确判词。**MyoPS-Net** 借的是 flexible modality combination 思想，不借其五序列结构。**U-MyoPS** 借的是 myocardium prior，不借其多 encoder + registration head 重结构。**MS-CaRe-CNN** 借的是 anatomy-first 再 pathology-refine 的 coarse-to-fine 思想，不借其双阶段完整 cascade 与 5-fold ensemble 主体。**APEx** 借的是 anatomy-to-pathology exchange，不借其 DETR 风格重型 query transformer。**PASSION** 借的是 imbalance-aware 缺模态训练策略，不借其“插到任意 backbone 就会涨”的外部宣称。**I-MMSeg** 借的是 modality-specific intensity prior 这个方向意识，不借其 CLIP + LLM text prompt 依赖，因为那既引入额外不可控先验，也没有本地因果证据证明它能直接解决 CARE scar 小灶与 edema hygiene 的核心矛盾。citeturn32search3turn33search0turn27search1turn26search15turn31search3turn34search0

## 首选架构与训练合同

在所有候选里，我只推荐一个首选完整架构，并给出一个真正更保守的备选。先给结论：**如果项目必须选一个“最值得实现”的下一代单-backbone 研究原型，我推荐首选架构为 CARE-MyoPath-PR；如果项目只想做最小风险验证，我推荐备选 CARE-MyoPath-Lite。** 但再次强调，这个“推荐”不等于高增益 GO；它只是“在 NO-GO 前提下，最值得实施的合同”。fileciteturn12file0

**首选架构名称：CARE-MyoPath-PR。** 它的一句话科学主张是：**在保留完整 nnU-Net 级 decoder 能力的前提下，用一个共享 backbone 产生全局 anatomy/context，再用 scar 与 edema 两条完全独立的 proposal–refinement 路径处理小病灶、多连通域、remote FP 与 T2-dependent diffuse boundary，从而引入现有 baseline 没有的 lesion formation authority。**

### 首选架构的精确合同

**输入模态与固定顺序**：固定输入顺序为 $$[I_{\text{LGE}}, I_{\text{T2}}, I_{\text{C0}}]$$，每个模态一通道，缺失模态输入全零张量；同时提供 availability 向量 $$a=[a_{\text{LGE}},a_{\text{T2}},a_{\text{C0}}]\in\{0,1\}^3$$。LGE 必须存在；T2 和 C0 可缺失。对 no-T2 病例，edema 路径在 inference 与 loss 中都硬关闭。这个输入合同直接继承 ARC 的显式 gate 思想与 MMRD 的 no-T2 hygiene 规则。fileciteturn12file0

**预处理与 working space**：所有模态共同做几何对齐后的统一 resample 到 $$1.2\times1.2\times1.2\ \text{mm}^3$$ 物理空间，这是 MyoPS++ 公开论文里可核验且跨中心一致的 working resolution；随后基于身体前景做外接框裁切，再做固定尺寸 $$160\times160\times112$$ 的中心化 patch。空间增强对所有模态共享同一随机仿射参数，避免人为打散 already-usable correspondence；强度增强按模态独立施加，以保留 T2/LGE/C0 的 modality-private cue。citeturn39search4

**主 backbone 的精确选择**：一个完整 3D residual encoder–decoder U-Net，五个尺度，通道数依次为 $$[32,64,128,256,320]$$，分辨率依次为 $$1, \tfrac12, \tfrac14, \tfrac18, \tfrac1{16}$$；decoder 对应通道为 $$[256,128,64,32]$$。编码器和解码器都完整保留，不允许 encoder-only inheritance，更不允许 decoder reset。选择这个 backbone 不是因为它“最先进”，而是因为 V4 已经清楚证明：**完整 decoder 的保存与否，会决定是否还拥有强基线能力**。fileciteturn12file0

**模态 stem 结构**：每个模态先经过一个独立 stem：$$1\rightarrow16\rightarrow32$$ 通道的两层 $$3\times3\times3$$ 卷积块，每层都是 Conv–GroupNorm–LeakyReLU。Stem 不共享参数，目的是保留 modality-private 低层统计特征。缺失模态的 stem 仍执行前向，但其输出随后被 availability 掩码乘零。这个设计借鉴 HeMIS 与 MyoPS-Net 的“先做模态私有嵌入，再做共享融合”。citeturn31search0turn32search3

**共享融合公式**：在每个尺度 $$s$$，设三个 stem/encoder 特征为 $$h_{\text{LGE}}^{(s)},h_{\text{T2}}^{(s)},h_{\text{C0}}^{(s)}$$。用 availability-aware 统计融合：
$$
\mu^{(s)}=\frac{\sum_m a_m h_m^{(s)}}{\sum_m a_m+\epsilon},
\qquad
\sigma^{(s)}=\sqrt{\frac{\sum_m a_m \left(h_m^{(s)}-\mu^{(s)}\right)^2}{\sum_m a_m+\epsilon}+\epsilon}
$$
再定义 gated sum
$$
\alpha_m^{(s)}=\sigma\!\left(W_m^{(s)}\left[h_m^{(s)},a\right]\right),\qquad
g^{(s)}=\sum_m a_m \alpha_m^{(s)}\odot h_m^{(s)}.
$$
最终共享特征为
$$
f^{(s)}=\phi^{(s)}\!\left(\left[\mu^{(s)},\sigma^{(s)},g^{(s)},\text{broadcast}(a)\right]\right),
$$
其中 $$\phi^{(s)}$$ 是一个 $$1\times1\times1$$ 压缩卷积加残差块。这个公式同时保留了 HeMIS 的统计鲁棒性与 ARC/CARE 所要求的显式 availability contract。citeturn31search0turn31search12 fileciteturn12file0

**anatomy/context 的来源与权限**：共享 decoder 在 full-image 上同时输出 $$\hat y_{\text{MYO}},\hat y_{\text{LV}},\hat y_{\text{RV}},\hat y_{\text{scar-global}},\hat y_{\text{edema-global}}$$ 五组 logits。其中心肌与血池分支只提供 **soft support** 与 **distance-coordinate**，不直接包办 pathology。具体做法是从 $$\hat y_{\text{MYO}},\hat y_{\text{LV}},\hat y_{\text{RV}}$$ 生成三个 detached context 通道：soft-myo、distance-to-blood-pool、distance-to-myo-boundary，供 proposal/refiner 使用，但 anatomy 分支不会覆盖 pathology 最终判决。这样既利用 anatomy prior，又不让“解剖分割正确”误冒充“病灶分割成功”。这一点与 U-MyoPS / APEx 的可借鉴部分一致，也符合 V4 对 anatomy–pathology exchange 的约束。citeturn33search0turn26search15

**scar proposal**：输入是 $$\tfrac12$$ 与 $$\tfrac14$$ 尺度共享特征、LGE stem 高分辨率特征、三个 anatomy/context 通道与 availability。Proposal 头是四个残差卷积块，输出两个图：$$p_{\text{scar-mask}}$$ 与 $$p_{\text{scar-center}}$$。前者学习 scar candidate heatmap，后者学习 lesion-center heatmap。监督不是直接 GT mask，而是两级监督：其一，scar GT 经 $$2\ \text{mm}$$ 膨胀得到的 candidate coverage mask；其二，每个 scar connected component 的中心球核监督。这样做的目的，是让 proposal 首先负责“看见每个 lesion instance”，而不是被迫在 proposal 阶段就把边界抠准。Batch7 的可保留经验正是 pathology-specific candidate supervision，但必须以不同实现重做。fileciteturn12file0

**scar refinement**：对通过 proposal 阈值的连通组件，提取最多 $$K=6$$ 个 ROI；每个 ROI 的物理外扩边界固定为各向 $$6\ \text{mm}$$，重采样到 $$48\times48\times16$$。Refiner 的输入包括：LGE、T2、C0 三个原始 patch（缺失模态仍以零输入）、proposal mask、soft-myo、distance-to-blood-pool、以及裁剪后的高分辨率共享特征。Refiner 不是第二个完整 U-Net，而是一个三层轻量局部网络，通道为 $$[48,96,96]$$，输出 scar residual logit patch 与 boundary confidence patch。Refiner 必须直接回贴到 full-image final logits；如果它没有进入 final output，这个实现自动判为 known-bad。V4 对 Batch7 与 PRISM 的最大教训就是：**proposal/refiner 必须对 final mask 有直接、可度量、可归因的 authority**。fileciteturn12file0

**edema proposal**：edema 不是 scar 那样的“小组件检测”，所以 proposal 形式不同。输入是 $$\tfrac12$$ 尺度共享特征、T2 stem 高分辨率特征、soft-myo 与 distance-to-myo-boundary；proposal 输出两个图：$$p_{\text{edema-band}}$$ 与 $$p_{\text{edema-mask}}$$。前者学习“心肌环上哪些扇区/带状区域值得细化”，后者学习粗糙 edema 区域。只有当 $$a_{\text{T2}}=1$$ 时，edema proposal 才计算损失与产生有效候选；当 $$a_{\text{T2}}=0$$ 时，proposal 头前向可执行但 logits 被硬置为 $$-\infty$$，不会形成任何 edema 正预测。这样既满足 hygiene，又防止 no-T2 hallucination。fileciteturn12file0

**edema refinement**：每个病例最多取两个 edema ROI，不按小组件切碎，而是对 proposal band 的并集求外接框，再各向扩张 $$10\ \text{mm}$$，重采样到 $$96\times96\times24$$。选择大 ROI，是因为 atlas 显示 edema 常见失败是 diffuse band boundary，而不是“多颗小结节”。Refiner 输入与 scar 类似，但额外加入 $$\hat y_{\text{scar-global}}$$ 的 detached soft channel，用于避免 scar/edema 边界互吞。输出是 edema residual logit patch。no-T2 下整个 refiner 完全关闭，不做伪推断。fileciteturn11file0 fileciteturn12file0

**prototype 是否使用**：**不使用**。原因非常直接：V4 已经把 prototype 的历史负结论降级为“控制不隔离，不能下定论”，但这不代表我们现在应该把 prototype 重新放回主线。既然当前任务是给出最稳妥、最可归因的单-backbone 合同，那么 prototype 是应该被刻意排除的高噪声变量。fileciteturn12file0

**safe hard-negative 的安全定义**：scar 与 edema 分开定义。Scar 的 hard-negative 只允许来自三类区域：$$1$$）LV/RV blood-pool 邻近带；$$2$$）心肌外 $$>5\ \text{mm}$$ 的 extracardiac bright region；$$3$$）T2-present 可靠病例中、远离 scar GT 与 edema GT 各自膨胀带的正常心肌。Edema 的 hard-negative 更保守，只允许来自 $$a_{\text{T2}}=1$$ 的血池邻近带与心肌外远端亮区，**不把整片 no-T2 myocardium 当 edema negative，也不把靠近 scar 的模糊带强行标为 edema negative**。这是 MMRD hygiene 与 atlas 视觉结论共同决定的。fileciteturn11file0 fileciteturn12file0

**final logits 组成**：scar 与 edema 各自都由 global、proposal、refiner 三部分组成：
$$
z_{\text{scar}}=\hat y_{\text{scar-global}}+0.5\,p_{\text{scar-mask}}+M_{\text{scar-ROI}}\odot r_{\text{scar}},
$$
$$
z_{\text{edema}}=\hat y_{\text{edema-global}}+0.5\,p_{\text{edema-mask}}+M_{\text{edema-ROI}}\odot r_{\text{edema}},
$$
其中 $$M_{\text{ROI}}$$ 是 accepted ROI 的回贴支持图，保证 refiner 只在被 proposal 指定的区域行使更强 authority。这一公式故意让 proposal 也进入 final logits，防止 proposal 变成“只影响 loss、不影响输出”的伪模块。

**官方标签映射**：先独立得到二值 scar mask 与 edema mask，再按官方 scar-priority 规则映射：若 scar 为正，则输出 label $$5$$；若 scar 为负且 edema 为正，则输出 label $$4$$；其余为非病灶类别。注意，训练阶段允许 edema refiner 看到 detached scar-global context，但**最终官方映射永远由 scar 优先**，不允许相互覆盖成含混的 edema-zone。fileciteturn12file0

**fallback 规则**：存在 fallback，但只能回退到**本模型自己的 global head**，绝不能回退到 nnU-Net/MoSAIC anchor。本模型若某病种 proposal 未产生 accepted ROI，则该病种 final logits 退化为 global + 0.5 proposal coarse logits；no-T2 edema 则直接为 hard zero，不存在“自由 hallucination fallback”。这保证了安全性，但不会导致“模型几乎逐体素等同 anchor”的 known-bad。fileciteturn12file0

**后处理精确规则**：scar 采用阈值 $$t_{\text{scar}}$$ 网格内选，候选阈值集合固定为 $$\{0.30,0.35,\dots,0.70\}$$；保留所有与 soft-myo 重叠比例 $$\ge 0.70$$ 且体积 $$\ge 6$$ voxel 的连通域，不做 largest-component-only。edema 阈值集合相同，但只在 $$a_{\text{T2}}=1$$ 时启用；之后做一次半径 $$1$$ voxel 的 closing，并保留与 soft-myo 重叠比例 $$\ge 0.80$$ 且体积 $$\ge 12$$ voxel 的连通域。所有阈值只允许在 inner-select 上按病种独立选择，禁止 outer 与 official validation 参与。这个后处理刻意保持轻量，因为本设计的预期增益主来源不是后处理。fileciteturn12file0

**参数量与算力预算**：以一个标准 3D 五尺度 residual U-Net 为参照，主 backbone 参数量约作为 $$1.00\times$$；三个 modality stem、两个 proposal head、两个轻 refiner、anatomy/context heads 总计新增参数控制在 backbone 的约 $$28\%\sim32\%$$；推理 FLOPs 约为 backbone 的 $$1.30\times\sim1.40\times$$；显存开销主要来自 ROI refinement 的缓存，但由于 scar ROI 最多 $$6$$ 个、edema ROI 最多 $$2$$ 个，整体仍满足“一个完整 backbone + 轻量专属模块”的项目硬约束。这个预算不是实际测量值，而是按上述通道合同得到的工程估算。

### 训练与验证闭环

训练协议必须从第一天就防止 ARC/PRISM 式“阶段名称改变，但 trainable parameters 和 loss 没有变”。我建议的严格闭环是如下固定方案，而不是“视情况调整”。

**数据划分**：使用 patient-level、center-stratified、T2-availability-aware 的固定 5-fold 家族。由于历史 fold0 outer 已被访问，且项目明确禁止再用于模型/阈值/后处理选择，因此新模型开发时固定采用：fold1 为 untouched outer；fold2+fold3 为 actual-train；fold4 为 inner-select；fold0 永久封存，不进入任何开发选择。这个协议牺牲了些许样本效率，但换来边界清晰。fileciteturn12file0

**采样规则**：每个训练 step 采两个 patch，batch size 物理为 $$2$$，gradient accumulation 为 $$4$$，等效 batch 为 $$8$$。其中 $$50\%$$ step 强制包含 T2-present 病例；scar 小病灶 oversampling 占 $$30\%$$ step，定义为 scar 连通域体积 $$\le 150$$ voxel 或最大物理直径 $$\le 8\ \text{mm}$$；edema boundary oversampling 占 $$30\%$$ step，中心落在 edema GT 边界带；safe-negative patch 占 $$20\%$$ step，但只在第三阶段开启。no-T2 病例只参与 scar 与 anatomy route，不进入 edema 损失。这个采样比重直接服务于 atlas 中最主要的 failure pool。fileciteturn11file0

**优化器与日程**：统一使用 AdamW，主干初始学习率 $$3\times10^{-4}$$，预训练继承的 encoder/decoder 在 warm start 阶段用较低学习率 $$1\times10^{-4}$$；weight decay 为 $$1\times10^{-4}$$；梯度裁剪 L2 norm 为 $$12$$。总步数固定为四阶段共 $$52{,}000$$ 步：阶段一 $$12{,}000$$ 步，阶段二 $$16{,}000$$ 步，阶段三 $$14{,}000$$ 步，阶段四 $$10{,}000$$ 步。学习率在每阶段内部做 cosine decay，阶段切换时重新设定 base lr，不沿用上一阶段尾值。

**阶段一**：激活模块为 modality stem、shared fusion、完整 backbone、global scar head、global edema head、anatomy heads；proposal/refiner 全部冻结。激活损失为 anatomy 多类 DiceCE、global scar DiceCE、global edema DiceCE，其中 edema loss 仍乘以 $$\mathbf 1[a_{\text{T2}}=1]$$。目的只有一个：在不破坏完整 decoder 的前提下，把 availability-aware 融合和双病种 global head 接到一个稳定 backbone 上。若阶段一结束时 inner-select scar Dice 低于同 split D0 anchor 的 $$-0.015$$，或 T2-present edema Dice 低于 D0 anchor 的 $$-0.020$$，则直接停线，不进入阶段二。

**阶段二**：解冻 scar/edema proposal 头，继续训练 backbone，但 refiner 仍冻结。新增损失是 proposal loss。Scar proposal loss 定义为
$$
\mathcal L_{\text{prop-s}}=
\mathcal L_{\text{DiceCE}}\!\left(p_{\text{scar-mask}},\tilde y_{\text{scar}}\right)
+\lambda_{\text{MIL-s}}\mathcal L_{\text{MIL}}\!\left(p_{\text{scar-center}},\mathcal C_{\text{scar}}\right)
+\lambda_{\text{CAT-s}}\mathcal L_{\text{CAT}}\!\left(p_{\text{scar-mask}},y_{\text{scar}}\right),
$$
其中 $$\tilde y_{\text{scar}}$$ 是膨胀后的 candidate mask，$$\mathcal C_{\text{scar}}$$ 是 lesion component 集合，$$\mathcal L_{\text{CAT}}$$ 是 component-adaptive Tversky。Edema proposal loss 定义为
$$
\mathcal L_{\text{prop-e}}=
\mathbf 1[a_{\text{T2}}=1]\Big(
\mathcal L_{\text{DiceCE}}\!\left(p_{\text{edema-mask}},y_{\text{edema}}\right)
+\lambda_{\text{band}}\mathcal L_{\text{DiceCE}}\!\left(p_{\text{edema-band}},b_{\text{edema}}\right)
\Big).
$$
阶段二的晋级门不是平均 Dice，而是：scar proposal 的 lesion-wise recall $$\ge 0.85$$、GT lesion coverage $$\ge 0.90$$、safe-negative FP 率不高于 global baseline 的 $$1.10\times$$；edema proposal 的 ROI coverage $$\ge 0.90$$、T2-present recall 不低于阶段一、no-T2 edema exact zero 持续成立。任何一项不达标，直接停线或回滚 proposal，而不是寄希望于 refiner 补回来。CATMIL 与 lesion-harvester 给出的正是这种“先把 lesion 看见”的原则。citeturn30search1turn29search0

**阶段三**：开启 scar refiner 与 edema refiner，同时保持 proposal 继续训练。Scar refiner 损失定义为
$$
\mathcal L_{\text{ref-s}}=
\mathcal L_{\text{DiceCE}}(r_{\text{scar}},y_{\text{scar}}^{\text{ROI}})
+\lambda_{\text{surf-s}}\mathcal L_{\text{surf}}(r_{\text{scar}},y_{\text{scar}}^{\text{ROI}})
+\lambda_{\text{cnt-s}}\mathcal L_{\text{cnt}}(r_{\text{scar}},y_{\text{scar}}^{\text{ROI}}),
$$
其中 surface loss 直接对应 HD95/边界，count consistency loss 约束 refiner 不要把多组件压成单组件。Edema refiner 损失定义为
$$
\mathcal L_{\text{ref-e}}=
\mathbf 1[a_{\text{T2}}=1]\Big(
\mathcal L_{\text{DiceCE}}(r_{\text{edema}},y_{\text{edema}}^{\text{ROI}})
+\lambda_{\text{surf-e}}\mathcal L_{\text{surf}}(r_{\text{edema}},y_{\text{edema}}^{\text{ROI}})
+\lambda_{\text{bdry}}\mathcal L_{\text{unc-bdry}}(r_{\text{edema}},y_{\text{edema}}^{\text{ROI}})
\Big).
$$
如果阶段三结束时 scar 的 refiner-minus-proposal Dice 增量小于 $$0.015$$，或 HD95 没有下降至少 $$2\ \text{mm}$$；或者 edema 的 refiner-minus-proposal T2-present Dice 小于 $$0.020$$ 且 boundary error/HD95 无改善，则 refiner 分支被判无效，不进入阶段四。

**阶段四**：启用 safe hard-negative queue，并把其损失以低权重加入：
$$
\mathcal L_{\text{hn-s}}=\text{BCE}_{\text{top-k}}(z_{\text{scar}},\mathcal N_{\text{scar}}),\qquad
\mathcal L_{\text{hn-e}}=\mathbf 1[a_{\text{T2}}=1]\text{BCE}_{\text{top-k}}(z_{\text{edema}},\mathcal N_{\text{edema}}).
$$
Top-k 固定为每 patch 最高分的 $$k=128$$ 个 mined negatives。阶段四的通过标准是：scar remote-FP 至少相对阶段三下降 $$20\%$$，且 scar Dice 下降不超过 $$0.005$$；edema no-T2 safety 继续维持 exact zero，T2-present Dice 下降不超过 $$0.005$$。如果 hard-negative 伤害超过收益，则该组件被永久移除，不允许“为了完整模型而硬保留”。

**checkpoint 选择**：scar 与 edema 采用分病种复合指标，而不是平均 Dice。Scar 复合选择指标定义为
$$
S_{\text{scar}}=0.45\,\text{Dice}-0.20\,\frac{\text{HD95}}{H_0}+0.20\,\text{LesionRecall}-0.10\,\text{RemoteFPRate}-0.05\,\text{HarmRate},
$$
edema 复合选择指标定义为
$$
S_{\text{edema}}=0.45\,\text{Dice}_{\text{T2-present}}
-0.20\,\frac{\text{HD95}}{H_0}
+0.15\,\text{Recall}
+0.10\,\text{CenterB/CMean}
-0.05\,\text{BoundaryError}
-0.05\,\text{HarmRate}.
$$
最终 checkpoint 只能在 fold4 inner-select 上挑选，阈值网格也只能在 fold4 上搜；fold1 outer 和 official validation 仅做只读汇报，绝不参与选择。fileciteturn12file0

### 最小因果消融矩阵与不可留白合同

按照用户要求，我不设计几十个散乱 ablation，只保留最小但有因果解释力的矩阵。其顺序固定如下：

| 版本 | 相对前一步新增 | 主要检验病种 | 继续门 | 失败解释 |
|---|---|---|---|---|
| A0 | 仅完整 backbone baseline | scar + edema | 复现 D0 同 split 非退化 | 若退化，说明融合/初始化破坏 backbone，本线终止 |
| A1 | + reliable-label / T2-conditioned supervision | edema | no-T2 edema exact zero，T2-present edema 不退化 | 若失败，说明 hygiene 接线错误 |
| A2 | + pathology-specific scar/edema global heads | 二者 | 任一病种至少获非退化增益 | 若失败，说明病种分头没有真实 authority |
| A3 | + proposal mechanism | 先 scar，后 edema | scar lesion recall、edema ROI coverage 达标 | 若失败，proposal 无效，不能进 refiner |
| A4 | + pathology-specific refinement | scar 与 edema 分开 | refiner-minus-proposal 达最低门 | 若失败，删除 refiner |
| A5 | + safe hard-negative | 先 scar，再 edema | remote FP 改善且不明显伤害 Dice | 若失败，删除 HN |
| A6 | + anatomy/pathology exchange | 二者 | HD95 或 boundary 有额外改善 | 若失败，删除 exchange |
| A7 | 完整首选模型 | 二者 | 二病种均优于 A4/A5，且 harm 可控 | 若失败，不做 full-data train |

每个组件还必须有独立“科学假设—输入张量—输出张量—是否进入 final logits—直接 loss—预计改善病种—最低 useful effect—retain/remove 规则”合同。这里不再展开成 20 张表，而给出核心条目：

| 组件 | 科学假设 | 输入张量 | 输出张量 | enters final logits | 最低 useful effect | remove 规则 |
|---|---|---|---|---|---|---|
| availability-aware fusion | 缺模态统计融合比简单拼接更稳 | 三模态 stem + $$a$$ | 各尺度共享特征 $$f^{(s)}$$ | 是，经 backbone | A0 不退化 | 任何一病种明显退化则回滚 |
| scar proposal | 小灶/多组件必须先被“看见” | $$f^{(1/2)},f^{(1/4)}$$ + LGE + anatomy | $$p_{\text{scar-mask}},p_{\text{scar-center}}$$ | 是 | lesion recall $$\ge0.85$$ | 不达标则不进 refiner |
| scar refiner | 局部高分辨率能修复边界与次级组件 | ROI raw + cropped features | $$r_{\text{scar}}$$ | 是 | refiner-minus-proposal $$\ge0.015$$ | 未达标删除 |
| edema proposal | edema 需要 T2-driven band detection | $$f^{(1/2)}$$ + T2 + anatomy | $$p_{\text{edema-band}},p_{\text{edema-mask}}$$ | 是 | ROI coverage $$\ge0.90$$ | 未达标删除 |
| edema refiner | diffuse edema 需要大 ROI 边界修正 | T2-centered large ROI | $$r_{\text{edema}}$$ | 是 | Dice $$\ge0.020$$ 或 HD95 明显改善 | 未达标删除 |
| safe hard-negative | remote FP/blood-pool FP 需要显式惩罚 | mined negatives | top-k negative loss | 间接，是 via $$z$$ | remote FP $$-20\%$$ | 伤害 Dice 即删 |
| anatomy exchange | 解剖支持能减少 class confusion | anatomy context + pathology features | exchanged features | 是 | HD95 / boundary 改善 | 无改善即删 |

接下来是**“从研究设计到 Codex 实现的不可留白合同”**。后续 Codex prompt 必须冻结以下字段，任何一项空白都视为 known-bad：模型类名、模块拓扑图、每层张量形状、初始化方式、预训练覆盖范围、trainable/frozen 参数名单、loss 公式与默认权重、固定 split 标识、训练步数、evaluation population、checkpoint 选择规则、threshold 网格、official decode 规则、输出路径模板、validator 语义、stop/continue 规则。与此同时，known-bad 至少必须拒绝以下 20 类错误：只继承 encoder 却声称保留强基线；proposal 未进入 refiner；refiner 未进入 final logits；scar/edema 共用同一小头；no-T2 进入 edema negative；prototype control 与 candidate 输入相同；模块只有梯度没有 final-label effect；short smoke 冒充正式训练；outer 用于阈值或 checkpoint 选择；full-data trained-on-case 结果冒充 validation；nnU-Net/MoSAIC 仍垄断 final output；fallback 让模型近似 identity；proposal recall 未达标仍启 refiner；component gain 不清楚仍进入下一阶段；validator 只查文件存在；pending/running job 包装成完成；scar 提升掩盖 edema 失败；edema safety 掩盖 T2-present 性能失败；architecture blank 留给 Codex 自行填充；后处理贡献包装成架构贡献。这里我没有“创造性补充”，而是把本轮研究的安全边界显式合同化。fileciteturn12file0

## 最终裁决、备选方案与参考阅读

### 最终 GO/NO-GO

我的最终裁决是：**NO_GO_FOR_HIGH_GAIN_MODEL**。这不是因为“首选架构毫无意义”，而是因为用户自己规定的 12 条 GO 条件里，至少有三条在当前证据下不能诚实满足。第一，虽然我能给出一个完整单-backbone 设计，也能明确继承 MMRD hygiene 与 ARC/Batch7 的两类历史经验，但**我无法证明它在 CARE official validation 上对 scar 与 pure edema 都存在“显著超过当前 nnU-Net”的可信路径**。CURRENT.md 与 V4 一起表明，official hosted validation 的 nnU-Net anchor 已经在 scar/edema 上约为 $$0.92/0.923$$，而现有 selector/correction 类路径的 case-oracle 上限只有 scar $$0.0220$$、pure edema $$0.0023$$。这意味着只要我们不引入一个已被证据支持的、新的、大幅度 lesion formation 机制，就不可能对 official metric 做出高增益承诺。citeturn12view0 fileciteturn12file0

第二，虽然 voxel oracle 对 scar 与 pure edema 都还显示出较大的理论剩余空间，但 V4 自己已经明确说明，这只能支持“外部新机制可能有空间”，**不能支持“现阶段已存在一条可兑现的机制路径”**。我给出的 CARE-MyoPath-PR 确实是最合理的新机制载体：它把 scar 的 lesion proposal / component-aware supervision、edema 的 T2-only large-ROI refinement、以及 anatomy-conditioned dual heads 放进了一个完整 decoder 主体里；但在没有任何 raw CSV/JSON 级别再审计、没有新 outer evidence、没有独立 HD95 绑定、也没有 MoSAIC vendor-recipe 可独立复核的情况下，我不能把它包装成“高概率超越 leaderboard 的长训主航道”。这会违反 V4 反复强调的“operational completion、scientific evidence、model success、submission readiness 必须分开”这一项目纪律。fileciteturn12file0 citeturn12view0

第三，当前可访问材料本身也有边界。我能够独立阅读的本地冻结材料包括：V4 主报告、DEEP_RESEARCH 约束包、独立 atlas PDF，以及当前公开 main 上的 CURRENT.md 与若干项目导读文件；但用户列出的那些 raw CSV/JSON 机器证据文件、以及本地 vendor-copy MoSAIC source/recipe，并未作为可访问文件完整暴露给我。因此，这份报告已经尽可能遵循“以机器证据为准”的原则，但**严格说，它仍然是一份“受限于已暴露证据包的深研设计裁决”，不是一次对所有底层 CSV/JSON 的逐项原件审计**。这不是鸡蛋里挑骨头，而是决定 GO/NO-GO 的关键因素之一。没有这层透明说明，任何高增益承诺都是不诚实的。

综合以上，若只问“现在该不该启动一轮以高增益为目标的长训练”，答案是否定的。当前最多可以诚实主张的是：**CARE-MyoPath-PR 是下一轮最值得实施的、具有明确因果归因能力的单-backbone 研究原型；它有希望在本地 OOF 的 scar 小灶召回、remote FP 控制和 T2-present edema boundary 上拿到结构性改善，但它不具备被我批准为‘官方验证高增益主航道’的证据条件。** 对 official validation 的现实预期，我认为更接近 scar $$+0.005\sim+0.020$$、pure edema $$0\sim+0.020$$ 这一等级；如果某次实验出现更大跃迁，那也必须被当成待复核异常，而不是先验承诺。这个预期区间来自 CURRENT.md 的 official anchor、V4 的 case-oracle bound、以及 atlas 中模型互补窄而 error pool 明显的新机制需求三者共同制约。citeturn12view0 fileciteturn11file0 fileciteturn12file0

### 备选方案

真正不同且更保守的备选，不是“把首选删掉一半再叫另一个名字”，而是：**CARE-MyoPath-Lite**。它保留与首选相同的输入合同、完整 backbone、availability-aware 融合、reliable-label/no-T2 hygiene 与 scar/edema 独立 global heads，但**取消两个 ROI refiner，只保留 scar/edema proposal 与 anatomy exchange**。也就是说，它承认：“当前最可靠的增益也许不来自局部重建，而来自更干净的病种解耦和 better proposal authority。” 这个方案的新增参数约为 backbone 的 $$12\%\sim15\%$$，推理 FLOPs 约 $$1.10\times\sim1.15\times$$，工程风险更小，因果归因更清楚，但机制上限也明显更低。它适合在项目不允许承担 ROI refiner 复杂度时做高可信验证。按我对证据的判断，它的现实上限更像 scar $$+0.005\sim+0.015$$、T2-present pure edema $$0\sim+0.015$$ 的 moderate gain 线路，而不是翻盘线路。fileciteturn12file0

### 当前能够主张什么

当前能够主张的，是以下几件事。其一，**完整 decoder 不可破坏**，这是 V4 最硬的本地因果证据之一。其二，**scar 与 pure edema 必须独立建模**，并且 edema 必须受 no-T2 hard gate 约束。其三，**supervision 要从“平均体素”升级到“病灶形成”**：scar 需要 proposal、component-aware weighting、lesion-level recall loss；edema 需要 T2-only proposal、大 ROI refinement、boundary uncertainty。其四，**help/harm、remote FP、proposal coverage、refiner-minus-proposal、no-T2 safety** 必须成为组件有效性的前置门，而不是论文附录。其五，alignment 最多是轻量附加项，不是主线；prototype 现在不该回主线。所有这些都既有本地证据，也有外部方法学支撑。fileciteturn12file0 citeturn30search1turn29search0turn31search3turn26search15

### 当前不能主张什么

当前不能主张的，也必须说清。不能主张“V4 feature probe 已经证明可部署 selector”；不能主张“MoSAIC M2-M10 已经证明 fair validation superiority”；不能主张“alignment 是全局主瓶颈”；不能主张“只要加一个局部 refiner 就有 $$\approx 0.1$$ Dice 上限”；不能主张“official validation 一定能超过当前 nnU-Net anchor”；更不能主张“持续长训练是现在最优资源配置”。如果忽略这些不能主张的边界，CARE 就会再次掉回 V3/V4 之前那种“模块存在—日志齐全—感觉合理—但科学上不成立”的循环。fileciteturn12file0

## 参考阅读

下面只列**本设计真正借力的一手来源**，并明确说明“借了什么、没借什么”。

- **MyoPS-Net: Myocardial Pathology Segmentation with Flexible Combination of Multi-Sequence CMR Images**；Junyi Qiu 等，2023，*Medical Image Analysis*。论文：MedIA 与 arXiv 页面。代码：官方 GitHub，**MIT**。本设计借用其“缺模态下先做模态私有嵌入，再做灵活共享融合”的思想；没有借用其五序列设定、也没有借用其可能导致多分支过重的整体结构。citeturn39search11turn26search8turn32search3

- **U-MyoPS**；官方仓库名称为 **NanYoMy/myops**，基于“Aligning Multi-Sequence CMR Towards Fully Automated Myocardial Pathology Segmentation”方向；公开代码仓库可见 **Apache-2.0**。论文/方法说明：官方 README 与公开全文摘要。代码：官方 GitHub。本文借用其 myocardium prior 与 pathology 需要 anatomical support 的思想；没有借用其多 encoder + registration head 的重型结构，也没有把 registration 升格为主线。citeturn33search0turn28search2

- **Multi-Source and Multi-Sequence Myocardial Pathology Segmentation Using a Cascading Refinement CNN**；Franz Thaler 等，2024，arXiv / CARE 2024 路线。论文：arXiv HTML。代码：我未检到官方公开代码。本文借用 anatomy-first 再 pathology-refine 的 coarse-to-fine 思路与统一物理空间工作流；没有借用双阶段完整 cascade 与 5-fold ensemble 作为方法主体。citeturn27search1turn27search5turn39search4

- **Anatomy-guided Pathology Segmentation**；Alexander Jaus 等，2024，MICCAI 2024。论文：MICCAI Open Access / arXiv。代码：官方 GitHub，**Apache-2.0**。本文借用 anatomy–pathology exchange 的机制灵感，即解剖信息应作为 pathology decoder 的条件输入；没有借用其 DETR 风格 query transformer 全量实现，也没有借用其依赖外部 anatomy dataset 的训练范式。citeturn26search15turn26search7turn32search2

- **PASSION: Towards Effective Incomplete Multi-Modal Medical Image Segmentation with Imbalanced Missing Rates**；Junjie Shi 等，2024，ACM MM 2024。论文：arXiv / ACM 页面。代码：官方 GitHub，**Apache-2.0**。本文借用其“缺模态率不均衡本身需要训练期平衡”的观点，以及 availability-aware、modality-balanced 训练策略；没有借用其 plug-and-play 泛化承诺，也没有把自蒸馏当成本地已验证有效机制。citeturn31search3turn26search9turn33search1

- **Incorporating Modality-Specific Intensity Prior as Text Prompt for Multimodal Myocardial Pathology Segmentation**；D. Fang 等，2026，*Medical Image Analysis*。论文：期刊摘要页。代码：官方 GitHub **I_MMSeg**；仓库页面未见清晰许可证声明。本文借用其“modality-specific intensity prior”这一方向意识，即 T2/LGE 的强度先验应病种特异化；没有借用其 CLIP + LLM text prompt 依赖，也没有把文本先验作为当前 CARE 主线。citeturn31search22turn34search0

- **A Composite Alignment-Aware Framework for Myocardial Lesion Segmentation in Multi-sequence CMR Images**；Yifan Gao 等，2025，MICCAI 2025。论文：MICCAI Open Access / arXiv。代码：官方 GitHub，**MIT**。本文借用其“轻量 alignment-aware 模块只在必要时使用”的启发；没有借用它作为两阶段主系统，也没有把 alignment 设为首要机制。citeturn26search6turn26search10turn32search1

- **HeMIS: Hetero-Modal Image Segmentation**；Mohammad Havaei 等，2016，MICCAI。论文：arXiv / Springer。代码：公开实现众多，但本文只借官方论文思想。本文借用其 mean/variance latent fusion 的基础范式；没有借用其原始任务与无解剖上下文限制。citeturn31search0turn31search12

- **Component-Adaptive and Lesion-Level Supervision for Improved Small Structure Segmentation in Brain MRI**；Minh Sao Khue Luu 等，2026，arXiv。论文：arXiv。代码：官方 GitHub **SmallLesionMRI**，仓库 README 可见但许可证尚未补全。本文借用 component-adaptive Tversky 与 lesion-level MIL 这两个损失思想；没有借用其脑 MRI 具体实验设定，也没有把其数值增益直接迁移到心脏任务。citeturn30search1turn33search3turn33search2

- **Lesion Harvester: Iteratively Mining Unlabeled Lesions and Hard-Negative Examples at Scale**；Jinzheng Cai 等，2020/2021，arXiv / *IEEE TMI*。论文：arXiv / PubMed。代码：官方释出的是 DeepLesion harvested annotation。本文借用“高召回 lesion proposal + selective FP suppression + hard negative suppression loss”的方法学框架；没有借用其 CT lesion detector 具体网络，也没有把其半监督挖掘流程照搬到 CARE。citeturn29search0turn29search4turn29search20

- **MyoPS: A Benchmark of Myocardial Pathology Segmentation Combining Three-Sequence Cardiac Magnetic Resonance Images**；Lei Li 等，2023，*Medical Image Analysis*。论文：arXiv / MedIA。代码：文中汇总 Challenge 公开代码。本文借用其对 MyoPS 任务障碍的总体分析框架，尤其是对病灶分割仍处于早期阶段的判断；没有把 MyoPS 2020 的干净三序列设定误当作 CARE MyoPS++ 的真实临床分布。citeturn38search2turn38search14turn38search5