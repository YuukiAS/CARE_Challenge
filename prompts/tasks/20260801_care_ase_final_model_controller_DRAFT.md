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
---

# CARE-ASE Final Model Controller — REVISED DRAFT

> 当前仍是待再次审查的执行草案，不授权实现、训练、Slurm、CURRENT/wiki 前移或 runtime push。后续用户一次性授权正式执行时，必须先把授权字段、reviewed commit/hash、commit/push/notify 边界冻结在 frontmatter；运行中不得再次停下来等待人工继续。

## 1. 唯一科学任务

严格实现并验证：

```text
prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
```

v2 的关键不可替代内容：

1. stock encoder、bottleneck、低中分辨率 decoder 完整继承；scar/edema 最高两级 decoder 必须复制完整 stock stage 权重，不得随机重建或缩成固定 `64/32` 小头。
2. 正常 forward 不读取、叠加或回退到 stock class4/class5 logits；step0 parity 仅作为初始化能力审计。
3. no-T2 最终损失使用排除 class4 的五类竞争，edema-exclusive 参数梯度精确为0。
4. Stage C 只能读取每个 fold 的 `actual-train complete` 病例，不能读取 inner、outer 或全部80例。
5. 每 fold 只能选择一个完整 checkpoint，禁止 scar/edema/anatomy 从不同 step 拼接共享参数。
6. W2 implementation PASS 后自动启动 W3；早期低分不能跳过 Stage A/B/C。

## 2. 角色图

本草案改为一个 Executor。原因是模型、loss、sampler、trainer 和 conditional final competition 高度耦合；三分支并行开发会增加接口遗漏、合并删模块和 no-T2 梯度泄漏风险。

```text
Planner/User-authorized frozen contract
  -> Controller/Coordinator
       -> Executor: implementation + tests + Slurm commands + aggregation
       -> Mapper: draft/final architecture and wiki fingerprint
       -> deterministic dependency finalizer + strict validators
       -> independent read-only Reviewer
       -> Controller same-scope repair loop
       -> terminal commit/push/notify only if start-time permission allows
```

Executor 不能宣布任务完成。Controller 必须逐 wave 检查真实 diff、命令、代码路径、tensor authority、训练预算、Slurm accounting、aggregation 和 required outputs。

## 3. 强制任务图

```text
W0 远端同步、协议/图/证据读取、资产与 split 冻结
 ↓
W1 单 Executor 完成全部实现与 deterministic tests
 ↓
W2 真实病例 preflight + mandatory same-goal repair loop
 ↓ IMPLEMENTATION_PASS only
W3 fold2/fold3 七个 2000-step chunk/fold，累计 14000 steps/fold
 ↓
W4 单一完整 checkpoint reload + inner freeze
 ↓
W5 outer 一次性评价 + module interventions + atlas
 ↓
W6 mapper final + strict validator + independent reviewer + terminal accounting
 ↓
若启动合同已授权：local commit -> main push -> notification_brief -> existing notifier
否则：terminal local packet -> return to user
```

不允许出现独立 W7 人工继续门。正式用户授权必须在 W0 前一次性编码，避免完成训练后因等待第二次 prompt 形成流程性 no-run。

## 4. W0：必须读取与冻结

读取最新 `origin/main`，并完整阅读：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md

