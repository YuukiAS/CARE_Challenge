---
task_key: 20260803_care_ase_r2_full_fidelity_execution
task_kind: scientific_milestone
task_type: full_fidelity_implementation_repair_training_and_fresh_replication
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
allow_diagnostic_push: false
new_training_authorized: true
required_training_folds: [1, 4]
artificial_wallclock_deadline: none
validation_upload_authorized: false
docker_upload_authorized: false
challenge_upload_authorized: false
hosted_metric_claim_authorized: false
contract_path: prompts/blueprints/CARE_ASE_R2_full_fidelity_execution_contract_20260803.yaml
---

# CARE-ASE R2 完整忠实实现、训练与新折复现实验正式 Controller

你是本次单一 Goal 的正式 Codex Controller。上一轮 CARE-ASE 虽完成训练和评价，但实际代码把阶段预算、学习率调度、部分模态训练、语义辅助损失、困难样本采样、面积参照、精确恢复和验证器全部做了不同程度的降级。本 Goal 的首要职责是先把代码完整修到合同要求，再训练；不得再出现“validator PASS，但实际训练入口仍是简化版”的情况。

科学目标是在新折同病例比较中，让 CARE-ASE 的 scar 与 pure-edema 同时优于 nnU-Net OOF 和 MoSAIC clean OOF。你必须以此为成功门，但不得承诺、伪造或通过改口径获得分数。你能够保证的是实现忠实、训练充分、评价公平和结果真实。

本 Goal 无人为十二小时终止线，不允许 one-fold fallback。fold1 与 fold4 都必须完成固定 14,000 optimizer steps，除非满足合同规定的真正操作阻塞边界。不得为了赶时间缩短训练、删损失、删采样、减少分支或跳过 Gate。

## 1. 启动与唯一真值

工作目录：

```text
/users/a/e/aereinh/CARE
```

先执行并记录：

```bash
git fetch origin main --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor 497e91489aeb608a373ea23d2b63d02dea6513d0 origin/main
git log --oneline -20 origin/main
```

未确认 `497e91489aeb608a373ea23d2b63d02dea6513d0` 是 `origin/main` 祖先时不得开始。

完整读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
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

prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment02_controller_only_interactive_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment03_final_audit_20260801.yaml
prompts/blueprints/CARE_ASE_R2_full_fidelity_execution_contract_20260803.yaml
prompts/tasks/20260803_care_ase_r1_plan_audit_and_supersession.md

