---
task_key: 20260801_care_ase_final_model
task_kind: scientific_milestone
task_type: final_asymmetric_pathology_model
status: DRAFT_REVIEW_PENDING_NOT_AUTHORIZED
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
---

# CARE-ASE Final Model Controller — CONTROLLER-ONLY INTERACTIVE DRAFT

当前文件只供下一轮 GPT 设计审核，不授权实现、训练、Slurm、CURRENT/wiki 前移或 runtime push。未来正式授权时必须一次性打开执行、训练、main commit、`origin/main` push 和 terminal notifier 权限；运行中不再启用 planning critic、独立 reviewer 或第二个人工继续门。

## 1. 冻结设计真值

执行时按以下优先级读取，后者覆盖冲突字段：

```text
prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment02_controller_only_interactive_20260801.yaml
```

不可降级的核心：

- 保留完整 stock encoder、bottleneck、低中分辨率 decoder；anatomy 保留原 stock 最高两级路径；scar/edema 各复制最高两级 stock decoder stage，不得随机重建小头。
- modality、proposal、soft-wall、extent、context 只通过零初始化残差投影或 Amendment02 冻结的确定性 ramp 进入；compatibility/step0 anatomy、scar、edema final logit parity 均 `<=1e-6`。
- 正常 final 不读取、相加、蒸馏或回退到 stock class4/class5 logits。
- no-T2 使用排除 class4 的五类最终竞争，edema-exclusive 参数梯度精确为0。
- Stage C 只读每 fold `actual-train complete`；禁止 inner、outer 或全部80例泄漏。
- 每 fold 只选择一个完整 checkpoint；禁止病种或 anatomy 跨 step 参数拼接。
- sentinel case 必须标记 train/inner/outer；只有 patient-held-out outer sentinel 可进入 promotion gate。
- early metric、视觉差或某个 hard case 暂未改善，均不能阻止 W3 或跳过 Stage A/B/C。

## 2. Agent Flow：Controller 盯住单 Executor

本任务只允许：

```text
GPT Planner / user
-> one Controller goal
   -> one Executor
   -> optional Mapper final
   -> strict Validators
   -> Controller verification and same-goal repair loop
   -> main commit + origin/main push + notifier
```

不启用 planning critic，不启用 independent reviewer。Executor 负责代码和命令，但不能宣布任务完成。Controller 是唯一协调者和验收者，必须逐 wave 检查真实 diff、tensor authority、数据划分、训练预算、interactive/Slurm accounting、aggregation、known-bad、wiki/fingerprint 和 terminal push；仍有授权范围内修复时，`NEEDS_REPAIR` 是内部继续状态，不是终态。

## 3. 不可中断任务图

```text
W0 evidence/split/asset/resource freeze
 -> W1 full implementation
 -> W2 real-case preflight + same-goal mandatory repair loop
 -> W3 fold2/fold3 formal 14000-step training
 -> W4 single-checkpoint reload + inner freeze
 -> W5 one-time outer + interventions + hard-case atlas
 -> W6 terminal aggregation + mapper + validator + Controller verification
 -> commit main + push origin/main + verify SHA + email
```

`W1/W2` 不能以 `NO_RUN`、`NEEDS_IMPLEMENTATION`、`PREFLIGHT_NEEDS_IMPLEMENTATION` 结束。W3只依赖 implementation PASS，不依赖早期科学分数。submitted、pending、running、preempted、startup-failed、partial checkpoint、awaiting sacct 均不是完成。

## 4. W0 强制同步、读取和冻结

必须 fetch 最新 `origin/main`，确认本地 `main` 与远端关系，读取项目协议、CURRENT、wiki、Slurm/mapper skill、全部 v2 设计文件、指定结果目录和 `docs/presentation/20260801/presentation-final.pdf`。必须视觉读取 SRR-v2/v2.5/v3、MMRD、Cascade、DG、ARC、PRISM、MyoWall、MoSAIC 和 V4 atlas。

必须实时核验 interactive allocation：

```text
job id: 61220581
partition: htzhulab
job name: CareDPR5d
user: aereinh
node: g1807htzh01
```

最低检查：

