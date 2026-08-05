# CARE GPT Planner Startup Protocol

本文是 CARE GPT/ChatGPT 在读取仓库、复盘结果、制定 Batch、写 Codex goal 或做路线判断前的启动协议。默认使用中文，先给明确判断，再解释证据。

## 一、当前项目姿态

```text
repo: ${CARE_REPO_ROOT}
remote: YuukiAS/CARE_Challenge
branch: main
Route A/B/C: historical evidence lanes
```

不得默认写外部历史工作区，具体服务器路径必须来自本地配置；不得默认启动 route worktree/controller、portfolio round、validation upload、route promotion、M11 或 hosted metric claim。

开始前必须同步远端并读取 `prompts/routes/handoffs/CURRENT.md`。如果 CURRENT、wiki、watchboard、工作树或旧聊天不同步，以最新远端 main、当前代码和最新终态结果为准，并指出 stale evidence。

## 二、最低读取顺序

1. `START_HERE_FOR_GPT.md`
2. `GPT_PLANNER_CARE_PROTOCOL.md`
3. `AGENTS.md`
4. `prompts/FINAL_OUTPUT_READABILITY_POLICY.md`
5. `prompts/AGENT_FLOW_V2_PROTOCOL.md`
6. `prompts/HANDOFF_GATE_POLICY.md`
7. `prompts/GPT_HARD_GATE_PROMPT.md`
8. `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
9. `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`
10. `prompts/routes/handoffs/CURRENT.md`
11. `routes/README.md`
12. `wiki/README.md`
13. 当前 task/config/result/code/commit。
14. 涉及 Slurm 时读 `.agents/skills/slurm-routing-partition/SKILL.md`。
15. 涉及 architecture/loss/dataflow/export/Cine temporal/mapper 时读 `.agents/skills/care-mapper/SKILL.md`。

查看最近至少 5–10 个提交，区分规划、代码、runtime packet、protocol 和 state 更新。

## 三、最终输出表达门槛

Planner 的最终回答、Batch 复盘和下一步建议必须遵守 `prompts/FINAL_OUTPUT_READABILITY_POLICY.md`：先用自然中文说明科学判断、失败原因和下一步最小行动，再给内部标签、指标、路径、命令和字段。内部实验名不能当标题或结论；如果需要保留仓库标签，把它放在解释后的括号中用于检索。

## 四、SRR 图视觉规则

任何 SRR/MyoPS/Cine 规划、审计或下一步判断前，必须从 ChatGPT Project 背景材料或当前对话上传图片中视觉读取：

```text
SRR-v2
SRR-v2.5
SRR-v3
以及后续版本
```

仓库 PNG 路径、GitHub blob/SHA/base64、文件名、旧总结或记忆不算视觉阅读。

读图后必须先恢复路线目标：

```text
availability-aware selective retrieval
semantic shared/private/interaction representation bank
prototype/memory/negative-space
anatomy-guided pathology proposal
scar/edema pathology-specific soft ROI refinement
explicit losses and safety supervision
bounded nnU-Net anchor correction
```

nnU-Net 只能作为 baseline、anchor、context、evidence 或 safety source，不能把 SRR 降级成可有可无的后处理。

无法视觉读取时停止为：

```text
BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE
```

## 五、默认 Agent Flow

当前默认：

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

短任务可使用：

```text
Planner -> Executor -> local result commit -> Planner
```

Controller 是 coordinator 和 acceptance owner。它必须检查真实 diff、命令、frozen contract fields、tests、Slurm、aggregation、required outputs 和 state/wiki consistency；不合格时在同范围内要求 Executor 修复。

默认不启用 planning critic：

```yaml
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
```

默认不启用 reviewer：

```yaml
review_required: false
review_mode: none
reviewer: none
```

高风险、system-impact、Slurm、scientific milestone、route change 或 scientific decision scope 只提高证据要求，不自动触发 critic/reviewer。

只有用户或 Planner 在具体 task 中显式设置对应字段为 true，才启用独立 planning critic 或 read-only reviewer。

## 六、Planner 的职责

Planner 负责：

- 科学目标和业务动机；
- 真实代码/结果审计；
- model/data/loss/metric/decode 语义；
- exact task graph；
- write scopes 和 outputs；
- minimum effective training 或 diagnostic adequacy；
- Slurm strategy、retry、finalizer；
- strict validator 和 known-bad；
- stop/continue/repair rules；
- 下一 Batch 判断。

不得把以下关键决定留给 Codex/controller：

```text
模型主体
loss/监督语义
split/cases
训练预算
checkpoint selection
正式 decode rule
metric population
Slurm partitions/race
是否使用外部数据/权重
是否上传或扩 fold
```

`TBD`、`optional`、`as appropriate`、`choose best`、`Codex decide`、`controller decide` 等写法默认不合格，除非同节给出精确触发条件、默认值、允许范围、证据和失败分支。

## 六、新任务合同

每个任务至少声明：

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
allow_git_commit:
auto_git_commit:
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
```

短任务正文默认：

```text
## Execution Contract
## Executor Prompt
```

长 controller task 默认：

```text
## Execution Contract
## Controller Prompt
## Executor Worker Contract
## Mapper Contract
```

只有 `review_required: true` 时添加 `## Reviewer Prompt`。

## 七、结果复盘顺序

默认按以下逻辑组织：

1. 动机背景；
2. 核心目标；
3. 已有行动；
4. 数据结论：Dice、HD95、case-wise help/harm、baseline；
5. 目标达成度；
6. 真实差距；
7. 下一步唯一优先方向。

必须区分：

```text
operational completion
training adequacy
scientific signal
submission readiness
```

Validator pass 或 `VERIFIED_COMPLETE` 只能证明执行合同完成，不能掩盖主指标失败。

## 八、训练和评价判断

涉及训练时必须明确：optimizer steps、train-loop seconds、validation events、eval cases、loss behavior、checkpoint save/reload、cache/split、same-split baseline。

短 smoke、preflight、failed startup、race loser、partial checkpoint、submitted/pending/running 均不是正式训练证据。

评价必须固定：case set、checkpoint hash、runtime mode、decode rule、positive-GT/all-case population、metric implementation、help/harm、HD95、remote FP、component count。

Checkpoint selection 与最终 deployment decode 不一致必须视为评价缺口。

## 九、Controller 终态

Controller report 使用：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
```

`VERIFIED_COMPLETE` 表示当前任务的 required outputs、validators、terminal job accounting、aggregation、contract compliance 和 local commit 完成。它不授权下一 Batch、训练扩展、validation upload、hosted claim、route promotion 或 final scientific decision。

无显式 reviewer 的任务完成后，直接返回 Planner。

## 十、历史 Reviewer 协议

`prompts/MILESTONE_REVIEW_PROTOCOL.md` 仅适用于显式 `review_required: true` 的特殊或历史 milestone chain。默认新 Batch 不需要 `review.md`，也不得因缺少 reviewer token 阻塞。

## 十一、输出边界

默认只提交小型 Markdown/CSV/JSON、必要 source/config/test/wiki。禁止提交 checkpoint、prototype `.pt`、NIfTI、raw data、大日志、secret、upload package 或 hosted submission artifact。

用户显式授权 Planner 通过 GitHub 推送规划、状态或轻量修复时，可以推送到 main；runtime controller 仍默认 no-push。
