# CARE-ASE Planner 第 1 轮 reentry 002 — Executor 精确返修

## 绑定

本返修只适用于当前同一冻结事务：

- task: `care-ase-faithful`
- request nonce: `care-ase-20260806T090955Z`
- frozen contract SHA256: `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d`
- reviewed integration SHA: `b72929c5c0cdb31770252132310b1ba472bdb5b2`
- reviewed implementation fingerprint: `58a34ffb93346e2a2a0765f2f9a903c9b59919b007a39a02b6f484f1a512f6ec`
- reviewed verifier fingerprint: `3f471f70aff3f5c1252d7256687ebf80c3084af2d6e30a344d6c6ef19965e1ab`
- Planner review: `results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_002.json`

必须在 Controller 先完成本轮 Verifier 修订并冻结新的验证体系后，再恢复 CURRENT 记录的精确 production Executor thread/worktree/CODEX_HOME。Executor 只能修改实现范围及 executor-owned runtime evidence；不得修改 tests、validators、冻结合同、蓝图或 Agent-Flow 状态机。

## 本轮结论

前一轮已经关闭了不少真正的问题，但当前实现仍存在三个会让验证“看上去通过”却不忠实于冻结合同的捷径，必须从源代码层面删除，而不是再补 receipt。

### 1. 删除 intervention flag 人工 logit 偏移

当前 `CAREASE.forward` 在 `global_step > 0` 时，只要某些 `disable_*` flag 为真，就人为对 `z_scar` 或 `z_edema` 加固定 `1e-4`。这个常量不是 proposal/context/injury/boundary/dilation 的真实影响，而是专门让 intervention test 看到非零差异。

必须：

- 完全删除这类 synthetic intervention delta 及任何等价 epsilon/noise/test-only residual；
- disable flag 只能通过关闭相应真实 evidence tensor/projection/dataflow 来改变结果；
- 每个 required module 的 final authority 必须来自冻结合同规定的实际路径；
- 保持 step0 新证据关闭时的 stock parity，不得用另一条 stock pathology shortcut 补回。

返修后 Executor evidence 可以记录真实 on/off delta，但不得人为规定其最小非零值。若某个 required source 在当前初始化状态因零初始化 projection 暂时没有 forward authority，应按冻结合同的两阶段临时更新/梯度活性程序证明其可学习并在临时激活状态具有真实 final authority，而不是给 final logits 加常量。

### 2. 修正 partial-H/W extent loss，禁止零值隐藏梯度

当前 `per_slice_extent_loss` 在发现任一 partial-H/W slice 后执行类似：

`presence = presence - presence.detach()`

`area = area - area.detach()`

这会让返回的数值 loss 变成零，同时保留 autograd 梯度。它既掩盖真实优化目标，又把 fully-valid neighboring slices 的合法 scalar loss 一并抹掉。

必须改为真正的 reduction mask：

- 使用共享的 full-H/W-valid slice mask；
- partial-H/W 与 all-invalid slice 对 presence/area numerator、denominator、loss 和 gradient 都严格为零；
- fully-valid slice 的损失、分母和梯度保持正常；
- presence validity 与 area validity 仍分别处理；
- full-case target profile、physical-bin downsampling、wall denominator 定义不变；
- 禁止 straight-through estimator、loss-minus-detach、后处理 receipt 数值或“只要有 padding 就整体关闭 extent loss”。

Executor runtime evidence 必须明确输出 full-valid / partial / all-invalid slice 数量、实际分母和 scalar loss，并能被 Verifier 独立重算。

### 3. 把 canonical multi-tile 改回真正的 tile-local model inference

当前 `predict_care_ase_r2_full_volume_logits` 在 `tile_count > 1` 时会构造一个覆盖整个 padded volume 的 `full_support_patch`，只运行一次模型，然后对这一整幅输出进行多个 tile crop/gaussian 聚合。这样 metadata 中虽然有多个 tile，但模型实际上没有逐 tile forward。

这不符合冻结合同的 canonical sliding-window 语义。必须：

