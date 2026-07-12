# TODO：修复 CARE Controller 的 Slurm 启动失败恢复与错误 Block 问题

## 目标

修复 CARE agent-flow 中以下系统性缺口：

```text
已获授权的 Slurm formal training job 因环境或包装器启动故障失败
→ packet 正确写成 NEEDS_EVIDENCE / RUNTIME_FAILURE
→ controller 却把“当前不能宣称完成”误解为“当前任务不能继续”
→ 要求用户重新授权本来已经授权的同一批 training jobs
→ active goal 被过早终止
```

本 TODO 是通用协议与执行基础设施修复任务，不是新的科学 milestone，不修改 M10 科学公式、variant、训练预算、split、metric 或 route decision，不执行 M10，不提交训练 job，不写任何 runtime `review.md`。

本次事故基线：

```text
commit: 79c28efdcf823fae9830593443a742a3664c4d56
message: Record M10 wave2 terminal failure packet
failed jobs:
  58644072
  58644073
  58644074
  58644106
  58644107
  58644108
  58644109
shared failure:
  ModuleNotFoundError: No module named 'mpmath'
environment repair:
  sympy 1.14.0
  mpmath 1.3.0
  torch.optim.AdamW initialization PASS
```

旧 jobs 必须保持失败历史，训练 credit 为零。此 TODO 只防止以后把可恢复的 operational failure 错误升级为永久 block。

---

## 一、根因

### 1. 状态定义存在，但没有恢复转换

当前 `prompts/HANDOFF_STATE_MACHINE.md` 能区分：

- `NEEDS_MONITOR`：仍在 pending/running/accounting；
- `NEEDS_EVIDENCE`：terminal execution 后证据缺失；
- `NEEDS_REVISION`：实现或 packet 需要修复；
- failed job 是 runtime failure evidence，不是 scheduler block。

但没有定义：

```text
RUNTIME_FAILURE / NEEDS_EVIDENCE
→ operational defect repaired
→ same-scope replacement attempt
→ EXECUTOR_RUNNING / NEEDS_MONITOR
```

因此 controller 可以把 outcome state 当成不可恢复的 task terminal state。

### 2. 没有“同范围 operational retry 默认已授权”的规则

当前协议没有明确写出：只要不改变 task、executor、scientific design、variant、预算、split、配置语义和 write scope，因以下原因发生的 replacement submission 属于原授权的一部分：

- 缺 Python 包；
- 环境激活错误；
- import path / wrapper 启动错误；
- Slurm header 或命令拼装错误；
- transient node / preemption；
- runtime output path 或 lock setup 的可修复错误。

于是 controller 自行发明了“需要新的显式授权”。

### 3. `afterany` 被错误用于 training-to-training dependency

M10 Wave 2 的七个正式任务被手工提交为：

```text
D0 --afterany--> D1 --afterany--> D2 --afterany--> D3
   --afterany--> refresh --afterany--> no-context --afterany--> alignment
```

D0 启动失败后，其余六个仍被调度并在相同位置失败。

正确语义应为：

```text
formal training stage → next required training stage: afterok
all training attempts → accounting/finalizer: afterany
```

`afterany` 应保留给终态核算，不应默认用于有成功前置条件的后续训练。

### 4. Finalizer 只会停止，不会提供可执行恢复分类

当前 `scripts/ops/care_milestone_finalizer.py` 将任一 failed state 汇总为：

```text
RUNTIME_FAILURE
```

随后 `scripts/ops/start_care_tmux_watcher.py` 对 `RUNTIME_FAILURE` 直接 `STOP_FAILURE`。

它们没有输出：

- failure class；
- 是否 retryable；
- 是否仍在原 task scope；
- 是否需要返回 Wave 1；
- 是否需要 GPT planner；
- replacement attempt 的所需字段；
- old/new job lineage。

### 5. Schema 和 validator 没有约束 retry / dependency semantics

当前 executor-plan schema 主要验证 lane、路径隔离、completion token 和 merge order，没有验证：

- training dependency 必须是 `afterok`；
- finalizer dependency 必须是 `afterany`；
- retry policy；
- preflight；
- replacement job ledger；
- retry 是否增加 executor count；
- old failed job 是否错误计入训练预算。

### 6. 缺少该事故的 known-bad regression test

没有测试阻止以下错误：

```text
startup failure + environment repaired
→ controller writes NEEDS_HUMAN_APPROVAL or NEEDS_GPT_PLANNER
→ no scientific scope change exists
```

也没有测试阻止 training job chain 使用 `afterany`。

---

