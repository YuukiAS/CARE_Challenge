# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 当前状态

```text
state_id: care_myops_srr_cascade_rescue_round1_amended_ready_20260724
round_id: post_round04_main_only_submission_rescue
state_updated_date: 2026-07-24
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: CARE_SRR_CASCADE_SUBMISSION_RESCUE
method_name: CARE-SRR-Cascade
short_method_name: SRR-Cascade
execution_label: SRR-Cascade Rescue Round 1
execution_code: SCR-R1
batch10_status: TERMINAL_STOP_RETAINED_AS_HISTORY
submission_rescue_status: READY_FOR_CONTROLLER_WITH_BINDING_PREEXECUTION_AMENDMENT
next_required_action: START_SRR_CASCADE_RESCUE_ROUND1_CONTROLLER
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

## 编号与名称

论文或方法层面统一称：

```text
CARE-SRR-Cascade
short: SRR-Cascade
```

当前执行不是 Batch11，也不续接旧 milestone 编号。当前执行单元称：

```text
SRR-Cascade Rescue Round 1
SCR-R1
```

若本任务完成后仍需要同一方法范围内的后续定向修复，使用 `SCR-R2`、`SCR-R3`；不得重新解释成 Batch11/12。

## 为什么可以在 Batch10 终止后重开

Batch10 对 CARE-MMRD 直接六类分割路线的终止判断继续有效。用户于 2026-07-24 显式授权一条新的 submission-rescue 主线，改变的是模型边界而不是恢复旧训练：

```text
不恢复 Batch9 Wave6
不启动 Batch11
不恢复 Route A/B/C worktree
不恢复旧 SRR 完整 forward
重新授权 nnU-Net 作为冻结 anchor/context/pathology fallback
冻结现有 CARE-MMRD checkpoint 作为 feature/evidence source
新增窄的 scar/edema 独立有界纠错头
```

因此本任务是新的主线科学任务。Batch10 的代码、指标、terminal packet 和停止理由保留为历史证据。

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
base_config: configs/care_mm/srr_cascade_submission_rescue.yaml
binding_preexecution_amendment: configs/care_mm/srr_cascade_submission_rescue_preexecution_amendment.yaml
controller_task: prompts/tasks/20260724_care_myops_srr_cascade_submission_rescue_controller.md
executor_plan: prompts/tasks/20260724_care_myops_srr_cascade_submission_rescue_executor_plan.yaml
architecture_impact: system
runtime_authorized: true
```

Base config、executor plan 与 amendment 冲突时，`preexecution_amendment` 优先。Controller 启动 Executor 前必须写出：

```text
results/20260724_care_myops_srr_cascade_submission_rescue/preexecution_amendment_receipt.json
results/20260724_care_myops_srr_cascade_submission_rescue/resolved_execution_contract.json
```

未形成无歧义 resolved contract 时不得开始实现。

## 目标模型

```text
[LGE,T2,C0] + availability
-> canonical five-fold OOF nnU-Net anchor probabilities/logits on ResEncM grid
-> deterministic frozen CARE-MMRD source feature/logit cache
-> case-level four-shard cross-fitted scar/edema prototype similarities
-> anchor-derived soft myocardium union, entropy uncertainty and physical distance support
-> independent scar correction head
-> independent edema-zone auxiliary plus pure-edema correction head
-> bounded correction only on compact channels 5 and 4
-> calibration-frozen per-pathology candidate
-> audit-only retention decision and exact anchor fallback
```

目标实现：

```text
src/care_myocardium/models/care_srr_cascade_rescue.py
CARESRRCascadeRescue
```

固定输出规则：

```text
channels 0-3: exact nnU-Net anchor logits
scar channel 5: anchor + scar_support * 2*tanh(delta_scar)
edema channel 4: anchor + T2_presence * edema_support * 2*tanh(delta_edema)
no-T2 edema: exact anchor logits and labels
```

Head、support、prototype、loss、selection 与 source cache 的精确公式以 binding amendment 为准，不得留给 Controller/Executor 自行选择。

## 训练与评价边界

正式训练固定为四个 seed-pathology Slurm job：

```text
scar seed20260724: control -> SRR
edema seed20260724: control -> SRR
scar seed20260725: control -> SRR
edema seed20260725: control -> SRR
```

每个 variant 固定 6250 optimizer steps；每个 job 最长 8 小时。短 overfit、preflight、失败 attempt、partial checkpoint 和 submitted/pending/running 均为零 formal credit。

正式训练前必须证明：anchor canonicalization/grid roundtrip、source-cache parity、initial identity、anatomy channel identity、no-T2 identity、prototype no-self-shard/no no-T2 leakage、共享空间变换、精确 loss 与目标梯度、200-step scar/edema fixed overfit、checkpoint roundtrip和真实 known-bad。

正式评价必须同时报告 Dice、exact Hausdorff distance、HD95、precision/recall、remote FP volume、component count、volume ratio、help/harm、empty prediction、changed voxels、CenterB/CenterC、no-T2 safety，并分开 positive-GT 与 all-case-empty-safe populations。

Calibration 22例只允许从 amendment 固定的六个候选中选择；audit 22例不得参与 checkpoint、seed、ensemble、threshold、postprocess、source、variant 或 pathology selection。

## 病种独立提交规则

Scar 与 edema 分别只能选择：

```text
USE_SRR_CASCADE
USE_CASCADE_CONTROL
FALLBACK_TO_NNUNET
```

至少一个病种通过 audit 才允许本地构建 custom submission-ready package。未通过的病种必须保留 nnU-Net，不能用两病种平均值、两 seed 平均值或 all-case empty-safe Dice掩盖失败。

官方 MyoPS 本地 package 必须使用现有 Dataset501 nnU-Net 五折 probability ensemble 作为 anchor；fold0 单模型只用于无泄漏本地 performance authority，不得作为正式 15 例 package anchor。Cine 不进行新训练，固定使用现有 Dataset502 nnU-Net 五折 inference/ensemble。两者均不是 custom gain。

## Batch10 历史终态

```text
selected_candidate: distill_epoch25_two_seed_mean/raw_argmax
audit scar Dice delta vs nnU-Net: about -0.022
audit edema Dice delta vs nnU-Net: about -0.029
scar HD95 and remote-FP unsafe
no-T2 edema voxels: 0
near-baseline gate: FAIL
```

这些结果说明直接 CARE-MMRD 路线不应继续；它们不否定当前 anchor-bounded、pathology-specific rescue 假设。

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
