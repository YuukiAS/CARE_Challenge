# CARE 三路线组合计划：2026-07-15 至 2026-07-27

## 当前结论

当前 setup 只完成了三路线并行开发环境。下一步不是直接训练，也不是直接启动三个 controller goal，而是让 GPT/Planner 分别写清楚 Route A、Route B、Route C 的具体任务合同；每条 route 经过独立 Critic 审查后，再启动对应 controller。

三条路线的关系是并行推进、互不阻塞、最终汇总比较：

```text
Portfolio planner
  -> Route A critic -> Route A controller -> Route A reviewer
  -> Route B critic -> Route B controller -> Route B reviewer
  -> Route C critic -> Route C controller -> Route C reviewer
  -> final reconciliation -> final reviewer -> package/submission decision
```

## 共同规则

Route A、Route B、Route C 都从同一个 setup commit 开始。每条路线都有独立 branch、worktree、controller、result namespace、runtime namespace、logs、locks、finalizer 和 reviewer。

任何 route 不得写入其他 route 的 worktree 或 runtime。正式训练必须等该 route 的 implementation validator 通过后才能开始。根 wiki 和 `current_state` 只允许在最终 reconciliation 阶段更新，不能由某条未审查 route 单独改写。

主工作树：

```text
/users/a/e/aereinh/CARE
```

只用于：

```text
main
portfolio setup
final reconciliation
shared infrastructure
```

不要在主工作树直接开发 Route A、B、C 的模型代码。

## 三条路线定位

Route A：

最小工作量、最快形成非纯 nnU-Net submission candidate 的路线。重点是尽快给出能本地验证、能打包的候选，不追求完整论文架构。

Route B：

中等工作量、完整架构实现路线。重点是把 SRR-v3 的 MyoPS 和 Cine 关键模块补齐，先通过真实 forward / loss / gradient / reload / intervention 验收，再正式训练。

Route C：

最大工作量、继承 M10 follow-up2 的完整 evidence / Cine fidelity 路线。重点是补齐历史证据、真实 checkpoint replay、真实 component intervention、CineMA / registration / temporal fidelity，不再作为 Route A/B 的阻塞前置。

## Branch 与 Worktree

| Route | Branch | Worktree | Controller tmux | Reviewer tmux |
| --- | --- | --- | --- | --- |
| Portfolio | `main` | `/users/a/e/aereinh/CARE` | `care_portfolio` | final reviewer only |
| Route A | `route_A` | `/users/a/e/aereinh/CARE_worktrees/route_A` | `care_route_A_controller` | `care_route_A_reviewer` |
| Route B | `route_B` | `/users/a/e/aereinh/CARE_worktrees/route_B` | `care_route_B_controller` | `care_route_B_reviewer` |
| Route C | `route_C` | `/users/a/e/aereinh/CARE_worktrees/route_C` | `care_route_C_controller` | `care_route_C_reviewer` |

Reviewer worktree 只能在对应 controller 提交可审查 packet 后创建。Reviewer worktree 必须固定到被审查 commit，不能跟随 controller 的可变 branch。

## tmux 会话

当前长期会话设计为 7 个：

```text
care_portfolio
care_route_A_controller
care_route_B_controller
care_route_C_controller
care_route_A_reviewer
care_route_B_reviewer
care_route_C_reviewer
```

现在只需要启动前 4 个 core session。三个 reviewer session 等对应 route 产生 committed packet 后再创建，避免 reviewer 和 controller 共用可写工作区。

## Compute Routing

共享 routing 策略在：

```text
configs/routes/partition_routing.yaml
```

可用 partition：

```text
htzhulab
a100-gpu
volta-gpu
```

有多个独立 ready job 时，优先把不同工作分配到不同 partition，避免浪费 GPU 跑同一个 mirror。只有单个关键路径 job pending，且三种 partition 都语义兼容时，才使用三路 race。

三路 race 必须满足：

```text
same logical_run_id
same code/config/split/checkpoint hash
isolated attempt output directories
one shared atomic winner lock
first lock holder becomes official attempt
started losers write RACE_LOST and exit
pending losers are cancelled by watcher
```