## 二、必须修改的协议文件

### 2.1 `prompts/HANDOFF_STATE_MACHINE.md`

增加明确的状态层级和恢复转换。

必须写清：

1. `NEEDS_EVIDENCE` 是 packet/evidence outcome，不自动撤销 execution authorization。
2. failed job 是 runtime failure，不是 scheduler block。
3. 同范围 operational repair 后，controller 可以将同一 executor 恢复到：

```text
EXECUTOR_RUNNING
OPERATIONAL_RETRY_RUNNING
NEEDS_MONITOR
```

4. replacement attempt 不增加 `executor_count`，因为它是同一 executor 的新 attempt。
5. 只有科学或权限边界变化才进入 `NEEDS_GPT_PLANNER` / `NEEDS_HUMAN_APPROVAL`。
6. 定义受控 block taxonomy，禁止使用无原因的裸 `BLOCKED`：

```text
BLOCKED_PREREQUISITE
BLOCKED_EXTERNAL_RESOURCE
BLOCKED_PERMISSION
BLOCKED_SCHEDULER_SATURATION
BLOCKED_UNRESOLVED_WORKTREE_CONFLICT
NEEDS_REVISION_RETURN_TO_PREVIOUS_WAVE
NEEDS_GPT_PLANNER
```

7. 明确以下不是 block：

```text
old jobs failed
current packet is NEEDS_EVIDENCE
replacement job IDs are needed
aggregator must be rerun
branch is not pushed
ordinary pending below scheduler threshold
same-scope environment repair completed
```

### 2.2 `prompts/AGENT_FLOW_V2_PROTOCOL.md`

新增 `Operational Failure Recovery` 章节。

最低规则：

```text
A same-task, same-executor, same-command-semantics replacement attempt after an
operational startup/runtime defect is already authorized by the original task.
It does not require a new planner decision and does not consume another executor slot.
```

必须区分：

- operational retry：环境、wrapper、node、preemption、路径、lock、启动依赖；
- implementation revision：需要修改当前 executor write scope 内的代码；
- previous-wave revision：需要修改冻结的 shared files；
- planning revision：需要改变 variant、公式、预算、split、task graph、executor count、外部资源权限或科学决策门。

明确 controller 不得因为 `NEEDS_EVIDENCE` 自行结束 goal；应先检查是否存在 task-local recovery path。

### 2.3 `prompts/CONTROLLER_TASK_PROTOCOL.md`

新增 controller 的强制恢复决策表：

| 情况 | controller 动作 |
|---|---|
| job pending/running/accounting | `NEEDS_MONITOR`，继续 continuity |
| startup failure，修复仍在 executor scope | 原 executor replacement attempt |
| preemption/node failure，同配置可恢复 | resume/replacement attempt |
| terminal success但 output缺失 | rerun collector/aggregator；仍缺失才 `NEEDS_EVIDENCE` |
| 需要修改当前 executor允许的 wrapper/helper | task-local revision 后重试 |
| 需要修改冻结 shared architecture/loss | `NEEDS_REVISION_RETURN_TO_PREVIOUS_WAVE` |
| 需要改变科学设计/预算/split/graph | `NEEDS_GPT_PLANNER` |
| 权限、数据、许可证无法解决 |受控 external/permission blocker |

增加硬规则：

```text
controller must cite the exact contract field that requires new human/planner
approval; absent such a field or a real scope change, it must not invent an
approval gate.
```

Controller report 中若写 `next_required_action: obtain explicit authorization`，validator 必须要求同时存在：

```text
authorization_reason
changed_contract_fields
out_of_scope_paths_or_actions
why_operational_retry_is_insufficient
```

否则 fail closed。

### 2.4 `prompts/HANDOFF_GATE_POLICY.md`

增加以下 gate principle：

```text
Fail-closed means “do not claim completion without evidence”.
It does not mean “stop attempting authorized task-local recovery”.
```

写明只有 machine-checkable scope change 才能要求 GPT/user approval。

增加 known-bad cases：

1. repaired dependency failure incorrectly requests new user authorization；
2. `NEEDS_EVIDENCE` incorrectly treated as permanent STOP；
3. failed job incorrectly classified as scheduler block；
4. pending under 24 hours incorrectly classified as scheduler block；
5. retry counted as a new executor；
6. old failed attempt contributes optimizer steps or train-loop seconds；
7. training-to-training dependency uses `afterany` without explicit independent-stage justification；
8. downstream stage starts after required upstream failure；
9. finalizer uses `afterok` and therefore fails to collect failed-job accounting。

