# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 当前状态

```text
state_id: care_myops_srr_cascade_submission_rescue_ready_20260724
round_id: post_round04_main_only_submission_rescue
state_updated_date: 2026-07-24
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: CARE_SRR_CASCADE_SUBMISSION_RESCUE
batch10_status: TERMINAL_STOP_RETAINED_AS_HISTORY
submission_rescue_status: READY_FOR_CONTROLLER
next_required_action: START_SRR_CASCADE_SUBMISSION_RESCUE_CONTROLLER
controller_is_coordinator: true
planning_review_required: false
review_required: false
validation_packaging_authorized: conditional_local_only
validation_upload_authorized: false
docker_local_build_authorized: conditional
docker_upload_authorized: false
hosted_metric_claim_authorized: false
fold_expansion_authorized: false
new_cine_training_authorized: false
route_promotion_authorized: false
```

## 为什么可以在 Batch10 终止后重开

Batch10 对 CARE-MMRD 直接六类分割路线的终止判断继续有效。用户于 2026-07-24 明确授权一条新的 submission-rescue 主线，改变的是模型边界而不是恢复旧训练：

```text
不恢复 Batch9 Wave6
不启动 Batch11
不恢复 Route A/B/C worktree
不恢复旧 SRR 完整 forward
重新授权 nnU-Net 作为冻结 anchor/context/pathology fallback
冻结现有 CARE-MMRD checkpoint 作为 feature/evidence source
新增窄的 scar/edema 独立有界纠错头
```

因此本任务是新的主线科学任务，不是对 Batch10 状态的篡改。Batch10 的代码、指标、terminal packet 和停止理由都保留为历史证据。

## 开发边界

只允许在：

```text
/users/a/e/aereinh/CARE
main
```

开发。不得写入 `/overflow/htzhu/CARE` 或历史 Route A/B/C worktree。Controller、Executor、Mapper 和 Finalizer 不得 push runtime 结果；本任务最终只允许本地轻量 commit，除非用户另行授权。

## 图视觉门

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_route_objective: observed-modality encoding -> clean pathology evidence retrieval -> anatomy-guided scar/edema proposals -> bounded nnU-Net correction -> pathology-specific fallback
```

本轮恢复 SRR-v3 的核心安全语义：nnU-Net 是最终六类 logits 基底，创新模块只对 scar/edema 做有界、可回退的纠错。旧 prototype/dictionary/SIP/arbiter 实现不得直接进入新 forward；只允许重新实现有明确 provenance 和 cross-fit 规则的窄 pathology prototype evidence。

## 当前任务入口

```text
task_key: 20260724_care_myops_srr_cascade_submission_rescue
status: READY_FOR_CONTROLLER
result_root: results/20260724_care_myops_srr_cascade_submission_rescue
planner_decision: results/srr_production/code_maturity/srr_cascade_submission_rescue_planner_decision_20260724.md
config: configs/care_mm/srr_cascade_submission_rescue.yaml
controller_task: prompts/tasks/20260724_care_myops_srr_cascade_submission_rescue_controller.md
executor_plan: prompts/tasks/20260724_care_myops_srr_cascade_submission_rescue_executor_plan.yaml
architecture_impact: system
runtime_authorized: true
```

## 目标模型

```text
[LGE,T2,C0] + availability
-> frozen five-fold OOF nnU-Net anchor logits
-> frozen CARE-MMRD full-view feature/anatomy/edema source
-> frozen CARE-MMRD scar evidence source
-> new four-shard cross-fitted scar/edema prototype similarities
-> anatomy union, uncertainty and physical distance support
-> independent scar correction head
-> independent edema-zone plus pure-edema correction head
-> bounded correction only on compact channels 5 and 4
-> per-pathology audit decision and exact anchor fallback
```

目标实现：

```text
src/care_myocardium/models/care_srr_cascade_rescue.py
CARESRRCascadeRescue
```

固定输出规则：

```text
channels 0-3: exact nnU-Net anchor logits
scar channel 5: anchor + support * 2*tanh(delta_scar)
edema channel 4: anchor + T2_presence * support * 2*tanh(delta_edema)
no-T2 edema: exact anchor logits and labels
```

## 冻结资产

Wave0 必须重新核对文件存在、SHA256、模型结构、normalization state 和 clean-checkout 可加载性。规划绑定的候选为：

```text
feature/anatomy/edema source:
results/20260723_care_myops_batch9_exposed_issues_repair/runtime/seed20260723/teacher_full_view/checkpoint_epoch50.pt
sha256: e92521fccec92d0066f3fa5c076fce16aea3bb02330b940c85321ab4726d1474

