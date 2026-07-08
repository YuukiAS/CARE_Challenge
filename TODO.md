# SRR-v3 / M8 实现审阅 TODO

## 1. 按模块逐项审计：哪些做到了，哪些没做到位

### 1.1 Availability / no-T2 safety：基本落实，但只解决了安全，不解决性能

这部分实现相对扎实。`t2_masked_edema_loss` 只在 T2-present 样本上计算 edema dense supervision；如果 batch 里没有 T2-present，就返回零损失而不是把 no-T2 当 edema-negative。 模型 forward 里也多次把 no-T2 的 edema proposal/logits 设为强负值 `-20.0`，例如 proposal dictionary 和最终 arbitration 都有 no-T2 block。

这说明 Codex 没有完全偷懒成 naive zero-fill。但 no-T2 safety 只能防止一种错误：不要把缺 T2 当作 edema negative。它不能自动学会 CenterB/CenterC 的 T2-present edema。M8 的失败恰好在 T2-present/edema-positive/CenterB/CenterC 上，所以这不是 safety 没做，而是**edema 表示、proposal 和 refiner 没学出有效增益**。

### 1.2 Modality encoder + retrieval dictionary：有实现，但不等于完整 SRR 语义检索系统

代码里确实有多尺度 shared/private/interaction dictionary。`dictionary_slot_config` 定义了 shared slots、LGE/T2/C0 private slots，以及 LGE-T2、LGE-C0、T2-C0 interaction slots；`GroupedExpertBank` 里这些 slot 都是 trainable conv expert；router 输入包含 pooled features、availability 和 nnU-Net anchor summary，并且会 mask invalid modality slots。

这部分说明“dictionary 骨架”是真有的，不是纯 CSV。但问题在于它目前更像一个 **MoE-style multi-slot fusion block**，而不是完全实现了我们图里的“semantic representation retrieval bank”。它的 semantic prior 是软正则；slot usage 有诊断；但是目前没有证明这些 slots 学到了稳定的、可解释的 lesion-forming representation，也没有证明禁用/启用 dictionary 会在最终 label 上产生预期差异。M8 review 只是说 architecture gap closure table 全部 closed with runtime evidence，但最后同一划分候选仍不能超过 anchor。

更重要的是，当前 route 评估没有做一个真正强的 causal ablation：例如 “same architecture without dictionary / without interaction / without semantic regularizer / without prototype memory / without refiner” 在同一 split、同一训练预算下逐项比较。这意味着我们现在只能说 dictionary 参与了 forward 和 training，不能说 dictionary 的科学价值被充分检验。

### 1.3 Prototype / negative memory：有真实 train/OOF fitting，但不是我们想象中的强 memory bank

代码里有 prototype bank，不是完全假的。`build_prototype_bank_from_labeled_features` 会从 train/runtime features 中提取 scar positive/negative、edema positive/negative，并且明确限制 edema positive 和 safe-negative 只来自 T2-present 样本，no-T2 myocardium 不进入 edema negative。 它也区分 normal myocardium、blood pool、outside myocardium、hard FP、artifact 等 negative 类别。

训练脚本确实会在正式 model 上 fit and load runtime prototype bank：它选择 T2 edema-positive cases、lesion cases 或其他 train cases，取 `_evidence_features`，调用 `build_prototype_bank_from_labeled_features`，再把 scar/edema prototypes load 到 model dictionary。

但这里有一个很大的 fidelity 问题：`ProposalDictionary` 里的 positive/negative prototypes 是 `register_buffer`，不是 `nn.Parameter`；`load_prototype_bank` 只是把 fitted prototype 拷贝进去。 也就是说，prototype vectors 本身不是一个在线可训练 memory bank。它们更像初始化后固定的 class anchors。后续 prototype margin loss 主要推动 feature/embedding 去适配这些固定 prototypes，而不是让 prototype memory 自身持续学习。`prototype_parameters()` 试图跟踪 prototype 相关参数，但由于 positive/negative 是 buffer，不是 parameter，它真正能跟踪更新的主要是 embedding/conv_score 一类参数。

所以我会这样定性：**prototype bank 有，但不是强 memory/prototype learning；hard-negative memory 有类别设计和 replay 入口，但不是完整的 iterative hard-negative mining system。**

