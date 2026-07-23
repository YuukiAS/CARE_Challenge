# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 当前状态

```text
state_id: care_myops_batch9_exposed_issues_repair_ready_20260723
round_id: post_round04_main_only
state_updated_date: 2026-07-23
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: CARE_MMRD_BATCH9_EXPOSED_ISSUES_REPAIR
batch7_operational_status: SIX_MATCHED_RUNS_COMPLETE
batch7_scientific_packet_status: INCOMPLETE_BR2_SIP_MECHANISM_CLOSURE
batch8_status: SUPERSEDED_UNEXECUTED_DIAGNOSTIC_CONTRACT
batch9_status: COMPLETE_NO_USABLE_SIGNAL_REPAIR_AUTHORIZED
batch9_repair_status: READY_FOR_CONTROLLER
next_required_action: RUN_BATCH9_EXPOSED_ISSUES_REPAIR
controller_is_coordinator: true
planning_review_required: false
review_required: false
batch8_authorized: false
batch9_authorized: true
batch9_repair_authorized: true
batch10_authorized: false
br2_lite_authorized: false
sip_training_authorized: false
proposal_refiner_training_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
validation_upload_authorized: false
hosted_metric_claim_authorized: false
route_promotion_authorized: false
nnunet_anchor_authorized: false
baseline_fallback_authorized: false
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
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
```

从旧图保留的是科学原则，而不是旧类：模态特异编码、只消费已观测模态、anatomy-first、scar/edema病种分治和小病灶保护。Batch 9 repair 保持 CARE-MMRD 直接分割架构，不恢复 prototype/memory/proposal/refiner/gate 长链，也不接入 nnU-Net anchor。

## 当前唯一授权任务：Batch 9 暴露问题修复

```text
task_key: 20260723_care_myops_batch9_exposed_issues_repair
status: READY_FOR_CONTROLLER
result_root: results/20260723_care_myops_batch9_exposed_issues_repair
controller_task: prompts/tasks/20260723_care_myops_batch9_exposed_issues_repair_controller.md
executor_plan: prompts/tasks/20260723_care_myops_batch9_exposed_issues_repair_executor_plan.yaml
config: configs/care_mm/batch9_exposed_issues_repair.yaml
planner_decision: results/srr_production/code_maturity/batch9_exposed_issues_repair_planner_decision_20260723.md
architecture_change: false
```

这不是 Batch 10，也不是接回 nnU-Net。`CAREMMReliableDistillResEnc` 的 forward、三模态独立 stem、availability hard mask、anatomy/scar/edema 分头和可靠标签边界保持不变。标准 nnU-Net 只允许作为同划分评价基线；禁止加载其 logits、checkpoint、预测或作为 fallback。

本任务只修复已暴露的问题：

```text
masked loss按真实有效体素归一化
直接训练与continuation使用显式多项式学习率衰减
scar/可靠edema/anatomy/background平衡采样
no-T2在argmax前hard mask edema类
每25 epoch固定44例验证与selected checkpoint reload
真实known-bad错误注入
逐seed fail-closed gate
Slurm/aggregation/validator驱动的真实finalizer receipts
```

两个 repaired direct seed 均通过空预测、no-T2 安全和同 seed 改善门后，才允许执行 teacher/control/distill continuation。不得用跨 seed 平均掩盖任一 seed 或病种失败。

## 方法重选历史

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

## 原 Batch 9 任务与终态

原任务：

```text
task_key: 20260722_care_myops_batch9_reliable_label_distillation
result_root: results/20260722_care_myops_batch9_reliable_label_distillation
terminal_token: BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER
controller_verification_decision: VERIFIED_COMPLETE
```

原 Batch 9 完成了两个 seed 的 direct/teacher/control/distill 运行，但出现直接主干显著低于基线、continuation 阳性空预测、跨 seed 不稳定和巨量远端假阳性。Planner 进一步审计确认，原 packet 还暴露出 loss 体素归一化、恒定高学习率 continuation、固定类优先采样、no-T2 decode、周期性验证、known-bad 与 per-seed final gate 缺陷。因此原终态只作为当前实现不可用的证据，不作为干净科学否定。

## Batch 9 模型边界

数据流保持：

```text
[LGE,T2,C0] + availability
-> 3 independent stems, 8 channels each
-> hard mask immediately after stem
-> concatenate 24 features + 3 availability channels
-> ResidualEncoderUNet M-level feature backbone
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

No-T2病例不得参与 edema segmentation、distillation 或 consistency 监督。Repair 后 inference/evaluation 必须在 argmax 前 hard mask class 4，预测 edema 体素精确为0。Center不得进入network tensor、normalization、router或validation inference。

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

No-T2不得作为edema negative。

## Repair 训练矩阵

固定seeds：

```text
20260723
20260724
```

每seed：

```text
repaired student_direct_reliable: 500 epochs x 250 = 125000 steps
teacher_full_view: 100 epochs x 250 = 25000 steps, gated
student_moddrop_control: 100 epochs x 250 = 25000 steps, gated
student_reliable_distill: 100 epochs x 250 = 25000 steps, gated
```

Direct 初始学习率 0.01，使用 polynomial decay。Continuation 从 repaired direct selected checkpoint warm-start，初始学习率 0.001，使用 polynomial decay。每25 epoch固定评价44例并保存 checkpoint；选择规则以两个病种的最低 Dice、平均 Dice 和正例 HD95 词典序决定，禁止固定只选 epoch500。

## Slurm

```text
seed20260723 -> htzhulab
seed20260724 -> a100-gpu
python -> /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
training dependencies -> afterok
finalizer/accounting -> afterany all attempts
```

V100只在完全相同模型、patch、batch、AMP、预算和采样语义通过preflight时允许fallback。Submitted/pending/running不是完成。

## 评价与终态

每个 selected checkpoint reload 后评价44例，报告 scar/edema Dice、HD95、precision、recall、components、remote-FP、volume ratio、empty rate、changed voxels、help/harm以及完整三模态、CenterB、CenterC、LGE-only、LGE+C0等分组。

Repair Controller 必须按每个 seed 独立判断。任一 seed 的任一病种出现 GT-positive 空预测、no-T2 edema 非零、相对原 Batch 9 direct 未改善，均阻止 continuation。任一 distill seed 相对 matched control 下降也必须明确失败，不能用跨 seed 平均覆盖。

## 未授权

```text
Batch8 runtime
nnU-Net anchor/logits/checkpoint/prediction fallback
旧SRR forward/loss
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

Controller的`VERIFIED_COMPLETE`只表示本 repair 合同完成，下一步返回Planner。
