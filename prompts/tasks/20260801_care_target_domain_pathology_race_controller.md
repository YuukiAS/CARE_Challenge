---
task_key: 20260801_care_target_domain_pathology_specialist_race
task_kind: scientific_milestone
task_type: parallel_target_domain_model_race
status: AUTHORIZED
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 4
executor_count: 4
parallel_execution_allowed: true
executor_plan_path: prompts/tasks/20260801_care_target_domain_pathology_race_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: true
validation_upload_authorized: false
docker_upload_authorized: false
new_slurm_job_authorized: false
existing_interactive_allocation_only: true
---

# CARE 完整三模态病种专属模型并行竞速 Controller

## 一、目标

本 Controller 必须完整执行：

```text
prompts/blueprints/CARE_target_domain_pathology_specialist_race_20260801.md
prompts/tasks/20260801_care_target_domain_pathology_race_executor_plan.yaml
```

本轮不是继续修 CARE-QIF v2，也不是宽泛搜新模型。唯一目标是：在相同 canonical fold2/fold3 完整三模态病例上，同时训练并比较四条 literature- and evidence-backed 模型 lane，并冻结一个全局 scar source 与一个全局 edema source，判断是否形成比同划分目标域 nnU-Net 更好的 submission candidate。

四条 lane：

```text
M0 TD-NNUNET
M1 MYOPSNET-L-CARE
M2 I-MMSEG-CARE
M3 CARE-TDS
```

## 二、启动与同步

```bash
cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH

git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -20
git diff --check
```

若 main 落后且工作树干净：

```bash
git pull --ff-only origin main
```

不得 reset、clean、覆盖或 stash 用户未提交改动。若改动与本任务 write scope 冲突，形成 `OPERATIONALLY_BLOCKED_ASSET_OR_IMPLEMENTATION` 终态 packet，并完成 push/notify。

必须确认 `origin/main` 至少包含：

```text
149daeb8d0170ac477df3bc9cf3eaefae0d3cc00
351b6b53949ad4e7352303b4bc6a2d1961e3c68d
52dcd4b477f58ec8866b13efc70401d3e0e1b8d8
```

## 三、强制阅读和视觉门

完整读取：

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

视觉读取当前 Project 材料中的：

```text
SRR-v2
SRR-v2.5
SRR-v3
```

在 `controller_context.json` 写：

```text
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: PASS
recovered_route_objective: pathology-specific evidence, soft anatomy context, negative-space accounting, full-volume safety
```

若无法视觉解释，停止为 `OPERATIONALLY_BLOCKED_ASSET_OR_IMPLEMENTATION`。

## 四、状态与证据边界

必须读取：

```text
results/20260801_mosaic_leaderboard_live_snapshot/leaderboard_snapshot.md
results/20260731_care_qif_v2_signal_audit/**
results/20260731_care_myopath_a0_a3_full_volume_closure/**
results/20260731_care_myowall_geometry_diagnostic_closure/**
results/20260730_care_failure_forensics_deep_research_packet/**
results/experiments/MyoPS-Net_iteration_log.md
```

确认：

```text
MoSAIC-attributed scar = 0.6965
MoSAIC-attributed edema = 0.6255
historical OrganAgent nnU-Net scar = 0.6258
historical OrganAgent nnU-Net edema = 0.6691
visible second-tier scar = 0.7323
visible second-tier edema = 0.7258 or 0.7324
```

这些 hosted 数字只作目标边界，不得参与 checkpoint、threshold、source selection 或本地 PASS。

`CURRENT.md` 和 wiki 若仍停留在 MyoWall 状态，记录为 stale；执行终态后更新为本任务诚实结果，不得把未完成 lane 写成成功。

## 五、Controller 先冻结数据与 split

数据合同：

```text
Dataset501_CAREMyoPS
complete tri-modal total = 80
CenterB = 35
CenterC = 45
input = [LGE,T2,C0]
scar = label 5
pure edema = label 4
injury = label 4|5
```

正式 folds：

```text
fold 2
fold 3
```

从 canonical `splits_final.json` 生成每折：

- complete tri-modal outer；
- complete tri-modal development pool；
- deterministic 20% inner selection；
- remaining actual train。

Inner 分层：

