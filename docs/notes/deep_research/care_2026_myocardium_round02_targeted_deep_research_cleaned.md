---
title: "CARE 2026 Myocardium Round02 定向深度研究报告（cleaned）"
author: "ChatGPT Deep Research"
date: "2026-07-17"
source_pdf: "care_2026_myocardium_round02_targeted_deep_research_original.pdf"
render_note: "从原始 PDF 重新抽取 raw text 后清理硬换行、页码、脚注号、公式、表格和引用；原始 PDF 同目录保留。"
---

# CARE 2026 Myocardium Round02 定向深度研究报告（cleaned）

> 来源：`care_2026_myocardium_round02_targeted_deep_research_original.pdf`。本 cleaned Markdown 去除了 PDF 反向抽取造成的多余空段、页码、脚注号和误代码块；两个表格已重建为 Markdown 表，公式和引用保留为可渲染形式。

## 结论先行

本轮在科学方向上不需要再改弦更张。Round02 的关键不是再搜一个更强 backbone，也不是把整个项目重写成另一个论文，而是把当前已经半成型的 SRR-v3 路线从"有名词、有模块、有表格"收束成真正进入 final path、可以做 changed-voxels/components 归因、可以 clean-reload、可以被严格 validator 卡住偷懒空间的实现合同。M9 与 M10 的历史证据已经非常清楚：只要 proposal、prototype memory、refiner、 registration、temporal 其中任一环节停留在 helper、proxy、bootstrap、stale selector、single-frame wrapper 或 local-only receipt，结果即使"输出变了"，也不等于"病灶形成被控制了"。M9 三个正式 SRR candidate 都不是近恒等，但 scar/edema Dice、HD95 和远端假阳性整体仍然恶化；M10 虽然补了一批机制与 packet，但 Route C 仍把 Cine 侧 runtime fidelity 与 D2/D3 intervention 标记为 NEEDS_EVIDENCE，而且 checkpoint selector 还暴露过复用历史评估、缺少 fresh --force 的问题。也就是说，Round02 的主要矛盾已经不是"有没有想法"，而是"如何把想法冻结成不可糊弄的合同"。我给出的唯一主张是：Route B 冻结完整四尺度 SRR-v3，但 proposal 必须采用"解剖保守级联 + prototype similarity-difference 作为附加证据"的混合机制；prototype memory 改成 fold-safe、OOF-fitted、推理时冻结的 prototype bank，而不是把在线 EMA helper 继续当正式核心；Cine 分支直接对接官方 CineMA 资产与真实 decoder 特征，不再使用 CARE 现有的小 3D conv wrapper 伪装成 CineMA；registration 必须从当前的"位移场 + grid_sample"升级为真正的 SVF + 七步 scaling-and-squaring + forward/inverse/ Jacobian/inverse-composition 收据；temporal 必须显式消费注册后的多帧 logits/features/motion/ Jacobian/quality，而不是把一个抽象的 temporal_z 塞给 temporal head。 Route A 则只保留压缩版：两尺度、无 interaction experts、无在线 memory，只做 conservative proposal/refiner 与 bounded correction；Route C 不再发明新 MyoPS 科学设计，而是冻结选择器、重放、intervention、Cine fidelity 证据合同。

外部模块里，真正值得借的只有两类。第一类是官方 CineMA：官方 GitHub 与 Hugging Face 都公开了代码、许可证和权重，且 segmentation lane 使用的是 ConvUNetR，推理脚本与模型下载路径明确；CARE Route A 合同甚至已经把 code commit、HF revision 和权重 SHA256 都写死了。第二类是数学局部件而不是整套替换：例如 VoxelMorph 里关于 diffeomorphic SVF 与 scaling-and-squaring 的数学正确实现可以借鉴，但不能因此把 Route C 已冻结的 scientific contract 改写成"直接换一个现成库就算完成"。相反，不应继续投入的方向包括：通用 backbone 大搜索、完整移植 U-MyoPS、重新发明 dictionary topology、synthetic T2、生成式缺模态补全、compactness-only 修补，以及任何不能进入 final path 的 wrapper/placeholder。

本研究还能解决的，是实现合同层面的歧义：proposal/refiner 的张量路径、prototype bank 的安全负样本边界、CineMA adapter 的 hook 点、registration/temporal 的最小因果链、checkpoint selector 和统一 evidence contract。最终仍只能靠实验回答的，只剩三类问题：其一，Route B 的 prototype-augmented proposal 相比 conservative anatomy-guided proposal 在 220 例 MyoPS 上是否真能稳定增益；其二，官方 CineMA feature 在 CARE 数据域是不是比 matched-random control 真正带来跨病例收益；其三，registered temporal aggregation 对 myocardium/cinemyops 是否有足够绝对收益，足以抵消工程与失败风险。需要单独声明的是：本研究无法访问 /users/a/e/aereinh/CARE 本地工作树，因而无法执行用户要求的本地 git status --short、 git fetch --all --prune 与远端 ref 枚举；以下判断仅基于远端 GitHub 证据与当前对话可访问资料，不能声称已经验证本地未提交或未推送工作。另外，我能够视觉阅读仓库中的 images/ SRR-v2.png、 SRR-v2.5.png、 SRR-v3.png 并据此解释架构内容，但无法独立确认它们与用户所说"Project 背景材料中的 SRR-v2/v2.5/v3"是否为完全同一份来源副本；这是本报告最主要的来源约束。

## 仓库证据摘要