### 1.4 Anatomy prior：有实现，但仍然依赖内部 anatomy head 和 anchor context，没有被证明是强解剖定位器

`AnatomyDistanceROIPrior` 确实实现了 `p_union`、`p_lv`、`p_rv`、union/LV/RV distance、uncertainty、scar/edema soft gate，并且 no-T2 时把 edema gate 置零。 forward 里 proposal/refiner 都消费这些 anatomy context：scar/edema dictionary 接收 task-specific anatomy soft gate logits，refiner 接收 P_union/P_LV/P_RV、distance map、uncertainty 和 task gate channel。summary 里也把 anatomy distance ROI prior 标记为 runtime consumed。

但它的强度仍然有限。它不是 CineMA/CorSeg 这种外部强 anatomy teacher，也不是一个充分训练的独立 anatomy-first cascade。它是同一个小模型内部 anatomy head 预测出的 soft prior，再叠加 nnU-Net anchor uncertainty/context。这个设计比纯后处理强，但没有证明“anatomy prior 本身”解决了 lesion localization。M8 子组结果显示 edema-positive/T2-present 仍然下降，说明 anatomy prior 没有把 edema 支撑区域学好。

### 1.5 Proposal：有公式、有 logits、有 prototype similarity，但可能被 anchor/context 和保守 gate 稀释

`ProposalDictionary.forward` 的 proposal 不是空壳。它计算 positive similarity、negative similarity、memory negative similarity，然后组合 learned conv score、evidence logits、anchor evidence、component evidence、anatomy prior。核心形式接近：

$$
\begin{aligned}
z_{\text{proposal}} ={}&
r
+ 2.5(s_{+}-s_{-})
+ 0.45z_{\text{evidence}} \\
&+ 0.35\,\mathrm{logit}(a_{\text{anchor}})
+ 0.30\,\mathrm{logit}(c_{\text{component}})
+ 0.20 A_{\text{anatomy}} .
\end{aligned}
$$

代码上就是 `conv + 2.5*(pos_sim - neg_sim) + evidence_logits + anchor/component/anatomy terms`，并且 edema no-T2 直接 block。

问题是，proposal heavily consumes nnU-Net anchor/component evidence。它不是纯 SRR image evidence proposal。nnU-Net 在这里不仅是 context，它直接进入 proposal logits 的重要项。这样做安全，但容易让 SRR 成为“围绕 anchor 小幅修补”的系统，而不是主角。

### 1.6 Soft ROI refiner：有实现，但实际是小 crop residual，不是完整 lesion formation engine

`CropSoftROIRefinementHead` 是实打实实现了的。它先用 proposal、proposal context、anchor evidence、component evidence、anatomy gate、uncertainty、distance support 形成 soft ROI；然后对每个 case 取 bounded crop，把 features、原图 modality crop、evidence logits、proposal logits、anatomy prior、anchor/component evidence、pos/neg similarity、uncertainty、distance、ROI、P_union/LV/RV、distance maps、task gate 等一大串输入拼起来，跑一个小 conv residual head，再 paste 回 crop。

这不是“完全没做 refiner”。但它的能力边界很窄：它是局部 residual，不是一个新的 full-resolution lesion generator；它的输出最终还要经过 baseline-preserving arbitration；如果 proposal 或 gate 不打开，它的作用就被稀释。M8 follow-up 的 proxy table 就显示 conservative fallback 根本没有启用 SRR case，高信号 fallback 启用了也只给 scar 微弱收益、edema 伤害。

### 1.7 Branch arbitration / final output：这是当前最接近“nnU-Net 做主角”的地方

这部分是我最不满意的实现。代码里有 `BaselinePreservingResidualGate` 和 `BranchArbitrationGate`。最终形式本质上是：

$$
z_{\text{final}} =
z_{\text{anchor}} + \Delta z_{\text{branch}} ,
$$

其中 $z_{\text{anchor}}$ 是 nnU-Net anchor logits，$\Delta z_{\text{branch}}$ 是 SRR/proposal/refiner 的 bounded delta。`BranchArbitrationGate` 里明确先构造 bounded delta，然后 `final = anchor_logits + branch_delta`。 SRRProposeRefineMyoPS forward 里 M6/M8 变体最终选择的是 arbitration 的 `final_logits`，否则是 baseline gate。

