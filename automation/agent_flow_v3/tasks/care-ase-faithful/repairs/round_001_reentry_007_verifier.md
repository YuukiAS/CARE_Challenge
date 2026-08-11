# CARE-ASE Planner → Verifier 精确返修（round 1 / reentry 7）

恢复当前 `care-ase-faithful` 的原 production Verifier thread。只允许修改 Verifier 所有的 tests、validators 和 verification-owned receipts；不得修改 CARE-ASE implementation 源码。返修输入固定为：

```text
request_nonce: care-ase-20260806T090955Z
frozen_contract_sha256: a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d
reviewed_integration_commit_sha: ed2e3097386bd322968936eb30fd434e621b51ce
reviewed_implementation_fingerprint_sha256: d4b60e96a46603a19acf19d9a040a84005f046b1252aceca844edf9f75eb28b6
reviewed_verifier_fingerprint_sha256: a731eec931128a73fc32113048c49a5a8de5a7db2d877b6f8bb66732eebbb380
planner_review: results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_007.json
planner_decision: PLANNER_REVISE_BOTH
```

## 已关闭项目必须保持

你在上一轮完成的 runtime-manifest 强绑定方向正确，必须保留：`task_id`、`request_nonce`、`frozen_contract_sha256`、`review_round`、`integration_commit_sha`、implementation/verifier fingerprints 和关键 receipt 内容 SHA 都要精确匹配；stale/missing manifest mutations 必须继续真实执行并非零退出。冻结 Verifier fingerprint 也必须继续只由冻结合同和 Verifier source/test definitions 构成，不能重新把 executable/runtime/CI 输出纳入 digest。

## 本轮新发现：current runtime identity 仍在最终事务门之外

当前被审阅 tuple 是：

```text
integration: ed2e3097386bd322968936eb30fd434e621b51ce
implementation fingerprint: d4b60e96a46603a19acf19d9a040a84005f046b1252aceca844edf9f75eb28b6
verifier fingerprint: a731eec931128a73fc32113048c49a5a8de5a7db2d877b6f8bb66732eebbb380
```

但 tracked `implementation/current_runtime_input_bundle.json` 和 `current_runtime_identity_receipt.json` 仍绑定上一轮：

```text
integration: 965b0aadaf436e11abdf37dfe3ce6699e928b7b0
implementation fingerprint: e7a6bfe00336354da7debf7321966c8a72c7ce43ee0bb00c316387c72659b7e3
```

而当前 `REQUIRED_RUNTIME_MANIFEST_ARTIFACTS` 没有强制包含这两个 current-runtime identity 证据，也没有 oracle 比较它们内部的 tuple 与当前 Planner tuple。因此即使 Controller 只生成一个新的 wrapper runtime manifest，formal runtime identity 仍可能是旧实现而 Verifier 给出 PASS。

## 必须修复

建立一个非循环的 current-runtime provenance oracle，并由最终 post-CI transaction gate 强制执行。必须满足：

1. 最终事务必须显式绑定 current runtime input bundle 与 identity validation receipt，或绑定一个语义等价、Controller-owned 的 post-integration runtime-binding receipt；路径和内容 SHA 都必须进入当前 runtime manifest。
2. oracle 必须检查 task ID、当前 nonce、冻结合同 SHA、精确 reviewed integration、当前 Verifier fingerprint，以及一个不产生自引用的 immutable implementation identity。
3. 当前 implementation fingerprint 设计把 runtime bundle SHA 纳入 fingerprint，而 bundle 又内嵌 implementation fingerprint。不要通过要求数学上的自哈希 fixed point 来解决。允许的机械修复方向是：immutable implementation fingerprint 不哈希 post-integration transaction bundle；随后 runtime manifest/binding receipt 同时绑定该 immutable implementation fingerprint 和 bundle SHA。若采用等价分层方案，也必须证明不存在“bundle 内嵌上一代 fingerprint”这种循环回退。
4. Verifier 必须独立读取真实 tracked artifacts，而不是相信 Executor evidence 中 `status=PASS` 或 `happy_path_validation=true`。
5. checkpoint/resume current provenance 也要通过同一 current transaction oracle 审核；本轮 tracked checkpoint probe 仍绑定 executor-local integration `d400c003...`，不能被当作最终 reviewed integration 的 exact runtime receipt。

## 必须新增的 executed known-bad

至少覆盖以下真实变异，均必须走真实 validator/transaction path 并非零退出：

```text
current_runtime_bundle_old_integration
current_runtime_bundle_old_implementation_identity
current_runtime_bundle_old_verifier_fingerprint
current_runtime_identity_receipt_old_tuple
current_runtime_identity_artifact_omitted_from_manifest
current_checkpoint_receipt_old_integration_tuple
post_integration_bundle_self_reference_or_previous_fingerprint_reuse
```

mutation 不能按 ID 直接返回失败，也不能只做字符串黑名单。需要实际修改 fixture/artifact 内容后调用相同的生产验证逻辑。

## 最终事务顺序

Verifier 完成本轮 source/test 修复并冻结新的 pre-Executor fingerprint 后，交 Controller 集成；再由原 Executor thread 按新 oracle 修 implementation/provenance。之后 Controller 必须生成新的 round-1 runtime manifest，运行精确 hosted CI；只有 CI 对最终 reviewed integration 成功后，原 production Verifier thread 才执行最终 post-CI transaction gate。

最终交回 Planner 前必须同时满足：

```text
executable_verifier_receipt.passed = true
failure_count = 0
transaction gate = PASS
frozen_verifier_validation_result.passed = true
runtime manifest = current round/current tuple/exact receipt hashes
current runtime identity = same current tuple
hosted CI actual head = reviewed integration
```

不得训练、访问 outer、部署、上传、构建 Docker 或合并 `develop` 到 `main`。不得修改 implementation 来替 Executor 修问题。
