# Batch 7 同范围机制闭环修复执行计划

Plan metadata:
- Type: active execution addendum
- Lane: historical Route B lineage, active main-only SRR MyoPS
- Round scope: Round04 post-portfolio mainline
- Status: ready for controller
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_batch7_upstream_candidate_quality_execution.md`
- Function: repair invalid Batch7 mechanism evidence, complete faithful dictionary/discovery implementation, and run stagewise component training
- Do not: start Batch8, monolithic 1200-step continuation, fold expansion, Cine, external data/weights, validation upload, backbone replacement, or hosted claims

## 总体判断

Batch 7 的正式 300 步结果说明当前联合模型没有形成稳定收益，但它没有回答最重要的问题：proposal、refiner、dictionary、source arbiter 和 production gate 分别做了什么。终态 intervention 表由同一组 formal300 指标复制而来，proposal/refiner 的核心指标为空，validator 仍然通过；同时 named negative memory 和 anchor-free discovery 也未按合同完整实现。

本修复不再新增复杂模块，而是把现有模块拆开、真实运行、逐段训练。只有前一个部件在 44 例上产生可验证的独立收益，后一个部件才允许开始。这样可以明确区分：

```text
实现/证据错误
vs
某个组件有害
vs
上游 proposal 本身无信号
vs
当前完整 SRR 设计不适合该数据
```

## 图示目标恢复

```yaml
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: COMPLETE
recovered_route_objective:
  - observed-modality-only multi-scale encoding
  - availability-aware shared/private/interaction retrieval
  - real prototype and semantic negative memory
  - anatomy-guided scar and edema proposals
  - pathology-specific soft-ROI refinement
  - bounded nnU-Net correction as safety, not replacement
```

## 固定来源和数据边界

```yaml
source_main_commit: 4c79554de785030ed59081ce3ae233711efc062a
batch6_checkpoint_sha256: 729c81e49bf846339ed2f39ef0f2656319befd2b9cfe73268d7cf501e6b40fbd
batch7_checkpoint_step: 300
batch7_checkpoint_sha256: d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
fold: 0
train_cases: 176
validation_cases: 44
label_mapping:
  background: 0
  lv_myo: 1
  lv_blood: 2
  rv_blood: 3
  edema: 4
  scar: 5