scar evidence source:
results/20260723_care_myops_batch9_exposed_issues_repair/runtime/seed20260723/student_reliable_distill/checkpoint_epoch25.pt
sha256: 366722497a47f292e07a0d1c1a3da57c2502b61042bc89b5cfc56b5a89e6a3a0
```

本地选择和最终审计固定复用 Batch10 的 22/22 calibration/audit manifest：

```text
results/20260724_care_myops_batch10_deadline_rescue/rescue_split_manifest.csv
```

Audit 病例不得参与 checkpoint、threshold、postprocess、source、variant 或 pathology selection。

## 训练与评价边界

正式训练仅允许配置中的两个 seed 和四个 matched variants。每个 variant 固定 6250 optimizer steps，并在 1250/2500/3750/5000/6250 完成 calibration 评价。短 overfit、preflight、失败 attempt、partial checkpoint 和 submitted/pending/running 均为零 formal credit。

训练前必须证明：

```text
initial anchor identity
anatomy channels exact identity
no-T2 edema exact identity
source checkpoint frozen and hash-bound
prototype no-self-shard and no no-T2 negative leakage
all spatial tensors receive the same transform
loss reaches final composed logits or declared edema-zone auxiliary output
200-step scar and edema fixed overfit each reduces loss >=30%
checkpoint save/reload max delta <=1e-6
real known-bad fixtures fail closed
```

正式评价必须同时报告 Dice、exact Hausdorff distance、HD95、precision/recall、remote FP volume、component count、volume ratio、help/harm、empty prediction、changed voxels、CenterB/CenterC、no-T2 safety，并分开 positive-GT 与 all-case-empty-safe populations。

## 病种独立提交规则

Scar 与 edema 分别在 calibration 冻结 candidate，随后只在 audit 判断是否替换 nnU-Net。每个病种只能选择：

```text
USE_SRR_CASCADE
USE_CASCADE_CONTROL
FALLBACK_TO_NNUNET
```

至少一个病种通过 audit 才允许本地构建 custom submission-ready package。未通过的病种必须保留 nnU-Net，不能用两病种平均值、两 seed 平均值或 all-case empty-safe Dice掩盖失败。

Cine 不进行新训练。只有 MyoPS 至少一个 custom 病种通过时，才允许把现有 Dataset502 nnU-Net 五折推理链作为 Cine 固定来源进入本地 package dry-run。该来源不是本任务的科学创新。

## Batch10 历史终态

Batch10 terminal packet仍有效：

```text
selected_candidate: distill_epoch25_two_seed_mean/raw_argmax
audit scar Dice delta vs nnU-Net: about -0.022
audit edema Dice delta vs nnU-Net: about -0.029
scar HD95 and remote-FP unsafe
no-T2 edema voxels: 0
near-baseline gate: FAIL
```

这些结果说明直接 CARE-MMRD 路线不应继续；它们不否定当前新任务的 anchor-bounded、pathology-specific rescue 假设。

## 当前未授权

```text
恢复旧 Batch9 Wave6
启动 Batch11
运行旧 Batch7/8
实例化旧 SRRProposeRefineMyoPS/ProposalDictionary/BR2/SIP/arbiter production path
复制或依赖 MoSAIC 代码或权重
外部数据或外部预训练权重
改变 calibration/audit split
用 audit 调参
新 Cine 训练
fold expansion
validation upload
Docker upload
hosted metric claim
route promotion
```
