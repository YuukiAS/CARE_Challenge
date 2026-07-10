---
task_key: "20260710_agent_flow_v2_history_parallel_chinese_followup"
project: "CARE_Challenge"
status: "READY"
task_type: "controller"
controller_mode: true
execution_mode: "controller_supervised"
requires_execution_controller: true
executor_slots: 1
mapper_slots: 1
mapper_required: true
architecture_impact: "system"
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: false
continuity_backend: "none"
review_mode: "independent_thread"
reviewer: "separate_readonly"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
auto_git_commit: true
allow_git_commit: true
auto_git_push: false
allow_git_push: false
allow_diagnostic_push: false
---

# CARE Agent-Flow v2 历史知识层、并行执行能力与中文 Wiki 修复

你是 CARE agent-flow v2 的 Codex maintenance controller。本任务只修复 handoff、controller/finalizer、版本化知识层、架构图、中文 wiki 和 validators。不要设计或执行 M10，不训练模型，不提交普通训练 Slurm job，不打包 validation，不上传，不修改历史 result packet。

当前基线 commit 之后已经实现了 canonical `prompts/AGENT_FLOW_V2_PROTOCOL.md`、Slurm dependency finalizer、root `wiki/` 和 D2 generator，但仍存在下述缺口。本任务必须关闭这些缺口后，用户才会制定 M10。

## 1. 开始前必须读取

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_ROLES.md
prompts/HANDOFF_STATE_MACHINE.md
prompts/CONTROLLER_TASK_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/templates/CONTROLLER_TASK_TEMPLATE.md
.agents/skills/care-mapper/SKILL.md
.agents/skills/slurm-routing-partition/SKILL.md
scripts/ops/care_milestone_finalizer.py
scripts/ops/submit_care_dependency_finalizer.py
jobs/src/care_milestone_finalizer.sh
scripts/validation/validate_handoff_policy.py
scripts/architecture/generate_care_architecture_wiki.py
scripts/architecture/validate_care_architecture_wiki.py
src/care_myocardium/tests/test_handoff_policy_validator.py
wiki/README.md
wiki/MODEL.md
wiki/EXECUTION.md
wiki/COMPONENTS.csv
wiki/LINEAGE.md
wiki/architecture.yaml
TODO.md
todo-m10.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md
```

检查最近 10 个 commit。确认当前 M9 follow-up token 是：

```text
M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY
```

不要从聊天推断状态。

## 2. 当前实现中必须修掉的问题

### 2.1 Finalizer 的 stale lock

当前 `care_milestone_finalizer.py` 使用 `O_EXCL` 创建 lock，但退出时只关闭文件描述符，没有删除 lock 文件。第一次运行后，后续人工 resume 或重试会永久命中 `FileExistsError`。

修复要求：

- lock 文件内容必须记录 PID、host、started_at、task_key；
- 正常退出和已处理失败退出时必须原子释放 lock；
- 异常中断遗留的 stale lock 必须可检测：PID 不存在、host 不同且超过 TTL、或显式 `--recover-stale-lock`；
- 不得静默删除仍有活进程持有的 lock；
- 添加 stale-lock、active-lock、retry-after-release 的测试。

### 2.2 `AWAITING_SACCT` 会导致 dependency finalizer 一次性退出

Slurm `afterany` job 启动时，accounting 可能暂时未刷新。当前 finalizer 将其写成 `NEEDS_MONITOR` 后退出，而 dependency job 不会自动重跑，overnight continuity 仍可能停住。

修复要求：

- finalizer 内部对 `AWAITING_SACCT` 做 bounded retry，例如每 30–60 秒检查一次，最长 10–20 分钟；
- retry 参数可配置并写入 receipt；
- 超时后写 `AWAITING_SACCT_RETRY_EXHAUSTED`，不得写 scheduler blocked；
- 可选择自动提交一个短 dependency/accounting-retry finalizer，但必须防止无限递归；
- synthetic tests 覆盖 accounting 第 1 次缺失、第 N 次出现、最终超时三种情况。

### 2.3 `tmux_watcher` 只有协议，没有实现

协议允许 `continuity_backend: tmux_watcher`，但当前没有 first-party watcher。

必须二选一：

1. 实现 `scripts/ops/start_care_tmux_watcher.py` 和对应 watcher loop；或
2. 从 active protocol/template/validator 中移除 `tmux_watcher`，只允许已实现的 `slurm_dependency`。

推荐实现 watcher，作为 dependency submission 失败时的真实 fallback。若实现，必须记录：

```text
session_name
pid
command
log_path
lock_path
result_dir
required_job_ids
poll_interval
started_at
```

watcher 必须使用 namespace-local tmux/session，不能依赖旧 `/nas` home 状态。

### 2.4 Finalizer、mapper、validator 和 commit 顺序不一致

canonical protocol 要求：terminal accounting -> aggregation -> mapper final -> validators -> controller report -> local packet commit。

当前 template 和 finalizer 实现仍存在以下风险：

- finalizer 可在 mapper final/最终 validator 前 commit；
- finalizer 代码先跑 validator，再跑 mapper final；
- controller 之后可能再次 commit，形成双 commit owner；
- dependency finalizer 运行时 controller report 可能尚未生成。

统一为两个确定性阶段：

```text
FINALIZER_A:
  terminal accounting
  runtime-output check
  aggregation
  write finalizer_state.json with READY_FOR_MAPPER_FINAL or failure state

