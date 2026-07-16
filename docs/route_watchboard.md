# SRR 三路线动态看板

`scripts/ops/build_route_watchboard.py` 生成 CARE SRR Route A+B+C 的只读动态看板。它用于查看 route 合同状态、轻量证据、tmux、Slurm 当前作业、最近 Slurm 作业和可审查性，不用于执行任何操作。

看板不会提交、取消、训练、上传、合并、推送，也不会产生 route promotion、route negative 或最终科学结论。

## 生成

从 CARE root 运行：

```bash
python scripts/ops/build_route_watchboard.py --user aereinh
```

默认输出：

```text
results/watchboard/index.html
results/watchboard/status.json
```

HTML 默认每 60 秒刷新一次。可以显式设置：

```bash
python scripts/ops/build_route_watchboard.py --user aereinh --refresh-seconds 60
```

## 页面内容

看板以中文为主，只保留必要英文，例如 `Route A/B/C`、branch、worktree、文件路径、Slurm state token、job id、partition、命令名和指标/任务名。

每条 route 展示：

- route 目的、下一个 gate、controller/reviewer tmux 可见性、worktree 变更数。
- SRR 架构/合同状态；合同未落地时显示 route 默认说明。
- result packet、controller report、manifest、completion check、review request、review 等轻量证据是否存在。
- packet 中提取到的状态 token，例如 `NEEDS_MONITOR`、`JOB_SUBMITTED`、`AWAITING_REVIEW`。
- packet 中提取到的 Slurm job id，以及 `squeue`/`sacct` 回填的当前或最近作业状态。
- 中文可审查性结论：例如“不可作为完成包审查”“可进入独立审查”“尚不可审查为完成”。

## 未完成状态规则

只要 result packet 或 Slurm 当前态包含以下任一情况，看板必须显示未完成，不能显示为完成包：

```text
NEEDS_MONITOR
PENDING_MONITOR
JOB_SUBMITTED
PENDING_PRIORITY
RUNNING
AWAITING_SACCT
```

如果作业已经结束但没有后续聚合证据，看板应显示“需补证据”或“不可作为完成包审查”。Controller 报告只能作为运行态或待审查证据，不能替代独立 reviewer，也不能给出最终科学结论。

## Slurm 数据

看板只读调用：

```text
squeue -h -u <user> -o %i|%u|%P|%j|%T|%M|%R
squeue -h -u <user> -p htzhulab|a100-gpu|volta-gpu -o %i|%u|%P|%j|%T|%M|%R
sinfo -o %P|%a|%l|%D|%t|%G
sinfo -p htzhulab|a100-gpu|volta-gpu -o %P|%a|%l|%D|%t|%G
sacct -n -P -S <最近14天> -u <user> --format JobIDRaw,JobName,Partition,State,ExitCode,Elapsed,Start,End
```

如果 `sacct` 不可用，看板仍会生成，并在风险区显示“sacct 最近作业查询不可用”。

分区摘要只展示 CARE GPU 分区：`htzhulab`、`a100-gpu`、`volta-gpu`。`general` 和 `general_big` 不进入分区摘要。

`general` partition 作业会显示为“只读展示”。这些作业可能维持远程开发连接，不能从 watchboard 取消或修改。

## 本地浏览

`--serve` 不是一次性静态快照。服务收到 `/`、`/index.html` 或 `/status.json` 请求时，会按 `--refresh-seconds` 间隔重新采集 route、tmux、Slurm 和 result packet 状态并更新输出文件。

```bash
python scripts/ops/build_route_watchboard.py --user aereinh --serve --host 127.0.0.1 --port 8765
```

然后打开：

```text
http://127.0.0.1:8765/index.html
```

如果浏览器不在 CARE 服务器上，使用现有 tunnel 或 SSH port forwarding。

## Tunnel 注意事项

当前工作区存在未跟踪本地辅助脚本：

```text
jobs/watchboard_tunnel.sh
```

该脚本指向 `127.0.0.1:8766`，而 watchboard serve 默认端口是 `8765`。本看板改造不修改、不覆盖、不纳入该未跟踪脚本；如果后续要正式管理 tunnel，需要单独决策端口和版本控制策略。

## 安全边界

看板界面禁止加入任何操作按钮或调用以下动作：

```text
scancel
sbatch
srun
git merge
git push
upload
```

它是运行态可视化工具，不是 executor、controller、finalizer 或 reviewer。
