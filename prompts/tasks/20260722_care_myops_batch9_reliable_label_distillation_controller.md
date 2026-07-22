---
task_key: 20260722_care_myops_batch9_reliable_label_distillation
task_kind: scientific_milestone
task_type: batch9_reliable_label_distillation_mainline
task_status: READY_FOR_CONTROLLER
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
risk_level: high
route_change: true
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
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
blocked_after_completion: Batch8,BR2_lite,SIP,prototype,memory,proposal,refiner,arbiter,production_gate,Batch10,fold_expansion,Cine,validation_upload,hosted_claim,route_promotion
---

## Execution Contract

本任务正式 supersede 尚未执行的 Batch 8，将 CARE MyoPS 主线从 nnU-Net anchor 上的 clean edema correction 切换为直接分割。唯一目标是实现并公平评价：

```text
强 nnU-Net ResEnc M 级主干
+ modality-specific stems
+ availability hard masking
+ anatomy/scar/edema病种特异输出
+ reliable edema supervision
+ structured modality dropout
+ complete-view teacher distillation
```

当前标准 nnU-Net只作为评价基线，不进入新模型forward。旧SRR、dictionary、prototype、memory、proposal、refiner、arbiter和gate不得进入本任务。

开始前必须同步远端 `main`、绑定最新SHA并读取：

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
results/srr_production/code_maturity/batch9_reliable_label_distillation_planner_synthesis_20260722.md
docs/plans/laneB_round04_active_srr_batch9_reliable_label_distillation_execution.md
configs/care_mm/batch9_reliable_label_distillation.yaml
prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_executor_plan.yaml
results/metrics/nnUNet.md
```

## Controller Prompt

你是本任务的 coordinator、连续运行负责人和最终操作验收人。必须监督 Executor完成代码、preflight、长训练、terminal accounting、聚合、strict validator、known-bad、Mapper final、wiki/CURRENT/fingerprint和本地轻量commit。普通实现、环境、Slurm、评价和packet问题必须在同一任务内退回Executor修复，不得只记录后退出。

### 1. 先冻结 Batch 9 科学边界

必须在 `controller_context.json` 记录当前SHA、task/config/plan/executor-plan hash、AGENTS/Slurm/Mapper skill hash、Dataset501 split与standard nnU-Net baseline路径。

必须确认：

```text
Batch8未执行且formal authority已撤销
Batch7 runtime只作历史证据
Batch9不加载Batch7 SRR checkpoint
Batch9不以nnU-Net logits作为模型输入或anchor
外部数据和外部预训练权重均禁用
```

发现工作树中已有人启动Batch8时，不得删除runtime；记录并停止Batch8后继续Batch9，前提是没有共享路径冲突。

### 2. 数据与标签语义必须来自运行时审计

不得照抄Deep Research中的中心数量。必须从当前 split、metadata、availability和label inventory生成：

```text
center_modality_label_inventory.csv
reliable_supervision_inventory.csv
fold0_case_manifest.csv
```

逐病例证明：

```text
anatomy监督是否可靠
scar监督是否可靠
edema监督是否可靠
自然availability
center仅作为sampler/诊断字段
```

No-T2病例的 edema segmentation、distillation和consistency supervised voxel count必须精确为0。禁止把无edema标注解释为背景真值。

### 3. 实现一个真正独立的新模型

必须新增：

```text
src/care_myocardium/models/care_mm_reliable_distill.py
CAREMMReliableDistillResEnc
src/care_myocardium/losses/care_mm_losses.py
src/care_myocardium/training/nnUNetTrainerCAREMMReliableDistill.py
```

允许增加必要的dataset/sampler helper，但不得调用旧SRR forward或loss。

模型固定数据流：

```text
3个独立1-channel stem，各输出8 channels
-> stem后立刻availability hard mask
-> 24 feature channels + 3 availability channels
-> official ResidualEncoderUNet M-level backbone
-> shared decoder feature
-> 4-channel anatomy head + scar residual head + edema residual head
-> six-class logits composition
-> argmax
```

必须使用当前环境可验证的官方 `ResidualEncoderUNet` 和 `nnUNetResEncUNetMPlans` 等价配置。禁止为了启动方便换成旧 `build_modality_encoder`、tiny U-Net、普通两层CNN或只包装现有nnU-Net预测。

以下类的import/实例化/forward调用计数必须为0：

```text
SRRProposeRefineMyoPS
ProposalDictionary
M10TwoPassSpatialDictionary
M10CrossFittedPrototypeMemory
CropSoftROIRefinementHead
DifferentiableSoftROIRefinementHead
PathologySourceArbiter
BranchArbitrationGate
BaselinePreservingResidualGate
```

### 4. Output和loss必须解决partial label，而不是伪装成普通六类CE

Anatomy head固定四类：background、healthy myocardium、LV、RV；label 4/5在anatomy target中remap为myocardium。Scar和edema使用独立binary head。六类logits固定为：

```text
[z_bg,z_myo,z_lv,z_rv,z_myo+r_edema,z_myo+r_scar]
```

No-T2时edema logit设为-20，但no-T2病例不得参与edema loss。

只允许config中声明的loss。每个非零loss必须：

1. 出现在实际命令解析后的`resolved_loss_contract.json`；
2. 进入runtime total loss；
3. 单独backward到授权参数；
4. 对禁止参数和不可靠样本梯度为0。

禁止空loss JSON、旧loss alias、config静态复制冒充runtime resolved contract、logits.mean梯度代理。

### 5. Teacher/student设计不得偷换

每个seed先完成`student_direct_reliable` 500 epochs。Teacher必须从同seed direct epoch500 checkpoint复制全部模型参数，再在天然完整三模态且标签可靠的训练病例上fine-tune 100 epochs。禁止teacher从头训练、读取validation GT或使用外部权重。

`student_moddrop_control`与`student_reliable_distill`都从同seed direct epoch500开始，均训练100 epochs，使用相同student batch、patch、student availability mask、augmentation、optimizer和frozen teacher forward。唯一差异是三项distillation loss是否非零。

Distillation仅在天然完整三模态训练病例上启用。Teacher看full view；student看结构化dropout view。自然缺失病例不得接收伪T2、伪edema、teacher edema pseudo-label或“补全后可靠”标签。

### 6. 结构化modality dropout必须显式可追踪

固定概率：

```text
full -> full 0.50 / LGE+C0 0.25 / LGE-only 0.25
LGE+C0 -> LGE+C0 0.75 / LGE-only 0.25
LGE-only -> LGE-only 1.00
```

LGE始终保留。每step保存自然mask、student mask、case、center、patch center、RNG状态。Matched control若manifest hash不同必须fail closed。

### 7. 训练前硬门

必须完成：

```text
clean_model_import_graph.json
legacy_module_call_counters.csv
resenc_environment_contract.json
availability_hard_mask_checks.csv
reliable_supervision_mask_checks.csv
resolved_loss_contract.json
loss_gradient_matrix.csv
fixed_real_case_overfit.json
checkpoint_roundtrip.json
known_bad_report.json
```

Fixed overfit覆盖自然full、LGE+C0、LGE-only各至少一个真实病例，100 steps，formal credit 0。可监督总loss下降至少30%；full病例scar/edema预测非空；no-T2 edema supervised voxel count严格为0。任何硬门不通过不得提交正式训练。

Known-bad必须真实注入并拒绝：

```text
旧SRR类进入import或forward
缺失模态stem非零
center ID进入network tensor或normalization
no-T2进入edema loss/distillation
声明loss未进入total
static config冒充runtime loss contract
matched pair病例/patch/dropout/augmentation不一致
checkpoint未reload
不同variant复用prediction path/hash
空scar/edema预测仍完成
PENDING/PLACEHOLDER/STATIC_INITIAL进入终态
少于合同epoch却写formal complete
```

### 8. 长训练不得缩水

固定两个seed：20260723、20260724。每seed必须完成：

```text
student_direct_reliable: 500 epochs x 250 steps = 125000
teacher_full_view: 100 epochs x 250 steps = 25000
student_moddrop_control: 100 epochs x 250 steps = 25000
student_reliable_distill: 100 epochs x 250 steps = 25000
```

Direct selected checkpoint固定epoch500。其余固定epoch100。所有selected checkpoint必须reload后对44例推理。禁止用early best替代固定终点，禁止把250 epoch中间checkpoint当正式终态。

两个seed流水线可并行：默认seed20260723走htzhulab，seed20260724走a100-gpu；单seed内部training依赖使用afterok。V100只有在不改变模型、patch、batch、AMP、预算和sampling语义时才可fallback。正式wrapper必须使用：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

最终finalizer使用afterany覆盖所有attempt。Submitted、pending、running、awaiting sacct均不是完成。

### 9. 评价必须面向完整三模态和病种差异

每个selected checkpoint评价全部44例，输出独立prediction目录、checkpoint SHA和prediction hashes。必须报告scar/edema Dice、HD95、precision、recall、component、remote-FP、volume ratio、empty rate、changed voxels，以及：

```text
all cases
positive-GT
complete-trimodal
CenterB
CenterC
LGE-only
LGE+C0
small-scar
large-scar
low-baseline
high-baseline
case-wise help/harm
```

本地B/C只是CenterD代理，报告不得写“已证明unseen-center泛化”。

### 10. 机械终态

按config严格判断：

```text
BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER
BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER
BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER
```

不得因为模型复杂、论文故事完整或某指标接近阈值而主观通过。Direct baseline、moddrop和distill三层决定必须分别列出全部gate字段。

### 11. Controller主动修复边界

以下均属于同范围问题，必须退回Executor修复：

```text
官方ResEnc import/plan/build错误
Dataset501 loader或metadata错误
partial-label mask错误
availability hard mask错误
loss/gradient authority错误
teacher初始化/冻结错误
matched manifest不一致
训练epoch或step计数错误
Slurm wrapper/env/path/lock错误
checkpoint reload或prediction hash错误
聚合/validator只查文件不查内容
CURRENT/wiki/fingerprint不一致
```

只有需要改变模型主体、loss公式、两个seed、500+100 epoch预算、数据范围、外部资源许可或科学门槛时，才返回Planner/用户。

### 12. 完成边界

Controller必须负责所有job到terminal accounting、post-completion aggregation、strict validator、known-bad、Mapper final、wiki/CURRENT/fingerprint和本地轻量commit。`controller_report.md`必须先用自然中文解释实际科学含义，再包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
contract_compliance_status:
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
direct_resenc_status:
moddrop_control_status:
reliable_distillation_status:
complete_trimodal_status:
center_b_status:
center_c_status:
partial_label_safety_status:
final_scientific_token:
git_commit_decision:
git_push_decision:
blocked_actions:
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

`VERIFIED_COMPLETE`只代表Batch 9合同完成，不自动授权BR2-lite、SIP、refiner、Batch10、fold expansion、Cine、validation upload或性能主张。

## Executor Worker Contract

Executor只能执行executor plan当前wave。必须返回真实diff、命令、环境、训练曲线、job IDs、checkpoint hashes、独立预测、聚合和validator结果；不得自行缩小网络、epoch、seed、病例、指标或改用旧SRR捷径。Executor不能宣布整体完成。

## Mapper Contract

Mapper必须检查新模型import graph、官方ResEnc配置、availability hard mask、partial-label supervision、teacher/student数据流、loss authority、trainable/frozen组、six-class compose、selected checkpoint final effect和旧SRR禁用状态。终态更新`wiki/COMPONENTS.csv`、`wiki/architecture.yaml`、D2/SVG/PNG与fingerprint；规划态只标为planned，运行证据完成后才能标verified。Mapper不决定下一Batch。