```text
center × scar-volume quartile × injury-volume quartile
seed = 20260801
```

必须在 manifest 中核对：

```text
fold2 contains Case3008, Case2019, Case2034 in outer
fold3 contains Case3009, Case2021 in outer
```

若 canonical split 不符合，记录真实 fold，不得移动病例以迎合蓝图；随后停止为数据合同冲突，不得自建有利 split。

Outer 只能在所有 lane checkpoint 与全局 source selection 冻结后评价一次。

## 六、现有 interactive allocation 硬门

只允许现有 RUNNING interactive allocation。

先执行：

```bash
squeue -u "$USER" -o '%i|%j|%P|%T|%M|%L|%R|%b'
scontrol show job <candidate_job_id>
sstat -j <candidate_job_id>.batch --format=JobID,AveCPU,AveRSS,MaxRSS
```

必须机器确认：

```text
state = RUNNING
allocated/free GPUs >= 4
remaining time >= 10:00:00
allocation not owned by another active CARE controller
```

严格禁止：

```text
salloc
sbatch
提交任何新 Slurm job/allocation
```

若不足，立即写完整 blocker packet，commit/push main，调用 notifier：

```text
scientific_decision = OPERATIONALLY_BLOCKED_EXISTING_ALLOCATION_INSUFFICIENT
```

不得偷偷改为串行训练。

## 七、四 Executor 并行隔离

按 executor plan 创建四个本地 worktree/branch。用户已授权这些 local-only branch 用于并行隔离；禁止推送这些 branch。

四个 Executor 同时开始，每个占一个 GPU：

```text
GPU0 -> M0 TD-NNUNET
GPU1 -> M1 MYOPSNET-L-CARE
GPU2 -> M2 I-MMSEG-CARE
GPU3 -> M3 CARE-TDS
```

使用同一 interactive allocation 内的独立 step：

```bash
srun --jobid="$INTERACTIVE_JOB_ID" --overlap --exclusive \
  --ntasks=1 --cpus-per-task=<lane_cpu> --gres=gpu:1 \
  bash -lc '<lane command>'
```

Controller 必须记录每个 step ID、CUDA_VISIBLE_DEVICES、PID、tmux window、log、runtime dir、result dir、start/end/state/exit code。

每个 lane fold2 后继续 fold3；四个 lane 彼此并行，单 lane 内两个 fold 串行。

## 八、实现验收

### M0

- exact stock PlainConvUNet；
- complete encoder/decoder/head；
- parameter-byte coverage `>=0.99`；
- FP32 stock parity `<=1e-6`；
- six-class official decode；
- no new loss/postprocess。

### M1

- C0/LGE/T2 only；
- CMFF、MPC、scar/edema branches真实 active；
- no T1/T2* placeholder in forward；
- only complete cases；
- pure edema label4, scar label5；
- full-volume reconstruction verified。

### M2

- official source commit/license/weights SHA；
- official intensity-prior feature enhancement active；
- official class feature modulation active；
- no runtime GPT call；
- not replaced by rank channels；
- external asset lane may use exact `LANE_BLOCKED_EXTERNAL_ASSET` only with evidence。

### M3

- same full stock backbone as M0；
- independent scar/pure-edema/injury/boundary heads；
- stock pathology logits absent from final prediction；
- CATMIL/lesion-MIL/safe-remote-FP losses implemented and direct-gradient verified；
- injury/boundary losses implemented；
- M0/M3 batch descriptor hashes identical；
- no query, prototype, router, ROI, hard geometry or bounded residual。

每个 lane 必须通过：one-batch overfit、finite loss、gradient audit、save/reload、full-volume one-case inference、known-bad preflight，才可正式训练。

## 九、训练预算

M0/M3 每 fold：

```text
4000 optimizer steps
AdamW
backbone/decoder lr 1e-4
classifier/new head lr 5e-4
weight decay 1e-4
effective batch 4
warmup 250
cosine to 1e-6
checkpoint + inner full-volume eval every 500
all 8 checkpoints eligible
```

M1/M2 每 fold：

```text
60–120 epochs
checkpoint + inner full-volume eval every 10 epochs
cannot stop before epoch 60
selected checkpoint reload required
```

任何 startup failure、OOM before loop、partial run、preflight或少于预算均为 zero formal credit。允许同范围 operational retry，但不得改 model/split/budget/label/eval semantics。

