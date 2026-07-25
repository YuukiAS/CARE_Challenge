# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。


## 2026-07-25 MoSAIC fold0 公平复现终态更新

本次最新已验证运行不是 validation 上传或新混合模型训练，而是 MoSAIC 在 MyoPS exact fold0 上的本地公平复现与同口径比较。结果根目录：

```text
results/20260725_care_myops_mosaic_fold0_reproduction
```

终态证据：

```text
strict_validator_report.json: PASS
finalizer_state.json: READY_FOR_LOCAL_PACKET_COMMIT
Slurm: 60589655 coarse COMPLETED 0:0; 60589656 scar COMPLETED 0:0; 60589657 edema COMPLETED 0:0; 60589658 finalizer FAILED 1:0 and retained; 60607636 replacement finalizer COMPLETED 0:0
exact split: data/benchmarks/protocol/splits_MyoPS.json fold0, 176 train / 44 val
runtime_adapter_audit.json: PASS, MyoPS-only, Cine not called, 44 normalized predictions
```

证据边界：`/users/a/e/aereinh/MoSAIC` 中的 checkpoint 仍然只代表 full-data submission 权重，可用于模型加载或官方 validation 部署 smoke；它们没有用于本次 fold0 训练、初始化或 44 例性能比较。本次 `mosaic_fold0_random_init` 的证据只来自 `results/20260725_care_myops_mosaic_fold0_reproduction/runtime/fold0/` 下新训练的 CoarseNet、FinePathNet scar expert 和 EdemaNet。

当前主比较固定为 `nnunet_fold0` vs `mosaic_fold0_random_init`，同一 canonical evaluator 输出 `canonical_casewise_metrics.csv`、`canonical_model_summary.csv`、`pairwise_help_harm.csv` 和 `complementarity_report.md`。Batch10 MMRD 与 Batch7 minimal 只因已有 fold0 预测而进入 secondary canonical recompute；SCR-R1 generic cascade control 没有当前可复算预测路径，只保留在 `historical_attempt_summary.csv` 的 historical_noncanonical 边界内。

本任务仍不授权 validation upload、Docker build、git push、新混合模型训练或 fold expansion。

## 当前状态

```text
state_id: care_myops_srr_cascade_scr_r1_runtime_closure_terminal_20260725
round_id: post_round04_main_only_submission_rescue
state_updated_date: 2026-07-25
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: CARE_SRR_CASCADE_SUBMISSION_RESCUE
method_name: CARE-SRR-Cascade
execution_code: SCR-R1
runtime_repair_code: SCR-R1-RC1
batch10_status: TERMINAL_STOP_RETAINED_AS_HISTORY
submission_rescue_status: TERMINAL_LOCAL_EVALUATED_BASELINE_FALLBACK
prior_controller_block: VALID_REAL_W3_RUNTIME_MISSING
next_required_action: REVIEW_TERMINAL_LOCAL_RESULTS_AND_DECIDE_FUTURE_STRATEGY
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

## 为什么当前不是直接提交 W3

Controller 已完成一轮 W-1/W0/W1/W2 实现与检查，并启动了 source-cache prerequisite attempts；随后发现：

```text
scripts/training/run_care_srr_cascade_rescue.py --formal-job
```

真实调用被代码主动写成：

```text
NEEDS_REPAIR_FORMAL_ENTRYPOINT_MISSING
```

同时，旧 W3 orchestrator硬编码cache job ID，并在cache PASS后仍强制拒绝formal submission。Controller 因此停止是正确的；smoke、dry-run或monitor不能替代每variant 6250 optimizer-step训练。

用户于2026-07-25授权同范围运行闭环修复：

```text
repair_id: SCR-R1-RC1
repair_task_key: 20260725_care_myops_srr_cascade_runtime_closure_repair
```

这不是SCR-R2、Batch11或新milestone，不改变科学假设、seed、budget、split、retention gate、Cine边界或上传权限。

## 最高优先级入口

```text
critic_report:
results/srr_production/code_maturity/scr_r1_runtime_block_critic_and_repair_20260725.md

