# Batch 7 repair Planner 审计与轻量 BR2 分解决定

## 总判断

Batch 7 repair 比原 Batch 7 真实得多：独立 44 例干预、identity 零变化、真实语义记忆、无 anchor 的 discovery 检查和 600 步 proposal 训练都已实际完成。因此这次不能再简单归因于“所有结果都是占位”。但是，Controller 所称的 `proposal-only` 阶段仍没有形成纯净的 proposal 科学实验：stage wrapper 传入空 loss 配置，M10 训练入口继续启用历史混合损失；梯度验收也只是对 proposal logits 均值反向传播，而不是验证正式训练 loss 的方向。与此同时，真实干预已经显示当前 semantic negative memory、prototype maps 和 16-slot spatial dictionary 的性能杠杆很小，scar proposal 持续为负。

需要修正此前“删除 dictionary”的表述：应淘汰或保留的是当前复杂 prototype/spatial dictionary 实现，不是放弃 Representation Retrieval Learning（R2/BR2）的论文主线。下一步必须比较普通 pathology proposal 与一个轻量、可解释、availability-masked 的 representer dictionary，并单独检验 Selective Integration Penalty（SIP）是否有增量价值。

## 当前实现中 SIP 的真实状态

当前 `src/care_myocardium/losses/srr_losses.py` 仍包含：

```text
semantic_retrieval_regularization
pattern_sip_integrativeness_loss
```

它们没有被删除，但已经不等同于论文 SIP：

- `semantic_retrieval_regularization` 使用人工设定的 scar/LGE、edema/T2 槽位先验、覆盖度和 interaction floor；
- `pattern_sip_integrativeness_loss` 对单个 batch 的平均 gate 使用量计算伪 gamma、KL、熵和 collapse；
- 两者没有直接定义论文中的 source-specific learner coefficient $\beta_d^{(s)}$，也没有跨数据源计算同一 representer 的 integrativeness。

因此这两个 loss 只能作为历史启发式正则，不能继续命名或解释为论文 SIP。新的正式实验中必须将它们权重固定为零，并由 validator 拒绝任何非零配置。

## SIP 的保留、删除与修改决定

决定为：**保留 SIP 思想，删除其当前启发式代理作为正式论文证据，并实现一个更忠实的 BR2-SIP。**

训练 source 定义为模型推理时同样可确定的 observed-modality pattern：

```text
s1 = LGE-only
s2 = LGE+C0
s3 = LGE+T2+C0
```

轻量 representer dictionary 只包含少量真实可训练模块：

```text
shared anatomy
LGE private
C0 private
T2 private
LGE-C0 interaction
LGE-T2 interaction
T2-C0 interaction
```

每个 source pattern 有一组 availability-masked learner coefficients $\beta_d^{(s)}$。无效 representer 必须在 softmax/sparse gate 前 hard-mask；source pattern 只来自 availability，不允许将 center 输入 router。图像条件 residual 可以存在，但 SIP 只作用于可审计的 source-level learner coefficients。

对 representer $d$，令 $O_d$ 为能够观察其所需模态的 source patterns，使用论文式连续松弛：

$$\widetilde\gamma_d(\tau)=\sum_{s\in O_d}\min\left(1,\frac{|\beta_d^{(s)}|}{\tau}\right),$$

$$P_{SIP}=\sum_{d:|O_d|>1}\min\left(1,\frac{|O_d|-\widetilde\gamma_d(\tau)}{|O_d|-1}\right).$$

$|O_d|\le 1$ 的模块没有跨 source 可整合性，必须排除在 SIP 外。每个 source 的 $\ell_1$ 稀疏项负责少量检索，SIP 负责鼓励同一 representer 被多个可观察 source pattern 共同检索。两者不能被 generic entropy/load-balance loss 替代。

## 已确认的执行与设计问题

1. Batch 7 repair 的 proposal stage 使用空 `--loss-weight-json {}`，历史 refiner、anchor preservation、arbitration、bounded correction、dictionary regularization、Pattern-SIP、prototype/memory 等默认项仍可能参与；新的 discovery/confirmation direct losses默认却为零。
2. 梯度验收对 logits 均值 backward，只证明连接，不证明正式 loss authority。
3. Anchor-free discovery 实际只覆盖两个 LGE-only 病例，没有覆盖 T2-present edema 和 CenterC complete tri-modal。
4. 关闭 semantic negative memory 后 edema 更好，说明当前负记忆可能过度抑制。
5. Prototype maps 对 edema 的贡献约 `+0.0007`，对 scar 无稳定收益，当前 16-slot dictionary 不足以作为论文核心性能来源。
6. Scar 的 proposal-only、refiner-only、learned-source 和 gate-one 均为负；edema 保留约 `+0.004～+0.006` 的小幅信号，两个病种必须分开判断。

## 下一步实验决定

不启动 Batch 8，不继续完整 Batch 7 系统。只允许一次六组匹配实验：

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

三组同病种实验必须从同一 checkpoint 和相同轻量模块初始化开始，使用相同 seed、病例序列、patch centers、optimizer、步数、评价和 decode：

- `minimal`：普通 pathology evidence/discovery/confirmation head，无 representer dictionary；
- `br2_no_sip`：加入轻量 availability-masked representer dictionary、source-level learner coefficients和每-source稀疏项，SIP 权重为零；
- `br2_sip`：与 `br2_no_sip` 完全同构同初始化，只增加正式 BR2-SIP。

当前 M10 16-slot spatial dictionary、prototype maps、semantic negative memory、refiner、source arbiter、production gate训练、legacy semantic regularization 和 legacy Pattern-SIP 均不得进入这六个实验。

## 最终保留门

- Minimal positive-case Dice `>=+0.003` 且安全门通过，才保留该病种 proposal。
- BR2 retrieval 相对 minimal 额外 Dice `>=+0.001` 且安全不恶化，才保留轻量 representer dictionary。
- SIP 相对同病种 `br2_no_sip` 额外 Dice `>=+0.0005`，或在 Dice 不下降超过 `0.0005` 的前提下将 HD95/remote-FP 改善至少 2%，且 help/harm 不恶化，才进入最终模型和论文性能主张。
- SIP 未通过时只删除 SIP loss，不自动删除已经证明有效的 BR2 retrieval。
- Scar minimal 仍为负时，停止 scar SRR correction；不得再用 dictionary/refiner/gate 继续补救。

这次分解的目标不是维护架构图，而是得到可写入论文的清楚结论：普通 proposal 是否有效、轻量 BR2 retrieval 是否提供独立价值、SIP 是否真正改善跨缺失模式的表示共享。