## 十、评价和组合

所有 lane 使用同一 canonical evaluator，必须输出：

```text
Dice, HD95, exact HD, PRE, SEN
lesion recall, small-lesion recall
remote FP count/volume
blood-pool-adjacent FP
component count, volume ratio
case-wise help/harm
CenterB/CenterC subgroup
```

先合并两个 fold 的 inner 结果，按 blueprint 的 lexicographic rule 冻结：

```text
one global scar source
one global edema source
```

禁止：

- outer-driven source selection；
- per-fold source selection；
- per-case selector；
- threshold tuning on outer。

冻结后，以 M0 anatomy + global scar source + global edema source + fixed scar priority，在 fold2+fold3 outer 只评价一次。

固定病例必须逐例解释：

```text
Case3008
Case3009
Case2019
Case2034
Case2021
```

## 十一、科学终态

严格按 blueprint 门输出且只允许：

```text
TARGET_DOMAIN_CANDIDATE_READY
SCAR_ONLY_CANDIDATE_READY
EDEMA_ONLY_CANDIDATE_READY
NO_GO_TARGET_DOMAIN_RACE
OPERATIONALLY_BLOCKED_EXISTING_ALLOCATION_INSUFFICIENT
OPERATIONALLY_BLOCKED_ASSET_OR_IMPLEMENTATION
```

模型成功必须来自 full-volume fold2+fold3 outer，不得用 training loss、inner-only、patch proxy、文件存在或 validator PASS 代替。

即使候选通过，本 goal 仍不授权：

```text
official validation inference/upload
Docker upload
hosted claim
Cine training
new Slurm job
```

## 十二、合并、commit 和 push

四个 Executor 只做 local commits。Controller 按固定顺序合并：

```text
M0 -> M1 -> M2 -> M3 -> integration/finalizer
```

所有 runtime、checkpoint、NIfTI、feature tensor、大日志保持 ignored，不进入 Git。

终态 commit message：

```text
experiment: complete target-domain pathology specialist race
```

Push 使用共享锁：

```bash
exec 9>/users/a/e/aereinh/.care-main-push.lock
flock -x 9

git fetch origin main
git rebase origin/main
./envs/env_CARE/bin/python scripts/validation/validate_target_domain_pathology_race.py --phase final
git diff --check
git push origin HEAD:main
```

禁止 force push，禁止推送 task branch。若 origin/main 前移，最多三次 fetch/rebase/validator/push。真实冲突无法机械处理时形成 blocker packet并通知。

验证：

```bash
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git ls-remote origin refs/heads/main | cut -f1)
test "$LOCAL_SHA" = "$REMOTE_SHA"
```

## 十三、Notifier

Goal achieved 或 blocked 都必须通知。

只有在：

- 全部 srun step terminal；
- aggregation/validator/commit 完成；
- push main 成功；
- remote SHA 验证完成；

之后写：

```text
results/20260801_care_target_domain_pathology_specialist_race/notification_brief.json
```

字段必须包含：

```text
task_name
final_status: complete | blocked
commit_status
push_status
key_conclusion
blocked_or_failure_reason
slurm_terminal_status
evidence_paths
next_step
```

随后执行：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

禁止自写 SMTP。若生成 notification receipt，必须再 commit/push main 并重新验证 SHA。

## 十四、最终返回

先用自然中文说明：

1. 为什么旧 MyoPS-Net 是否被公平重测；
2. 完整三模态 fine-tune 本身带来多少收益；
3. I-MMSeg 强度先验是否真实有效；
4. CARE-TDS 是否修复 Case3008/3009；
5. Case2019 remote FP 是否下降；
6. Case2034 edema 边界/体积是否改善；
7. 哪个全局 scar source、edema source 被选中；
8. 是否达到 candidate gate；
9. 哪些动作仍未授权。

随后报告：

```text
controller_verification_decision
scientific_decision
existing allocation ID / GPU count / remaining time
M0/M1/M2/M3 implementation and training status
fold2/fold3 case counts
all srun step IDs and terminal states
scar summary
edema summary
case-wise sentinel findings
global source selection
validator and known-bad status
commit SHA
remote main SHA
notifier receipt
```