MAPPER_FINAL:
  update current wiki/history delta when required
  write mapper_report_final.md and architecture_delta_final.md

FINALIZER_B:
  validate result packet
  validate wiki/current/history/diagrams
  validate controller receipts
  git diff --check
  local commit exactly once
```

允许用一个脚本的两个 mode：`--stage accounting` 与 `--stage commit`，或两个独立脚本。必须只有一个 local packet commit owner。reviewer 在 commit 后运行。

## 3. 增加安全的多 executor 并行能力

当前系统只有 `executor_slots` 数字和“不允许超额”检查，没有 machine-readable task graph、并行 wave、写入隔离、worktree、merge 顺序和真实 launcher。因此它还不具备安全并行能力。

### 3.1 新增 execution plan

每个 controller-supervised task 必须声明：

```yaml
executor_slots: 1               # 最大同时运行数，可由 GPT 在 milestone 前设为 2、3...
executor_count: 1               # 本任务 executor 总数，可大于 slots，通过多 wave 执行
parallel_execution_allowed: false
executor_plan_path: "prompts/tasks/<task_key>_executor_plan.yaml"
```

新增 machine-readable plan schema：

```yaml
version: 1
max_parallel: 2
executors:
  - id: myops_implementation
    prompt_path: results/<task_key>/subagents/myops_implementation_prompt.md
    wave: 1
    depends_on: []
    blocking: true
    can_run_parallel: true
    isolation_mode: separate_worktree
    branch_name: codex/<task_key>/myops_implementation
    worktree_path: <namespace-local path>
    read_scope: []
    write_scope: []
    shared_files_forbidden: []
    result_dir: results/<task_key>/executors/myops_implementation
    runtime_output_root: results/<task_key>/runtime/myops_implementation
    slurm_job_namespace: <unique prefix>
    merge_order: 1
