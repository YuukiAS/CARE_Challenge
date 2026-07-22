# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 当前状态

```text
state_id: care_myops_batch9_reliable_label_distillation_ready_20260722
round_id: post_round04_main_only
state_updated_date: 2026-07-22
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: CARE_MyoPS_reliable_label_distillation_direct_segmentation
batch7_operational_status: SIX_MATCHED_RUNS_COMPLETE
batch7_scientific_packet_status: INCOMPLETE_BR2_SIP_MECHANISM_CLOSURE
batch8_status: SUPERSEDED_UNEXECUTED_DIAGNOSTIC_CONTRACT
batch9_status: READY_FOR_CONTROLLER
next_required_action: RUN_BATCH9_RELIABLE_LABEL_DISTILLATION_MAINLINE
controller_is_coordinator: true
planning_review_required: false
review_required: false
batch8_authorized: false
batch9_authorized: true
batch10_authorized: false
br2_lite_authorized: false
sip_training_authorized: false
proposal_refiner_training_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
validation_upload_authorized: false
hosted_metric_claim_authorized: false
route_promotion_authorized: false
```

## 开发边界

只允许在：

```text
/users/a/e/aereinh/CARE
main
```

开发。不得写入 `/overflow/htzhu/CARE` 或历史 Route A/B/C worktree。Route A/B/C 只保留 lineage 和历史证据。