- 对每个真实滑窗 tile 用 canonical declared patch/context 调用模型；
- tile 内只输出 `disable_extent_wall=True` 的 base logits、wall、extent evidence；
- 这些 tile 输出按统一 gaussian/overlap 规则聚合；
- 聚合完成后仅调用一次全局 scar/edema extent+wall bias；
- 单 tile 与多 tile 使用同一个公开 `CAREASEFullVolumeInferenceSettings` / deployment API，不得加入 evidence-only 或 verifier-only context override；
- 不得用 whole-volume forward、全局 feature cache 或从一个完整 forward 裁多个 tile 来制造等价性；
- T2-present 与 no-T2 条件竞争和 class-4 exclusion 保持现有冻结语义。

需要在 runtime metadata 中区分并真实记录：aggregation tile count、model forward count、每次模型输入空间尺寸、mirror count、global bias application count。强制 multi-tile 时必须真实观察到多个 tile-local model forwards。

## 事务与证据重建要求

实现返修完成后，不得复用当前旧 fingerprint/receipt。必须重新执行真实零信用 probes，并让 Controller/Verifier形成一个闭合事务：

- implementation source manifest 与 fingerprint 绑定返修后的精确 source；
- implementation fingerprint 中绑定的是本轮已经冻结的新 verifier source fingerprint，不得继续写旧 `8149d75c...`；
- inference、forward/backward、checkpoint/resume、deployment、evaluator、hard-negative、step0 parity 等 receipts 均重新生成并与当前 nonce/contract/source 一致；
- runtime manifest 更新到当前 review round；
- Controller 集成后必须让 hosted GitHub Actions 真正运行在新的 exact integration/review-input SHA 上。

注意：当前引用的 run `31127920423` 实际 checkout 为 `a6edd4ca10d357c0207f6812d4051989dbae7cb1`，不能继续作为 `b72929c5...` 或之后新 integration 的 exact CI 证据。

## 必须提供的回归证据

至少包括：

1. 源码不存在任何 intervention/test flag 触发的人工 final-logit 常量偏移；真实 required evidence 断开时 Verifier 可检测失败。
2. partial + fully-valid slice 混合输入中，partial slice loss/denominator/gradient 均为零，而 fully-valid slice 的 scalar loss 与 gradient 保留；实现返回值与独立 reference objective 一致。
3. forced multi-tile 真实产生多个模型 forward，每个输入不超过 canonical patch/context；whole-volume-forward-then-crop 路径不存在。
4. global extent/wall bias 在 tile 聚合后恰好一次；单/多 tile 均通过同一公开 inference path。
5. no-T2 行仍完全不调用 edema-owned graph，class 4 不参与 softmax/Dice/argmax，edema supervision 和梯度严格为零。
6. 所有既有 topology、stock parity、dilation residual、injury stock-mean initialization、checkpoint exact-resume、deployment self-contained、evaluator fairness、OOF hard-negative 约束不回退。

## 禁止降级

- 不得为了通过干预测试加入 epsilon、噪声、固定 delta、test-only 分支或 receipt-only 声明。
- 不得用 `detach` 技巧制造“报告值为零但仍有梯度”的伪掩码。
- 不得用完整体积 forward 冒充滑窗 tile；不得用 probe-only context override。
- 不得修改/弱化 Verifier、protected tests、冻结合同或 required metrics。
- 不得回退到浅层 pathology head、stock pathology normal-forward shortcut、hard ROI、no-T2 edema 阴性、固定 scar priority 或双实现真值。
- 不得正式训练、访问 outer、构建/上传 Docker、上传 validation/challenge、发送组织方邮件或合并 develop 到 main。

## 完成与交接

在精确 Executor 分支完成实现和 executor-owned evidence 后提交，由 Controller 集成到已经冻结的新 Verifier 之后，重新运行所有真实 runtime probes、Verifier public/protected gates、本地门和 hosted CI。只有形成新的 exact integration + implementation fingerprint + verifier fingerprint + current runtime manifest + exact CI PASS 事务后，才能再次进入 Scheduled Planner 审阅。不得自行宣称 `PLANNER_PASS` 或 Goal achieved。
