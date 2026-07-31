---
task_key: 20260731_care_myowall_if_mechanism_pilot
task_kind: scientific_milestone
task_type: mechanism_feasibility
controller_mode: controller_supervised
milestone_number: null
milestone_id: null
status: AUTHORIZED
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260731_care_myowall_if_pilot_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
review_mode: none
reviewer: none
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: false
route_promotion_gate: false
experiment_adequacy_gate: matched_four_arm_8000_steps
route_negative_gate: false
scientific_completion_gate: mechanism_pilot_only
diagnostic_publication_gate: true
diagnostic_publication_scope: results/20260731_care_myowall_if_mechanism_pilot
blocked_after_diagnostic_publication: false
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
---

# CARE-MyoWall-IF 心肌壁坐标病理场交互式机制试验 Controller

## 开场判断

本轮批准的是一项可证伪的机制试验，不是完整候选模型长训练。Deep Research 提出的“心肌壁坐标病理场”具有足够的新信息路径：它把 scar 的多弧段、跨壁程度和 pure edema 的带状连续性写入输出空间，并把远端组织从病理搜索域中结构性排除；但外部证据只证明极坐标/隐式心脏坐标可行，并没有证明 CARE 上能大幅涨分。因此 Controller 必须先完成几何闭环和四臂 matched pilot，只有 scar 与 pure edema 同时通过最终标签门，才能返回 Planner 建议后续完整训练。

本任务不授权：

```text
完整 48k-step 训练
fold1 outer 访问
fold0 outer 二次使用
validation upload
Docker upload
hosted metric claim
ROI proposal/refiner
prototype/dictionary/router
diffusion/第二完整 backbone
```

## 一、唯一科学合同

完整执行：

```text
prompts/blueprints/CARE_MyoWall_IF_mechanism_pilot_20260731.md
prompts/tasks/20260731_care_myowall_if_pilot_executor_plan.yaml
```

二者是冻结合同。不得以“实现更方便”为由更改：

- 数据人口；
- fold；
- pilot split 算法；
- stock checkpoint；
- patch 语义；
- wall lattice；
- arm 定义；
- loss；
- 8000 steps；
- checkpoint cadence；
-评价门；
-停止门。

任何需要改变上述字段的情况，停止为 `NEEDS_GPT_PLANNER`，不得由 Controller 自行补设计。

## 二、仓库与启动

```text
repo: /users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
result_root: results/20260731_care_myowall_if_mechanism_pilot
runtime_root: results/20260731_care_myowall_if_mechanism_pilot/runtime
```

禁止写入：

```text
/overflow/htzhu/CARE
/users/a/e/aereinh/CARE_worktrees/route_A
/users/a/e/aereinh/CARE_worktrees/route_B
/users/a/e/aereinh/CARE_worktrees/route_C
```

启动命令：

```bash
cd /users/a/e/aereinh/CARE
git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -20
git diff --check
```

如果 main 落后，且工作树干净：

```bash
git pull --ff-only origin main
```

如果有用户未提交改动：

- 不 reset；
- 不 clean；
- 记录 changed files；
- 只有与本任务 write scope 冲突时才停止；
- 非冲突改动保持不动。

必须读取：

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

必须读取：

```text
results/20260730_care_failure_forensics_deep_research_packet/CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v4.pdf
results/20260730_care_failure_forensics_deep_research_packet/v4_atlas_pages_a3_landscape.pdf
results/20260730_care_failure_forensics_deep_research_packet/DEEP_RESEARCH_MODEL_DESIGN_INPUT_20260730_v4.md
results/20260729_care_prism_v2_backbone_repair_and_resume/**
```

## 三、Project 图像回执

GPT Planner 已在当前 Project 中视觉读取：

```text
SRR-v2
SRR-v2.5
SRR-v3
CARE-MMRD
CARE-SRR-Cascade
CARE-ARC
MoSAIC
```

冻结的历史经验仅作为边界：