当前远端工作流要求先读 AGENTS.md、 START_HERE_FOR_GPT.md、 GPT_PLANNER_CARE_PROTOCOL.md、一组 route protocol、 CURRENT.md、watchboard 与 wiki/history； CURRENT.md 明确把当前 round 指到了 portfolio_round02_planner_handoff_20260717.md 以及 Route A/B/C 的当轮 Critic handoff。仓库治理文件强调：不得把 pending Slurm、local proxy、hosted metric 占位、未经过 current_round_critic_required的路线当成完成，也不得把配置或 helper 误报成机制闭环。 src/care_myocardium 目录同时暴露了当前 MyoPS、proposal/prototype、Cine、refiner 与 loss 的一组第一方实现，这些正是本轮要冻结合同的接入点。就当前可见的实现状态看，仓库里已经存在 proposal / prototype / bounded correction / Cine adapter / registration / temporal 的代码骨架，但多处仍然停留在"可运行、可记录、不可证明是 faithful final-path 机制"的阶段。 pathology_heads.py 目前只是给解剖 head 后接一个 soft anatomy prior，然后用这个 prior bias scar 与 edema logits； proposal_prototypes.py 已经把 edema safe negative 限制到 T2-present 样本，并显式禁止把 no-T2 myocardium 当 edema negative；但 srr_propref.py 里 proposal prototype 的默认来源仍写成 deterministic_axis_bootstrap_pending_train_or_oof_fit，说明默认前向仍可能停留在 bootstrap 占位。与此同时，最终输出仲裁现在是显式 anchored 的 bounded correction： final = anchor_logits + gate * max_delta * tanh(srr_logits - anchor_logits)，而 no-T2 的 edema channel 还会被强制 fail-closed。也就是说，当前主干仍然非常强依赖 anchor，而不是已经彻底进入"SRR-owned final logits"。

Cine 侧的问题更集中。CARE 现有 CineMAAdapter 只是一个对 image + cinema_prior 做两层 3D 卷积再出四类 logits 的小网络；它不是官方 CineMA，也没有稳定暴露官方 decoder feature。当前 RegistrationUNet 只预测一个经 0.25*tanh 缩放的 3 通道场，再用 grid_sample(..., padding_mode="border") 去 warp；能看到 smoothness_loss，但在已抓取代码里看不到七步 scaling-and-squaring、forward/inverse transform、 Jacobian determinant、folding rate 或 inverse-composition。 CineTemporalModel 的接口也只接 ed_image、 ed_prior 和一个抽象 temporal_z，然后把 ED adapter 输出与 TemporalSlotDictionary 融合；它没有把"registered logits/features、reference 与 non-reference frame、motion/Jacobian/ quality"强制写进接口，因此从 contract 角度看还不够 faithful。历史 handoff 与 review 对各路线的阻塞也已经很清楚。Route A 的当轮合同已经把它定位成"compressed SRR gate-opening and real CineMA temporal candidate"，并且明确禁止 single-frame wrapper、 morphology-only postprocessor、identity residual gate；它还把官方 CineMA 资产的 code commit、HF revision、权重 SHA256、固定 frame set、 SyNOnly 和至少四个通过注册的非参考帧写进了路线合同。反过来，Route A 旧审查结论指出其先前候选"没有可测标签变化"，因此 changed voxels 为零的候选不得再冒充非 nnU-Net 候选。Route C 当前结果与 review 也表明，M10 follow-up2 的 Cine fidelity 与 D2/D3 证据并未真正收官，仍然属于 NEEDS_EVIDENCE，不能把 partial evidence 包装成 final scientific decision。

## 历史失败与根因表

下表不是"只挑支持新方案的证据"，而是把当前远端能明确核对到的坏结果、未完成结果和已知不合格实现一并列出来。需要坦率说明：用户要求逐行列出精确 Dice、HD95、remote-FP、component burden 数值，但这些数值在当前公开的远端摘要与 review 文本中并未全部显式展开，可见仓库更完整的 CSV/validator/ runtime packet 并未全部入库；因此表内数值字段只能区分为"已明确为零、已明确恶化、或远端摘要未显式给数"，不能伪造具体数字。

| 实验/版本 | final path 状态 | changed voxels | Dice | HD95 | remote-FP | component burden | 实现状态 | 失败解释 | Round02 含义 |
|---|---|---:|---|---|---|---|---|---|---|
| Route A 旧候选 | 实际近恒等/无可测输出变化 | 0 | 远端摘要未显式给数 | 远端摘要未显式给数 | 远端摘要未显式给数 | 远端摘要未显式给数 | 实现/证据不充分 | 不是“轻量非 nnU-Net 候选”，而是没有真正打开 final path 的 gate | Route A 必须把 non-identity gate 写入 completion token；changed voxels 为零直接 known-bad |
| M9 三个正式 SRR candidate | 非近恒等，但仍是负向 | 非零 | 整体恶化 | 整体恶化 | 整体恶化 | 恶化或未受控 | 形式上完整，科学上失败 | 输出确实变了，但 proposal/memory/refiner 没有控制病灶形态，反而放大远端假阳性与组件负担 | Round02 不允许再把“输出变化”当成功；必须量化 lesion-centric help/harm |
| M9 prototype/proposal/refiner | 未形成因果闭环 | 未证明 | 未证明改善 | 未证明改善 | 未证明改善 | 未证明改善 | helper/骨架偏多 | wiki 对比明确说 memory 更像 helper、proposal recall 仍弱、refiner 因果证据不足 | Route B 的 memory 与 proposal/refiner 必须写成张量合同与 selector 指标，不许停留在命名层面 |
| M10 complete mechanism repair | MyoPS packet 较 M9 更完整，但仍未完成独立 runtime 关门 | 非零 | 远端摘要未显式给数 | 远端摘要未显式给数 | 远端摘要未显式给数 | 远端摘要未显式给数 | NOT_REVIEWED 边界仍在 | all-checkpoint evaluation 与 D2/D3 intervention packet 虽已加入，但还需要独立 runtime review | Route C 不能把 packet 完整性等同科学完成 |
| M10 continuation reconciliation | selector 可信度受损 | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 | 证据污染 | checkpoint selection 复用了 20260711 历史评估痕迹、缺少 fresh --force 证据，因此 best checkpoint 不能被当新鲜选择结果 | selector 必须强制 fresh --force 与 SHA 绑定 |
| M10 follow-up2 Cine fidelity | final-path faithful 仍不足 | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 | NEEDS_EVIDENCE | Route C 自身承认 real SyN strict aggregation 与 temporal terminal outputs 仍缺 | Cine fidelity 仍是必须关闭的 evidence gap |
| 当前 CARE registration/temporal 代码 | 与合同不一致 | 可变但不可归因 | 不适用 | 不适用 | 不适用 | 不适用 | first-party skeleton | registration 只有 displacement + warp；temporal 只有 temporal_z，没有强制 registered logits/features/motion/Jacobian 输入 | Round02 必须写 faithful registration/temporal contract |

