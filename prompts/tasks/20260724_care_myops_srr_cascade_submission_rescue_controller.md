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
diagram_update_required: false
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

本任务的方法名称固定为 `CARE-SRR-Cascade`，简称 `SRR-Cascade`；本次执行称为 `SRR-Cascade Rescue Round 1`（`SCR-R1`）。它不是 Batch11，也不续接旧 milestone 编号。

本任务不是继续 CARE-MMRD，也不是恢复旧 SRR 全链。冻结 nnU-Net 作为最终六类 logits 基底、解剖上下文和病种 fallback；冻结现有 CARE-MMRD checkpoint 作为特征与病种证据；新建四分片 cross-fitted 病种原型和 scar/edema 独立轻量纠错头，只对病理通道做有界修正。任一病种未通过 audit 门时，最终输出保留该病种的 nnU-Net。

以下文件共同构成冻结合同，后者在冲突时覆盖前者：

```text
results/srr_production/code_maturity/srr_cascade_submission_rescue_planner_decision_20260724.md
configs/care_mm/srr_cascade_submission_rescue.yaml
prompts/tasks/20260724_care_myops_srr_cascade_submission_rescue_executor_plan.yaml
configs/care_mm/srr_cascade_submission_rescue_preexecution_amendment.yaml
```

`preexecution_amendment` 是本次执行前复核后的强制修正：它写死 anchor 概率到 logits 与预处理网格的转换、冻结 source cache、head 维度、support 公式、case-level prototype、每项 loss、checkpoint/seed ensemble 选择、四个 seed-pathology Slurm job，以及官方 package 使用五折 nnU-Net ensemble anchor。不得忽略或自行降级。

禁止恢复旧 `SRRProposeRefineMyoPS`、ProposalDictionary、BR2/SIP、arbiter、旧 Batch7/8 runtime；不得复制或依赖 MoSAIC 代码或权重。Cine 不训练，最终包固定使用现有 Dataset502 nnU-Net 五折链。允许本地 Docker/package dry-run，不允许上传。

## Controller Prompt

你是本任务唯一的 Controller、协调者和最终操作验收人。开始前同步最新远端 `main`，绑定当前 SHA，读取治理文件、四份冻结合同、Batch10 terminal packet、Slurm skill 和 Mapper skill。若远端已前移，先检查是否与本任务冲突；不得在未重绑定时执行。

在启动 Executor 前，必须完成一个额外的 `Wave -1`：核对 base config/executor plan 与 preexecution amendment，将所有覆盖项写入：

```text
results/20260724_care_myops_srr_cascade_submission_rescue/preexecution_amendment_receipt.json
results/20260724_care_myops_srr_cascade_submission_rescue/resolved_execution_contract.json
```

记录四份合同的路径与 SHA256，明确 `amendment_wins_on_conflict=true`。若无法得到无歧义的 resolved contract，停止为 `NEEDS_REPAIR`，不得让 Executor自行补设计。

严格按修正后的 Wave 0–6 监督一个 Executor。每个 Wave 后必须亲自检查真实 git diff、调用图、checkpoint/anchor/source-cache/prototype hashes、数据划分、增强对应关系、loss 梯度、预测、Slurm和 required outputs。普通实现、训练、评价、导出、validator或 packet 缺陷属于同范围修复，必须退回同一 Executor 修复并复验，不能只记录问题后结束。

特别防止以下复发：