```bash
squeue -u "$USER" -p htzhulab -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
squeue -j 61220581 -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
scontrol show job 61220581
srun --jobid=61220581 --overlap /users/a/e/aereinh/CARE/envs/env_CARE/bin/python -c 'import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))'
```

W0 exact outputs：

```text
results/20260801_care_ase_final_model/controller_context.json
results/20260801_care_ase_final_model/controller_ledger.csv
results/20260801_care_ase_final_model/controller_bootstrap_snapshot.md
results/20260801_care_ase_final_model/source_commit_and_hash_manifest.json
results/20260801_care_ase_final_model/stock_fold2_fold3_checkpoint_manifest.json
results/20260801_care_ase_final_model/plans_and_architecture_receipt.json
results/20260801_care_ase_final_model/split_receipt.json
results/20260801_care_ase_final_model/split_case_lists.json
results/20260801_care_ase_final_model/sentinel_case_contract.json
results/20260801_care_ase_final_model/sentinel_split_authority.csv
results/20260801_care_ase_final_model/interactive_allocation_receipt.json
results/20260801_care_ase_final_model/runtime_estimate_and_takeover_plan.json
```

stock checkpoint/plans/split真正不可读，或train/inner/outer交集非空，才可能进入阻塞判定。interactive身份或剩余时长不符时应先走资源修复/替换，不得把它当科学终态。

## 5. W1 全实现门

Exact contract及两份amendment的required files/classes必须全部为真实实现。AST/runtime/diff必须拒绝：

```text
pass / NotImplementedError / random output / fixed-zero placeholder
module declared but not called
loss declared but absent from total loss
encoder-only inheritance / decoder reset / shallow D0 pathology heads
random anatomy decoder or missing stock top-stage clones
stock class4/5 logits entering normal final
extent/wall direct bias破坏step0 parity
no-T2 class4 gradient through final competition
Stage C dataset containing inner/outer/all-80
hard-negative manifest not consumed by sampler
per-pathology checkpoint splicing
hard ROI / hard wall / scar priority / dictionary / prototype / query
nonouter sentinel case controlling promotion
```

W1必须写 `implementation_snapshot.md`、`source_diff_summary.md`、`contract_coverage.json`、`stock_clone_and_parity_receipt.json`，且 `remaining_gap_count: 0`。任何gap都在本Goal继续实现；缺module/head/loss/sampler/evaluator不是block理由。

## 6. W2 真实 preflight 与强制 repair

固定病例：

```text
Case2019 complete CenterB
Case3008 complete CenterC
Case1045 LGE-only
Case7009 LGE+C0
```

必须在 interactive allocation 中证明：

1. stock compatibility与anatomy/scar/edema step0 final parity；
2. normal forward不读取stock pathology logits；
3. 所有合同输出、loss denominator、finite value和直接梯度；
4. no-T2 five-class competition与edema-exclusive gradient max abs `0.0`；
5. one-batch overfit中scar、edema和final competition均明显下降；
6. save/reload包含model/optimizer/scheduler/RNG/sampler/batch cursor及extent ramp state；
7. full-volume one-case sliding-window inference；
8. module on/off改变对应中间量和final labels；
9. Stage C loader只读actual-train complete；
10. sentinel authority不允许train/inner病例进入promotion；
11. known-bad全部fail closed。

每类失败最多3次同合同repair；不得改变blueprint、split、budget、loss权重、metric或科学语义。三次仍失败时，必须有完整attempt/diff/reproducer，并由Controller确认无同范围修复后才可block。

## 7. W3：interactive优先、可并行但绝不等待到No-Run

所有主要模型工作优先在现有 interactive job `61220581` 上通过以下形式运行：

```bash
srun --jobid=61220581 --overlap <exact command>
```

每 fold 保持七个连续 `2000-step` exact-resume chunk：Stage A 1个、Stage B 4个、Stage C 2个，总计14000步；checkpoint每1000步。chunk只是恢复边界，不能重置stage、scheduler、sampler或batch cursor。

固定调度：