这些失败共同指向一个根因：dictionary-only 或 dense-head-only 实现即使改变了输出，也不自动等于控制了"病灶怎么形成"。 SRR-v3 图里 proposal、soft ROI、scar/edema 专属 refiner、bounded correction 和 Cine temporal retrieval 是分工明确的：前半段负责"选择证据"，后半段负责"形成病灶"。如果只有 retrieval/export 表格，没有 proposal recall、ROI retention、refiner 改写的证据链，那么输出变化大多会表现为远端 FP、噪声组件、HD95 恶化，或者被 anchor residual 吞回到近恒等。M9 的失败正是这类"有扰动、无可控病灶形成"的典型。

## 五份核心实现合同

## Proposal 与 refiner 决策

从 SRR-v3 图、当前 CARE 代码和历史失败证据合起来看，Round02 不应选"单纯卷积 proposal head"做 Route B 主实现。单纯卷积 head 的优点是侵入小、220 例也容易训，但它最容易重走 M9 的老路：输出确实改变，却把 proposal 当成另一个 dense logit，并不能解释为什么 ROI 应该被包含、为什么远端小岛应该被压掉、为什么 scar 与 edema 的形态规则不同。另一方面，纯 prototype similarity-difference proposal 如果直接当主头，又会把当前仓库里 deterministic_axis_bootstrap_pending_train_or_oof_fit 的问题放大——因为 default bank 还可能是 bootstrap，占位 prototype 一旦进入 final path，训练稳定性和可解释性都会被污染。最稳妥的主实现，是解剖保守级联 proposal 为主、prototype similarity-difference 为辅的轻量组合：先用 anatomy prior、anchor uncertainty、component evidence、modality evidence 形成 conservative coarse proposal，再把正负 prototype 相似度差 s^+ - s^- 作为加性证据，而不是唯一证据源。这个设计既继承了 MyoPS-Net、U-MyoPS、MyoPS2020 winner 中"依赖解剖/序列互补、从 coarse 到 fine 收缩候选区"的稳定性，也吸收了 anatomy-guided pathology segmentation 这类工作对病灶 containment 的强调，但避免了把整个项目移植到另一套重型 pipeline。因此，Route B 主实现我建议冻结为如下张量流。输入固定顺序是 `[LGE, T2, C0]`，shape 记为

$$
x \in \mathbb{R}^{B\times 3\times H\times W\times D}, \qquad m \in \{0,1\}^{B\times 3}.
$$

四尺度 modality-specific stems 各自产生

$$
f^{\mathrm{LGE}}_{\ell}, f^{\mathrm{T2}}_{\ell}, f^{\mathrm{C0}}_{\ell} \in \mathbb{R}^{B\times C_{\ell}\times H_{\ell}\times W_{\ell}\times D_{\ell}}.
$$

每尺度再产生 shared/private/interaction expert 输出与 pathology-specific routed feature。proposal 侧不直接吃 raw image，而是吃病种专属 routed feature、anatomy union 概率 $p_{\mathrm{myo}}$、anchor scar/edema 概率与熵、component map、prototype positive/negative similarity 图，以及 anatomy neighborhood / distance-support。scar proposal logits 为

$$
z^{\mathrm{prop}}_{\mathrm{scar}} = h\left([r^{\mathrm{scar}}, p_{\mathrm{myo}}, p^{\mathrm{anchor}}_{\mathrm{scar}}, u^{\mathrm{anchor}}, c^{\mathrm{anchor}}_{\mathrm{scar}}, s^{+}_{\mathrm{scar}}, s^{-}_{\mathrm{scar}}, d]\right),
$$

edema proposal logits 为

$$
z^{\mathrm{prop}}_{\mathrm{ede}} = h\left([r^{\mathrm{ede}}, p_{\mathrm{myo}}, p^{\mathrm{anchor}}_{\mathrm{ede}}, u^{\mathrm{anchor}}, c^{\mathrm{anchor}}_{\mathrm{ede}}, s^{+}_{\mathrm{ede}}, s^{-}_{\mathrm{ede}}, d, m_{\mathrm{T2}}]\right).
$$

