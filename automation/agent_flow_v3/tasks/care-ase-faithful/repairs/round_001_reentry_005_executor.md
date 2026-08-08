# CARE-ASE Planner → Executor 精确返修（round 1 / reentry 5）

恢复本任务已绑定的 production Executor thread / CODEX_HOME / worktree。只修改 Executor 获授权的 CARE-ASE 实现与 implementation artifacts；不得修改 Verifier tests/validators，不得训练、访问 outer、部署、上传或合并 develop 到 main。

本轮绑定：request nonce `care-ase-20260806T090955Z`；冻结合同 SHA256 `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d`；Planner 审阅 integration `d643c80ce15aa77a28ffb0bec6661afac5be3237`；implementation fingerprint `dd5593f869823de7fe0b76f953c3ea1ade6d0c1426a7e26a39a4ae1aea6fa692`；verifier fingerprint `7bdf871a1bd13c7f3faf30350b0c73797dd5818a90622be892917ebe875803ad`；审阅记录 `results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_005.json`；结论 `PLANNER_REVISE_BOTH`。

必须等 Verifier 先完成本轮 oracle 与 immutable fingerprint 修复并冻结新的 Verifier fingerprint 后，再恢复此 Executor。不要基于本提示中的旧 verifier fingerprint直接生成最终 evidence。

## 1. 修复 SliceExtentHead 的 partial-H/W 跨 z 信息与梯度泄漏

当前 `SliceExtentHead.forward` 只在 H/W 汇聚时对 valid pixels 做 mask；partial-H/W slice 仍可产生非零 `sequence_input`，随后进入 kernel=3 的 Conv1d 序列。这样 fully-valid 邻片的 extent loss 可以通过 z 卷积依赖 partial slice feature，并向该 partial slice 反传梯度。冻结合同要求 partial-H/W slice 的 extent bias、loss、gradient 都为零，这包括不能作为相邻有效切片的序列证据来源。

必须在进入 Conv1d 序列之前计算 full-H/W-valid 的 per-z mask，并使 partial/all-invalid slice 的 sequence input 对后续序列严格为零，同时保持 fully-valid 邻片的真实 extent supervision 与非零梯度。训练和推理的 validity 语义必须一致；不得只在最终 loss/bias 上再乘 mask，不得使用 `loss-loss.detach()`、straight-through 或整卷关闭 extent head。

修复后必须由新的 Verifier 真实端到端证明：只对 fully-valid 邻片 loss 反传时，partial slice 输入 feature 梯度为零；邻片梯度非零。

## 2. 把 schema-v4 checkpoint / formal runtime 绑定到当前 Agent-Flow 事务

当前 checkpoint/runtime 仍以历史 R2 `effective_contract_sha256`、`origin_main_sha`、旧 task/result/permit 语义为中心，并没有把当前 request nonce 与本冻结合同 SHA 作为必需 provenance；`care_ase_runtime.py` 与 sampler 仍存在活动默认值硬编码旧 `20260804...` result/task 路径。

必须在不削弱已有精确 resume 能力的前提下：

- schema v4 formal checkpoint 增加并强制保存/验证当前 `request_nonce`、`frozen_contract_sha256`、当前 implementation/source/integration binding；
- resume 对 missing/wrong nonce、missing/wrong frozen-contract SHA、source/integration drift 必须 fail closed；
- 历史 v8/v9 effective contract、origin-main 等如仍有科研来源价值，可保留为次级 provenance，但不能替代当前冻结合同；
- formal runtime、hard-negative manifest 与结果根目录必须由当前任务/输入 bundle 参数化，不得把旧 task/result/permit 路径作为活动默认真值；
- hard-negative 仍必须严格使用 same-fold patient-held-out stock OOF，并保留 checkpoint/prediction/hash/geometry 证明；不得改成 in-fold 或当前 CARE-ASE 预测。

不得启动正式训练来验证这些改动；使用确定性 smoke/probe/checkpoint roundtrip 即可。

## 3. 重建 implementation evidence/fingerprint，并绑定 Verifier-first 冻结指纹

当前 `implementation_fingerprint.json` 与 `implementation_source_manifest.json` 仍嵌入旧 Verifier `3dcacf...`，而本轮 Planner packet 绑定的是另一代 Verifier。等 Verifier 完成新的 immutable fingerprint freeze 后：

- 重新生成 source manifest、implementation evidence、implementation fingerprint；
- fingerprint 必须绑定新的精确 frozen verifier fingerprint、当前 nonce、冻结合同 SHA、源文件哈希与所有 implementation runtime receipts；
- 不得手工改 fingerprint 字符串或在 CURRENT/planner packet 中伪造绑定；
- 所有上一轮已经修好的科学实现必须保持：injury Dice+BCE、纯 scar component-adaptive Tversky、真实 dilation residual、真实 tile-local inference、no-T2 graph exclusion、independent named evidence authority、partial-H/W final bias/loss mask 等。

## 4. 最终交接

Executor 完成后只提交 implementation role commit/evidence 给 Controller。Controller 集成后必须再恢复冻结的 Verifier，对最终精确 integration 独立执行全部验证；随后对同一 integration 跑 hosted CI，并在 CI 成功后形成 post-CI transaction receipt。只有 nonce + contract + requirement truth + integration + implementation fingerprint + frozen verifier fingerprint + runtime receipts + CI 全部一致时，才能再次交 Planner。

禁止任何为了让 Verifier 通过而删除模型模块、降低验证阈值、替换 protected tests、恢复旧降级实现或改冻结合同。