```

### 3.2 并行准入规则

GPT 必须在 milestone 开始前决定数量、wave 和依赖关系。Controller 不能自行增加 executor 数量，也不能自行把顺序任务改成并行。

同一 wave 允许并行的充分条件：

- `can_run_parallel: true`；
- `depends_on` 已完成；
- code-writing executor 使用独立 git worktree/branch；
- `write_scope` 不重叠；
- `result_dir`、runtime output、Slurm job name/log/lock 全部隔离；
- 不共同修改 canonical shared prompts、`AGENTS.md`、root wiki current files、shared config 或同一个 source file；
- 共享文件只由 controller merge phase 修改；
- 资源预算允许，不因并行导致相同数据/cache/checkpoint 污染。

MyoPS 与 Cine 默认按顺序执行。只有 GPT 在 plan 中证明其 source/config/output/worktree/resource scope 独立时，才能放在同一 wave。

### 3.3 并行执行和合并

Controller 必须能够：

- 按 wave 启动不超过 `executor_slots` 的 subagents；
- 记录每个 session/subagent ID、prompt hash、worktree、branch、PID/command、start/end、exit status、commit；
- executor 只能提交自己的 branch；
- controller 是唯一 merge owner；
- 按 `merge_order` cherry-pick/merge；
- 发现冲突时停止为 `NEEDS_REVISION_PARALLEL_MERGE_CONFLICT`，不能让 LLM 静默重写冲突；
- 合并后重新运行 mapper、validators 和 tests；
- 清理 worktree 前确认 commit 已合并且无未提交文件。

新增 receipt：

```text
results/<task_key>/executor_plan.yaml
results/<task_key>/executor_launch_ledger.csv
results/<task_key>/executor_merge_ledger.csv
```

### 3.4 Validator known-bad

必须失败：

- `executor_slots > 1` 但没有 executor plan；
- 同一 wave 写入范围重叠；
- code-writing executor 共用同一 worktree；
- result/runtime/log/lock 路径冲突；
- controller 实际启动数超过 slots；
- 未完成 dependency 就启动；
- executor 直接改 canonical shared files；
- merge conflict 被忽略；
- controller 自行增加 executor 数量；
- MyoPS/Cine 未证明隔离却被默认并行。

更新 execution-flow 图：显示单 executor 默认路径，以及 GPT 明确授权时的 parallel executor waves；不要画成所有任务默认并行。

## 4. 建立版本化、组件级的架构分析知识层

根目录 `TODO.md` 是 M8 实现分析，`todo-m10.md` 是 M9 阶段分析。它们不是待办任务，不应继续留在根目录，也不应放入 `results/` 或 gitignore。

将它们迁移为 root wiki 下的 canonical history：

```text
wiki/history/
  README.md
  COMPARISON.md
  MIGRATION_MANIFEST.csv
  M08/
    README.md
    snapshot.yaml
    COMPONENTS.csv
    architecture.yaml
    components/
      availability-no-t2.md
      retrieval-dictionary.md
      prototype-memory.md
      anatomy-prior.md
      proposal.md
      refiner.md
      arbitration.md
      losses.md
      checkpoint-selection.md
      training-evidence.md
      cine-temporal.md
    figures/
      architecture.d2
      architecture.svg
      architecture.png
      gap.d2
      gap.svg
      gap.png
  M09/
    README.md
    snapshot.yaml
    COMPONENTS.csv
    architecture.yaml
    components/
      availability-no-t2.md
      retrieval-dictionary.md
      prototype-memory.md
      anatomy-prior.md
      proposal.md
      refiner.md
      arbitration.md
      losses.md
      checkpoint-selection.md
      training-evidence.md
      cine-temporal.md
    figures/
      architecture.d2
      architecture.svg
      architecture.png
      gap.d2
      gap.svg
      gap.png
      delta-from-M08.d2
      delta-from-M08.svg
      delta-from-M08.png
