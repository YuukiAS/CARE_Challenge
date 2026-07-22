# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch7_center_hierarchical_br2_sip_decomposition_ready_20260722
round_id: post_round04_main_only
state_updated_date: 2026-07-22
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: SRR_MyoPS_from_historical_Route_B_lineage
batch6_scientific_status: FINAL_OBJECTIVE_REPAIRED_BUT_BELOW_USABLE_SIGNAL
batch7_operational_status: FORMAL300_COMPLETE_STOP_GATE
batch7_repair_operational_status: VERIFIED_COMPLETE_STOPPED_AT_PROPOSAL_GATE
batch7_repair_scientific_status: TRUTHFUL_EVIDENCE_BUT_PROPOSAL_STAGE_LOSS_AUTHORITY_IMPURE
batch7_minimal_decomposition_status: VERIFIED_COMPLETE_NEGATIVE_SIGNAL
next_required_action: RETURN_TO_PLANNER_FOR_SRRMyoPS_STOP_OR_NEW_DIRECTION_DECISION
planning_review_required: false
review_required: false
controller_is_coordinator: true
batch8_authorized: false
refiner_training_authorized: false
source_arbiter_training_authorized: false
production_gate_training_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
backbone_replacement_authorized: false
validation_upload_authorized: false
hosted_metric_claim_authorized: false
route_promotion_authorized: false
final_scientific_decision_authorized: false
```

## 开发边界

只允许在：

```text
/users/a/e/aereinh/CARE
main
```

开发。不得写入 `/overflow/htzhu/CARE` 或历史 Route A/B/C worktree。Route A/B/C 只保留 lineage 和历史证据。

## 当前流程

```text
Planner
-> Controller/Coordinator
   -> one Executor
   -> Mapper draft/final
   -> deterministic Finalizer/Validator
   -> Controller verification and same-scope repair loop
   -> local lightweight commit
