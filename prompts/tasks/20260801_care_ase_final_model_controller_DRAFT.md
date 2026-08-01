---
task_key: 20260801_care_ase_final_model
task_kind: scientific_milestone
task_type: final_asymmetric_pathology_model
status: DRAFT_FINAL_AUDITED_NOT_AUTHORIZED
risk_level: critical
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: null
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
allow_git_commit: false
auto_git_commit: false
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
new_training_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
blueprint_path: prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
implementation_contract_path: prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
implementation_contract_amendment_paths:
  - prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml
  - prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment02_controller_only_interactive_20260801.yaml
  - prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment03_final_audit_20260801.yaml
---

# CARE-ASE Final Model Controller — FINAL-AUDITED CONTROLLER-ONLY INTERACTIVE DRAFT

当前文件仍然不授权实现、训练、GPU 作业、validation、Docker、hosted claim、CURRENT/wiki 前移或 runtime push。正式执行时，用户必须一次性把 frontmatter 中 execution/training/commit/push 权限改为授权状态，并保留 validation、Docker 与 hosted claim 为 false；运行过程中不再设置 planning critic、independent reviewer 或第二个人工继续门。

## 1. 唯一设计真值与优先级

正式 Controller 必须按以下顺序读取，后者覆盖冲突字段：

```text
prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment02_controller_only_interactive_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment03_final_audit_20260801.yaml
```

`prompts/tasks/20260801_care_ase_final_model_planning_review.md` 是历史审查记录，不是 runtime 权限或科学字段来源。当前 `planning_review_required: false`、`review_required: false`，不得恢复其中已经被 Amendment02/03 取代的 reviewer、a100 mirror 或候选提交顺序。

不可降级的模型边界：

- 完整继承 stock encoder、bottleneck、低中分辨率 decoder；anatomy 保留 stock 最高两级路径。
- scar 和 pure-edema 各复制 stock 最高两级完整 decoder stage，包括 transition、skip fusion、卷积块和 deep supervision classifier。
- 所有新证据只能通过零初始化残差投影或 Amendment03 冻结的 extent/wall ramp 进入；step-0 anatomy、scar、edema final logits 与 stock 对应行最大绝对误差均不超过 `1e-6`。
- 正常推理不得读取、叠加、蒸馏或 fallback 到 stock class4/class5 logits。
- no-T2 使用排除 class4 的五类竞争；edema-exclusive loss 精确为零，edema-exclusive 参数梯度最大绝对值精确为 `0.0`。
- Stage C 只使用每 fold `actual-train complete`；inner、outer 与全部80例均禁止进入。
- 每 fold 固定使用完整 `step14000` checkpoint。inner 每2000步只做描述性监控，不得选择 checkpoint 或改变训练。
- early Dice、视觉差、loss 波动或 named hard case 暂未改善，均不能阻止 W3，也不能跳过 Stage A/B/C。

## 2. Agent Flow

```text
GPT Planner / user
-> one Controller goal
   -> one Executor
   -> Mapper final
   -> strict Validators
   -> Controller verification and same-goal repair loop
   -> main lightweight commit
   -> push origin/main
   -> verify SHA equality
   -> notification
```

`parallel_execution_allowed: false` 约束的是 Agent/Executor，不禁止 Amendment02/03 明确授权的 fold3 Slurm batch 与 fold2 interactive 运行并行。Executor 不能宣布 Goal 完成。Controller 是唯一协调者和验收者；仍有授权范围内修复时，`NEEDS_REPAIR` 只是内部继续状态。

## 3. 不可中断任务图

```text
W0 evidence/split/asset/resource freeze
 -> W1 full implementation
 -> W2 real-case preflight and mandatory same-goal repair
 -> W3 fold2/fold3 exact 14000-step training
 -> W4 step14000 full-state reload and freeze
 -> W5 one-time outer evaluation, interventions and hard-case atlas
 -> W6 aggregation, mapper, validators and Controller verification
 -> commit main, push origin/main, verify SHA and notify
```

