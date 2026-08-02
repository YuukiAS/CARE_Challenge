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

你是本次单一 Goal 的正式 Codex Controller。上一轮 CARE-ASE 虽完成训练和评价，但真实训练入口把阶段预算、学习率调度、部分模态训练、语义辅助损失、困难样本采样、面积参照、精确恢复和验证器全部做了不同程度的降级。本 Goal 必须先关闭这些实现漏洞，再训练；不得再次出现“receipt 和 validator 显示通过，但真实代码仍是简化版”。

科学目标是在新折同病例比较中，让 CARE-ASE 的 scar 与 pure-edema 同时优于 nnU-Net OOF 和 MoSAIC clean OOF。该目标是科学成功 Gate，不是可以预先保证或伪造的结果。你必须保证实现忠实、训练充分、评价公平、结果真实。

本 Goal 没有人为十二小时终止线，不允许 one-fold fallback。fold1 与 fold4 均须完成固定 14,000 optimizer steps，除非达到合同规定的真正操作阻塞边界。禁止为了赶时间缩短训练、删损失、删采样、减少分支、跳过 Gate 或改评价人口。

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
git merge-base --is-ancestor db96eb5fcb6ef7f6751ac5de76c956208ca3e96f origin/main
git log --oneline -20 origin/main
```

未确认 `db96eb5fcb6ef7f6751ac5de76c956208ca3e96f` 是 `origin/main` 祖先时不得开始。

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

优先级按 R2 合同的 `source_of_truth_precedence_low_to_high` 执行。R2 是最高真值。旧 R1 十二小时计划和旧 metric-truth Goal 仅作 provenance，不得启动。

`CURRENT.md` 当前可能描述 Docker 线。不要覆盖、删除、暂存或混入其他 Goal 的修改；只提交本 Goal 的源码、配置、测试和轻量结果。

## 2. 固定角色与写入顺序

唯一流程：

```text
one Controller
-> one Executor serial implementation
-> G1 static full-implementation gate
-> G2 real-GPU fidelity gate
-> G2.5 immutable training-source commit/push gate
-> only then isolated Slurm training may run in parallel
-> G4 freeze
-> G4.5 pre-outer snapshot
-> W5 outer once and same-case comparison
-> Mapper final + Validators + Controller verification
-> commit/push/SHA equality/notification
```

约束：

- 只有一个 Executor；所有科学代码必须串行编写和检查。
- `parallel_execution_allowed: false` 约束 Agent，不禁止 G2.5 后的隔离 Slurm 训练并行。
- G2.5 前禁止任何正式训练 `srun`、`sbatch`、占位训练 job 或正式 checkpoint。
- Executor 不能宣布 Goal 完成。
- Controller 必须检查真实 diff、真实训练入口、真实 wrapper、真实 runtime 和 receipt 内容，不能只信 PASS token。
- 用 `care_ase_r2_full_fidelity` namespace-local tmux watcher 或等价 durable finalizer 保持连续监督到终态。

## 3. W0 / G0：来源、split、资源与 outer 零访问冻结

结果根目录：

```text
results/20260803_care_ase_r2_full_fidelity_execution
```

必须写：

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
stock checkpoint / plans / preprocessing / OOF baseline 来源可读并有 SHA256
effective_contract 已合并 base + amendment01/02/03 + R2
```

### 主 interactive allocation

用户指定主资源：

```text
job_id: 61794608
partition: htzhulab
user: aereinh
```

实时核验：

```bash
squeue -u "$USER" -p htzhulab -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
squeue -j 61794608 -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
scontrol show job 61794608
srun --jobid=61794608 --overlap \
  /users/a/e/aereinh/CARE/envs/env_CARE/bin/python \
  -c 'import torch,sys; print(sys.executable); print(torch.__version__); print(torch.cuda.is_available(), torch.cuda.get_device_name(0))'
```

不得再假定旧 job `61220581` 有效。若 `61794608` 已失效，只允许在 `htzhulab` 申请或提交替代资源；禁止自动转到其他 partition。

G0 失败不得进入 W1；路径、权限、磁盘和资源识别问题必须同 Goal 修复。

## 4. W1 / G1：完整行为实现门

必须修真实代码，不得只修文档、receipt 或 validator。允许保留紧凑文件布局，但 R2 合同中的行为必须完整实现。

### 必须进入真实 forward 和总损失

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

所有公式、权重、人群、归一化和 invalid-population 规则以 R2 合同为准。no-T2 中所有 edema-exclusive loss、bias 和参数梯度必须精确为零；class4 必须从最终竞争图中排除，不能映射成 background 负类。

### 必须实现 sampler

Stage A/B 严格执行 R2 的 20-step case-group cycle：完整 10、LGE-only 5、LGE+C0 5。完整病例 CenterB/CenterC 交替有放回，scar/edema 焦点交替；部分模态仅 scar 焦点。Stage C 只读 actual-train complete。

scar/edema 的 20-event focus cycle、fallback、OOF FN/FP 定义和 hard-negative manifest 消费必须逐项实现。生成 manifest 但 sampler 不读取属于硬失败。

