---
task_key: 20260724_care_myops_srr_cascade_submission_rescue
task_kind: scientific_milestone
task_type: srr_cascade_submission_rescue
status: READY_FOR_CONTROLLER
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
experiment_adequacy_gate: controller_contract
route_negative_gate: planner_only
scientific_completion_gate: planner_only
diagnostic_publication_gate: controller_verified_local_commit
diagnostic_publication_scope: lightweight_source_config_test_result_and_wiki_only
blocked_after_diagnostic_publication: validation_upload,docker_upload,hosted_metric_claim,fold_expansion,new_cine_training,batch11,route_promotion
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

## Execution Contract

本任务不是继续 CARE-MMRD，也不是 Batch11。用户显式授权一条新的截止日前 submission-rescue 主线：冻结 nnU-Net 作为最终六类 logits 基底、解剖上下文和病种级 fallback；冻结现有 CARE-MMRD checkpoint 作为特征/证据源；用全新、窄实现的 cross-fitted pathology prototype evidence 与 scar/edema 独立轻量纠错头，只对病理通道做 `2*tanh(delta)` 有界修正。任一病种未通过 audit 门时自动保留 nnU-Net。

必须严格执行 Planner decision、config和executor plan。不得恢复旧 `SRRProposeRefineMyoPS`、ProposalDictionary、BR2/SIP、arbiter、旧 Batch7/8 runtime，也不得复制或依赖 MoSAIC 代码/权重。Cine 不训练，最终包固定使用现有 Dataset502 nnU-Net 五折链。允许本地 Docker/package dry-run，不允许上传。

## Controller Prompt

你是本任务唯一的 Controller、协调者和最终操作验收人。开始前同步最新远端 `main`，绑定当前 SHA，读取治理文件、Planner decision、config、executor plan、Batch10 terminal packet、Slurm skill和Mapper skill。若远端已前移，先检查是否与本任务冲突；不得在未重绑定时执行。

严格按 Wave 0–6 顺序监督一个 Executor。每个 Wave 后必须亲自检查真实 git diff、调用图、checkpoint/anchor/prototype hashes、数据划分、增强对应关系、loss梯度、预测、Slurm和required outputs。普通实现、训练、评价、导出、validator或packet缺陷属于同范围修复，必须退回同一 Executor修复并复验，不能只记录问题后结束。

特别防止以下复发：

1. 用 in-fold、GT、随机或被修改的 anchor 代替 OOF anchor；
2. source checkpoint hash不匹配、source参数被训练或 norm状态漂移；
3. training case查询包含自身 prototype shard，或 no-T2 myocardium进入 edema negative；
4. 只增强 image/label，未同步 anchor、source feature/logit、prototype和distance map；
5. loss监督 residual 但没有作用于最终 composed logits；
6. custom head改动 anatomy 0–3通道，或无T2时改动 edema；
7. control/SRR没有共享初始化、sampler、augmentation、预算和decode；
8. 用 calibration/audit混用、all-case empty-safe Dice、HD95替代官方 exact HD；
9. checkpoint selection和最终部署decode不同，或selected checkpoint未reload；
10. 短overfit、submitted/pending/running、partial checkpoint、token或文件存在被写成完成；
11. 只看平均值，掩盖单seed、单病种、CenterB/CenterC、help/harm和remote-FP失败；
12. 为了“做出东西”私自放宽门槛、引入外部权重、启动新Cine训练或上传。

正式训练前，必须通过 initial anchor identity、no-T2 exact identity、anatomy-channel identity、200-step fixed overfit、单loss backward、同步空间增强 fiducial、prototype cross-fit、checkpoint roundtrip和真实 known-bad。任何失败不得提交正式训练。

两个seed job可在config指定的两个partition并行，但每个job内部按固定顺序运行四个matched variants，写入隔离runtime/log/lock目录。训练依赖用`afterok`，所有attempt的accounting/finalizer用`afterany`。Controller持续负责到全部attempt terminal、重新aggregation、strict validator、Mapper/wiki/CURRENT/fingerprint和本地轻量commit完成；submitted-only不是终态。

最终按病种独立机械判断 `USE_SRR_CASCADE | USE_CASCADE_CONTROL | FALLBACK_TO_NNUNET`。至少一个custom分支通过audit才允许本地构建submission-ready包；两病种都失败则诚实返回baseline-only，不得包装成custom成功。最终只允许以下科学token之一：

```text
CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
PARTIAL_CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
NO_CUSTOM_RESCUE_USE_BASELINE_ONLY
OPERATIONALLY_BLOCKED
```

Controller report开头先用自然中文解释实际结果，再给Dice、exact HD、HD95、help/harm、remote FP、component、empty prediction、no-T2 safety、CenterB/C和hash证据。`VERIFIED_COMPLETE`只代表本任务合同完成，不代表hosted成绩或允许上传。

Batch完全结束、aggregation/validator/commit状态确认后，写`results/20260724_care_myops_srr_cascade_submission_rescue/notification_brief.json`，使用既有 notifier 向`1155246312@link.cuhk.edu.hk`发送中文短邮件。不得在submitted、pending、running或monitor阶段通知。

## Executor Worker Contract

Executor只执行executor plan授权的实现、测试、Slurm、聚合、评价、Mapper输入和本地package dry-run。每个Wave返回真实diff、命令、hash、job ID和证据给Controller；不能自行宣布整体完成、修改科学门槛、增加variant、上传或push。

## Mapper Contract

Mapper核对新模型真实调用图、冻结source、OOF anchor、prototype cross-fit、病种独立correction、no-T2和anatomy identity、loss/gradient、selection/deployment decode、official export、Cine frozen source及终态证据。实现完成后更新root wiki、COMPONENTS、architecture/fingerprint和CURRENT；不得把validator PASS写成科学成功。