CARE-ASE v2 blueprint and exact contract
results/20260801_care_nnunet_mosaic_complementarity_closure/**
results/20260801_care_four_lane_evidence_reconciliation/**
results/20260730_care_failure_forensics_deep_research_packet/**
results/20260731_care_myopath_a0_a3_full_volume_closure/**
results/20260731_care_myowall_geometry_diagnostic_closure/**
results/20260731_care_qif_v2_signal_audit/**
docs/presentation/20260801/presentation-final.pdf
```

视觉读取并在 receipt 中记录：

```text
SRR-v2, SRR-v2.5, SRR-v3
CARE-MMRD, CARE-SRR-Cascade, CARE-DG, CARE-ARC
CARE-PRISM, CARE-MyoWall-IF, MoSAIC, V4 hard-case atlas
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
```

任一 stock checkpoint/plans/split 不可读，或 train/inner/outer 有交集，才允许 `OPERATIONALLY_BLOCKED_ASSET_OR_RUNTIME`。不得用旧 receipt 或相似路径代替。

## 5. W1：完整实现，不接受 future work

Executor 必须实现 exact contract 的全部 required files/classes。Controller 用 AST、runtime 和 diff 联合拒绝：

- `pass`、`NotImplementedError`、随机输出、固定零占位；
- module 声明但 forward 未调用；
- loss 声明但未进入总损失；
- encoder-only、decoder reset、随机浅 pathology head；
- scar/edema top stages 未完整复制 stock stage；
- stock pathology logits进入正常 final；
- no-T2 class4 仍进入最终 loss graph；
- Stage C 数据集指向全部80例或含 inner/outer；
- hard-negative manifest未被 sampler真实消费；
- scar/edema/anatomy允许跨 checkpoint拼接；
- hard ROI、hard wall、fixed scar-priority、dictionary/prototype/query 被恢复。

W1 outputs：

```text
implementation_snapshot.md
source_diff_summary.md
contract_coverage.json
stock_clone_and_parity_receipt.json
remaining_gap_count: 0
```

`remaining_gap_count > 0` 必须继续同一 Executor 实现；不是终态，也不能返回 Planner。

## 6. W2：真实病例 preflight 与 repair loop

固定病例：

```text
complete CenterB: Case2019
complete CenterC: Case3008
LGE-only: Case1045
LGE+C0: Case7009
```

必须完成：

1. stock compatibility 每尺度 FP32 parity；
2. cloned scar/edema step0 class4/class5 parity；
3. CARE-ASE normal forward 输出全部合同 key，且正常 final 不读取 stock pathology logits；
4. 每项 loss finite、有效 denominator 正确、直接梯度到目标模块；
5. no-T2 conditional five-class final loss，edema-exclusive 梯度 max abs `0.0`；
6. one-batch overfit：scar、edema、final competition 均下降；
7. save/reload 包含 model/optimizer/scheduler/RNG/sampler cursor，输出一致；
8. full-volume one-case sliding-window inference；
9. 每个辅助模块 on/off 对对应中间量及 final labels 有可测影响；
10. all known-bad fixtures fail closed；
11. Stage C loader 证明只读取 actual-train complete；
12. checkpoint loader拒绝跨 step 参数拼接。

每个 failure class 最多3次同合同 repair。repair 不能改 blueprint、split、budget、loss权重、metric或科学语义。三次后仍失败时，只有附带完整 attempt diff、错误、最小复现和“为何继续同范围修复不可能”的证据，才能 operational block；不得写 `NO_RUN`、`NEEDS_IMPLEMENTATION` 或 `PREFLIGHT_NEEDS_IMPLEMENTATION` 作为终态。

## 7. W3：不可跳过的正式训练

每 fold 七个 2000-step chunk：

```text
chunk 1: Stage A, step 0-2000
chunk 2-5: Stage B, step 2000-10000
chunk 6-7: Stage C, step 10000-14000
```

每个 chunk 单 job `<=8h`。训练 chunk 依赖使用 `afterok`；所有 attempt 的 accounting/finalizer 使用 `afterany`。正式 wrapper 固定：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

禁止裸 `python`。

### 固定路由

- 先提交 `htzhulab`。
- 2小时首次检查仍 pending，则提交同 fold/chunk 的 `a100-gpu` 隔离 mirror。
- per-fold/per-chunk atomic winner lock；一个启动后立即取消仍 pending mirror。
- V100 不进入本合同。
- 两个兼容分区连续12次、每2小时均未启动，才允许24小时 scheduler block。

startup/preemption 同语义重试各最多2次，unknown 0次。每次重试必须保持 code/config/split hash，旧 attempt 永久留 ledger，训练 credit 为0。

Controller必须持续到全部 chunk terminal。submitted、pending、running、preempted、startup_failed、partial checkpoint、awaiting sacct 都不是完成，也不能结束 Goal。

## 8. W4：单一 checkpoint 选择与 reload

候选 step：`4000,6000,8000,10000,12000,14000`。每 fold 使用 v2 contract 的 joint score 选择一个完整 checkpoint；禁止 scar、edema、anatomy分别选择或拼接共享参数。

选中后必须重新加载整个 checkpoint并写：

```text
checkpoint_selection_casewise.csv
checkpoint_selection_summary.csv
checkpoint_freeze_receipt.json
selected_state_dict_sha256
full_reload_parity_receipt.json
outer_access_count_before_freeze: 0
```

## 9. W5：outer一次性评价、干预与atlas

checkpoint freeze 后，每 fold outer 只能读取一次。decode、extent系数、threshold、checkpoint、source均不可变化。必须使用 canonical physical-space evaluator，并报告 exact contract 全部指标。

atlas至少包含：

```text
Case3008 Case3009 Case3027 Case3012 Case2034 Case2025
Case2019 Case2012 Case2009 Case1045 Case1029 Case8021
```

每例显示 LGE/T2/C0、GT、stock、CARE-ASE、scar proposal/center/context、edema injury/extent/boundary、soft-wall、FP/FN和预先声明的module-off版本。Controller必须视觉核对病例ID、slice、orientation、label和prediction provenance。

干预必须在同一 selected checkpoint、同一case、同一decode下执行，记录 changed voxels、final-label delta、Dice、HD95、remote FP、component和volume ratio。module presence或nonzero gradient不能替代final-output effect。

## 10. W6：终态闭合

Mapper final 在 reviewer 前运行，更新 root wiki/fingerprint时只能写真实 terminal 状态；未通过 reviewer 的模型不得写 candidate-ready。

Independent Reviewer 必须固定 terminal commit 的只读 checkout，检查：

- 完整 decoder clone 与正常 final 无 stock pathology shortcut；
- no-T2 class4 loss/gradient完全隔离；
- Stage C 无 inner/outer/全80例泄漏；
- 每fold足额14000步且Stage A/B/C全部完成；
- exact resume无step reset/overlap/gap/duplicate；
- 单一 checkpoint reload；
- outer access count与机器指标；
- proposal/extent/context/soft-wall真实影响final；
- promotion token与机器gate一致；
- negative是否为faithful negative。

Reviewer tokens：

```text
CARE_ASE_REVIEW_PASS
CARE_ASE_REVIEW_REVISE_IMPLEMENTATION
CARE_ASE_REVIEW_REVISE_EVIDENCE
```

REVISE 必须进入同一 Controller 的授权范围 repair loop；不得以 review revise 结束并把实现问题留给未来。

Controller terminal report 必须包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status
experiment_adequacy_decision
contract_compliance_status
required_outputs_complete
validators_passed
all_jobs_terminal
aggregation_complete
review_token
scientific_token
git_commit_decision
git_push_decision
next_required_action
```

若正式启动时已授权 commit/push：review PASS 和 strict validator PASS 后完成 lightweight local commit、push main、确认 remote SHA，随后写 `notification_brief.json` 并调用：

```text
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

禁止自建 SMTP，禁止 terminal push 前通知，禁止上传 validation/Docker或声称 hosted metric。

## 11. 当前边界

```text
allow_execution: false
allow_training: false
allow_slurm_submission: false
allow_current_or_wiki_update: false
allow_runtime_commit_push_notify: false
```

本轮只完成设计修订并推送规划文件。需要下一次独立审查通过后，用户才决定是否将本草案转成正式、一次性授权的 Controller 合同。
