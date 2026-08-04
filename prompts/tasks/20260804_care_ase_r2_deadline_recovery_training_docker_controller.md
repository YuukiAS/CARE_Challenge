---
task_key: 20260804_care_ase_r2_deadline_recovery_training_docker
task_kind: scientific_milestone
task_type: absolute_deadline_recovery_training_inner_selection_and_docker_finalization
status: AUTHORIZED_BY_USER
risk_level: critical
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: null
mapper_slots: 1
mapper_required: false
architecture_impact: none
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
review_required: false
review_mode: none
reviewer: none
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: false
formal_training_authorized: true
inner_evaluation_authorized: true
outer_access_authorized: false
validation_upload_authorized: false
docker_source_and_build_staging_authorized: true
docker_upload_authorized: false
organizer_email_send_authorized: false
fixed_interactive_jobs:
  fold1: 61794608
  fold4: 61830309
official_docker_deadline_hkt: 2026-08-04T15:59:00+08:00
training_and_selection_cutoff_hkt: 2026-08-04T14:59:00+08:00
---

# CARE-ASE R2 截止日前恢复训练、真实内层选择与 Docker 最终准备 Controller

## 一、结论和最高优先级

上一任务在 fold1/fold4 都只训练到 step16、没有任何 inner comparison、没有 deployable checkpoint 的情况下，把“吞吐不足”错误写成了 `CARE_ASE_INNER_NO_GO_USE_FALLBACK` 并停止训练。该结论不是科学 no-go，本任务明确将其作废。

本任务必须立即恢复 CARE-ASE 训练，持续运行到绝对训练截止时间；吞吐慢、预计无法达到 14000 步、早期没有分数、fallback 已经可用，都不是提前停止理由。Controller 只能在绝对截止时冻结实际完成的 checkpoint 和证据，然后用最后一小时完成 Docker 最终准备。

官方 Docker/Test Results 截止时间为 2026-08-03 23:59 PST，即香港时间：

```text
2026-08-04 15:59 HKT
```

绝对时间线：

```text
现在开始至 14:59 HKT：源码运行修复、两折并行训练、checkpoint、最终快速 inner 比较和候选冻结
14:59–15:59 HKT：只做 Docker checkpoint 注入/验证/归档，或确认已验证 fallback archive 可立即提交
```

Controller 不得再次用相对 T0、九小时窗口、预计 ETA、fallback 完整性或旧 terminal JSON 提前结束。

## 二、上一错误终态的处理

读取但不得继承其科学结论：

```text
results/20260804_care_ase_r2_emergency_9h_training_docker/terminal_scientific_decision.json
results/20260804_care_ase_r2_emergency_9h_training_docker/controller_report.md
```

固定解释：

```text
step16 runs = early runtime evidence only
named-evidence canary PASS = implementation liveness evidence
CARE_ASE_INNER_NO_GO_USE_FALLBACK = invalid because inner selection was not performed
no_formal_training_resume_after_no_go = superseded by this explicit user authorization
```

不得删除历史 packet；在新结果中标注 `SUPERSEDED_PREMATURE_TERMINATION`。

## 三、启动与同步

```bash
cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH

git fetch origin main --prune
git checkout main
git pull --ff-only origin main
git status --short --branch
```

确认当前 main 包含本任务文件。完整读取仓库启动协议、上一 emergency task、最新 source/permit/runtime packet、Docker fallback packet 和 Slurm skill。

创建持久 tmux：

```text
care_ase_deadline_recovery
  controller
  fold1
  fold4
  monitor
  docker
  finalizer
```

Controller 必须持续运行到 15:59 HKT 前的终态，不得通知后退出、不得在训练 RUNNING 时完成 Goal。

## 四、GPU 恢复和替代路由

首先检查：

```bash
scontrol show job -dd 61794608
scontrol show job -dd 61830309
squeue -j 61794608,61830309 -o '%.18i %.12P %.35j %.2t %.10M %.10l %.4D %R'
```

固定优先映射：

```text
61794608 -> fold1
61830309 -> fold4
```

若 allocation 仍存活，立即复用，不允许再做长审计。

若某 allocation 已结束或无法创建合法 GPU job-step：

1. 另一 fold 继续，不得一起等待；
2. 立即按 `.agents/skills/slurm-routing-partition/SKILL.md` 提交 replacement；
3. 优先 `htzhulab`，若预计等待相对剩余时间过长，立即与 `a100-gpu` 做隔离 routing race；
4. 首个开始运行者获胜，取消仍 pending 的 mirror；
5. 不得等待用户确认，不得裸跑 login-node GPU。

任何单次 startup、OOM、lock、permit、manifest 或 checkpoint 错误都由同一 Controller 直接修复并重启受影响 fold，不得结束 Goal。

## 五、最终源码和允许的即时修复

当前科学实现以最新已通过 canary 的 CARE-ASE source 为起点。不得改模型结构、loss 权重、patch、四 microbatch、Stage 定义、采样比例、label/decode 语义。

