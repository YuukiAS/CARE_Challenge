# Start Here For GPT

本文件是所有 CARE GPT/ChatGPT 规划、路线判断、Batch 复盘和 Codex goal 的根入口。

## 必读顺序

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
13. 当前任务、结果、代码和必要 skill。

不得用旧聊天记忆、watchboard、旧 route 状态或自然语言总结替代当前远端 `main` 和 `CURRENT.md`。

## 最终输出说人话

面向用户、Planner 或科研负责人的最终分析必须先给自然中文判断，再给内部标签、路径、指标和命令。不得把仓库内部实验名、状态 token、机制标签或英文短语堆叠当作标题或结论；内部代号只能放在解释后的括号中用于定位。发送前按 `prompts/FINAL_OUTPUT_READABILITY_POLICY.md` 做可读性验收。

## 当前 main-only posture

默认仓库：

```text
/users/a/e/aereinh/CARE
main
```

禁止默认写入：

```text
/overflow/htzhu/CARE
/users/a/e/aereinh/CARE_worktrees/route_A
/users/a/e/aereinh/CARE_worktrees/route_B
/users/a/e/aereinh/CARE_worktrees/route_C
```

Route A/B/C 是历史 evidence lanes。只有用户显式重新授权某条 route 时，才恢复 route worktree/controller。

## 默认 Sprint Flow

当前默认流程：

```text
Planner
-> Controller/Coordinator
   -> Executor
   -> optional Mapper
   -> deterministic Finalizer/Validator
   -> Controller verification and repair loop
   -> local lightweight result commit
-> Planner
```

短、非 Slurm、低恢复风险任务可以：

```text
Planner -> Executor -> local result commit -> Planner
```

Controller 是 coordinator 和 acceptance owner。Executor 负责代码和命令，但不能宣布整个任务完成。

默认：

```yaml
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
```

高风险、system-impact、Slurm、scientific milestone、route change 或 scientific decision scope 只提高证据、validator 和 controller 验收要求，不自动触发 critic/reviewer。

只有用户或 Planner 在具体任务中显式设置 `planning_review_required: true` 或 `review_required: true`，才启用旧的独立 planning critic 或 read-only reviewer。

## 新任务必须声明

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

长 Slurm/overnight/multi-job/high-resume-risk 必须用 `controller_supervised` 和 durable finalizer。任何 `executor_count > 1` 必须有隔离写入范围和有效 executor plan。

## Prompt 结构

短任务默认：

```text
## Execution Contract
## Executor Prompt
```

长 controller 任务默认：

```text
## Execution Contract
## Controller Prompt
## Executor Worker Contract
## Mapper Contract
```

只有 `review_required: true` 时才添加：

```text
## Reviewer Prompt
```

Reviewer prompt 不得作为所有 milestone 的默认必需段。

## Controller 完成语义

Controller 必须检查：

- 当前 SHA 和任务 hash；
- Executor 的真实 diff；
- frozen model/config/split/case/budget/decode/metric 字段；
- tests、known-bad、strict validators；
- Slurm terminal accounting；
- post-completion aggregation；
- exact required outputs；
- CURRENT/wiki/fingerprint 一致性；
- lightweight local commit 边界。

Controller report 必须包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
```

`VERIFIED_COMPLETE` 只代表当前 Batch 执行合同完成。下一 Batch、训练扩展、route promotion、validation upload、hosted claim 和 final scientific decision仍由 Planner/用户决定。

## SRR/MyoPS/Cine 图视觉门

任何 SRR/MyoPS/Cine 规划前必须按 `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md` 视觉读取 ChatGPT Project 材料中的：

```text
SRR-v2
SRR-v2.5
SRR-v3
以及更晚版本
```

仓库文件名和 GitHub blob metadata 不能替代视觉阅读。

规划必须恢复以下路线目标：

```text
[LGE,T2,C0] + availability
-> modality-specific multi-scale encoding
-> shared/private/interaction selective retrieval
-> prototype/memory/negative-space
-> anatomy-guided scar/edema proposals
-> pathology-specific soft ROI refinement
-> bounded nnU-Net correction
```

无法读图时停止为：

```text
BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE
```

## Slurm 门

涉及 Slurm 时必须读取 `.agents/skills/slurm-routing-partition/SKILL.md`。正式 wrapper 禁止裸 `python`。Submitted、pending、running、monitor、awaiting sacct 均不是完成。Controller 必须持续负责到所有 job terminal、aggregation 和 validator 完成。

## Mapper 门

涉及 architecture、loss、dataflow、export、Cine temporal、registration 或 controller observability 时必须读取 `.agents/skills/care-mapper/SKILL.md`，并更新 root wiki/fingerprint 或明确记录 stale evidence。

## 历史 reviewer 协议

`prompts/MILESTONE_REVIEW_PROTOCOL.md` 只适用于显式 `review_required: true` 的历史或特殊任务。默认 Batch 不得因为缺少 `review.md` 被阻塞。