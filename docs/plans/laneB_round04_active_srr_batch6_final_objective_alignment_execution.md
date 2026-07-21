# CARE SRR Batch 6：最终输出目标对齐与纠错门修复

Plan metadata:
- Type: active main-line mechanism-repair and bounded-training execution plan
- Lane: historical Route B lineage merged into main; Route A/B/C are evidence lanes only
- Round scope: post-Round04 main-only Batch 6
- Status: READY_FOR_CONTROLLER
- Parent evidence: `results/20260721_srr_batch5_post_batch4_diagnostic_repair/`
- Parent plan: `docs/plans/laneB_round04_active_srr_batch5_post_batch4_diagnostic_repair.md`
- Planning review: not required
- Independent reviewer: not required
- Function: repair the final deployed objective and production correction authority, then run a gated fold0 calibration wave
- Do not: replace the backbone, expand folds, start Cine, rebuild prototype memory, upload validation, or claim hosted improvement

## 一、动机背景

Batch 4 已经证明当前 SRR 可以真实训练，但最终结果仍几乎等于 nnU-Net：edema 只提高约 `+0.00068`，scar 只提高约 `+0.00134`。Batch 5 又证明，单纯把 production gate 全部打开并不会带来明显提升，去掉 nnU-Net anchor 后性能反而明显下降。

这说明当前问题不是“再多跑一些步数就会自然变好”，也不是“gate 太保守所以没有放行”。真正的结构性问题是：proposal 和 refiner 各自在接受监督，但最终部署的 `outputs["logits"]` 没有直接接受 scar/edema GT 纠错损失；production gate 主要得到的是保护 anchor 的梯度，而不是在 anchor 错误位置打开的纠错梯度。同时，现有两个正权重项还会把 correction 和 refiner residual 往零压。

Batch 5 的 packet 还留下三项证据缺口：实际有效 loss 权重没有完整解析；proposal-only/refiner-only 的 gate 输入仍互相混杂；proposal component、remote FP 和 ROI coverage 字段为空。因此 Batch 6 必须先补齐这些诊断，再允许训练。

## 二、核心目标

Batch 6 只解决一个主问题：

> 让训练目标直接服务于最终部署输出，并让 production gate 学会区分“这里需要纠正 nnU-Net”和“这里应保持 nnU-Net”。

它必须完成四件事：

1. 修复 Batch 5 的 loss 权重、组件干预、proposal/ROI 指标和 validator 缺口。
2. 为最终 `outputs["logits"]` 增加直接 scar/edema GT 损失。
3. 把旧 correction-opportunity 替换为直接监督 production gate 的 repair/preserve 损失，并补充 anchor uncertainty 等输入。
4. 从 Batch 4 selected checkpoint 开始，先过 fixed-batch overfit，再跑 300-step fold0 calibration；只有达到明确门槛才继续到总计 900 steps。

## 三、固定科学边界

```yaml
branch: main
worktree: /users/a/e/aereinh/CARE
fold: 0
train_cases: 176
validation_cases: 44
edema_positive_validation_cases: 16
scar_positive_validation_cases: 43
source_checkpoint_step: 1800
source_checkpoint_sha256: bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6
source_prototype_asset_sha256: 8b262f8bb87e0733a48e169c77b028a3833b70cbcd33d2ac2fb4857ba1cbde83
model_class: SRRProposeRefineMyoPS
model_variant: m10_d3_hierarchical_memory_propref
encoder_profile: full_4scale
base_channels: 32
final_output_mode: anchor_bounded_srr_correction
formal_decode: outputs_logits_argmax
primary_metric_population: positive_gt_cases
```

不得改变 split、病例数、label mapping、anchor、prototype/memory 内容、最大 correction bound 或正式 decode。

## 四、Batch 5 证据修复

### 4.1 实际有效 loss 权重

必须从 Batch 4 正式 wrapper、argparse 默认值、variant contract、legacy alias 和 explicit override 逐层解析，而不是从空的 Batch 5 `loss_weights` 字段推断。输出中每个 canonical loss 必须记录：

```text
source
raw key
alias chain
canonical component
resolved effective weight
consumed tensors
parameter groups receiving gradient
optimization direction: repair | preserve | shrink | regularize | disabled
```

`resolved_weight` 不得为空。审计必须使用 Batch 4 selected checkpoint 和真实 fixed validation patches，前后参数 hash 必须一致。

### 4.2 纯净组件干预

