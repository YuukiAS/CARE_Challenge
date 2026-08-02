---
task_key: 20260803_care_ase_r1_12h_faithful_repair
task_kind: scientific_milestone
task_type: faithful_implementation_repair_retrain_and_fresh_replication
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
allow_diagnostic_push: true
new_training_authorized: true
max_controller_wallclock_hours: 12
validation_upload_authorized: false
docker_upload_authorized: false
challenge_upload_authorized: false
hosted_metric_claim_authorized: false
contract_path: prompts/blueprints/CARE_ASE_R1_12h_faithful_repair_contract_20260803.yaml
---

# CARE-ASE R1 十二小时忠实修复、重训与新折复现实验正式 Controller

你是本次单一 Goal 的正式 Codex Controller。用户授权你修复 CARE-ASE 已确认的实现降级，并在总墙钟时间不超过 12 小时的前提下重新训练。科学目标是让忠实实现的 CARE-ASE 在新折同病例比较中同时超过 nnU-Net OOF 和 MoSAIC clean OOF；这是目标，不是允许伪造的保证。无论结果成功、部分成功、失败还是操作阻塞，都必须如实聚合、提交、推送、核验远端 SHA 并发送终态通知。

不得先运行旧的 `20260803_care_ase_metric_truth_repair` Goal。本 Goal 已将它作为 W5 的一部分吸收并取代。

## 1. 仓库与同步

工作目录：

```text
/users/a/e/aereinh/CARE
```

远端与分支：

```text
YuukiAS/CARE_Challenge
main
```

禁止写入：

```text
/overflow/htzhu/CARE
```

开始时执行并记录：

```bash
git fetch origin main --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor 64a69d42bc84fe458757cc3ff545cdcf02a69520 origin/main
git log --oneline -15 origin/main
```

工作树存在 Docker 或其他任务修改时，不得覆盖、删除、暂存或混入本 Goal。只提交本 Goal 的源码、配置、测试和轻量结果。

## 2. 必读真值

完整读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
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

prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment02_controller_only_interactive_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment03_final_audit_20260801.yaml
prompts/blueprints/CARE_ASE_R1_12h_faithful_repair_contract_20260803.yaml

