---
task_key: 20260801_care_target_domain_race_gap_closure
task_kind: scientific_milestone
task_type: faithful_four_lane_gap_closure
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
executor_plan_path: prompts/tasks/20260801_care_target_domain_race_gap_closure_executor_plan.yaml
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
existing_interactive_required: true
new_interactive_allocation_authorized: false
htzhulab_queue_jobs_authorized: true
a100_gpu_authorized: false
volta_gpu_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

# CARE 完整三模态四模型竞速缺口闭合 Controller

## Execution Contract

必须完整执行：

```text
prompts/blueprints/CARE_target_domain_race_gap_closure_20260801.md
prompts/tasks/20260801_care_target_domain_race_gap_closure_executor_plan.yaml
```

不得只读摘要。不得把旧 `9f302fe` 的 `NO_GO_TARGET_DOMAIN_RACE` 解释为四模型科学失败。

本任务的科学对象：

```text
M0R faithful target-domain nnU-Net control
M1 MYOPSNET-L-CARE faithful adaptation
M2 I-MMSEG-CARE faithful adaptation
M3 CARE-TDS
```

本任务必须将 M0 的实际训练合同错误单独审计。旧 M0 结果保留，但只允许命名为：

```text
HIGH_LR_SHORT_FINETUNE_NEGATIVE
```

## Controller Prompt

### 1. Bootstrap

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

若main落后且工作树干净：

```bash
git pull --ff-only origin main
```

不得 reset、clean、覆盖或 stash 用户未提交文件。无关未跟踪文件保持不动。

必须确认 origin/main 包含：

```text
fd6be914b7f79777f06247e25477356d68f4a982
629a48c3b12745b6093cd99bb31829d785c37310
33de0813ef039a5ad556b01866a316f695566d59
```

### 2. Required reading and visual gate

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

视觉读取 Project 中的：

```text
SRR-v2
SRR-v2.5
SRR-v3
```

写入：

```text
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: PASS
recovered_route_objective: modality-specific evidence; pathology-specific authority; soft anatomy context; negative-space accounting; full-volume help/harm
```

无法视觉解释则形成 `OPERATIONALLY_BLOCKED_IMPLEMENTATION`，完成push和notify。

### 3. Old M0 fidelity audit

读取：

```text
scripts/training/target_domain_race/run_m0_td_nnunet.py
src/care_myocardium/nnunet/target_domain_race_trainer.py
scripts/evaluation/target_domain_race/evaluate_m0_td_nnunet_outer.py
results/20260801_care_target_domain_pathology_specialist_race/m0_td_nnunet/**
```

机器验证：

```text
actual optimizer = default nnU-Net SGD
actual initial lr = 1e-2
actual scheduler = epoch PolyLR
actual epochs = 16
actual checkpoint selection = stock checkpoint_best semantics
all 500-step full-volume inner checkpoint selection = absent
```

将旧 M0 绑定为 `HIGH_LR_SHORT_FINETUNE_NEGATIVE`。不得在新报告中写成忠实 target-domain control。

### 4. Freeze data

复用但重新 hash：

```text
results/20260801_care_target_domain_pathology_specialist_race/split_receipt.json
```

必须保持 fold2/fold3 membership 不变。不得读取 official validation。

必须写：

```text
outer_previously_accessed_for_old_M0: true
outer_role_this_task: deterministic_replay_only_after_inner_freeze
```

### 5. Existing interactive allocation

必须发现一个当前 RUNNING 的既有 interactive allocation。禁止 `salloc`。

```bash
squeue -u "$USER" -o '%i|%j|%P|%T|%M|%L|%R|%b'
scontrol show job <candidate_job_id>
```

记录：job ID、partition、GPU、剩余时间、node、owner、是否被其他controller占用。

没有可用RUNNING interactive allocation时：

```text
scientific_decision = OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST
```

随后完成阻塞packet、push main、notify。不得新建interactive allocation。

### 6. Four local executors

按照 executor plan 创建四个 local-only worktree。禁止推送 task branch。

四个 Executor 并行完成代码、资产、preflight。Controller不得用“缺wrapper”停止M1/M3；这些缺口正是本任务授权实现范围。

#### M0R

必须实现：

