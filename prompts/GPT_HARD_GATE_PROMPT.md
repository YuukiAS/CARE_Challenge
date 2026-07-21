# GPT Hard-Gate Prompt For CARE Handoff

本文件是 CARE 新任务在进入 Codex 前的 hard-gate 入口。它用于防止缺失子任务、短 smoke、submitted-only、错误评价语义、过期机器状态或自然语言自证被包装成完成。

## 一、核心原则

每条反偷懒要求必须落实为至少一种机器可检查证据：

1. 精确文件路径；
2. frontmatter/schema 字段；
3. 非零失败的 validator；
4. controller report/completion check 字段；
5. known-bad regression test；
6. metric、hash、provenance 或 terminal job receipt。

无法机器检查的内容只能作为建议，不能作为完成门。

最终面向用户、Planner 或科研负责人的分析还必须通过 `prompts/FINAL_OUTPUT_READABILITY_POLICY.md`：先写自然中文判断和因果解释，再写内部标签、路径、指标、命令和机器字段。不得把仓库内部实验名、状态 token 或机制标签直接当标题或结论。

## 二、SRR 图视觉启动门

任何 SRR/MyoPS/Cine 规划、目标修订或路线判断前，GPT 必须按 `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md` 视觉阅读 ChatGPT Project 材料中的 SRR-v2、SRR-v2.5、SRR-v3 及更晚版本。

规划必须写明：

```text
diagram_versions_read:
visual_read_status:
recovered_route_objective:
```

路线目标必须保留：availability-aware selective retrieval、semantic representation bank、anatomy-guided pathology proposal、scar/edema pathology-specific soft-ROI refinement、prototype/memory/negative-space、安全监督和 bounded nnU-Net correction。nnU-Net 只能作为 anchor/context/evidence/safety source，不能替代 SRR。

无法视觉读图时停止为：

```text
BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE
```

## 三、默认 Sprint Agent Flow

当前默认流程是：

```text
Planner
-> Controller/Coordinator
   -> Executor
   -> optional Mapper
   -> deterministic Finalizer/Validator
   -> Controller verification and same-scope repair loop
   -> local lightweight commit
-> Planner
```

Controller 是 coordinator 和 acceptance owner。Executor 不能自行宣布整个任务完成。

默认不启用 planning critic：

```yaml
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
```

默认不启用 independent reviewer：

```yaml
review_required: false
review_mode: none
reviewer: none
```

只有用户或 Planner 在具体 task 中显式设置 `planning_review_required: true` 或 `review_required: true` 时，旧 critic/reviewer 流程才启用。高风险、system-impact、Slurm、scientific milestone、route change 或 scientific decision scope 本身不得自动触发 critic/reviewer。

历史 task 已显式启用 critic/reviewer 时，其已有 receipt 继续有效；不得回写历史合同来伪造新默认。

## 四、每个新任务的执行合同

至少声明：

```yaml
task_key:
task_kind:
task_type:
status:
risk_level:
route_change:
scientific_decision_scope:
execution_mode: direct_executor | controller_supervised
requires_execution_controller: true | false
controller_is_coordinator: true | false
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path:
mapper_slots: 1
mapper_required: true | false
architecture_impact: none | component | system
wiki_update_required: true | false
diagram_update_required: true | false
slurm_runtime_continuity_required: true | false
continuity_backend: none | slurm_dependency | tmux_watcher
planning_review_required: false | true
review_required: false | true
allow_git_commit: true | false
auto_git_commit: true | false
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
```

任何 `executor_count > 1`、`executor_slots > 1` 或并行执行必须提供有效 executor plan、隔离写入范围、独立 runtime/log/lock、依赖和确定性 merge order。

## 五、Controller 验收门

Controller 必须：

1. 冻结 Planner 合同和当前 SHA；
2. 检查 Executor 的真实 git diff 和 changed files；
3. 核对模型、配置、split、病例数、训练预算、decode、metric 和 hash 未被缩水或漂移；
4. 运行声明的 tests、known-bad 和 strict validators；
5. 监督所有 Slurm attempt 到 terminal accounting；
6. 在 runtime 完成后重新 aggregation；
7. 检查 required outputs 的内容而不只是文件存在；
8. 对同范围 bug 将工作退回 Executor 修复；
9. 只在所有完成条件满足时本地提交轻量结果；
10. 返回 Planner，不自动授权下一 Batch。

Controller report 必须包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
contract_compliance_status:
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
git_commit_decision:
git_push_decision:
blocked_actions:
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

`VERIFIED_COMPLETE` 只代表当前执行合同在操作和证据上完成，不自动代表模型成功、路线晋级、validation upload、hosted claim、fold expansion、下一 Batch 或 final scientific decision。

