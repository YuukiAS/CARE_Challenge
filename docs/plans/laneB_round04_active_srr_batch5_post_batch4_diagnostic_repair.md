# CARE SRR Batch 5：Batch 4 后评价语义与输出权威诊断修复

Plan metadata:
- Type: active main-line diagnostic repair plan
- Lane: historical Route B lineage merged into main; Route A/B/C are not active branches
- Round scope: post-Round04 main-only Batch 5
- Status: READY_FOR_CONTROLLER
- Parent evidence: `results/20260721_srr_batch4_forced_fold0_training/`
- Planning review: not required
- Independent reviewer: not required
- Training: forbidden in Batch 5

## 一、动机背景

Batch 4 已经关闭了长期困扰 SRR 的主要工程借口：正式模型完成真实 1800-step fold0 训练、176/44 数据覆盖、完整原型/记忆、schema-v2 checkpoint、同 checkpoint 三模式、identity exact 和三次 44 例评价均有终态证据。

但最终提升只有 edema `+0.00068`、scar `+0.00134`，HD95 没有改善到足以支持候选信号。当前结果说明工程闭环已经形成，科学增益仍然很弱。

现在不应该直接增加训练预算或 dictionary 复杂度。Batch 4 的结果包仍无法回答：

```text
proposal 是否真正优于 anchor？
refiner 是否在 proposal 基础上改善局部形状？
production_correction_gate 是否把有用修正压成 near-identity？
checkpoint selection 是否使用了最终部署 decode 语义？
```

Batch 5 的目标是用现有 checkpoint 把这四个问题回答清楚，并形成唯一的下一次训练修复方向。

## 二、核心目标

Batch 5 必须完成：

1. 修复 Batch 4 checkpoint selection 与正式 runtime decode 不一致的问题。
2. 分离 positive-GT pathology 指标和 all-case empty-safe 指标。
3. 对同一 checkpoint 做 proposal/refiner/production-gate 的真实运行时干预。
4. 建立病例级 `memory/proposal -> refiner -> production gate -> bounded correction -> final metric` 闭环。
5. 补齐 prototype/memory manifest 的 feature/config/code/split/anchor/asset hash。
6. 修复 CURRENT、entrypoint authority 和 root wiki/fingerprint 的过时状态。
7. 只给出一个 Batch 6 训练修复方向。

Batch 5 不训练，不改变 checkpoint 权重，不重建 prototype/memory，不扩 fold。

## 三、已有行动与 Batch 4 数据结论

### 已完成

- `m10_d3_hierarchical_memory_propref + full_4scale + base_channels=32`。
- 176 例训练、44 例验证。
- 1800 optimizer steps、1800 秒训练循环。
- step 600/1200/1800 各 44 例评价。
- selected checkpoint step 1800，SHA256：

```text
bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6
```

- 同 checkpoint identity/bounded/no-anchor。
- identity changed voxels 0，softmax delta 0。
- frozen prototype/memory 176 cases，无 validation leakage。

### 科学结果

```text
edema Dice: 0.3944358977 -> 0.3951155483
scar Dice:  0.5601692281 -> 0.5615107217
```

- edema CenterB 小幅改善，CenterC 基本不变。
- scar 主要在 no-T2/LGE-only 子组改善。
- T2-present scar 与 CenterC scar 略降。
- scar remote FP 平均下降约 14.73 mm3，但 HD95 略差。
- 平均 Dice 增量远低于 Batch 4 candidate gate `+0.01`。

## 四、已识别的评价与机制缺口

### 4.1 checkpoint selection decode mismatch

历史 Batch 4 aggregator 使用：

```text
predictions/fold_0/step_<step>/pathology_aware
```

选择 checkpoint；正式 selected-checkpoint control 使用：

```text
anchor_bounded_srr_correction -> outputs["logits"].argmax
```

Batch 5 必须保留历史选择结果不变，同时在新 namespace 中用正式 logits argmax 对 step 600/1200/1800 重新排序。

### 4.2 all-case edema 指标混入 empty-GT

`validation_checkpoint_metrics.csv` 的 edema all-case Dice 约 0.78，不能与 positive-case baseline 0.3944 比较。Batch 5 必须输出两套明确字段：

```text
positive_gt_case_mean
all_case_empty_safe_mean
```

科学判断只使用 positive-GT pathology 指标。

### 4.3 诊断记录的不是正式修正门

正式 final logits 使用：

```text
production_correction_gate
bounded_scar_correction
bounded_edema_correction
```

现有 `correction_gate_diagnostics.csv` 主要记录旧 baseline/arbitration 量。Batch 5 必须从正式输出张量直接记录 production gate 与 bounded correction。

### 4.4 缺少同 checkpoint 机制干预

必须在相同 checkpoint、相同 44 cases、相同 anchor、相同 decode rule 下运行：

```text
anchor_identity_control
anchor_bounded_full
srr_no_anchor_control
anchor_bounded_proposal_only
anchor_bounded_refiner_only
production_gate_closed
production_gate_open_bounded_control
```

proposal-only 与 refiner-only 是诊断模式，不是 submission candidate。

## 五、固定实现合同

### 5.1 不可改变的输入

```yaml
fold: 0
cases: 44
checkpoint_steps: [600, 1200, 1800]
selected_checkpoint_sha256: bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6
prototype_memory: immutable Batch 4 asset
model_weights: immutable
optimizer_steps: 0
```

### 5.2 代码修复

必须修改或新增：

```text
scripts/evaluation/audit_srr_batch4_selection_semantics.py
scripts/srr_production/infer_myops.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/srr_production/prototype_memory.py
scripts/evaluation/validate_srr_batch5_packet.py
tests/srr_production/test_myops_batch5_diagnostics.py
```

