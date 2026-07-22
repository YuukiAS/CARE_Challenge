---
task_key: 20260722_srr_batch7_minimal_pathology_decomposition
task_kind: scientific_milestone
task_type: final_minimal_proposal_br2_sip_decomposition
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
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: planner_only
experiment_adequacy_gate: explicit_loss_authority_six_matched_runs_and_br2_sip_ablation
scientific_completion_gate: planner_only
blocked_after_diagnostic_publication: Batch8,refiner,source_arbiter,production_gate,fold_expansion,Cine,validation_upload,hosted_claim
---

## Execution Contract

本任务不是继续维护当前 M10 复杂 dictionary，也不是放弃 R2/BR2 论文思想。它必须把此前四组“minimal vs prototype/spatial dictionary”实验修订为六组：普通 proposal、轻量 BR2 representer dictionary、同一 BR2 dictionary 加正式 SIP。当前 16-slot spatial dictionary、prototype maps 和 semantic negative memory 不得进入正式比较。

开始前同步 `main`、绑定最新远端 SHA，并读取：

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

固定 checkpoint SHA256：

```text
d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
```

## Controller Prompt

你是 coordinator 和验收负责人。必须持续监督 Executor，检查真实 diff、loss、SIP公式、representer参数、availability mask、匹配初始化、Slurm、预测、聚合、validator、CURRENT/wiki/fingerprint；同范围问题必须立即修复和重跑，不能只记录问题后退出。

### 1. 先区分论文 SIP 与历史启发式 loss

当前代码中的：

```text
semantic_retrieval_regularization
pattern_sip_integrativeness_loss
```

不得作为论文 SIP。六个正式实验中它们必须精确为零，并标记 `legacy_heuristic_not_paper_sip`。必须新增真正作用于 source-specific learner coefficients 的：

```text
loss_br2_source_l1_sparsity
loss_br2_selective_integration_penalty
```

source 只能由 availability pattern 定义：LGE-only、LGE+C0、LGE+T2+C0；center只能报告，不能输入 router。SIP 必须按 config 的 $\widetilde\gamma_d$ 和 $P_{SIP}$ 公式实现，$|O_d|\le1$ 的 representer排除。

### 2. 轻量 BR2 dictionary 必须真实且最小

只允许以下 representers：shared anatomy、LGE、C0、T2、LGE-C0、LGE-T2、T2-C0。每个必须有独立参数和输出，禁止同一 tensor 重命名。缺少所需模态的模块必须在 normalization 前 hard-mask，最终权重严格为零。

BR2 router必须分别输出：

```text
source-level learner coefficients
image-conditioned residual
final retrieval weights
availability valid mask
```

Minimal variant不得实例化或消费 BR2参数。`br2_no_sip` 与 `br2_sip` 除 SIP weight外必须结构、初始化、数据和命令完全一致。禁止 prototype bank、prototype maps、semantic memory、M10 16-slot spatial dictionary。

### 3. Loss authority 硬门

训练前必须生成：

```text
resolved_stage_loss_weights.csv
loss_specific_gradient_matrix.csv
sip_formula_unit_tests.json
sip_weight_calibration.csv
representer_parameter_manifest.csv
availability_mask_checks.csv
```

硬门：

- 空 `{}` loss config必须失败；
- refiner、final pathology、arbiter、production gate、branch arbitration、bounded correction、prototype、memory、generic load balance、legacy semantic regularization、legacy Pattern-SIP全部为零；
- 每个非零 loss单独 backward，梯度只能进入目标病种和授权轻量 BR2模块；
- 不得对 logits均值 backward代替正式 loss；
- SIP候选权重只按 config 的固定 gradient-ratio规则选择，Executor不得主观选择；
- 旧 Pattern-SIP改名冒充、batch-average gate代理、center-conditioned router、重复 representer、未 hard-mask均必须作为 known-bad被拒绝。

任何一项不通过，不得提交训练。

### 4. 运行六个匹配实验

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

每个400 optimizer steps，200/400评价全部44例。同病种三组必须共享 checkpoint、seed、病例序列、patch centers、optimizer、预算、decode和共有模块初始化；两个BR2组还必须共享全部BR2参数初始化。

Scar必须采样scar-positive和anchor-error区域。Edema只使用T2-present监督；no-T2 edema全链严格为零。Anchor-free discovery检查必须覆盖LGE-only scar、T2-present edema和CenterC complete tri-modal。

### 5. 最终必须给出六个决定

```text
scar_minimal: RETAIN | RETIRE
scar_br2: RETAIN | RETIRE | NOT_APPLICABLE
scar_sip: RETAIN | REMOVE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_br2: RETAIN | RETIRE | NOT_APPLICABLE
edema_sip: RETAIN | REMOVE | NOT_APPLICABLE
```

规则：

- minimal达到`+0.003`并通过安全门才保留；
- BR2相对minimal额外`+0.001`且安全不恶化才保留；
- SIP相对no-SIP额外`+0.0005`，或Dice下降不超过`0.0005`且HD95/remote-FP改善至少2%，help/harm不恶化，才保留；
- SIP失败只删除SIP，不自动删除有效BR2；
- Scar minimal仍为负时立即停止scar SRR，不得用BR2/refiner/gate补救；
- 不得把“当前适配失败”写成否定原论文。

### 6. Controller主动修复边界

以下属于同范围问题，必须退回Executor修复并重跑，不得交给用户：

```text
旧M10 dictionary或prototype/memory进入正式路径
legacy Pattern-SIP非零或冒充新SIP
SIP公式、source集合或mask错误
center进入router
representer参数重复或只是feature别名
minimal暗中消费BR2
no-SIP与SIP初始化/数据不匹配
loss未解析或梯度流向错误
T2/no-T2语义错误
Slurm、hash、split、decode、aggregation错误
validator只检查文件存在
CURRENT/wiki/fingerprint未更新
```

只有需要改变六实验矩阵、400步预算、数据范围、backbone或科学门槛时，才停止交给Planner/用户。

### 7. 完成边界

Controller负责所有jobs到terminal accounting，完成post-completion aggregation、strict validator、known-bad、mapper final、wiki/CURRENT/fingerprint和本地轻量commit。不得启动refiner、arbiter、production gate、Batch8、fold expansion、Cine、上传或hosted claim。

Controller report首段必须用自然中文说明：minimal是否有效、轻量BR2是否增加价值、SIP是否真实有益、当前复杂dictionary哪些应删除。结尾必须包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
scar_minimal_decision:
scar_br2_decision:
scar_sip_decision:
edema_minimal_decision:
edema_br2_decision:
edema_sip_decision:
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

`VERIFIED_COMPLETE`只表示本合同完成，不自动授权后续训练或论文结论。

## Executor Worker Contract

Executor只能按executor plan当前wave工作，必须返回真实diff、命令、resolved loss、SIP公式测试、参数manifest、runtime、job ID、预测和聚合证据。不得更改科学矩阵，不得自行宣布整体完成。

## Mapper Contract

Mapper必须检查minimal与轻量BR2的真实数据流、source coefficients、availability mask、SIP、loss、trainable groups和final output effect，并更新wiki/COMPONENTS/architecture fingerprint。Mapper不决定路线晋级。