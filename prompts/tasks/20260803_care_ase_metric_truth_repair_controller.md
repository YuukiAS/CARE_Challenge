---
task_key: 20260803_care_ase_metric_truth_repair
task_kind: scientific_milestone
task_type: posthoc_metric_truth_and_same_split_comparison
status: AUTHORIZED_BY_USER
risk_level: high
branch_policy: main-only
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
mapper_slots: 1
mapper_required: true
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
new_training_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
contract_path: prompts/blueprints/CARE_ASE_metric_truth_repair_contract_20260803.yaml
---

# CARE-ASE 指标真值修复与同划分三方比较正式 Controller

你是本次单一 Goal 的正式 Codex Controller。你的职责不是重新设计或训练 CARE-ASE，而是把已经完成的 CARE-ASE 运行从“操作完成但指标口径和实现忠实性解释不完整”修复成一份公平、可核验、不会误导决策的科学比较。

当前时间非常紧。不得借此 Goal 大改模型、重新训练、调阈值、重选检查点、修改解码或访问 validation。你必须持续监督一个 Executor，任何实现缺口都在同一 Goal 内修复，直到聚合、验证、main 提交、push、远端 SHA 核验和邮件通知全部完成。

## 1. 当前已知事实

当前完成提交：

```text
169929244d3ebcb1c463a0e6f68297714d6e7fd8
care-ase: finalize W5 outer evaluation
```

W4.5 实现快照：

```text
9517fe1738be5a03bc5d9115dade618ca3bc31b8
```

当前结果中：

```text
scar all_outer 88 cases mean Dice = 0.523500573079597
reported edema all_outer 88 rows mean Dice = 0.7953093461967583
T2-present / complete-modality edema 32 cases mean Dice = 0.43710070204108536
no-T2 edema 56 rows mean Dice = 1.0
```

因此 `0.7953093461967583` 不能继续作为 pure-edema 结果。它混入了 56 个 no-T2、GT 空且预测空的 `Dice=1.0` 行。正式 pure-edema 主口径必须只使用 32 个 T2-present outer 病例。

当前 W5 也没有在同一 packet 中重算或逐病例连接同划分 nnU-Net 与 MoSAIC clean OOF，因此现有结果不能支持“CARE-ASE 同时超过 nnU-Net 和 MoSAIC”的结论。

## 2. 同步与必读

进入：

```text
/users/a/e/aereinh/CARE
```

执行：

```bash
git fetch origin main --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline -15 origin/main
```

工作树若有当前 Docker 或其他任务修改，不得覆盖、删除或混入本 Goal。只提交本 Goal 审核过的轻量文件。

必须阅读：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/handoffs/CURRENT.md
.agents/skills/care-mapper/SKILL.md

prompts/blueprints/CARE_ASE_metric_truth_repair_contract_20260803.yaml
prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment03_final_audit_20260801.yaml

