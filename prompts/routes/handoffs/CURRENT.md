# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch8_clean_edema_br2_ready_20260722
round_id: post_round04_main_only
state_updated_date: 2026-07-22
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: SRR_MyoPS_from_historical_Route_B_lineage
batch7_operational_status: SIX_MATCHED_RUNS_COMPLETE
batch7_scientific_packet_status: NEEDS_EVIDENCE_REPAIR_NOT_VALID_BR2_SIP_CLOSURE
batch8_status: READY_FOR_CONTROLLER
next_required_action: RUN_BATCH8_CLEAN_EDEMA_BR2_CONFIRMATION
controller_is_coordinator: true
planning_review_required: false
review_required: false
batch8_authorized: true
scar_training_authorized: false
sip_training_authorized: false
refiner_training_authorized: false
source_arbiter_training_authorized: false
production_gate_training_authorized: false
batch9_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
backbone_replacement_authorized: false
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

恢复的路线目标是 observed-modality-only encoding、选择性 shared/private/interaction retrieval、解剖引导病灶候选、病种特异 refinement 与 nnU-Net 安全比较。Batch 8 只保留其中对 clean edema BR2 判断必要的部分；SIP 和 refiner 不在本批训练。

## Batch 7 终态复核

Batch 7 六组 400-step runtime 在操作层面完成：

```text
scar job: 59992434 COMPLETED 0:0
edema job: 59994167 COMPLETED 0:0
scar minimal positive Dice delta: -0.0049928620
edema minimal positive Dice delta: +0.0013426793
edema BR2 positive Dice delta: +0.0029631724
edema BR2 minus minimal: +0.0016204931
```

但原科学闭环被 Planner supersede，原因：

```text
controller_report仍是READY_FOR_CONTROLLER_VERIFICATION
completion_check只声明executor_scope_complete
scar BR2 no-SIP/SIP均为空预测
no-SIP与SIP最终指标完全相同
source_learner_coefficients来自静态新建模型初值
病种系数文件仍含PENDING_DETAILED_BETA_EXPORT
integrativeness_diagnostics仅为STATIC_INITIAL_COEFFICIENTS
validator未检查checkpoint-derived coefficients、空预测或PENDING字段
minimal/BR2仍经过旧ProposalDictionary
决策代码未真正执行全部help/harm、HD95、remote-FP安全门
```

因此当前解释为：

```text
Batch7 operational evidence: retained
Batch7 scar minimal negative signal: retained
Batch7 edema BR2 small positive signal: retained as hypothesis
Batch7 BR2/SIP final scientific closure: invalid pending Batch8 evidence repair
```

## Scar 决定

```text
SCAR_SRR_TRAINING_STOPPED
challenge scar path: nnU-Net anchor
```

Batch 8 只诊断 Batch 7 scar BR2 清空发生在哪一阶段，不再训练 scar dictionary、proposal、SIP、refiner、arbiter 或 gate。

## Batch 8 唯一任务

```text
BATCH8_CLEAN_EDEMA_BR2_CONFIRMATION
```

权威文件顺序：

```text
1. results/srr_production/code_maturity/batch8_clean_edema_br2_planner_decision_20260722.md
2. docs/plans/laneB_round04_active_srr_batch8_clean_edema_br2_confirmation_execution.md
3. configs/srr_production/myops_batch8_clean_edema_br2.yaml
4. prompts/tasks/20260722_srr_batch8_clean_edema_br2_controller.md
5. prompts/tasks/20260722_srr_batch8_clean_edema_br2_executor_plan.yaml
6. results/20260722_srr_batch7_minimal_pathology_decomposition/
```

当前任务路径：

```text
task_key: 20260722_srr_batch8_clean_edema_br2_confirmation
result_root: results/20260722_srr_batch8_clean_edema_br2_confirmation
source_checkpoint_sha256: d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
```

## Batch 8 模型边界

必须新增独立薄模型：

```text
src/care_myocardium/models/srr_batch8_clean_edema.py
CleanEdemaBR2Corrector
```

只允许从 source checkpoint 加载并冻结：

```text
modality encoders
base retrieval
anatomy decoder
edema decoder
anatomy-union context所需权重
```

不得实例化完整 `SRRProposeRefineMyoPS` 后仅靠 flags 关闭旧模块。以下调用计数必须为0：

```text
ProposalDictionary
M10TwoPassSpatialDictionary
M10CrossFittedPrototypeMemory
prototype maps / semantic negative memory
scar/edema refiner
source arbiter
branch arbitration
learned production gate
legacy Pattern-SIP
```

Clean minimal：

```text
frozen edema feature + T2 image + frozen anatomy-union probability
-> clean edema delta head
-> anchor edema logit + 2*tanh(delta)
```

Clean BR2只增加：

```text
shared anatomy
LGE private
T2 private
LGE-T2 interaction
```

系数是 edema-specific、signed、spatially-global；禁止 softmax/simplex/top-k、逐病例beta residual和center进入网络。训练使用CenterB/CenterC beta，验证仅使用 pooled beta。

## Batch 8 实验

固定两个 seed：

```text
20260722:
  edema_clean_minimal_seed20260722
  edema_clean_br2_seed20260722
20260723:
  edema_clean_minimal_seed20260723
  edema_clean_br2_seed20260723
```

每组800步，在200/400/800评价全部44例；step800固定为正式checkpoint并reload。每个seed的minimal/BR2必须共享common-head初始化、中心/病例/patch序列、augmentation、optimizer模板、预算、评价和decode。

训练只使用T2-present、可靠edema监督的CenterB/CenterC病例。No-T2病例不进入训练、beta、loss或negative；终态必须保持逐体素anchor identity。

## 训练前硬门

必须先完成：

```text
Batch7真实checkpoint机制导出
scar空预测阶段定位
clean model import graph
checkpoint白名单加载
旧模块调用计数全0
minimal/BR2初始logits差<=1e-6
no-T2 exact anchor identity
两个真实病例100-step fixed overfit，loss下降>=30%，预测非空
逐loss gradient authority
checkpoint roundtrip<=1e-6
真实known-bad fail-closed
```

任一不通过，不得提交正式训练。

## Slurm

```text
seed20260722 -> htzhulab
seed20260723 -> a100-gpu
python -> /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
finalizer dependency -> afterany all seed jobs
```

两个seed jobs可独立并行，但必须隔离runtime/prediction/checkpoint/log/lock；一个seed不能替代另一个。Submitted/pending/running/monitor不是完成。

## 保留门

Clean BR2只有全部满足才保留：

```text
每seed BR2 positive Dice delta >= +0.002
两seed平均 BR2 positive Dice delta >= +0.003
每seed BR2-minus-minimal >= +0.0005
两seed平均 BR2-minus-minimal >= +0.001
CenterB/CenterC平均delta均>=0
combined help>=harm
HD95 non-worse
remote-FP relative worsening<=5%
no-T2 exact anchor identity
无空预测
所有机制字段来自selected checkpoint且为数值
```

终态只能是：

```text
EDEMA_CLEAN_BR2_RETAIN_PENDING_PLANNER
或
RETIRE_SRRMyoPS_PERFORMANCE_LINE_USE_NNUNET
```

## 未授权

```text
SIP training
refiner training
scar training
source arbiter / production gate
Batch9
fold expansion
Cine
external data or weights
validation packaging/upload
hosted metric claim
route promotion
```

Controller的 `VERIFIED_COMPLETE` 只表示Batch 8合同完成，下一步仍返回Planner。