`NO_RUN`、`NEEDS_IMPLEMENTATION`、`PREFLIGHT_NEEDS_IMPLEMENTATION`、submitted、pending、running、preempted、startup-failed、partial checkpoint 与 awaiting sacct 都不是终态。W3 只依赖 W2 implementation PASS，不依赖早期科学分数。

## 4. W0：同步、资产、split、资源与存储冻结

必须执行并记录：

```bash
git fetch origin main --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline -12 origin/main
```

必须读取项目协议、CURRENT、wiki、Slurm/mapper skill、五份设计真值、指定 evidence 目录和 presentation PDF，并视觉读取 SRR-v2/v2.5/v3、MMRD、Cascade、DG、ARC、PRISM、MyoWall、MoSAIC 与 V4 atlas。若 CURRENT/wiki 与更新后的 main 不一致，必须把旧状态标为 stale，不得用旧状态覆盖当前源码和最新提交。

必须实时核验既有 allocation：

```text
61220581 | CareDPR5d | htzhulab | aereinh | g1807htzh01
```

最低检查：

```bash
squeue -u "$USER" -p htzhulab -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
squeue -j 61220581 -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
scontrol show job 61220581
srun --jobid=61220581 --overlap /users/a/e/aereinh/CARE/envs/env_CARE/bin/python -c 'import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))'
```

W0 还必须：

- 生成 train/inner/outer case list、hash 与全零交集证明；
- 冻结 fold2/fold3 stock checkpoint、plans、preprocess 与 canonical patient-held-out OOF prediction manifest；
- 从 `actual-train` 计算 scar/edema area reference，不得读取 inner/outer；
- 用真实 checkpoint 序列化测量存储需求，检查 bytes、inode、quota、fsync 与 atomic rename；
- 用至少20个真实 optimizer steps、checkpoint 与一次 full-volume eval 估计剩余时长；
- 在任何正式 W3 命令前写 replacement allocation、fold3 takeover 和 watcher 状态机。

W0 exact outputs 至少包括：

```text
results/20260801_care_ase_final_model/controller_context.json
results/20260801_care_ase_final_model/controller_ledger.csv
results/20260801_care_ase_final_model/controller_bootstrap_snapshot.md
results/20260801_care_ase_final_model/source_commit_and_hash_manifest.json
results/20260801_care_ase_final_model/stock_fold2_fold3_checkpoint_manifest.json
results/20260801_care_ase_final_model/plans_and_architecture_receipt.json
results/20260801_care_ase_final_model/split_receipt.json
results/20260801_care_ase_final_model/split_case_lists.json
results/20260801_care_ase_final_model/split_hash_manifest.json
results/20260801_care_ase_final_model/sentinel_case_contract.json
results/20260801_care_ase_final_model/sentinel_split_authority.csv
results/20260801_care_ase_final_model/extent_area_reference_receipt.json
results/20260801_care_ase_final_model/interactive_allocation_receipt.json
results/20260801_care_ase_final_model/runtime_estimate_and_takeover_plan.json
results/20260801_care_ase_final_model/storage_quota_receipt.json
```

实现缺口、allocation identity mismatch 或剩余时长不足都先进入同 Goal 修复，不是科学阻塞。

## 5. W1：完整实现门

Exact contract 与三份 amendment 声明的 source/classes/runtime helper 必须全部真实实现。AST/runtime/diff 必须拒绝：

```text
pass / NotImplementedError / random output / fixed-zero placeholder
module declared but not called
loss declared but absent from total loss
encoder-only inheritance / decoder reset / shallow D0 pathology head
random anatomy decoder or incomplete stock top-stage clone
stock class4/class5 logits entering normal final
scar proposal, center, context, edema injury, boundary, context, extent or wall without declared final-logit entry
separate duplicate scar slice-presence heads
no-T2 class4 gradient through final competition
Stage C containing inner/outer/all-80
hard-negative manifest not consumed by sampler
inner-selected checkpoint or per-pathology checkpoint splicing
hard ROI / hard wall / scar priority / dictionary / prototype / query
nonouter sentinel controlling promotion
missing runtime allocation/lock/watcher helper
```

