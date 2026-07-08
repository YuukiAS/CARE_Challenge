# SRR Dictionary 实现审阅 TODO

## 1. 当前结论：两代 dictionary 都存在，但 M8 还没有可部署增益

我读完当前 repo 后的判断是：现在代码里其实有两代 dictionary。第一代是 `SRRMyoPSLite`，它更像概念验证；第二代是 `SRRV2MyoPSUNet` / `SRRProposeRefineMyoPS`，方向明显更正确，但最新 M8 审计显示还没有形成可部署增益。当前最新 review 的结论是 `M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED`，并且明确说不支持 route promotion、fold expansion、validation packaging/upload 或 M9。最关键的数值证据是：所有 M8 candidate 的 edema 都低于 same-split nnU-Net anchor，scar 增益很小或只能算 diagnostic-only；hard subgroup 里 CenterB、CenterC、T2-present、edema-positive 仍然 harmful 或 unresolved。

具体到数值，M8 最强的 scar candidate 也只是大约 $+0.0054$ Dice，而对应 edema 下降约 $-0.0073$；另一个 T2/CenterC edema repair 变体甚至出现 pathology-aware edema HD95 大幅恶化。`m8_candidate_failure_matrix.csv` 里可以看到，anchor edema Dice 约 $0.7114$，几个 SRR candidate edema 基本在 $0.702\sim0.704$，全部低于 anchor；scar 则从 $0.5876$ 到最高约 $0.5930$，属于很小增益，不足以作为路线成功证据。

## 2. 按模块逐项审计：dictionary 主要问题在哪里

### 2.1 Lite dictionary：私有和 interaction slot 并不真正模态私有

目前 dictionary 的第一个实质问题，是旧版 Lite 里的“私有 dictionary”和“interaction dictionary”很多时候并不是真正的模态私有。`SRRMyoPSLite` 先对三个 stem 输出做 masked fusion，然后把这个 fused tensor 送进 retrieval；而 `SRRRetrievalBlock.forward()` 里又把同一个 fused tensor 复制成 `[fused, fused, fused]` 作为三个“模态特征”。这意味着 LGE-private、T2-private、C0-private 或 interaction slot 在 Lite 路径里并没有真正看到不同模态的独立特征，它们只是对同一个 fused representation 做不同 expert 变换。这个问题会直接削弱 BR2 的核心精神，因为 BR2 要求 $\Theta_{\mathrm{LGE}}$、$\Theta_{\mathrm{T2}}$、$\Theta_{\mathrm{C0}}$ 至少在输入证据上是真正分开的。

### 2.2 Routing：偏整图级证据选择，不是病灶级候选形成

第二个问题是，当前 dictionary 的 routing 仍然偏“整图级证据选择”，不是“病灶级候选形成”。`RetrievalRouter` 的 query 主要是 fused feature 的全局均值、availability 和 anchor summary，然后输出每个 expert 的权重；这能学到“这个样本大概该看 LGE 还是 T2”，但很难学到“哪一小块心肌区域像 scar，哪一块是远端假阳性”。当前项目背景里也已经指出，SRR 不是不该做，而是不应再作为最终 dense segmentation head；它现在学到了一部分“该看哪种证据”，但还没学到 lesion formation，也就是病灶如何在空间上形成低远端假阳性、低 component burden、低 HD95 的医学合理 mask。

### 2.3 SIP-style regularizer：更像工程 coverage，不是真正跨 source integrativeness

第三个问题是 SIP-style regularizer 目前还是偏工程化的 entropy/coverage/semantic slot prior，而不是论文里那种跨 source 的 integrativeness。代码里 `retrieval_regularization()` 主要做 entropy floor、coverage MSE 到 uniform target、max-weight penalty；`semantic_retrieval_regularization()` 虽然加入 scar 偏 LGE、edema 偏 T2、interaction mass floor，但它本质还是手写语义先验，不是真正统计“这个 expert 是否被多个 availability pattern / style group / hard subgroup 稳定复用”。这会导致两个副作用：一方面，它可能把 gate 拉向看起来“均衡”的使用，而不是 clinically useful 的使用；另一方面，它很难解释为什么 CenterB/CenterC edema-positive 仍然失败。