repair_config:
configs/care_mm/srr_cascade_runtime_closure_repair.yaml

repair_controller:
prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_controller.md

repair_executor_plan:
prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_executor_plan.yaml
```

冲突优先级：

```text
SCR-R1-RC1 repair config
> SCR-R1 preexecution amendment
> SCR-R1 base config / executor plan
> historical Controller-generated resolved contract
```

原SCR-R1 controller入口已更新为指向本修复。不得继续使用绑定在旧 `6b9834c6...` SHA 的Controller context直接运行旧formal shell。

## 前序 Wave 当前判定

```text
Wave -1:
RETAIN_PASS
合同路径、SHA和amendment precedence可保留；补入RC1 authority hashes。

Wave 0:
CONDITIONAL_PASS_REVALIDATE_RUNTIME_FIELDS
保留220例OOF manifest、checkpoint SHA、22/22 split和plans fingerprint；
必须补真实anchor tensor/grid/official-export roundtrip、工作树分类和动态job-state。

Wave 1:
IN_PLACE_REPAIR_REQUIRED
保留bounded composition、0-3 identity、no-T2 identity和loss公式；
必须把当前共享scar/edema trainable trunk改成独立trunks，补production runtime和category-aware prototypes。

Wave 2:
REVALIDATE_BEFORE_FORMAL
旧检查主要是合成4通道tiny feature和clone-only fiducial；
必须在真实32通道source cache、真实OOF anchor、真实label和真实augmentation上重跑。

Wave 3:
EXPECTED_BLOCK_ZERO_FORMAL_CREDIT
现有cache attempts只属于prerequisite；没有正式模型训练credit。
```

## 旧 Slurm 状态边界

远端最后记录过：

```text
superseded_no_lock_cache: 60450660
locked_cache_attempts: 60451021, 60451022
```

这些编号不是新orchestrator authority。恢复Controller后必须现场刷新`squeue/sacct`：

- completed cache只有通过SCR-R1-RC1 adoption validator才能复用；
- pending旧attempt可以取消并由新状态驱动orchestrator替代；
- running attempt可以完成后验收，但不能因stale lock阻塞修复；
- failed/partial cache不得触发formal jobs；
- 新orchestrator禁止硬编码任何job ID。

## 开发边界

只允许：

```text
/users/a/e/aereinh/CARE
main
```

不得写入 `/overflow/htzhu/CARE` 或历史 Route A/B/C worktree。Controller、Executor、Mapper和Finalizer默认不得push runtime；最终只允许本地轻量commit，除非用户另行授权。

启动修复时允许记录但不得静默混入commit的pre-existing untracked：

```text
.codex_runtime/
scripts/evaluation/batch10_baseline_reference_consistency.py
scripts/evaluation/batch10_strict_entrypoint_audit.py
tests/care_mm/test_batch10_fair_inference.py
```

其他未知untracked source/test必须先分类或停止修复。

## 图视觉门

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD, CARE-SRR-Cascade
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_route_objective: observed-modality encoding -> clean pathology evidence retrieval -> anatomy-guided support -> bounded nnU-Net correction -> pathology-specific fallback
```

本轮运行修复不改变CARE-SRR-Cascade科学图，因此不要求新PNG。

## 冻结方法

```text
[LGE,T2,C0] + availability
-> five-fold OOF nnU-Net anchor on resolved preprocessed grid
-> tiled frozen CARE-MMRD teacher feature/anatomy/edema cache
-> tiled frozen CARE-MMRD scar evidence cache
-> category-aware four-shard cross-fitted scar/edema prototypes
-> independent scar correction trunk
-> independent edema-zone/pure-edema correction trunk
-> bounded correction only on compact channels 5/4
-> per-pathology calibration freeze, audit and exact anchor fallback
```