W1 必须写：

```text
implementation_snapshot.md
source_diff_summary.md
contract_coverage.json
stock_clone_and_parity_receipt.json
parameter_group_coverage_receipt.json
component_final_logit_wiring_receipt.json
runtime_helper_contract_receipt.json
```

`remaining_gap_count` 必须为0。缺 module/head/loss/sampler/evaluator/runtime helper 是 W1 repair，不是 block。

## 6. W2：真实病例 preflight 与强制 repair

固定病例：

```text
Case2019 complete CenterB
Case3008 complete CenterC
Case1045 LGE-only
Case7009 LGE+C0
```

必须在 live htzhulab allocation 中证明：

1. stock compatibility 与 anatomy/scar/edema final-logit step0 parity；
2. normal forward 不读取 stock pathology logits；
3. 每个声明组件按 Amendment03 真正进入 final logits；
4. 所有 loss denominator、finite value 和直接梯度有效；
5. no-T2 five-class competition与 edema-exclusive gradient max abs `0.0`；
6. one-batch overfit 中 scar、edema、final competition 均下降；
7. exact scheduler、named optimizer groups、bf16/fp32 reduction 与 gradient accumulation 符合合同；
8. save/reload 覆盖完整 state、ramp、next-batch hash，并在 optimizer-step 边界精确续跑；
9. full-volume one-case sliding-window inference；
10. 每个预声明 module-off 干预产生并记录 final-logit/label delta；
11. Stage C loader 只读 actual-train complete；
12. sentinel authority、fixed-step14000 checkpoint 与 known-bad 全部 fail closed；
13. allocation replacement、fold3 atomic lock、watcher restart、secondary accounting 和 push retry 状态机通过无训练副作用的 dry-run。

每一失败类最多三次同合同 repair。不得更改 blueprint、split、14000步、loss权重、metric、decode、promotion 或外部资源权限。三次仍无法完成真实 forward/backward 时，Controller 才能按 Amendment02 阻塞边界判断。

## 7. W3：interactive-first 且不得 No-Run

所有主要训练优先使用：

```bash
srun --jobid=61220581 --overlap <exact command>
```

每 fold 固定七个连续 `2000-step` chunk：Stage A 1个、Stage B 4个、Stage C 2个，总计 `14000` optimizer steps；checkpoint 每1000步。chunk 只是恢复边界，不得重置 global/stage step、scheduler、optimizer moments、RNG、sampler、batch descriptor、ramp 或 next-batch hash。

固定调度：

1. fold2 先在既有 allocation 运行。
2. fold3 可作为唯一并行训练 job 提交到 `htzhulab`，使用同 code/config/split/budget 与独立 runtime/log。
3. batch 与 interactive 在每个 fold3 chunk 前竞争 shared atomic mkdir lock；loser 必须在读取训练 batch 前退出并记 zero credit。
4. fold3 batch 已启动并持锁时，让其完成，interactive 不重复。
5. fold2 完成而 fold3 batch 仍 pending 时，执行 `scancel` 并按 Amendment03 轮询；若取消期间转为 running，由 atomic lock 决定唯一 winner。
6. 禁止自动转到 a100、volta 或其他 partition。
7. 既有 allocation 无法覆盖剩余工作时，在其过期前按 Amendment03 exact template 提交 `CareASE5d` htzhulab allocation holder；只在当前 chunk terminal、checkpoint reload PASS 后把新 chunk 接到 replacement allocation。
8. startup/preemption 失败为 zero credit，按合同重试；pending parallel job 不得阻止 interactive 串行进度。
9. `care_ase_final_model` tmux watcher 必须持续记录 heartbeat、hash、job/chunk owner 与下一非终态 wave；Controller 进程中断后从状态文件恢复。
10. sacct 延迟先自动轮询，再按 Amendment03 双重 secondary accounting；sacct latency 本身不得成为 block。

Stage A/B/C 无论早期指标如何都必须完成。低分只能影响最终科学 token，不能改变执行预算。

## 8. W4：固定终点 checkpoint