V100 只有 16 GB，必须显式声明兼容。不得为了适配 V100 而偷偷改变模型、batch 语义、loss、label、split 或科学预算。如果 V100 不兼容，就把 V100 用于独立 inference、checkpoint replay shard、validator 或轻量任务。

## 每日计划

| 日期 | Route A | Route B | Route C | Portfolio / shared |
|---|---|---|---|---|
| 7月15日 Day 0 | 创建分支、worktree、controller 环境 | 创建分支、worktree、controller 环境 | 创建分支、worktree、controller 环境 | 清理分支，建立 tmux、routing 和 README |
| 7月16日 Day 1 | 完成 route 合同和代码缺口清单 | 完成完整架构代码缺口清单 | 完成 M10 继承状态和可复用资产清单 | 三个 Critic 可并行审查，互不阻塞 |
| 7月17日 Day 2 | 集中补齐代码，不做正式训练 | 集中补齐全部核心代码，不做正式训练 | 补齐 evidence / Cine fidelity 实现，不做正式训练 | 检查三个 partition 和 route isolation |
| 7月18日 Day 3 | 真实病例 smoke、梯度和 checkpoint 验收 | 全架构 forward、loss、intervention 和 reload 验收 | replay / Cine implementation gate | 各 route implementation freeze |
| 7月19日 Day 4 | 首轮有预算训练或评估 | 第一阶段训练 | evidence replay 与 Cine 首阶段运行 | 三 partition 全面调度 |
| 7月20日 Day 5 | 第一次候选继续/停止决策 | proposal / 中间机制继续/停止决策 | 第一批完整 evidence / Cine 决策 | 汇总但不合并科学结论 |
| 7月21日 Day 6 | 通过 gate 后扩展 folds / cases | refinement 或下一训练阶段 | 后续 runtime 阶段 | Docker 和 package dry-run 开始 |
| 7月22日 Day 7 | 形成第一版候选 package | 形成完整架构单折候选 | 形成可审计的 M10 / Cine 候选 | route-local reviewer 开始 |
| 7月23日 Day 8 | 根据证据做最后一次定向修改 | 根据机制证据做最后一次定向修改 | 补齐剩余 evidence / runtime | 比较 reviewed packets |
| 7月24日 Day 9 | 冻结候选 | 冻结候选 | 冻结可用结果 | Docker、paper 表格、图和 submission QA |
| 7月25日 Day 10 | 最终 route packet | 最终 route packet | 最终 route packet | final reconciliation 与最终 reviewer |
| 7月26日 Buffer | 只修复 runtime 或 packaging 问题 | 只修复 runtime 或 packaging 问题 | 只修复 runtime 或 packaging 问题 | 上传和 Docker 缓冲 |
| 7月27日 Deadline | 禁止新增科学实验 | 禁止新增科学实验 | 禁止新增科学实验 | 最终提交 |

硬边界：

```text
Day 2 之前不得用长训练掩盖缺失实现。
Day 3 implementation gate 未通过的 route 不得进入正式训练。
某条 route 失败不阻塞其他 route。
某条 route review 未完成时，不得写入 root current state。
7月26日不得再引入新架构或新 loss。
```

## 下一步工作流

1. GPT/Planner 写三个 route 的具体合同与 executor plan。
2. 三个 route 分别进入 Critic 审查；Critic 可以并行。
3. 某条 route 的 Critic 通过后，即可启动该 route controller，不必等另外两条。
4. 每条 route controller 只管理本 route 的 executor、validator、finalizer 和 mapper。
5. 每条 route 产生 committed packet 后，创建对应 reviewer worktree 和 reviewer session。
6. 三条 route 的 reviewed packet 完成后，由 final reconciliation 比较候选并决定 package/submission。

## 验证命令

从主工作树运行当前仍有效的轻量检查：

```bash
./envs/env_CARE/bin/python -m pytest -q tests/ops/test_build_route_watchboard.py
git diff --check
```

查看当前状态：

```bash
bash scripts/ops/route_status.sh
```