允许在启动后最多 20 分钟内直接修复下列运行问题：

- metrics 每个 microbatch `.cpu().item()` 或同步；
- image/seg/properties/full-case target 重复解压或重复 hash；
- deterministic ordered prefetch/pinned-memory/non-blocking H2D；
- 日志逐步 fsync；
- checkpoint 频率和任意完整 step 的安全保存；
- signal/lock/permit/manifest/absolute-path 启动错误；
- 已明确发现的 sampler、augmentation、source-z、inner monitor/selector 接口错误。

速度修复必须保持逐 tensor 数值语义；不得采用 AMP、TF32、较小模型、较小 patch、较少 microbatch、删除 head/loss/augmentation 或降低采样预算来换速度。

若 critical source 变化：

- 创建新的 implementation commit；
- 重建 critical source manifest、runtime bundle 和两个 fold permit；
- 旧 step16 以及旧 source 的任何新运行均为 zero-credit；
- 两折从 step0 启动。

运行主循环必须：

```text
非日志 step: collect_metrics=false
每20 step: 聚合一次 metrics
每 step: 仅一次必要 finite/loss/grad 摘要同步
case arrays和target cache: LRU，首次验证后不重复hash
日志: 批量flush
```

## 六、训练不得再次提前停止

两折从 step0 并行启动。由于旧运行没有 checkpoint，不得声称从 step16 resume。

原科学 schedule 保持：

```text
Stage A 0–2000
Stage B 2000–10000
Stage C 10000–14000
```

但当前截止日前客观无法完成 14000 步时：

- 不得伪造完成；
- 不得压缩或跳过 Stage；
- 不得因为 ETA 大于剩余时间而停止；
- 必须持续训练到 `2026-08-04 14:15 HKT`，然后保存最后完整 step checkpoint；
- 14:15–14:59 用于 checkpoint reload、快速 inner comparison和候选冻结；
- 若比较提前完成，允许训练继续到最迟14:30，但必须确保14:59前完成选择。

为避免再次白跑，checkpoint 改为：

```text
每250完整 optimizer steps保存并独立reload验证
收到SIGUSR1/SIGTERM时在最后完整step安全保存
14:15 HKT强制保存最后完整step checkpoint
```

任一 verified checkpoint 都可用于运行恢复；但科学报告必须明确它实际处于哪个 Stage、完成多少步，不能称为完整 14000-step 模型。

Controller 不允许在14:59前把以下任一理由当成终态：

```text
ETA too long
cannot reach 14000
fallback already ready
only Stage A completed
no inner result yet
one fold slower
checkpoint below old fixed candidate set
```

## 七、在线有效性监控

已通过的 named-evidence canary若 source未变可继承；source变化后必须在 step100 前重跑。

每20步记录：

```text
step seconds median/p90
loss finite
parameter/gradient/Adam finite
actual LR和Stage
scar/edema/anatomy关键loss
no-T2 edema call/gradient
GPU utilization/VRAM
case cache hit rate
target cache hit rate
```

每100步在一个冻结 actual-train sanity batch 上做不改变训练状态的预测检查：

```text
scar/edema非空率
volume ratio
remote component count
重复推理确定性
```

发现明确数值或实现错误时直接修复；不得把普通早期低分当作错误，不得改模型或阈值追分。

## 八、截止日前快速 inner 比较

训练开始前从每 fold 的 frozen inner 中确定一个 6-case `DEADLINE_FAST_PANEL`，覆盖：

```text
CenterB tri-modal
CenterC tri-modal
small scar
scar remote-FP risk
edema under-activation
edema over-extent
```

不得包含 outer，不得按结果换病例。

不在训练早期反复占用 GPU 做全体积评价。固定执行：

1. 每 fold 第一个 `>=500` 的 verified checkpoint：若在 13:15 HKT 前产生，后台完成一次 3-case mini panel；训练继续。
2. 14:15 HKT 的最后 verified checkpoint：14:15–14:59 在两块 GPU 上并行跑各自 6-case panel。
3. 使用同病例 held-out nnU-Net OOF、同 canonical full-volume inference、同 Gaussian/mirroring/decode/physical metric。

输出至少包括：

```text
scar Dice/HD95/remote FP/component count/small-lesion recall
pure-edema Dice/HD95/sensitivity/volume ratio
case-wise help/harm
CenterB/CenterC
empty prediction
checkpoint actual step和Stage
```

紧急 CARE-ASE checkpoint 只有在以下全部满足时才可进入 Docker 候选：

```text
checkpoint reload PASS
两病种无catastrophic collapse
no-T2 safety PASS
相对stock没有多数病例明显受损
至少一个病种出现可信正向信号
无远端FP或体积爆炸
```

若没有满足，不得谎称 CARE-ASE 候选；继续使用已经验证的 fallback。这里的 fallback 选择只发生在训练和真实 panel 完成后，不能再作为提前停止训练的理由。