results/20260801_care_ase_final_model/controller_report.md
results/20260801_care_ase_final_model/w45_implementation_snapshot/**
results/20260801_care_ase_final_model/outer_eval/fold_2/casewise_metrics.csv
results/20260801_care_ase_final_model/outer_eval/fold_3/casewise_metrics.csv
results/20260730_care_failure_forensics_deep_research_packet/standardized_casewise_metrics.csv
results/20260731_care_metric_truth_reconciliation/metric_semantics_contract.json
results/20260801_care_nnunet_mosaic_complementarity_closure/**
```

`CURRENT.md` 当前主要描述 Docker 线。该状态不得覆盖 CARE-ASE 本 Goal，也不得被本 Goal改成 CARE-ASE 主线；Docker 安全提交线保持独立。

## 3. 固定角色和持续监督

唯一流程：

```text
one Controller
-> one Executor
-> Mapper final
-> deterministic Validators
-> Controller real-diff/runtime/evidence verification
-> same-goal repair while authorized
-> main commit
-> push origin/main
-> verify local main == origin/main
-> notification_brief.json
-> existing notifier --once
```

不启用 planning critic、independent reviewer 或第二个人工继续门。Executor 不能宣布 Goal 完成。Controller 必须保持运行或由 `care_ase_r1_12h` tmux watcher 持续接管，直到所有正式 Slurm 步骤终态、聚合、验证、提交、推送和通知结束。

## 4. 十二小时硬预算

Controller 启动时立即写 `controller_start_utc`，十二小时后为绝对终止边界。目标时限：

```text
T+1.5h：W0/W1 完成
T+2.5h：W2 通过，训练源码已 commit/push 冻结
T+10h：W3 两折训练完成；若第二训练 lane 不可用则至少 fold4 完成
T+12h：W4/W4.5/W5/W6、push 和通知完成
```

不得通过缩短 14,000 步、删辅助损失、删采样规则、减少模型分支或改成浅层头来赶时间。若在 T+2.5h 仍不能通过忠实实现预检，禁止用已知错误实现启动训练；必须形成带最小复现的阻塞包、push 和通知。

## 5. 为什么改用 fold1 与 fold4

fold2/fold3 outer 已经被读取，不能再作为新的独立晋级依据。新主实验固定为：

```text
fold1
fold4
```

这两折的 CARE-ASE outer 在 W4.5 前不得读取。实现修复只能依据原 blueprint、base contract、amendment01/02/03 和已确认的代码合同偏差，禁止依据 fold1/fold4 outer 调参。

若 T+1.5h 只有一条可用训练 lane，立即启动 fold4，同时继续申请 fold1 lane至 T+2h。T+2h 仍无第二 lane时，允许只完成 fold4，但最终只能给 `ONE_FOLD_REPLICATION_ONLY`，不得声称两折稳定超过基线。

## 6. W0：来源、时间与新折冻结

必须生成：

```text
results/20260803_care_ase_r1_12h_faithful_repair/controller_context.json
results/20260803_care_ase_r1_12h_faithful_repair/time_budget_ledger.json
results/20260803_care_ase_r1_12h_faithful_repair/source_hash_manifest.json
results/20260803_care_ase_r1_12h_faithful_repair/effective_contract.json
```

必须冻结：

- fold1/fold4 train、inner、outer 清单与零交集证明；
- fold1/fold4 stock checkpoint、plans、preprocessing 和 canonical OOF prediction 哈希；
- 当前源码和旧 W4.5 快照；
- baseline casewise 与 metric semantics；
- 两折 outer 零访问计数；
- 当前 allocation、GPU 数量、剩余时间、磁盘、inode 和 quota。

优先核验既有 allocation `61220581`。如仍可用，使用隔离的 srun step 和显式 GPU 绑定。只允许 `htzhulab`；禁止自动使用 a100、volta 或其他 partition。

## 7. W1：必须关闭全部已知实现漏洞

不允许仅修验证器或改 receipt。必须修改真实模型、训练器、采样器、损失、scheduler、checkpoint 和评价代码，使它们满足 R1 合同。

至少关闭：

1. 阶段必须是 A 0–2000、B 2000–10000、C 10000–14000。
2. 实现每阶段线性预热和 power=0.9 多项式衰减；禁止 `scheduler_state=none`。
3. Stage A/B 使用 20 步固定循环：完整10、LGE-only 5、LGE+C0 5；Stage C只用 actual-train complete。
4. 完整病例 CenterB/CenterC 交替，瘢痕/水肿训练焦点交替。
5. 真实消费 OOF FN/FP、小瘢痕、边界和安全水肿负样本清单。
6. 从各折 actual-train 计算 scar/edema 面积参照；禁止硬编码 0.20/0.30。
7. 实现 anatomy、wall、signed distance、scar proposal/component/center/extent/context、edema dense/injury/boundary/extent/context/relation 的全部语义损失及 base contract 固定权重。
8. 瘢痕与水肿最高两级 deep supervision 使用原 nnU-Net 尺度权重；不得只计算中间 logits 而不进入总损失。
9. 水肿 context 中 label5 必须 ignore；no-T2 不得成为 edema negative。
10. no-T2 五类竞争完全排除 class4；若输入标签存在 class4，映射为 ignore 而不是 background。
11. 实现 Stage A/B/C 精确参数冻结、解冻、命名参数组和学习率。
12. 完整 checkpoint 保存与恢复 scheduler、全部 RNG、worker seed、sampler/batch cursor、next-batch SHA、ramp 和代码/配置/split/plans/stock 哈希。
13. 原子保存必须执行 tmp、file fsync、parent fsync、rename、SHA256、full reload。
14. 修复验证器，使旧实现中的每一个已知偏差均被 known-bad fixture 拒绝。

允许保留当前紧凑源码布局，避免为了分文件引入新的工程风险；这不允许降低任何行为合同。

W1 输出至少包括：

```text
implementation_gap_closure.json
known_bad_validator_report.json
target_cache_receipt.json
sampler_contract_receipt.json
optimizer_scheduler_contract_receipt.json
loss_gradient_contract_receipt.json
area_reference_receipt.json
```

`remaining_gap_count` 必须为 0。

## 8. W2：真实 GPU 忠实性门

只能使用 fold1/fold4 actual-train 病例，禁止读取新 outer。

必须证明：

- stock encoder、bottleneck、完整低中 decoder、anatomy top stages和scar/edema最高两级 clone均满足覆盖与第0步最终logit parity；
- 正常推理不读取 stock class4/class5 logits；
- 每项语义损失在有效 fixture 上有有限非零梯度；在不允许的人群上精确为零；
- 200 optimizer-step sampler dry-run精确符合 10/5/5、中心交替、病种焦点和各类百分比；
- Stage A/B/C 边界步的 trainability、base LR、current LR、warmup、poly progress全部正确；
- 实际面积参照与独立重算一致；
- no-T2 edema-exclusive gradient max abs为0；
- 每个组件关闭后在预检病例上记录最终logit delta和最终label delta；
- one-batch overfit、full-volume滑窗、保存/完整重载、next-batch hash和exact resume通过；
- known-bad旧版配置全部 FAIL CLOSED。

W2 通过后，立即把本次训练源码、配置、测试和轻量 receipts提交并push到 main，写 `training_source_commit_sha`。不等待人工确认，W3只能从该提交启动。训练期间禁止修改科学源码。

## 9. W3：两折并行固定 14,000 步

固定训练：

```text
fold1: 14000 optimizer steps
fold4: 14000 optimizer steps
```

优先两条隔离 GPU lane 并行运行。一个 Executor可以提交两个隔离的 Slurm step，但必须分别使用：

- 独立 runtime 目录；
- 独立 atomic lock；
- 独立日志与 checkpoint；
- 显式 GPU 绑定；
- 相同 `training_source_commit_sha`、effective contract和模型配置。

先对每折运行 50 个真实 optimizer step吞吐探针，并将 checkpoint、target cache和一次full-volume monitor开销计入 P90。只有预计可在剩余硬期限内完成才启动正式训练。

正式训练不得因低 Dice、loss 波动、视觉效果或困难病例暂未改善而提前结束。每 1000 步保存完整 checkpoint；第 14000 步为唯一正式checkpoint。inner每2000步仅监控，不得选checkpoint或改训练。

Controller 必须持续记录 heartbeat、step、stage、scheduler、checkpoint SHA、source SHA 和 job accounting。submitted、pending、running、preempted、awaiting sacct都不是终态。

## 10. W4 与 W4.5

W4 通过条件：

```text
完成折 global_step == 14000
checkpoint_step14000.pt 完整重载 PASS
model/optimizer/scheduler/RNG/sampler/hash/ramp 字段完整
outer_access_count_before_freeze == 0
```

W4.5 生成轻量快照并 push：

- training source commit；
- effective contract；
- W1/W2 receipts；
- 训练 stage、scheduler、sampler、checkpoint 和 terminal accounting；
- 两折 checkpoint SHA256；
- outer 零访问证明。

不得提交 checkpoint、NIfTI、原始数据或大日志。push成功后立即进入W5，不等待 GPT、Planner 或用户确认。

## 11. W5：新折一次评价与三方公平比较

先冻结 fold1/fold4 case set，然后对每个完成折只运行一次 outer：

```text
CARE-ASE R1 fixed step14000 fixed argmax
nnunet_oof canonical casewise
mosaic_clean_oof canonical casewise
```

正式口径：

- scar：完成新折的全部唯一 outer 病例；
- pure-edema：只统计其中 T2-present outer 病例；
- no-T2 edema 行必须完全排除，不得用空—空 Dice=1抬高均值；
- 按 case_id 严格连接三个模型，病例集合必须一致；
- 报告 mean、median、GT-positive、empty prediction、help/harm/neutral、CenterB、CenterC、完整模态、no-T2 scar和小scar；
- HD/HD95只有在三个模型都绑定到相同预测和相同实现时才能比较，否则写 `NOT_BOUND_DO_NOT_INFER`；
- 不得读取结果后改模型、阈值、decode或checkpoint。

同时完成旧 fold2/fold3 指标真值修复，但只作为 posthoc secondary evidence。

科学成功必须同时满足：

```text
CARE-ASE R1 scar mean Dice > max(nnU-Net, MoSAIC)
CARE-ASE R1 pure-edema mean Dice > max(nnU-Net, MoSAIC)
每个病种相对 nnU-Net harm fraction <= 0.50
无灾难性空预测增加
CenterC edema sensitivity在可绑定时不低于nnU-Net
```

若只完成fold4，不得给两折成功token。

## 12. W6：终态

固定顺序：

```text
aggregation
-> Mapper final
-> strict validators
-> Controller检查真实diff、source SHA、runtime、case set和结果
-> git diff --check
-> main lightweight commit
-> push origin/main
-> verify local main == origin/main
-> notification_brief.json
-> ./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

最终第一行只能是以下之一：

```text
CARE_ASE_R1_BEATS_BOTH_ON_FRESH_FOLDS
CARE_ASE_R1_PARTIAL_GAIN
CARE_ASE_R1_NO_GAIN
CARE_ASE_R1_ONE_FOLD_REPLICATION_ONLY
CARE_ASE_R1_OPERATIONALLY_BLOCKED
```

随后用自然中文说明：

1. 修复了哪些真实实现漏洞；
2. 实际训练了哪些折和多少步；
3. 与同病例nnU-Net、MoSAIC相比的scar和pure-edema结果；
4. help/harm、CenterB/CenterC和空预测说明什么；
5. 是否达到同时超过两者的目标；
6. commit SHA、origin/main SHA和通知回执；
7. validation、Docker、challenge upload和hosted claim仍未授权。

低分或未超过基线仍属于科学上有效的完成，不得隐瞒、改口径或伪造成功。
