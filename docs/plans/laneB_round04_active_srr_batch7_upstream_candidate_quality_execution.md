# CARE SRR Batch 7：重建上游候选质量与 proposal/refiner 来源选择

Plan metadata:
- Type: active main-line architecture repair and bounded fold0 execution plan
- Lane: historical Route B lineage merged into main; Route A/B/C are not active branches
- Round scope: post-Round04 main-only Batch 7
- Status: READY_FOR_CONTROLLER
- Parent evidence: `results/20260721_srr_batch6_final_objective_alignment/`
- Planner audit: `results/srr_production/code_maturity/batch6_planner_audit_and_batch7_decision.md`
- Planning review: not required
- Independent reviewer: not required
- Training: authorized only by the staged gates below

## 一、总体判断

Batch 6 已经证明最终输出的真实标签监督和纠错门可以学习，但只训练 gate 与两个 refiner 后，模型仍只比 nnU-Net 平均高约 `+0.0017`。当前最重要的问题不是模型“不敢改”，而是上游没有持续提供足够可靠的新候选：prototype/memory 可能与训练后特征空间错位，空间 dictionary 没有读取 prototype maps，proposal 过度依赖 nnU-Net，而 scar refiner 会破坏已有 proposal。Batch 7 必须先修这些信息源，再进行有限训练；不得把 Batch 6 机械延长到 900 步。

## 二、Batch 6 给出的直接证据

同一 step300 checkpoint、同一 44 例、同一 argmax 评价下：

```text
full learned gate:        edema +0.00272475, scar +0.00067397
full gate=1:              edema +0.00772109, scar +0.00028663
proposal-only gate=1:     edema +0.00434505, scar +0.00261628
refiner-only gate=1:      edema +0.00495245, scar -0.00876189
```

因此：

- edema 还有部分可兑现修正被 gate 压住，但上界仍不足以靠 gate 单独达到目标；
- scar proposal 有小幅正信号，scar refiner 明显有害；
- 固定 `0.5 * (proposal + refiner)` 融合必须删除；
- Batch 7 的主目标必须是提高 proposal/refiner 本身的独立质量，而不是再次只调 final gate。

## 三、图示目标与实现边界

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3
visual_read_status: COMPLETE
recovered_route_objective:
  [LGE,T2,C0] + availability
  -> modality-specific multi-scale encoding
  -> shared/private/interaction selective retrieval
  -> trained-feature-aligned prototype/memory/negative-space
  -> anatomy-guided anchor-independent discovery + anchor-confirmation proposals
  -> pathology-specific differentiable soft-ROI refinement
  -> learned proposal/refiner source selection
  -> directly supervised bounded nnU-Net correction
```

nnU-Net 只允许作为 baseline、anchor、上下文、错误提示和安全来源。独立发现分支不得读取 nnU-Net scar/edema probability 或由其生成的 pathology component map。

## 四、冻结输入与来源

```yaml
source_main_commit: f139c54fd6b55b99409fcf546a1a0e117d7aa06b
source_checkpoint_step: 300
source_checkpoint_sha256: 729c81e49bf846339ed2f39ef0f2656319befd2b9cfe73268d7cf501e6b40fbd
source_checkpoint_result_root: results/20260721_srr_batch6_final_objective_alignment
fold: 0
train_cases: 176
validation_cases: 44
primary_decode: outputs_logits_argmax
primary_population: positive_gt_cases
nnunet_anchor_source: exact fold OOF probabilities and predictions
external_data_or_weights: forbidden
```

Batch 4 的旧 prototype asset 只作对照，不再作为 Batch 7 正式训练资产。

## 五、固定架构修复

### 5.1 从训练后 checkpoint 重建 prototype/memory

必须新增共享构建入口：

```text
scripts/srr_production/build_srr_batch7_prototype_memory.py
```

固定流程：

```text
load Batch6 step300 checkpoint
-> model.eval()
-> freeze encoders and base ScaleRetrieval
-> extract pre-spatial scar/edema features from all 176 fold0 train cases
-> use train labels and OOF anchor only
-> build four deterministic case shards
-> write schema-v2 asset and manifest
```

要求：

- feature stage 固定为 `SRRProposeRefineMyoPS._evidence_features.before_m10_spatial`；
- validation case IDs 与 labels 不得进入构建；
- training query 排除自身 shard，validation query 使用全部 train shards；
- tensor SHA256 必须覆盖完整 contiguous tensor bytes，不得只哈希前缀或 tensor sum；
- 旧资产和新资产必须输出 cosine/nearest-neighbour drift audit；
- 编码器与 base retrieval 在 Batch 7 所有正式训练阶段保持冻结，避免新资产再次失配。

### 5.2 用真实语义负样本替代人为负记忆

正式资产必须建立以下真实类别，所有向量来自 Batch 6 step300 的训练病例特征：

```text
scar:
  positive_scar
  normal_myocardium
  blood_pool
  outside_myocardium
  lge_bright_non_scar
  anchor_remote_false_positive