固定输出：

$$z^{final}_{0:3}=z^{anchor}_{0:3},$$

$$z^{final}_{scar}=z^{anchor}_{scar}+r_{scar}\,2\tanh(\Delta_{scar}),$$

$$z^{final}_{edema}=z^{anchor}_{edema}+m_{T2}r_{edema}\,2\tanh(\Delta_{edema}).$$

Scar formal job中edema通道保持anchor；edema formal job中scar通道保持anchor。Control与SRR只允许prototype maps为zero或real这一项不同。

## 运行修复目标入口

必须实现并验收：

```text
src/care_myocardium/srr_production/anchor_runtime.py
src/care_myocardium/data/care_srr_cascade_runtime.py
src/care_myocardium/training/care_srr_cascade_trainer.py
scripts/training/run_care_srr_cascade_formal.py
scripts/inference/run_care_srr_cascade_inference.py
scripts/evaluation/evaluate_care_srr_cascade.py
scripts/evaluation/select_care_srr_cascade.py
scripts/evaluation/validate_care_srr_cascade_packet.py
```

同时修复model/prototype/cache/formal shell/orchestrator。所有细节以runtime closure config为准，Executor不得自行选择替代设计。

## 正式训练前重新授权门

必须全部PASS：

```text
all-220 OOF anchor cache and official-export roundtrip: 0 changed voxels per case
all-220 source cache: 880 fields, checkpoint/config/grid/hash/parity pass
category-aware prototype cache and same-shard exclusion pass
four matched schedule hashes frozen
real 32-channel scar overfit 200 optimizer steps: loss reduction >=30%
real 32-channel edema overfit 200 optimizer steps: loss reduction >=30%
actual shared augmentation fiducial: 0 mismatch
each active pathology loss independent backward pass
checkpoint/resume cursor and output roundtrip pass
htzhulab and a100-gpu GPU preflight pass
four formal CLI dry-runs and orchestrator idempotence pass
real known-bad suite pass
formal_authorization_gate.json: PASS
```

旧 `preflight_receipt.json` 不能单独满足该门。

## W3–W6 预定义闭环

W3固定四个logical runs：

```text
scar_seed20260724: htzhulab, control -> SRR
edema_seed20260724: htzhulab, control -> SRR
scar_seed20260725: a100-gpu, control -> SRR
edema_seed20260725: a100-gpu, control -> SRR
```

每variant固定6250 optimizer steps、gradient accumulation 2，并在1250/2500/3750/5000/6250保存checkpoint与calibration评价。允许同logical run按signal/preemption精确resume；partial attempt为零credit，完整logical run才计入。

W4固定六候选/病种、calibration-only选择、audit一次性读取和病种独立fallback。W5在至少一个custom pathology通过audit时才做15 MyoPS + 15 Cine本地package/Docker dry-run，MyoPS anchor必须是现有Dataset501五折probability ensemble。W6完成strict validator、known-bad、Mapper/wiki/CURRENT/fingerprint和本地轻量commit。

## 允许的终态

```text
CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
PARTIAL_CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
NO_CUSTOM_RESCUE_USE_BASELINE_ONLY
OPERATIONALLY_BLOCKED
```

`OPERATIONALLY_BLOCKED`只适用于无法生成的服务器资产、低于45GiB的实测存储、两个授权GPU partition完成所有允许尝试后仍不可用，或外部集群故障。普通代码、cache、训练、评价、selection、打包、validator或Mapper错误属于同范围修复。

## 当前未授权

```text
恢复Batch9 Wave6
启动Batch11或SCR-R2
运行旧Batch7/8
旧完整SRR/ProposalDictionary/BR2/SIP/arbiter production path
MoSAIC代码或权重
外部数据或外部预训练权重
改变22/22 split或用audit调参
新增seed/variant或改变6250-step预算
新Cine训练
fold expansion
validation upload
Docker upload
hosted metric claim
route promotion
runtime git push
```