- exact stock parity；
- AdamW parameter groups；
- per-step 250-step warmup + cosine；
- 4000-step loop；
- common deterministic batch manifests；
- eight 500-step checkpoints；
- checkpoint reload；
- full-volume inner selection。

禁止继承旧 `nnUNetTrainerTargetDomainRace4000` 的 SGD/PolyLR语义。

#### M1

必须 pin/audit：

```text
QJYBall/MyoPS-Net@479f07028c5bdb12b405dc92212aa48ae6ba947a
```

实现 complete-trimodal exporter、C0/LGE/T2-only forward、CMFF/MPC、scar/injury targets、slice-to-volume reconstruction和canonical evaluator。

旧 `third_party/MyoPS-Net` 可作参考，但不得未经 source diff audit 直接宣称 faithful。

#### M2

必须 pin：

```text
zzzzzzl24/I_MMSeg@90f46c4eb72924509895fcda6bc6a3b8c3316e66
```

自动尝试公开source和assets，记录license/provenance/hash。保留官方CLIP prior、intensity-prior enhancement与class modulation。

若Google Drive明确要求人工批准，写：

```text
M2 lane status = ASSET_APPROVAL_REQUIRED
```

其他lane继续。禁止手工rank替代。

#### M3

严格实现 blueprint 冻结的 F0+soft context、四heads、targets、loss公式、actual-train-only hard negatives、M0R共同batch manifests和final-label interventions。

任何loss只写字符串但不进入total或无直接梯度，preflight必须失败并在同范围修复。

### 7. Formal implementation gates

每个eligible lane在正式训练前必须具备：

```text
model build/import
one real-case forward
finite loss
backward and direct target gradients
one-batch overfit
save/reload parity
full-volume one-case inference
canonical evaluator invocation
known-bad preflight PASS
```

M0R/M3额外要求 batch manifest hash identity。

M1额外要求 slice-to-volume roundtrip和T1/T2*不进入forward。

M2额外要求official module intervention改变final labels。

Controller必须检查真实diff和运行证据，不得接受声明性receipt。

### 8. Formal scheduling

严格执行：

```text
interactive first lane: M3
interactive takeover order after M3: M0R -> M1 -> M2
```

M3通过preflight后，立即在既有interactive allocation用`srun`执行fold2+fold3。

M0R/M1/M2各自通过preflight后，先提交一个`htzhulab` job排队。M2资产未通过则不提交。

Queue job固定：

```text
partition=htzhulab
gpu=1
cpus=12
mem=96G
walltime=12:00:00
one lane job runs fold2 then fold3
```

禁止提交a100-gpu/volta-gpu。

每个lane必须用原子claim：

```text
/users/a/e/aereinh/.locks/care_td_gap_closure_20260801/<lane>.claim
```

queued job和interactive step均先claim；loser写`RACE_LOST_ZERO_CREDIT`退出。

当interactive当前lane terminal：

1. 按 M0R、M1、M2 检查queue状态；
2. 第一条eligible lane若`PENDING`，`scancel`；
3. 等待`sacct`确认CANCELLED；
4. 用existing interactive `srun --jobid --overlap --exclusive --gres=gpu:1`运行该lane；
5. 若queue job已RUNNING并持claim，不重复，检查下一个pending lane；
6. 若已COMPLETED，检查下一lane；
7. 若startup失败，修复同范围bug并优先interactive exact resume；
8. 只要存在eligible pending lane，不得让interactive GPU空闲。

Submitted/PENDING/RUNNING/AWAITING_SACCT不是终态。Controller持续负责全部job/step到terminal accounting和aggregation。

### 9. Training minimums

M0R/M3每fold：

```text
4000 optimizer steps
8 checkpoint events
8 full-volume inner evaluations
selected checkpoint reload
```

M1/M2每fold：

```text
minimum 60 epochs
checkpoint/full-volume inner every10 epochs
no early stop before60
selected pathology checkpoints reload
```

不允许减少cases、step、epoch、input size、heads或loss适配资源。

### 10. Evaluation and source freeze

统一指标：

```text
Dice, HD95, exact HD, PRE, SEN
lesion recall, small-lesion recall
remote FP count/volume
blood-pool-adjacent FP
component count, volume ratio
case-wise help/harm
CenterB/CenterC subgroup
```