edema, T2-present only:
  positive_edema
  normal_myocardium
  blood_pool
  outside_myocardium
  t2_high_non_edema
  anchor_remote_false_positive
```

精确定义：

- `normal_myocardium`: label 1；
- `blood_pool`: labels 2 or 3；
- `outside_myocardium`: label 0；
- `lge_bright_non_scar`: myocardium labels 1 or 4, scar label excluded, LGE robust-z `>=2.0`；
- `t2_high_non_edema`: T2-present, myocardium labels 1 or 5, edema label excluded, T2 robust-z `>=2.0`；
- `anchor_remote_false_positive`: corresponding anchor pathology component has zero GT overlap and `union_distance > 0.65`；
- no-T2 case contributes neither edema positive nor edema negative.

若某个命名类别在某 shard 中没有真实向量，该类别必须记录 count=0 并在 query 时 mask；禁止 deterministic-axis、random、repeat-last 或复制其他类别补齐。

`ProposalDictionary` 原有 deterministic named negative buffers 只能保留为 legacy initialization；formal Batch 7 path 必须完全绕过它们，validator 必须验证其 final similarity contribution 为零。

### 5.3 让 prototype/memory 真正进入 spatial dictionary

当前 `M10TwoPassSpatialDictionary` 支持 `prototype_maps`，但正式 forward 没有传入。Batch 7 必须修改：

```text
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/srr_production/prototype_memory.py
```

固定数据流：

```text
pre-spatial scar/edema features
-> case-exclusive memory query
-> scar_pos, scar_neg, edema_pos, edema_neg similarity maps
-> M10TwoPassSpatialDictionary(prototype_maps=...)
-> spatial gates and retrieved features
-> pathology proposal heads
```

不得在 spatial dictionary 后用改变过的特征重新查询冻结 memory。memory query 始终使用与资产同空间的 pre-spatial features。

同 checkpoint 干预必须证明 `prototype_maps on/off` 会改变：

```text
spatial gate weights
retrieved features
proposal logits
final logits or labels
```

所有缺失模态 private/interaction slot 权重必须精确为零。

### 5.4 双来源 proposal

在 `ProposalDictionary` 中实现两个明确分支：

```text
discovery branch:
  post-spatial image features
  learned evidence logits
  positive-negative memory similarity
  anatomy support and uncertainty
  no nnU-Net pathology probability
  no nnU-Net pathology component map

confirmation branch:
  discovery logit
  nnU-Net pathology probability
  nnU-Net pathology component
  anchor confidence/entropy
  anatomy support
```

两个分支各用独立可学习 `1x1x1` fusion，不再使用现有固定系数加法。再用每病种两路 softmax reliability head 生成 `discovery_weight` 与 `confirmation_weight`，得到 proposal logit。

直接监督必须包括：

```text
proposal BCE + Dice
anchor-missed lesion recovery: GT positive and anchor pathology negative
anchor false-positive suppression: anchor pathology positive and GT negative
remote-FP penalty
lesion recall diagnostic
```

干预 `zero_anchor_pathology_context` 时，discovery branch 必须保持非零并继续有 GT 梯度；若 proposal 与 final logits 完全回到 identity，formal path 失败。

### 5.5 正式 refiner 改为可微软 ROI proposal refinement

旧 `CropSoftROIRefinementHead` 保留为 legacy/diagnostic，不得作为 Batch 7 正式 refiner。新增：

```text
DifferentiableSoftROIRefinementHead
```

固定定义：

```text
soft_roi = learned function of proposal probability, prototype margin,
           anatomy support, uncertainty and modality image
