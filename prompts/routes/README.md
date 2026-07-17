# CARE 三路线 GPT 提示词入口

本目录保存 2026-07-15 至 2026-07-27 的 CARE Myocardium 三路线提示词。以后从 GPT Project 或 Notion 复制提示词时，优先看这里，不再从旧 `M10 followup2` 单一里程碑模板开始。

## 复制顺序

1. GPT 项目设置参考：

```text
prompts/routes/gpt_project_instructions_route_portfolio.md
```

如果 ChatGPT Project UI 中的实际项目提示词和该文件不同，以 UI 当前设置为准；但后续 round 的 planner/critic handoff 入口必须固定到第 5 项的 `CURRENT.md`。

2. 让 GPT 规划 Route A、Route B、Route C 时使用：

```text
prompts/routes/route_portfolio_planner_prompt.md
```

3. 所有三路线角色都必须先读反偷懒协议：

```text
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
```

4. 从 Notion 或 GPT 项目里复制角色提示词时使用：

```text
prompts/routes/notion_route_prompt_copy_blocks.md
```

5. controller/reviewer 执行后，给总 GPT Planner 或单路线 Critic 的当前轮次入口固定为：

```text
prompts/routes/handoffs/CURRENT.md
```

`CURRENT.md` 会指向当前 round 的总 planner prompt，以及 Route A/B/C 各自的 critic prompt。命名和轮次规则见：

```text
prompts/routes/handoffs/README.md
```

6. GPT Planner 输出不要默认写 `prompts/shared/`。三条路线的规划文件默认写入：

```text
prompts/routes/route_A.md
prompts/routes/route_A_executor_plan.yaml
prompts/routes/route_A_critic_request.md
prompts/routes/route_A_planner_audit.md

prompts/routes/route_B.md
prompts/routes/route_B_executor_plan.yaml
prompts/routes/route_B_critic_request.md
prompts/routes/route_B_planner_audit.md

prompts/routes/route_C.md
prompts/routes/route_C_executor_plan.yaml
prompts/routes/route_C_critic_request.md
prompts/routes/route_C_planner_audit.md
```

`prompts/shared/` 只用于真正需要合入共享 executor/reviewer prompt 或 canonical milestone staging 的内容。

## Notion 第一行替换

Notion `CARE Challenge > Prompts` 页面里的旧代码块可以继续保留作为角色模板，但第一行需要从单一 `M10 followup 2` 改成三路线入口。

Planner、Critic、Planning integrator 代码块第一行：

```text
本轮任务：CARE Myocardium 三路线并行 route portfolio（route_A / route_B / route_C，2026-07-15 至 2026-07-27）；本页正文只作角色模板，本轮以仓库 prompts/routes/README.md 与 prompts/routes/route_portfolio_planner_prompt.md 为准。
```

Controller 代码块第一行：

```text
本轮执行对象：某一条已通过 Critic 的 route（route_A 或 route_B 或 route_C）；从 prompts/routes/route_X.md 和 prompts/routes/route_X_executor_plan.yaml 启动，不使用旧 M10 followup2 单里程碑合同。
```

Reviewer 代码块第一行：

```text
本轮审阅对象：某一条 route 的 controller packet（route_A 或 route_B 或 route_C）；只读审阅该 route 的结果目录，不跨 route 代替最终路线选择。
```

## 当前流程

1. 初始三路线规划时，GPT Planner 先读仓库、Project 背景 SRR 图、`prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`、`prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md` 和 `prompts/routes/route_portfolio_planner_prompt.md`。
2. 执行后回传或下一步决策时，GPT Planner 和 Critic 都先读 `prompts/routes/handoffs/CURRENT.md`，不要猜最新文件名。
3. GPT Planner 是一个 thread，统一负责 Route A、Route B、Route C 的 portfolio round。
4. Critic 是三个独立 thread；每个 Critic 只读取 `CURRENT.md` 中自己 route 的当前 critic prompt。如果该 route 是 `NO_CURRENT_CRITIC_HANDOFF`，Critic 停止。
5. GPT Planner 分别向 `route_A`、`route_B`、`route_C` 推送规划合同、executor plan、critic request 和 planner audit。
6. 每条 route 各有一个独立 Critic。Critic 通过后，该 route 的 Controller 才能启动。
7. Controller 在对应 route worktree 中执行；不能跨 route 写文件。
8. Reviewer 只在对应 route controller packet 提交后启动，且只读审阅；审阅前必须检查 `ROUTE_ANTI_LAZINESS_PROTOCOL.md` 中的 Slurm、短 smoke、validator、receipt 自洽规则，以及 `ROUTE_HARD_REQUIREMENTS_MATRIX.md` 中对应 route 的持续强要求。
9. 最终选择和合并由后续 portfolio reconciliation 完成，不由任一单独 route controller 决定。