-> Planner
```

Controller 必须检查真实 diff、source 语义、representer、signed coefficients、SIP公式、representer尺度、source-balanced采样、loss-specific gradient、匹配实验、Slurm、aggregation、CURRENT/wiki/fingerprint。普通实现和证据问题必须在当前任务内修复，不得直接退回用户。

## SRR 图与保留的目标

Planner 已视觉读取 ChatGPT Project 材料中的 SRR-v2、SRR-v2.5、SRR-v3。

当前保留的论文主线为：

```text
observed-modality-only encoding
-> center-source / availability-observation semantics
-> lightweight shared/private/interaction representers
-> signed source-specific sparse retrieval
-> optional supervised-source SIP
-> pathology proposal
-> bounded nnU-Net comparison/safety
```

必须明确：

- 当前 M10 16-slot spatial dictionary、prototype maps 和 semantic negative memory 已出现低杠杆或负证据，不再进入正式实验；
- R2/BR2 的共享 representer + source-specific sparse learner思想尚未被否定；
- 当前任务检验的是可部署的中心分层轻量 BR2，而不是继续修旧 dictionary；
- nnU-Net仍可作为 baseline、anchor、context、error signal和safety source，但不能替代BR2候选本身。

## 历史结果

### Batch 6

```text
edema positive Dice delta: +0.0027247487
scar positive Dice delta: +0.0006739682
mean positive Dice delta: +0.0016993584
```

Batch 6 修通 final pathology supervision 和 production gate，但收益不足。

### Batch 7 formal300

```text
terminal commit: 4c79554de785030ed59081ce3ae233711efc062a
edema positive Dice delta: +0.0054302188
scar positive Dice delta: -0.0048258512
mean positive Dice delta: +0.0003021838
help/harm: 23/35
```

原 Batch 7 机制表因复制指标、identity非零和placeholder已被取代。

### Batch 7 mechanism closure repair

```text
terminal commit: 0fcc3ff605112a0efeab73f3df2f83249793d321
proposal job: 59828884
optimizer steps: 600
mean positive Dice delta: +0.0012229660
scar positive Dice delta: -0.0019961366
edema positive Dice delta: +0.0044420686
help/harm: 25/27
remote-FP relative worsening max: 0.0530525167
```

它真实补齐独立干预、identity零变化、真实category memory、anchor-free discovery代码路径和strict validator。但Planner复核发现proposal stage传入空loss JSON，历史混合M10 loss继续参与，不能作为纯proposal或R2/BR2的最终否定。


### Batch 7 minimal pathology decomposition terminal packet

```text
terminal local commit: recorded_by_this_local_packet_commit
scar job: 59992434 COMPLETED 0:0
edema job: 59994167 COMPLETED 0:0
aggregation status: PASS
scar_minimal: RETIRE
scar_br2: NOT_APPLICABLE
scar_sip: NOT_APPLICABLE
edema_minimal: RETIRE
edema_br2: NOT_APPLICABLE
edema_sip: NOT_APPLICABLE
```

Minimal proposal did not meet the retain gate for either scar or edema. BR2 and SIP are therefore not retained for this MyoPS SRR line. This does not authorize Batch8, refiner, arbiter, gate, Cine, fold expansion, upload, hosted metric claims, or route promotion.

## 论文与数据适配审计

当前权威审计：

```text
results/srr_production/code_maturity/batch7_br2_sip_comprehensive_architecture_audit_20260722.md
```

审计结论：

1. 原论文的source应对应采集中心或数据来源，availability是source的observation set；
2. 原论文默认各source有可靠response，CARE no-T2病例不具备可靠edema监督；
3. 原论文主要面向标量回归/表格数据，不直接覆盖3D密集小病灶分割；
4. 原BR2主公式偏模态加性，interaction是扩展，不能无限堆交互槽；
5. SIP可能在中心异质性下产生负迁移，必须做no-SIP严格消融；
6. neural representer若不固定尺度，可通过放大representer、缩小beta绕开L1/SIP；
7. 逐病例softmax router或image residual会把方法退化为普通mixture-of-experts并绕开source coefficient；
8. validation不能依赖center ID，部署必须使用availability-pattern pooled coefficient。

## 当前 BR2 / SIP 正式语义

### Training source 与 deployment source

```text
training source: metadata.center
the source observation set: availability vector
deployment source: pooled availability pattern
center as network/router input: forbidden
center as training coefficient index: allowed
validation uses center-specific beta: forbidden
```

训练期系数：

$$
\beta_{p,d}^{(c)}=\bar\beta_{p,d}^{(a_c)}+\delta_{p,d}^{(c)},
$$

同availability pattern内 `delta` 和为零并使用L2 shrinkage。训练forward使用center beta；44例验证和部署只使用pattern beta。

### Lightweight representers

只允许：

```text
shared anatomy
LGE private
C0 private
T2 private
LGE-C0 interaction
LGE-T2 interaction
T2-C0 interaction
```

它们只接在proposal用的全分辨率pathology feature上，每个独立参数化、末层零初始化、乘beta前固定per-case RMS。Private只读本模态，interaction读取归一化双模态特征、乘积和绝对差。

### Learner coefficients

```text
pathology-specific
spatially global
signed and unconstrained
no softmax/simplex/top-k
no image-conditioned coefficient residual
hard availability mask by multiplication
invalid effective beta exact zero
```

### SIP

旧：

```text
semantic_retrieval_regularization: formal weight 0
pattern_sip_integrativeness_loss: formal weight 0
```

新：

```text
loss_br2_source_l1_sparsity
loss_br2_center_deviation_shrinkage
loss_br2_selective_integration_penalty
```

SIP只作用于同时观察到所需模态并拥有可靠目标病种监督的训练中心系数。No-T2中心不得建立edema beta，不得进入edema SIP、loss或negative。`|O|<=1` 的representer排除。

允许的论文表述只能是：

```text
R2/BR2/SIP-inspired medical imaging adaptation
```

禁止声称原论文excess-risk理论直接适用于3D分割，禁止声称已因果分离center和missingness。

## 当前唯一任务

```text
BATCH7_FINAL_CENTER_HIERARCHICAL_BR2_SIP_PATHOLOGY_DECOMPOSITION
```

权威文件顺序：

```text
1. results/srr_production/code_maturity/batch7_br2_sip_comprehensive_architecture_audit_20260722.md
2. docs/plans/laneB_round04_active_srr_batch7_minimal_pathology_decomposition_execution.md
3. configs/srr_production/myops_batch7_minimal_decomposition.yaml
4. prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_controller.md
5. prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml
6. results/20260721_srr_batch7_mechanism_closure_repair/
```

## 六个匹配实验

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

同病种三组必须从同一checkpoint开始，使用相同seed、source-balanced病例序列、patch centers、optimizer、400步预算、评价和decode。两个BR2组还必须共享全部BR2初始化及第50步warmup状态，只允许SIP权重不同。

正式sampler：

```text
均匀选择目标病种合格中心
-> 中心内均匀选择病例
-> 病灶或anchor-error patch
```

Edema只使用T2-present可靠监督中心；no-T2 edema全链严格为零。

## Loss和实现硬门

训练前必须证明：

```text
真实中心-模态inventory和病种source eligibility
六组resolved loss完整，空loss JSON被拒绝
legacy semantic/Pattern-SIP精确为零
每个非零loss单独backward且梯度范围正确
center不进入图像网络
validation只使用pattern beta
signed beta且无softmax/simplex/image residual
representer固定RMS并拒绝scale escape
minimal不实例化/消费BR2
BR2 no-SIP/SIP结构、初始化、warmup和采样一致
invalid representer effective beta严格为零
no-T2 source不进入edema beta/SIP/loss
新SIP数值公式测试和权重校准通过
anchor-free discovery覆盖LGE-only scar、T2-present edema、CenterC complete tri-modal
```

## 最终保留门

Minimal：positive-case Dice `>=+0.003`，help>=harm，HD95/remote-FP恶化<=5%，complete-trimodal不下降，no-T2 edema严格为零。

BR2：相对minimal额外Dice `>=+0.001`，安全不恶化，complete-trimodal不下降，worst-positive-center下降不超过`0.003`。

SIP：相对no-SIP额外Dice `>=+0.0005`；或Dice下降不超过`0.0005`且HD95/remote-FP改善至少2%，同时complete-trimodal、worst-center和help/harm不恶化。

终态必须写出：

```text
scar_minimal: RETAIN | RETIRE
scar_br2: RETAIN | RETIRE | NOT_APPLICABLE
scar_sip: RETAIN | REMOVE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_br2: RETAIN | RETIRE | NOT_APPLICABLE
edema_sip: RETAIN | REMOVE | NOT_APPLICABLE
```

Scar minimal仍为负时停止scar SRR，不得用BR2/refiner/gate补救。SIP失败只删除SIP，不自动删除有效BR2。

## 已授权

```text
explicit pathology proposal loss authority
center-source / availability-observation inventory
source-balanced sampler
lightweight normalized shared/private/interaction representers
hierarchical signed source coefficients
training-center beta and deployment-pattern beta separation
supervision-aware BR2 SIP and no-SIP ablation
loss-specific gradient verification
six matched 400-step runs
complete-trimodal and worst-center safety evaluation
strict validator and known-bad
mapper/wiki/fingerprint update
local lightweight result commit
```

## 未授权

```text
Batch8
current M10 dictionary/prototype/memory continuation
refiner training
source-arbiter training
production-gate training
backbone replacement
encoder redesign
fold expansion
Cine
external data or weights
validation packaging/upload
hosted metric claim
route promotion
final scientific stop
```

Controller 的 `VERIFIED_COMPLETE` 只表示本次分解合同完成，下一步仍返回Planner。