- 保留完整成熟 decoder；
- scar/edema 分治；
- no-T2 edema hygiene；
- final-output authority；
- case-wise help/harm、HD95、remote FP；
- 禁止弱 anchor correction、未隔离 prototype、模块只存在不进入 final output。

本任务不得恢复 SRR dictionary、PRISM router、Cascade prototype 或 ARC direct decoder。

## 四、Controller 与角色

固定角色图：

```text
Controller/Coordinator
  -> Executor（唯一，负责代码、命令、interactive Slurm step）
  -> Mapper（只读，P2 draft 与 P4 final）
  -> deterministic validator/finalizer
  -> Controller same-scope repair
  -> terminal commit/push/email
```

Controller 必须检查：

- 每一波真实 git diff；
- model/config/split/checkpoint/hash；
- interactive job/step terminal accounting；
- 训练步数与 train-loop time；
- checkpoint save/reload；
- casewise metrics；
- validators 与 known-bad；
- CURRENT/wiki 最终状态；
- terminal push 与 email receipt。

Executor 不能宣布整个任务完成。

## 五、P0：指标依赖、数据与资产冻结

### 5.1 Metric truth dependency

先检查：

```text
results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json
```

若存在，必须验证 hash 和：

```text
metric_contract_status == PASS
canonical_t2_present_count == 80
```

若不存在，Controller 不能猜测指标。允许先完成 P1/P2 的实现和几何 zero-credit 工作；正式 P3 四臂训练保持阻塞。Controller 每 5 分钟检查一次，最多等待 6 小时。

6 小时后仍不存在：

- 不启动正式训练；
- 写 `metric_dependency_blocker.json`；
- 继续完成所有不依赖正式指标的实现、tests 和 geometry；
- 最终为 `OPERATIONALLY_BLOCKED_METRIC_TRUTH_DEPENDENCY`；
- 按终态规则 push blocker packet 并发邮件。

不得在本任务内部用 V4 PDF 文本替代 metric truth receipt。

### 5.2 Stock fold1 asset

重新定位并绑定：

```text
fold1 checkpoint_final.pth
nnUNetPlans.json
dataset.json
splits_MyoPS.json
```

记录：

```text
path
size
sha256
trainer
network class
patch size
channels
strides
kernel sizes
input order
```

预期 patch size `[20,256,256]`。如果运行时不同，以 plans 真值为准，并检查蓝图是否仍兼容；不能静默固定 `Z=112`。

### 5.3 Pilot split

严格执行蓝图中的 fold1-train 32-case deterministic inner algorithm。

输出：

```text
pilot_train_cases.txt
pilot_inner_cases.txt
pilot_split_receipt.json
pilot_subgroup_matrix.csv
```

验证：

```text
train/inner disjoint
train+inner == fold1 train
fold1 outer not read
inner total = 32
inner T2-present = 16
inner LGE-only = 8
inner LGE+C0 = 8
```

如果实际 fold1 train 不能满足模态配额，停止为 `NEEDS_GPT_PLANNER_SPLIT_CONTRACT`；不得自行降低样本数。

## 六、交互式 GPU allocation

本任务明确要求使用 interactive allocation，不使用 `sbatch` 训练科学 arm。

### 6.1 复用优先

检查：

```bash
squeue -u "$USER" -o '%i|%j|%P|%T|%M|%L|%R|%b'
sinfo -o '%P|%a|%l|%D|%t|%G'
```

优先复用满足以下条件的 RUNNING interactive GPU allocation：

```text
GPU: H100 or A100
remaining time >= 6 hours
partition priority: htzhulab > a100-gpu > volta-gpu
not owned by another active CARE controller
```

写：

```text
interactive_allocation_receipt.json
```

### 6.2 新建 interactive allocation

若无可复用 allocation，在 namespace-local tmux 中启动：

