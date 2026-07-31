---
task_key: 20260731_care_qif_v2_signal_audit
task_kind: scientific_milestone
task_type: mechanism_signal_audit
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
executor_plan_path: prompts/tasks/20260731_care_qif_v2_signal_audit_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: component
wiki_update_required: false
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: none
reviewer: none
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: true
route_promotion_gate: false
experiment_adequacy_gate: mechanism_signal_only
route_negative_gate: false
scientific_completion_gate: joint_signal_decision_only
diagnostic_publication_gate: true
diagnostic_publication_scope: results/20260731_care_qif_v2_signal_audit
blocked_after_diagnostic_publication: false
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
---

# CARE-QIF v2 两项核心可测事实审计 Controller

## Execution Contract

本任务只检验两个事实：

1. 病例内 LGE/T2 rank、robust-z、local contrast 是否在 CenterB 与 CenterC 中均保留 scar/injury-zone 可分性；
2. Scar component-query supervision 是否在 cross-center full-volume 评价中提高 lesion recall，同时 no-object queries 控制 remote false positive。

本任务不是完整 CARE-QIF v2 开发，不训练 edema field，不实现 ROI/refiner，不修改 production model，不访问 official validation/outer，不上传 Docker。

必须完整执行：

```text
prompts/blueprints/CARE_QIF_v2_signal_audit_20260731.md
prompts/tasks/20260731_care_qif_v2_signal_audit_executor_plan.yaml
```

二者与本文件共同构成冻结合同。不得只阅读摘要，不得自行更换 population、query count、loss、steps、selection score、pass gate 或结论 token。

## 用户授权边界

用户在当前任务中明确授权：

- 在 `main` 完成本任务；
- 运行必要的 CPU/GPU 诊断和四个 matched query pilot runs；
- 终态轻量 commit 推送到 `origin/main`；
- 不推送任何 `task/*`、`codex/*` 或其他临时远端分支；
- goal 达成或真实阻塞后，必须先完成 push 与 remote SHA 验证，再调用仓库现有 notifier 发送中文通知。

Runtime 中禁止 push。只有 terminal aggregation、validator、commit 全部完成后才允许 push。

## 当前仓库

```text
repo: /users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
```

不得创建 task branch 或额外 worktree。不得写 `/overflow/htzhu/CARE`。

## Bootstrap

开始前执行：

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

不得 reset、clean、覆盖或 stash 用户改动。若存在与本任务 write scope 冲突的未提交改动，停止为 `OPERATIONALLY_BLOCKED_WORKTREE_CONFLICT`，写终态阻塞 packet，push 可提交的 task-local轻量结果并 notify；不得覆盖。

## 必读

完整阅读：

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

必须读取最新结果：

```text
results/20260731_care_metric_truth_reconciliation/**
results/20260731_care_myopath_a0_a3_full_volume_closure/**
results/20260731_care_myowall_geometry_diagnostic_closure/**
results/20260730_care_failure_forensics_deep_research_packet/**
```

必须确认：

```text
metric_contract_status: PASS
A0-A3 scientific_decision: SYSTEMATIC_HARM
MyoWall scientific_decision: HARD_WALL_REPRESENTATION_INVALID
```

旧 `CURRENT.md` 或 wiki 若未及时反映最新两项结果，只记录 stale state，不得自行修改。

## Task graph

严格执行：

```text
W0 bootstrap/data/checkpoint/component freeze
→ W1 intensity signal audit
→ W2 OOF feature cache + query implementation/preflight
→ W3 BC_DENSE, BC_QUERY, CB_DENSE, CB_QUERY sequential formal runs
→ W4 held-out-center full-volume evaluation + intervention + atlas
→ W5 joint decision + validators + mapper + commit + push + notify
```

W1 和 W2 可以由 Controller按依赖顺序穿插，但只有一个 Executor；不得增加 executor 数量。正式 GPU run 一次只能有一个 active job。

## W0：数据、OOF 主干和组件统计冻结

必须从 canonical metadata 构建：

```text
complete tri-modal count = 80
CenterB = 35
CenterC = 45
```

若不一致：

```text
scientific_decision: DATA_CONTRACT_MISMATCH
```

不得继续。

为每个完整三模态病例绑定：

```text
case_id
center
modality availability
scar burden
injury burden
clean-OOF fold
clean-OOF checkpoint path/SHA256
plans/dataset/split SHA256
```

每个 case 必须恰好由一个未见过该病例的 checkpoint 提取 feature。任何 overlap/ambiguous fold 都停止为 `OOF_FEATURE_PROVENANCE_FAIL`。