## 图视觉门

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
```

从旧图保留的是科学原则，而不是旧类：模态特异编码、只消费已观测模态、anatomy-first、scar/edema病种分治和小病灶保护。Batch 9 不再实现 prototype/memory/proposal/refiner/gate 长链。

## 方法重选结论

用户提供的 Deep Research 报告建议暂停 Batch 8，改为强主干、可靠标签掩码、完整到不完整蒸馏和病种特异直分割。Planner结合仓库历史后接受主方向，但修正了四点：

```text
不接受1200-1600 step作为强3D主干正式证据
teacher不从少量B/C病例随机初始化
自然缺失病例不生成伪T2或伪edema监督
首轮不同时加入BR2-lite、SIP或refiner
```

权威综合判断：

```text
results/srr_production/code_maturity/batch9_reliable_label_distillation_planner_synthesis_20260722.md
```

## Batch 7 与 Batch 8 状态

Batch 7 的操作证据继续保留：

```text
scar minimal positive Dice delta: -0.0049928620
edema minimal positive Dice delta: +0.0013426793
edema BR2 positive Dice delta: +0.0029631724
edema BR2 minus minimal: +0.0016204931
```

但 Batch 7 的 BR2/SIP 科学闭环不完整：scar BR2清空、SIP/no-SIP预测完全相同、训练后系数没有真实导出、终态仍含静态/PENDING证据、validator未检查语义。

Batch 8 文件保留：

```text
results/srr_production/code_maturity/batch8_clean_edema_br2_planner_decision_20260722.md
docs/plans/laneB_round04_active_srr_batch8_clean_edema_br2_confirmation_execution.md
configs/srr_production/myops_batch8_clean_edema_br2.yaml
prompts/tasks/20260722_srr_batch8_clean_edema_br2_controller.md
prompts/tasks/20260722_srr_batch8_clean_edema_br2_executor_plan.yaml
```

其状态固定为：

```text
SUPERSEDED_UNEXECUTED_DIAGNOSTIC_CONTRACT
formal_authority: false
runtime_authorized: false
```

不得删除这些历史计划，也不得启动其Controller。

## Batch 9 唯一任务

```text
BATCH9_RELIABLE_LABEL_DISTILLATION_DIRECT_SEGMENTATION
```

权威文件顺序：

```text
1. results/srr_production/code_maturity/batch9_reliable_label_distillation_planner_synthesis_20260722.md
2. docs/plans/laneB_round04_active_srr_batch9_reliable_label_distillation_execution.md
3. configs/care_mm/batch9_reliable_label_distillation.yaml
4. prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_controller.md
5. prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_executor_plan.yaml
6. results/metrics/nnUNet.md
```

任务路径：

```text
task_key: 20260722_care_myops_batch9_reliable_label_distillation
result_root: results/20260722_care_myops_batch9_reliable_label_distillation
```

## Batch 9 模型

必须新增：

```text
src/care_myocardium/models/care_mm_reliable_distill.py
CAREMMReliableDistillResEnc
src/care_myocardium/losses/care_mm_losses.py
src/care_myocardium/training/nnUNetTrainerCAREMMReliableDistill.py
```

数据流：

```text
[LGE,T2,C0] + availability
-> 3 independent stems, 8 channels each
-> hard mask immediately after stem
-> concatenate 24 features + 3 availability channels
-> official nnU-Net v2 ResidualEncoderUNet M-level backbone
-> shared decoder feature
-> 4-class anatomy head
-> scar residual head
-> edema residual head
-> direct six-class logits
-> argmax
```

六类logits：

```text
[background, myocardium, LV, RV, myocardium+edema, myocardium+scar]
```

No-T2时edema logit为-20。Center不得进入network tensor、normalization、router或validation inference。

旧组件调用计数必须为0：

```text
SRRProposeRefineMyoPS
ProposalDictionary
M10TwoPassSpatialDictionary
M10CrossFittedPrototypeMemory
prototype/semantic memory
refiner
source arbiter
branch arbitration
bounded anchor correction
production gate
legacy Pattern-SIP
```

## 可靠监督

```text
anatomy: all valid labels, pathology remap to myocardium
scar: metadata-scar-reliable cases
edema: T2-present and metadata-edema-reliable cases only
```

No-T2病例的edema segmentation、distillation和consistency supervised voxel count必须为0。No-T2不得作为edema negative。

## 训练矩阵

固定seeds：

```text
20260723
20260724
```

每seed：

```text
student_direct_reliable: 500 epochs x 250 = 125000 steps
teacher_full_view: 100 epochs x 250 = 25000 steps
student_moddrop_control: 100 epochs x 250 = 25000 steps
student_reliable_distill: 100 epochs x 250 = 25000 steps
```

Teacher从同seed direct epoch500复制，不从头训练；只在天然完整三模态可靠训练病例上fine-tune。

Moddrop control与distill从同一student checkpoint开始，使用相同病例、patch、student mask、augmentation、optimizer、teacher forward和预算，唯一差异是distillation loss权重。

结构化student view：

```text
full -> full 0.50 / LGE+C0 0.25 / LGE-only 0.25
LGE+C0 -> LGE+C0 0.75 / LGE-only 0.25
LGE-only -> LGE-only 1.00
```

Distillation只在天然完整病例上启用。自然缺失病例不得获得伪T2或伪edema监督。

## Loss

```text
loss_anatomy_ce_dice: 1.0
loss_scar_bce_dice: 1.0
loss_edema_bce_dice_reliable_only: 1.0
loss_moddrop_consistency: 0.1 in control/distill
loss_distill_logits: 0.5 in distill only
loss_distill_feature: 0.1 in distill only
loss_distill_anatomy: 0.1 in distill only
temperature: 2.0
teacher_confidence_threshold: 0.60
```

每个非零loss必须来自实际runtime resolved contract、进入total并单独backward到授权参数。

## Slurm

```text
seed20260723 -> htzhulab
seed20260724 -> a100-gpu
python -> /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
training dependencies -> afterok
finalizer/accounting -> afterany all attempts
```

V100只在完全相同模型、patch、batch、AMP、预算和采样语义通过preflight时允许fallback。Submitted/pending/running不是完成。

## 训练前硬门

必须通过：

```text
runtime center/modality/label inventory
clean import graph and legacy call count zero
official ResEnc environment contract
availability hard-mask checks
reliable supervision mask checks
resolved loss and loss-gradient authority
full/LGE+C0/LGE-only real-case fixed overfit
checkpoint roundtrip
semantic known-bad fixtures
```

Fixed overfit 100 steps、formal credit 0，不能替代正式500/100 epoch运行。

## 评价与终态

每个selected checkpoint reload后评价44例，报告scar/edema Dice、HD95、precision、recall、components、remote-FP、volume ratio、empty rate、changed voxels、help/harm及：

```text
positive-GT
all cases
complete-trimodal
CenterB
CenterC
LGE-only
LGE+C0
small/large scar
low/high baseline
```

本地B/C只能作为CenterD代理，不得声称已证明unseen-center泛化。

终态只允许：

```text
BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER
BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER
BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER
```

## 未授权

```text
Batch8 runtime
BR2-lite
SIP
prototype/memory
proposal/refiner
source arbiter/production gate
Batch10
fold expansion
Cine
external data/pretrained weights
validation packaging/upload
hosted metric claim
route promotion
final scientific stop
```

Controller的`VERIFIED_COMPLETE`只表示Batch 9合同完成，下一步返回Planner。