```bash
tmux new-session -d -s care_myowall_if_alloc \
  "cd /users/a/e/aereinh/CARE && \
   salloc -p htzhulab --gres=gpu:1 --cpus-per-task=16 --mem=128G \
          --time=12:00:00 --job-name=CARE_MyoWall_IF_Pilot \
          bash -lc 'echo ALLOCATION_READY; sleep infinity'"
```

等待 `squeue` 显示 RUNNING 并记录 job id。

若 htzhulab 30 分钟仍 PENDING，取消该 allocation，按同样参数转 `a100-gpu`。

`volta-gpu` 只允许 geometry cache、inference 和 tests；不得在 V100 上偷改 batch、channels、lattice 或 loss。若只有 V100 可用，继续等待 H100/A100，最多 24 小时；超过后按 Slurm skill 判定 blocker。

### 6.3 运行 step

所有 GPU 命令使用：

```bash
srun --jobid="$INTERACTIVE_JOB_ID" --overlap \
  --ntasks=1 --cpus-per-task=16 --gres=gpu:1 \
  bash -lc '<exact command>'
```

正式 Python：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

禁止裸 `python`。

每次 step 启动打印：

```text
python executable/version
torch/CUDA
CUDA_VISIBLE_DEVICES
GPU name/memory
Slurm job/step/node/partition
repo HEAD/status
task prompt SHA
blueprint SHA
config/split/checkpoint hashes
command
output directory
```

每次只允许一个 active GPU step。

### 6.4 Allocation 时限与 exact resume

若 12 小时不足：

- 保存 arm checkpoint 与 optimizer/scheduler/scaler/RNG/batch-manifest cursor；
- 当前 interactive allocation 正常结束；
- 新建同规格 interactive allocation；
- exact resume；
- 不减少 8000 steps；
- 所有 allocation/job/step 均进入 accounting。

## 七、P1：Stock parity 与 geometry closure

### 7.1 Stock adapter

实现：

```text
src/care_myocardium/models/myowall_if/stock_adapter.py
```

必须完整加载 stock fold1 encoder、decoder、seg heads。

必须通过：

```text
parameter byte coverage >=0.99
missing/unexpected keys = 0
FP32 stock logits max_abs_error <=1e-6
argmax changed voxels = 0
save/reload max_abs_error <=1e-6
```

高分辨率 feature hook 固定为：

```text
network.decoder.stages[-1]
```

若输出不是 32 channels 或空间与 stock logits 不一致，fail closed。

### 7.2 Geometry cache

实现：

```text
src/care_myocardium/models/myowall_if/geometry.py
scripts/training/myowall_if/build_geometry_cache.py
```

对 pilot train/inner 全部病例运行 stock sliding-window inference，构建蓝图规定的 centroid/endo/epi/rho 网格和 rank features。

缓存只保存：

```text
centroids
endo/epi radii
valid masks
rank normalization statistics
geometry hashes
```

不得提交大 feature tensor、raw logits 或 NIfTI 到 Git。

### 7.3 Geometry gate

生成：

```text
geometry_casewise_metrics.csv
geometry_gate_report.json
geometry_visual_examples/**
```

必须实际渲染至少 20 例：

- original wall/stock wall；
- polar/wall lattice；
- inverse roundtrip；
- endo/epi curves；
- invalid angles。

Mapper/Codex 必须视觉检查至少 10 例 complete tri-modal、5 例 LGE-only、5 例 LGE+C0。

只有蓝图 geometry gate 全部通过，才进入 P2。

失败时不实现 Cartesian fallback 掩盖；停止为 `STOP_GEOMETRY_NOT_RELIABLE`。

## 八、P2：实现与 zero-credit 验收

实现精确类：

```text
StockNNUNetFeatureAdapter
FrozenStockGeometryCacheBuilder
WallCoordinateTransform
WallInverseTransform
RobustWallRankFeatures
CartesianMatchedPathologyHead
ScarWallFieldHead
EdemaWallFieldHead
MyoWallPilotModel
MyoWallPilotLoss
MyoWallPilotEvaluator
```

固定文件范围：