runtime_mode: anchor_bounded_srr_correction
decode_rule: outputs_logits_argmax
primary_population: positive_gt_cases
no_t2_edema_supervision: forbidden
```

## 需要被明确废止的 Batch 7 证据

以下文件保留作为错误证据，但不得支持任何机制判断：

```text
results/20260721_srr_batch7_upstream_candidate_quality/final_mechanism_interventions.csv
results/20260721_srr_batch7_upstream_candidate_quality/proposal_refiner_metrics.csv
results/20260721_srr_batch7_upstream_candidate_quality/source_arbiter_metrics.csv
```

新 packet 必须写出 `superseded_evidence.md`，逐项说明为什么失效，以及由哪些新文件取代。

## 修复后的唯一结果目录

```text
results/20260721_srr_batch7_mechanism_closure_repair/
```

禁止改写 Batch 6 和原 Batch 7 历史结果目录。

# 执行阶段

## B7R-00：启动、状态和证据绑定

目的：防止继续从 stale `CURRENT.md`、wiki 或错误 intervention 表出发。

必须完成：

1. 同步远端 `main` 并绑定当前 HEAD、task hash、config hash、AGENTS hash、Slurm skill hash；
2. 确认工作树只包含授权修改；
3. 读取 Batch6/Batch7 terminal packet、当前代码和本计划；
4. 将原 Batch7 的操作终态与科学证据状态分开记录；
5. 写出旧 intervention 文件的逐字段错误说明；
6. 在训练前更新 `CURRENT.md` 为 repair active，但不得前移为科学成功。

Required outputs:

```text
controller_bootstrap_snapshot.md
controller_context.json
controller_ledger.csv
superseded_evidence.md
implementation_snapshot.md
```

失败分支：任何 checkpoint、split、case、decode 或 source commit 不匹配时停止为 `NEEDS_REPAIR_NO_IMPLEMENTATION`。

## B7R-01：真实 intervention runner 和 fail-closed validator

目的：保证每种模式真的运行模型，而不是复制同一张表。

必须新增或修复：

```text
scripts/evaluation/run_srr_batch7_repair_interventions.py
scripts/evaluation/aggregate_srr_batch7_repair_interventions.py
scripts/evaluation/validate_srr_batch7_repair_packet.py
tests/srr_production/test_myops_batch7_repair_semantics.py
```

每种模式必须使用同一 selected checkpoint、同一 44 cases、同一 argmax decode，但各有独立：

```text
runtime/interventions/<mode>/predictions/
runtime/interventions/<mode>/prediction_manifest.json
runtime/interventions/<mode>/commands.json
```

强制模式：

```text
anchor_identity
production_gate_closed
full_learned
production_gate_one
proposal_only_gate_one
refiner_only_gate_one
learned_source_gate_one
prototype_maps_off
semantic_negative_memory_off
zero_anchor_confirmation_context
no_anchor_diagnostic
```

每个 manifest 必须包含：

```text
checkpoint path + SHA256
code/config hash
case list hash
44 inference calls
prediction file SHA256 per case
runtime mode
intervention mode
decode rule
command hash
```

Validator 必须 fail closed：

- `anchor_identity` 和 `production_gate_closed` 对每例 changed voxels 必须为 0，softmax 最大差必须 `<=1e-6`；
- 除上述预期等价对外，不同 mode 不得拥有完全相同的 44-case prediction hash 集；
- 所有 `proposal_only`、`refiner_only`、`learned_source` 数值必须非空且来自独立 prediction root；
- 文件中出现 `placeholder`、`copied_from_formal`、空指标、同一 prediction root 复用时退出非零；
- `no_anchor_diagnostic` 必须与 identity 至少一个病例不同；
- known-bad fixture 必须包含原 Batch7 复制表，并确认 validator 拒绝。

本阶段只做代码和小规模真实病例检查，不做正式训练。

## B7R-02：语义负记忆和真正 anchor-free discovery

### 2A. 真实 category memory

正式 named negative categories 固定为：

Scar:

```text
normal_myocardium
blood_pool
outside_myocardium
lge_bright_non_scar
anchor_remote_false_positive
```

Edema，仅 T2-present：

```text
normal_myocardium
blood_pool
outside_myocardium
t2_high_non_edema
anchor_remote_false_positive
```

实现要求：

- 资产保存每个 category 的 tensor、source case IDs、vector count、valid mask 和完整 SHA256；
- 不足以形成银行的 category 使用 `valid_mask=false`，绝不使用 deterministic axis、random、repeat-last 或复制其他类别；
- 正式 `_negative_memory_bank()` 只能拼接 `valid_mask=true` 的真实 bank；
- deterministic prototypes 可以保留为非正式 bootstrap 代码，但 formal asset loader 必须把其 contribution 设为零并由前向断言保证；
- edema 不得从 no-T2 病例提取正样本或负样本；
- training query 使用 exclude-query-shard，validation 使用全部 training shards；
- 验证集 case/label 不得参与资产构建。

Required outputs:

```text
semantic_memory_manifest.json
semantic_memory_category_counts.csv
semantic_memory_tensor_hashes.csv
semantic_memory_valid_masks.csv
```

### 2B. 真正 anchor-free discovery

不得只在 proposal 层把 anchor map 置零。必须把特征路径拆成：

```text
image -> modality encoders once
      -> anchor-free retrieval -> discovery features -> discovery proposal
      -> anchor-conditioned retrieval/context -> confirmation proposal