同一个 Batch 4 checkpoint、同一 44 cases、同一 anchor、同一 prototype/memory、同一 argmax decode 下，必须运行：

```text
anchor_identity_control
full_learned_gate
full_gate_one
full_gate_zero
proposal_only_gate_one
refiner_only_gate_one
```

`proposal_only_gate_one` 的 correction 和 gate 都不得读取 refiner 输出；`refiner_only_gate_one` 的 correction 和 gate 都不得读取 proposal 输出。它们是组件诊断，不是 deployable candidate。

### 4.3 proposal 与 ROI 指标

每个 case/pathology/mode 必须真实计算而不是留空：

```text
proposal_voxel_precision
proposal_voxel_recall
proposal_lesion_recall
proposal_component_count
proposal_remote_fp_count
proposal_remote_fp_volume_mm3
roi_gt_coverage
roi_outside_ratio
refiner_residual_abs_mean
changed_voxels_vs_anchor
Dice delta
HD95 delta
component delta
remote FP delta mm3
```

### 4.4 Batch 5 reconciliation validator

Validator 必须 fail closed 检查：

- 所有 required 字段非空且有限；
- effective weights 与真实训练入口一致；
- proposal/refiner 纯净干预没有 cross-input；
- exact aggregation command 能由当前脚本接受并返回 0；
- 44 cases × 2 pathologies × all declared modes 完整；
- parameter hash 不变；
- receipt、Slurm accounting、completion check 和 controller report 自洽。

这一步 optimizer steps 必须为 0。

## 五、最终输出直接监督

当前最终六类 logits 记为 $$z^{final}$$。为避免把 one-channel branch logits 与最终六类 softmax 混淆，Batch 6 使用 one-vs-rest margin：

$$
m_{scar}=z^{final}_5-\log\sum_{c\neq5}\exp z^{final}_c,
$$

$$
m_{edema}=z^{final}_4-\log\sum_{c\neq4}\exp z^{final}_c.
$$

最终 pathology loss 为：

$$
\mathcal L_{final}=\mathcal L_{scar}^{Dice+BCE}(m_{scar},y_{scar})
+\mathbb 1_{T2}\mathcal L_{edema}^{Dice+BCE}(m_{edema},y_{edema}).
$$

要求：

- scar 在所有 valid cases 上监督；
- edema 只在 T2-present cases 上监督；
- no-T2 edema final correction、proposal、ROI 和 refiner residual 继续严格为零；
- `loss_final_scar_pathology` 和 `loss_final_edema_t2_present_pathology` 必须出现在训练日志、gradient matrix 和 checkpoint contract 中；
- 两项损失都必须对 production gate 和对应 refiner 产生非零纠错梯度。

## 六、production gate 修复

### 6.1 gate 输入

现有 4-channel gate 扩为 13-channel gate，输出仍为 scar/edema 两个通道。固定输入顺序：

```text
0 scar proposal logit
1 edema proposal logit
2 scar refiner logit
3 edema refiner logit
4 anchor scar probability
5 anchor edema probability
6 anchor maximum confidence
7 anchor entropy
8 anchor top1-top2 margin
9 abs(scar proposal - scar refiner)
10 abs(edema proposal - edema refiner)
11 anatomy uncertainty
12 anatomy union support
```

Batch 4 gate checkpoint 迁移规则固定为：旧 4 个输入通道权重原样复制到新 gate 的 0:4；新增 4:13 通道权重初始化为零；两个输出 bias 原样复制。除该 gate 形状迁移外，所有 Batch 4 参数必须 exact-load，missing/unexpected keys 必须只包含明确允许的 gate migration keys。

### 6.2 gate repair/preserve 目标

对 pathology $$p$$：

```text
repair_mask_p = valid & (anchor_binary_prediction_p != gt_binary_p)
preserve_mask_p = valid & ~repair_mask_p & (anchor_max_confidence >= 0.80)
```

edema 的两个 mask 再与 `T2-present` 相交。其他体素不参与 gate supervision。

Gate 使用 logits 级 balanced BCE：

```text
positive class = repair_mask
negative class = preserve_mask
pos_weight = clamp(number_of_preserve_voxels / max(number_of_repair_voxels, 1), 1, 20)
```

必须输出：

```text
loss_production_gate_repair_preserve
repair_mask_voxels
preserve_mask_voxels
gate_mean_on_repair
gate_mean_on_preserve
gate_gradient_l2_from_final_pathology_loss
gate_gradient_l2_from_gate_supervision
```