```text
src/care_myocardium/models/myowall_if/**
scripts/training/myowall_if/**
scripts/evaluation/myowall_if/**
jobs/myowall_if/**
tests/myowall_if/**
configs/myowall_if/**
results/20260731_care_myowall_if_mechanism_pilot/**
```

禁止修改：

```text
stock nnU-Net source
PRISM production source
MoSAIC source
production evaluator
fold0/fold1 outer locks
```

### 8.1 Configs

创建固定 config：

```text
configs/myowall_if/pilot_common.yaml
configs/myowall_if/arm_C0.yaml
configs/myowall_if/arm_W1.yaml
configs/myowall_if/arm_W2.yaml
configs/myowall_if/arm_W3.yaml
```

所有字段必须显式；不得引用默认值填设计空白。

### 8.2 Matched arm parity

验证：

```text
same train/inner cases
same batch_descriptor_manifest
same augmentation seeds
same steps
same optimizer/scheduler
same evaluation cadence
new parameter counts within ±5%
```

### 8.3 One-batch overfit 与 zero-credit smoke

对每 arm：

```text
one-batch overfit 200 steps
real-case smoke 100 steps
save/reload
on/off intervention
no-T2 exact-zero test
```

均为 zero formal credit。

必须证明：

- wall transform 关闭后回到 C0 tensor contract；
- theta 打乱显著破坏 wall continuity；
- T2 rank 打乱只伤害 edema 相关输出，不系统性抬高 scar；
- wall 外高亮注入不产生病理 mask；
- final logits 只来自对应 arm pathology head；
- stock pathology logits 权重为零且不参与 forward composition。

### 8.4 Pretraining validator

实现：

```text
scripts/validation/validate_myowall_if_pilot.py
tests/myowall_if/test_known_bad.py
```

覆盖蓝图 20 项 known-bad，并非只检查文件存在。

P2 validator PASS 后才允许 P3。

## 九、P3：四臂正式训练

训练顺序固定：

```text
C0 -> W1 -> W2 -> W3
```

不得并行训练四 arm，以确保同一 GPU、相同环境和可追踪资源。

在训练前生成：

```text
batch_descriptor_manifest.jsonl
```

包含完整 8000-step case/crop/augmentation sequence。所有 arm 从 step0 重放同一 manifest。

每 arm：

```text
8000 optimizer steps
checkpoint every 1000
fixed inner evaluation every 1000
physical batch=2
accumulation=2
AdamW lr=3e-4
weight_decay=1e-4
warmup=500
cosine to 1e-6
grad clip=12
bf16 on H100/A100
```

每 arm 必须记录：

```text
optimizer steps
train-loop seconds
loss curves by component
actual LR curve
GPU memory
step time
validation events
checkpoint hashes
save/reload receipt
```

失败 startup、OOM、preemption、allocation timeout 为 zero credit。普通同范围 bug 由 Controller 修复并 exact resume。

不能为了 OOM：

- 缩小 lattice；
- 减少 channels；
- 缩短 steps；
- 减少病例；
- 改 loss；
- 改 batch semantics。

允许的 OOM 修复仅限：

```text
activation checkpointing
non-blocking transfer
cache staging
AMP implementation bug
memory leak repair
```

若仍无法在 H100/A100 执行，停止为 `OPERATIONALLY_BLOCKED_MEMORY`。

## 十、P4：统一评价与科学裁决

每个 arm 的 8 个 checkpoint 全部重载评价，禁止只用训练时 summary。

评价人口：

```text
pilot_inner 32
pure edema: 其中16个T2-present only
no-T2 safety: 其余16个
```

指标按蓝图全部报告。

生成：

```text
casewise_metrics.csv
checkpoint_metrics.csv
arm_summary.csv
component_metrics.csv
help_harm.csv
complexity_report.csv
causal_ablation_report.md
visual_comparison_atlas.pdf
```

视觉 atlas 至少包括：

