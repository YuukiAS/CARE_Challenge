---
task_key: 20260722_srr_batch7_minimal_pathology_decomposition
task_kind: scientific_milestone
task_type: final_minimal_center_hierarchical_br2_sip_decomposition
controller_mode: coordinator_acceptance_owner
status: READY_FOR_CONTROLLER_COMPREHENSIVE_BR2_AMENDMENT
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
experiment_adequacy_gate: explicit_loss_authority_center_hierarchical_br2_sip_six_matched_runs
scientific_completion_gate: planner_only
blocked_after_diagnostic_publication: Batch8,refiner,source_arbiter,production_gate,fold_expansion,Cine,validation_upload,hosted_claim
---

## Execution Contract

本任务不是继续维护当前 M10 复杂 dictionary，也不是放弃 R2/BR2 论文思想。它只做一次最终、可证伪的六组实验：普通 proposal、可部署的轻量中心分层 BR2、以及同一 BR2 加正式 SIP。当前 16-slot spatial dictionary、prototype maps、semantic negative memory、refiner、source arbiter 和 production-gate 学习不得进入正式比较。

开始前必须同步远端 `main`、绑定最新 SHA，并按顺序读取：

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
results/srr_production/code_maturity/batch7_br2_sip_comprehensive_architecture_audit_20260722.md
docs/plans/laneB_round04_active_srr_batch7_minimal_pathology_decomposition_execution.md
configs/srr_production/myops_batch7_minimal_decomposition.yaml
prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml
```

固定 checkpoint SHA256：

```text
d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
```

## Controller Prompt

你是本任务的 coordinator 和验收负责人。必须持续监督 Executor，逐 wave 检查真实 diff、source 定义、representer、系数、SIP、loss、采样、Slurm、预测、聚合、validator、CURRENT/wiki/fingerprint。同范围实现、测试、证据和运行问题必须立即退回 Executor 修复并重跑，不能只记录问题后退出。

### 1. Source 语义必须正确

论文中的 source 在本任务中定义为训练采集中心，不是 availability pattern。必须从真实 metadata 重建中心—模态 inventory；availability 只是该中心的 observation set。

Center ID 只允许用于：

```text
训练期 source coefficient 索引
source-balanced sampling
分中心诊断
```

Center one-hot、名称、编号或统计量不得进入 encoder、representer、proposal、router 或任何图像网络输入。正式 44 例验证和部署只能使用 availability-pattern pooled coefficient，禁止读取 center-specific coefficient。

若实际 fold0 metadata 与 config 的中心—模态关系不一致，训练前阻塞并返回 Planner，不得静默改 source。

### 2. 轻量 BR2 必须可解释且可部署

只允许 7 个独立 representers：shared anatomy、LGE、C0、T2、LGE-C0、LGE-T2、T2-C0。它们只接在 proposal 使用的全分辨率 pathology feature 上，不得复用 M10 16-slot dictionary。

每个 representer 必须：

- 独立参数化，禁止 tensor 别名或复制同一模块；
- private 只读取本模态；interaction 读取两模态归一化特征、乘积和绝对差；
- 末层与病种投影零初始化，使 BR2 初始行为等于 minimal；
- 在乘 learner coefficient 前固定为 per-case RMS=1；
- 缺失所需模态时 effective coefficient 和贡献严格为零。

### 3. Learner coefficient 不能退化成普通路由器

正式系数必须是病种特异、空间全局、可正可负的标量。禁止 softmax、simplex、top-k 归一、和为 1 约束以及 image-conditioned coefficient residual。

必须实现：

```text
beta_center = beta_pattern + center_deviation
同 availability pattern 内 center_deviation 和为零
center deviation 使用 L2 shrinkage
训练 forward 使用 beta_center
验证/部署 forward 只使用 beta_pattern
```

必须分别输出 `beta_pattern`、训练诊断用 `beta_center`、`center_deviation`、availability mask 和 effective masked beta。

### 4. SIP 必须真正作用于受监督 source coefficient

旧 `semantic_retrieval_regularization` 和 `pattern_sip_integrativeness_loss` 六个正式实验中必须精确为零，并标记为历史启发式，不得改名冒充论文 SIP。

新增：

```text
loss_br2_source_l1_sparsity
loss_br2_center_deviation_shrinkage
loss_br2_selective_integration_penalty
```

SIP 的 source 集合是同时观察到所需模态并拥有可靠目标病种监督的训练中心。No-T2 中心不得建立 edema coefficient，不得进入 edema SIP、edema loss或edema negative。`|O|<=1` 的 representer必须排除。

Representer RMS 固定后才允许使用 `tau=0.10`。SIP 权重只能按 config 的固定、train-only、center-balanced gradient-ratio规则从候选中选择，Executor不得主观选择。

### 5. Source-balanced 训练和匹配实验

Batch size为1，正式 sampler必须：

```text
均匀选择目标病种合格中心
-> 中心内均匀选择病例
-> 选择病灶或 anchor-error patch
```

必须保存逐步 sampler manifest；不同中心采样次数偏差不得超过 config。

严格运行：

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

每组 400 optimizer steps，200/400 对全部44例评价。同病种三组共享 checkpoint、seed、source-balanced病例序列、patch centers、optimizer、预算、decode和共有模块初始化。两个BR2组还必须共享全部BR2初始化及第50步 warmup状态，唯一差异只能是 SIP weight。

BR2训练顺序固定：1-50步冻结representer；51-350步交替更新 coefficient block 与 representer/pathology block；351-400步冻结representer做系数校准。不得自行改成全部模块同时更新。

### 6. Loss authority 硬门

训练前必须生成并验收：

```text
center_modality_inventory.csv
pathology_source_eligibility.csv
source_balanced_sampler_manifest.csv
resolved_stage_loss_weights.csv
loss_specific_gradient_matrix.csv
sip_formula_unit_tests.json
sip_weight_calibration.csv
representer_parameter_manifest.csv
representer_scale_checks.csv
beta_hierarchy_checks.csv
availability_mask_checks.csv
```

空 `{}` loss config、历史混合M10 loss、另一病种loss、refiner/final/gate/arbiter/prototype/memory/generic dictionary loss或旧Pattern-SIP非零，必须使 validator失败。每个非零loss必须单独 backward，梯度只能进入目标病种和授权BR2模块；禁止用logits均值代替loss验收。

### 7. Known-bad 必须真实拒绝

以下必须注入真实错误对象并由生产validator非零退出：

```text
availability pattern被当作唯一训练source
center进入图像网络
验证使用center-specific beta
softmax/simplex或per-image coefficient residual
representer输出未做RMS归一
representer放大而beta缩小以绕过L1/SIP
重复representer或tensor别名
缺失模态representer权重非零
no-T2中心进入edema beta/SIP/loss
旧Pattern-SIP冒充新SIP
no-SIP与SIP初始化、warmup或采样不一致
validator只检查文件存在
```

### 8. 评价必须针对挑战赛部署条件

除正例Dice、HD95、远端假阳性和help/harm外，必须报告：

```text
complete-trimodal subgroup
CenterB / CenterC及全部有正例中心
worst-positive-center Dice
proposal precision / recall / lesion-wise recall
anchor-missed recovery / false-positive suppression
beta、center deviation、integrativeness和representer RMS
source-balanced sampling counts
```

Minimal、BR2、SIP均必须通过 complete-trimodal不下降门；BR2/SIP还不得让worst-positive-center下降超过config阈值。不得只用总体均值掩盖CenterC或完整三模态伤害。

### 9. 终态决定与主张边界

必须返回：

```text
scar_minimal: RETAIN | RETIRE
scar_br2: RETAIN | RETIRE | NOT_APPLICABLE
scar_sip: RETAIN | REMOVE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_br2: RETAIN | RETIRE | NOT_APPLICABLE
edema_sip: RETAIN | REMOVE | NOT_APPLICABLE
```

Scar minimal仍为负时停止scar SRR，不得用BR2/refiner/gate补救。SIP失败只删除SIP，不自动删除有效BR2。

任何文稿只能称为 `R2/BR2/SIP-inspired medical imaging adaptation`。禁止声称原论文理论界已覆盖3D分割，禁止声称已因果分离center与missingness，禁止在未通过消融门时声称SIP带来性能提升。

### 10. 主动修复与完成边界

普通实现、测试、loss、sampling、Slurm、hash、split、decode、聚合、validator、receipt和wiki问题必须在本任务内修复。只有需要改变六实验矩阵、400步预算、数据范围、backbone或科学阈值时，才停止并交给Planner/用户。

Controller负责所有jobs到terminal accounting、post-completion aggregation、strict validator、known-bad、mapper final、CURRENT/wiki/fingerprint和本地轻量commit。不得启动refiner、arbiter、production gate、Batch8、fold expansion、Cine、上传或hosted claim。

Controller report首段必须用自然中文说明：minimal是否有效、轻量BR2是否增加价值、SIP是否真实有益、哪些旧组件应删除。结尾必须包含：

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

Executor只能按executor plan当前wave工作，必须返回真实diff、命令、source inventory、resolved loss、SIP公式测试、参数manifest、sampler manifest、runtime、job ID、预测和聚合证据。不得改变科学矩阵，不得自行宣布整体完成。

## Mapper Contract

Mapper必须检查minimal与轻量BR2的真实数据流、中心/availability source语义、signed coefficients、representer尺度、SIP、loss、trainable groups和final output effect，并更新wiki/COMPONENTS/architecture fingerprint。Mapper不决定路线晋级。