results/20260801_care_ase_final_model/controller_report.md
results/20260801_care_ase_final_model/pooled_fold2_fold3_statistics.csv
results/20260801_care_ase_final_model/outer_eval/fold_2/casewise_metrics.csv
results/20260801_care_ase_final_model/outer_eval/fold_3/casewise_metrics.csv
results/20260801_care_ase_final_model/split_authority_fold2.csv
results/20260801_care_ase_final_model/split_authority_fold3.csv
results/20260801_care_ase_final_model/w45_implementation_snapshot/**

results/20260730_care_failure_forensics_deep_research_packet/standardized_casewise_metrics.csv
results/20260731_care_metric_truth_reconciliation/metric_semantics_contract.json
results/20260801_care_nnunet_mosaic_complementarity_closure/**
```

`CURRENT.md` 当前主要描述 Docker 线。若它没有记录最新 CARE-ASE 结果，把它标记为不属于本 Goal 的当前机器真值，不要修改 Docker 决策。

## 3. Agent Flow

固定流程：

```text
one Controller goal
-> one Executor
-> Mapper final
-> strict Validators
-> Controller verification and same-goal repair
-> commit main
-> push origin/main
-> verify local main == origin/main
-> notification_brief.json
-> existing notifier --once
```

不启用 planning critic、independent reviewer 或第二个人工继续门。Executor 不能宣布 Goal 完成。Controller 必须持续负责到最终通知完成。

## 4. W0：来源与人口冻结门

W0 必须生成：

```text
results/20260803_care_ase_metric_truth_repair/controller_context.json
results/20260803_care_ase_metric_truth_repair/source_hash_manifest.json
results/20260803_care_ase_metric_truth_repair/implementation_deviation_receipt.json
```

必须冻结并哈希：

- 两折 CARE-ASE outer casewise 指标；
- 两折 split authority；
- canonical `standardized_casewise_metrics.csv`；
- metric semantics contract；
- 当前 CARE-ASE controller report；
- W4.5 snapshot commit 与审计包 SHA。

必须验证：

```text
fold2 outer == 44 unique cases
fold3 outer == 44 unique cases
fold2/fold3 outer intersection == empty
scar denominator == 88 unique cases
pure-edema denominator == 32 unique T2-present cases
```

no-T2 edema 行不得进入任何 edema 均值、help/harm、HD 或 promotion 结论。

W0 的缺文件、路径或字段属于同 Goal repair，不得 No-Run。若 canonical baseline casewise 文件确实不可读，先从已提交的 complementarity/forensics 代码和证据恢复；不得直接改用 hosted validation 数字。

## 5. W1：实现偏差绑定

本 Goal 不修模型，但必须把当前运行相对 Amendment03 的偏差写成机器可读证据。至少包括：

1. 实际阶段为 `2000/4000/8000`，不是 `2000/8000/4000`；
2. 实际没有合同要求的学习率调度器；
3. 14,000 步全程使用 `complete_only=True`，没有 Stage A/B 的 `10/5/5` 部分模态采样；
4. 候选、中心、上下文、损伤支持、边界、范围、关系及病理深监督没有按合同形成独立语义损失；
5. 采样器没有完整实现中心平衡、病种焦点、OOF FN/FP、小病灶、边界和安全负样本比例；
6. exact resume 状态和验证器覆盖不完整。

机器结论固定为：

```text
implementation_classification: CARE_ASE_SIMPLIFIED_COMPLETE_MODALITY_VARIANT
faithful_exact_contract_claim: false
```

不得修改历史文件伪装为当时已经通过完整合同；只新增 posthoc audit。

## 6. W2：三方逐病例连接与严格人口验证

使用 `case_id` 连接：

```text
CARE-ASE frozen fold2/fold3 outer
nnunet_oof
mosaic_clean_oof
```

nnU-Net 与 MoSAIC 必须来自 canonical clean held-out OOF casewise source，不得使用：

- hosted validation 数字；
- full-data MoSAIC；
- MoSAIC final deployment recipe；
- 不同病例集合；
- 不同病理定义；
- 病例 oracle 或 selector。

生成：

```text
population_and_join_validator.json
three_way_casewise.csv
```

每个病理的每个病例必须同时有三模型 Dice。任何缺行、重复行、错标签、no-T2 edema 混入都必须 fail closed 并在同 Goal 修复。

## 7. W3：公平三方统计

主比较：

```text
scar：88 outer cases
pure-edema：32 T2-present outer cases
```

必须输出每个模型的：

- mean Dice；
- median Dice；
- gt-positive mean Dice；
- empty GT 数；
- empty prediction 数；
- CenterB 与 CenterC；
- complete modality；
- no-T2 scar；
- small scar（若 canonical source 有绑定定义）；
- 病例级最佳模型。

CARE-ASE 相对 nnU-Net 和 MoSAIC 分别计算：

```text
help: delta Dice > 0.001
harm: delta Dice < -0.001
neutral: abs(delta Dice) <= 0.001
```

输出：

```text
three_way_summary.csv
center_and_modality_summary.csv
help_harm_summary.csv
empty_and_infinite_metric_audit.csv
```

物理 HD95、exact HD、remote FP 和组件数只有在三模型都绑定到同一实现和同一病例预测来源时才能比较。若 canonical baseline 仅有 Dice，明确写 `NOT_BOUND_DO_NOT_INFER`，不得用 CARE-ASE 单模型 HD 与历史不同口径数字硬比。

## 8. W4：可选固定评价重算边界

优先使用已经冻结的 casewise 指标完成最低充分三方 Dice 比较。

只有在以下情况才允许重跑固定推理：

- 已有 CARE-ASE 指标文件损坏或计算公式需修复；
- 三模型预测文件均已存在且能在数小时内使用统一 metric evaluator 重算；
- 不会影响最后一天的 Docker 安全线。

任何重算必须使用：

```text
CARE-ASE frozen checkpoint_step14000.pt
原固定 sliding-window
原固定 argmax decode
无阈值搜索
无检查点选择
无模型修改
```

重算 outer 只属于 posthoc metric repair，不得据此改模型。若物理指标来源不齐，完成 Dice 真值后继续，不得阻塞。

## 9. W5：科学解释

生成：

```text
metric_truth_receipt.json
scientific_interpretation.md
controller_report.md
```

科学结论只能使用以下四个 token：

```text
CARE_ASE_SIMPLIFIED_VARIANT_BEATS_BOTH_ON_SCAR_AND_EDEMA
CARE_ASE_SIMPLIFIED_VARIANT_PARTIAL_GAIN
CARE_ASE_SIMPLIFIED_VARIANT_NO_GAIN
METRIC_TRUTH_INSUFFICIENT_SOURCE_BINDING
```

判定规则：

- 两个病理在正确人口上均高于同划分 nnU-Net 和 MoSAIC，且相对 nnU-Net 的 help 多于 harm，才允许第一个 token；
- 只有一个病理有稳定增益，使用 `PARTIAL_GAIN`；
- 均无增益或伤害更多，使用 `NO_GAIN`；
- canonical casewise 来源无法闭合，使用 `INSUFFICIENT_SOURCE_BINDING`。

即使第一个 token 成立，也只能声称“简化完整模态训练变体”有本地同划分信号，不得声称完整 Amendment03 CARE-ASE 已验证，不得自动授权 validation 或 Docker。

必须明确：

```text
0.7953093461967583 is invalid as pure-edema headline
0.43710070204108536 is the current valid CARE-ASE T2-present edema mean before three-way join validation
```

## 10. 严格验证与防降级

严格验证器必须逐项检查：

1. 88 个 scar unique cases；
2. 32 个 T2-present edema unique cases；
3. no-T2 edema 行数为 0；
4. 每病例三模型均存在且无重复；
5. baseline model IDs 精确为 `nnunet_oof` 和 `mosaic_clean_oof`；
6. 无 hosted/full-data/selector 数字进入主表；
7. help/harm 从逐病例 delta 重新计算；
8. 当前运行被标记为 simplified variant；
9. 没有训练、阈值、decode、checkpoint 或模型修改；
10. 所有结论可由输出 CSV 重算。

禁止用以下方式降级：

- 只比较全局历史均值；
- 用 0.7953 作为 edema；
- 省略 MoSAIC；
- 省略 case-wise help/harm；
- 把缺失的 HD 填成 0 或沿用别的实验；
- 用硬编码结论代替逐病例 join；
- 因一个来源字段名称不同而直接 No-Run；
- 只写报告不产出机器可读表。

## 11. 运行连续性与阻塞边界

这是轻量 Goal，不需要新的长期训练作业。优先在现有 CPU 或已存在 allocation 上完成；若需要 GPU 重算，优先复用当前 htzhulab allocation，但不得影响 Docker 主线。

以下不是 block 理由：

- CSV 列名需要适配；
- canonical 文件需要从现有脚本恢复；
- 一次 join 或 validator bug；
- 物理指标无法三方统一；
- 当前 CARE-ASE 分数很差；
- MoSAIC 某些物理指标缺失；
- push 一次失败。

只有 canonical nnU-Net/MoSAIC held-out casewise Dice 经现有仓库所有绑定来源仍无法恢复，才允许 `METRIC_TRUTH_INSUFFICIENT_SOURCE_BINDING`。这仍是科学终态，不是 No-Run；必须继续聚合、提交、推送和通知。

## 12. 终态、提交、推送和通知

固定顺序：

```text
aggregation terminal
-> Mapper final
-> strict validators
-> Controller verification
-> git diff --check
-> add reviewed files only
-> commit main
-> push origin main
-> verify local main == origin/main
-> write notification_brief.json
-> ./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

禁止 force push、自建 SMTP、提前通知或混入 checkpoint、NIfTI、大日志、Docker archive。

Push 失败属于同 Goal retry，不得退出。无论科学结论好坏，都必须完成 main push 和邮件通知。

## 13. 最终输出

第一行只允许：

```text
CARE_ASE_METRIC_TRUTH_GOAL_ACHIEVED
```

或：

```text
CARE_ASE_METRIC_TRUTH_GOAL_BLOCKED
```

随后自然中文说明：

1. 当前 0.7953 为什么无效；
2. 正确 pure-edema 人口和分数；
3. CARE-ASE、nnU-Net、MoSAIC 三方 scar 与 edema 结果；
4. 相对 nnU-Net 的 help/harm；
5. CenterB/CenterC 与小 scar；
6. 当前实现偏差；
7. 是否值得最后一天做任何新动作；
8. commit SHA、origin/main SHA 和通知回执；
9. validation、Docker 与 hosted claim 仍未授权。