results/20260801_care_ase_final_model/controller_report.md
results/20260801_care_ase_final_model/w45_implementation_snapshot/**
results/20260801_care_ase_final_model/outer_eval/fold_2/casewise_metrics.csv
results/20260801_care_ase_final_model/outer_eval/fold_3/casewise_metrics.csv
results/20260730_care_failure_forensics_deep_research_packet/standardized_casewise_metrics.csv
results/20260731_care_metric_truth_reconciliation/metric_semantics_contract.json
results/20260801_care_nnunet_mosaic_complementarity_closure/**
```

后者覆盖前者。R2 合同是本次执行最高优先级。旧 R1 十二小时计划和旧 metric-truth Goal 只作 provenance，不得并行启动。

`CURRENT.md` 当前可能描述 Docker 线。不要覆盖、删除或混入 Docker 工作树修改；只提交本 Goal 的源码、测试、配置和轻量结果。

## 2. 固定 Agent Flow 与代码写入顺序

唯一流程：

```text
one Controller
-> one Executor serial implementation
-> G1 static gate
-> G2 real GPU gate
-> G2.5 immutable training-source commit/push gate
-> only then Slurm training may run in parallel
-> Mapper final
-> deterministic Validators
-> Controller real-diff/runtime/evidence verification
-> same-goal repair while authorized
-> main commit/push/SHA equality
-> notification
```

规则：

- 只有一个 Executor，所有科学代码串行编写、串行检查。
- `parallel_execution_allowed: false` 约束 Agent，不禁止 G2.5 后 fold1/fold4 的隔离 Slurm 并行。
- 在 G2.5 之前，禁止任何正式训练 `srun`、`sbatch` 或训练 checkpoint 生成。
- Executor 不能宣布 Goal 完成。
- Controller 必须检查真实 diff、真实入口、真实运行参数和真实 receipt 内容，不能只相信 PASS token。
- Controller 必须由 `care_ase_r2_full_fidelity` namespace-local tmux watcher 或等价 durable finalizer 持续负责到终态。

## 3. W0 / G0：来源、split、资源与外层零访问冻结

结果根目录：

```text
results/20260803_care_ase_r2_full_fidelity_execution
```

必须生成：

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
source_hash_manifest.json
effective_contract.json
split_and_outer_access_receipt.json
allocation_61794608_receipt.json
storage_quota_receipt.json
```

必须证明：

```text
fold1 actual-train / inner / outer 两两零交集
fold4 actual-train / inner / outer 两两零交集
fold1 outer 与 fold4 outer 不重复
fold1/fold4 outer 尚未被本 Goal 读取
stock checkpoint / plans / preprocessing / OOF baseline 来源可读且有 SHA256
effective_contract 已把 base + amendment01/02/03 + R2 合并成机器可解析真值
```

### 3.1 主 interactive allocation

用户指定主资源：

```text
job_id: 61794608
partition: htzhulab
user: aereinh
```

必须实时核验：

```bash
squeue -u "$USER" -p htzhulab -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
squeue -j 61794608 -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
scontrol show job 61794608
srun --jobid=61794608 --overlap \
  /users/a/e/aereinh/CARE/envs/env_CARE/bin/python \
  -c 'import torch,sys; print(sys.executable); print(torch.__version__); print(torch.cuda.is_available(), torch.cuda.get_device_name(0))'
```

不得假定旧 job `61220581` 仍有效。若 `61794608` 已失效，只允许申请或提交 `htzhulab` 替代资源；禁止自动转到 a100、volta 或其他 partition。

W0 未通过不得进入 W1；可修复路径、权限、磁盘和资源识别问题必须同 Goal 修复。

## 4. W1 / G1：完整行为实现门

必须修改真实运行代码，不得只改文档、receipt 或 validator。允许保留紧凑文件布局，但所有行为必须符合 R2 effective contract。

### 4.1 必须实现的模型和监督

必须同时存在并进入真实前向/总损失：

```text
完整 stock encoder + bottleneck + low/mid decoder
原始 stock anatomy highest-two-stage path
scar highest-two-stage exact clone
edema highest-two-stage exact clone
anatomy4 / wall / signed endo+epi distance / wall depth context
scar full+half dense supervision
scar quarter+half occupancy proposal
scar quarter+half component center
scar slice presence + area extent
scar four-class context
edema full+half dense supervision
injury labels4|5 support
signed pure-edema boundary
edema slice presence + area extent
edema four-class context with scar ignored
relation loss
```

每项 loss 必须使用 R2 合同的公式、权重和人群。no-T2 中所有 edema-exclusive loss、bias 和参数梯度必须精确为零；class4 必须从最终竞争计算图排除，不得映射成 background 负类。

### 4.2 必须实现的 sampler

Stage A/B 必须严格使用合同中的 20-step case-group cycle：

```text
complete 10
LGE-only 5
LGE+C0 5
```

完整病例必须 CenterB/CenterC 交替有放回，scar/edema 焦点交替；部分模态只允许 scar 焦点。Stage C 只允许 actual-train complete，CenterB/CenterC 交替。

scar 和 edema 的 20-event focus cycle、fallback 层级、OOF FN/FP 定义和 hard-negative manifest 消费必须逐项实现。生成 manifest 但 sampler 不读取属于硬失败。

### 4.3 必须实现的 optimizer/scheduler

只创建一次 AdamW；阶段切换不得重建 optimizer。稳定参数组必须互斥且覆盖全部参数。冻结参数 `requires_grad=false` 且 current LR 为 0。

阶段固定：

```text
A: global 0-2000
B: global 2000-10000
C: global 10000-14000
```

每个参数组的 base LR、min LR、warmup 和 power=0.9 poly 公式必须逐字执行 R2 合同。禁止 `scheduler_state=none`、固定 LR 或粗略近似。

### 4.4 必须实现的 checkpoint/resume

每 1000 步保存一次，只在完整 optimizer step 后保存。必须执行：

```text
tmp write
file fsync
parent directory fsync
atomic rename
SHA256
full reload
```

checkpoint 字段必须完整；缺任何一个字段都必须被 validator 拒绝。resume 必须通过行为等价测试，不只是 state dict 能加载。

### 4.5 G1 输出与 PASS

必须生成：

```text
implementation_gap_closure.json
parameter_group_coverage.json
semantic_loss_coverage.json
sampler_static_contract.json
scheduler_static_contract.json
checkpoint_schema_contract.json
known_bad_validator_report.json
```

G1 PASS 要求：

```text
remaining_gap_count == 0
所有旧降级配置 known-bad 均 FAIL CLOSED
真实训练入口引用的是新实现而不是旧 wrapper
AST/source-path/runtime-entrypoint 三重绑定一致
```

G1 失败必须退回同一 Executor 修复；不得提交训练。

## 5. W2 / G2：真实 GPU 忠实性门

只允许 fold1/fold4 actual-train 病例。禁止读取新 outer。

fixture 必须由合同规定的确定性算法从 actual-train 选择并写入 `preflight_case_manifest.json`，至少覆盖：

```text
complete CenterB scar+edema positive
complete CenterC scar+edema positive
LGE-only scar positive
LGE+C0 scar positive
small-scar actual-train case
```

必须在 job `61794608` 上或经验证的 htzhulab 替代资源上运行并证明：

1. stock 参数覆盖率、最高两级 clone、step0 anatomy/scar/edema final-logit parity 全部通过；
2. normal forward 不读取 stock class4/class5 logits；
3. 每项语义 loss 在有效 fixture 有有限值、非零梯度；在无效人群精确为零；
4. 400 optimizer-step descriptor dry-run 精确符合 case group、中心、病种焦点与 focus category cycle；
5. Stage A/B/C 边界步的 trainability、base LR、current LR、warmup 和 poly progress 与公式逐值一致；
6. fold-specific scar/edema area reference 与独立重算完全一致；
7. no-T2 edema-exclusive gradient max abs == 0.0；
8. 每个组件 module-off 至少记录 final-logit delta；若在声明测试病例上 label delta 为 0，必须扩大到所有预声明实际训练 fixture，不得用 logit-only 伪装机制成功；
9. one-batch overfit 能降低 final、scar、edema 和辅助 loss；
10. 全体积 sliding-window smoke 通过；
11. atomic save/reload、SHA、完整字段通过；
12. uninterrupted two-step 与 save/reload two-step 在 loss、logits、参数、scheduler 和 next-batch hash 上一致；
13. 旧 `2000/4000/8000`、scheduler none、complete-only Stage A/B、缺任一 loss、硬编码 area reference、manifest 未消费、缺 checkpoint 字段均被拒绝。

必须生成：

```text
preflight_case_manifest.json
real_gpu_preflight_receipt.json
sampler_400_step_receipt.json
scheduler_numeric_receipt.json
loss_gradient_receipt.json
area_reference_receipt.json
exact_resume_receipt.json
```

G2 未完全通过不得进入 G2.5。

## 6. W2.5 / G2.5：训练前不可变源码 Gate

这是正式训练许可门，不能省略。

固定顺序：

```text
git diff --check
-> 完整 tests
-> strict effective-contract validator
-> 检查真实 training entrypoint 和 wrapper
-> 只提交本 Goal 的源码、配置、测试和轻量 receipts
-> push origin/main
-> git fetch origin main
-> verify local HEAD == origin/main
-> 写 training_source_commit_receipt.json
```

`training_source_commit_receipt.json` 必须记录：

```text
training_source_commit_sha
effective_contract_sha256
model/trainer/loss/sampler/scheduler/evaluator/validator SHA256
split/plans/stock checkpoint SHA256
G1/G2 validator SHA256
```

在远端 SHA 相等前禁止启动正式训练。G2.5 后任何会改变模型、loss、sampler、scheduler、checkpoint 或 decode 的代码修改，必须使已受影响的训练 credit 归零，并返回 G1/G2/G2.5。

## 7. W3：完整两折训练与逐 chunk Gate

必须完成：

```text
fold1: 14000 optimizer steps
fold4: 14000 optimizer steps
```

不允许 one-fold fallback，不允许 early stop，不允许根据 inner 或早期困难病例跳过阶段。

### 7.1 fold1 主 interactive 路径

fold1 主要使用：

```bash
srun --jobid=61794608 --overlap <exact frozen training command>
```

按 7 个连续 2000-step chunk 执行。每个 chunk 前加载并验证上一边界状态；第一个 chunk 从 step0 开始。

### 7.2 fold4 可并行路径

只有 G2.5 完成、training source 已 push 后，才允许向 `htzhulab` 额外提交 fold4 的 7-chunk `afterok` chain。每个 job 使用：

```text
partition=htzhulab
qos=gpu_access
gres=gpu:1
cpus-per-task=8
mem=64G
walltime<=8h per 2000-step chunk
exact frozen Python and source commit
```

禁止在代码尚未写完、G1/G2 未通过时预提交占位 job。

### 7.3 并行竞争与接管

fold1/fold4 使用独立 runtime、log、lock 和 checkpoint 目录。每 fold/chunk 在读第一个 batch 前获取 atomic mkdir lock。

若 fold1 完成时 fold4 当前未完成 chunk 仍 pending：

```text
取消 pending fold4 chain
轮询确认取消状态
在 61794608 上从最后完整 chunk checkpoint 串行继续 fold4
```

若取消过程中 fold4 chunk 已启动并持锁，让它完成；interactive loser 在读取数据前退出并记 zero credit。

若 `61794608` 失效，Controller 必须在 htzhulab 申请或提交替代资源并继续，不得转其他 partition。

### 7.4 每个 2000-step chunk 的硬 Gate

下一 chunk 只能在以下全部通过后启动：

```text
Slurm step terminal success
到达准确 global step
边界 checkpoint 完整 reload
training_source_commit_sha 不变
effective_contract_hash 不变
stage / scheduler / current LR 正确
sampler cursors 和 next-batch hash 正确
checkpoint SHA 已记录
不存在 optimizer-step 重叠、缺口或重复
```

startup failure、preemption、race loser、partial checkpoint 均为 zero credit。submitted、pending、running、awaiting sacct 均不是终态。

## 8. W4：两折固定终点冻结 Gate

W4 只有在以下全部满足时 PASS：

```text
fold1 global_step == 14000
fold4 global_step == 14000
两个 checkpoint_step14000.pt 完整 reload PASS
model/optimizer/scheduler/RNG/worker seed/sampler/cursors/hashes/ramp 字段完整
training source commit 与 G2.5 完全一致
fold1/fold4 outer access count before freeze == 0
```

必须生成：

```text
checkpoint_freeze_receipt.json
full_reload_parity_receipt.json
outer_access_audit_receipt.json
```

检查点损坏或字段缺失必须从最后完整 chunk 修复，不得进入 outer。

## 9. W4.5：outer 前不可变快照 Gate

轻量快照必须包括：

```text
training source commit
effective contract
G1/G2/G2.5 receipts
14 个 fold/chunk continuity receipts
Slurm accounting
fold1/fold4 checkpoint SHA256
outer zero-access proof
```

固定顺序：

```text
build snapshot
-> snapshot validator
-> lightweight main commit
-> push origin/main
-> verify local main == origin/main
-> 立即进入 W5
```

不等待 GPT、Planner 或用户确认。不得提交 checkpoint、NIfTI、raw data 或大日志。

## 10. W5：新折 outer once 与三方公平比较

在任何 CARE-ASE outer inference 前先冻结：

```text
fold1/fold4 outer case lists
scar denominator
T2-present pure-edema denominator
canonical nnunet_oof rows
canonical mosaic_clean_oof rows
predeclared intervention/atlas cases
```

对每个新折只运行一次 CARE-ASE outer，固定 `checkpoint_step14000.pt` 和固定 argmax：

```text
T2 present: classes 0,1,2,3,4,5
no T2: classes 0,1,2,3,5
```

正式比较：

```text
CARE-ASE R2
nnunet_oof
mosaic_clean_oof
```

必须按同一 `case_id`、同一 pathology、同一 population 严格连接：

- scar：fold1+fold4 全部唯一 outer；
- pure-edema：仅 T2-present outer；
- no-T2 edema 行完全排除；
- 报告 mean、median、GT-positive、empty prediction、help/harm/neutral、CenterB、CenterC、完整模态、no-T2 scar、小 scar；
- HD95、exact HD、remote FP 和 component count 只有三个模型都能用相同 prediction-level evaluator 重算时才能比较，否则明确写 `NOT_BOUND_DO_NOT_INFER`；
- 无穷 HD 病例必须计数，不能从均值中静默删除；
- 结果不得改变模型、decode 或 checkpoint。

同时修复旧 fold2/fold3 edema 口径，但只能作为 secondary posthoc evidence。

科学成功要求：

```text
pooled fresh scar Dice >= max(nnU-Net, MoSAIC) + 0.001
pooled fresh pure-edema Dice >= max(nnU-Net, MoSAIC) + 0.001
每个病种相对 nnU-Net harm fraction <= 0.50
每个新折每个病种不低于 nnU-Net 超过 0.01
无灾难性空预测增加
CenterC edema sensitivity 不低于 nnU-Net 超过 0.01
相同 metric 可绑定时 HD95/remote FP 不得实质恶化
```

达不到必须如实给 partial/no-gain，不得通过筛病例、改 denominator 或改 metric 获得成功。

## 11. W6：Mapper、严格验收、提交、推送和通知

固定顺序：

```text
aggregation
-> Mapper final 与 wiki/fingerprint 修复
-> strict validators + known-bad regressions
-> Controller 检查真实 diff、training source、14 个 chunk、case set 和指标
-> git diff --check
-> lightweight main commit
-> push origin/main
-> git fetch origin main
-> verify local main == origin/main
-> write notification_brief.json
-> ./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

最终第一行只能是：

```text
CARE_ASE_R2_BEATS_NNUNET_AND_MOSAIC_ON_FRESH_FOLDS
CARE_ASE_R2_PARTIAL_GAIN
CARE_ASE_R2_NO_GAIN
CARE_ASE_R2_OPERATIONALLY_BLOCKED
```

随后用自然中文说明：

1. 上一轮哪些降级实现被关闭；
2. G1/G2/G2.5 是否真正通过；
3. fold1/fold4 各自完成多少步和哪些 Slurm job；
4. CARE-ASE、nnU-Net、MoSAIC 的同病例 scar/pure-edema 结果；
5. help/harm、CenterB/CenterC、空预测、HD 和远端假阳性；
6. 是否达到同时超过两者的目标；
7. commit SHA、origin/main SHA 和通知回执；
8. validation、Docker、challenge upload、hosted claim、外部数据/权重仍未授权。

## 12. 阻塞边界

低分、loss 波动、视觉不佳、排队、单次启动失败、单个 preemption、一次 push 失败都不是阻塞。

只有在同范围修复与重试耗尽后，以下情况允许 `OPERATIONALLY_BLOCKED`：

```text
数据/split/stock checkpoint 经路径权限修复后仍不可读
仓库或本地存储不可恢复损坏
htzhulab 连续 24 小时无可用 61794608/替代 lane 且所有提交均未启动
同一实现失败类别三次真实修复仍无法通过 G1/G2，并有 attempt diff 与最小复现
安全清理和本地替代路径后仍不可恢复的 quota/filesystem failure
```

无论完成或阻塞，都必须形成轻量 packet、commit、push、SHA 核验和终态通知。
