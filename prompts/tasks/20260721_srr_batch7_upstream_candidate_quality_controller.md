---
task_key: 20260721_srr_batch7_upstream_candidate_quality
task_kind: scientific_milestone
task_type: upstream_candidate_quality_and_source_selection_repair
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
status: READY_FOR_CONTROLLER
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260721_srr_batch7_upstream_candidate_quality_executor_plan.yaml
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
experiment_adequacy_gate: rebuild_asset_then_fixed_overfit_then_300_step_then_conditional_1200_step
route_negative_gate: planner_only
scientific_completion_gate: planner_only
diagnostic_publication_gate: false
diagnostic_publication_scope: none
blocked_after_diagnostic_publication: validation_upload,hosted_claim,fold_expansion,Cine,route_promotion,M11,Batch8
training_allowed: true
backbone_replacement_allowed: false
fold_expansion_allowed: false
cine_allowed: false
validation_upload_allowed: false
hosted_metric_claim_allowed: false
next_batch_authorization: planner_only
---

## Execution Contract

Batch 6 已经把最终输出监督和纠错门接通，但 300 步后仍只比 nnU-Net 平均高约 `+0.0017`。本任务不再把训练时间加到同一套上游候选上，而是修复 prototype/memory、spatial dictionary、proposal、scar refiner 和 proposal/refiner 来源选择，使模型先产生更可靠的新候选，再判断这些候选能否转化为明显的最终收益。

本任务只执行 Batch 7。不得更换 backbone，不得解冻或重设计 modality encoders 与 base multi-scale retrieval，不得扩 fold、启动 Cine、使用外部数据或权重、上传 validation、声称 hosted 指标、晋级路线、启动 M11 或自动启动 Batch 8。