这里 $r^{\mathrm{scar}}$ 与 $r^{\mathrm{ede}}$ 都保留梯度；prototype similarity 图本身对 feature 保留梯度，但 bank tensor 在正式训练中冻结；distance map 与 component label 只作诊断/条件，不反传到其生成器。proposal probability 是

$$
p^{\mathrm{prop}}=\sigma(z^{\mathrm{prop}}).
$$

soft ROI 不是硬 crop，而是

$$
\mathrm{ROI}=g\left(p^{\mathrm{prop}},p_{\mathrm{myo}},u^{\mathrm{anchor}},d_{\mathrm{myo}},c^{\mathrm{anchor}}\right) \in [0,1]^{B\times 1\times H_{\ell}\times W_{\ell}\times D_{\ell}}.
$$

然后 scar 与 edema 分别进入各自 refiner。scar refiner 的 crop dilation 小、局部分辨率高、hard negative 压制更强；edema refiner 的 dilation 更大、上下文更宽、边界更软。final pathology logits 由 refiner 输出的 bounded delta 回填到全图，再进入 anchor-bounded correction。这个思路与当前 `srr_propref.py` 里 soft ROI 已经显式消费 `proposal_logits`、`anatomy_prior`、`anchor_evidence`、`component_evidence`、`pos_similarity`、`neg_similarity` 的方向一致，但要把默认 bootstrap bank 与“只是 helper”两个漏洞封死。

Route A 压缩版则不应保留 prototype 作为正式必要模块。Route A 的目标是最快形成"非纯 nnU-Net 候选"，所以只保留两尺度、无 interaction experts、无在线 memory；proposal 只吃 routed task features、 anatomy union probability、anchor entropy、anchor component mask 与 modality evidence，scar 用 1- voxel soft dilation，小 ROI、高分辨局部 refiner；edema 用 4-voxel dilation、大 ROI、上下文保留 refiner。这一压缩版其实已经与当前 Route A 合同高度一致。Route A 的 fallback 很简单：若 proposal/refiner 没有通过 changed-voxels/gate-open/retention 证明，则回退到 conservative bounded correction 候选，不再声称是完整 SRR-v3。

scar 与 edema 必须分开写，而不是一个双通道 head。scar 主要由 LGE 证据驱动，proposal threshold 更高，negative prototype 更强，ROI dilation 更小，目标优先压 remote FP 与 component burden，并加入 boundary/HD-sensitive objective。edema 则只能在 T2-present 样本上有正监督；no-T2 样本可以参加 anatomy loss、scar loss、shared/private routing regularization、以及 fail-closed gate 约束，但绝不能把 no-T2 myocardium 当 edema negative，因为"没拍到 T2"并不等于"没有 edema"。edema 的 proposal 应更注重 recall、更大 receptive field、更软边界与 uncertainty，并把 safe negative 限定为 T2- present 的远离 edema 的正常 myocardium / blood / outside / hard FP。当前 CARE 的 prototype builder 已经把这条 safety 规则写进代码；Round02 需要做的是把它从 helper 上升为正式合同。训练阶段上，我建议冻结四段式：第一段 evidence warmup，只训 shared/private/interaction retrieval 与 anatomy head，让 router、retrieval、anchor-bounded path 达到稳定非退化；第二段训 proposal，冻结 refiner，只看 proposal recall / precision / positive-case nonempty / proposal-to-final retention；第三段训 refiner，冻结 proposal head 主体，仅允许小学习率微调 proposal temperature 与 gate；第四段低学习率 joint fine-tune，把 proposal/refiner/gate/bounded correction 连起来。每一段必须有进入下一段的 gate，不再用"epoch 到了"自动推进：比如 evidence warmup 不通过 router sensitivity、proposal 阶段不通过 recall gate、refiner 阶段不通过 changed-component 与 HD95 方向性，就不得进入下一段。这个 staged 设计不是为了优雅，而是为了避免 220 例数据在多个弱信号模块同时训练时直接塌成 anchor imitation。

## Prototype memory 与安全负样本合同