### 2.5 `.agents/skills/slurm-routing-partition/SKILL.md`

新增完整的 `Preflight and Replacement Submission` 章节。

必须要求：

1. 每个正式训练链在首个 GPU job 前运行与正式环境相同的 compute-environment preflight；不能只在 login node import。
2. 至少验证：

```text
python executable
critical imports
optimizer construction
CUDA visibility when required
config parse
output/log/lock parent writability
entrypoint --print-contract or equivalent dry run
```

3. 默认依赖：

```text
training stage requiring upstream success: afterok
independent training stages: no dependency or explicit plan-declared dependency
accounting/finalizer over all attempts: afterany
```

4. 允许 bounded same-scope retry，建议默认：

```yaml
max_startup_retries: 2
max_preemption_retries: 2
max_unknown_retries: 0
```

5. retry 前必须校验 command/config/code/split fingerprint；任何语义变化都不能伪装成 retry。
6. 旧失败 job 永久保留，training credit 全部为零。
7. replacement receipt 必须记录 old/new job ID 与理由。
8. 一个 job failure 不得自动被称为 goal blocked。

---

## 三、必须修改的 schema 与 validator

### 3.1 `prompts/schemas/executor_plan.schema.yaml`

为 Slurm executor 增加或条件要求以下字段：

```yaml
retry_policy:
  operational_retry_allowed: true
  same_executor_attempt: true
  max_startup_retries: 2
  max_preemption_retries: 2
  max_unknown_retries: 0
  require_same_code_hash: true
  require_same_config_hash: true
  require_same_split_hash: true
  failed_attempt_training_credit: zero

slurm_dependency_policy:
  training_dependency: afterok
  finalizer_dependency: afterany

preflight:
  required: true
  command: <exact command or helper invocation>
  receipt_path: results/<task_key>/executors/<executor_id>/preflight_receipt.json

retry_ledger_path: results/<task_key>/executors/<executor_id>/replacement_job_ledger.csv
```

对于非 Slurm executor 可不要求这些字段。

### 3.2 `prompts/schemas/controller_packet.schema.yaml`

当发生 replacement attempt 时，条件要求：

```text
replacement_job_ledger.csv
operational_retry_receipt.json
preflight_receipt.json
```

`finalizer_state.json` 增加受 schema 检查的字段：

```text
failure_class
retryable
suggested_next_state
attempt_number
supersedes_job_ids
replacement_job_ids
training_credit_policy
```

### 3.3 如有必要新增 `prompts/schemas/runtime_retry.schema.yaml`

若不希望把 retry 细节塞入 executor-plan schema，可新增独立 schema，但必须被 active policy 与 validator 实际读取，不能成为无人调用的文档。

### 3.4 `scripts/ops/validate_executor_plan.py`

新增检查：

- Slurm executor 是否声明 retry policy 和 preflight；
- required-success chain 是否使用 `afterok`；
- finalizer 是否使用 `afterany`；
- retry ledger 路径是否在 executor 自己的 result scope；
- retry 不得创建新 executor id；
- max retry 非负且有上限；
- `failed_attempt_training_credit` 必须为 `zero`；
- `afterany` training dependency 必须有显式 `independent_of_upstream_success: true` 和理由，否则失败。

Fallback YAML parser 也必须支持新增 nested fields，或者明确要求 PyYAML 并 fail closed；不能在无 PyYAML 时静默忽略 retry policy。

### 3.5 `scripts/validation/validate_handoff_policy.py`

新增 packet/controller 检查：

- `NEEDS_EVIDENCE` 后若写“需要新授权”，是否存在真实 scope change；
- replacement attempt 是否有 old/new job lineage；
- failed attempts 是否错误计入有效 steps/seconds；
- failed job 是否错误标为 scheduler block；
- scheduler block 是否具有 12 次、每次间隔 2 小时、累计 24 小时证据；
- current task scope 内可修复却直接 `STOP/BLOCKED` 的 packet 必须失败；
- retry 后状态应回到 running/monitor，而不是继续引用旧 `NEEDS_EVIDENCE` 作为拒绝执行理由。

---

## 四、必须修改或新增的执行代码

### 4.1 新增 `scripts/ops/run_care_training_preflight.py`

建议提供统一 helper，输出 JSON receipt。

输入至少包括：

```text
--python
--entrypoint
--config
--result-dir
--log-dir
--lock-path
--import <module> (repeatable)
--optimizer-smoke-command
--contract-command
--receipt-path
```

输出：