这比“静默 fallback”好，因为它确实导出 branch weights、correction mask、proposal/refiner delta 等证据。但从路线精神看，这已经把 nnU-Net 放得太中心了。尤其 `BranchArbitrationGate` 的 gate 初始化是 closed-biased：`context_gate.weight` 初始化为 0，bias 为 `-1.2` 或 `-2.0`，也就是一开始就倾向小开口。 再加上 anchor preservation、bounded correction、patch loss selection，SRR 很容易永远只做很小的残差修补。这样得出“SRR 没潜力”是不公平的；更准确是：**当前实现把 SRR 放在 anchor 的笼子里，没证明它能独立形成 lesion mask。**

这直接触碰你说的底线：nnU-Net 不能是主角。当前 repo 规则也要求 SRR 不能退化为普通 nnU-Net 后处理或隐藏 identity。 当前实现不是普通后处理，但它仍然是“anchor-first residual correction”。下一轮必须把 nnU-Net 从 final decision 主体降级为 context/teacher/safety source。

### 1.8 Loss：有很多 loss，但 M8 变体 loss weight 可能严重 miswired

这是我这次最重要的代码发现之一。M8 的 `m8_variant_config_contract.json` 给每个 variant 定义了不同 loss weights，比如 `baseline_preservation`、`component_proposal`、`edema`、`proposal`、`prototype_margin`、`roi`、`roi_remote`、`scar`、`semantic_retrieval` 等。 不同变体也确实有不同配置，例如 scar precision 变体和 T2/CenterC edema 变体的 loss weights 明显不同。

训练脚本的 `apply_variant_config_contract` 会把这些 JSON 里的 loss weights 写进 `args.scar_weight`、`args.edema_weight`、`args.proposal_weight`、`args.margin_weight` 等。 但问题在于：M8 变体走的是 `srr_m6_expanded_total_loss` 路径，而 `propref_loss` 调用它时**没有把这些 args weights 传进去**。源码是：

`total, m6_metrics = srr_m6_expanded_total_loss(outputs, labels, availability, detach_metrics=detach_m6_metrics)`

也就是没有传 `weights=...`。 而 `srr_m6_expanded_total_loss` 里面如果没有传 weights，就用默认 component weights。

这意味着一个很严重的可能性：**M8 JSON 里那些看起来很精细的 loss-weight variant 设计，可能大部分没有真正作用到 expanded loss。** 这不是小问题。它会让三个变体的“配置差异”主要落在 model variant / encoder / dictionary config / sampler / threshold 上，而不是预期的 loss schedule 上。Codex 如果据此说“loss 也试了，没潜力”，这个结论我不接受。先修这个 wiring，再谈 loss 有没有用。

### 1.9 Checkpoint selection：实现与配置声明不一致

M8 config 里写了很具体的 checkpoint selection rule，例如 scar precision 变体写“best same-split scar Dice/HD95 guard”，T2 CenterC edema 变体写“best T2-present edema subgroup subject to no-T2 safety”。

但训练代码实际 checkpoint best 是根据 `val_patch_loss` 更新的。训练 loop 在 scheduled validation step 上跑 `validate_patch_loss`，然后如果 `val_loss < best_val` 就保存 `checkpoint_best.pt`。 这和 leaderboard-facing 的 Dice/HD95/hard subgroup guard 不是一回事。后面确实导出了 full-case eval，但 checkpoint selection 已经由 patch loss 决定了。

这也是一个关键偏差。我们要优化的是 scar/edema 的 final label、HD95、remote FP、component burden、CenterB/CenterC/T2-present hard subgroup，而不是 patch loss。Codex 这版在“训练选择机制”上没有完全按挑战赛目标实现。

### 1.10 Training budget：不是 smoke，但仍不等于完整路线验证

公平地说，M8 不是 6-step smoke。`m8_training_budget_ledger.csv` 显示 4 个 included training run，每个约 7200 秒，optimizer steps 大约 50k 级别，validation events 20–30。 M8 review 也确认总 train-loop seconds 是 `28800.190`，并且有 110 validation events。