### 必须实现 optimizer/scheduler

AdamW 只创建一次；阶段切换不得重建 optimizer。稳定参数组互斥且覆盖全部参数。冻结组 `requires_grad=false` 且 current LR 为 0。

阶段固定：

```text
A: global 0-2000
B: global 2000-10000
C: global 10000-14000
```

每组 base LR、min LR、warmup 和 power=0.9 poly 逐步公式必须原样执行。禁止 `scheduler_state=none`、固定 LR 或近似 scheduler。

### 必须实现 checkpoint/resume

每 1000 步、完整 optimizer step 后保存：

```text
tmp write -> file fsync -> parent fsync -> atomic rename -> SHA256 -> full reload
```

checkpoint 字段必须完整；resume 必须通过行为等价测试。

### G1 输出与 PASS

```text
implementation_gap_closure.json
parameter_group_coverage.json
semantic_loss_coverage.json
sampler_static_contract.json
scheduler_static_contract.json
checkpoint_schema_contract.json
known_bad_validator_report.json
```

PASS 要求：

```text
remaining_gap_count == 0
所有旧降级配置 known-bad 均 FAIL CLOSED
真实训练入口绑定新实现
AST/source/runtime-entrypoint 三重一致
```

G1 失败必须退回同一 Executor 修复；不得训练。

## 5. W2 / G2：真实 GPU 忠实性门

只允许 fold1/fold4 actual-train 病例，禁止读取新 outer。fixture 按 R2 合同的确定性算法选择并写入 `preflight_case_manifest.json`，必须覆盖：

```text
complete CenterB scar+edema positive
complete CenterC scar+edema positive
LGE-only scar positive
LGE+C0 scar positive
small-scar actual-train case
```

在 `61794608` 或经验证的 htzhulab 替代资源上证明：

1. stock 参数覆盖、top-stage clone、step0 anatomy/scar/edema parity；
2. normal forward 不读取 stock class4/class5 logits；
3. 每项 loss 有效 fixture 有有限非零梯度，无效人群精确为零；
4. 400-step descriptor dry-run 精确符合 case group、中心、病种焦点和 focus cycle；
5. Stage A/B/C 边界 trainability、base/current LR、warmup、poly progress 逐值正确；
6. area reference 与独立 actual-train 重算完全一致；
7. no-T2 edema-exclusive gradient max abs == 0.0；
8. 每个组件 module-off 记录 final-logit delta；若 label delta 为 0，扩大到全部预声明 actual-train fixture，不能用 logit-only 伪装；
9. one-batch overfit 同时降低 final、scar、edema 和辅助 loss；
10. full-volume sliding-window smoke；
11. atomic save/full reload/SHA/完整字段；
12. uninterrupted two-step 与 save/reload two-step 在 loss、logits、参数、scheduler、next-batch hash 上一致；
13. 旧阶段、scheduler none、complete-only Stage A/B、缺 loss、硬编码 area、manifest 未消费、缺 checkpoint 字段全部被拒绝。

必须写：

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

固定顺序：

```text
git diff --check
-> full tests
-> strict effective-contract validator
-> 检查真实 training entrypoint 和 wrapper
-> 提交本 Goal 源码/配置/测试/轻量 receipts
-> push origin/main
-> git fetch origin main
-> verify local HEAD == origin/main
-> write training_source_commit_receipt.json
```

receipt 必须记录：

```text
training_source_commit_sha
effective_contract_sha256
model/trainer/loss/sampler/scheduler/evaluator/validator SHA256
split/plans/stock checkpoint SHA256
G1/G2 validator SHA256
```

远端 SHA 相等前禁止训练。G2.5 后任何科学源码变化都使受影响训练 credit 归零，并返回 G1/G2/G2.5。

## 7. W3：完整两折训练与逐 chunk Gate

必须完成：

```text
fold1: 14000 optimizer steps
fold4: 14000 optimizer steps
```

无 one-fold fallback，无 early stop，无 inner checkpoint selection。

### fold1 主 interactive 路径

fold1 主要使用：

```bash
srun --jobid=61794608 --overlap <exact frozen training command>
```

按 7 个连续 2000-step chunk 执行。

### fold4 可并行路径

只有 G2.5 通过且 training source 已 push 后，才允许向 `htzhulab` 提交 fold4 的 7-chunk `afterok` chain：

```text
partition=htzhulab
qos=gpu_access
gres=gpu:1
cpus-per-task=8
mem=64G
walltime<=8h per 2000-step chunk
exact frozen Python and source commit
```

禁止代码未完成时预提交占位 job。

### 并行接管

fold1/fold4 使用独立 runtime、log、lock、checkpoint。每 fold/chunk 读首个 batch 前获取 atomic mkdir lock。

若 fold1 完成时 fold4 当前未完成 chunk 仍 pending：取消 pending chain，轮询确认，再在 `61794608` 从最后完整 checkpoint 串行继续 fold4。若取消期间 batch 已启动并持锁，让其完成；interactive loser 在读数据前退出并记 zero credit。

