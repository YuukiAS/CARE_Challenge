# CARE-ASE Planner 第 1 轮 reentry 002 — Verifier 精确返修

## 绑定

本返修只适用于以下不可替换的当前事务：

- task: `care-ase-faithful`
- request nonce: `care-ase-20260806T090955Z`
- frozen contract SHA256: `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d`
- reviewed integration SHA: `b72929c5c0cdb31770252132310b1ba472bdb5b2`
- reviewed implementation fingerprint: `58a34ffb93346e2a2a0765f2f9a903c9b59919b007a39a02b6f484f1a512f6ec`
- reviewed verifier fingerprint: `3f471f70aff3f5c1252d7256687ebf80c3084af2d6e30a344d6c6ef19965e1ab`
- Planner review: `results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_002.json`

只恢复 CURRENT 中记录的精确 production Verifier thread/worktree/CODEX_HOME。Verifier 只能修改 tests、validators 和 verifier-owned receipts；不得修改实现、训练源码、冻结合同、蓝图或 Agent-Flow 状态机。

## 本轮核心问题

当前 Verifier 已经从“receipt replay”升级为可真实加载 torch、nnU-Net 和 train-only 病例的执行环境，这是有效进展；但它仍会把三个明显的测试感知捷径判为 PASS，因此验证体系尚未达到冻结合同要求的独立反降级能力。

第一，当前模型在 intervention flags 打开时会直接给最终 scar/edema logit 人工加 `1e-4`。这不是被禁用模块的真实因果影响，却恰好满足“关掉模块后 final logits 非零变化”的现有 oracle。第二，partial-H/W extent loss 在检测到 partial slice 后使用 `loss - loss.detach()`，使报告的 loss 为零但仍可保留隐藏梯度。第三，所谓 canonical multi-tile 在 tile_count>1 时只对整个 full-support volume 做一次模型 forward，再把同一次输出裁成多个名义 tile 聚合；现有 Verifier 只看 tile_count，而没有验证实际 tile-local forward。

此外，当前事务绑定仍不闭合：Verifier executable receipt/source 常量仍绑定 `5fd6c265...` 和 verifier fingerprint `8149d75c...`，而当前 Planner packet 绑定 `b72929c5...` 和 `3f471f70...`；runtime manifest 仍为 review round 0；当前引用的 GitHub Actions run `31127920423` 实际 checkout 是 `a6edd4ca10d357c0207f6812d4051989dbae7cb1`，不是 `b72929c5...`。

## 必须完成的 Verifier 返修

### 1. 真实 final-authority oracle

建立 verifier-owned 的实际数据流干预，不得只调用 implementation 提供的 disable flag 后检查结果是否变化。

对每个冻结合同要求必须影响最终重建的模块/证据源，至少验证：

- scar proposal occupancy/center；
- scar context；
- edema injury；
- edema boundary；
- edema context 与 dilation 1/2/4；
- scar/edema extent + wall bias；
- 每个具名 evidence projection。

Verifier 必须能够识别并拒绝以下坏实现：模块已存在且 auxiliary loss 正常，但 final path 被断开；disable flag 自己加常量/噪声/epsilon；receipt 直接声明 intervention PASS。

加入真实 protected executable mutation：断开某一 required source 到 final projection/reconstruction 的连接，同时保留所有 intervention flags 和 auxiliary outputs。Validator 必须非零退出。不得通过修改一个 JSON 字段来模拟失败。

### 2. partial-H/W 的数值目标与梯度一致性

重写 verifier-owned partial-H/W probe，使它不只检查 partial slice 的梯度为零，还要独立构造 reference objective：

- 一个 partial-H/W slice；
- 一个 fully-valid neighbor slice；
- 独立仅以 fully-valid slice 计算参考 presence/area loss。