这里必须明确给一个与当前仓库不同的决定：Round02 的正式 final-path 原型记忆不应采用在线 EMA memory 作为主推理机制，而应采用"fold-safe、OOF-fitted、inference-frozen prototype bank + training-only hard-negative queue"的双层方案。原因很直接。当前 SafePrototypeMemoryBank 的确已经实现了"拒绝 no-T2 edema negative 更新"，也会把更新事件记 ledger；但它本质上仍是一个类别均值的 EMA helper，仓库历史总结也明确指出它"更明确，但像 helper"，并未证明自己真正影响了 final logits 或 checkpoint selection。与此同时， srr_propref.py 里 prototype 默认来源还可能是 deterministic axis bootstrap，这对正式推理是不可接受的。正式规范应当是这样的。scar positive prototype 来自 train fold 或 OOF feature tensor 中 scar GT voxel 的多尺度均值；scar negative prototype 来自正常 myocardium、blood pool、outside-myocardium、hard FP、 artifact 五类。edema positive prototype 只来自 T2-present 且 edema-positive 的 voxel；edema safe negative 也只来自 T2-present 的"远离 edema 的正常 myocardium、blood、outside、hard FP、 artifact"，并且禁止任何 no-T2 myocardium、unknown edema status tissue、伪阴性 region、或 validation/test label参与更新。prototype 数量上，Route B 建议每尺度 scar 正样本 $K^+_{\mathrm{scar}}=8$、负样本 $K^-=12$；edema 正样本 $K^+_{\mathrm{ede}}=8$、安全负样本 $K^-=12$。feature 维度跟随该尺度 channel，不额外投影到太小维度；每尺度、每病种、每正负分开存。初始化采用 OOF centroid fit，不用 learnable parameter，也不用随机初始化进正式路径。 } 更新策略分成四层。当前 batch prototype 只用于算 batch-level similarity 与 hard-negative mining，不落盘。epoch memory 只用于训练时统计与 replay，不用于 validation/test 推理。validation/test frozen memory 是在每个 fold 上由 train/OOF feature 离线拟合后写入 checkpoint 的 prototype bank，clean reload 后字节级一致。training-only hard-negative queue 则单独维护，被 remote-FP / proposal-FP / refiner-FP 触发，每个病种每尺度最多保留固定数量，例如 256 个 component-level centroid，采用 FIFO + hardest-first 混合替换。分布式训练下，prototype fit 必须通过 all-gather 收集 train fold feature centroid，再统一写 bank；但 hard-negative queue 不需要跨 rank 强同步，只要在 rank0 聚合并定期 broadcast 摘要即可。checkpoint serialization 必须同时写入：bank tensor、source manifest SHA、fit script commit、OOF split receipt、类目计数、空类 fallback 标记。只要来源不是 train/OOF，bank 就判 invalid。如果时间预算太紧，conservative fallback 就是 Route A 的那套：保留 anatomy-guided proposal，不把 prototype memory 作为 final-path 必需项；Route B 仍可保留 prototype 为正式核心，但要把 planner 写成"若 OOF-fitted frozen bank 未在 gate 时间内完成，则降级到 no-prototype conservative proposal control，不得把 bootstrap prototype 当正式结果"。这一点特别重要，因为当前代码已经证明 bootstrap vector 很容易伪装成"有 prototype 模块"，但这恰恰是 Round02 要根除的偷懒路径。

## CineMA adapter 合同

这一部分最需要做"代码现实主义"。官方 CineMA 不是 CARE 里那个小型 CineMAAdapter。官方 GitHub 仓库 mathpluscode/CineMA 公开声明项目为 MIT 许可，并给出 fine-tuned segmentation、classification、 regression、landmark 等多任务模型；Hugging Face 模型卡明确列出了 segmentation SAX 的权重文件与配置文件。Route A 当前 round02 合同甚至已经把 Route A 要使用的官方资产固定为：code repository commit c10daa1d93f0ea28d8b9ad9206b0f673d25805c1、HF revision b1251ee50423bceeca84c080782fc3bc7756dea6、SAX segmentation 权重 finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors，以及 SHA256 c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f。这些是 Round02 最可靠的现成外部资产冻结点。官方 segmentation 模型类是 cinema.segmentation.convunetr.ConvUNetR。源码里 get_model(config) 直接实例化 ConvUNetR，而 ConvUNetR.from_finetuned(...) 则通过 hf_hub_download 下载模型权重和 config，再加载 safetensors state dict。该模型的 forward(image_dict) 返回 per-view logits；对 SAX 而言是 3D 输入， out_chans=config.model.out_chans。官方示例使用 ScaleIntensityd 和 SpatialPadd(keys="sax", spatial_size=(192,192,16), method="end")，说明最小官方推理范式是强度缩放到标准范围、再 pad 到固定 SAX 体尺寸。官方 MAE 特征抽取脚本 mae_feature_extraction.py 则公开了 CineMA.from_pretrained() 和 feature_forward(image_dict) 这条 first-party feature API，且同样使用 ScaleIntensityd 与 (192,192,16) pad。因此，Round02 要冻结的 CineMA adapter 不是"再包一层小卷积适配器"，而是双源适配。解剖 logits 应来自官方 fine-tuned ConvUNetR的 SAX segmentation 权重；特征则优先取 ConvUNetR.forward() 中最后 decoder tensor x、也就是 pred_head_dict['sax'] 的输入张量。这是当前最稳的真实 hook 点，因为它在官方代码里客观存在： x = self.decoder_dict[view](embeddings_view) 之后才有 preds[view] = self.pred_head_dict[view](x)。如果不想 monkey-patch 全 forward，最小 first-party adapter 就是复制官方 ConvUNetR.forward()，在 pred_head_dict['sax'](x) 前把 x 与 logits 一并返回。这样拿到的 feature shape 是 $$[B,C_{\text{dec}},H,W,D]$$，stride 为 1，与 logits 空间一一对应；它比去 hook ViT token 或 MAE latent 更适合作为 CARE 的 anatomy evidence。

CARE 数据适配上，Planner 应写死如下合同。cine 原始 4D 数据一律重排为 $$[T,Z,H,W]$$ 或 $$[Z,H,W,T]$$ 后再统一成内部张量 $$[B,1,Z,H,W]$$ 的单帧 SAX 输入，不允许混乱轴顺序。ED/reference frame 由标签或已冻结的 frame selector 定义，非参考帧都要在相同 orientation canonicalization、spacing 和 intensity normalization 下处理。官方脚本显示其 segmentation SAX 是单 timeframe 输入，所以 CARE 不应该把原 4D 堆进官方模型，而应做per-frame inference + 3D volume reconstruction：每个选中时间帧各自进入官方 SAX segmentation 模型，保存 logits、probabilities、decoder feature、predictive entropy 和原 affine/ header provenance。label mapping 则对应四类 anatomy 语义；如果后续要接 CARE 的 compact cine label，必须在 adapter 里显式记录从官方 output classes 到 CARE 需要的 anatomy 语义映射，而不是在后处理脚本里悄悄重编码。