- 8 个小/multi-component scar；
- 8 个 T2-present edema；
- 4 个 remote/blood-pool FP；
- 4 个 no-T2；
- C0/W1/W2/W3/GT 同切片并列。

### 10.1 决策

只允许：

```text
PILOT_PASS_DUAL_PATHOLOGY
PARTIAL_SIGNAL_NO_PROMOTION
STOP_GEOMETRY_NOT_RELIABLE
STOP_WALL_FIELD_NO_GAIN
OPERATIONALLY_BLOCKED
```

必须严格执行蓝图阈值。

不得以：

```text
loss下降
wall-space auxiliary变好
gradient非零
remote FP单项下降
scar单项提升
```

替代双病种 final-label gate。

## 十一、Mapper 与 wiki

P2 后 Mapper 写：

```text
mapper_report_draft.md
architecture_trace_draft.csv
```

P4 后写：

```text
mapper_report_final.md
architecture_trace_final.csv
architecture_delta_final.md
```

Mapper 必须追踪：

```text
input -> stock full encoder/decoder -> F0
F0/intensity/anatomy -> C0 or wall transform
wall scar/edema heads -> inverse transform
final logits -> official labels
loss -> owning tensor -> owning parameters
```

最终只更新 wiki/CURRENT 为**机制试验终态**，不得写 route promotion、validation readiness 或新主线成功。

如果 pilot fail，wiki 必须诚实记录失败原因。

## 十二、严格验证

最终 validator 必须检查：

- task/executor plan hash；
- stock asset/hash/parity；
- split/hash/outer lock；
- metric truth dependency；
- geometry gate；
- exact class/wiring；
- arm matched contract；
- 8000 steps/arm；
- checkpoint reload；
- terminal interactive accounting；
- casewise scar/pure edema/no-T2；
- help/harm/HD95/remote FP；
- complexity budget；
- visual atlas；
- allowed decision token；
- no validation/Docker/hosted claim；
- no large binary committed。

validator error 必须非零退出。

## 十三、Interactive continuity 与 finalizer

使用 namespace tmux：

```text
care_myowall_if_controller
care_myowall_if_alloc
care_myowall_if_finalizer
```

finalizer 每 5 分钟检查：

```text
squeue/sacct
interactive job/steps
arm checkpoint cursor
required outputs
validator state
```

`submitted/pending/running/awaiting sacct` 均不是完成。

Controller 不能在 interactive allocation 仍运行、arm 未达 8000、aggregation 未完成或 validator 未通过时结束。

## 十四、Commit、push 与邮件

Runtime 过程中禁止 push。

终态满足以下之一后才允许提交：

```text
VERIFIED_COMPLETE with one allowed scientific decision
or true OPERATIONALLY_BLOCKED with complete blocker evidence
```

只提交轻量内容：

```text
source/config/scripts/tests
small CSV/JSON/Markdown
compressed visual atlas/PDF if within repo boundary
CURRENT/wiki terminal update
notification_brief.json
```

禁止提交：

```text
checkpoint
raw logits/probabilities
NIfTI
geometry dense cache
large logs
secret
upload package
```

commit message：

```text
experiment: complete CARE MyoWall-IF mechanism pilot
```

提交后：

```bash
git fetch origin main
```

如果 remote main 未前移，直接：

```bash
git push origin main
```

如果 remote main 前移：

- 只允许在 task files 无冲突时 `git rebase origin/main`；
- 重跑 validators；
- 再 push；
- 有冲突则停止 `HUMAN_INTERVENTION_REQUIRED`，不得 force push。

push 后验证 remote SHA。

### 14.1 完成邮件

终态、commit、push 和 remote SHA 确认后写：

```text
results/20260731_care_myowall_if_mechanism_pilot/notification_brief.json
```

字段：

```text
task_name
final_status
commit_status
push_status
key_conclusion
blocked_or_failure_reason
slurm_terminal_status
evidence_paths
next_step
```

然后运行：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

不得手写 SMTP，不得在 pending/running/未 push 时发完成邮件。