```json
{
  "exit_code": 0,
  "python": "...",
  "python_version": "...",
  "imports": {},
  "optimizer_smoke": "pass",
  "cuda_visible": true,
  "config_hash": "...",
  "code_hash": "...",
  "split_hash": "...",
  "path_writability": {},
  "checked_at_utc": "..."
}
```

正式 submission helper 必须拒绝缺失或失败的 preflight receipt。

### 4.2 新增 `scripts/ops/submit_care_training_chain.py`

不要再让 executor 手写七条 `sbatch --dependency=...`。

helper 应读取 machine-readable chain manifest，例如：

```yaml
stages:
  - id: D0
    script: jobs/src/run_...d0.sh
    requires_success_of: []
  - id: D1
    script: jobs/src/run_...d1.sh
    requires_success_of: [D0]
```

行为：

- 默认用 `afterok` 构造 required-success dependency；
- 输出完整 submission receipt；
- 记录 stage→job ID；
- 记录 command/config/code/split hash；
- 支持 `--replacement-for <old receipt>`；
- replacement 只能保持相同 stage graph 和 fingerprints；
- 自动生成 `replacement_job_ledger.csv`；
- old attempt 标记 zero credit；
- 自动把 old+new job IDs 交给 finalizer submission；
- 不负责科学重规划。

### 4.3 修改 `scripts/ops/submit_care_dependency_finalizer.py`

保持 `afterany`，但强化其用途边界：

- docstring 和 receipt 明确 `finalizer_only: true`；
- 拒绝被当作 training-chain helper；
- receipt 记录所有 attempt job IDs，而不仅是最新 replacement IDs；
- 可区分 `effective_training_job_ids` 与 `failed_attempt_job_ids`。

### 4.4 修改 `scripts/ops/care_milestone_finalizer.py`

不要只输出笼统的 `RUNTIME_FAILURE`。

增加 failure classification 输入或逻辑，至少支持：

```text
STARTUP_ENVIRONMENT_FAILURE
STARTUP_WRAPPER_FAILURE
PREEMPTED_RETRYABLE
NODE_FAILURE_RETRYABLE
OUT_OF_MEMORY_NEEDS_REVISION
MODEL_OR_DATA_FAILURE_NEEDS_REVISION
UNKNOWN_RUNTIME_FAILURE
```

Finalizer 输出：

```text
failure_class
retryable
retry_reason
suggested_next_state
attempt_number
job_attempt_lineage
training_credit
```

推荐状态映射：

```text
retryable operational failure + attempts remain
  → OPERATIONAL_RETRY_REQUIRED

retryable but retry budget exhausted
  → NEEDS_EVIDENCE / NEEDS_REVISION with exact reason

shared architecture/model defect
  → NEEDS_REVISION_RETURN_TO_PREVIOUS_WAVE

scientific contract change required
  → NEEDS_GPT_PLANNER
```

Finalizer 不应自行改变科学配置；可以交回 controller 进行受控 retry。

### 4.5 修改 `scripts/ops/start_care_tmux_watcher.py`

目前对任何 `RUNTIME_FAILURE` 直接 `STOP_FAILURE`。

应增加：

```text
OPERATIONAL_RETRY_REQUIRED
STARTUP_FAILURE_RETRYABLE
PREEMPTED_RETRYABLE
```

这些状态应：

- 停止当前 finalizer polling；
- 返回明确的 `HAND_BACK_TO_CONTROLLER_FOR_SAME_SCOPE_RETRY`；
- 不写 task permanently blocked；
- 不要求 GPT/user，除非 finalizer 证明 scope change。

### 4.6 训练预算聚合器

所有正式 training aggregators 必须按 attempt lineage 计算 credit：

```text
failed startup attempt: 0 steps, 0 seconds
preempted attempt: only verified completed optimizer steps/seconds may be cumulative
replacement attempt: cumulative only when code/config/split fingerprints match
reset run with changed semantics: new run, not retry
```

M10 的 `scripts/evaluation/aggregate_srr_v3_m10_myops.py` 可作为 regression fixture，但通用逻辑应尽量放在 reusable helper 中，避免每个 milestone 重新实现。

---

## 五、必须增加的回归测试

新增或扩展测试文件，建议：

```text
src/care_myocardium/tests/test_operational_retry_policy.py
src/care_myocardium/tests/test_slurm_dependency_semantics.py
src/care_myocardium/tests/test_controller_block_taxonomy.py
src/care_myocardium/tests/test_care_milestone_finalizer.py
src/care_myocardium/tests/test_handoff_policy_validator.py
```

最低测试矩阵：

