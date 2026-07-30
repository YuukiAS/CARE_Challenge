---
task_key: 20260731_care_myopath_pr_a0_a3_feasibility
task_kind: scientific_milestone
task_type: mechanism_feasibility
controller_mode: controller_supervised
milestone_number: null
milestone_id: null
status: AUTHORIZED
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
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
wiki_update_required: false
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: none
reviewer: none
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: false
experiment_adequacy_gate: mechanism_feasibility_only
route_negative_gate: false
scientific_completion_gate: a0_a3_decision_only
diagnostic_publication_gate: true
diagnostic_publication_scope: results/20260731_care_myopath_pr_a0_a3_feasibility
blocked_after_diagnostic_publication: false
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
---

# CARE 单主干双病种候选生成 A0–A3 可行性实验

## 结论与任务边界

本任务不把 CARE-MyoPath-PR 当作已经获批的最终架构，也不训练完整 Proposal–Refinement 系统。

唯一目标是回答：

> 在完整保留成熟编码器与解码器能力的前提下，scar 与 pure edema 的独立病种路径和候选生成器，能否形成 nnU-Net/MoSAIC 现有预测之外的有效病灶候选，而不是再次成为模块存在、梯度非零、最终标签无收益的装饰？

只运行 A0、A1、A2、A3 四个递进版本。A3 通过前，禁止实现局部 ROI refiner、prototype memory、dictionary、稀疏 router、alignment、hard-negative replay queue、full-data training、fold expansion、validation upload 或 Docker。

## Planner visual-reading receipt

```text
diagram_versions_read:
  - SRR-v2
  - SRR-v2.5
  - SRR-v3
  - CARE-MMRD
  - CARE-SRR-Cascade
  - CARE-ARC
  - MoSAIC
visual_read_status: READ_BY_GPT_PLANNER_IN_CURRENT_PROJECT
```

从图中恢复的有效设计边界：

- SRR-v2/v2.5：模态可用性、病种专属 proposal、scar 小 ROI 与 edema 大 ROI 的差异化 refinement；
- SRR-v3：强基线保护、nnU-Net context、最终修正直接进入 logits，但 bounded correction 上限过低；
- MMRD：完整共享主干、可靠标签、no-T2 edema hygiene；
- Cascade：case-wise help/harm、remote-FP、安全门，但 prototype control 未隔离；
- ARC：单共享主体和显式 availability，但不能重置完整 decoder 后重新学习整张 mask；
- MoSAIC：病种专属专家和 anatomy context 有价值，但多模型 recipe 不作为本任务主体。

本任务只测试其中最小共同核心：

```text
完整成熟主干
+ 可靠监督
+ scar/edema 独立全局权限
+ 病种专属候选直接进入 final logits
```

## Active workspace and branch

必须在隔离 worktree 执行：

```text
worktree: /users/a/e/aereinh/CARE_worktrees/task_myopath_a0_a3_20260731
branch: task/20260731-myopath-a0-a3
base: origin/main
```

不得写主工作树或其他 task/route worktree。

## Bootstrap and required reading

先执行：

```bash
cd /users/a/e/aereinh/CARE_worktrees/task_myopath_a0_a3_20260731
git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -15
git diff --check
```