1. 用 in-fold、GT、随机、硬标签或非规范 logit 转换代替 OOF probability anchor；
2. standard nnU-Net anchor 与 ResEncM source grid 只按 shape 对齐，未做物理几何、crop、transpose 与 roundtrip；
3. source checkpoint hash 不匹配、source 参数被训练、norm 状态漂移，或 source cache 与直接 forward 不一致；
4. training case 查询包含自身 prototype shard，prototype 被大体积病例支配，或 no-T2 myocardium 进入 edema negative；
5. 只增强 image/label，未同步 anchor、source feature/logit、prototype map 和 distance map；
6. loss 只监督 raw residual、公式由 Executor 临时决定，或没有作用于最终 composed logits；
7. custom head 改动 anatomy 0–3 通道，使用 learned support gate，或无 T2 时改动 edema；
8. control/SRR 没有共享初始化、sampler、augmentation、预算和 decode；
9. calibration/audit 混用、all-case empty-safe Dice 或 HD95 代替官方 exact HD；
10. checkpoint selection 和最终部署 decode 不同、seed/ensemble候选集合临时扩展，或 selected checkpoint 未 reload；
11. 把四个 variants 塞进一个超长 seed job；正式拓扑必须是四个 seed-pathology job，每个 job 顺序运行 matched control 与 SRR；
12. 官方 MyoPS package 继续使用单个 fold0 anchor；正式 package 必须使用现有 Dataset501 五折 probability ensemble，且不得用 GT/指标调节兼容行为；
13. 短 overfit、submitted/pending/running、partial checkpoint、token或文件存在被写成完成；
14. 只看平均值，掩盖单 seed、单病种、CenterB/CenterC、help/harm 与 remote-FP 失败；
15. 为了“做出东西”私自放宽门槛、引入外部权重、启动新 Cine 训练或上传。

正式训练前，必须通过：anchor canonicalization 与 grid roundtrip、source cache parity、initial anchor identity、no-T2 exact identity、anatomy-channel identity、200-step fixed overfit、单 loss backward、同步空间 fiducial、case-level prototype cross-fit、checkpoint roundtrip 和真实 known-bad。任何失败不得提交正式训练。

正式运行固定为四个 seed-pathology job：两个 scar、两个 edema；每个 job 内先 control 后 SRR，每个 variant 6250 optimizer steps，最长 8 小时。训练依赖使用 `afterok`，所有 attempt 的 accounting/finalizer 使用 `afterany`。Controller必须持续负责到所有 attempt terminal、重新 aggregation、strict validator、Mapper/wiki/CURRENT/fingerprint 和本地轻量 commit 完成；submitted-only不是终态。

Calibration 22例只用于按修正合同的固定六候选集合选择 checkpoint/单 seed/两 seed probability mean；audit 22例不得参与任何选择。最终按病种独立机械判断 `USE_SRR_CASCADE | USE_CASCADE_CONTROL | FALLBACK_TO_NNUNET`。至少一个 custom 分支通过 audit 才允许本地构建 submission-ready 包；两病种都失败则诚实返回 baseline-only。

最终只允许以下科学 token 之一：

```text
CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
PARTIAL_CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
NO_CUSTOM_RESCUE_USE_BASELINE_ONLY
OPERATIONALLY_BLOCKED
```

Controller report 开头先用自然中文解释实际结果，再给 Dice、exact HD、HD95、help/harm、remote FP、component、empty prediction、no-T2 safety、CenterB/C 和 hash 证据。`VERIFIED_COMPLETE`只代表本任务合同完成，不代表 hosted 成绩或允许上传。

Batch完全结束、aggregation/validator/commit状态确认后，写 `results/20260724_care_myops_srr_cascade_submission_rescue/notification_brief.json`，使用既有 notifier 向 `1155246312@link.cuhk.edu.hk` 发送中文短邮件。不得在 submitted、pending、running 或 monitor 阶段通知。

## Executor Worker Contract

Executor只执行 resolved contract 授权的实现、测试、source cache、Slurm、聚合、评价、Mapper输入和本地 package dry-run。每个 Wave 返回真实 diff、命令、hash、job ID 和证据给 Controller；不能自行宣布整体完成、修改科学门槛、增加 variant、上传或 push。

## Mapper Contract

Mapper核对新模型真实调用图、冻结 source/cache、OOF anchor canonicalization 与 grid roundtrip、case-level prototype cross-fit、病种独立 correction、no-T2 与 anatomy identity、loss/gradient、selection/deployment decode、五折 package anchor、official export、Cine frozen source及终态证据。实现完成后更新 `wiki/README.md`、`wiki/current_state.yaml`、`wiki/architecture.yaml`、`wiki/COMPONENTS.csv` 和 CURRENT；本轮不要求生成新的架构 PNG。不得把 validator PASS 写成科学成功。