### Good fixtures

1. startup missing package → repair → same-scope replacement → accepted；
2. preemption → same checkpoint/config resume → accepted；
3. training chain uses `afterok`；
4. finalizer uses `afterany` over all attempts；
5. old failed attempt preserved with zero credit；
6. replacement job IDs do not increase executor count；
7. terminal successful replacement outputs aggregate and proceed。

### Known-bad fixtures

1. `NEEDS_EVIDENCE` 被当成永久 `STOP`；
2. 无 scope change 却写 `obtain explicit authorization`；
3. D0 failed 后 D1 通过 `afterany` 启动；
4. finalizer 使用 `afterok`，导致失败 job 无 accounting；
5. failed 11-minute startup 被计入 train-loop seconds；
6. replacement 更改 config/split，却仍标 same retry；
7. retry 伪装成第四个 executor；
8. 普通 pending 未满 24 小时就标 scheduler block；
9. runtime failure 标 scheduler block；
10. preflight 只在 login node 运行、compute environment 未验证；
11. retry 次数无限；
12. retry ledger 缺 old/new job ID；
13. finalizer/watchdog 把 retryable failure 写成 permanent blocked；
14. controller 引用旧 initialization/maintenance 边界覆盖当前 scientific contract。

使用当前 M10 七 job 事故作为固定 regression fixture：

```text
first job elapsed: 00:11:04
remaining jobs elapsed: 00:00:42 or 00:00:43
all state: FAILED
all exit: 1:0
failure: missing mpmath
repair: optimizer smoke PASS
expected next action: same Wave 2 replacement attempt, not new planning authorization
```

---

## 六、文档优先级判断

本问题不是只改 handoff，也不是只改 Slurm skill。

必须同时改：

1. **状态机**：定义可恢复转换；
2. **handoff/controller policy**：禁止把缺证据等同永久终止；
3. **Slurm skill**：定义 preflight、retry 与依赖类型；
4. **schema/validator**：把规则变成机器可检查；
5. **submission helper**：避免手写错误 dependency chain；
6. **finalizer/watcher**：输出 retryability，而不是笼统停止；
7. **tests**：用本次事故防回归。

只改 prompt 文案仍会复发，因为 Codex 可以再次从模糊状态推导出“保守停止”。只改 Python 也不够，因为 planner/controller contract 仍可能把 retry 解释成越权。必须协议和执行层同时闭环。

---

## 七、完成标准

Codex 完成修改后必须：

1. 列出全部修改文件与理由；
2. 不执行 M10、不提交任何普通 Slurm training job；
3. 不修改 M10 科学合同、结果指标或已有失败 job 历史；
4. 运行并通过：

```bash
python scripts/validation/validate_handoff_policy.py --policy --warnings-as-errors
python scripts/validation/validate_handoff_policy.py --repository-readiness --warnings-as-errors
python scripts/ops/validate_executor_plan.py prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
pytest -q src/care_myocardium/tests/test_operational_retry_policy.py
pytest -q src/care_myocardium/tests/test_slurm_dependency_semantics.py
pytest -q src/care_myocardium/tests/test_controller_block_taxonomy.py
pytest -q src/care_myocardium/tests/test_care_milestone_finalizer.py
pytest -q src/care_myocardium/tests/test_handoff_policy_validator.py
git diff --check
```

如果实际测试路径不同，可调整，但必须覆盖上述行为。

5. 写维护结果包，例如：

```text
results/20260712_operational_retry_and_slurm_recovery_protocol_repair/
```

至少包含：

```text
result.md
implementation_snapshot.md
protocol_change_matrix.csv
state_transition_matrix.csv
slurm_dependency_test.md
operational_retry_selftest.md
known_bad_selftest.csv
validator_report.md
commands_run.md
completion_check.md
review_request.md
MANIFEST.md
```

6. 本地提交轻量文件后停止；不写 `review.md`，不 push，交由独立 reviewer 审阅。

---

## 八、最终预期行为

修复后，遇到同类事故应自动遵循：

```text
formal job startup failure
→ terminal accounting records failure
→ classify operational retryability
→ failed attempt gets zero training credit
→ task-local environment/wrapper repair
→ compute-environment preflight
→ same executor, same wave, same contract replacement submission
→ EXECUTOR_RUNNING / NEEDS_MONITOR
→ terminal accounting and aggregation
→ only then decide completion/review
```

只有发生真实 scope change、冻结层代码缺陷、权限/资源不可解、retry budget exhausted 或满足严格 scheduler saturation 门槛时，才允许返回受控 blocker。