必须同时满足：实现返回的实际 scalar loss 与参考值一致；partial slice numerator/denominator contribution 为零；partial slice 对 extent head 的梯度严格为零；fully-valid neighbor 在存在误差时 scalar loss 非零、梯度非零。

加入 protected mutation，明确拒绝 `x - x.detach()`、straight-through zero-valued loss、仅在 receipt 中把 loss 写成零、或遇到任一 padding 就整体关闭 extent supervision 的实现。

### 3. 真正的 tile-local canonical inference oracle

Verifier 必须 instrument 每一次模型 forward 的输入 shape、call id、mirror factor 和对应 tile 坐标。对 forced multi-tile：

- 实际模型 forward 数必须与真实 tile/mirroring 调用一致，而不是只有一个 full-volume forward；
- 每个模型输入空间尺寸必须受 canonical declared patch/context 上限约束；
- aggregate tile count 与 actual model forward count 分开记录；
- tile 只产生 base logits、wall、extent evidence；
- global bias 聚合后仅调用一次；
- T2-present 与 no-T2 都走同一公开 inference API/settings。

加入 protected mutation：恢复“whole-volume full_support forward 一次，然后裁 output 冒充多个 tiles”的路径时，Verifier 必须非零退出。不能仅凭 `tile_count > 1`、call id 字符串或输出接近就判定真实多 tile。

### 4. 不可变事务与 CI 绑定验证

Verifier 自身的 source fingerprint 与 execution receipt 必须采用不会产生“一轮落后”的绑定方案。建议把：

- verifier source/test/validator fingerprint；
- executable run receipt hash；
- integrated implementation fingerprint；
- exact integration SHA

作为显式不同字段，再由最终 transaction fingerprint 聚合，而不是让 executable receipt 声称一个随后因 receipt 本身加入而变化的 verifier fingerprint。

Verifier transaction gate 必须检查 exact reviewed integration/source binding，而不只是 `integration_sha` 是当前 HEAD 的 ancestor。任何 verifier critical source 在被审 integration 之后改变，都必须使旧 transaction 失效。

同时验证 runtime manifest 的 review round、nonce、contract、integration、implementation/verifier fingerprints 均为当前事务。Hosted CI 的最终 head SHA 由 Controller 在整合后提供；Verifier/validator 必须拒绝“旧 CI run 继承给新 integration”的声明。

## 必须新增/强化的回归证据

至少应形成真实可执行证据证明：

1. 删除真实 named evidence final authority 时 validator fail；仅保留人工 `+1e-4` intervention delta 也 fail。
2. partial + full-valid 混合切片中，实际 scalar extent loss 等于 fully-valid-only 参考目标；partial 梯度为零，full-valid 梯度非零。
3. full-support pseudo-tiling mutation fail；真实 forced multi-tile 观察到多个受 patch 限制的模型 forward。
4. 把 executable receipt/Verifier source/implementation fingerprint 任一换成旧 SHA/fingerprint 时 transaction gate fail。
5. forged Executor PASS receipt 无法替代 Verifier 自己的执行观测。

## 禁止降级

- 不得把实现中的特殊测试 flag、布尔字段、固定 epsilon 或 receipt 声明当作 final authority 证据。
- 不得预生成 mutation failure JSON 代替真实 mutation + execution。
- 不得为了让测试通过而降低冻结 tolerance、删除 required module、取消 extent、取消 sliding-window 或改冻结合同。
- 不得修改 Executor 范围的源代码来替其修实现。
- 不得训练、访问 outer、构建/上传 Docker、上传 validation/challenge、发送邮件或合并 develop 到 main。

## 完成与交接

完成后在精确 Verifier 分支提交 verifier-owned 修改和真实 receipts，运行全部 public/protected/local gates，并冻结新的 verifier source/transaction fingerprint。随后返回 Controller 集成；Controller 必须先集成 Verifier，再恢复同一精确 Executor production thread。不要自行更新 Planner decision，不要自行宣称 Goal achieved。