### 2.4 Prototype proposal：方向正确，但还不是强 lesion proposal engine

第四个问题是 prototype proposal 已经写进代码，但还没有变成足够强的 lesion proposal engine。Lite 版本的 `PathologyProposalHead` 默认使用 deterministic axis prototypes，并通过 similarity difference、anchor/component evidence、anatomy prior 混入 final logits；这至少比普通 dense head 更接近“病灶 proposal”，但默认原型并不是从真实 train/OOF feature 里稳定拟合出来的医学原型。PropRef 版本明显更进一步：`ProposalDictionary` 有 scar/edema 正负 prototype、negative memory、hard FP、artifact、remote FP island 等概念，且 edema 在 no-T2 时会被强制阻断；但 M8 结果说明这些机制还没转化为 deployable gain。

### 2.5 PropRef skeleton：模块存在，但被 anchor arbitration 牵制

第五个问题是当前最正确的 PropRef skeleton 被 nnU-Net anchor arbitration 牵制得比较厉害。`SRRProposeRefineMyoPS` 已经有 modality-specific encoders、per-scale retrieval、scar/edema proposal dictionary、soft ROI refinement、baseline preserving residual gate 和 branch arbitration；这说明 Codex 至少已经不再只是偷懒写一个普通 U-Net。但是 M8 review 也说明：当它试图避免伤害 anchor 时，deployable conservative fallback 会退化成 anchor-only；当它更多使用 SRR 时，scar 只小涨而 edema 变差。也就是说，当前系统不是“没有模块”，而是 **SRR 分支没有稳定产生超过 anchor 的病灶级 correction signal**。

## 3. 当前路线判断：继续 V2/PropRef，不继续 Lite 小变体

所以，当前 dictionary **适用，但只适用于继续做 V2/PropRef 主线，不适合继续做 Lite dictionary 小变体**。`SRRV2MyoPSUNet` 已经修正了 Lite 的核心问题：它有真正的 modality-private encoder，并且每个尺度的 retrieval 直接接收 `[LGE_scale, T2_scale, C0_scale]`，文档也明确说 private retrieval experts 操作的是 modality-specific features，而不是已经平均的 fused feature。这个路径才是 BR2 医学影像版本的合理起点。

下一步我不建议让 Codex 再做 “`cross_modal_interaction_dictionary` vs `anchor_guided_dictionary` vs `hierarchical_router_dictionary`” 这种平行小实验，因为这些变体已经证明最多给 scar 很小的局部信号，不能解决 edema 和 hard subgroup。更合适的是把任务升格为四个有明确失败门的 architecture repair variants。

## 4. 下一步应该做什么

### 4.1 True-BR2 Modality Bank Repair

第一条 variant 应该叫 **True-BR2 Modality Bank Repair**。目标是彻底禁止任何 `[fused,fused,fused]` 伪模态路径进入正式模型，所有 shared/private/interaction expert 都必须在 per-scale modality features 上运行。形式上，每层 dictionary 可以写成

$$
\mathcal{D}_{\ell}
= \mathcal{D}^{\mathrm{sh}}_{\ell}
\cup \mathcal{D}^{\mathrm{LGE}}_{\ell}
\cup \mathcal{D}^{\mathrm{T2}}_{\ell}
\cup \mathcal{D}^{\mathrm{C0}}_{\ell}
\cup \mathcal{D}^{\mathrm{LGE,T2}}_{\ell}
\cup \mathcal{D}^{\mathrm{LGE,C0}}_{\ell}.
$$

这个 variant 的目的不是马上超过 nnU-Net，而是验证“真 BR2 字典”本身是否能在相同训练预算下改善 scar/edema hard subgroup；如果不能，后续就不要再用 dictionary 本体当主要卖点。

### 4.2 Lesion Proposal Dictionary Repair

