---
task_key: 20260801_care_ase_final_model
task_kind: scientific_milestone
task_type: final_asymmetric_pathology_model
status: DRAFT_REVISE_NOT_AUTHORIZED
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
continuity_backend: slurm_dependency
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/tasks/20260801_care_ase_final_model_planning_review.md
planning_review_token: CARE_ASE_CONTROLLER_REVISE
planning_reviewed_commit: null
review_required: true
review_mode: independent_thread
reviewer: separate_readonly
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
implementation_contract_amendment_path: prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml
---

# CARE-ASE Final Model Controller — REVISED DRAFT

当前文件仍不授权实现、训练、Slurm、CURRENT/wiki 前移或 runtime push。后续正式授权时，必须一次性冻结 reviewed commit、执行权限和 commit/push/notify 权限；运行中不得再设置第二个人工继续门。

## 1. 冻结设计真值

执行时必须同时读取，冲突时 amendment 优先：

```text
prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml
```

不可降级的核心是：

- 保留完整 stock encoder、bottleneck、低中分辨率 decoder；anatomy 保留原 stock 最高两级成熟路径；scar/edema 各复制最高两级 stock decoder stage，而不是随机重建小头。
- 新 modality/proposal/soft-wall/extent/context 信息只能通过零初始化残差投影进入，step0 anatomy/scar/edema logit parity 均 `<=1e-6`。
- 正常 final 不读取、相加或回退到 stock class4/class5 logits。
- no-T2 使用排除 class4 的五类最终竞争，edema-exclusive 参数梯度精确为0。
- Stage C 只读每 fold `actual-train complete`；禁止 inner/outer/全部80例泄漏。
- 每 fold 只选择一个完整 checkpoint；禁止病种或 anatomy 跨 step 拼接共享参数。
- early metric 不能阻止 W3 或跳过 Stage A/B/C。

## 2. 单 Executor 与 Controller 权限

模型、loss、sampler、conditional competition 和 trainer 高度耦合，本草案只允许一个 Executor，避免并行 worktree 合并时删模块或产生接口漂移。fold2/fold3 只在 Slurm runtime 并行。

Executor 执行代码和命令，但不能宣布任务完成。Controller 必须检查真实 diff、runtime tensor authority、训练预算、Slurm accounting、aggregation、validator 和 reviewer；同范围缺陷必须退回同一 Executor 修复。

## 3. 不可中断任务图

```text
W0 evidence/split/asset freeze
 -> W1 full implementation
 -> W2 real-case preflight + same-goal repair loop
 -> W3 fold2/fold3 formal 14000-step training
 -> W4 single-checkpoint reload + inner freeze
 -> W5 one-time outer + interventions + atlas
 -> W6 terminal aggregation + mapper + validator
 -> local candidate commit
 -> independent reviewer at fixed candidate SHA
 -> repair/rerun if revise
 -> exact reviewed SHA push + notify only if start-time authorized
```

`W1/W2` 不能以 `NO_RUN`、`NEEDS_IMPLEMENTATION`、`PREFLIGHT_NEEDS_IMPLEMENTATION` 结束。`W3` 只依赖 implementation PASS，不依赖早期科学分数。submitted、pending、running、preempted、startup-failed、partial checkpoint、awaiting sacct 均不是完成。

## 4. W0 必须读取与输出

