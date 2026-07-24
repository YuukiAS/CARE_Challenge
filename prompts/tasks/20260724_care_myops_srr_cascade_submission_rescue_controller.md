---
task_key: 20260724_care_myops_srr_cascade_submission_rescue
task_kind: scientific_milestone
task_type: srr_cascade_submission_rescue
status: READY_FOR_CONTROLLER_RUNTIME_CLOSURE_REPAIR
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260724_care_myops_srr_cascade_submission_rescue_executor_plan.yaml
binding_runtime_closure_repair_path: prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_controller.md
binding_runtime_closure_config_path: configs/care_mm/srr_cascade_runtime_closure_repair.yaml
binding_runtime_closure_executor_plan_path: prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

## Execution Contract

方法名称保持 `CARE-SRR-Cascade`，本次执行保持 `SRR-Cascade Rescue Round 1`（`SCR-R1`）。它不是 Batch11、SCR-R2 或旧 milestone。

Controller 在提交真实 W3 前发现正式 Python runtime 缺失，并正确停止。用户随后授权 `SCR-R1-RC1` 同范围运行闭环修复。以下三份文件现为最高优先级：

```text
results/srr_production/code_maturity/scr_r1_runtime_block_critic_and_repair_20260725.md
configs/care_mm/srr_cascade_runtime_closure_repair.yaml
prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_executor_plan.yaml
```

完整修复 Controller 入口：

```text
prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_controller.md
```

它们在冲突时覆盖旧 preexecution amendment、base config、旧 executor plan和旧 Controller生成的resolved contract。科学假设、seed、6250-step预算、22/22 split、retention gate、Cine边界和上传权限不变。

冻结方法仍是：五折 OOF nnU-Net anchor作为最终六类logit基底和病种fallback；两个hash-bound CARE-MMRD checkpoint只提供冻结证据；全新category-aware cross-fitted prototype evidence进入scar/edema独立轻量纠错头；只修改通道5/4，通道0–3和未激活病种保持anchor；任一病种audit失败即fallback。

禁止恢复旧 `SRRProposeRefineMyoPS`、ProposalDictionary、BR2/SIP、arbiter、Batch7/8 runtime或Batch9 Wave6；不得使用MoSAIC代码/权重、外部数据/权重、新Cine训练、fold expansion或上传。

## Controller Prompt

你是SCR-R1唯一Controller。若当前goal停在 `NEEDS_REPAIR_FORMAL_ENTRYPOINT_MISSING`，不要把它视为终态，也不要直接重跑旧formal shell。同步最新`origin/main`，确认包含SCR-R1-RC1修复文件，然后按新修复Controller入口恢复同一goal。

先重建当前authority chain与Controller context；保留旧W-1/W0/W1/W2/W3 receipts作为历史证据。根据修复矩阵：W-1保留PASS；W0资产保留但补真实anchor roundtrip和worktree/job-state复验；W1原位修复独立病种trunk、prototype类别与production runtime；W2在真实cache/anchor/augmentation上重跑；W3此前零formal credit。

严格监督一个Executor按RC0–RC6执行。每个Wave后检查真实diff、调用图、cache/hash、augmentation、loss梯度、checkpoint/resume、预测、Slurm与required outputs。普通代码或runtime缺陷必须退回同一Executor修复，不得再次仅因“仓库缺实现”而终止，因为新合同已经写死实现结构与入口。

正式训练前必须看到：

```text
formal_authorization_gate.json: PASS
all-220 anchor roundtrip: 0 changed voxels per case
all-220 source cache: 880 valid fields
real 32-channel scar/edema 200-step overfit: loss reduction >= 30%
actual augmentation fiducial: 0 mismatch
four formal dry-runs: PASS
orchestrator idempotence and real known-bad: PASS
```

正式运行固定四个seed-pathology logical jobs，每个job先matched control后SRR，每个variant 6250 optimizer steps并在1250/2500/3750/5000/6250验证。允许同logical run在signal/preemption下按固定hash resume，但只有两个variant均完整结束才有formal credit。调度器必须状态驱动且不得硬编码job ID。

W3结束后继续同一goal完成W4 calibration六候选冻结与audit、条件式W5 official package/Docker dry-run、W6 strict validator/Mapper/CURRENT/wiki/fingerprint和本地轻量commit。不得停在submitted/pending/running/monitor/resume状态。

最终仅允许：

```text
CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
PARTIAL_CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
NO_CUSTOM_RESCUE_USE_BASELINE_ONLY
OPERATIONALLY_BLOCKED
```

`OPERATIONALLY_BLOCKED`仅可用于真实缺失且不可生成的服务器资产、存储低于合同门槛、授权partition在所有允许尝试后仍不可用或外部集群故障；普通实现错误不属于operational block。

Batch完全结束、aggregation/validator/commit确认后才写notification并发送完成邮件。不得push runtime、validation/Docker上传或hosted claim。

## Executor Worker Contract

Executor按SCR-R1-RC1修复plan实施，不得自行改变科学设计、seed、budget、split、门槛、候选、decode或上传权限。每个Wave返回真实diff、测试、asset/hash、job与证据；dry-run、smoke和partial checkpoint均不得冒充formal complete。

## Mapper Contract

Mapper核对真实production调用图：OOF anchor builder、tiled frozen source cache、independent pathology trunks、category-aware cross-fit prototypes、matched schedule、active-pathology losses、resume、selection/audit decode、five-fold package anchor、official export与fallback。终态更新root wiki、COMPONENTS、architecture、CURRENT和fingerprint；不要求新PNG。
