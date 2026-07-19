# CARE Route Portfolio Watchboard

`scripts/ops/build_route_watchboard.py` 生成 CARE Route A/B/C 的只读 portfolio watchboard。它从 `prompts/routes/handoffs/CURRENT.md` 动态读取当前 `round_id`、active/deferred routes、controller authority boundary、route head/blob bindings、critic handoff/review paths、allowed planning tokens 和 checkpoints，再交叉展示 route-local packet、tmux、Slurm 和 live service 状态。

看板只观察，不执行。页面不得有操作按钮；脚本不得提交/取消 Slurm、启动 controller、上传 validation、合并、推送、route promotion、M11、hosted metric claim 或 final scientific decision。

## Source Of Truth

`prompts/routes/handoffs/CURRENT.md` 是 portfolio truth。`results/watchboard/status.json` 和 `results/watchboard/index.html` 是 ignored/generated live output，只用于验证服务当前展示，不作为源码真相提交。

当 Controller 已写出 terminal packet 并准备交 independent reviewer 时，`CURRENT.md` 可包含 `Controller Terminal Packet / Reviewer Targets` section。看板用该 section 识别当前 phase transition：旧 planner/critic binding 仍作为历史规划绑定展示，旧 `review.md` 或旧 `NEEDS_MONITOR` keyword 不得覆盖新的 terminal reviewer target。Reviewer source-of-truth 仍是 route worktree terminal packet、target commit、review request、validator 和 Slurm/accounting evidence；watchboard 不是 reviewer 证据。

如果 `CURRENT.md` 缺少字段，看板必须显示 parse warning 和 `unknown/blocked`，不得回退到旧 round、旧 critic path 或 hardcoded token。

## 生成

从 CARE root 运行：

```bash
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/build_route_watchboard.py --user aereinh
```

默认输出：

```text
results/watchboard/index.html
results/watchboard/status.json
```

验证用临时输出建议写到 `/tmp`：

```bash
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/build_route_watchboard.py --user aereinh --output-dir /tmp/care_watchboard_verify
```

## Live Serve

Canonical live service 使用 `127.0.0.1:8766`，并且必须用 repo env Python：

```bash
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/build_route_watchboard.py --user aereinh --serve --host 127.0.0.1 --port 8766
```

`--serve` 不是一次性静态快照。服务收到 `/`、`/index.html` 或 `/status.json` 请求时，会按 `--refresh-seconds` 重新采集 CURRENT、route packet、tmux、Slurm、process 和 ops service 状态并刷新 generated output。

历史 `8765` 或 bare `python ... --serve` 是 legacy/duplicate risk，可能覆盖 `results/watchboard/status.json`。替换 live service 时只能维护 `care_watchboard` session/window 和 exact matched watchboard serve 进程；不得 send-keys 到 `care_route_A/B/C`，不得触碰 Route A/B/C controller。

## Schema

`status.json` 顶层包含：

```text
portfolio_round
routes[route_id].portfolio_state
routes[route_id].planning_gate
routes[route_id].controller_authority
routes[route_id].runtime_state
routes[route_id].slurm_attempts
routes[route_id].tmux_activity
routes[route_id].packet_state
routes[route_id].review_state
routes[route_id].next_action
warnings[]
staleness[]
forbidden_actions[]
live_service_state
ops_services.watchboard_server
ops_services.watchboard_tunnel
ops_services.controller_notifier
```

每条 active route 的 critic/controller/reviewer 状态必须来自 CURRENT 绑定与 route-local evidence，不得用 main/coordinator 状态替代 route packet truth。Deferred/dormant route 只展示历史证据和 topology 风险，不进入 active completion summary。

`ops_services.controller_notifier` 展示 notifier health：`Notify` tmux window、watcher loop 进程、state/status/log paths、last scan、last event、last email status、enabled routes、config warnings，以及 SMTP secret 是否存在的布尔值。不得写出 SMTP password 或 secret 内容。

## Runtime Rules

下列状态一律不是完成：

```text
PENDING
RUNNING
NEEDS_MONITOR
PENDING_MONITOR
JOB_SUBMITTED
PENDING_PRIORITY
AWAITING_SACCT
SCIENTIFIC_UNDERTRAINED
submitted-only
undertrained
```

如果 packet 写着 `NEEDS_MONITOR` 且 `squeue`/`sacct` 仍 pending/running/awaiting-accounting，看板必须明确显示 monitor, not completion。Slurm job IDs 优先从 packet、ledger、finalizer_state 和 controller_context 抽取；job name fuzzy match 只能作为 low-confidence fallback。

`general` partition 作业只读展示，不进入 CARE GPU routing summary，也不得给取消建议。`volta-gpu` 可用性必须按 packet/ledger compatibility evidence 展示；如果已有 `sm_70`、PyTorch no-kernel-image 或 V100 incompatible 记录，不得只因 volta 空闲提示可用。

## tmux Discovery

Route sessions 从 `care_route_A`、`care_route_B`、`care_route_C` 发现。Controller window 按 convention 解析：

```text
RouteX-RoundNNController
RouteX-Controller   # legacy/generic
```

active controller 优先匹配当前 `portfolio_round.round_id` 的 round-specific window。旧窗口只标为 legacy/inactive；pane 处于 sleep/monitor 时仍必须与 Slurm/packet truth 交叉验证。

## Safety And Git Boundary

Implementation 只在 main worktree 修改源码、文档和测试：

```text
/users/a/e/aereinh/CARE
```

Route worktrees 只读检查：

```text
/users/a/e/aereinh/CARE_worktrees/route_A
/users/a/e/aereinh/CARE_worktrees/route_B
/users/a/e/aereinh/CARE_worktrees/route_C
```

提交只 stage 必要文件：

```text
scripts/ops/build_route_watchboard.py
docs/route_watchboard.md
tests/ops/test_build_route_watchboard.py
```

不要 force-add `results/watchboard/`，除非另有明确决策要求 tracked static artifact。默认保持 generated/ignored。

提交前验证：

```bash
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python -m pytest -q tests/ops/test_build_route_watchboard.py tests/ops/test_controller_notifications.py
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/build_route_watchboard.py --user aereinh --output-dir /tmp/care_watchboard_verify
git diff --check
curl -fsS http://127.0.0.1:8766/status.json
```
