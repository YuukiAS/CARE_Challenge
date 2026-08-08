# CARE-ASE Planner → Verifier 精确返修

你是本任务已经绑定的 production Verifier。必须恢复原 Verifier thread / CODEX_HOME / worktree；不得新建替代角色，不得修改实现代码。

## 本轮绑定

- task_id: `care-ase-faithful`
- request_nonce: `care-ase-20260806T090955Z`
- frozen contract SHA256: `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d`
- Planner 审阅的 integration: `491ba697e7a51712d9d04fc27824e4efa018827a`
- Planner 审阅的 implementation fingerprint: `25828c210776d499613a872754d39290cf9df416a747fb9f0f86c56f91711dc6`
- Planner 审阅的 verifier fingerprint: `1cce33fdfe102efb63979870f190bfc1a2584385a07f6f2db2ccddcb14e69aaa`
- Planner review: `results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_004.json`
- decision: `PLANNER_REVISE_BOTH`

先读取冻结合同、上述 Planner review、当前 Verifier 源码与当前实现，但只修改 Verifier 被授权的 validators/tests/verification artifacts。

## 必须修复的问题

当前 Verifier 对 loss 的检查仍然停留在“名称、权重、included、denominator、finite”等 receipt 层，无法证明真实执行公式符合合同。当前实现已经证明这个漏洞可被实际利用：

1. 冻结合同要求 injury 项为 `0.40 * Dice+BCE`，但当前 `care_ase_loss` 实际调用 `binary_dice_focal(alpha=0.35, gamma=2.0)`，receipt 仍把它报告成 `injury_dice_bce`。
2. 冻结合同要求 scar component 项为 `0.25 * component-adaptive Tversky(alpha=0.3,beta=0.7)`，但当前实现把该项变成 `0.5*Tversky + 0.5*scar_occupancy Dice/Focal`，再乘 0.25；额外 occupancy objective 不在冻结合同的唯一允许 loss 集中。
3. 当前 kb13 主要能抓“漏项/假 denominator”，抓不到“同名 term 内部换公式或混入未授权 objective”。

因此本轮 Verifier 必须升级为**loss semantic oracle**，不能继续相信 implementation self-report。

## 必须实现的 Verifier 行为

### 1. 独立重算 injury Dice+BCE

从 Verifier 自己加载的真实 train-only T2-present case / mixed batch 的模型输出、target、availability 出发，独立计算冻结合同定义的 injury target（label 4 或 5）以及 T2 gating，然后独立计算 Dice+BCE。

参考计算不得调用：

- `care_ase_loss`
- `care_ase_loss_with_term_details`
- implementation 中用于 injury 的同一个 loss helper
- Executor receipt 中的 `injury_dice_bce` 数值

Verifier 必须把独立参考值与实际总 loss 中 0.40 injury contribution 做可追溯比较，并证明 implementation 执行的确实是 Dice+BCE，而不是 focal 或其它替代。

### 2. 独立重算 scar component-adaptive Tversky

从真实病例的 scar half-resolution预测与 full-case component identity/volume metadata 出发，按冻结合同独立重算 per-GT-component adaptive Tversky，参数必须是 `alpha=0.3, beta=0.7`，small-component scaling 按合同公式执行。

必须验证：

- 0.25 scar component contribution 只来自该 Tversky；
- 不得混入 quarter/half occupancy Dice/Focal、center loss、proposal loss或其它未声明 objective；
- 总 loss 中不存在通过已声明 term 名称包裹的隐藏 auxiliary loss。

同样不得把 implementation 的 `per_gt_component_tversky` 或 `care_ase_loss_with_term_details` 直接当 reference oracle；可以读取模型输出/target，但参考数学必须由 Verifier 独立实现。

### 3. 验证唯一允许 loss 集

冻结合同已经给出唯一允许的加权 loss 集。Verifier 必须独立检查：

- 每个允许项确实存在并使用正确公式；
- 权重正确；
- eligibility/T2 gating/ignore mask 正确；
- 总 loss 等于允许项贡献之和；
- 不存在额外 weighted auxiliary objective 被加入总 loss；
- 不允许仅靠 term 名、`computed_by` 字符串或 receipt schema 证明公式正确。

现有 denominator、finite、真实病例、no-T2 等检查继续保留，不得降级。

### 4. 增加真正的 protected known-bad

至少新增并真实执行以下两类 mutation；不能只修改 JSON 声明：

A. `injury_dice_bce` 的真实实现被替换为 Dice+Focal，名称仍保持 `injury_dice_bce`。Verifier 必须 fail。

B. scar component 项真实实现变为 `Tversky + λ * occupancy_loss`，其中 `λ` 至少测试两个非零值或两种混合方式，term 名仍保持 `scar_component_adaptive_tversky`。Verifier 必须 fail。

这些测试必须证明 Verifier 是根据数学语义检测，而不是根据函数名/源码字符串/固定常量黑名单检测。

禁止通过新增无合同依据的 blocking threshold 来实现。所用数值容差只允许是验证同一确定性公式的浮点比较容差，并必须在 verification artifact 中注明其逻辑来源；不得引入新的科学要求。

### 5. 修复 transaction binding 设计

当前 Verifier 源码中仍硬编码旧的 `REVIEWED_INTEGRATION_COMMIT=0fc3...` 与旧 `REVIEWED_VERIFIER_FINGERPRINT=8fc1...`，当前 executable receipt 也仍绑定旧 integration 且 `passed=false`。这不能形成当前可重放事务。

在本轮 Verifier 修复并冻结时：

- 新 Verifier source/fingerprint 必须明确绑定当前 nonce、contract、review round；
- transaction gate 必须拒绝混用旧 integration / implementation / verifier / runtime tuple；
- 不得通过修改 CURRENT 或 planner packet 伪造一致性；
- Verifier 完成修复后先冻结新的 verifier fingerprint，再交 Executor 基于该 fingerprint 返修与重建 evidence；
- Executor 返修集成后，Verifier 必须针对**新的精确 integration**重新独立执行，最终 executable receipt 必须 `passed=true` 才能进入 Planner review。

如果 transaction 常量需要由 Controller 在新 integration 形成后生成/绑定，必须设计成明确的 transaction input，而不是把旧 integration 永久写死在 Verifier 源码里。

## 上一轮已经修好的能力必须保留

不得破坏：

- verifier-owned final-authority intervention；
- implementation-owned disable flag delta 只作辅助/诊断，不作为权威证明；
- 对 intervention-only synthetic signal 的语义检测；
- partial-H/W extent reference objective；
- real tile-local forward instrumentation；
- full-support pseudo-tiling known-bad；
- real CNN single-full-context vs tile-local 差异保持 diagnostic-only；
- no-T2 graph/gradient/competition检查；
- checkpoint/resume、deployment、evaluator、hard-negative binding 等现有真实执行检查。

## 完成标准

在恢复 Executor 前，至少必须先证明：

1. 当前 `491ba697...` 的错误 injury/ scar component loss 会被新的 Verifier fail-closed；
2. 两类公式替换 protected known-bad 均真实失败；
3. Verifier 自身所有 public/protected tests 通过；
4. 新 verifier fingerprint/freeze receipt 已生成且不可由 Executor 修改；
5. 没有 formal training、outer access、Docker build/upload、validation upload、organizer email 或 develop->main merge。

完成后按 Agent-Flow v3 协议把新的 Verifier role commit/fingerprint交回 Controller，由 Controller 再恢复精确 Executor thread。不得自己修改实现来让测试通过。