开始前必须同步远端 `main`，确认工作树安全，并读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
results/srr_production/code_maturity/batch6_planner_audit_and_batch7_decision.md
docs/plans/laneB_round04_active_srr_batch7_upstream_candidate_quality_execution.md
configs/srr_production/myops_batch7.yaml
prompts/tasks/20260721_srr_batch7_upstream_candidate_quality_executor_plan.yaml
results/20260721_srr_batch6_final_objective_alignment/
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/srr_production/prototype_memory.py
scripts/training/run_srr_propref_myops_fold0.py
```

仓库和工作树固定为：

```text
/users/a/e/aereinh/CARE
main
```

禁止写入 `/overflow/htzhu/CARE` 和 Route A/B/C worktree。

## Controller Prompt

你是 Controller，也是 Coordinator 和 acceptance owner。你必须检查 Executor 的真实 git diff、实现语义、参数冻结、prototype/memory 来源、梯度、干预、Slurm 终态、聚合、validator、CURRENT/wiki/fingerprint 和最终本地 commit。发现同范围缺口时必须退回同一 Executor 修复，不能只相信完成 token，也不能请求 critic/reviewer 替你验收。

Controller 面向 Planner 的最终报告必须先用自然中文解释：当前真正修好了什么、为什么有效或无效、下一步应做什么、暂时不允许做什么；之后才可以列机器字段、路径和指标。

### 固定任务图

```text
B7-00 bootstrap, bind Batch6 terminal evidence and frozen contract
B7-01 rebuild trained-feature-aligned prototype/memory asset
B7-02 implement prototype-conditioned spatial retrieval
B7-03 implement dual-source proposal, differentiable refiner and source arbiter
B7-04 strict tests, real-case intervention and checkpoint roundtrip
B7-05 fixed two-case 100-step overfit
B7-06 exact 300-step fold0 upstream calibration
B7-07 conditional extension to total 1200 steps after machine gate only
B7-08 selected-checkpoint interventions, mapper/wiki/fingerprint and controller verification
```

所有阶段 blocking；B7-07 是唯一条件阶段。B7-06 gate 失败时必须跳过 B7-07，但仍执行 B7-08 形成完整负结果包。

### 不可改变的科学输入

```text
source terminal commit = f139c54fd6b55b99409fcf546a1a0e117d7aa06b
source checkpoint step = 300
source checkpoint SHA256 = 729c81e49bf846339ed2f39ef0f2656319befd2b9cfe73268d7cf501e6b40fbd
fold = 0
train cases = 176
validation cases = 44
model = SRRProposeRefineMyoPS
variant = m10_d3_hierarchical_memory_propref
encoder profile = full_4scale
base channels = 32
final mode = anchor_bounded_srr_correction
decode = outputs["logits"].argmax
primary population = positive-GT pathology cases
```

Batch 4 prototype asset只允许作为 historical intervention control；Batch 7 正式训练必须使用从 source checkpoint 和全部 176 个训练病例重建的 schema-v2 asset。

### B7-01 asset 重建验收

必须新增或修改：

```text
scripts/srr_production/build_srr_batch7_prototype_memory.py
src/care_myocardium/srr_production/prototype_memory.py
src/care_myocardium/models/srr_dictionary_memory.py
```

Controller 必须确认：

1. source checkpoint SHA 与合同完全一致，并在 `model.eval()` 下提取；
2. feature stage 是 pre-M10-spatial features；
3. source case IDs 正好是 fold0 176 个训练病例，validation intersection 为零；
4. 每个 tensor 使用完整字节 SHA256；
5. 四 shard、case exclusion、zero-count mask 和 no-T2 edema exclusion 生效；
6. semantic negative 只来自真实训练病例和合同定义类别；
7. deterministic-axis、random、repeat-last 和 category copy 的正式 contribution 为零；
8. 资产 `.pt` 保持 ignored，不得 commit；只提交 manifest、counts 和 drift CSV。

Required outputs：

```text
results/20260721_srr_batch7_upstream_candidate_quality/prototype_memory_manifest.json
results/20260721_srr_batch7_upstream_candidate_quality/prototype_feature_drift.csv
results/20260721_srr_batch7_upstream_candidate_quality/semantic_negative_counts.csv
```

### B7-02/03 实现验收

必须修改或新增：

```text
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/srr_production/prototype_memory.py
src/care_myocardium/losses/srr_losses.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/training/run_srr_batch7_fixed_overfit.py
scripts/training/run_srr_batch7_formal.py
scripts/srr_production/infer_myops.py
scripts/evaluation/aggregate_srr_batch7_formal.py
scripts/evaluation/aggregate_srr_batch7_interventions.py
scripts/evaluation/validate_srr_batch7_packet.py
tests/srr_production/test_myops_batch7_upstream_candidate.py
jobs/srr_production/
```

实现必须逐项符合 `configs/srr_production/myops_batch7.yaml`：

- pre-spatial memory maps 真实传入 M10 spatial dictionary；
- discovery proposal 不读取 nnU-Net pathology probability/component；
- confirmation proposal可读取 anchor 上下文；
- proposal 两分支由 learned softmax reliability 融合，不是固定加权；
- formal refiner 类为 `DifferentiableSoftROIRefinementHead`，起点为 proposal logits；
- formal refiner 不含离散 crop/bounding-box/Python case loop；
- `PathologySourceArbiter` 学习选择 proposal/refiner；
- 正式 full candidate 不含固定 `0.5/0.5` 平均；
- Batch 6 final pathology loss、production gate repair/preserve 和 no-T2 safety 保留；
- 新增损失使用 canonical names 和配置中的精确权重。

### 必须通过的实现干预

相同 source checkpoint、相同病例、无 optimizer step：

```text
rebuilt asset vs old Batch4 asset
prototype maps on vs off
semantic negative memory on vs off
zero anchor pathology context
discovery branch on vs off
proposal only
refiner only
learned source
```

必须证明：

- prototype maps on/off 改变 spatial gates、retrieved features、proposal logits，并对至少一个真实病例改变 final logits；
- zero anchor pathology context 后 discovery proposal 仍非零、仍有 GT gradient；
- refiner output 以 proposal logits 为基线；
- learned source weights逐病种归一化为 1；
- missing-modality private/interaction slot max weight 为 0；
- no-T2 edema proposal、ROI、residual、candidate、correction、loss 和梯度全部为 0。

Required outputs：

```text
results/20260721_srr_batch7_upstream_candidate_quality/implementation_snapshot.md
results/20260721_srr_batch7_upstream_candidate_quality/asset_intervention_metrics.csv
results/20260721_srr_batch7_upstream_candidate_quality/gradient_authority.csv
results/20260721_srr_batch7_upstream_candidate_quality/checkpoint_roundtrip.json
```

### B7-05 fixed overfit

固定病例和预算：

```text
Case2002
Case1002
100 optimizer steps
formal training credit = 0
```

训练前必须通过同 Python/CUDA/config/asset/checkpoint/output/log/lock preflight。只有以下全部满足才可进入 B7-06：

```text
combined final pathology loss decrease >=20%
discovery proposal loss decrease >=20%
scar refiner repair loss decrease >=15%
source arbiter loss decrease >=10%
nonzero gradients reach spatial dictionary, proposal, refiner, source arbiter and production gate
zero anchor pathology context leaves discovery nonzero
Case1002 no-T2 edema full chain exact zero
all losses finite
save/reload final logits max delta <=1e-6
```

失败时 Controller 必须完成同范围代码修复；修复耗尽后写 `NEEDS_REPAIR`，不得提交正式训练。

### B7-06 formal 300

固定预算：

```text
optimizer = AdamW
learning rate = 1e-4
weight decay = 1e-4
grad clip = 12
patch = 12x96x96
batch size = 1
optimizer steps = exactly 300
full-volume evaluation = steps 100,200,300
cases per evaluation = 44
```

Trainable 只能是：

```text
m10_spatial_dictionary
scar/edema dictionary learned fusion and embedding
evidence_heads.scar
evidence_heads.edema
scar/edema differentiable refiners
scar/edema source arbiters
production_correction_gate
```

Frozen 必须是：

```text
all encoders
base ScaleRetrieval
all FlexibleTaskDecoder modules
evidence_heads.anatomy
rebuilt prototype/memory tensors
nnU-Net anchor
```

Controller 必须逐参数名称验证 freeze/trainable，不得只看 group label。

### B7-06 继续门

只有以下全部满足才允许 B7-07：

```text
final mean positive Dice delta >= +0.005
each pathology final Dice delta >= +0.001
proposal-only mean positive Dice delta >= +0.005
scar refiner-only Dice delta >= 0
scar learned-source no more than 0.001 below scar proposal-only
edema learned production gate captures >=60% of gate-one gain
help >= harm
HD95 relative worsening <=5% each pathology
remote-FP relative worsening <=5% each pathology
no-T2 edema exact zero
all required losses finite and gradients nonzero
```

Gate 必须由聚合脚本机器计算并写入 `training_adequacy.json`。失败动作固定为：

```text
STOP_AT_300_AND_SKIP_1200
```

不得因 step100->300 趋势上升、主观预期或队列空闲而覆盖 gate。

### B7-07 conditional 1200

仅在 B7-06 gate 为 PASS 时，从 step300 checkpoint resume 到总计 1200 steps，评价 step600/900/1200。Trainable/frozen groups、asset、split、decode、metric 和 optimizer semantics 不得改变。Training dependency 使用 `afterok`。

### Checkpoint selection

Eligibility 与排序严格读取 config。Selected checkpoint 必须 reload 后再做正式指标和最终干预；不得根据名称、最后一步或 patch loss自动选择。

### Final intervention packet

Selected checkpoint、同一 44 cases、同一 argmax decode 必须运行：

```text
anchor identity
old Batch4 asset
rebuilt Batch7 asset
prototype maps off
semantic negative memory off
zero anchor pathology context
proposal only
refiner only
learned source
GT-oracle source diagnostic only
production gate closed / learned / one
no-anchor diagnostic
```

Required outputs：

```text
results/20260721_srr_batch7_upstream_candidate_quality/training_adequacy.json
results/20260721_srr_batch7_upstream_candidate_quality/checkpoint_selection.csv
results/20260721_srr_batch7_upstream_candidate_quality/final_mechanism_interventions.csv
results/20260721_srr_batch7_upstream_candidate_quality/casewise_metrics.csv
results/20260721_srr_batch7_upstream_candidate_quality/subgroup_metrics.csv
results/20260721_srr_batch7_upstream_candidate_quality/help_harm.csv
results/20260721_srr_batch7_upstream_candidate_quality/proposal_refiner_metrics.csv
results/20260721_srr_batch7_upstream_candidate_quality/source_arbiter_metrics.csv
results/20260721_srr_batch7_upstream_candidate_quality/slurm_attempts.csv
```

### Strict validator / known-bad

Validator 必须构造并拒绝以下真实错误对象，而不是只搜索字符串：

```text
asset built from random or pretraining checkpoint
validation leakage
partial tensor hash
deterministic/random/repeated semantic negative
no-T2 edema memory vector
prototype maps omitted or all-zero while claimed wired
missing-modality slot nonzero
discovery collapses when anchor pathology context zero
formal refiner starts from evidence logits
formal refiner uses discrete crop/bounding box
fixed 0.5 proposal/refiner average remains
scar refiner harmful but continuation passes
1200 submitted after 300 gate fail
checkpoint not reloaded or decode mismatch
monitor packet claimed complete
runtime push or runtime review.md
```

### Slurm boundary

```text
Python: /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
primary: htzhulab
900s pending mirror: a100-gpu
volta: forbidden
max runtime per stage: 14400s
winner lock: required
isolated attempt directories: required
training dependencies: afterok
finalizer/accounting: afterany
```

Controller 负责到所有 attempts terminal、post-completion aggregation、mapper final、wiki/fingerprint 检查、validator、`git diff --check` 和单个本地轻量 commit完成。`SUBMITTED/PENDING/RUNNING/NEEDS_MONITOR/AWAITING_SACCT` 均不是完成。

### Git and publication boundary

Runtime roles不得 push。不得跟踪 checkpoint、prototype `.pt`、NIfTI、raw data、大日志、secret、upload package 或 hosted artifact。

Batch 7 达到任何本地等级都不得自动扩 fold、上传、晋级或启动 Batch 8。

### Controller report ending

报告首段必须是自然中文判断，随后以以下机器字段结束：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
contract_compliance_status:
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
selected_checkpoint_sha256:
final_mean_positive_dice_delta:
scar_positive_dice_delta:
edema_positive_dice_delta:
proposal_only_mean_positive_dice_delta:
scar_refiner_only_dice_delta:
edema_gate_capture_fraction:
git_commit_decision:
git_push_decision: NO_PUSH
blocked_actions: backbone_swap,encoder_retrieval_redesign,fold_expansion,Cine,external_data,validation_upload,hosted_claim,route_promotion,M11,Batch8
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

只有 required outputs 内容完整、所有作业终态、聚合 exit 0、mapper/wiki/fingerprint 一致、strict validator/known-bad exit 0 且本地轻量 commit 完成，才可写 `VERIFIED_COMPLETE`。这只表示 Batch 7 合同完成，不表示科学成功。

## Executor Worker Contract

Executor 只有一个，严格按 executor plan 的 wave 顺序工作。Executor 负责授权范围内的实现、测试、资产构建、Slurm 提交、聚合和证据写入，但不能宣布整个 Batch 完成，不能写 `review.md`，不能 push，不能启动下一 Batch。任何科学设计冲突必须返回 Controller，不得自行改模型、预算、split、gate 或评价语义。

所有新轻量结果写入：

```text
results/20260721_srr_batch7_upstream_candidate_quality/
```

## Mapper Contract

Mapper 在实现后和终态各运行一次。它必须检查 model/loss/dataflow/checkpoint/export、prototype/memory来源、spatial prototype conditioning、dual-source proposal、new refiner、source arbiter 和 final output effect，更新 `wiki/`、`COMPONENTS.csv`、`architecture.yaml`、图和 code fingerprint。没有 runtime 证明的组件必须保持 unverified；Mapper 不训练、不作科学晋级决定。

## Reviewer Prompt

`review_required: false`。不得启动独立 reviewer。Controller 完成后直接返回 Planner。