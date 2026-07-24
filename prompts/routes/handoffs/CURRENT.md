# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 当前状态

```text
state_id: care_myops_batch10_deadline_rescue_ready_20260724
round_id: post_round04_main_only
state_updated_date: 2026-07-24
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: CARE_MMRD_BATCH10_DEADLINE_RESCUE
batch7_operational_status: SIX_MATCHED_RUNS_COMPLETE
batch7_scientific_packet_status: INCOMPLETE_BR2_SIP_MECHANISM_CLOSURE
batch8_status: SUPERSEDED_UNEXECUTED_DIAGNOSTIC_CONTRACT
batch9_original_status: COMPLETE_NO_USABLE_SIGNAL_WITH_IMPLEMENTATION_DEFECTS
batch9_repair_status: WAVE0_5_CODE_PUSHED_WAVE6_HUMAN_STOPPED_AT_EPOCH25
batch10_status: READY_FOR_CONTROLLER
next_required_action: RUN_BATCH10_DEADLINE_RESCUE
controller_is_coordinator: true
planning_review_required: false
review_required: false
batch10_authorized: true
batch11_authorized: false
nnunet_evaluation_baseline_read_authorized: true
nnunet_model_anchor_or_fallback_authorized: false
validation_packaging_authorized: false
validation_upload_authorized: false
docker_local_build_authorized: true
docker_upload_authorized: false
hosted_metric_claim_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
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
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
```

Batch 10 保留 CARE-MMRD 的三模态独立 stem、availability hard mask、ResidualEncoderUNet、anatomy/scar/edema 分头和六类直接输出。旧 SRR 的 prototype、memory、BR2、SIP、proposal、refiner、source arbiter、production gate 和 nnU-Net anchor 不进入 Batch 10。

## 用户终止的 Batch 9 repair 状态

用户已终止原 Wave 6 在 epoch 25 之后的继续运行。不得自动恢复原 control/distill 到 epoch100。

当前人工提供的 epoch25 轻量结果：

```text
seed20260723 control: scar 0.4743, edema 0.3188
seed20260723 distill: scar 0.4754, edema 0.3316
seed20260724 control: scar 0.4291, edema 0.3354
seed20260724 distill: scar 0.4221, edema 0.3576

matched distill-control:
seed20260723 scar +0.0011, edema +0.0128
seed20260724 scar -0.0070, edema +0.0223
```

这些数字说明蒸馏对 edema 有信号，但对 scar 不稳定，并且仍不能证明超过 nnU-Net。截图不是终态 packet；Batch 10 Wave0 必须绑定本地 checkpoint、job、runtime receipt 和 hash。

最新代码提交：

```text
3705a37bf4519144ea52155a2a7a3d2d118e3776
```

该提交只声明 Wave0–5 部分实现和 Wave6 runtime support，不是 Batch9 terminal scientific packet。

## 为什么启动 Batch 10

进一步代码审计发现以下问题仍会改变当前分数的可信度：

```text
全体积单次forward代替plans滑窗推理
shape-only nearest-neighbor zoom代替正式inverse preprocessing/export
checkpoint评价使用默认模型构造而非checkpoint plans/config
ResEnc M plans与硬编码preprocessed目录可能不一致
student空间增强未同步到natural/teacher view
病理覆盖gate只检查任意类别confidence
sampler没有先按center均衡
远端代码可能依赖未提交case_metadata.py
CURRENT/wiki与真实Wave6 runtime不同步
```

因此 Batch 10 不是再次无边界训练，而是一次限时的公平重评与提交决策。

## 当前唯一授权任务：Batch 10 截止日前救援

```text
task_key: 20260724_care_myops_batch10_deadline_rescue
status: READY_FOR_CONTROLLER
result_root: results/20260724_care_myops_batch10_deadline_rescue
planner_decision: results/srr_production/code_maturity/batch10_deadline_rescue_planner_decision_20260724.md
config: configs/care_mm/batch10_deadline_rescue.yaml
controller_task: prompts/tasks/20260724_care_myops_batch10_deadline_rescue_controller.md
executor_plan: prompts/tasks/20260724_care_myops_batch10_deadline_rescue_executor_plan.yaml
architecture_change: false
training_semantics_change: conditional_component_repair
```

执行顺序固定为：

```text
freeze Batch9 runtime and clean-checkout audit
-> plans/preprocessing fingerprint
-> nnU-Net v2 sliding-window + official inverse export
-> fair re-evaluation of 8 existing checkpoints and baseline
-> bounded ensemble and calibration/audit postprocessing
-> near-baseline gate
-> conditional synchronized 25-epoch matched rescue
-> paper/Docker go-no-go and terminal packet
```

## nnU-Net 边界

允许只读现有 fold0 nnU-Net NIfTI prediction和metrics，使用同一 evaluator重算 baseline、case-wise help/harm、HD95和remote FP。

禁止：

```text
加载标准nnU-Net checkpoint进入CARE-MMRD
把nnU-Net logits/probabilities作为模型输入
anchor correction
ensemble source
prediction fallback
Docker fallback
```

## 条件式训练门

只有正确重评后的最佳非 nnU-Net 候选在独立 audit 半集满足：

```text
scar gap to nnU-Net <= 0.04
edema gap to nnU-Net <= 0.03
GT-positive empty = 0
no-T2 edema voxels = 0
HD95 relative worsening <= 10%
```

才允许从 repaired direct selected checkpoint重新运行两个 seed 的 matched control/distill，各25 epoch、6250 steps。训练必须修复共享空间增强、center-first sampling和scar/edema病种特异confidence mask。任一 seed、任一病种下降不得被平均掩盖。

## Paper 与 Docker 决策

用户提供的时间边界：

```text
paper deadline: 2026-07-27
docker submission deadline: 2026-08-03
```

Batch 10 必须分别生成 `paper_decision.md` 和 `docker_decision.md`。Paper候选要求audit split两病种基本不低于同划分nnU-Net、完整44例至少一个病种提高0.005、另一个非负，并满足HD95/help-harm/remote-FP安全门。

Docker候选允许更接近基线，但必须是有实质意义的非 nnU-Net CARE-MMRD候选并通过端到端本地dry-run。Controller只可构建本地image和submission-ready manifest；上传仍需用户确认。

## 终止边界

完成正确推理、teacher/ensemble、固定后处理以及允许的25 epoch短续训后，若 scar 仍低于baseline超过0.03或edema低超过0.02，停止CARE-MMRD竞赛路线，不启动Batch11，不恢复Batch7或旧SRR长链。

## 当前未授权

```text
resume old Wave6 to epoch100
Batch7 runtime
Batch8 runtime
Batch11
nnU-Net model/anchor/logits/probability/fallback
BR2/SIP/prototype/memory/proposal/refiner
new backbone
external data/pretrained weights
fold expansion
Cine training
validation upload
Docker upload
hosted metric claim
route promotion
final scientific claim before Batch10 terminal packet
```

`configs/srr_production/entrypoints.yaml` 仍记录旧 Batch9 authority，当前标记为 stale；Batch10 Wave0 必须在实现入口和strict audit准备完成后同步修复，不得把旧 authority 当作当前科学状态。