全部 220 例做 scar connected-component 统计：

```text
26-connectivity
component count
component physical volume
small component count below 1000 mm3
centroid
blood-pool distance
myocardium-boundary distance
```

必须检查至少 99% 病例的 component count `<=32`。失败则：

```text
scientific_decision: QUERY_CAPACITY_INVALID
```

不得静默保留 largest 32。

W0 outputs：

```text
results/20260731_care_qif_v2_signal_audit/controller_context.json
results/20260731_care_qif_v2_signal_audit/frozen_data_contract.json
results/20260731_care_qif_v2_signal_audit/oof_backbone_manifest.csv
results/20260731_care_qif_v2_signal_audit/component_statistics.csv
results/20260731_care_qif_v2_signal_audit/component_capacity_receipt.json
```

## W1：Fact A 强度信号

严格按 blueprint 实现：

```text
GT_CONTEXT
DEPLOYABLE_CONTEXT
raw baseline
rank composite
CenterB -> CenterC
CenterC -> CenterB
secondary center-stratified five-fold
```

正式实现路径：

```text
scripts/forensics/care_qif_v2_signal_audit/intensity_features.py
scripts/forensics/care_qif_v2_signal_audit/run_intensity_audit.py
scripts/forensics/care_qif_v2_signal_audit/aggregate_intensity_audit.py
tests/care_qif_v2_signal_audit/test_intensity_audit.py
```

不得：

- 在 test center fit scaler/imputer；
- 选择 test center 上最佳 feature；
- 用全体素平衡采样的 AUPRC 冒充自然 prevalence；
- 将 GT context 结果当 deployable 结果；
- 将 edema label 4 单独称 injury zone；
- 使用 no-T2病例。

输出：

```text
intensity_feature_manifest.json
intensity_casewise_metrics.csv
intensity_transfer_summary.csv
intensity_context_comparison.csv
intensity_probe_coefficients.csv
intensity_signal_receipt.json
```

`intensity_signal_receipt.json` 必须包含：

```text
scar_decision
injury_decision
BC raw/rank AUROC/AUPRC lift
CB raw/rank AUROC/AUPRC lift
CenterB/CenterC per-case median and Q25 AUROC
GT-vs-deployable context delta
all gate predicates
```

W1 失败不阻止 W2–W4；两个事实必须独立完成。

## W2：Fact B 实现与 preflight

正式实现路径：

```text
scripts/training/care_qif_v2_signal_audit/build_oof_feature_cache.py
scripts/training/care_qif_v2_signal_audit/query_models.py
scripts/training/care_qif_v2_signal_audit/query_losses.py
scripts/training/care_qif_v2_signal_audit/query_dataset.py
scripts/training/care_qif_v2_signal_audit/run_query_pilot.py
scripts/evaluation/care_qif_v2_signal_audit/evaluate_query_pilot.py
configs/care_qif_v2_signal_audit/common.yaml
configs/care_qif_v2_signal_audit/BC_DENSE.yaml
configs/care_qif_v2_signal_audit/BC_QUERY.yaml
configs/care_qif_v2_signal_audit/CB_DENSE.yaml
configs/care_qif_v2_signal_audit/CB_QUERY.yaml
jobs/care_qif_v2_signal_audit/run_query_pilot.sh
tests/care_qif_v2_signal_audit/**
```

精确类：

```text
CleanOOFFeatureExtractor
DeterministicIntensityChannels
CommonScarFeatureStem
DenseParameterMatchedControl
ScarComponentQueryHead
ScarSetMatcher
ScarComponentQueryLoss
CrossCenterScarDataset
CrossCenterScarEvaluator
```

结构、Q=32、Transformer decoder、loss、union formula 均以 blueprint 为准。

