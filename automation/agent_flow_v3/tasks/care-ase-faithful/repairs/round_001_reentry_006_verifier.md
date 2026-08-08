# CARE-ASE Planner → Verifier 精确返修（round 1 / reentry 6）

你必须恢复当前 `care-ase-faithful` 的原 production Verifier thread，只修改 Verifier 所有的验证源码、测试和验证产物；不得修改 CARE-ASE 实现源码。所有工作绑定以下不可替换输入：

```text
request_nonce: care-ase-20260806T090955Z
frozen_contract_sha256: a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d
reviewed_integration_commit_sha: 965b0aadaf436e11abdf37dfe3ce6699e928b7b0
reviewed_implementation_fingerprint_sha256: e7a6bfe00336354da7debf7321966c8a72c7ce43ee0bb00c316387c72659b7e3
reviewed_verifier_fingerprint_sha256: 6acc8fdc640df9be54848dfc676da45257d887c0f4be5ce71efa6230114a4a17
planner_review: results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_006.json
planner_decision: PLANNER_REVISE_BOTH
```

## 本轮必须修复的验证缺口

当前 Verifier fingerprint 的“只由冻结合同与 verifier source/test definitions 组成”的设计是正确方向，必须保留；不得重新把 executable receipt、CI receipt、mutation output、integration SHA 或 implementation fingerprint 纳入 frozen verifier digest。

但 `validators/care_ase_faithful/run_executable_verifier.py::transaction_gate` 对 runtime manifest 仍然 fail-open：当前 `runtime_receipt_manifest.json` 明明是 `review_round=0`，且没有当前 `request_nonce` 与 `frozen_contract_sha256`，现有代码却因为使用可选字段检查而不会仅凭这些缺失直接拒绝。请把 runtime manifest 变成当前事务的强制、机器可重放证据。

修复后至少必须强制存在并精确相等：

```text
task_id
request_nonce
frozen_contract_sha256
review_round
integration_commit_sha
implementation_fingerprint_sha256
verifier_fingerprint_sha256
```

manifest 还必须绑定当前关键 runtime receipt 的路径与内容 SHA，至少覆盖 implementation evidence、checkpoint/resume、inference、deployment/evaluator probes、executable Verifier、transaction gate、frozen verifier validation 和 hosted CI evidence。缺字段、旧轮次、旧 integration、旧 implementation fingerprint、旧 verifier fingerprint、receipt 内容 SHA 漂移均必须 fail closed。

必须新增并真实执行以下 known-bad，而不是只按 ID 返回失败：

1. `runtime_manifest_round0_reused`：review round 1 时注入 round 0 manifest；
2. `runtime_manifest_missing_nonce`；
3. `runtime_manifest_missing_frozen_contract`；
4. `runtime_manifest_old_integration`；
5. `runtime_manifest_old_implementation_fingerprint`；
6. `runtime_manifest_old_verifier_fingerprint`；
7. `runtime_manifest_receipt_sha_drift`。

每个 mutation 都必须通过真实 verifier path 得到非零退出，并保留 executable report。不得通过字符串扫描、固定 PASS/FAIL JSON 或 Executor 自报替代运行验证。

## 最终事务闭合要求

当前 hosted CI 对 `965b0aad...` 已成功，但现存 `executable_verifier_receipt.json` 和 `transaction_gate_receipt.json` 仍绑定 `afcf93cf...` 且为 FAIL_CLOSED，`frozen_verifier_validation_result.json` 仍 `passed=false`。这不能作为最终通过证据。

请把 Verifier 支持成明确的两阶段或等价 fail-closed 流程：

- pre-CI 阶段可运行所有模型/runtime probes，并把“尚无当前 exact CI”标记为事务未闭合；
- hosted CI 对最终 integration 真正成功后，必须由同一 production Verifier thread 再执行 post-CI transaction gate；
- post-CI gate 必须独立读取真实 CI head SHA 与 conclusion，并要求它们精确对应最终 integration；
- 只有 post-CI gate `PASS`、`failure_count=0`，且 frozen verifier validation `passed=true`，Controller 才能生成新的 Planner review packet。

增加 old CI head、pending CI、failed CI、旧 verifier receipt/reused planner tuple 的回归坏例，全部必须 fail closed。不要通过把 pre-CI failure 标记 `allowed=true` 后让 Controller 直接当最终 PASS。

## 保持已关闭项目不回退

必须继续覆盖并保持通过：

- `SliceExtentHead` partial-H/W 在 Conv1d 前清零，邻片 loss 对 partial slice feature 梯度严格为零；
- injury 必须为 Dice+BCE；scar component 项必须为纯 component-adaptive Tversky；
- required evidence final authority 不能靠 intervention-only 人工信号；
- no-T2 行不执行 edema-owned 子图；
- canonical full-volume inference 必须真实逐 tile forward，global extent/wall bias 聚合后只施加一次；
- checkpoint 当前 nonce/合同/integration provenance mismatch 必须 fail closed；
- frozen verifier fingerprint 必须保持 pre-Executor immutable。

完成后冻结新的 Verifier source fingerprint，并提交 Verifier-owned source/test/definition 变更。不要修改 implementation；不要训练、访问 outer、部署、上传或合并 `develop` 到 `main`。Verifier 完成后交 Controller 集成，再由原 Executor thread 处理其实现范围返修。