`61794608` 失效时，在 htzhulab 申请/提交替代资源继续；不得转其他 partition。

### 每个 2000-step chunk Gate

下一 chunk 前必须全部通过：

```text
Slurm terminal success
准确 global step
边界 checkpoint full reload
training_source_commit_sha 不变
effective_contract_hash 不变
stage/scheduler/current LR 正确
sampler cursors 与 next-batch hash 正确
checkpoint SHA 已记录
无 step overlap/gap/duplicate
```

startup failure、preemption、race loser、partial checkpoint 均 zero credit；pending/running/awaiting sacct 非终态。

## 8. W4：两折固定终点冻结 Gate

PASS 必须同时满足：

```text
fold1 global_step == 14000
fold4 global_step == 14000
两个 checkpoint_step14000.pt full reload PASS
model/optimizer/scheduler/RNG/worker seed/sampler/cursors/hashes/ramp 字段完整
training source commit 与 G2.5 一致
fold1/fold4 outer access before freeze == 0
```

写：

```text
checkpoint_freeze_receipt.json
full_reload_parity_receipt.json
outer_access_audit_receipt.json
```

损坏或字段缺失必须从最后完整 chunk 修复，不得进入 outer。

## 9. W4.5：outer 前不可变快照 Gate

快照必须包含 training source、effective contract、G1/G2/G2.5、14 个 chunk continuity receipts、Slurm accounting、两折 checkpoint SHA256 和 outer-zero-access。

固定顺序：

```text
build snapshot -> validator -> lightweight commit -> push -> remote SHA equality -> immediately W5
```

不等待人工确认，不提交 checkpoint、NIfTI、raw data 或大日志。

## 10. W5：新折 outer once 与三方公平比较

在任何 CARE-ASE outer inference 前冻结：

```text
fold1/fold4 outer cases
scar denominator
T2-present pure-edema denominator
canonical nnunet_oof rows
canonical mosaic_clean_oof rows
predeclared intervention/atlas cases
```

每折只运行一次 CARE-ASE outer，固定 step14000 与 argmax：

```text
T2 present: 0,1,2,3,4,5
no T2: 0,1,2,3,5
```

按同一 case_id/pathology/population 比较 CARE-ASE R2、nnunet_oof、mosaic_clean_oof：

- scar：fold1+fold4 全部唯一 outer；
- pure-edema：仅 T2-present outer；
- no-T2 edema 完全排除；
- 报告 mean、median、GT-positive、empty、help/harm/neutral、CenterB、CenterC、complete、no-T2 scar、小 scar；
- HD95/exact HD/remote FP/component count 仅在三个模型均可用同一 prediction-level evaluator 重算时比较，否则写 `NOT_BOUND_DO_NOT_INFER`；
- 无穷 HD 必须计数；
- outer 结果不得改变模型、decode 或 checkpoint。

旧 fold2/fold3 metric truth 只作 secondary posthoc evidence。

成功 Gate：

```text
pooled fresh scar Dice >= max(nnU-Net, MoSAIC) + 0.001
pooled fresh pure-edema Dice >= max(nnU-Net, MoSAIC) + 0.001
每病种相对 nnU-Net harm fraction <= 0.50
每新折每病种不低于 nnU-Net 超过 0.01
无灾难性空预测增加
CenterC edema sensitivity 不低于 nnU-Net 超过 0.01
相同 metric 可绑定时 HD95/remote FP 不得实质恶化
```

不达标必须如实给 partial/no-gain，禁止筛病例或改口径。

## 11. W6：终态

固定顺序：

```text
aggregation
-> Mapper final + wiki/fingerprint
-> strict validators + known-bad
-> Controller 检查真实 diff/source/14 chunks/case set/metrics
-> git diff --check
-> lightweight commit
-> push origin/main
-> fetch and verify local main == origin/main
-> notification_brief.json
-> ./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

最终第一行只能是：

```text
CARE_ASE_R2_BEATS_NNUNET_AND_MOSAIC_ON_FRESH_FOLDS
CARE_ASE_R2_PARTIAL_GAIN
CARE_ASE_R2_NO_GAIN
CARE_ASE_R2_OPERATIONALLY_BLOCKED
```

随后用自然中文说明：关闭的实现漏洞、各 Gate、fold1/fold4 步数和 job、三方结果、help/harm、困难中心、是否达标、commit/push/通知，以及所有未授权上传边界。

## 12. 阻塞边界

低分、loss 波动、视觉不佳、排队、单次启动失败、单个 preemption、一次 push 失败都不是阻塞。

只有同范围修复/重试耗尽后，以下情况允许 `OPERATIONALLY_BLOCKED`：

```text
数据/split/stock checkpoint 经修复仍不可读
仓库或存储不可恢复损坏
htzhulab 连续24小时无 61794608/替代 lane 且所有提交未启动
同一实现失败类别三次真实修复仍无法通过 G1/G2，且有 attempt diff 和最小复现
安全清理和本地替代路径后仍不可恢复的 quota/filesystem failure
```

完成或阻塞都必须形成轻量 packet、commit、push、SHA 核验和终态通知。