先用fold2+fold3 inner汇总冻结 one global scar source和one global edema source。不得per-case/per-fold选择。

冻结后才 deterministic replay fold2+fold3 outer。不得修改checkpoint、threshold、loss或source。

Final anatomy使用fold-specific stock anatomy；scar/edema使用冻结global source；scar priority固定。

固定逐例分析：

```text
Case3008
Case3009
Case2019
Case2034
Case2021
```

### 11. Terminal decision

只允许：

```text
TARGET_DOMAIN_CANDIDATE_READY
SCAR_ONLY_CANDIDATE_READY
EDEMA_ONLY_CANDIDATE_READY
NO_GO_AFTER_FAITHFUL_FOUR_LANE_EVALUATION
M2_ASSET_APPROVAL_REQUIRED_OTHER_LANES_COMPLETE
OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST
OPERATIONALLY_BLOCKED_IMPLEMENTATION
```

即使candidate ready，也不授权official validation、Docker或hosted claim。

### 12. Validator and known-bad

实现：

```text
scripts/validation/validate_target_domain_race_gap_closure.py
```

Known-bad至少覆盖blueprint 21项。尤其必须捕获：

- M0R SGD1e-2/PolyLR回退；
- M1 wrapper-only；
- M2 rank substitute；
- M3 stock pathology shortcut；
- hard-negative declaration-only；
- duplicate queue/interactive lane；
- interactive idle while eligible lane pending；
- outer-driven selection。

Validator error必须非零退出。

### 13. Integration and write scopes

Executors只写自己的plan scope并做local commit。Controller按：

```text
M0R -> M1 -> M2 -> M3 -> integration/finalizer
```

合并。

允许更新：

```text
prompts/routes/handoffs/CURRENT.md
wiki/README.md
```

但只能写诚实terminal状态。M2资产阻塞不得写成模型失败。

禁止提交checkpoint、NIfTI、feature tensor、raw data、大日志、secret。

### 14. Push

终态commit：

```text
experiment: complete faithful target-domain four-lane gap closure
```

使用锁：

```bash
exec 9>/users/a/e/aereinh/.care-main-push.lock
flock -x 9

git fetch origin main
git rebase origin/main
./envs/env_CARE/bin/python scripts/validation/validate_target_domain_race_gap_closure.py --phase final
git diff --check
git push origin HEAD:main
```

禁止force push和task branch push。

验证：

```bash
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git ls-remote origin refs/heads/main | cut -f1)
test "$LOCAL_SHA" = "$REMOTE_SHA"
```

### 15. Notifier

Goal achieved或blocked都必须notify。

只在全部jobs/steps terminal、aggregation、validator、commit、push和remote SHA验证完成后，写：

```text
results/20260801_care_target_domain_race_gap_closure/notification_brief.json
```

运行：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

不得自写SMTP。若生成notification receipt，commit/push main并再次验证SHA。

### 16. Final response

先用自然中文回答：

1. 旧M0为何不是faithful negative；
2. M0R是否保持或改善stock；
3. M1是否公平复现MyoPS-Net；
4. M2是否真实运行官方I-MMSeg，或为何资产阻塞；
5. M3各heads/loss是否真正参与final labels；
6. Case3008/3009是否改善；
7. Case2019 remote FP是否改善；
8. Case2034 edema sensitivity/volume是否改善；
9. global scar/edema source；
10. 是否形成candidate。

然后列：

```text
controller_verification_decision
scientific_decision
interactive allocation ID
all queue job IDs and states
all interactive step IDs and states
M0R/M1/M2/M3 training adequacy
fold2/fold3 case counts
selected checkpoint hashes
scar/edema summary
sentinel case findings
validator/known-bad status
commit SHA
remote main SHA
notifier receipt
```

## Executor Worker Contract

每个Executor只执行其lane和write scope。不得自行改变模型、loss、split、budget、selection或调度。实现gap必须在同一goal修复；不能把`PREFLIGHT_NEEDS_IMPLEMENTATION`当作正常完成。

## Mapper Contract

Mapper只读检查：

```text
input -> modality path -> encoder/decoder -> pathology heads -> losses -> final logits -> official labels
```

必须验证M1核心模块、M2官方模块、M3四heads及M0R optimizer/scheduler真实性，并检查不存在旧失败机制的隐式shortcut。