必须生成 clean-OOF feature cache。Cache 只写：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260731_care_qif_v2_signal_audit/features
```

禁止 Git 跟踪 feature tensor。

Preflight 必须包含：

1. 真实病例 full-volume forward；
2. dense/query arm shape一致；
3. query Hungarian matching有 matched/unmatched queries；
4. no-object loss非零；
5. query on/off 改变 final labels；
6. save/reload 输出误差 `<=1e-6` FP32；
7. evaluated case 的 feature checkpoint未见过该 case；
8. dense/query 参数量报告；
9. one-batch overfit 至少 200 steps，query mask loss下降且无 NaN；
10. full-volume remote-FP evaluator执行。

Preflight 是 zero-credit，不得当 Fact B 结果。

输出：

```text
implementation_snapshot.md
feature_cache_manifest.csv
parameter_count_report.json
one_batch_overfit_report.json
preflight_intervention_report.json
preflight_validator_report.json
```

## W3：四个 matched formal runs

正式 runs：

```text
BC_DENSE
BC_QUERY
CB_DENSE
CB_QUERY
```

顺序固定，不并行。

每个 run：

```text
4000 optimizer steps
AdamW
lr 3e-4
weight_decay 1e-4
physical batch 1
accumulation 4
warmup 250
cosine min lr 1e-6
bf16 H100/A100
gradient clip 12
checkpoint/eval every 500
seed 20260731
```

同方向 dense/query 必须消费相同：

```text
train cases
selection cases
case order
crop/full-volume descriptor
augmentation parameters
random seed
optimizer-step count
validation cadence
```

写：

```text
batch_descriptor_manifest_BC.jsonl
batch_descriptor_manifest_CB.jsonl
```

Dense/query manifest hash 必须一致。

Selection 只在训练中心内部 selection subset使用 blueprint 固定 score。Held-out center 不能用于 threshold、checkpoint、early stop或参数调整。

每个 run达到 4000 steps；不得因为 loss plateau 或资源节省提前停。Timeout/preemption只能 exact resume，必须保存：

```text
model
optimizer
scheduler
scaler
RNG states
batch cursor
optimizer step
```

失败 startup attempt 记 0 credit。

## Slurm

正式 Python：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

禁止裸 `python`。

先检查：

```bash
squeue -u "$USER" -o '%i|%j|%P|%T|%M|%L|%R|%b'
sinfo -o '%P|%a|%l|%D|%t|%G'
```

Preferred：

```text
htzhulab
```

30 分钟仍 pending，取消并保持同 config/hash 转：

```text
a100-gpu
```

不得 race，不得同时跑两个 GPU job。

资源：

```text
gpu:1
cpus:16
memory:128G
walltime:12h
```

训练依赖：`afterok`；finalizer/accounting：`afterany`。

必须提交 durable finalizer，Controller 持续到 terminal accounting、aggregation 和 validator。`PENDING/RUNNING/AWAITING_SACCT` 不是完成。

W3 outputs：

```text
training_accounting.csv
checkpoint_selection.csv
batch_manifest_hashes.csv
slurm_attempt_lineage.csv
selected_checkpoint_manifest.csv
```

Checkpoint 和大日志不提交 Git。

## W4：Held-out center full-volume evaluation

冻结 selected checkpoints 后：

```text
BC models evaluate CenterC 45 exactly once
CB models evaluate CenterB 35 exactly once
```

必须完整评价 blueprint 指标。

Query intervention：对 selected query arm checkpoint分别关闭 query contribution，但保留 dense head，报告：

```text
changed labels
Dice delta
HD95 delta
lesion recall delta
small-lesion recall delta
remote FP delta
query precision
duplicate-query rate
```

不得只做 gradient/logit intervention。

Case-wise help/harm threshold：

```text
Dice delta > +0.01: help
Dice delta < -0.01: harm
else neutral
```

Atlas 固定选择：

```text
CenterC: Case3008, Case3009 if present
query-vs-dense largest 5 lesion-recall gains
query-vs-dense largest 5 remote-FP harms
largest 5 small-lesion gains
```

去重后最多 18 例。

每例显示：

```text
LGE/T2/C0
GT scar
OOF nnU-Net scar reference
Dense control
Query arm
Query-disabled intervention
query masks with confidence
FP/FN
component IDs
```

输出：

```text
query_casewise_metrics.csv
query_transfer_summary.csv
query_component_metrics.csv
query_intervention_metrics.csv
query_help_harm.csv
component_query_receipt.json
case_atlas.pdf
case_atlas_contact_sheet.png
visual_findings.md
```

## W5：联合裁决

严格使用 blueprint token：

```text
GO_QIF_V2_MODEL_PILOT
GO_SCAR_ONLY_REDESIGN
GO_INTENSITY_DENSE_ONLY
NO_GO_QIF_V2
```

不得发明“差不多通过”“建议继续长训”等模糊结论。

只有：

```text
INTENSITY_SIGNAL_PASS_BOTH
AND COMPONENT_QUERY_FACT_PASS
```

才能写：

```text
GO_QIF_V2_MODEL_PILOT
```

即便 GO，也只表示下一轮可以设计完整模型 pilot，不授权本 goal 自动启动。

## Write scope

只允许写：

```text
scripts/forensics/care_qif_v2_signal_audit/**
scripts/training/care_qif_v2_signal_audit/**
scripts/evaluation/care_qif_v2_signal_audit/**
tests/care_qif_v2_signal_audit/**
configs/care_qif_v2_signal_audit/**
jobs/care_qif_v2_signal_audit/**
results/20260731_care_qif_v2_signal_audit/**
```

禁止修改：

```text
src/care_myocardium/models/care_myopath_pilot.py
src/care_myocardium/models/myowall_if/**
prompts/routes/handoffs/CURRENT.md
wiki/README.md
data/**
现有 A0-A3/MyoWall 结果
production evaluator
```

## Required outputs

```text
results/20260731_care_qif_v2_signal_audit/controller_context.json
results/20260731_care_qif_v2_signal_audit/controller_ledger.csv
results/20260731_care_qif_v2_signal_audit/frozen_data_contract.json
results/20260731_care_qif_v2_signal_audit/oof_backbone_manifest.csv
results/20260731_care_qif_v2_signal_audit/component_statistics.csv
results/20260731_care_qif_v2_signal_audit/component_capacity_receipt.json
results/20260731_care_qif_v2_signal_audit/intensity_feature_manifest.json
results/20260731_care_qif_v2_signal_audit/intensity_casewise_metrics.csv
results/20260731_care_qif_v2_signal_audit/intensity_transfer_summary.csv
results/20260731_care_qif_v2_signal_audit/intensity_context_comparison.csv
results/20260731_care_qif_v2_signal_audit/intensity_probe_coefficients.csv
results/20260731_care_qif_v2_signal_audit/intensity_signal_receipt.json
results/20260731_care_qif_v2_signal_audit/implementation_snapshot.md
results/20260731_care_qif_v2_signal_audit/feature_cache_manifest.csv
results/20260731_care_qif_v2_signal_audit/parameter_count_report.json
results/20260731_care_qif_v2_signal_audit/one_batch_overfit_report.json
results/20260731_care_qif_v2_signal_audit/preflight_intervention_report.json
results/20260731_care_qif_v2_signal_audit/preflight_validator_report.json
results/20260731_care_qif_v2_signal_audit/training_accounting.csv
results/20260731_care_qif_v2_signal_audit/checkpoint_selection.csv
results/20260731_care_qif_v2_signal_audit/batch_manifest_hashes.csv
results/20260731_care_qif_v2_signal_audit/slurm_attempt_lineage.csv
results/20260731_care_qif_v2_signal_audit/selected_checkpoint_manifest.csv
results/20260731_care_qif_v2_signal_audit/query_casewise_metrics.csv
results/20260731_care_qif_v2_signal_audit/query_transfer_summary.csv
results/20260731_care_qif_v2_signal_audit/query_component_metrics.csv
results/20260731_care_qif_v2_signal_audit/query_intervention_metrics.csv
results/20260731_care_qif_v2_signal_audit/query_help_harm.csv
results/20260731_care_qif_v2_signal_audit/component_query_receipt.json
results/20260731_care_qif_v2_signal_audit/case_atlas.pdf
results/20260731_care_qif_v2_signal_audit/case_atlas_contact_sheet.png
results/20260731_care_qif_v2_signal_audit/visual_findings.md
results/20260731_care_qif_v2_signal_audit/joint_decision_receipt.json
results/20260731_care_qif_v2_signal_audit/slurm_accounting.csv
results/20260731_care_qif_v2_signal_audit/finalizer_state.json
results/20260731_care_qif_v2_signal_audit/strict_validator_report.json
results/20260731_care_qif_v2_signal_audit/known_bad_report.json
results/20260731_care_qif_v2_signal_audit/mapper_report_final.md
results/20260731_care_qif_v2_signal_audit/controller_report.md
results/20260731_care_qif_v2_signal_audit/completion_check.md
results/20260731_care_qif_v2_signal_audit/MANIFEST.md
results/20260731_care_qif_v2_signal_audit/notification_brief.json
```

## Strict validator and known-bad

实现：

```text
scripts/validation/validate_care_qif_v2_signal_audit.py
tests/care_qif_v2_signal_audit/test_known_bad.py
```

必须拒绝：

1. 80/35/45 case count不匹配；
2. evaluated case feature checkpoint见过该病例；
3. GT context进入 query pilot；
4. test center用于 scaler/threshold/checkpoint selection；
5. AUROC来自平衡采样而非自然评价体素；
6. no-T2进入 injury probe；
7. injury错误定义为仅 label4；
8. raw/rank feature定义漂移；
9. query count不是32；
10. component overflow被静默删除；
11. query不进入 final labels；
12. query只做 auxiliary loss；
13. stock scar logit参与 query final composition；
14. dense/query病例顺序或 augmentation不匹配；
15. 任一正式 run少于4000 steps；
16. checkpoint未 reload；
17. held-out center参与 selection；
18. 只报告 Dice不报告 lesion/remote FP/HD95；
19. recall提高但 remote FP爆炸仍判 PASS；
20. 只在一个方向有效仍判 PASS；
21. query intervention只有 logit delta；
22. patch proxy冒充 full volume；
23. pending/running job冒充完成；
24. checkpoint/feature cache/NIfTI被提交；
25. CURRENT/wiki被修改；
26. runtime 中 push；
27. 推送 task/codex remote branch；
28. notifier在 push/remote SHA验证前运行；
29. joint token与两个 fact receipt不一致；
30. GO 后自动启动完整模型训练。

Validator errors必须非零退出。

## Mapper

Mapper 只读检查：

```text
OOF checkpoint -> F0/F1 -> deterministic rank channels
-> common stem -> dense/query heads -> final scar probability
```

必须确认：

- 没有第二完整 backbone；
- stock pathology logits不参与 final；
- GT context不进入 deployable path；
- query/no-object/mask/center loss映射正确；
- dense/query输入相同；
- held-out-center leakage不存在。

写 `mapper_report_final.md`，不得修改 wiki。

## Completion, commit, push

Controller 只能在：

```text
all jobs terminal
all four formal runs complete
all held-out-center evaluations complete
aggregation complete
strict validator PASS
known-bad PASS
mapper final complete
required outputs complete
```

后写 `controller_verification_decision: VERIFIED_COMPLETE`。

轻量 commit message：

```text
experiment: complete CARE-QIF v2 signal audit
```

禁止提交：

```text
checkpoint
NIfTI
feature tensors
raw data
large logs
secrets
```

Push 前：

```bash
git fetch origin main
git rebase origin/main
./envs/env_CARE/bin/python scripts/validation/validate_care_qif_v2_signal_audit.py --phase final
git diff --check
git push origin HEAD:main
```

禁止 force push，禁止 push任何其他 ref。

验证：

```bash
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git ls-remote origin refs/heads/main | cut -f1)
test "$LOCAL_SHA" = "$REMOTE_SHA"
```

若远端前移，最多3次 fetch/rebase/validator/push。真实冲突停止为：

```text
OPERATIONALLY_BLOCKED_MAIN_MERGE_CONFLICT
```

## Notification

无论 achieved 或 blocked，都必须在 push 与 remote SHA 验证后写：

```text
results/20260731_care_qif_v2_signal_audit/notification_brief.json
```

字段：

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

然后运行：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

禁止自写 SMTP，不得在 pending/running/未 push 时通知。

若 notifier 生成 receipt，提交 receipt 并再次 push main、验证 remote SHA。

## Controller report

开头先用自然中文回答：

1. CenterB/CenterC scar intensity signal是否同时成立；
2. CenterB/CenterC injury intensity signal是否同时成立；
3. deployable context是否保留 GT context信号；
4. query相对 dense是否提高 lesion和small-lesion recall；
5. remote FP、HD95、Dice是否付出不可接受代价；
6. Case3008/3009发生了什么；
7. 是否允许设计完整 CARE-QIF v2 pilot；
8. 什么仍未授权。

随后列：

```text
controller_verification_decision
joint_scientific_decision
scar_intensity_decision
injury_intensity_decision
component_query_decision
BC summary
CB summary
pooled query-vs-dense summary
all Slurm job IDs/states
validator status
commit SHA
remote main SHA
notifier receipt
```

明确说明：

- 已推送 main；
- 未推送额外远端分支；
- 未访问 outer/official validation；
- 未上传 Docker；
- 未启动完整 CARE-QIF v2；
- 未修改 CURRENT/wiki。

## Controller prompt

Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, controller-as-coordinator diff inspection and repair loop, strict validators and known-bad regressions, minimum effective training, terminal Slurm accounting and post-completion aggregation, mapper/dataflow/leakage gates, patient-clean OOF feature provenance, matched cross-center controls, final-label interventions, and terminal main push plus existing notifier after remote SHA verification. If any hard gate fails, continue same-scope repair when authorized or stop with a truthful blocked token; do not claim VERIFIED_COMPLETE.

## Executor worker contract

The Executor performs authorized implementation and commands but cannot declare the whole task complete. Return every wave to the Controller/Coordinator for diff, evidence, validator, runtime, leakage, metric and contract verification. Do not fill architecture blanks, change gates, reduce budgets, use held-out-center selection, or add modules outside the frozen blueprint.