### 6.3 旧损失处理

Batch 6 canonical effective weights 固定为：

```yaml
loss_anatomy_union_lv_rv: 1.0
loss_scar_proposal: 1.0
loss_edema_proposal_t2_present_only: 1.0
loss_scar_refiner_roi: 1.0
loss_edema_refiner_t2_present_roi: 1.0
loss_final_scar_pathology: 1.0
loss_final_edema_t2_present_pathology: 1.0
loss_production_gate_repair_preserve: 0.20
loss_anchor_preservation_outside_roi: 0.05
loss_component_remote_fp: 0.05
loss_no_t2_edema_safety: 0.50
loss_dictionary_entropy_coverage_load_balance: 0.20
loss_pattern_sip_integrativeness: 0.05
loss_prototype_diversity_margin: 0.20
loss_memory_bank_update_or_alignment: 0.05
loss_correction_opportunity: 0.0
loss_branch_arbitration_consistency: 0.0
loss_bounded_correction: 0.0
loss_refiner_final_label_effect: 0.0
loss_cine_temporal_consistency: 0.0
loss_cine_reference_warp_consistency: 0.0
```

Legacy alias 不得覆盖这些 canonical weights。Wrapper 必须把最终解析表写入 checkpoint 和 tracked result packet。

## 七、训练阶段

### 7.1 fixed-batch overfit gate

使用固定真实病例：

```text
Case2002: T2-present, scar-positive, edema-positive
Case1002: no-T2, scar-positive
```

从两例各固定采一个 pathology-containing patch，组成固定 batch，运行 60 optimizer steps。仅训练：

```text
production_correction_gate
scar_refine
edema_refine
```

冻结 encoder、retrieval、evidence heads、proposal dictionaries、prototype/memory。

Overfit 通过条件全部满足：

```text
combined final pathology loss decreases by at least 20%
scar final pathology loss decreases by at least 15%
edema final pathology loss decreases by at least 15%
gate repair/preserve loss decreases by at least 10%
production gate has nonzero repair gradient
final logits change from step 0
Case1002 no-T2 edema full chain remains exact zero
all losses finite
checkpoint save/reload reproduces final logits within 1e-6
```

60-step overfit 是进入正式训练的实现门，不计入 300-step formal budget。失败时不得提交正式训练，Controller 必须退回同一 Executor 修复。

### 7.2 300-step calibration wave

从迁移后的 Batch 4 selected checkpoint 开始。固定：

```yaml
optimizer: AdamW
learning_rate: 0.0001
weight_decay: 0.0001
grad_clip: 12.0
patch_shape: [12, 96, 96]
batch_size: 1
optimizer_steps: 300
full_volume_eval_steps: [100, 200, 300]
validation_cases_per_eval: 44
trainable_groups:
  - production_correction_gate
  - scar_refine
  - edema_refine
frozen_groups:
  - encoders
  - retrieval
  - evidence_heads
  - scar_dictionary
  - edema_dictionary
  - prototype_memory
```

Step 300 继续门全部满足后，Controller 才能机械地启动 900-step extension：

```text
mean of scar/edema positive-case Dice delta >= +0.003
each pathology Dice delta >= -0.002
help pathology-cases >= harm pathology-cases
HD95 relative worsening <= 5% for each pathology
remote-FP relative worsening <= 5% for each pathology
no-T2 edema exact-zero safety passes
final pathology and gate losses finite with nonzero gradients
```

若任一门失败，Batch 6 在 300 steps 后停止，不得用更多训练掩盖失败。

### 7.3 conditional 900-step extension

若 300-step 门通过，从 selected step-300 checkpoint 继续到总计 900 optimizer steps。Step 301 起解冻：

```text
scar_dictionary
edema_dictionary
evidence_heads
```

encoder、retrieval 和 prototype/memory 仍保持冻结。Full-volume eval 固定在 total steps `[450, 600, 900]`。

## 八、评价与科学门

所有正式判断使用同一 fold0 44 cases、同一 nnU-Net baseline、`outputs["logits"].argmax`、positive-GT pathology population，并单独报告 all-case empty-safe。

必须报告：

```text
scar/edema Dice and delta
scar/edema HD95 and delta
case-wise help/harm
CenterB/CenterC
LGE-only and T2-present groups
remote FP volume
component count
proposal precision/recall/lesion recall
ROI coverage/outside ratio
production gate repair-vs-preserve separation
```

Batch 6 结果等级：