residual = depthwise-separable 3D residual head over full feature patch
refiner_logits = proposal_logits + residual_scale * soft_roi * residual
```

要求：

- 正式 refiner 起点必须是 `proposal_logits`，不是 `evidence_logits`；
- 不得用阈值、`nonzero`、bounding-box 或 Python case loop 决定正式训练路径；
- scar 使用 LGE，edema 使用 T2；无 T2 edema soft ROI、residual 和 logits correction 精确为零；
- `proposal_wrong -> signed repair toward GT`；
- `proposal_correct and high-confidence -> preserve`；
- 输出 proposal/refiner paired Dice、HD95、remote FP 和 changed voxels。

### 5.6 学习选择 proposal 或 refiner

删除正式路径中的：

```text
0.5 * (proposal_logits + refiner_logits)
```

新增每病种 `PathologySourceArbiter`：

```text
inputs:
  proposal logit/probability
  refiner logit/probability
  absolute disagreement
  prototype positive-negative margin
  soft ROI
  anchor confidence/entropy
  anatomy uncertainty/support
outputs:
  proposal_source_weight
  refiner_source_weight
```

权重经两路 softmax。训练时用 detached per-voxel binary GT loss 生成 best-source target；proposal 与 refiner 打平时固定选择 proposal。candidate pathology logit 为两者加权和，再交给 Batch 6 production gate 决定是否对 anchor 施加 bounded correction。

必须有 `proposal_only`、`refiner_only`、`learned_source` 和仅诊断用 `GT_oracle_source` 四种模式。oracle 不能成为部署候选。

## 六、损失合同

Batch 6 direct final pathology loss 和 production gate repair/preserve loss继续保留。新增 canonical components：

```yaml
loss_scar_discovery_proposal: 1.0
loss_edema_discovery_proposal_t2_present: 1.0
loss_scar_confirmation_proposal: 0.5
loss_edema_confirmation_proposal_t2_present: 0.5
loss_anchor_missed_lesion_recovery: 1.0
loss_anchor_false_positive_suppression: 0.25
loss_semantic_negative_margin: 0.20
loss_spatial_prototype_conditioning: 0.10
loss_scar_refiner_repair_preserve: 1.0
loss_edema_refiner_repair_preserve_t2_present: 1.0
loss_source_arbiter: 0.20
loss_final_scar_pathology: 1.0
loss_final_edema_t2_present_pathology: 1.0
loss_production_gate_repair_preserve: 0.20
loss_no_t2_edema_safety: 0.50
loss_component_remote_fp: 0.05
```

禁止恢复正权重的 correction-magnitude 或 refiner-residual shrink loss。

## 七、执行阶段

### B7-00：绑定终态与架构审计

不训练。绑定 Batch 6 terminal commit、selected checkpoint、split、case list、decode 和 metric；输出当前旧资产、人工负记忆、prototype-map 空接线、旧 refiner 和固定平均的代码证据。

### B7-01：重建资产与 asset-only 干预

使用全部 176 个训练病例重建 schema-v2 asset。完成 old-vs-rebuilt 和 prototype-map on/off 的 44 例 inference-only 干预。该阶段只证明资产与接线真实，不作性能晋级。

### B7-02：实现 proposal/refiner/source arbiter 与测试

完成上述固定代码结构、loss、checkpoint schema、inference modes、strict validator 和 known-bad。真实病例 forward/backward 必须覆盖 LGE-only、LGE+C0、LGE+T2+C0。

### B7-03：固定病例 100 步过拟合

病例固定为：

```text
Case2002: T2-present scar/edema
Case1002: LGE-only scar
```

每个病例使用固定包含目标病灶的 patch。该阶段 formal training credit 为 0。

必须同时满足：

```text
combined final pathology loss relative decrease >= 20%
discovery proposal loss relative decrease >= 20%
scar refiner repair loss relative decrease >= 15%
source arbiter loss relative decrease >= 10%
nonzero gradients: spatial routers, proposal heads, refiners, source arbiters, production gate
zero_anchor_pathology_context keeps discovery branch nonzero
Case1002 no-T2 edema entire chain exact zero
all losses finite
save/reload max logits delta <= 1e-6
```

失败则停止，不得提交正式训练。

### B7-04：正式 300 步上游校准

从 Batch 6 step300 checkpoint warm start，加载 Batch 7 rebuilt asset。

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
```

Trainable：

```text
m10_spatial_dictionary routers/experts/proposal0
scar_dictionary and edema_dictionary learned fusion/embedding
new scar and edema differentiable refiners
evidence_heads.scar and evidence_heads.edema
scar and edema source arbiters
production_correction_gate
```

