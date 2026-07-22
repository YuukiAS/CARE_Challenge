---
task_key: 20260722_srr_batch8_clean_edema_br2_confirmation
task_kind: scientific_milestone
task_type: batch8_clean_edema_br2_confirmation
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
executor_plan_path: prompts/tasks/20260722_srr_batch8_clean_edema_br2_executor_plan.yaml
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
scientific_completion_gate: planner_only
blocked_after_completion: SIP,refiner,scar_training,Batch9,fold_expansion,Cine,validation_upload,hosted_claim,route_promotion
---

## Execution Contract

本任务是用户显式授权的 Batch 8。它不是继续修完整 SRR，也不是把 Batch 7 的负结论直接继承下来。唯一目标是：先修复 Batch 7 终态机制证据，再用两个独立 seed 公平比较“干净 edema head”与“同一 head 加轻量 BR2”。Scar 训练停止；SIP、refiner、source arbiter、production gate 和旧 M10 dictionary/prototype/memory 全部不进入本批。

开始前必须同步远端 `main`、绑定当前 SHA，并读取：

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
results/srr_production/code_maturity/batch8_clean_edema_br2_planner_decision_20260722.md
docs/plans/laneB_round04_active_srr_batch8_clean_edema_br2_confirmation_execution.md
configs/srr_production/myops_batch8_clean_edema_br2.yaml
prompts/tasks/20260722_srr_batch8_clean_edema_br2_executor_plan.yaml
```

固定 source checkpoint SHA256：

```text
d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
```

## Controller Prompt

你是本任务 coordinator 和最终验收负责人。必须持续监督 Executor，检查真实 git diff、代码调用图、checkpoint 白名单、Batch7 checkpoint 导出、preflight、Slurm、完整体积预测、聚合、strict validator、mapper final、CURRENT/wiki/fingerprint 和本地轻量 commit。同范围问题必须立即退回 Executor 修复并重跑，不得只记录问题后结束。

### 1. 先修复 Batch 7 终态证据

不得接受现有 `VERIFIED_COMPLETE_NEGATIVE_SIGNAL` 作为 BR2/SIP 科学闭环。必须从 Batch7 scar/edema warmup50、step200、step400 checkpoint 真实导出 beta、center deviation、effective beta、representer RMS、projection norm、proposal-logit分位数、预测正体素数、SIP值和梯度。禁止：

```text
新建模型后导出初始参数
STATIC_INITIAL_COEFFICIENTS
PENDING_DETAILED_BETA_EXPORT
PLACEHOLDER
仅复制summary字段
```

必须定位 scar BR2 首次空预测发生在哪个 checkpoint，以及是 proposal、final correction、decode 还是 checkpoint 状态造成。SIP/no-SIP完全相同也必须通过真实 checkpoint 系数和输出差异解释。完成后写 `batch7_packet_supersession.md`，明确原 runtime保留但原科学闭环被 supersede。

### 2. 实现独立 clean model，禁止 flags 伪关闭

必须新增 `src/care_myocardium/models/srr_batch8_clean_edema.py::CleanEdemaBR2Corrector`。禁止实例化完整 `SRRProposeRefineMyoPS` 后仅靠 flags 关闭旧模块。Clean model只能显式持有 source checkpoint 白名单中的冻结主干，以及新 clean head/BR2。

旧模块调用计数必须严格为0：

```text
ProposalDictionary
M10TwoPassSpatialDictionary
M10CrossFittedPrototypeMemory
prototype maps / semantic negative memory
CropSoftROIRefinementHead
DifferentiableSoftROIRefinementHead
PathologySourceArbiter
BranchArbitrationGate
BaselinePreservingResidualGate
production_correction_gate
```

Clean minimal 输入只能是 frozen edema feature、T2 image、frozen anatomy-union probability。Final output只在原始 nnU-Net 六类 logits 的 edema 通道增加 `2*tanh(delta)`，其余通道不变。无T2时 delta、logit变化和label变化必须精确为0。

Clean BR2只允许四个独立 representer：shared anatomy、LGE private、T2 private、LGE-T2 interaction。系数必须为 signed spatially-global scalar；禁止 softmax/simplex/top-k、逐病例beta residual和center进入网络。训练使用CenterB/CenterC beta，验证只使用pooled beta。

### 3. Loss authority 必须独立

不得调用旧 `propref_loss`、M10 expanded total loss或任何旧 alias。只允许 config 中五项 clean loss。每个非零 loss 必须单独 backward，冻结模块、旧模块和未授权模块梯度为0。Resolved loss必须从实际命令/运行解析，而不是从 config 静态复制。

### 4. 训练前硬门

必须完成且通过：

```text
clean_model_import_graph.json
checkpoint_whitelist_load.csv
legacy_module_call_counters.csv
clean_initial_equivalence.json
clean_no_t2_identity.csv
clean_fixed_overfit.json
clean_loss_gradient_matrix.csv
clean_checkpoint_roundtrip.json
clean_known_bad_report.json
```

Fixed overfit必须使用两个真实T2-present edema病例，100步，formal credit 0，loss下降至少30%，最终预测非空，BR2在step25后产生非零delta。任一硬门失败不得提交正式训练。

Known-bad必须真实注入并拒绝：旧ProposalDictionary进入forward、checkpoint白名单外key被消费、静态beta导出、`PENDING`字段、空预测仍标完成、no-T2非零修正、minimal/BR2初始化不等、同seed采样不匹配、validator只检查文件存在。

### 5. 两个seed正式运行

严格运行四组：

```text
edema_clean_minimal_seed20260722
edema_clean_br2_seed20260722
edema_clean_minimal_seed20260723
edema_clean_br2_seed20260723
```

每组800 optimizer steps，200/400/800评价全部44例，step800固定为正式checkpoint并reload后推理。同seed两组必须共享 common-head初始化、中心/病例/patch序列、augmentation、optimizer模板、预算、评价和decode。禁止best-checkpoint挑选。

允许两个独立seed jobs并行提交：seed20260722默认htzhulab，seed20260723默认a100-gpu。两job必须有隔离runtime/prediction/checkpoint/log/lock根目录；一个seed不能替代另一个。正式wrapper必须使用 `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`，先在相同partition做GPU preflight。

所有job必须由durable `afterany` finalizer负责到terminal accounting、post-completion aggregation、strict validator、mapper final和本地轻量commit。Submitted/pending/running/monitor不是完成。

### 6. 评价必须防止再次假闭环

每个seed/variant必须有独立预测目录和checkpoint SHA，并报告：正例Dice、HD95、remote-FP、component、changed voxels、CenterB、CenterC、help/harm、anchor FN recovery、anchor FP suppression、正预测体素数，以及从正式step800 checkpoint导出的beta/projection/representer诊断。

Validator必须拒绝：

```text
任何PENDING/STATIC_INITIAL/PLACEHOLDER字段
BR2预测为空却仍写机制完成
beta文件不是来自selected checkpoint
minimal与BR2复用同一prediction hash
seed间复用checkpoint或sampler manifest
CenterB/CenterC缺失
help/harm、HD95、remote-FP未进入决策
```

### 7. 终态决定

按 config 全部门槛机械判断：

```text
EDEMA_CLEAN_BR2_RETAIN_PENDING_PLANNER
或
RETIRE_SRRMyoPS_PERFORMANCE_LINE_USE_NNUNET
```

Scar固定为：

```text
SCAR_SRR_TRAINING_STOPPED_USE_NNUNET
```

不得自行放宽阈值，也不得因 `+0.0029` 接近门槛而主观通过。终态报告必须先用自然中文解释：信号是否跨seed稳定、是否确实来自BR2、CenterB/C是否都安全、为什么保留或停止。

### 8. Controller主动修复边界

以下属于同范围问题，必须退回Executor修复，不得交给用户：

```text
Batch7 checkpoint导出缺失或静态
scar collapse未定位
clean model仍调用旧模块
checkpoint白名单错误
loss/gradient不符
no-T2不严格identity
fixed overfit未达标
seed/variant初始化或采样不匹配
Slurm wrapper/import/path/lock错误
prediction/checkpoint hash错误
aggregation或validator语义漏洞
CURRENT/wiki/fingerprint未更新
```

只有需要改变模型四representer结构、两个seed、800步预算、数据范围、外部资源许可或科学门槛时，才停止并交给Planner/用户。

### 9. 完成边界

Controller必须负责所有attempt到terminal accounting，完成finalizer、aggregation、strict validator、known-bad、mapper final、wiki/CURRENT/fingerprint和本地轻量commit。Controller report结尾必须包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
contract_compliance_status:
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
batch7_evidence_repair_status:
scar_collapse_diagnosis_status:
edema_clean_minimal_two_seed_status:
edema_clean_br2_two_seed_status:
center_b_safety_status:
center_c_safety_status:
final_scientific_token:
git_commit_decision:
git_push_decision:
blocked_actions:
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

`VERIFIED_COMPLETE`只代表本Batch合同完成，不自动授权SIP、refiner、Batch9、fold expansion、Cine、上传或论文性能主张。

## Executor Worker Contract

Executor只能按executor plan当前wave工作，必须返回真实diff、命令、checkpoint-derived证据、job IDs、预测、聚合和validator结果。不得改变科学矩阵、阈值、seed、预算或模块结构，不得自行宣布整体完成。

## Mapper Contract

Mapper必须检查clean model真实import graph、checkpoint白名单、旧模块调用计数、minimal/BR2数据流、loss、trainable/frozen组、no-T2 identity、selected checkpoint机制导出和final output effect。终态更新wiki/COMPONENTS/architecture fingerprint，旧Batch7科学闭环标为superseded。Mapper不决定下一Batch。