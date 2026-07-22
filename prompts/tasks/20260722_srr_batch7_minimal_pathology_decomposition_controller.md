---
task_key: 20260722_srr_batch7_minimal_pathology_decomposition
task_kind: scientific_milestone
task_type: final_minimal_proposal_and_dictionary_decomposition
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
status: READY_FOR_CONTROLLER
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: component
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: planner_only
experiment_adequacy_gate: explicit_loss_authority_and_four_matched_pathology_runs
route_negative_gate: planner_only
scientific_completion_gate: planner_only
diagnostic_publication_gate: false
diagnostic_publication_scope: none
blocked_after_diagnostic_publication: Batch8,refiner,source_arbiter,production_gate,fold_expansion,Cine,validation_upload,hosted_claim
---

## Execution Contract

本任务不是继续修完整 Batch7，也不是启动 Batch8。它是当前 proposal/dictionary 路线的最终最小分解：先修正此前 `proposal-only` 阶段实际使用混合 M10 loss 的问题，再分别比较 scar/edema 的 minimal proposal 与 dictionary proposal。任务结束后必须明确删除或保留每个病种的 proposal 和 dictionary，不允许继续用“还需完善组件”延长同一路线。

开始前必须同步 `main`，绑定当前远端 SHA，并读取：

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
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
results/srr_production/code_maturity/batch7_repair_planner_audit_and_minimal_decomposition_decision_20260722.md
docs/plans/laneB_round04_active_srr_batch7_minimal_pathology_decomposition_execution.md
configs/srr_production/myops_batch7_minimal_decomposition.yaml
prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml
```

固定来源：

```text
source checkpoint SHA256: d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
fold0 train/validation: 176/44
decode: outputs["logits"].argmax
```

## Controller Prompt

你是本任务的 coordinator 和验收负责人。必须持续监督 Executor，检查真实 diff、resolved loss、loss-specific gradient、冻结范围、匹配采样、Slurm、prediction roots、aggregation、validator、CURRENT/wiki/fingerprint，并对同范围问题立即要求修复和重跑。不得只记录问题后退出。

### 1. 训练前先修 loss authority

此前 Batch7 repair 的 proposal stage 传入空 loss JSON，M10 默认混合 loss仍包含 refiner、anchor preservation、arbitration、bounded correction、dictionary regularization等项，不能解释为纯 proposal 实验。本任务必须显式实现并验证配置中的每个 stage loss。

训练前必须生成：

```text
results/20260722_srr_batch7_minimal_pathology_decomposition/resolved_stage_loss_weights.csv
results/20260722_srr_batch7_minimal_pathology_decomposition/loss_specific_gradient_matrix.csv
```

硬门：

- 四个实验的 loss 权重必须与 config 完全一致；
- 空 `{}` loss config 必须被 validator 拒绝；
- refiner、final pathology、source arbiter、production gate、branch arbitration、correction opportunity、bounded correction、refiner effect、semantic negative memory 和未授权的 generic dictionary loss 必须为零；
- 每个非零 loss 必须单独 backward，梯度只能到达声明的目标病种模块；
- 不得再用 proposal logits 均值 backward 代替 loss authority；
- resolved loss 或梯度矩阵不合格时不得提交训练。

### 2. 补齐 anchor-free discovery 覆盖

必须在固定病例类别上检查 discovery：

```text
一个 LGE-only scar-positive validation case
一个 T2-present edema-positive validation case
一个 CenterC complete tri-modal validation case
```

病例由脚本按 split 和 metadata 确定性选择，并将 exact case IDs 写入 `anchor_free_discovery_coverage.csv`。每个病例必须验证 discovery 不随 confirmation anchor context 改变，confirmation 会改变；edema 检查必须真正发生在 T2-present 病例上。

### 3. 运行四个匹配实验

严格独立运行：

```text
scar_minimal
scar_dictionary
edema_minimal
edema_dictionary
```

每个从相同 source checkpoint 开始，400 optimizer steps，在 200/400 对全部 44 例评价。四个实验必须使用相同 seed、病例序列、patch centers、optimizer、步数、评价和 decode；dictionary pair只允许 dictionary/prototype-map开关不同。

Minimal 必须关闭 spatial dictionary、prototype maps 和 semantic negative memory。Dictionary variant只允许增加 real prototype maps和M10 spatial dictionary，semantic category memory仍关闭。

Scar 和 edema 必须分别采样、分别训练、分别判断。Edema 训练只使用 T2-present监督；no-T2 edema整条链保持严格零。

### 4. 终态必须删除或保留，而不是继续完善

按 config 的门分别决定：

```text
scar_minimal: RETAIN | RETIRE
scar_dictionary: RETAIN | RETIRE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_dictionary: RETAIN | RETIRE | NOT_APPLICABLE
```

规则：

- minimal positive-case Dice `>=+0.003` 且安全门通过才 RETAIN；
- minimal 失败则该病种 proposal在本挑战赛 RETIRE，dictionary为 NOT_APPLICABLE；
- dictionary相对 minimal额外 Dice `>=+0.001` 且安全不恶化才 RETAIN，否则 RETIRE；
- scar minimal失败后，不得继续 scar dictionary/refiner/arbiter/gate repair；
- edema minimal失败后，不得继续 edema dictionary/refiner/arbiter/gate repair；
- 不得用 scar/edema mean掩盖单病种失败。

### 5. Controller 主动修复边界

以下属于同范围问题，必须退回 Executor 修复并重跑，不得交给用户：

```text
loss 权重未解析或与 config 不一致
gradient authority 使用错误标量
冻结/训练组不符
四实验初始化或采样不匹配
minimal 仍消费 dictionary/memory
semantic memory 意外进入正式训练
T2/no-T2 语义错误
Slurm wrapper、Python、hash、split、decode、aggregation错误
validator只检查文件存在
CURRENT/wiki/fingerprint未更新
```

只有需要改变四实验矩阵、400步预算、数据范围、外部资源许可、backbone或科学阈值时，才停止交给 Planner/用户。

### 6. 完成边界

Controller 必须负责所有 jobs 到 terminal accounting，完成 post-completion aggregation、strict validator、known-bad、mapper final、wiki/CURRENT/fingerprint和本地轻量 commit。提交、pending、running、某一实验完成或 validator文件存在均不是任务完成。

不得启动 refiner、source arbiter、production gate、Batch8、fold expansion、Cine、validation upload或 hosted claim。

Controller report 首段必须用自然中文说明：哪种最小机制有独立价值，dictionary是否增加价值，哪些组件已正式删除。结尾必须包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
scar_minimal_decision:
scar_dictionary_decision:
edema_minimal_decision:
edema_dictionary_decision:
operational_completion_status:
experiment_adequacy_decision:
validators_passed:
all_jobs_terminal:
aggregation_complete:
git_commit_decision:
git_push_decision:
blocked_actions:
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

`VERIFIED_COMPLETE`只表示本分解合同完成，不自动授权后续训练或科学完成。

## Executor Worker Contract

Executor 只能按 executor plan 当前 wave 工作，必须返回真实 diff、命令、resolved loss、梯度、runtime、job ID、预测和聚合证据。不得改变科学矩阵，不得用旧 Batch7 packet替代新结果，不得自行宣布整个任务完成。

## Mapper Contract

Mapper 必须检查四个 variant 的实际数据流、loss、trainable groups、dictionary开关和 final output effect，并在终态更新 wiki/COMPONENTS/architecture fingerprint。Mapper不决定路线晋级。