```text
mechanism repaired but not useful:
  300-step continuation gate fails

small usable signal:
  final selected mean Dice delta >= +0.005 and each pathology >= 0

candidate signal:
  final selected mean Dice delta >= +0.010 and safety gates pass

strong signal:
  scar Dice delta >= +0.030 and edema Dice delta >= +0.030
```

只有 Planner/用户可根据结果授权 fold expansion。Controller 不得自动扩 fold。

## 九、执行图

```text
B6-00 bootstrap and freeze Batch4/Batch5 authority
B6-01 repair Batch5 effective-weight, pure-intervention, proposal/ROI evidence and validator
B6-02 implement final pathology loss and production gate repair
B6-03 fixed two-case 60-step overfit and reload gate
B6-04 formal 300-step fold0 calibration with 44-case evaluations
B6-05 conditional extension to total 900 steps only after the fixed step-300 gate
B6-06 selected-checkpoint pure interventions and mechanism aggregation
B6-07 mapper/wiki/fingerprint and strict packet validation
B6-08 controller verification and return to Planner
```

所有阶段 blocking。不得跳过 B6-01 直接训练，也不得在 B6-04 未通过时执行 B6-05。

## 十、Slurm 合同

```text
Python: /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
primary partition: htzhulab
submit isolated a100-gpu mirror after 900 seconds pending
volta-gpu: forbidden for formal model work because the current build lacks sm_70 support
preflight: same Python/config/output/log/lock contract as training
training dependency: afterok
finalizer/accounting dependency: afterany
atomic winner lock: required per training stage
pending loser cancellation: required
maximum job walltime: 4 hours per stage
```

所有 attempts 必须记录 job ID、partition、state、exit code、elapsed、node、log、runtime output、optimizer steps、aggregation command 和 aggregation exit code。Submitted、pending、running 或 awaiting accounting 不是完成。

## 十一、Required outputs

```text
results/20260721_srr_batch6_final_objective_alignment/controller_context.json
results/20260721_srr_batch6_final_objective_alignment/controller_ledger.csv
results/20260721_srr_batch6_final_objective_alignment/controller_bootstrap_snapshot.md
results/20260721_srr_batch6_final_objective_alignment/batch5_reconciliation.md
results/20260721_srr_batch6_final_objective_alignment/resolved_loss_weights.csv
results/20260721_srr_batch6_final_objective_alignment/pure_intervention_metrics.csv
results/20260721_srr_batch6_final_objective_alignment/proposal_roi_metrics.csv
results/20260721_srr_batch6_final_objective_alignment/implementation_snapshot.md
results/20260721_srr_batch6_final_objective_alignment/fixed_batch_overfit.json
results/20260721_srr_batch6_final_objective_alignment/loss_gradient_authority.csv
results/20260721_srr_batch6_final_objective_alignment/training_adequacy.json
results/20260721_srr_batch6_final_objective_alignment/checkpoint_selection.csv
results/20260721_srr_batch6_final_objective_alignment/subgroup_metrics.csv
results/20260721_srr_batch6_final_objective_alignment/help_harm.csv
results/20260721_srr_batch6_final_objective_alignment/final_mechanism_interventions.csv
results/20260721_srr_batch6_final_objective_alignment/slurm_attempts.csv
results/20260721_srr_batch6_final_objective_alignment/finalizer_state.json
results/20260721_srr_batch6_final_objective_alignment/mapper_report_draft.md
results/20260721_srr_batch6_final_objective_alignment/architecture_delta_draft.md
results/20260721_srr_batch6_final_objective_alignment/mapper_report_final.md
results/20260721_srr_batch6_final_objective_alignment/architecture_delta_final.md
results/20260721_srr_batch6_final_objective_alignment/controller_report.md
results/20260721_srr_batch6_final_objective_alignment/completion_check.md
results/20260721_srr_batch6_final_objective_alignment/MANIFEST.md
```

## 十二、禁止事项

Batch 6 不允许：

```text
backbone replacement or comparison
encoder/retrieval redesign
prototype/memory rebuild
fold expansion
Cine training
external weights or data
validation package or upload
hosted metric claim
route promotion
M11
Batch7 automatic start
```

Batch 6 即使失败，也必须回答一个清楚的问题：在最终输出获得直接监督、gate 获得真实纠错目标后，当前 proposal/refiner 是否能够把 `+0.001` 级 near-identity 提升推进到至少 `+0.005` 的可用信号。