pretrained 与 matched-random control 也必须写得足够严。两条 lane 必须使用同一个 ConvUNetR结构、同一个 config、同一个 adapter/head、同一个数据、同一个 split、同一个 augmentation、同一个 seed、同一个 downstream initialization；唯一区别只能是上游 CineMA segmentation 权重从官方 safetensors 加载，还是按相同 config 新建后经过相同初始化函数得到 matched-random。不能让 pretrained lane 用官方 head，而 random lane 另起一个小 adapter，这样比较根本无效。

## Registration 与 temporal 合同

当前 CARE 的 registration 代码已经证明"first-party"不等于"faithful"：现有实现有一个 3D U-Net、一个位移场和一个 warp()，但没有看见七步 scaling-and-squaring、forward/inverse consistency、Jacobian receipts、label/probability/feature 分别插值规则，也没有明确 case-level/pair-level aggregate replay。换句话说，它是一个 registration skeleton，不是本轮需要的 faithful contract。Voxelmorph 的 probabilistic diffeomorphic 论文把 stationary velocity field 和 differentiable scaling-and-squaring 明确写成核心； Round02 应借鉴的是这一数学局部件，而不是整个项目直接依赖第三方训练脚本。我建议 Planner 冻结如下 first-party faithful registration 实现。网络输出 stationary velocity field

$$v \in \mathbb{R}^{B\times 3\times Z\times H\times W}.$$

单位统一在 normalized grid coordinates 中定义；forward transform $\phi=\exp(v)$ 通过七步 scaling-and-squaring 实现，inverse transform $\phi^{-1}=\exp(-v)$ 同样七步积分得到。image / feature / probability warp 使用 trilinear 插值，label warp 使用 nearest，border handling 固定为 border，并分别存 receipt。每个 pair-level 结果都必须记录 image similarity、Jacobian determinant 直方图、folding rate、inverse-composition error、smoothness loss，以及 warped feature/probability/label 的 SHA。case-level pass 把 reference frame 与所有 non-reference frame 的 pair receipt 聚合；aggregate pass 再把 case-level 收据汇总进 temporal manifest。clean reload 时，任何 temporal 训练都必须从这些已落盘、已验 SHA 的 registered outputs 复现，而不是重复在线临时注册后无账可追。这个合同与 Route A 当前把 SyNOnly、transform path、warped image、warped CineMA logits/features、per-pair similarity/Jacobian receipt 写入要求是一致的，只是现在要把 Route C 与 Route B

也统一到同一收据标准。temporal 侧同理。当前 CineTemporalModel 只接收 `ed_image`、`ed_prior` 和一个抽象的 `temporal_z`，这不满足用户要求的真实因果路径。Round02 的正式 temporal contract 应当强制输入注册到参考帧空间后的 logits/features：

$$
[f^{(0)}_{\mathrm{cine}}, \ell^{(0)}_{\mathrm{cine}}, u^{(0)}_{\mathrm{cine}}, \{f^{(t\to 0)}_{\mathrm{cine}}, \ell^{(t\to 0)}_{\mathrm{cine}}, u^{(t\to 0)}_{\mathrm{cine}}, |d^{(t\to 0)}|, J^{(t\to 0)}, q_t, \tau_t\}_{t\in\mathcal{T}}].
$$

其中参考帧固定是 ED / frame 0，非参考帧来自冻结 frame set，且都必须注册到参考帧空间。Route A 可以用 masked mean aggregation；Route B 则保留 temporal slot dictionary，但 slot 输入必须显式拼入 anatomy logits、decoder feature、motion magnitude、Jacobian、uncertainty、frame quality、temporal position，而不是任意抽象 latent。最小训练预算上，Route A 沿用合同里的 6 帧采样、至少 4 个通过注册的非参考帧；Route B 则要求 reference-only control、unregistered multi-frame control、registered temporal aggregation、 temporal-off、motion-off、anatomy-off、pretrained-vs-random 全套消融都指向同一最终输出头。只有这样， changed_voxels 和 changed_components 才能证明 temporal 真的被 final output 消费。

## 统一 evidence 与 checkpoint 选择合同

Round02 的 evidence contract 必须从"有没有涨一点 Dice"升级到以病灶为中心的多指标选择器。训练监控可以看 Dice、loss、proposal recall、proposal precision、proposal-to-final retention、positive-case nonempty rate、gate-open voxel rate。实现 gate 则必须看 changed voxels、changed components、 proposal recall、full clean-reload equality、anchor-on/off 与 proposal-on/off、refiner-on/off、 prototype-on/off 是否真的改 final logits。科学比较时，才能看 Dice、HD95、remote-FP voxels、 myocardium 外 FP ratio、component count、largest-component ratio、lesion-wise recall、volume ratio、case-wise help/harm、scar-positive subgroup、T2-present edema-positive subgroup、no-T2 subgroup、CenterB、CenterC、complete tri-modal subgroup。像 empty-GT 平均收益、compact-label proxy、foreground mean 这类指标只能作诊断，不能决定 promotion。当前 Route A 合同其实已经把其中一大半原则写出来了：foreground mean、empty-GT edema averages、compact-label-only proxy improvement 都不能当路线成功标准。

checkpoint selector 不能再按单一 Dice，也不能让 HD95 或 empty-GT 支配。我的建议是固定分层选择器：