1. fold2先在`61220581`运行。
2. 需要并行时，可同时把fold3提交到`htzhulab`，必须与interactive运行使用相同code/config/split/budget，并隔离runtime/log/lock。
3. 若fold3 batch已经启动，让其完成，不得再在interactive重复。
4. 若fold2完成时fold3仍pending，立即取消pending fold3 job，并在`61220581`中串行继续fold3。
5. 禁止自动转向a100、volta或其他partition。
6. W3前根据真实preflight吞吐量与`scontrol`剩余时长评估；若现有allocation无法覆盖剩余工作，必须在其过期前申请/提交新的`htzhulab` interactive allocation，并保持exact resume，不得返回Planner或写No-Run。

startup/preemption同语义重试各2次，unknown 0次，失败credit为0。Controller必须持续到全部step terminal、sacct/interactive accounting、runtime aggregation闭合。

## 8. W4 单一 checkpoint

候选step固定：`4000,6000,8000,10000,12000,14000`。每fold用冻结joint score选择一个完整checkpoint；同分选更晚step。选择后重新加载整个state dict，并写：

```text
checkpoint_selection_casewise.csv
checkpoint_selection_summary.csv
checkpoint_freeze_receipt.json
full_reload_parity_receipt.json
outer_access_count_before_freeze: 0
```

## 9. W5 outer、hard cases与机制证据

freeze后每fold outer只读一次。不得调整threshold、extent系数、checkpoint、source或decode。必须报告Dice、HD95/exact HD mm、precision、sensitivity、lesion/small-lesion recall、component、remote/blood-pool FP、volume ratio、help/harm、CenterB/CenterC。

atlas固定包含：

```text
Case3008 Case3009 Case3027 Case3012 Case2034 Case2025
Case2019 Case2012 Case2009 Case1045 Case1029 Case8021
```

每例必须标明`actual_train/inner/outer`。只有outer病例可进入promotion；其余只能解释机制，不得选择checkpoint或改变模型。若Case3008/3009不是outer，使用Amendment02冻结的CenterC severe-underactivation outer subgroup gate。

每例显示原始模态、GT、stock、CARE-ASE、scar proposal/center/context、edema injury/extent/boundary、soft-wall、FP/FN和预声明module-off。Controller视觉核对病例ID、slice、orientation、label和prediction provenance。

干预必须同checkpoint/case/decode，报告changed voxels、final-label delta、Dice、HD95、remote FP、component和volume ratio。module存在或梯度非零不是机制成功。

## 10. 允许阻塞的严格边界

Controller必须先耗尽同范围修复与资源接管。以下不是block理由：实现缺口、preflight bug、低Dice、视觉不佳、某个stage早期失败、单个startup failure、短期pending、parallel job未启动、旧interactive剩余时长不足。

只有Amendment02列明的不可修复数据/checkpoint/仓库/文件系统问题、24小时无任何可用htzhulab资源、或同一失败类3次真实修复仍无法forward/backward，才允许`OPERATIONALLY_BLOCKED`。blocked packet必须包含attempt lineage、reproducer、已尝试修复、证据路径与下一动作。

## 11. W6 Controller终态、push与邮件

不启用independent reviewer。固定顺序：

```text
terminal runtime或blocked证据aggregation
 -> mapper final（如架构/wiki变化）
 -> strict validator PASS（含achieved/blocked packet语义）
 -> Controller逐项核对diff、合同、训练、评价与证据
 -> 在main创建轻量commit
 -> push origin/main
 -> 验证local main == origin/main SHA
 -> 写notification_brief.json
 -> 调用既有notifier一次
```

未来正式启动合同必须在W0前一次性设定：

```text
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
```

无论goal achieved还是blocked，都必须完成main push与邮件通知，不得停在pending、monitor、未聚合、未commit、未push状态。push失败属于同Goal operational retry，不得立即退出。

通知只允许：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

禁止自建SMTP、提前通知、validation/Docker上传或hosted claim。

## 12. 当前草案边界

```text
allow_execution: false
allow_training: false
allow_slurm_submission: false
allow_current_or_wiki_update: false
allow_runtime_commit_push_notify: false
```

本轮只供新的GPT继续审核与必要设计修订。审核通过后，用户再决定是否把本草案转换为正式的一次性授权Controller合同。