## 六、精确任务图与结果路径

每个 controller task 必须给出有序任务图，并为每个 blocking wave 指定：

```text
wave/task id
dependencies
write scope
results/<task_key>/ exact outputs
completion conditions
failure/repair branch
```

blocking 输出缺失时必须写 `INCOMPLETE`/`NEEDS_REPAIR`，不得用相似旧文件、自然语言总结、历史 receipt 或 later-stage report 替代。

## 七、训练和评价硬门

涉及训练时必须声明 minimum effective training：

```text
min_optimizer_steps
min_train_loop_seconds
min_eval_cases
validation events
one-batch overfit
finite loss/loss decrease
prediction sanity
same-split baseline
cache isolation
checkpoint save/reload
```

短 smoke、one-batch、preflight、failed startup、race loser、partial checkpoint 和 undertrained run 均为 zero formal credit，除非合同明确只要求诊断。

评价必须固定：

```text
case set
checkpoint hash
decode rule
metric implementation
positive-GT/all-case population semantics
same-split baseline
help/harm
HD95
remote FP
component count
```

Checkpoint selection 与最终部署 runtime/decode 不一致时，必须 fail closed。

## 八、Slurm 与 monitor 门

正式 Slurm wrapper 必须使用通过 preflight 的精确 Python，禁止裸 `python`。

```text
SUBMITTED
PENDING
RUNNING
CONFIGURING
COMPLETING
NEEDS_MONITOR
AWAITING_SACCT
```

均不是完成。

完成证据必须记录：job ID、partition、state、exit code、elapsed、node、log、runtime output、aggregation command/exit、updated tracked outputs。

同范围 operational retry 不需要新 Planner 决定，但必须保持科学 variant、budget、split、config semantics、task graph 和 write scope；失败 attempt 永久保留并计 zero credit。

训练依赖使用 `afterok`；terminal accounting/finalizer 使用 `afterany`。

## 九、Mapper 与 Wiki

架构、loss、dataflow、export、Cine temporal、registration 或 controller observability 变化必须使用 `.agents/skills/care-mapper/SKILL.md`。

Mapper/finalizer 必须检查 root wiki、COMPONENTS、architecture/fingerprint 和 CURRENT 是否与最终代码/证据一致。过期 wiki 不得被 validator 忽略，也不得用旧 review token 前移 current state。

## 十、Critic/Reviewer 显式 opt-in

当且仅当 task 明确：

```yaml
planning_review_required: true
```

才要求独立 GPT planning review 和匹配 hash/token。

当且仅当 task 明确：

```yaml
review_required: true
```

才要求 independent read-only reviewer 和 `review.md`。

没有显式 reviewer 的默认任务以 Controller 的 `VERIFIED_COMPLETE` 作为执行终态，并返回 Planner。Controller 仍不得自授 route promotion、scientific stop、validation upload、hosted claim、fold expansion 或下一 Batch。

## 十一、Known-Bad Regression

至少覆盖：

- required task directory/file 缺失却写 ready；
- short smoke 冒充正式训练；
- submitted/pending packet 冒充完成；
- old wrapper/synthetic data/hard-coded metric 成为正式入口；
- no-T2 edema 误监督；
- checkpoint 没有 reload；
- selected checkpoint/decode 与最终 inference 不一致；
- all-case empty-GT 指标冒充 positive-case pathology 进展；
- controller 只相信 token 而不检查 evidence；
- stale CURRENT/wiki 与 terminal packet 冲突；
- code/config/split/checkpoint/prototype hash 缺失或错配。

历史 `20260704_srr_v25_full_completion_goal` 必须继续作为 missing-subtask known-bad 失败样例。

## 十二、Future Goal Required Wording

高风险 controller goal 应包含：

`Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, controller-as-coordinator diff inspection and repair loop, strict validators and known-bad regressions, minimum effective training when training is required, terminal Slurm accounting and post-completion aggregation, mapper/wiki/fingerprint gates when architecture is affected, and SRR diagram-bootstrap evidence for SRR/MyoPS/Cine work. If any hard gate fails, continue same-scope repair when authorized or stop with NEEDS_REPAIR/NEEDS_EVIDENCE; do not claim VERIFIED_COMPLETE.`

Executor wording：

`The Executor performs authorized implementation and commands but cannot declare the whole task complete. Return every wave to the Controller/Coordinator for diff, evidence, validator, runtime and contract verification.`

默认任务不得再附加“必须等待独立 critic/reviewer”措辞；只有显式 opt-in task 才添加对应提示。