必须读取：

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
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
```

必须读取 V4 证据与 atlas：

```text
results/20260730_care_failure_forensics_deep_research_packet/CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v4.pdf
results/20260730_care_failure_forensics_deep_research_packet/v4_atlas_pages_a3_landscape.pdf
results/20260730_care_failure_forensics_deep_research_packet/DEEP_RESEARCH_MODEL_DESIGN_INPUT_20260730_v4.md
results/20260730_care_failure_forensics_deep_research_packet/v4_component_survival_ledger.csv
results/20260730_care_failure_forensics_deep_research_packet/v4_large_gain_bounds.csv
```

还必须阅读：

```text
results/20260729_care_prism_v2_backbone_repair_and_resume/**
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
```

## Parallel dependency on metric truth lane

本任务可以立即完成：

- 代码映射；
- 设计合同冻结；
- A0 实现与 identity parity；
- one-batch overfit；
- zero-credit smoke；
- Slurm wrapper/preflight；
- mapper draft。

正式 A1–A3 GPU 训练前必须读取：

```text
/users/a/e/aereinh/CARE_worktrees/task_metric_truth_20260731/results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json
```

或在该 task branch 合并/复制后读取同一相对路径：

```text
results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json
```

必须满足：

```text
metric_contract_status: PASS
```

若 receipt 尚未生成，Controller 保持等待；不得自行解释 `0.922x` 或选择指标。

## Frozen data and evaluation semantics

本任务只做单折机制诊断，不产生 promotion candidate。

开发病例使用现有 fold0 的：

```text
actual_train
inner_select: 35 cases
```

fold0 outer 已访问，只能读取历史结果，禁止本任务再次使用。

fold1 outer 保持未访问。

由于 stock fold0 nnU-Net 曾见过部分 development population，本任务的指标只能解释 matched component effect，不得写成 clean generalization 或 hosted prediction。

标签：

```text
scar = label 5
pure edema = label 4, only canonical T2-present reliable cases
edema-zone = label 4|5, diagnostic only
myocardium union = label 1|4|5
```

## Single-backbone architecture contract

只允许一个完整 3D nnU-Net/PlainConvUNet 编码器—解码器主体。

必须从 frozen stock fold0 checkpoint 完整加载：

```text
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth
```

启动时重新验证 SHA256，不得仅相信历史 manifest。

A0 关闭所有新增模块时，最终六类 logits 必须与 stock nnU-Net 在 FP32 下逐体素一致：

```text
max_abs_error <= 1e-6
changed_argmax_voxels = 0
parameter_byte_coverage >= 0.99
```

不允许只继承 encoder，不允许随机重置 decoder，不允许改变 plans、patch、normalization 或 stock output head。

## New lightweight modules

### Modality stems

三个轻量 stem：

```text
LGE: 1 -> 16 -> 32
T2: 1 -> 16 -> 32
C0: 1 -> 16 -> 32
```

每层：

```text
Conv3d(kernel=3,padding=1) -> InstanceNorm3d -> SiLU
```

每个 stem 只有两层，不构成完整 encoder。

不可用模态在 stem 输出后严格乘 availability mask 为零。

### A2 pathology global heads

从 stock decoder 最终高分辨率特征 `F_dec0` 与对应 modality stem 特征构造：

```text
scar_input = concat(F_dec0, stem_LGE, availability_broadcast)
edema_input = concat(F_dec0, stem_T2, availability_broadcast)
```

C0 不直接进入 pathology head 第一版；其解剖信息已由 stock decoder 提供。不得因“更完整”自行加入额外模态或模块。

两个独立头结构相同但参数不共享：

```text
1x1 Conv -> 64
ResidualBlock(64)
3x3 Conv -> 32
1x1 Conv -> 1 logit
```

A2 final composition：

```text
anatomy logits 0:3 = stock logits 0:3
scar logit = stock scar logit + delta_scar_global
edema logit = stock edema logit + m_T2 * delta_edema_global
```

`delta` 不设人为很小的 tanh 上界；它拥有形成新病灶的权限。但必须使用零初始化最后一层，使 step0 与 A0 完全一致。

### A3 scar proposal

输入：

```text
F_dec0
F_dec1 upsampled to full resolution
stem_LGE
soft myocardium-union probability detached
```

输出两个 full-resolution logit：

```text
p_scar_candidate
p_scar_center
```

监督：

- candidate target：scar GT 各向 2 mm 物理膨胀；
- center target：每个 scar connected component 的物理质心 3 mm 球；
- 每个 component 必须独立计入 lesion recall。

### A3 edema proposal

输入：

```text
F_dec0
F_dec1 upsampled to full resolution
stem_T2
soft myocardium-union probability detached
```

输出：

```text
p_edema_candidate
p_edema_band
```

监督只在真实 T2-present 病例生效：

- candidate target：pure-edema label 4；
- band target：pure-edema 区域沿 myocardium ring 的 3 mm 扩张带；
- no-T2 output logit hard-set to -20 before sigmoid；
- no-T2 edema loss and gradient exactly zero。

### A3 final composition

Proposal 必须直接进入 final logits：

```text
z_scar = z_stock_scar + delta_scar_global + 0.5 * p_scar_candidate
z_edema = z_stock_edema + m_T2 * (delta_edema_global + 0.5 * p_edema_candidate)
```

`0.5` 为冻结系数，本任务不得调参。

A3 不做 crop、ROI、paste-back 或 refiner。

## Variant definitions

### A0 — 完整主干 identity

新增 stem/head/proposal 均关闭。

目的：证明没有再次损坏成熟 decoder、预处理和 decode。

形式：固定 inference，不训练。

### A1 — 可靠监督与 availability 合同

架构仍为 A0；训练逻辑增加：

- availability hard mask；
- no-T2 pure-edema loss mask；
- center-balanced sampler；
- T2-present病例显式采样。

A1 只允许短程低学习率 full-model continuation，不新增 pathology head。

目的：判断正确监督语义是否至少保持基线，而不是宣称新架构增益。

### A2 — 病种独立全局权限

启用 modality stems 和两个 global pathology heads。

目的：判断 scar 与 edema 分开利用 LGE/T2 是否能产生稳定、病例外方向一致的增量。

### A3 — 病种专属 proposal 直接进入 final logits

启用 A2 + scar/edema proposal。

目的：判断新模型是否真正拥有现有 baseline 之外的病灶形成能力。

## Training budgets

所有训练均从 A0 stock checkpoint 开始，不从前一 variant checkpoint 串接；确保 matched comparison。

统一：

```text
optimizer: AdamW
weight_decay: 1e-4
batch_size_physical: 2
gradient_accumulation: 4
mixed_precision: bf16 if supported, otherwise fp16
clip_grad_norm: 12
checkpoint_every: 500 steps
validation_every: 500 steps
same seed: 20260731
same case order/sampler seed across variants
```

A1：

```text
steps: 3000
lr pretrained full network: 1e-5
```

A2：

```text
steps: 5000
lr stock backbone: 3e-5
lr new modules: 3e-4
```

A3：

```text
steps: 8000
lr stock backbone: 3e-5
lr A2 global heads/stems: 1e-4
lr proposal heads: 3e-4
```

每个 variant 独立 optimizer/scheduler。

Cosine scheduler 不得被每 step 重写 base LR。

每个正式 job 单次 walltime <= 8h；若步数无法在 8h 内完成，按 exact-resume 分段，不得减少步数。

训练依赖使用 `afterok`，finalizer 使用 `afterany`。

## Loss contracts

A1 使用 stock Dice+CE，但 pure-edema class-4 voxel loss仅在 T2-present病例激活；scar 与 anatomy 保持正常监督。

A2：

```text
L_total = L_stock_anatomy
        + L_scar_global
        + m_T2 * L_edema_global
        + 0.2 * L_stock_pathology_stability
```

其中 stability 只约束新模型在无明确新证据区域不要全面漂移，不是逐体素 identity anchor。

A3：

```text
L_total = L_A2
        + L_scar_candidate
        + 0.5 * L_scar_center
        + m_T2 * (L_edema_candidate + 0.5 * L_edema_band)
```

第一轮不得加入：

```text
prototype loss
contrastive memory
HD loss
surface loss
compactness
containment hard mask
scar-edema inclusiveness
alignment loss
uncertainty gate
```

目的是避免失败归因再次混杂。

## Sampler

病例级先按以下 strata 平衡：

```text
center
T2 presence
scar positive
pure-edema positive
scar burden quartile
pure-edema burden quartile
```

每个 batch 必须至少包含：

- 一个 scar-positive病例；
- 若存在 T2-present训练病例，一个 T2-present病例；
- safe-negative patch 不得来自 no-T2 myocardium 作为 edema negative。

Scar patch 采样：

```text
40% scar component-centered
30% myocardium boundary
30% random foreground
```

Edema patch 采样只在 T2-present：

```text
40% pure-edema centered
30% edema boundary
30% myocardium foreground
```

## Required implementation evidence

每个 variant 必须保存：

```text
model/config/split/sampler/checkpoint hashes
trainable/frozen parameter manifest
optimizer groups
actual LR curve
loss component curve
selected checkpoint reload receipt
final logits tensor statistics
casewise metrics
changed voxels vs A0
```

A2/A3 必须对 scar 与 edema 分开做 on/off intervention：

```text
disable scar head only
disable edema head only
disable scar proposal only
disable edema proposal only
```

报告：

```text
final-logit delta
changed labels
Dice
HD95
lesion recall
component count
remote FP
volume ratio
help/harm
```

梯度非零不是机制成功。

## Evaluation

只在 inner-select 35 例做固定评价。

必须报告：

Scar：

```text
Dice
HD95 mm
exact HD mm
precision
recall
lesion-wise recall
small-lesion recall
multi-component recall
pred component count
remote FP
volume ratio
help/harm vs A0
```

Pure edema，真实 T2-present inner cases only：

```text
Dice
HD95 mm
exact HD mm
precision
recall
ROI/candidate coverage
pred component count
remote FP
volume ratio
help/harm vs A0
```

No-T2：

```text
edema probability max <= 2.1e-9
edema positive voxels = 0
edema loss = 0
edema gradient = 0
```

## Continue/stop gates

### A0 gate

必须：

```text
FP32 max_abs_error <= 1e-6
changed argmax voxels = 0
stock metric reproduction within 1e-6
```

失败即 implementation repair，不得进入 A1。

### A1 gate

必须：

- scar Dice 相对 A0 不低于 0.015；
- T2-present pure-edema Dice 相对 A0 不低于 0.020；
- no-T2 safety 全通过；
- HD95 不出现系统性恶化；
- harm cases 不得超过 help cases + 20%。

失败：停止 A2/A3，判定监督/训练管线仍未保持基线。

### A2 gate

必须满足至少一项病种有效，并且另一病种不显著受损：

- scar Dice >= A1 + 0.01，或 scar lesion recall >= A1 + 0.05；
- pure-edema Dice >= A1 + 0.01，或 edema recall >= A1 + 0.05；
- 另一病种 Dice 下降不超过 0.015；
- remote FP 不得增加超过 20%；
- changed labels 不能近乎全零，也不能全图漂移。

A2 两病种均无信号：停止 A3，返回 Planner。

### A3 gate

Scar proposal：

```text
lesion-wise recall >= 0.85
GT lesion coverage >= 0.90
small-lesion recall >= A2 + 0.08
remote FP <= A2 * 1.10
```

Edema proposal：

```text
T2-present candidate coverage >= 0.90
T2-present recall >= A2 + 0.05
Dice not below A2 by more than 0.01
no-T2 exact zero
```

Final prediction：

- 至少一个病种 Dice 相对 A2 提升 >= 0.015；
- 两个病种均不得出现 harm >= 60%病例；
- proposal on/off 必须改变 final labels；
- proposal 中间指标与最终病种指标方向一致。

只有 A3 通过，Planner 才可考虑下一任务中的 ROI refinement。

A3 失败不得在本任务内添加新 loss、prototype、refiner 或更换 backbone。

## Write scope

允许写：

```text
src/care_myocardium/models/care_myopath_pilot.py
src/care_myocardium/training/care_myopath_pilot/**
scripts/training/care_myopath_pilot/**
scripts/evaluation/care_myopath_pilot/**
jobs/care_myopath_pilot/**
tests/care_myopath_pilot/**
configs/care_myopath_pilot/**
results/20260731_care_myopath_pr_a0_a3_feasibility/**
```

不得修改 stock nnU-Net source、PRISM production code、MoSAIC source、fold0 outer lock 或 production evaluator。

## Validator and known-bad

实现：

```text
scripts/validation/validate_care_myopath_a0_a3.py
tests/care_myopath_pilot/test_known_bad.py
```

必须拒绝：

1. 只继承 encoder；
2. decoder reset；
3. A0 不能逐体素复现；
4. no-T2 进入 edema loss；
5. scar/edema head共享参数；
6. proposal只用于 auxiliary loss；
7. proposal不进入 final logits；
8. on/off只有 gradient、没有 changed labels；
9. A1/A2/A3 串接 checkpoint导致不公平；
10. variant case order/augmentation不同；
11. outer用于选择；
12. edema-zone冒充 pure edema；
13. short smoke冒充正式训练；
14. scheduler被 base LR 重置覆盖；
15. proposal recall不达标仍启动 refiner；
16. A3失败后私自加 loss/module；
17. pending/running job冒充完成；
18. evaluator只有 mean Dice；
19. scar提升掩盖 edema系统性失败；
20. model/config/split/checkpoint hash缺失。

## Required outputs

```text
results/20260731_care_myopath_pr_a0_a3_feasibility/controller_context.json
results/20260731_care_myopath_pr_a0_a3_feasibility/controller_ledger.csv
results/20260731_care_myopath_pr_a0_a3_feasibility/implementation_snapshot.md
results/20260731_care_myopath_pr_a0_a3_feasibility/a0_identity_report.json
results/20260731_care_myopath_pr_a0_a3_feasibility/a1_summary.json
results/20260731_care_myopath_pr_a0_a3_feasibility/a2_summary.json
results/20260731_care_myopath_pr_a0_a3_feasibility/a3_summary.json
results/20260731_care_myopath_pr_a0_a3_feasibility/casewise_metrics.csv
results/20260731_care_myopath_pr_a0_a3_feasibility/proposal_metrics.csv
results/20260731_care_myopath_pr_a0_a3_feasibility/component_intervention.csv
results/20260731_care_myopath_pr_a0_a3_feasibility/help_harm.csv
results/20260731_care_myopath_pr_a0_a3_feasibility/slurm_accounting.csv
results/20260731_care_myopath_pr_a0_a3_feasibility/finalizer_state.json
results/20260731_care_myopath_pr_a0_a3_feasibility/strict_validator_report.json
results/20260731_care_myopath_pr_a0_a3_feasibility/known_bad_report.json
results/20260731_care_myopath_pr_a0_a3_feasibility/mapper_report_final.md
results/20260731_care_myopath_pr_a0_a3_feasibility/controller_report.md
results/20260731_care_myopath_pr_a0_a3_feasibility/completion_check.md
results/20260731_care_myopath_pr_a0_a3_feasibility/MANIFEST.md
```

## Completion semantics

`controller_report.md` 开头必须先回答：

1. A0 是否完整保持成熟基线？
2. A1 是否证明可靠监督至少不会破坏能力？
3. A2 是否证明 scar/edema 独立路径有真实增量？
4. A3 是否形成有效病灶候选？
5. 哪个病种有效、哪个无效？
6. 是否值得进入 ROI refinement？
7. 是否应被前沿 Deep Research 的新范式取代？

机器字段：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
a0_gate:
a1_gate:
a2_gate:
a3_gate:
scar_mechanism_signal:
pure_edema_mechanism_signal:
roi_refinement_authorized: false
fold_expansion_authorized: false
validation_upload_authorized: false
git_commit_decision:
git_push_decision: NOT_AUTHORIZED
next_required_action: RETURN_TO_PLANNER
```

本地 commit：

```text
experiment: evaluate CARE MyoPath A0-A3 mechanism feasibility
```

禁止 push，禁止自动合并 main，禁止启动下一阶段。

## Controller prompt

Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, controller-as-coordinator diff inspection and repair loop, strict validators and known-bad regressions, minimum effective training, terminal Slurm accounting and post-completion aggregation, mapper/fingerprint gates, and the frozen A0-A3 architecture contract. If any hard gate fails, continue same-scope repair when authorized or stop with NEEDS_REPAIR/OPERATIONALLY_BLOCKED; do not claim VERIFIED_COMPLETE.

## Executor worker contract

The Executor performs authorized implementation and commands but cannot declare the whole task complete. Return every wave to the Controller/Coordinator for diff, evidence, validator, runtime and contract verification. Do not fill architecture blanks or add components outside the frozen A0-A3 contract.

## Mapper contract

The Mapper is read-only except for task-local mapper reports. It must trace input -> full stock encoder/decoder -> pathology global heads -> proposal logits -> final logits -> official labels, verify all tensor shapes, trainable/frozen parameter coverage, no-T2 behavior and on/off interventions, and identify any implementation that silently restores anchor monopoly or leaves proposal outside final output.