邮件必须用中文简要说明：

- 双病种 pilot 是否通过；
- 四臂最重要结果；
- interactive job terminal；
- commit/push；
- 下一步是否允许。

## 十五、Required outputs

至少：

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
metric_dependency_receipt.json
asset_freeze_receipt.json
pilot_split_receipt.json
pilot_train_cases.txt
pilot_inner_cases.txt
pilot_subgroup_matrix.csv
stock_parity_report.json
geometry_cache_manifest.csv
geometry_casewise_metrics.csv
geometry_gate_report.json
implementation_snapshot.md
tensor_contract_report.json
one_batch_overfit_report.json
zero_credit_smoke_report.json
batch_descriptor_manifest.jsonl
pretraining_strict_validator_report.json
arm_C0_training_summary.json
arm_W1_training_summary.json
arm_W2_training_summary.json
arm_W3_training_summary.json
checkpoint_manifest.csv
interactive_allocation_receipt.json
interactive_job_accounting.csv
casewise_metrics.csv
checkpoint_metrics.csv
arm_summary.csv
component_metrics.csv
help_harm.csv
complexity_report.csv
causal_ablation_report.md
visual_comparison_atlas.pdf
known_bad_report.json
strict_validator_report.json
mapper_report_draft.md
mapper_report_final.md
architecture_delta_final.md
finalizer_state.json
controller_report.md
completion_check.md
MANIFEST.md
notification_brief.json
push_receipt.json
email_send_receipt.json
```

## 十六、Controller report

开头必须先用自然中文回答：

1. 心肌壁几何是否可靠？
2. W1 相比 matched Cartesian C0 是否真正改善 final labels？
3. scar 小病灶、多组件和 remote FP 是否改善？
4. pure edema 的 Dice/HD95/召回是否改善？
5. W2/W3 说明 component/guard loss和rank信号是否有独立贡献？
6. 结果是否只是 anatomy hard mask？
7. 是否值得进入完整训练？
8. 什么仍然未授权？

机器字段：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
metric_dependency_status:
stock_parity_gate:
geometry_gate:
C0_status:
W1_status:
W2_status:
W3_status:
scar_mechanism_signal:
pure_edema_mechanism_signal:
scientific_decision:
long_training_authorized: false
outer_access_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
all_jobs_terminal:
aggregation_complete:
validators_passed:
git_commit_decision:
git_push_decision:
remote_sha_verified:
email_decision:
next_required_action: RETURN_TO_PLANNER | HUMAN_INTERVENTION_REQUIRED
```

## Controller hard-gate wording

Before executing the scientific task, enforce the hard-gate policy: exact task graph, frozen architecture and split contract, controller-as-coordinator diff inspection and same-scope repair loop, strict semantic validators and known-bad regressions, full stock checkpoint/decoder parity, metric-truth dependency, geometry round-trip gate, matched four-arm 8000-step training, interactive Slurm terminal accounting, post-completion aggregation, mapper/wiki/fingerprint gates, terminal lightweight commit/push, and notifier email only after remote SHA verification. If any gate fails, continue same-scope repair when authorized or stop with NEEDS_REPAIR/OPERATIONALLY_BLOCKED; do not claim VERIFIED_COMPLETE.

## Executor worker contract

The Executor performs authorized implementation, interactive Slurm commands, training, evaluation and evidence writing but cannot declare the whole task complete. It must not fill architecture blanks, change frozen formulas, reduce budgets, access outer, add rescue modules, or push during runtime. Return every wave to the Controller for diff, evidence, validator, runtime and contract verification.

## Mapper contract

The Mapper is read-only except for task-local mapper reports and authorized terminal wiki updates. It must prove that wall transform, pathology heads and inverse transform truly own final scar/pure-edema logits; verify no stock pathology monopoly, no shared disease head, no no-T2 leakage, and no module-present-only evidence; and compare code/runtime to the frozen blueprint before finalization.
