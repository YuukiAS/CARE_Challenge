# CARE-ASE Planner → Executor 精确返修（round 1 / reentry 6）

必须在 Verifier 完成 reentry 6 的新 oracle/fingerprint 冻结并由 Controller 集成后，恢复当前 `care-ase-faithful` 的原 production Executor thread。只修改 implementation/runtime 范围，不得修改 Verifier 源码或测试。

本轮返修来源绑定：

```text
request_nonce: care-ase-20260806T090955Z
frozen_contract_sha256: a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d
reviewed_integration_commit_sha: 965b0aadaf436e11abdf37dfe3ce6699e928b7b0
reviewed_implementation_fingerprint_sha256: e7a6bfe00336354da7debf7321966c8a72c7ce43ee0bb00c316387c72659b7e3
reviewed_verifier_fingerprint_sha256: 6acc8fdc640df9be54848dfc676da45257d887c0f4be5ce71efa6230114a4a17
planner_review: results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_006.json
planner_decision: PLANNER_REVISE_BOTH
```

实际实现必须绑定 Controller 集成后的 reentry 6 新冻结 Verifier fingerprint；不得继续绑定上面作为“被审阅旧输入”的 verifier fingerprint。

## 唯一阻断实现问题：历史 R2 runtime identity 仍是活动默认真值

当前 `src/care_myocardium/training/care_ase_runtime.py` 仍存在并实际使用：

```text
TASK_KEY = 20260804_care_ase_r2_emergency_9h_training_docker
RESULT_DIR = results/<旧 TASK_KEY>
PROBE_RUNTIME_DIR = .../<旧 TASK_KEY>
EFFECTIVE_CONTRACT = CARE_ASE_R2_effective_contract_v9_20260803.yaml
CRITICAL_SOURCE_SEED_PATHS = 多个旧 20260803/20260804 task/controller/addendum
历史 training permit decision / task path 校验
formal target manifest task_key == 旧 TASK_KEY
```

`src/care_myocardium/training/care_ase_sampler.py` 还把 hard-negative 默认 manifest 写死为：

```text
results/20260804_care_ase_r2_emergency_9h_training_docker/hard_negative_manifest_fold{fold}.json
```

并以历史 task-key allowlist 判断 manifest 合法性。

冻结合同允许历史 v8/v9 科学合同、OOF prediction/checkpoint 等作为显式、哈希绑定的来源资产，但明确要求旧 main/result/permit 路径参数化并绑定当前 `care-ase-faithful` nonce、冻结合同和精确提交。现在这种实现会让未来人工授权 formal training 继续落入旧任务 lineage，因此必须修。

## 必须实现

建立单一明确的当前 runtime input bundle/配置入口，使 probe、formal training、resume、deployment 需要的身份字段至少包括：

```text
task_id = care-ase-faithful
request_nonce
frozen_contract_sha256
implementation_source_manifest_sha256
implementation_fingerprint_sha256
integration_commit_sha
fold
explicit result/probe root
explicit hard-negative manifest path + manifest SHA
secondary effective v8/v9 contract path + SHA（若仍需要）
formal user decision/permit provenance（仅未来人工授权后才可提供）
```

要求：

1. formal runtime 在任何 materialization/forward/optimizer step 前验证上述当前事务字段；缺失或错配必须 fail closed。
2. 历史 `20260804...` permit 决策或 task document 不得被当前任务接受为 formal training 授权；当前 Planner 决策仍不是训练许可。
3. result/probe root 不得由旧 TASK_KEY 隐式决定。probe 可写当前任务的零信用临时路径，但不得污染历史 formal result 或正式 checkpoint lineage。
4. hard-negative manifest 必须由当前 runtime bundle 显式传入；继续核验精确 fold、patient-held-out OOF、source checkpoint/prediction SHA、preprocessed geometry，但不要用历史 task_key allowlist 充当当前 provenance。
5. 当前 checkpoint schema 已加入 nonce/contract/source/integration 字段，必须保留；formal save 与 resume 调用链必须从当前 runtime bundle 传入这些值，不能只让 helper 支持参数却由正式入口继续传历史/UNSET 值。
6. deployment/resume 必须验证同一当前 provenance；secondary v8/v9 contract hash 可以记录，但不得覆盖 frozen_contract_sha256。
7. 任何旧 import wrapper 若保留，只能薄转发到唯一实现，不能保留第二套历史 runtime 真值。

## 必须提交的证据

基于 Verifier 新冻结版本重建 implementation evidence/fingerprint，并至少提供：

- 当前 runtime bundle 的结构化 receipt 与内容 SHA；
- 旧 TASK_KEY、旧 permit、旧 result root 注入当前 formal runtime 时，在 forward 前 fail closed；
- nonce、frozen contract、integration、implementation fingerprint 任一缺失/错配时 fail closed；
- hard-negative manifest 由显式当前 bundle 传入，且 OOF checkpoint/prediction/geometry 绑定仍通过；
- checkpoint save→resume dry-run 对当前 nonce/合同/source/integration 精确匹配，错配拒绝；
- no formal training started、no outer access、no deployment/upload 的机器证据。

这些只能是零信用 probe/dry-run；不得为了“证明可运行”启动 14,000-step 正式训练。

## 禁止绕过

- 不得只改 receipt/字段名称而保留旧 TASK_KEY、旧 permit 或旧 manifest 默认路径。
- 不得把 `care-ase-faithful` alias 成 `20260804...` 来让旧检查通过。
- 不得删除 provenance 检查来换取兼容。
- 不得修改 Verifier 以适配你的实现。
- 不得访问 outer、正式训练、合并 `develop`→`main`、部署、构建/上传 Docker 或提交 validation/challenge。

完成后交 Controller 集成；Controller 必须生成当前 review round 的 runtime manifest、运行本地 gates、推送新的精确 `develop` integration，并等待该 exact SHA 的 hosted CI。CI 成功后还必须由 Verifier 对最终 tuple 做 post-CI transaction recheck，之后才可再次交 Planner。