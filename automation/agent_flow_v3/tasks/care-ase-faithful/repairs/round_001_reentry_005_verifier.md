# CARE-ASE Planner → Verifier 精确返修（round 1 / reentry 5）

恢复本任务已绑定的 production Verifier thread / CODEX_HOME / worktree。只修改 Verifier 获授权的 validators、tests 与 verification artifacts；不得修改 CARE-ASE 实现，不得训练、访问 outer、部署、上传或合并 develop 到 main。

本轮绑定：request nonce `care-ase-20260806T090955Z`；冻结合同 SHA256 `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d`；Planner 审阅 integration `d643c80ce15aa77a28ffb0bec6661afac5be3237`；implementation fingerprint `dd5593f869823de7fe0b76f953c3ea1ade6d0c1426a7e26a39a4ae1aea6fa692`；verifier fingerprint `7bdf871a1bd13c7f3faf30350b0c73797dd5818a90622be892917ebe875803ad`；审阅记录 `results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_005.json`；结论 `PLANNER_REVISE_BOTH`。

先完整读取冻结合同、Planner review、当前 Verifier 源码与当前实现，再修以下阻断项。

## 1. 修复 partial-H/W 跨 z 泄漏验证盲区

当前 `SliceExtentHead` 在 H/W pooling 时按像素 mask，但 partial-H/W slice 仍形成非零 sequence input，再进入 kernel=3 的 Conv1d 序列，因此 fully-valid 邻片的 loss 可能通过 z 卷积向 partial slice feature 反传。现有 partial-H/W probe 直接构造 presence/area logits，绕过真实 `SliceExtentHead`，无法发现这一点。

Verifier 必须新增真实端到端 oracle：构造一个 partial-H/W slice 紧邻 fully-valid slice 的输入，真实经过 `SliceExtentHead` 的 pooling + Conv1d；只对 fully-valid 邻片的 extent objective 反传。必须要求 partial slice 输入 feature 的梯度严格为零，同时 fully-valid 邻片保持非零梯度。再增加真实 mutation：去掉 full-slice pre-sequence mask / 恢复逐像素-only pooling 语义时必须非零退出。不得只对最终 loss 或 bias 做 mask 来冒充修复。

## 2. 验证当前 Agent-Flow 合同与 checkpoint/runtime provenance

当前 formal checkpoint/runtime 仍大量继承历史 R2 provenance；Verifier 不能只验证旧 `effective_contract_sha256`、`origin_main_sha` 或 permit 字段。新的 checkpoint/resume oracle 必须独立要求并核对当前 request nonce、当前冻结合同 SHA256、当前 implementation/source/integration provenance，并对 wrong/missing nonce、wrong/missing frozen-contract SHA、硬编码旧 active result/permit binding 等 known-bad 实际 fail-closed。

旧 v8/v9 effective contract 可作为次级来源证明，但不能替代当前 Agent-Flow 冻结合同。hard-negative manifest 仍需保持 same-fold patient-held-out OOF、真实 source checkpoint/prediction/hash/geometry 证明。

## 3. 重新定义真正可冻结的 Verifier fingerprint

当前 fingerprint 把 implementation-dependent 的 executable receipt、integrated validation、protected/runtime mutation execution outputs 等运行后产物的 hash 纳入 fingerprint。这样 Executor 或 integration 一变化，Verifier fingerprint 自身必然变化，破坏“Verifier-first freeze → Executor bind”的顺序。

必须把 frozen verifier identity 限定为 pre-Executor immutable inputs：冻结合同/requirement truth、Verifier 源码、public/protected test definitions、mutation definitions/manifests 等。implementation-specific executable receipt、integrated validation、mutation execution outputs、CI result 必须作为独立 runtime evidence，反向绑定 frozen verifier fingerprint、implementation fingerprint、integration SHA、nonce、contract SHA、review round，但不得改变 frozen verifier fingerprint。

必须证明：对至少两个不同 implementation / integration 重新执行同一个冻结 Verifier 后，frozen verifier fingerprint 完全不变；而伪造旧 transaction tuple / stale receipt 仍被 transaction gate 拒绝。

## 4. 保留已经关闭的问题，不得回退

必须继续保留并实际执行：独立 loss semantic oracle（injury Dice+BCE；scar pure component-adaptive Tversky）、对应 focal/occupancy mutation；verifier-owned final-authority removal 与 named-projection gradient；no-T2 子图/竞争/梯度隔离；partial-H/W fully-valid 邻片监督；真实 tile-local inference 与 full-support pseudo-tiling known-bad；checkpoint/resume RNG/cursor；deployment self-contained load；evaluator 与 hard-negative binding。

## 5. 交接顺序

本轮 Verifier 修好上述 oracle 与 immutable fingerprint 架构后，先冻结新的 Verifier fingerprint，再交回 Controller。Controller 随后必须恢复精确 Executor thread，让 Executor 修实现并把 implementation evidence/fingerprint 绑定到这个新 Verifier。Executor 集成后，Verifer 必须针对最终精确 integration 再独立执行一次；最终 executable receipt 必须 `passed=true`、transaction failures 为空，并绑定最终 integration 与 exact hosted CI。pre-CI expected failure 不能作为 Planner-ready PASS。

不得自行修改 CURRENT 伪造一致性，也不得通过删除 transaction checks、降级 known-bad 或放宽科学合同来通过。