第二条 variant 应该叫 **Lesion Proposal Dictionary Repair**。这里 dictionary 不再只是 feature bank，而是 scar/edema 的正负原型库。scar dictionary 应该有 $D_{\mathrm{scar}}^+$ 和 $D_{\mathrm{scar}}^-$，负类至少包括 normal myocardium、blood pool、outside myocardium、LGE bright artifact、remote FP island；edema dictionary 的负类必须只来自 T2-present safe negatives，绝对不能从 no-T2 myocardium 里挖负样本。代码里的 prototype utility 已经有这个方向：scar negative categories 和 edema T2-present negative categories 是分开的，`build_prototype_bank_from_labeled_features()` 也明确排除了 no-T2 myocardium 作为 edema negative。下一步要让 Codex 做的是：prototype bank 必须从 same-split train/OOF features 显式 fit/load；若仍是 deterministic bootstrap，训练和评估必须 fail closed。

### 4.3 Lesion-aware Router + Pattern-SIP

第三条 variant 应该叫 **Lesion-aware Router + Pattern-SIP**。现在 router query 太粗，应把 query 从全局 pooled fused feature 改成病灶条件 query：包含局部 proposal evidence、anatomy distance、anchor uncertainty、component flags、T2 feature statistics、availability pattern。对应的 SIP 也要改成 pattern-conditioned，而不是 uniform coverage。更合理的 soft integrativeness 可以定义为：对 expert $k$、任务 $t$、availability/style group $g$，统计平均使用量 $u_{t,k,g}$；共享 expert 要跨多个 $g$ 有稳定覆盖，LGE-private/T2-private expert 只在对应模态存在时纳入覆盖，interaction expert 只在 pair 有效时纳入覆盖。这样才更接近论文里 $\gamma_d=\sum_s I(\beta_d^{(s)}\neq 0)$ 的精神，而不是单纯让每个 expert 都平均被用到。论文原始 SIP 的意义就是鼓励 representer 被多个 source 检索，同时保持部分共享结构；直接对应到我们的医学分割版，就应该是“跨 availability/style/hard subgroup 的软复用”，而不是 batch 内均匀用完所有 slot。

### 4.4 T2-present Edema Proposal Recall Repair

第四条 variant 应该叫 **T2-present Edema Proposal Recall Repair**。M8 失败最明显的是 edema，不是 scar。当前 edema 的 no-T2 safety 是做对了，但 T2-present edema-positive / CenterB / CenterC 仍然不稳定。因此下一步不能只是给 T2 多加几个 private slot，而要强制 edema proposal recall 先过关。训练上应该把 T2-present edema-positive case 分层采样，按 CenterB/CenterC、病灶大小、T2 强度和 anchor error 类型建 batch；loss 里加入 edema proposal recall floor，但仍然保持 no-T2 edema logits/export 阻断。这个 variant 的成功门不应只看 mean Dice，而要看 T2-present edema-positive 的 proposal recall、HD95、remote FP、component count 是否同时改善。

## 5. 优先级和冻结路线

如果要把这几个 variant 排优先级，我建议先做 **Lesion Proposal Dictionary Repair** 和 **T2-present Edema Proposal Recall Repair**，而不是先做更大的 backbone 或更复杂的 interaction dictionary。原因很直接：当前已有 M8 证据表明，SRR 对 scar 有微弱正信号，但 edema 拖垮整体；而项目背景也明确指出，SRR 已经会做 evidence selection，却没有形成 lesion proposal。继续改 dictionary slot 数量无法根治这个问题。真正需要验证的是：正负 prototype、hard-negative replay、soft ROI refiner、T2-safe edema supervision 能不能把 evidence selection 转成 lesion formation。

我会建议暂时冻结三类路线。第一，冻结 `SRRMyoPSLite` 的 dictionary topology 小变体，除非作为 sanity control；它的 fused-duplicate 结构不适合作为正式 BR2 extension。第二，冻结“在当前 full-image dense head 上继续堆 compactness/containment loss”的路线，因为没有 proposal 的 compactness 很容易牺牲 recall 换一点 HD。第三，冻结任何把 no-T2 myocardium 当 edema negative 的路线；这一点当前代码大体已经做对了，后面不要回退。
