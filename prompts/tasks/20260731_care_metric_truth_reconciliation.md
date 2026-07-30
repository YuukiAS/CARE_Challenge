---
task_key: 20260731_care_metric_truth_reconciliation
task_kind: audit
task_type: metric_truth_reconciliation
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
executor_plan_path: null
mapper_slots: 1
mapper_required: false
architecture_impact: none
wiki_update_required: false
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: none
reviewer: none
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: false
experiment_adequacy_gate: diagnostic_only
route_negative_gate: false
scientific_completion_gate: metric_contract_only
diagnostic_publication_gate: true
diagnostic_publication_scope: results/20260731_care_metric_truth_reconciliation
blocked_after_diagnostic_publication: false
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
---

# CARE 指标真值、病例人群与分数来源统一

## Execution Contract

本任务只解决一个问题：把当前 CARE 仓库中被混写的指标、病例人群、标签语义和分数来源统一成一份机器可解析的唯一真值合同。

它不设计模型，不修改正式训练，不启动新架构，不选择 checkpoint，不调阈值，不访问未授权 outer，不上传 validation/Docker。

当前必须解释清楚的数字至少包括：

```text
D0 identity: scar 0.9224 / pure edema 0.9231
D1 decoder reset: scar 0.547 / pure edema 0
D2 top train: scar 0.7108 / pure edema 0.2664
D3 short fine-tune: scar 0.9227 / pure edema 0.9225
nnU-Net clean OOF: scar 0.5610 / pure edema 0.4308
fold0 outer nnU-Net: scar 0.5340911530 / edema-zone 0.5592277699
fold0 outer PRISM: scar 0.4196441776 / edema-zone 0.2471543848
MoSAIC clean OOF
MoSAIC full-data mechanism probe
MoSAIC official hosted validation
nnU-Net official hosted comparator
```

核心目标不是挑一个“看起来最高”的数字，而是回答每个数字究竟是什么：

- 模型对 GT 的 Dice；
- 预测与预测之间的 identity/parity；
- clean OOF；
- train-on-case full-data probe；
- inner-select；
- one-time outer；
- hosted validation；
- scar；
- official pure edema；
- internal edema-zone；
- all-case 或 positive-GT population。

## Active workspace and branch

本 Codex goal 必须在隔离 worktree 中执行：

```text
worktree: /users/a/e/aereinh/CARE_worktrees/task_metric_truth_20260731
branch: task/20260731-metric-truth
base: origin/main
```

不得写入主工作树或其他 task/route worktree。

## Bootstrap

先执行：