## 九、Docker 从现在并行准备

Docker window 从 Goal 启动时就开始，不等 checkpoint。

`docker` 窗口必须立即完成：

- CARE-ASE base image/ENTRYPOINT/dependencies/preprocess/postprocess/canonical inference；
- checkpoint作为最后一层注入；
- official input/output path和compact→official label mapping；
- `/input:ro`、`--network none`、无交互；
- host/container prediction equivalence helper；
- 保持现有 OrganAgent fallback archives、SHA和Drive链接完全不变。

绝对 Docker 最终窗口：

```text
14:59–15:59 HKT
```

若14:59选中 CARE-ASE：

1. 注入冻结 checkpoint；
2. 至少1例 official-format smoke；
3. host/container array与geometry核对；
4. clean save/load；
5. `docker save | gzip -1`；
6. 写 archive size/SHA/run command。

若 CARE-ASE 未过快速 panel、checkpoint未及时可用、或15:35前无法完成CARE-ASE归档：

- 立即冻结已验证 OrganAgent fallback archives为提交资源；
- 核对 archive/Drive link/email draft；
- 不得破坏或覆盖 fallback；
- 不得把 fallback 使用解释为 CARE-ASE 科学 no-go。

本任务不授权 Docker upload、validation upload、outer access或组织方邮件发送。最终只把资源准备到用户可以立即提交。

## 十、不可接受的终态偷换

本任务禁止使用下列终态结束：

```text
CARE_ASE_INNER_NO_GO_USE_FALLBACK（在没有真实deadline panel时）
VERIFIED_COMPLETE_WITH_FALLBACK（训练仍可继续但被提前停止时）
OPERATIONALLY_BLOCKED_DEADLINE_OR_RUNTIME
NEEDS_MONITOR
RUNNING
AWAITING_USER
```

Controller 必须持续到14:59完成训练/选择，并持续到15:59完成Docker资源冻结。

允许的最终科学分类只有：

```text
CARE_ASE_DEADLINE_CHECKPOINT_CANDIDATE
CARE_ASE_DEADLINE_CHECKPOINT_NOT_SAFE_USE_FALLBACK
```

二者都必须建立在实际完成到截止点的训练和真实 fast-panel 上；若基础设施故障导致某折缺失，使用另一折的真实结果，并如实记录，不能提前结束整个 Goal。

## 十一、必须产出

结果根：

```text
results/20260804_care_ase_r2_deadline_recovery_training_docker/
```

至少包含：

```text
controller_context.json
time_deadline_contract.json
superseded_terminal_audit.md
interactive_job_recovery.json
source_repairs.md
implementation_commit_receipt.json
training_permit_fold1.json
training_permit_fold4.json
live_status.json
training_summary_fold1.json
training_summary_fold4.json
checkpoint_manifest_fold1.json
checkpoint_manifest_fold4.json
deadline_fast_panel_fold1.json
deadline_fast_panel_fold4.json
deadline_casewise_fold1.csv
deadline_casewise_fold4.csv
deadline_checkpoint_selection.json
docker_base_staging.json
docker_finalization.json
fallback_integrity_receipt.json
terminal_decision.json
controller_report.md
completion_check.md
MANIFEST.md
notification_brief.json
```

每5分钟更新 `live_status.json`，包括当前香港时间、距离14:59和15:59剩余时间、两折step/ETA、checkpoint、GPU、Docker状态和下一动作。

## 十二、提交、推送和通知

训练/runtime不得每步提交。允许在源码运行修复后提交新的 implementation/runtime packet。

15:59前聚合轻量终态结果，更新 CURRENT/wiki，创建单个终态 commit 并 push `origin/main`。若终态 commit/push 会危及 Docker 最终准备，先完成 Docker 资源冻结，再立即补交终态 packet。

只有训练/selection/Docker资源全部达到绝对终态、所有训练进程和job-step已正确停止或保存、commit/push确认后，才运行既有 notifier：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

不得在训练进行中通知，不得用 notifier 作为停止训练的触发器。

## Executor Worker Contract

Executor 只执行本任务授权的启动修复、两折训练、checkpoint、inner fast panel、Docker staging和轻量证据。Executor不能自行宣布整个Goal完成，不能访问outer，不能上传，不能发送邮件，不能改模型科学设计。

## 最终用户回传

用自然中文明确说明：

1. 距离官方截止时实际使用了多少时间；
2. 两折最终训练到多少真实 optimizer steps、处于哪个Stage；
3. 是否发生源码运行修复和从0重启；
4. 最后 verified checkpoint；
5. deadline fast-panel相对held-out nnU-Net的病例级结果；
6. 是否选择CARE-ASE进入Docker；
7. Docker archive或fallback资源最终状态；
8. outer/upload/email均未执行；
9. HEAD/origin/main和最终证据路径。

不得只返回状态 token。
