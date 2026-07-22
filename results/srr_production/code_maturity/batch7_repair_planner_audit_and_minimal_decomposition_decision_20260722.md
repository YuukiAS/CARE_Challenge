# Batch 7 repair Planner 审计与最小分解决定

## 总判断

Batch 7 repair 比原 Batch 7 真实得多：独立 44 例干预、identity 零变化、真实语义记忆、无 anchor 的 discovery 检查和 600 步 proposal 训练都已实际完成。因此这次不能再简单归因于“所有结果都是占位”。但是，Controller 所称的 `proposal-only` 阶段仍没有按合同形成纯净的 proposal 科学实验：stage wrapper 传入空 loss 配置，M10 训练入口继续启用历史混合损失；梯度验收也只是对 proposal logits 均值反向传播，而不是验证正式训练 loss 的方向。与此同时，真实干预已经显示 semantic negative memory 对 scar 几乎无益、对 edema 反而略有伤害，prototype maps 的收益很小，scar proposal 在所有真实模式下持续为负。因此当前结论应拆成两部分：Codex 仍未完整实现“纯 proposal 目标”，但当前复杂 dictionary/proposal 设计本身也已经暴露出低杠杆和病种冲突。

## 已经真实完成的部分

原 Batch 7 的复制表问题已修复。`anchor_identity` 和 `production_gate_closed` 在全部 44 例上均为零变化；不同 intervention 有独立预测和不同结果。真实 category memory 已覆盖 scar/edema 的正例与多类负例，记录病例、数量、valid mask 和 tensor hash，并保持 validation zero leakage。Discovery 在被测试病例中对 confirmation anchor context 保持不变，而 confirmation 会变化。

这些证据说明本轮工程修复并非完全失败，不能再把低分全部归因于假实现。

## Codex 仍未实现到位的关键点

### 1. 所谓 proposal-only 训练仍不是纯 proposal 目标

`scripts/training/run_srr_batch7_repair_stagewise.py` 对 proposal stage 使用 `proposal_only_gate_one` 并冻结 refiner、arbiter 和 production gate，但传给正式训练入口的是：

```text
--loss-weight-json {}
```

M10 variant 的 `propref_loss` 不使用普通 stage 分支，而始终进入 `srr_m6_expanded_total_loss`。空权重会启用历史默认项，包括 refiner loss、anchor preservation、correction opportunity、branch arbitration、bounded correction、remote-FP、dictionary balance、Pattern-SIP、prototype margin、memory alignment 和 refiner-effect；相反，新的 discovery/confirmation direct losses 默认仍为零。冻结 refiner 不会切断 refiner output 对 proposal 的梯度，因此 proposal 参数仍会被下游历史目标牵引。

因此 600 步结果不能被解释为“明确训练 anchor-free discovery 和 proposal 后仍失败”，只能解释为“在冻结部分模块后，继续用混合 M10 loss 微调 proposal 相关参数仍不足”。

### 2. 梯度验收没有验证正式 loss

`run_srr_batch7_repair_implementation_checks.py` 使用：

```text
out[loss_key].float().mean().backward()
```

它只证明 proposal logits 与参数相连，不证明正式 proposal loss、memory loss、remote-FP loss 或 discovery/confirmation loss具有正确方向。Validator 没有要求一份 resolved stage loss 权重表，也没有检查所有非 proposal 项在 proposal stage 必须为零。

### 3. Anchor-free discovery 检查覆盖不足

实现检查默认只取验证集前两个病例，当前实际是 `Case1002` 和 `Case1007`，均为 LGE-only。Edema 在无 T2 情况下被硬归零，因此当前测试没有验证 T2-present edema discovery，也没有覆盖完整多模态的 CenterB/CenterC 病例。Scar 的检查有意义，但还不能证明整个多模态 discovery 路径都满足合同。

## 已经指向具体设计问题的证据

### 1. Semantic negative memory 目前没有产生正收益

同一 Batch 7 checkpoint 的真实 intervention 中，关闭 semantic negative memory 后 edema 正例 Dice 从约 `+0.00562` 提高到 `+0.00624`，scar 基本不变，说明当前 negative memory 至少没有帮助最终分割，甚至可能过度压制 edema。

### 2. Prototype maps 和空间 dictionary 的最终杠杆很小

关闭 prototype maps 后，edema 从约 `+0.00562` 降至 `+0.00488`，贡献约 `+0.00074`；scar 则几乎不变且仍为负。连接已经真实存在，但当前效果远不足以支撑 16-slot dictionary 作为核心性能来源。

### 3. Scar 与 edema 的目标明显冲突

600 步过程中，edema 从 `+0.00346` 上升并停在 `+0.00444`；scar 从 `-0.00412` 恢复到 `-0.00200`，但始终为负。Scar 的 HD95有所改善，却伴随 Dice 下降；T2-present scar 和 CenterC scar 伤害更明显。这说明共享 dictionary、共享 proposal 训练和统一负空间对两个病种并不合适。Edema 有可保留的小幅信号，scar 当前链路则在系统性删除或错改真实小病灶。

### 4. Source arbiter 和 refiner 不能挽救坏 proposal

真实 intervention 中 scar 的 proposal-only、refiner-only、learned-source 和 gate-one 全部为负；no-anchor 仍严重崩溃。当前问题已经发生在候选生成之前或候选生成本身，继续训练 refiner、arbiter 和 gate只会掩盖根因。

## 目标达成度

本轮达成了“证据真实性修复”和“真实 proposal stage 运行”，但没有达成“纯 proposal 科学验证”。因此：

```text
operational completion: PASS
truthful intervention infrastructure: PASS
semantic memory provenance: PASS
pure proposal objective authority: FAIL
scar proposal scientific signal: FAIL
edema proposal scientific signal: SMALL_POSITIVE
complex dictionary value: UNPROVEN_TO_NEGATIVE
full architecture rejection: NOT_AUTHORIZED
```

## 下一步决定

不再继续完整 Batch 7 系统，也不启动 Batch 8。只允许一次最终的最小病种分解，用来回答两个问题：

1. 冻结通用 encoder/retrieval 后，一个不带 spatial dictionary、semantic memory、refiner、arbiter 和 gate 的最小 scar/edema proposal，是否本身能比 nnU-Net anchor 更好？
2. 在相同训练和采样下，加入 prototype maps/spatial dictionary 是否能稳定贡献至少 `+0.001` Dice？

必须先修复纯 loss authority，再分别训练四个匹配实验：scar minimal、scar dictionary、edema minimal、edema dictionary。不得把两个病种合并成一个 mean gate决定是否保留。若 scar minimal 仍为负，则停止 scar SRR correction，挑战赛中保留 nnU-Net scar；若 edema minimal 达到 `+0.003`，则允许保留简化 edema proposal。某病种的 dictionary 只有在相对 minimal 额外提高至少 `+0.001` 且安全指标不恶化时才能保留，否则删除。

这次最小分解后不再允许继续完善同一复杂组件。它是当前 dictionary/proposal 路线的最终保留或删除判定。