```bash
cd /users/a/e/aereinh/CARE_worktrees/task_metric_truth_20260731
git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -15
git diff --check
```

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
```

还必须读取 V4 证据包及所有底层来源：

```text
results/20260730_care_failure_forensics_deep_research_packet/CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v4.pdf
results/20260730_care_failure_forensics_deep_research_packet/DEEP_RESEARCH_MODEL_DESIGN_INPUT_20260730_v4.md
results/20260730_care_failure_forensics_deep_research_packet/standardized_casewise_metrics.csv
results/20260730_care_failure_forensics_deep_research_packet/standardized_model_summary.csv
results/20260730_care_failure_forensics_deep_research_packet/v4_mosaic_m0_m10_casewise.csv
results/20260730_care_failure_forensics_deep_research_packet/v4_mosaic_m0_m10_summary.csv
results/20260730_care_failure_forensics_deep_research_packet/v4_large_gain_bounds.csv
results/20260730_care_failure_forensics_deep_research_packet/v4_feature_probe_fold_results.csv
```

以及：

```text
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_inner_select_formal_v2/summary.json
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_outer_once_formal_v2/summary.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_training_summary.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_strict_validator_report.json
```

对 MoSAIC hosted 数字，必须从仓库已有 provenance、submission log、paper truth ledger 或绑定结果读取，不得从聊天记忆手填。

## Frozen label semantics

必须冻结并验证：

```text
scar: internal label 5
official pure edema: internal label 4, only reliable T2-present cases
internal edema-zone: label 4 or 5, internal diagnostic only
myocardium union: label 1 or 4 or 5
T2-present canonical denominator: 80
```

`edema-zone` 不能再写作 official edema。

## Ordered task graph

### M0. Source inventory

扫描所有会产生上述数字的脚本、CSV、JSON、Markdown、PDF source、checkpoint receipt 和 prediction manifest。

输出：

```text
results/20260731_care_metric_truth_reconciliation/source_inventory.csv
results/20260731_care_metric_truth_reconciliation/score_occurrence_inventory.csv
```

`score_occurrence_inventory.csv` 每一条自然语言或机器数字都记录：

```text
score_id
value
source_path
source_sha256
source_row_or_key
model_id
checkpoint_sha256
prediction_sha256
case_set_id
case_count
train_case_relationship
population_role
pathology_object
label_definition
metric_name
metric_implementation
physical_spacing_used
empty_gt_policy
positive_gt_only
threshold
decode_rule
is_hosted
is_clean_oof
is_train_on_case
is_prediction_parity
claim_allowed
notes
```

### M1. D0–D3 semantic reconstruction

必须读取 decoder-reset 的实际实现和计算脚本，判断 `0.922x` 是：

- 对 GT 的 Dice；
- 与 stock nnU-Net prediction 的 parity；
- 某个 validation-like population；
- 或其他指标。

不得从变量名推断。必须追踪到：

```text
input cases
GT/prediction paths
decode
metric function
aggregation
```

如现有输出不足，允许运行固定 checkpoint 的只读 inference/parity replay。不得训练。

输出：

```text
decoder_reset_score_semantics.json
decoder_reset_score_lineage.csv
```

### M2. nnU-Net score lineage

区分并绑定：

```text
clean OOF
fold0 inner-select
fold0 outer once
full-data/train-on-case
hosted validation
prediction parity
```

每个 score 必须有唯一 `score_contract_id`。

### M3. MoSAIC score lineage

必须分开：

```text
M0/M1 clean OOF
M2-M10 full-data mechanism probe
local complete-trimodal diagnostic
hosted validation
paper-reported values
```

必须标明每个 case 是否参与对应 checkpoint 训练。

### M4. Metric implementation cross-check

对当前正式需要保留的 score，使用 forensic reference evaluator 独立重算或抽样交叉验证：

```text
Dice
HD95 in mm
exact HD in mm
lesion recall
remote FP
component count
```

若 raw prediction 不存在，标记 `NOT_RECOMPUTABLE_FROM_LOCAL_PREDICTION`，不得伪造重算。

### M5. 唯一真值表

生成：

```text
metric_truth_table.csv
metric_semantics_contract.json
metric_truth_receipt.json
score_lineage_report.md
deep_research_score_corrections.md
```

`metric_truth_table.csv` 至少包含以下主列：

```text
score_contract_id
model_id
model_role
checkpoint_sha256
prediction_sha256
case_set_id
case_count
train_relation
population
pathology
label_semantics
metric
value
ci_if_available
threshold
decode
source_path
evidence_grade
allowed_comparison_group
forbidden_comparison_group
```

`metric_truth_receipt.json` 必须包含：

```json
{
  "metric_contract_status": "PASS|FAIL",
  "canonical_t2_present_count": 80,
  "d0_0p922_semantics": "...",
  "clean_oof_contract_ids": [],
  "outer_once_contract_ids": [],
  "hosted_contract_ids": [],
  "forbidden_direct_comparisons": [],
  "remaining_blockers": []
}
```

只有以下条件全部满足才允许 `PASS`：

1. D0–D3 数字来源已追踪到实际计算；
2. scar、pure edema、edema-zone 没有混写；
3. clean、outer、full-data、hosted、parity 分开；
4. 80 个 T2-present denominator 已绑定；
5. 每个核心 score 都有 source/hash/case population；
6. 比较组和禁止比较组已写清；
7. strict validator 通过。

## GPU and Slurm boundary

本任务以 CPU 为主。

只有在缺少 D0–D3 或某个核心 score 的 raw prediction、且 exact checkpoint/code/config/case set 已绑定时，才允许提交一个只读 diagnostic inference job。

GPU 任务不得训练，不得选择 checkpoint，不得改变阈值。

正式 Python：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

禁止裸 `python`。

如果提交 Slurm，必须使用 durable `afterany` finalizer，并记录 terminal accounting。

## Write scope

只允许写：

```text
scripts/forensics/metric_truth/**
tests/forensics/metric_truth/**
results/20260731_care_metric_truth_reconciliation/**
```

不得修改：

```text
src/care_myocardium/models/**
src/care_myocardium/training/**
现有 production evaluator
CURRENT.md
wiki/README.md
```

若发现 production evaluator 有 bug，只记录修复建议，不在本任务修改。

## Strict validator and known-bad

实现：

```text
scripts/forensics/metric_truth/validate_metric_truth.py
tests/forensics/metric_truth/test_metric_truth_known_bad.py
```

known-bad 必须拒绝：

1. prediction parity 冒充 GT Dice；
2. train-on-case full-data 冒充 clean OOF；
3. fold0 outer 用于二次选择；
4. edema-zone 冒充 official edema；
5. no-T2 进入 pure-edema denominator；
6. hosted score 无 submission provenance；
7. checkpoint 名称代替 SHA；
8. case_count 缺失；
9. metric implementation 缺失；
10. physical spacing 未知却报告 HD95 mm；
11. D0 0.922 与 clean OOF 0.56 直接比较；
12. MoSAIC M2-M10 与 hosted validation 直接比较；
13. PDF prose 覆盖底层 CSV/JSON；
14. `metric_contract_status: PASS` 但仍有核心 unresolved score。

validator 发现 error 必须非零退出。

## Completion and commit

最终必须生成：

```text
results/20260731_care_metric_truth_reconciliation/controller_report.md
results/20260731_care_metric_truth_reconciliation/completion_check.md
results/20260731_care_metric_truth_reconciliation/MANIFEST.md
```

`controller_report.md` 开头先用自然中文回答：

1. 哪些数字此前被混写？
2. D0 `0.922x` 到底是什么？
3. 当前可用于公平模型比较的唯一 clean/inner 指标是什么？
4. 当前可用于 hosted 比较的数字是什么？
5. 哪些比较以后必须禁止？
6. Lane B A0–A3 是否可以正式启动？

机器字段：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
metric_contract_status: PASS | FAIL
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
git_commit_decision:
git_push_decision: NOT_AUTHORIZED
next_required_action:
```

本地 commit：

```text
audit: reconcile CARE metric truth and score lineage
```

禁止 push。最终返回 Planner，由 Planner 决定是否合并该 task branch。

## Controller prompt

Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, controller-as-coordinator diff inspection and repair loop, strict validators and known-bad regressions, terminal Slurm accounting and post-completion aggregation when diagnostic inference is needed. If any hard gate fails, continue same-scope repair when authorized or stop with NEEDS_REPAIR/OPERATIONALLY_BLOCKED; do not claim VERIFIED_COMPLETE.

## Executor worker contract

The Executor performs authorized inspection, scripts, fixed inference and aggregation but cannot declare the whole task complete. Return every wave to the Controller/Coordinator for diff, evidence, validator, runtime and contract verification.