必须 fetch 最新 `origin/main`，读取项目协议、当前机器真值、Slurm/mapper skill、v2 设计文件、指定结果目录与 `docs/presentation/20260801/presentation-final.pdf`。必须视觉读取：SRR-v2/v2.5/v3、MMRD、Cascade、DG、ARC、PRISM、MyoWall、MoSAIC 与 V4 atlas。

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
```

stock checkpoint/plans/split 不可读，或 train/inner/outer 交集非空，才允许 operational block。不得用旧 receipt、相似文件或自然语言代替。

## 5. W1 全实现门

Exact contract 的 required files/classes 必须全部为真实实现。AST/runtime/diff 必须拒绝：

```text
pass / NotImplementedError / random output / fixed-zero placeholder
module declared but not called
loss declared but absent from total loss
encoder-only inheritance / decoder reset / shallow D0 pathology heads
random anatomy decoder or missing stock top-stage clones
stock class4/5 logits entering normal final
no-T2 class4 gradient through final competition
Stage C dataset containing inner/outer/all-80
hard-negative manifest not consumed by sampler
per-pathology checkpoint splicing
hard ROI / hard wall / scar priority / dictionary / prototype / query
```

W1必须写 `implementation_snapshot.md`、`source_diff_summary.md`、`contract_coverage.json`、`stock_clone_and_parity_receipt.json`，且 `remaining_gap_count: 0`。任何 gap 都在本 Goal 继续实现。

## 6. W2 真实 preflight

固定病例：

```text
Case2019 complete CenterB
Case3008 complete CenterC
Case1045 LGE-only
Case7009 LGE+C0
```

必须证明：

1. stock compatibility 与 anatomy/scar/edema step0 parity；
2. normal forward 不读取 stock pathology logits；
3. 所有合同输出、loss denominator、finite value和直接梯度；
4. no-T2 five-class final competition与 edema-exclusive gradient max abs `0.0`；
5. one-batch overfit 中 scar、edema、final competition 均下降；
6. save/reload 包含 model/optimizer/scheduler/RNG/sampler/batch cursor并保持输出一致；
7. full-volume sliding-window inference；
8. module on/off改变对应中间量和 final labels；
9. Stage C loader只读 actual-train complete；
10. loader拒绝跨 step参数拼接；
11. known-bad 全部 fail closed。

每类失败最多3次同合同 repair；不得改变 blueprint、split、budget、loss权重、metric或科学语义。三次仍失败时，只有完整 attempt/diff/reproducer 与不可修复证据才可 operational block。

## 7. W3 Slurm 与 exact resume

每 fold 七个 `2000-step` chunk：Stage A 1个、Stage B 4个、Stage C 2个，总计14000步。每 job walltime `<=8h`。训练依赖 `afterok`，所有 attempt 的 finalizer/accounting 用 `afterany`。正式 Python 固定：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

禁止裸 `python`。

路由：先 `htzhulab`；2小时仍 pending，提交同 fold/chunk 隔离的 `a100-gpu` mirror；atomic winner lock决定唯一正式 attempt，启动后取消 pending mirror；V100不进入本合同。所有兼容分区连续12次、每2小时均未启动，才可24小时 scheduler block。

startup/preemption同语义重试各2次，unknown 0次，失败 credit 为0。checkpoint必须保存 model、optimizer、scheduler、precision state、global/stage step、Python/NumPy/Torch/CUDA RNG、sampler cursor、batch descriptor cursor、code/config/split hashes。resume必须证明无step reset、overlap、gap或duplicate。

Controller必须持续到全部 chunk terminal、sacct闭合、runtime aggregation完成。

## 8. W4 单一 checkpoint

候选 step固定：`4000,6000,8000,10000,12000,14000`。每 fold 用 contract 的 joint score 选择一个完整 checkpoint；同分选更晚 step。选择后重新加载整个 state dict，并写：

```text
checkpoint_selection_casewise.csv
checkpoint_selection_summary.csv
checkpoint_freeze_receipt.json
full_reload_parity_receipt.json
outer_access_count_before_freeze: 0
```

## 9. W5 outer 与机制证据

freeze 后每 fold outer只读一次。不得调整 threshold、extent系数、checkpoint、source或decode。必须报告 Dice、HD95/exact HD mm、precision、sensitivity、lesion/small-lesion recall、component、remote/blood-pool FP、volume ratio、help/harm、CenterB/CenterC。

atlas固定包含：

```text
Case3008 Case3009 Case3027 Case3012 Case2034 Case2025
Case2019 Case2012 Case2009 Case1045 Case1029 Case8021
```

每例显示原始模态、GT、stock、CARE-ASE、scar proposal/center/context、edema injury/extent/boundary、soft-wall、FP/FN和预声明module-off。Controller视觉核对病例ID、slice、orientation、label和prediction provenance。

干预必须同 checkpoint/case/decode，报告 changed voxels、final-label delta、Dice、HD95、remote FP、component和volume ratio。module存在或梯度非零不是机制成功。

## 10. 终态、Reviewer、push/notify顺序

固定顺序：

```text
terminal runtime aggregation
 -> mapper final
 -> strict validator PASS
 -> create local candidate commit
 -> independent reviewer read-only checkout at that exact candidate SHA
 -> if revise: repair and rerun from earliest affected wave, create new candidate SHA
 -> reviewer PASS on current candidate SHA
 -> if start-time authorized, fast-forward push that exact reviewed SHA to main
 -> verify remote SHA equality
 -> write notification_brief.json
 -> invoke existing notifier once
```

Reviewer必须检查成熟 decoder clone、no-T2零梯度、Stage C无泄漏、14000步、resume连续性、单checkpoint reload、outer access count、final-output interventions与promotion token。

Reviewer tokens：

```text
CARE_ASE_REVIEW_PASS
CARE_ASE_REVIEW_REVISE_IMPLEMENTATION
CARE_ASE_REVIEW_REVISE_EVIDENCE
```

implementation revise 使受影响 runtime 失效，必须从最早受影响 wave 重跑；evidence revise 至少重新 aggregation、validator 与 review。Reviewer未PASS禁止push；reviewed SHA与pushed SHA必须完全相同。

未来正式启动若已授权，push后调用：

```text
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

禁止自建SMTP、提前通知、validation/Docker上传或hosted claim。

## 11. 当前草案边界

```text
allow_execution: false
allow_training: false
allow_slurm_submission: false
allow_current_or_wiki_update: false
allow_runtime_commit_push_notify: false
```

本轮仅落库设计修订。下一次独立复审通过后，用户才决定是否把本草案转换为正式的一次性授权合同。