```

具体要求：

- modality encoders 只执行一次；
- discovery retrieval 的 `anchor_features=None`，不能读取 nnU-Net probabilities、components、confidence 或 uncertainty；
- confirmation branch 才允许读取 nnU-Net pathology context；
- `zero_anchor_confirmation_context` 只影响 confirmation，不得改变 discovery logits，最大绝对差 `<=1e-6`；
- 改变/置零 anchor context 必须使 confirmation logits 至少一个真实病例变化 `>1e-5`；
- discovery 在 zero-anchor 下必须非恒零；
- prototype maps 必须输入 anchor-free spatial discovery path。

Required outputs:

```text
discovery_independence.csv
semantic_memory_intervention.csv
prototype_map_intervention.csv
```

## B7R-03：修复后 checkpoint 的真实 44 例干预基线

目的：在任何新训练前，确定 Batch7 step300 当前到底是哪一环有害。

使用 Batch7 step300 checkpoint，完成 B7R-01 的全部模式，并输出：

```text
intervention_casewise_metrics.csv
intervention_summary.csv
intervention_prediction_manifest.csv
proposal_refiner_metrics.csv
source_arbiter_metrics.csv
```

最低解释要求：

- proposal-only scar/edema Dice、HD95、remote FP、help/harm；
- refiner-only 相对 proposal-only 的增量；
- learned source 相对各单独 source 的增量；
- prototype maps on/off 和 semantic memory on/off 对 proposal logits、final logits、final labels 的影响；
- gate learned/one/closed 的实际收益；
- no-anchor 仅作为诊断，不得成为候选。

如果本阶段任何强制 mode 缺失、空值、复用 prediction root 或 identity 非零，禁止进入训练。

## B7R-04：Proposal-only 分阶段训练

目的：先判断 dictionary + discovery/confirmation proposal 是否能产生独立可用信号；refiner、arbiter 和 production gate 不得掩盖这一判断。

初始化：

- 从 Batch7 step300 checkpoint 加载已兼容权重；
- 使用 B7R-02 修复后的 semantic memory asset；
- scar/edema refiner 冻结；
- source arbiter 冻结并强制 proposal source weight=1；
- production gate 冻结并在正式 proposal-only 评价中 force gate=1；
- encoders 和基础 scale retrieval 冻结；
- trainable：anchor-free spatial discovery retrieval、scar/edema proposal dictionary、pathology evidence heads；
- no-T2 edema 全链严格为零。

训练预算：

```yaml
optimizer: AdamW
learning_rate: 0.0001
weight_decay: 0.0001
batch_size: 1
patch_shape: [12, 96, 96]
optimizer_steps: 600
full_volume_eval_steps: [200, 400, 600]
validation_cases_per_eval: 44
```

继续门，全部满足才进入 refiner：

```text
proposal-only mean positive Dice delta >= +0.003
scar proposal-only Dice delta >= -0.001
edema proposal-only Dice delta >= +0.003
help >= harm
HD95 relative worsening <=5% each pathology
remote-FP relative worsening <=5% each pathology
no-T2 edema exact zero
proposal/dictionary gradients nonzero
selected checkpoint reload verified
```

失败时：停止后续 refiner/arbiter/gate 训练，返回 Planner，结论为 `PROPOSAL_CHAIN_INADEQUATE_AFTER_FAITHFUL_REPAIR`。不得延长步数掩盖失败。

## B7R-05：Scar 和 Edema refiner 分开训练

本阶段只有 B7R-04 通过后执行。两种病症不得混成一个 composite gate。

### 5A. Scar refiner

- 冻结 proposal、dictionary、encoder、retrieval、edema refiner、arbiter 和 gate；
- 只训练 scar refiner 300 steps；
- full-volume eval at 100/200/300；
- 重点 loss：小病灶保持、漏检恢复、边界、远端 FP；
- 正式比较基线为同 checkpoint 的 scar proposal-only。

Scar refiner 接受门：

```text
scar refiner Dice >= scar proposal Dice +0.001
scar HD95 relative worsening <=2%
scar remote-FP relative worsening <=2%
scar harm count <= proposal harm count
```

失败时正式路径固定 `scar_source=proposal_only`，scar refiner 继续保留为 negative diagnostic，不得交给 arbiter平均。

### 5B. Edema refiner

- 从同一 proposal checkpoint 开始；
- 只训练 edema refiner 300 steps；
- full-volume eval at 100/200/300；
- 只在 T2-present 病例监督；
- 重点 loss：召回、边界和 T2 high non-edema 抑制。

Edema refiner 接受门：

```text
edema refiner Dice >= edema proposal Dice +0.001
edema HD95 relative worsening <=2%
edema remote-FP relative worsening <=5%
no-T2 edema exact zero
```

失败时正式路径固定 `edema_source=proposal_only`。

## B7R-06：来源选择器和 production gate

只有至少一个 refiner 通过对应接受门时，才训练 source arbiter；未通过的 pathology 必须 hard-mask 到 proposal-only。

Source arbiter：

```yaml
optimizer_steps: 200
trainable: accepted_pathology_source_arbiters_only
frozen: all_other_model_parameters
full_volume_eval_steps: [100, 200]
```

接受门：learned source 对每个 pathology 不得比该 pathology 最佳已接受 source 低超过 `0.001`，且 help/harm 不得恶化。

Production gate：

```yaml
optimizer_steps: 200
trainable: production_correction_gate_only
frozen: all_upstream_components
full_volume_eval_steps: [100, 200]
```

最终候选门：

```text
mean positive Dice delta >= +0.005
each pathology Dice delta >= 0
help >= harm
HD95 relative worsening <=5% each pathology
remote-FP relative worsening <=5% each pathology
no-T2 edema exact zero
```

本任务即使通过最终候选门，也不授权 fold expansion、upload 或 hosted claim。

## B7R-07：最终真实干预、mapper 和状态收尾

对最终 selected checkpoint 重新运行 B7R-01 的所有独立模式。必须满足：

- identity/gate-closed exact zero；
- 每个 mode 有独立 44-case prediction root；
- proposal/refiner/source/gate 的指标无空值；
- prediction hash 与命令 hash 完整；
- source checkpoint reload 后再评价；
- `CURRENT.md`、entrypoints、wiki、COMPONENTS、architecture fingerprint 与终态一致；
- 原 Batch7 错误证据明确 superseded，但历史文件不删除。

Required terminal outputs:

```text
final_intervention_casewise.csv
final_intervention_summary.csv
proposal_refiner_metrics.csv
source_arbiter_metrics.csv
semantic_memory_effect.csv
discovery_independence.csv
training_stage_adequacy.json
checkpoint_selection.csv
help_harm.csv
subgroup_metrics.csv
slurm_attempts.csv
mapper_report_draft.md
mapper_report_final.md
architecture_delta_final.md
validator_status.json
finalizer_state.json
controller_report.md
completion_check.md
MANIFEST.md
```

# Slurm 和连续性

```yaml
python_executable: /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
primary_partition: htzhulab
mirror_partition: a100-gpu
mirror_after_pending_seconds: 900
volta_allowed: false
maximum_runtime_seconds_per_job: 14400
continuity_backend: slurm_dependency
training_dependency: afterok
finalizer_dependency: afterany
require_preflight: true
require_atomic_winner_lock: true
require_isolated_attempt_directories: true
cancel_pending_losers: true
```

任何 submitted、pending、running 或 awaiting-accounting 状态都不是完成。Controller 必须负责到所有 job terminal、聚合、validator、wiki/state 和本地轻量 commit 完成。

# Controller 验收硬门

Controller 不得因为 unit tests、gradient 非零、fixed overfit 或 validator 文件存在而宣布完成。必须亲自检查：

1. intervention runner 是否真的调用模型多次；
2. 每个 mode 是否有独立预测文件和 hash；
3. identity 是否严格为零；
4. placeholder 和空字段是否被拒绝；
5. named semantic memory 是否真实分组并使用 valid mask；
6. discovery tensor 是否对 anchor context 不变；
7. proposal/refiner/arbiter/gate 是否按阶段冻结和训练；
8. 失败模块是否被正式禁用，而不是继续平均；
9. 所有 Slurm 作业是否终态并完成 post-completion aggregation；
10. CURRENT/wiki/fingerprint 是否更新。

只有上述全部满足，才允许：

```text
controller_verification_decision: VERIFIED_COMPLETE
```

`VERIFIED_COMPLETE` 只表示本修复合同完成，不代表 SRR 成功，也不授权下一 Batch。