```

这里允许一个 `history/`、每版本一个目录、每版本一个 `components/` 和 `figures/`，不要继续扩张为 papers/entities/gaps/decisions 等繁杂树。

### 4.1 迁移 M8

把 `TODO.md` 的所有实质分析按 component 拆分，保留：

- 事实判断；
- 数学公式；
- 代码路径、symbol 和配置；
- 实现状态；
- 当时的证据边界；
- 下一步建议。

不得为了简洁丢失关键批评，例如 loss wiring、anchor-centered arbitration、prototype buffer、checkpoint selection、Cine proxy 等。

### 4.2 迁移 M9

把 `todo-m10.md` 按相同 component 结构拆分。该文件部分内容写于 M9 follow-up re-audit 之前，必须保留“当时判断”，不能用后来的结论覆盖历史。

在 M09 `README.md` 和 `snapshot.yaml` 中分开写：

```text
analysis_as_written
later_status_update
```

`later_status_update` 必须引用最终 token：

```text
M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY
```

说明 evidence/validator blocker 后来被修复，但 M9 科学方向仍为 no-promotion diagnostic-only。

### 4.3 版本快照与不可变性

每个 `snapshot.yaml` 至少包含：

```yaml
milestone:
analysis_source:
source_blob_sha:
analysis_as_of_commit:
review_token_at_time:
latest_known_review_token:
architecture_version:
code_fingerprint:
component_files:
figure_files:
created_at_utc:
```

历史版本文件在创建后默认不可被后续 mapper 重写。后续纠错只能追加 `ERRATA.md` 或 `later_status_update`，不能静默改写原判断。

### 4.4 迁移完整性

创建 `MIGRATION_MANIFEST.csv`：

```text
source_file,source_heading,destination_file,destination_anchor,migration_status,content_note
```

所有 `TODO.md` 和 `todo-m10.md` 的实质 heading 必须映射到 destination。只有 validator 证明 coverage 完整、历史图生成成功、所有新文件已 tracked 后，才删除 root `TODO.md` 和 `todo-m10.md`。

## 5. 所有版本示意图与分析必须对齐

扩展 architecture generator，使其支持：

```bash
python scripts/architecture/generate_care_architecture_wiki.py --current
python scripts/architecture/generate_care_architecture_wiki.py --history M08
python scripts/architecture/generate_care_architecture_wiki.py --history M09
python scripts/architecture/generate_care_architecture_wiki.py --check-all
```

历史图必须从该版本自己的 `architecture.yaml + COMPONENTS.csv` 生成，不得从 current 文件复制。

每个版本至少两张图：

1. `architecture`：该版本真实实现的数据流；
2. `gap`：每个 component 的 current/target/evidence 状态。

从第二个版本开始增加 `delta-from-previous`，只显示新增、移除、状态变化和主数据流变化。

图与分析对齐要求：

- 每个图节点必须有 `component_id`；
- 每个 component Markdown 必须链接对应图节点或 figure；
- `snapshot.yaml` 保存 source hash；
- validator 检查 D2/SVG/PNG 是否来自当前 snapshot source；
- `wiki/history/COMPARISON.md` 提供 M8 vs M9 的简明对比表和 delta 图；
- current `wiki/README.md` 只展示当前 3 张图，并提供“历史版本”入口，避免第一屏繁杂。

## 6. Wiki 以中文为主，并强制调用写作 skill

当前 `wiki/README.md`、`MODEL.md`、`EXECUTION.md` 和 D2 labels 主要是英文，不符合用户阅读需求。

### 6.1 写作 skill 发现与调用

在改写 wiki 前，必须发现当前 Codex session 可用的 global writing skills。优先寻找并调用：

```text
chinese-prose
scientific-prose
research-documents 或等价科研文档 skill
```

使用当前 runtime 提供的 skill discovery；若通过文件系统，检查 `$HOME/.agents/skills/`、`${CODEX_HOME}/skills/` 和当前已加载插件/skill 目录。不要假装发现。

写入：

```text
wiki/writing_skill_receipt.json
```

至少记录：

```text
skill_name
scope: global
source_path_or_runtime_identifier
sha256_or_version
files_written
invoked_at_utc
```

如果 global writing skill 确实不可用，停止为：

```text
NEEDS_EVIDENCE_GLOBAL_WRITING_SKILL_UNAVAILABLE
```

不要静默只用普通 LLM 改写。Repo-local skill 可以用于校验，但不能冒充 global skill receipt。

### 6.2 中文规则

以下文件正文和图节点标签以中文为主：

```text
wiki/README.md
wiki/MODEL.md
wiki/EXECUTION.md
wiki/LINEAGE.md
wiki/history/**/*.md
wiki/figures/*.d2
wiki/history/**/figures/*.d2
```

只保留必要英文：

- 文件路径、class/function、配置键；
- 模型/算法/指标名，如 `SRR`, `nnU-Net`, `Dice`, `HD95`；
- 状态 token、review token；
- 必须与代码或 validator 精确匹配的字段。

不要把普通概念堆成英文。表头、图标题、图注、入口说明、component 解读必须使用自然中文。

`COMPONENTS.csv` 的机器字段名可保留英文，但 `role`、`notes`、面向用户的解释列应为中文。

## 7. 更新 current wiki

Current wiki 继续保持简洁：

```text
wiki/README.md
wiki/MODEL.md
wiki/EXECUTION.md
wiki/COMPONENTS.csv
wiki/LINEAGE.md
wiki/architecture.yaml
wiki/figures/
```

`wiki/README.md` 第一屏：

- 当前架构版本；
- 当前 review token；
- 当前模型图、差距图、执行流程图；
- 不超过 12 行 component summary；
- 链接到 `wiki/history/README.md`。

不要把所有历史 component 内容塞进 current README。

## 8. Validators 与 tests

### 8.1 Handoff validator

新增检查：

- `executor_slots`、`executor_count` 必须为正整数；
- `executor_slots > 1` 必须有 valid executor plan；
- 并行 wave 的 write/result/runtime/log/lock/worktree 冲突；
- finalizer stale lock；
- `AWAITING_SACCT` retry contract；
- 声明 tmux watcher 但没有真实 receipt；
- finalizer 在 mapper final/validator 前 commit；
- 双 commit owner；
- wiki 中文 hard gate 和 writing skill receipt；
- root `TODO.md` / `todo-m10.md` 在迁移完成后仍存在；
- history snapshot/figures/component links 不一致。

### 8.2 Architecture/history validator

扩展 `validate_care_architecture_wiki.py --strict --history`：

- current 与每个 history version required files 存在；
- source files/symbol/evidence path 可验证；
- snapshot hash、D2 source、SVG/PNG 一致；
- 每个 component file 被 version README/manifest 引用；
- 每个 graph node 有 component_id；
- M09 delta 图只引用 M08/M09；
- history 文件 tracked，不能位于 `results/` 或被 `.gitignore` 排除；
- `MIGRATION_MANIFEST.csv` 覆盖两个源 TODO 的全部实质 headings；
- 中文正文比例合理，普通英文密度过高时 fail closed；受保护 token/path/code 不计入该比例。

### 8.3 Finalizer tests

至少覆盖：

```text
PENDING -> NEEDS_MONITOR
RUNNING -> NEEDS_MONITOR
AWAITING_SACCT then COMPLETED -> continue finalization
AWAITING_SACCT retry exhausted -> honest accounting wait state
COMPLETED + outputs -> aggregation
COMPLETED + missing outputs -> NEEDS_EVIDENCE
FAILED -> RUNTIME_FAILURE, not scheduler block
active lock -> refuse
stale lock -> recover only under policy
lock released -> retry succeeds
FINALIZER_A cannot commit
FINALIZER_B cannot run before mapper final and validators
single commit owner
```

### 8.4 Parallel executor tests

至少覆盖：

```text
one executor default
2 executors in same wave with separate worktrees/write scopes -> valid
2 executors with overlapping source file -> fail
MyoPS/Cine parallel without explicit isolation proof -> fail
executor_count > executor_slots across sequential waves -> valid
same-wave active executors > slots -> fail
merge conflict -> NEEDS_REVISION_PARALLEL_MERGE_CONFLICT
unmerged executor branch before finalization -> fail
```

## 9. 必须更新的 active 文件

至少检查并按需修改：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_ROLES.md
prompts/HANDOFF_STATE_MACHINE.md
prompts/CONTROLLER_TASK_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/templates/CONTROLLER_TASK_TEMPLATE.md
.agents/skills/care-mapper/SKILL.md
scripts/ops/care_milestone_finalizer.py
scripts/ops/submit_care_dependency_finalizer.py
jobs/src/care_milestone_finalizer.sh
scripts/validation/validate_handoff_policy.py
scripts/architecture/generate_care_architecture_wiki.py
scripts/architecture/validate_care_architecture_wiki.py
src/care_myocardium/tests/test_handoff_policy_validator.py
wiki/**
README.md
```

如实现并行 launcher，可新增：

```text
scripts/ops/validate_executor_plan.py
scripts/ops/launch_care_executor_wave.py
scripts/ops/merge_care_executor_wave.py
scripts/ops/start_care_tmux_watcher.py
prompts/templates/EXECUTOR_PLAN_TEMPLATE.yaml
```

## 10. 验证命令

必须运行并记录：

```bash
python scripts/validation/validate_handoff_policy.py --strict-tasks --warnings-as-errors
python scripts/architecture/validate_care_architecture_wiki.py --strict --history
python scripts/architecture/generate_care_architecture_wiki.py --check-all
python -m unittest src.care_myocardium.tests.test_handoff_policy_validator
python -m py_compile \
  scripts/ops/care_milestone_finalizer.py \
  scripts/ops/submit_care_dependency_finalizer.py \
  scripts/validation/validate_handoff_policy.py \
  scripts/architecture/generate_care_architecture_wiki.py \
  scripts/architecture/validate_care_architecture_wiki.py
bash -n jobs/src/care_milestone_finalizer.sh
git diff --check
```

如果新增 watcher/parallel scripts，也必须 `py_compile` 并运行 synthetic tests。

## 11. Git 与完成边界

- 只提交 handoff、controller/finalizer、validators、tests、wiki、历史分析和轻量图；
- 不修改模型训练代码；
- 不训练、不提交普通 Slurm job；
- 不修改历史 `results/` packet；
- 不提交 checkpoints、NIfTI、predictions、logs、raw data、upload package 或 secrets；
- 本地 commit，不 push；
- controller 不写 `review.md`；
- separate reviewer 后续只读审阅本任务 packet。

## 12. 最终输出

最终回复只报告：

```text
finalizer 修复项
并行 executor 实现与安全规则
M8/M9 历史迁移位置
生成的版本图
中文 wiki 与 global writing skill receipt
validator/test 结果
commit SHA
确认未 push
```
