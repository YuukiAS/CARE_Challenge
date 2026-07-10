# loss 与优化目标

> 历史快照：M08。本页只保存从 `TODO.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

### 1.8 Loss：有很多 loss，但 M8 变体 loss weight 可能严重 miswired

这是我这次最重要的代码发现之一。M8 的 `m8_variant_config_contract.json` 给每个 variant 定义了不同 loss weights，比如 `baseline_preservation`、`component_proposal`、`edema`、`proposal`、`prototype_margin`、`roi`、`roi_remote`、`scar`、`semantic_retrieval` 等。 不同变体也确实有不同配置，例如 scar precision 变体和 T2/CenterC edema 变体的 loss weights 明显不同。

训练脚本的 `apply_variant_config_contract` 会把这些 JSON 里的 loss weights 写进 `args.scar_weight`、`args.edema_weight`、`args.proposal_weight`、`args.margin_weight` 等。 但问题在于：M8 变体走的是 `srr_m6_expanded_total_loss` 路径，而 `propref_loss` 调用它时**没有把这些 args weights 传进去**。源码是：

`total, m6_metrics = srr_m6_expanded_total_loss(outputs, labels, availability, detach_metrics=detach_m6_metrics)`

也就是没有传 `weights=...`。 而 `srr_m6_expanded_total_loss` 里面如果没有传 weights，就用默认 component weights。

这意味着一个很严重的可能性：**M8 JSON 里那些看起来很精细的 loss-weight variant 设计，可能大部分没有真正作用到 expanded loss。** 这不是小问题。它会让三个变体的“配置差异”主要落在 model variant / encoder / dictionary config / sampler / threshold 上，而不是预期的 loss schedule 上。Codex 如果据此说“loss 也试了，没潜力”，这个结论我不接受。先修这个 wiring，再谈 loss 有没有用。

---

### 1.10 Training budget：不是 smoke，但仍不等于完整路线验证

公平地说，M8 不是 6-step smoke。`m8_training_budget_ledger.csv` 显示 4 个 included training run，每个约 7200 秒，optimizer steps 大约 50k 级别，validation events 20–30。 M8 review 也确认总 train-loop seconds 是 `28800.190`，并且有 110 validation events。

所以不能简单说“没训”。但它仍然不是完整路线验证。原因有三个：第一，loss config 可能 miswired；第二，checkpoint selection 不是 metric/hard-subgroup selection；第三，最终输出被 anchor-first residual arbitration 限制。训练时间真实，不代表训练的是我们真正想验证的系统。

---

## 3. 为什么“按照挑战赛难点设计”仍然可能没涨分

这件事并不矛盾。一个设计方向抓住了难点，但实现方式可能仍然失败。CARE 的难点是缺模态、中心偏移、T2 edema、远端 FP、HD95、cine temporal evidence。M8 确实围绕这些词写了模块；但从代码看，有些模块被实现成了“保守 residual around nnU-Net”，有些 loss 没按 variant contract 生效，有些 selection gate 和评价指标错位。

换句话说，当前模型不是“SRR 正面打败 nnU-Net”的系统，而是“nnU-Net 输出上加一个被安全门控限制的 SRR 修正”。这种架构天然很容易出现两种结果：打开太少，就几乎等于 anchor；打开多一点，就在 edema 上引入不稳定。M8 follow-up 的 policy table 正好复现了这个模式：conservative proxy fallback 启用 SRR 的 case 数是 0，完全退回 anchor；high-SRR fallback 启用 SRR 后 scar 小涨，edema 仍掉。

这不是“挑战赛难点不存在”。这是“当前实现没有把 SRR 做成主证据生成器，而是做成保守修补器”。

---

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
