# CARE 执行流程

## 角色

- `planner`：GPT/ChatGPT 规划者，写路线、任务、milestone、controller、executor、mapper 和 reviewer contract。
- `controller`：长任务的顶层 Codex goal，负责 phase grounding、subagent 协调、Slurm continuity、FINALIZER_A/B、validator 和本地 packet commit。
- `executor`：执行者，做授权实现、命令和初始证据；不自审，不拥有 overnight continuity。
- `mapper`：只读架构/证据映射者；只有任务授权时才更新 `wiki/`。
- `finalizer`：确定性脚本阶段，不是 reviewer。`FINALIZER_A` 做 accounting/aggregation；`FINALIZER_B` 做 validators、wiki/history checks、`git diff --check` 和唯一 local commit。
- `validator`：一方 fail-closed 脚本。
- `reviewer`：独立只读审阅者，只在 packet commit 后写 `review.md`。

## 默认路径

短任务：

```text
planner -> executor -> local commit -> separate reviewer
```

长 Slurm / overnight / multi-job / high-resume-risk 任务：

```text
planner -> controller
                 |-> executor wave(s)
                 |-> mapper draft
                 |-> durable finalizer / watcher
                 |-> mapper final
                 |-> validators
                 |-> local packet commit
            controller stops
            -> separate reviewer
```

## 并行 executor

默认只有 1 个 executor。若 `executor_count > 1`、`executor_slots > 1` 或 `parallel_execution_allowed: true`，必须提供 `executor_plan_path`，并通过 `scripts/ops/validate_executor_plan.py`。同一 wave 只能运行 write scope 不重叠、worktree/branch/result/runtime/log/lock 都隔离的 executor。MyoPS 与 Cine 默认顺序执行，除非 GPT 明确给出隔离证明。

## Slurm 状态

`PENDING`、`RUNNING`、`CONFIGURING`、`COMPLETING`、`AWAITING_SACCT` 是 monitor state，不是 completion，也不是 scheduler block。`AWAITING_SACCT` 由 finalizer bounded retry；超时写 `AWAITING_SACCT_RETRY_EXHAUSTED`。scheduler block 需要 Slurm skill 的 12 次、每 2 小时、总 24 小时 all-pending evidence。
