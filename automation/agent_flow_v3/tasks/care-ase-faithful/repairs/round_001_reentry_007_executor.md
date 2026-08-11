# CARE-ASE Planner → Executor 精确返修（round 1 / reentry 7）

必须等待本轮 Verifier 完成新的 current-runtime provenance oracle 并由 Controller 冻结/集成后，再恢复当前 `care-ase-faithful` 的原 production Executor thread。只修改 implementation/runtime 范围，不得修改 Verifier 源码、测试、冻结合同或状态机。

返修来源固定为：

```text
request_nonce: care-ase-20260806T090955Z
frozen_contract_sha256: a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d
reviewed_integration_commit_sha: ed2e3097386bd322968936eb30fd434e621b51ce
reviewed_implementation_fingerprint_sha256: d4b60e96a46603a19acf19d9a040a84005f046b1252aceca844edf9f75eb28b6
reviewed_verifier_fingerprint_sha256: a731eec931128a73fc32113048c49a5a8de5a7db2d877b6f8bb66732eebbb380
planner_review: results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_007.json
planner_decision: PLANNER_REVISE_BOTH
```

实际返修必须绑定 Verifier 本轮新冻结后的 fingerprint，不得把上面的旧 reviewed Verifier fingerprint 当作最终目标。

## 本轮实现问题不是模型结构，而是 runtime provenance 闭环

当前模型、loss、no-T2、extent 和 canonical tile-local inference 本轮未发现新的阻断性科学降级；不要无关重构这些已关闭部分。

真正问题在 tracked current-runtime identity：

```text
results/agent_flow_v3/care-ase-faithful/implementation/current_runtime_input_bundle.json
results/agent_flow_v3/care-ase-faithful/implementation/current_runtime_identity_receipt.json
```

它们仍绑定上一轮：

```text
integration = 965b0aadaf436e11abdf37dfe3ce6699e928b7b0
implementation fingerprint = e7a6bfe00336354da7debf7321966c8a72c7ce43ee0bb00c316387c72659b7e3
```

而当前 Planner tuple 已是 `ed2e3097... / d4b60e96...`。checkpoint probe 也仍记录 executor-local integration `d400c003...`。这意味着“current runtime identity”证据并非当前精确实现事务。

此外，当前 implementation fingerprint 把 runtime input bundle/identity receipt 的 SHA 纳入 fingerprint，而 bundle 又保存 `implementation_fingerprint_sha256`。若继续要求两者互相精确包含，就形成自引用；当前实现实际上通过在 bundle 中保存上一代 fingerprint 绕开了循环，但这正是本轮发现的 stale binding。

## 必须实现的非循环分层

按 Verifier 本轮新 oracle 采用一个明确、单一的非循环 provenance 方案。推荐机械结构如下，允许等价实现，但不能改变科学合同：

1. **immutable implementation identity**：implementation fingerprint 只覆盖 implementation source manifest、静态实现证据和其他在 integration 前可冻结的 immutable 输入；不得把“必须在最终 integration/CI 后才能生成”的 runtime transaction bundle/receipt 哈希回自己的 fingerprint。
2. **post-integration runtime binding**：current runtime bundle 或等价 binding artifact 在 reviewed integration 已知后生成，明确绑定：task_id、request_nonce、frozen contract SHA、immutable implementation fingerprint、Verifier fingerprint、reviewed integration SHA、fold、显式 result/probe roots、显式 hard-negative manifest path+SHA，以及当前 formal user decision/permit provenance。
3. **formal runtime fail-closed**：任何 materialization、forward、optimizer step、formal checkpoint save/resume 之前都必须验证上述 post-integration bundle；旧 integration、旧 implementation identity、旧 verifier fingerprint、旧 task key、旧 permit、旧 result root 均拒绝。
4. **runtime manifest 再绑定**：Controller 最终 runtime manifest 同时绑定 immutable implementation fingerprint、post-integration runtime bundle SHA、identity validation receipt SHA、checkpoint/inference/deployment/evaluator receipts、Verifier receipts 和 exact hosted CI。不要让 implementation fingerprint 与 runtime bundle互相哈希。

历史 v8/v9 合同和 `results/20260804...` 下的 OOF hard-negative artifact 可以继续作为显式、SHA 绑定的科学来源资产；不要为了路径看起来“新”而复制或改写 OOF 数据。关键是它不能再充当 current task identity、默认 permit 或隐式 result root。

## 必须重新生成的零信用证据

在新 Verifier fingerprint 下至少重建：

- immutable implementation fingerprint/source manifest；
- current runtime input/binding artifact 及其内容 SHA；
- current runtime identity probe，证明 reviewed integration/implementation/verifier/nonce/contract 精确匹配；
- stale integration、stale implementation identity、stale verifier、旧 task key、旧 permit、旧 result root 在 forward 前 fail closed；
- checkpoint save→resume zero-credit probe，证明当前 nonce/合同/source/runtime binding 精确匹配，错配拒绝，下一步 loss/gradient/optimizer/scheduler 与 uninterrupted 一致；
- inference/deployment/evaluator probes 继续保持 canonical full-volume、self-contained deployment 和公平 metric population；
- `formal_training_started=false`、`outer_accessed=false`、无部署/上传。

若某些 post-integration binding receipt 必须由 Controller 在 integration SHA 已知后生成，则实现只负责提供确定性生成/验证入口，Controller 负责事务产物；不要让 Executor伪造未来 integration SHA。

## 保持关闭项

不得回退以下项目：injury Dice+BCE；纯 component-adaptive Tversky；partial-H/W 在 Conv1d 前清零且无跨 z 梯度；required evidence 真实 final authority；no-T2 不执行 edema-owned graph；真实逐 tile forward；聚合后 global extent/wall bias 只施加一次；deployment reload 不重开 stock checkpoint。

不得启动正式训练、访问 outer、部署、上传、构建 Docker 或合并 `develop` 到 `main`。完成后交 Controller 重新集成并等待精确 hosted CI；CI 成功后必须由 Verifier 再执行 post-CI transaction gate，不能直接交 Planner。