允许对现有 Batch 4 aggregator 增加显式 decode 参数，但不得覆盖或重写历史 Batch 4 tracked result files。所有新结果写入：

```text
results/20260721_srr_batch5_post_batch4_diagnostic_repair/
```

### 5.3 production correction ablation

在 `SRRProposeRefineMyoPS.forward()` 增加显式诊断参数，默认行为必须保持不变：

```text
full
proposal_only
refiner_only
gate_closed
gate_open_bounded_control
```

定义：

```text
full:
  raw = 0.5 * (refiner_logits + proposal_logits) - anchor_logits
proposal_only:
  raw = proposal_logits - anchor_logits
refiner_only:
  raw = refiner_logits - anchor_logits
gate_closed:
  bounded correction = 0
gate_open_bounded_control:
  gate = 1，仍保留 tanh max-delta bound
```

这只是 inference-time intervention，不得修改 checkpoint 参数或训练状态。

### 5.4 必须输出的病例级字段

每个 case、pathology、checkpoint、intervention 至少记录：

```text
production_gate_mean/p50/p95/max
raw_correction_abs_mean/p95/max
bounded_correction_abs_mean/p95/max
proposal_positive_voxels
proposal_component_count
proposal_remote_fp_count
roi_gt_coverage
roi_outside_ratio
refiner_residual_abs_mean
changed_voxels_vs_anchor
Dice delta
HD95 delta
component delta
remote FP delta mm3
```

### 5.5 checkpoint 重新排序

先按正式 argmax 输出计算 eligibility：

```text
each pathology Dice delta >= -0.002
HD95 relative worsening <= 5%
remote FP relative worsening <= 5%
help cases >= harm cases
```

有 eligible checkpoint 时按以下固定字典序：

```text
maximize minimum scar/edema positive-case Dice delta
maximize mean scar/edema positive-case Dice delta
minimize harm pathology-case count
minimize positive-case HD95
minimize remote FP delta
select earlier step
```

没有 eligible checkpoint 时输出 `B5_NO_SAFETY_ELIGIBLE_CHECKPOINT`，不得强行选 best。

## 六、执行图

```text
B5-00 bootstrap, bind main and Batch 4 immutable evidence
B5-01 repair evaluation/decode semantics and tests
B5-02 implement production correction inference interventions
B5-03 run same-checkpoint 44-case diagnostic inference
B5-04 aggregate paired metrics and mechanism attribution
B5-05 repair prototype provenance hashes and validators
B5-06 mapper/current/wiki/fingerprint update
B5-07 controller verification and unique Batch 6 decision
controller returns to Planner
```

所有阶段 blocking。Controller 是 coordinator 和 acceptance owner；Executor 不能自行宣布完成。

## 七、Slurm 边界

Batch 5 只允许一个 inference-only logical run，不允许 optimizer construction之后的任何训练 step。

```text
primary: htzhulab
after 900 seconds pending: a100-gpu isolated mirror
volta-gpu: forbidden because current torch build does not support sm_70
max runtime: 3600 seconds
same checkpoint/config/case hashes
atomic winner lock
pending loser cancelled
finalizer: afterany
```

所有 inference attempt 必须记录 optimizer step count 为 0。

## 八、完成标准

必须存在：

```text
results/20260721_srr_batch5_post_batch4_diagnostic_repair/evaluation_semantics_audit.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/checkpoint_reranking.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/mode_intervention_metrics.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/casewise_mechanism_attribution.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/prototype_manifest_audit.json
results/20260721_srr_batch5_post_batch4_diagnostic_repair/batch6_unique_repair_decision.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/controller_report.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/completion_check.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/MANIFEST.md
```

Controller 只有在以下条件全部满足时才能写 `VERIFIED_COMPLETE`：

- Batch 4 historical files未被改写；
- 44 例、三个 checkpoint、所有 intervention 完整；
- checkpoint SHA、case list、decode rule 一致；
- production gate 真实张量已进入病例级表；
- positive-case/all-case 语义分离；
- prototype hashes 非空且验证通过；
- CURRENT/wiki/fingerprint 与 Batch 4/5 状态一致；
- strict validator 和 known-bad tests exit 0；
- 最终只选一个 Batch 6 repair direction。

## 九、Batch 6 唯一方向规则

根据干预证据只能选择一个：

```text
B5_FINAL_OBJECTIVE_ALIGNMENT_BOTTLENECK
B5_OUTPUT_AUTHORITY_BOTTLENECK
B5_PROPOSAL_PRECISION_BOTTLENECK
B5_REFINER_EFFECTIVENESS_BOTTLENECK
B5_EVALUATION_SEMANTICS_ONLY_ISSUE
B5_INSUFFICIENT_MECHANISM_EVIDENCE
```

判断优先级：

1. oracle 平均增益至少 `+0.01`、full 仍接近 identity，且 production gate 缺少直接 final-pathology repair loss或 magnitude penalty 明确偏好零修正：`B5_FINAL_OBJECTIVE_ALIGNMENT_BOTTLENECK`。
2. loss 路径合理，但 gate-open 相对 full 的平均 positive-case Dice 至少 `+0.005`：`B5_OUTPUT_AUTHORITY_BOTTLENECK`。
3. proposal-only 无信号或 remote/component FP 明显恶化：`B5_PROPOSAL_PRECISION_BOTTLENECK`。
4. proposal-only 有信号，但 refiner-only/full 相对 proposal 平均下降至少 `0.002`：`B5_REFINER_EFFECTIVENESS_BOTTLENECK`。
5. 只有 selection/decode 修复改变结论：`B5_EVALUATION_SEMANTICS_ONLY_ISSUE`。
6. 其他：`B5_INSUFFICIENT_MECHANISM_EVIDENCE`。

Batch 5 不得自行启动 Batch 6 训练。