Frozen：

```text
all modality encoders
base multi-scale ScaleRetrieval
anatomy decoder and evidence_heads.anatomy
rebuilt prototype/memory tensors
nnU-Net anchor
```

### B7-05：300 步继续门

只有全部满足才允许继续到总计 1200 步：

```text
final mean scar/edema positive-case Dice delta >= +0.005
each pathology final Dice delta >= +0.001
proposal-only mean scar/edema Dice delta >= +0.005
scar refiner-only Dice delta >= 0
scar learned-source Dice no more than 0.001 below scar proposal-only
edema learned gate captures >=60% of full-gate-one Dice gain
help cases >= harm cases
HD95 relative worsening <=5% each pathology
remote-FP relative worsening <=5% each pathology
no-T2 edema exact zero
all required gradients nonzero and losses finite
```

失败则停止在 300，并完成最终机制包；不得继续训练。

### B7-06：条件扩展到总计 1200 步

仅在 B7-05 机器继续门通过后，从 step300 checkpoint resume：

```text
total optimizer steps: 1200
additional full-volume eval: 600, 900, 1200
trainable/frozen groups unchanged
training dependency: afterok
```

不得在扩展阶段解冻 encoder 或 base retrieval，也不得重建 asset。

### B7-07：checkpoint 选择和最终干预

正式选择只使用 `outputs["logits"].argmax`、positive-GT populations。Eligibility：

```text
each pathology Dice delta >= 0
help >= harm
HD95 relative worsening <=5%
remote-FP relative worsening <=5%
no-T2 edema exact zero
```

排序：最大化两病种最小 Dice delta，然后最大化 mean，减少 harm、HD95 和 remote FP，最后选更早 step。

Selected checkpoint 必须 reload 后，在相同 44 例运行：

```text
anchor identity
old Batch4 asset
rebuilt Batch7 asset
prototype maps off
semantic negative memory off
zero anchor pathology context
proposal only
refiner only
learned proposal/refiner source
GT-oracle source, diagnostic only
production gate closed / learned / one
no-anchor diagnostic
```

必须报告病例级 Dice、HD95、remote FP、component、changed voxels、proposal precision/recall、lesion recall、ROI coverage、source weights 和 gate capture ratio。

## 八、科学等级

```text
mean Dice delta < +0.01: still insufficient
+0.01 to < +0.03: useful upstream mechanism signal
+0.03 to < +0.05: substantial but below project target
>= +0.05 mean and each pathology >= +0.03: Batch7 target reached
```

任何等级都不自动授权 fold expansion 或 validation upload。

## 九、Known-bad 与 strict validator

必须 fail closed：

- 用随机初始化或训练前 checkpoint 建立正式 asset；
- validation case/label 泄漏；
- 完整 tensor hash 缺失；
- deterministic-axis、random 或 repeat-last semantic negative 进入正式 similarity；
- no-T2 病例进入 edema 正负 memory；
- spatial dictionary 未实际读取 nonzero prototype maps却声称已接线；
- missing-modality slot 非零；
- zero anchor pathology context 后 discovery branch 归零；
- 正式 refiner 仍以 evidence logits 为起点；
- 正式 refiner仍使用离散 crop/bounding box；
- 固定 `0.5/0.5` proposal/refiner 平均仍在正式路径；
- scar refiner harmful 但 300 步继续门通过；
- 300 步 gate 失败却提交 1200 步；
- selected checkpoint 未 reload 或 decode 不一致；
- submitted/pending/monitor packet 冒充完成；
- runtime role push 或写 `review.md`。

## 十、Slurm 与完成边界

```text
Python: /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
primary: htzhulab
mirror after 900s pending: a100-gpu
volta: forbidden
max runtime per stage: 4 hours
atomic winner lock: required
isolated attempt directories: required
training dependency: afterok
finalizer/accounting dependency: afterany
```

Controller 必须负责到所有 attempt terminal、post-completion aggregation、mapper final、strict validator 和本地轻量 commit。Runtime 角色不得 push。

禁止提交 checkpoint、prototype `.pt`、NIfTI、raw data、大日志、secret 或 upload package。

## 十一、未授权范围

```text
backbone replacement or comparison
encoder/base retrieval redesign
fold expansion
Cine training
external data or weights
validation packaging/upload
hosted metric claim
route promotion
M11
Batch8 automatic start
final scientific stop
```