所以不能简单说“没训”。但它仍然不是完整路线验证。原因有三个：第一，loss config 可能 miswired；第二，checkpoint selection 不是 metric/hard-subgroup selection；第三，最终输出被 anchor-first residual arbitration 限制。训练时间真实，不代表训练的是我们真正想验证的系统。

### 1.11 CineMA / Cine registration：只是诊断性 proxy，不是完整 Cine route

Cine 这条线也没有“全部实现到位”。`run_srr_v3_m7_cine_registration_repair.py` 的 docstring 明确说它是 bounded diagnostic repair attempt，读取 existing CineMyoPS safe cases 和 CineMA frame predictions，跑小规模 SimpleITK Demons non-reference registration probe；它不训练 VoxelMorph、不打包 validation、不 upload、不 promotion。

脚本里确实实现了 SimpleITK Demons 和 ANTsPy SyNOnly registration，选择 frame0 和 non-reference frames，评估 myocardium/LV Dice、HD95、NCC 等。  后续所谓 temporal dictionary 是从 cached warped segmentation proxy 构造的，核心是把 warped non-reference segmentation proxy 和 fixed frame 做 quality-weighted union / temporal proxy，并记录 CineMA label-space caveat。

这说明 CineMA 被用作 frame-wise anatomy proxy，registration 被用作 diagnostic temporal evidence；但它不是一个完整的 CineMA fine-tuned model，也不是一个端到端 cine temporal segmentation route，更不是 VoxelMorph-based motion branch。M8 review 也承认 Cine evidence 已经不只是 smoke，但仍然是 local proxy evidence，不能 claim hosted metric readiness。

所以 Cine 不能被判“路线没潜力”。当前只能说：**CineMA + registration 还停留在证据闭环/诊断 proxy 层，没有落实成最终输出模型。**

---

## 2. 我对 Codex 当前实现的信任结论

我不认为 Codex 这次只是“随便写了个完全假的架构”。代码量和结构确实存在，M8 也不是纯烟测。它实现了不少 SRR-v3 图里的模块：availability-aware routing、多尺度 dictionary、prototype proposal、soft ROI refiner、anatomy distance prior、no-T2 safety、branch arbitration、训练日志、validator、自测。

但我也不认为它有资格说“路线没潜力”。原因是：它实现的是一个**过度保守、过度 anchor-centered、部分配置 miswired 的候选族**。尤其这几个问题非常关键：

第一，M8 的 loss-weight contract 很可能没有真正作用于 expanded loss。变体配置写得很漂亮，但 `srr_m6_expanded_total_loss` 没拿到这些 weights。这个问题不修，所有关于“loss 试过了”的结论都不可信。

第二，最终输出以 nnU-Net anchor 为中心：代码明确是 $z_{\text{final}}=z_{\text{anchor}}+\Delta z_{\text{branch}}$。这不是完全违背“anchor/context/safety”的规则，但已经太接近“nnU-Net 主角，SRR 修补”。

第三，checkpoint best 用 patch loss，而不是 hard subgroup Dice/HD95/remote-FP guard。这个选择会让训练目标和比赛目标错位。

第四，prototype bank 是一次性 fit 后作为 buffer 使用，不是强 memory bank；negative-space 有设计，但不是完整 iterative hard-negative mining。

第五，CineMA/registration 只是 diagnostic proxy，不是完整 Cine branch。

所以我会把当前状态定为：

**M8/M8 follow-up 不支持继续扩展当前候选；但不能作为 SRR-v3 科学路线失败证据。下一步必须是 implementation fidelity repair，而不是 route abandonment。**

---

## 3. 为什么“按照挑战赛难点设计”仍然可能没涨分

这件事并不矛盾。一个设计方向抓住了难点，但实现方式可能仍然失败。CARE 的难点是缺模态、中心偏移、T2 edema、远端 FP、HD95、cine temporal evidence。M8 确实围绕这些词写了模块；但从代码看，有些模块被实现成了“保守 residual around nnU-Net”，有些 loss 没按 variant contract 生效，有些 selection gate 和评价指标错位。