每 fold 唯一正式 checkpoint：

```text
checkpoint_step14000.pt
```

inner full-volume 结果只用于显示训练轨迹、数值异常与机制健康，不得选择 checkpoint。W4 必须完整 reload step14000 state dict，并证明：

```text
checkpoint_step: 14000
outer_access_count_before_freeze: 0
model_optimizer_scheduler_ramp_sampler_hash_reload: PASS
```

必须写：

```text
inner_monitor_casewise.csv
inner_monitor_summary.csv
checkpoint_freeze_receipt.json
full_reload_parity_receipt.json
```

禁止自动挑选最佳 checkpoint、同折不同病种 checkpoint、权重平均、参数拼接、inner/outer 调参和 posthoc threshold。

## 9. W5：一次 outer、hard cases 与可证伪机制

step14000 freeze 后，每 fold outer 只读一次。报告 Dice、HD95/exact HD mm、precision、sensitivity、lesion/small-lesion recall、component、remote/blood-pool FP、volume ratio、help/harm、CenterB/CenterC。

atlas 固定包含：

```text
Case3008 Case3009 Case3027 Case3012 Case2034 Case2025
Case2019 Case2012 Case2009 Case1045 Case1029 Case8021
```

每例必须标记 `actual_train/inner/outer`。只有 outer 病例可进入 promotion；train/inner 只能解释机制。Case3008/3009 非 outer 时，使用冻结的 CenterC severe-underactivation subgroup；若不足两例，按 Amendment03 取 stock sensitivity 最低两例；outer CenterC T2-present 总数不足两例时，edema promotion 失败但 Goal 继续聚合，不得 block。Case2009 非 outer 时只作描述性诊断。

每例显示原始模态、GT、stock、CARE-ASE、scar occupancy/center/context、edema injury/extent/boundary/context、soft-wall、FP/FN 和所有预声明 module-off。干预必须同 checkpoint/case/input/sliding-window/decode，报告 Amendment03 的 final-logit、final-label 与病例级指标。模块存在、梯度非零或中间图好看不构成机制成功。

最终 promotion 使用 fold2+fold3 pooled outer casewise 行和同病例 patient-held-out stock baseline。不得用 MoSAIC selector、validation disagreement 或 named sentinel 改模型。

## 10. 严格阻塞边界

以下不是 block 理由：实现缺口、preflight bug、低Dice、视觉不佳、loss波动、某个stage或hard case暂未改善、单次startup failure、短期pending、parallel job未启动、既有allocation剩余时间不足、sacct延迟或push单次失败。

只有 Amendment02 明确列出的不可修复数据/checkpoint/仓库/文件系统问题、24小时没有可用 htzhulab 资源，或同一合同失败类三次真实修复仍无法 forward/backward，才允许 `OPERATIONALLY_BLOCKED`。blocked packet 必须包含 attempt lineage、minimal reproducer、diff、hash、已尝试修复和下一动作。

## 11. W6：Controller 终态、push 与邮件

不启用 critic/reviewer。固定顺序：

```text
terminal achieved 或 blocked evidence aggregation
-> mapper final
-> strict validators
-> Controller 核对真实 diff、合同、训练、评价、runtime、accounting 与 evidence
-> create main lightweight commit
-> push origin/main with Amendment03 retry policy
-> verify local main == origin/main SHA
-> write notification_brief.json
-> ./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

无论 achieved 还是 blocked，都必须 push 和通知；不得停在 pending、monitor、未聚合、未commit、未push或SHA不一致状态。禁止 force push、自建 SMTP、提前通知、validation/Docker 上传或 hosted claim。

## 12. 当前边界与未来激活

当前仍是设计草案：

```text
allow_execution: false
allow_training: false
allow_slurm_submission: false
allow_current_or_wiki_update: false
allow_runtime_commit_push_notify: false
```

未来正式授权必须在启动前一次性设置：

```text
status: AUTHORIZED_BY_USER
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
new_training_authorized: true
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
```

缺失或错误字段是 W0 fail-closed repair，不得被转成 No-Run 或第二个人工继续门。