$$
S = 0.40\,\Delta \mathrm{Dice}_{\mathrm{scar-pos}}
+ 0.25\,\Delta \mathrm{Dice}_{\mathrm{ede-pos,T2}}
+ 0.15\,(-\Delta \mathrm{HD95}_{\mathrm{scar-pos,clip}})
+ 0.10\,(-\Delta \mathrm{HD95}_{\mathrm{ede-pos,T2,clip}})
+ 0.10\,(-\Delta \mathrm{remoteFP}_{\mathrm{all,clip}}).
$$

但只有在以下硬门都通过时才计算 $S$：proposal recall 不低于预设阈值；changed voxels 非零；changed components 非零；no-T2 edema correction 为零；fresh evaluation receipt 完整；case manifest SHA、prediction SHA、checkpoint SHA、evaluator commit 四者绑定齐全。如果任一 gate 不过，selector 直接判 invalid，而不是继续比较分数。之所以这样定，是因为 M10 continuation 已经证明“选择器证据一旦不 fresh”，整个 best checkpoint 都会被污染。

fresh evaluation 的防伪规则也必须写死。第一，所有 Round02 选择都必须使用 fresh --force evaluation；第二，禁止从旧 packet 或旧 CSV 抄录 metrics；第三，任何 metrics_summary.csv都必须携带 evaluator git commit、checkpoint SHA、prediction SHA、manifest SHA、timestamp 和 command receipt；第四， validator 要有 known-bad fixture：把旧 metrics 复制到新 packet、把 compact-label 结果冒充 official metric、把 submitted-only Slurm 当完成、把 no-op candidate 冒充 non-identity，这些都必须 fail closed。只有这样，Route C 才能把"evidence 与 accounting"这条路线真正做成可信控制组。

## Route A 与 Route B/C 的 Planner 修订建议

Route A 不需要被扩展成完整 SRR-v3；它需要做的是把"最小非纯 nnU-Net 候选"写得更硬。现有 Route A contract 已经相当接近目标，我建议 Planner 只做四个修订。第一，把 final-output nonidentity gate 再写得明确： changed_voxels > 0、 changed_components > 0、 temporal_on_off_changes >= 8 cases 三者必须同时满足，任何一个不满足都只能形成 honest negative/incomplete packet，不能 candidate-ready。第二，把 proposal/refiner 从"结构存在"改成"必须提供 proposal recall、proposal precision、proposal-to- final retention 与 per-case ROI receipt"；第三，把 Cine branch 的 SyNOnly 收据从 pair-level 扩展到 case- level aggregate manifest；第四，把 fallback 候选写成 conservative bounded correction，不允许 Route A 在失败后偷滑回纯锚点路径。当前 Route A 合同里关于两尺度 SRR、无 interaction experts、分病种 soft ROI、官方 CineMA 资产、6 帧采样和至少 4 个注册通过的非参考帧等部分都可以保留，不需要再重写。

Route B 则必须从"让 Controller 自己选拓扑"改成"一份无歧义科学设计"。Planner 应把 Route B 的 architecture 冻结成四尺度，每尺度都有 modality-specific encoder、shared expert、private expert、 interaction expert；scar 路由允许 shared + LGE-private + LGE-T2 + LGE-C0，edema 路由允许 shared + T2- private + LGE-T2 + T2-C0，anatomy 路由允许 shared + C0-private + LGE-C0 + T2-C0。这一 task-specific routing 逻辑其实已经在 srr_losses.py 的任务语义 regularization 里显式编码过，应直接上升为 route contract。Proposal 部分则固定用"anatomy-guided conservative cascade + prototype similarity- difference augment"；refiner 固定 scar 小 ROI / edema 大 ROI；prototype 固定为 OOF-fitted frozen bank + training-only hard-negative queue；最终输出固定为 anchored bounded correction，但要求 proposal/ refiner 改变的是 SRR logits，再由 gate 约束并体现在 final logits 上。CineMA 使用官方 asset 与 matched- random control；registration 使用 SVF + 七步 scaling-and-squaring 的 faithful first-party 实现；temporal 使用 registered temporal aggregation + full ablation map。换句话说，Route B 的 Controller 不应该再被允许"自己看看哪种 proposal 更合适"。 Route C 的定位必须坚持不变：它是 M10 follow-up2 evidence 与 Cine fidelity 路线，不是再发明 MyoPS 新模型。Planner 对 Route C 的修订重点应落在文件级 gate： route contract 里明确 inheritance 边界； executor plan 里加 fresh all-checkpoint replay、strict selector receipt、final-path intervention、D2/D3 close-out、clean reload、validator-ready packet； required evidence 里要求 real final-path intervention 逐一覆盖 anchor/proposal/refiner/prototype/registration/temporal on/off； known-bad fixtures 里加入 stale metrics reuse、 --force 缺失、single-frame wrapper、temporal inputs not consumed、registered outputs missing SHA。Route C 需要冻结的不是新科学设计，而是"如何忠实证明已冻结设计真的进入 final path"。这一点与当前 Route C 的 review 边界完全一致。

## 实现任务矩阵与未解决问题

下面这张矩阵只保留 Controller 真正需要实现、而且 Planner 现在就能冻结的任务。为了减少阅读负担，我把字段压缩成最关键的十项；其中"输入/输出"都写到足够落代码的粒度，"new training required" 只标是否需要新的正式训练，而不是 smoke test。