换句话说，当前模型不是“SRR 正面打败 nnU-Net”的系统，而是“nnU-Net 输出上加一个被安全门控限制的 SRR 修正”。这种架构天然很容易出现两种结果：打开太少，就几乎等于 anchor；打开多一点，就在 edema 上引入不稳定。M8 follow-up 的 policy table 正好复现了这个模式：conservative proxy fallback 启用 SRR 的 case 数是 0，完全退回 anchor；high-SRR fallback 启用 SRR 后 scar 小涨，edema 仍掉。

这不是“挑战赛难点不存在”。这是“当前实现没有把 SRR 做成主证据生成器，而是做成保守修补器”。

---

## 4. 下一步应该做什么

我建议下一步不要直接训练新大实验，也不要让 Codex 继续自由发挥。下一步应该是一个**强制 fidelity repair milestone**，目标不是涨分，而是先把“我们真正想验证的 SRR 系统”修到位。只有 fidelity 过了，后面的训练结果才有解释价值。

第一件事，修 loss wiring。必须让 `m8_variant_config_contract.json` 里的 component loss weights 真正进入 `srr_m6_expanded_total_loss`。同时加一个 unit test：把某个 component weight 设为 0 和设为 10，检查 total loss 和对应梯度确实变化。没有这个测试，不允许再说“loss 试过了”。

第二件事，修 checkpoint selection。不能再用 patch loss 选 best。下一轮至少要在 scheduled checkpoints 上跑 same-split full-case 或 bounded full-volume eval，按 scar/edema 分开，结合 Dice、HD95、remote FP、component count、CenterB/CenterC/T2-present/no-T2 guardrail 选择 best。patch loss 只能做训练 sanity，不能做 leaderboard-facing selection。

第三件事，降级 nnU-Net 的地位。nnU-Net 可以继续作为 context、teacher、uncertainty source、safety source、anatomy/anchor feature，但不能作为默认 final logits 主体。当前 $z_{\text{final}}=z_{\text{anchor}}+\Delta z$ 的范式要改成 SRR 主输出为主，nnU-Net 只作为辅助输入和损失正则。可以保留一个单独的 safety fallback mode，但它不能是 candidate 的常规输出路径。否则我们永远只是在测试“nnU-Net 可否被小修补”。

第四件事，做 causal ablation，而不是只报总分。必须在同一 split、同一训练预算下至少比较：SRR-main 无 final anchor、SRR-main + anchor context、SRR-main + prototype、SRR-main + prototype + refiner、当前 anchor-residual 版本、anchor-only。每个 variant 必须报告 final label 差异率、proposal/refiner 对最终 logits 的贡献、scar/edema 分项、困难子组、no-T2 safety。没有 causal ablation，就不能知道哪个模块真的有效。

第五件事，重做 prototype/memory。短期可以先不做复杂 memory，但必须至少让 prototype bank 的状态可审计：来源、case 数、positive/negative counts、T2-present edema counts、hard-negative counts、是否 deterministic fallback、是否更新。更强版本应该做 EMA prototype 或 learnable prototype 参数，而不是一次性 buffer。并且 hard-negative mining 不应只是读取一个旧 CSV，而应有一轮“由当前模型误报产生 hard negatives → 安全过滤 → 回灌训练”的闭环。

第六件事，refiner 要从“crop residual”升级为真正 lesion formation 模块。现在 refiner 是局部 residual head，但最终受到 anchor arbitration 限制。下一步要强制记录：proposal recall、proposal precision、soft ROI GT coverage、outside-myocardium ROI ratio、refiner residual 是否改变 final label、refiner disabled 后的 metric delta。只有当这些指标证明 refiner 真的在 lesion 上工作，才能说 refiner 被验证。

第七件事，Cine 另立为 anatomy-first temporal route，不要把当前 proxy 当完成。CineMA 应该作为 frame-wise anatomy teacher/backbone 或 feature extractor，ED/reference registration 应该用于把 non-reference evidence warp 到 reference space，temporal aggregation 必须影响最终 `CineMyoPS` output。当前 Demons/SyNOnly + CineMA segmentation proxy 是有用诊断，但不能替代 Cine route。VoxelMorph 未训练/未验证时不能 claim ready。