| task | route | exact input | exact output | source files | external dependency | implementation gate |
|---|---|---|---|---|---|---|
| proposal-conservative-cascade | A/B | routed pathology features; anatomy union; anchor entropy/components; modality evidence | per-pathology proposal logits/prob + ROI receipt | `src/care_myocardium/models/srr_propref.py`; `pathology_heads.py` | 无 | proposal recall/precision receipt |
| prototype-bank-oof-fit | B | train/OOF feature tensors + labels + availability | frozen bank checkpoint + fit receipt + category counts | `proposal_prototypes.py`; new route-local fit script | 无 | no-T2 edema negative rejection |
| scar/edema refiner | A/B | soft ROI; modality crop; anatomy prior; uncertainty; pos/neg sim | pathology-specific refined logits + retention receipt | `srr_propref.py`; `refiner/soft_roi.py` | 无 | proposal-to-refiner causal path |
| official CineMA adapter | A/B/C | per-frame SAX volume | official logits + decoder feature + entropy + provenance | route-local adapter under `src/care_myocardium/...` | official CineMA repo + HF weight | feature hook before `pred_head_dict['sax']` |
| faithful registration | A/B/C | reference frame + non-reference frames + logits/features | forward/inverse warp outputs + Jacobian/folding/inverse-error receipts | `cine/registration_model.py`; route-local rewrite | ANTsPy control; VoxelMorph math reference | 7-step scaling-and-squaring + inverse composition |
| temporal aggregation | A/B/C | registered logits/features; motion magnitude; Jacobian; uncertainty; frame quality; temporal position | final temporal logits + on/off intervention receipt | `cine/temporal_model.py`; `temporal_dictionary.py` | official CineMA features | temporal inputs consumed proof |
| fresh selector | C | checkpoint list + manifests + evaluator commit | selector report with bound SHAs | route-local eval scripts | 无 | `--force` compulsory |
| lesion-centric evaluator | A/B/C | official labels + predictions + manifests | metrics CSV + help/harm matrix + subgroup tables | route-local validation scripts | 无 | official metric only; compact proxy rejected |

真正还不能靠代码审计或文献完全回答、必须靠实验解决的问题，其实只剩很少几条。其一，Route B 的 prototype-augmented proposal 相比 no-prototype conservative proposal，是否在 220 例 MyoPS 上能稳健提高 positive-case lesion recall，同时控制 remote-FP 与 component burden；它的方向是合理的，但最终数值只能靠实验。其二，官方 CineMA decoder feature 是否在 CARE 数据分布上比 matched-random control 带来显著增益；CineMA 论文说明预训练在多任务和低数据设置上有优势，但 CARE 的 cine 标签空间和推理流程不同，仍需做严格 control。其三，registered temporal aggregation 与 reference-only / unregistered multi- frame control 比较后，是否有足够幅度的 final-output 改变与指标收益，值得保留在候选路径中。除此之外， Round02 不再需要新的科学发明，而是需要把现有设计写对、连通、验真。

```text
PROPOSAL_REFINER_RESEARCH_STATUS=READY_WITH_EXPLICIT_FALLBACK
PROTOTYPE_MEMORY_RESEARCH_STATUS=READY_WITH_EXPLICIT_FALLBACK
CINEMA_ADAPTER_RESEARCH_STATUS=READY_WITH_EXPLICIT_FALLBACK
REGISTRATION_TEMPORAL_RESEARCH_STATUS=NEEDS_TARGETED_CODE_PROBE
PLANNER_REVISION_READINESS=READY_WITH_EXPLICIT_FALLBACK
```

## 参考来源（从原 PDF 抽取并去重）

1. <https://raw.githubusercontent.com/YuukiAS/CARE_Challenge/route_C/results/20260714_srr_v3_m10_continuation_reconciliation/result.md>
2. <https://raw.githubusercontent.com/YuukiAS/CARE_Challenge/route_C/results/20260714_srr_v3_m10_continuation_reconciliation/review.md>
3. <https://raw.githubusercontent.com/YuukiAS/CARE_Challenge/route_A/prompts/routes/route_A.md>
4. <https://github.com/mathpluscode/CineMA>
5. <https://pubmed.ncbi.nlm.nih.gov/36495601/>
6. <https://raw.githubusercontent.com/YuukiAS/CARE_Challenge/main/images/SRR-v3.png>
7. <https://raw.githubusercontent.com/YuukiAS/CARE_Challenge/main/prompts/routes/handoffs/CURRENT.md>
8. <https://raw.githubusercontent.com/YuukiAS/CARE_Challenge/main/src/care_myocardium/models/pathology_heads.py>
9. <https://github.com/YuukiAS/CARE_Challenge/blob/main/src/care_myocardium/cine/cinema_adapter.py>
10. <https://raw.githubusercontent.com/YuukiAS/CARE_Challenge/route_C/wiki/history/COMPARISON.md>
11. <https://raw.githubusercontent.com/YuukiAS/CARE_Challenge/route_C/results/route_C/review.md>
12. <https://github.com/YuukiAS/CARE_Challenge/blob/main/src/care_myocardium/cine/registration_model.py>
13. <https://github.com/YuukiAS/CARE_Challenge/blob/main/src/care_myocardium/models/srr_propref.py>
14. <https://raw.githubusercontent.com/YuukiAS/CARE_Challenge/main/src/care_myocardium/models/proposal_prototypes.py>
15. <https://github.com/YuukiAS/CARE_Challenge/blob/main/src/care_myocardium/models/srr_dictionary_memory.py>
16. <https://github.com/mathpluscode/CineMA/blob/main/cinema/segmentation/convunetr.py>
17. <https://github.com/YuukiAS/CARE_Challenge/blob/main/src/care_myocardium/losses/srr_losses.py>
