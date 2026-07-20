# CARE SRR Batch 1：MyoPS 单一主干原地修复

Plan metadata:
- Type: authoritative executable code-repair plan
- Lane: historical Route B merged into main; single active SRR mainline
- Round scope: post-Round04 main-only sprint; no Round05
- Status: active after Batch 0 commit `414427746e51e5d84918e57512619a2d3412326c`
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_plan_correction_addendum.md`
- Function: 将 Batch 0 选定的现有 `SRRProposeRefineMyoPS` 和真实 fold0 runner 原地修复为一条完整、连续、可做真实 inference 的 MyoPS 主干
- Do not: 不修改 Cine；不完成公平 fold0 比较；不正式训练；不提交 Slurm；不写第二套模型；不恢复 B3-B6 阶段链；不把测试 PASS 写成训练就绪
- Supersedes: 父计划/TODO 中任何把 `scripts/evaluation/evaluate_predictions.py`、完整公平比较或 Cine 纳入 Batch 1 的表述；这些工作属于 Batch 2/3

## 1. Batch 0 绑定事实

Batch 0 已确认：

1. 当前唯一应继续修复的模型源码是 `src/care_myocardium/models/srr_propref.py`，状态为 `real_but_incomplete`。
2. 当前唯一训练候选是 `scripts/training/run_srr_propref_myops_fold0.py`，它读取真实 Dataset501 数据，但没有 formal authority。
3. 当前正式训练入口为空：`formal_entrypoints: []`，状态为 `BLOCKED_PENDING_BATCH1_REPAIR`。
4. Round04 B3-B8 及其 job wrappers 已被禁止作为正式入口。
5. 现有 ProposalDictionary 在没有真实 runtime bank 时会保留 deterministic-axis prototype fallback。
6. M10 cross-fitted memory 已有类和状态字段，但 query 没有接入 proposal/final logits。
7. 同一模型类混有 legacy residual、M6 arbitration、M9 pure SRR-main、M10 pure proposal-refinement 等互斥 final-output 语义。
8. 当前 runner 使用真实缓存 nnU-Net 概率/预测作为 anchor/context，但没有形成严格 checkpoint/split/case/provenance authority。
9. B3->B4->B5->B6 是 token/file existence 关系，不是连续模型 checkpoint；Batch 1 不修复这条旧链，而是废弃它的 production 权限。
10. `scripts/evaluation/evaluate_predictions.py` 已是真实 prediction/GT metric 实现，但 component/remote-FP 和公平比较封装属于 Batch 2。

## 2. Batch 1 唯一目标

Batch 1 只解决：

> 把现有 MyoPS SRR 模块第一次收束成一个真实病例可端到端 forward/backward、使用真实 OOF anchor 与 prototype/memory、拥有唯一 final-output 语义、可完整 save/reload 的单一模型和单一连续 runner。

完成后的数据流必须是：

```text
真实 Dataset501 [LGE,T2,C0] + availability
-> modality-specific encoders
-> four-scale shared/private/interaction retrieval
-> spatial/pathology-conditioned retrieval + live Pattern-SIP statistics
-> anatomy union/LV/RV
-> real cross-fitted scar/edema prototypes and safe-negative memory
-> separate scar/edema proposal
-> separate soft-ROI refiner
-> pathology-specific bounded correction
-> same-case real OOF nnU-Net anchor logits/probabilities
-> final logits
-> one complete checkpoint
```

Batch 1 不评价是否超过 nnU-Net；它只证明这条代码链真实、连续且不能退化为 deterministic/random/placeholder。

## 3. 唯一生产模型语义

不得继续让 variant 名称隐式决定 final logits。必须在现有 `SRRProposeRefineMyoPS` 中增加显式 production final-output mode，并由 production config 固定为：

```text
final_output_mode: anchor_bounded_srr_correction
final_logits = anchor_logits + bounded_pathology_specific_correction
```

要求：

- nnU-Net anchor 是稳定 segmentation basis，不参与反向传播。
- SRR correction 必须来自真实原始模态、retrieval、prototype proposal 和 refiner，不得只读取 nnU-Net hard prediction做后处理。
- `anchor_identity_control` 强制 correction 为零时必须逐体素恢复 anchor。
- `srr_no_anchor_control` 只作为诊断输出，不是 production 默认。
- M9/M10 pure-SRR output 仍可保留为历史/control，但 production mode 不得走它们。
- 不新增第二个模型类；允许新增 config、enum、薄 facade 或 production alias。

Production scientific configuration 应保留完整结构：四尺度、shared/private/interaction、spatial retrieval、Pattern-SIP 和 cross-fitted memory。若其中任何一项在本批无法真实接通，Batch 1 必须返回 blocked/partial，不得静默降级为 M6 或普通 residual head。

## 4. 真实 nnU-Net anchor authority

Batch 1 不强制在 SRR 进程中重新运行 nnU-Net checkpoint。允许使用已有缓存概率/logits，但必须把它升级为可验证的真实 OOF anchor authority。

必须建立 manifest，逐 case 记录：

- case ID；
- 来源 fold；
- probability/logit/prediction path；
- nnU-Net checkpoint path 与 SHA256；
- plans/trainer/config；
- preprocessing/split hash；
- tensor shape、class order和空间信息；
- 是否 OOF。

规则：

- 每个病例必须使用其对应 validation fold 产生的 OOF anchor；不得使用随机 anchor。
- fold0 validation cases 使用 fold0 validation probabilities。
- fold0 training cases应从其作为 validation case 的其他折 OOF 输出获得 anchor；若仓库缺少全病例 OOF probabilities，Batch 1 必须明确阻塞，不得改用随机、GT或无 provenance fallback。
- anchor 缺失、shape/class/affine/hash 不符必须 fail closed。
- anchor tensor 只作为 frozen context/safety/final base。

## 5. 真实 cross-fitted prototype 与 memory

### 5.1 禁止 fallback

Production mode 中：

- `deterministic_axis_prototypes` 只能用于未拟合模块初始化和 tests；
- 进入真实 forward 前，scar/edema bank 必须有完整 provenance；
- 没有有效 vectors 时直接失败，不能重复最后一个向量、使用 deterministic axis 或生成 random bank。

### 5.2 四 shard cross-fitting

在 fold0 training cases 内建立固定四 shard：

- prototype source 只能来自 fold0 training set；
- validation cases不得进入；
- 当前训练 case 不得查询包含自身 feature 的 bank；
- validation/inference 查询由全部 fold0 training shards拟合的 frozen bank；
- scar：positive、normal myocardium、outside myocardium、blood pool、LGE artifact、remote FP；
- edema：T2-present positive 与 T2-present safe negatives；
- no-T2 myocardium绝不能进入 edema negative。

每个 bank 保存 source cases、shard、checkpoint/config/preprocess/feature hashes、class、availability 和 counts。

### 5.3 接入真实前向

必须形成：

```text
cross-fitted memory query
-> positive/negative similarity
-> proposal formula terms
-> proposal logits
-> refiner logits
-> bounded final correction
```

`M10CrossFittedPrototypeMemory.query` 必须真实影响 proposal/final output。关闭 memory 或替换 bank 后，同一真实 batch 的 proposal/final logits 必须发生可测变化。

## 6. Router、Pattern-SIP 与 missing-slot mask

必须保持现有四尺度 shared/private/interaction retrieval，并修复为 production 可审计状态：

- availability 明确控制 valid slot；
- 缺失模态 private/interaction slot 权重逐 batch/task/scale/slot 严格为零；
- spatial/pathology-conditioned query 真实读取局部 feature、anatomy、proposal/uncertainty；
- Pattern-SIP 使用 live forward gate statistics，不得从运行后 CSV 反推；
- Pattern-SIP loss 对 router 参数必须有非零梯度；
- load balance/coverage 与 Pattern-SIP 不能只是同一个 loss 的不同名称。

## 7. Loss 真实优化闭环

在现有 runner/模型中原地修复 loss。每项必须分类为 `optimized`、`monitor_only` 或 `control_only`：

- anatomy DiceCE；
- scar proposal；
- scar refiner/final correction；
- edema proposal，仅 T2-present 且 edema label available；
- edema refiner/final correction，仅 T2-present 且 edema label available；
- scar negative-space/remote-FP；
- edema T2-present safe-negative；
- soft anatomy/ROI；
- dictionary similarity/contrast；
- memory alignment/update；
- router load balance；
- live Pattern-SIP；
- bounded correction/preservation。

要求：

- 不得保留 alias loss 冒充独立机制；
- placeholder zero loss 只能标为未实现并阻塞 production；
- 真实 T2-present batch 上梯度必须到达 edema encoder/router/dictionary/proposal/refiner；
- no-T2 batch 上所有 edema-owned loss、proposal correction、refiner correction和相关梯度必须为零；
- scar 和 edema分别报告梯度，不用 composite mean 掩盖。

## 8. 单一连续 checkpoint 与 resume

废弃 B3-B6 production stage continuity。一个 runner、一个模型对象、一个 checkpoint series。

Checkpoint 必须保存并恢复：

- complete model state；
- optimizer、scheduler、AMP scaler；
- global step/epoch；
- production final-output mode；
- encoder/router/dictionary/proposal/refiner config；
- OOF anchor manifest hash；
- prototype/memory banks与 provenance；
- split/case/label/preprocess hashes；
- source commit；
- RNG states；
- best-metric state占位结构（本批不做正式选择）。

Save/reload 后同一真实输入的所有关键 tensor 必须一致，resume 不得重新拟合/重置 prototype、memory、gate或step。

## 9. Batch 1 允许的真实运行

允许：

- 三种 modality pattern 各一例真实 load/forward；
- T2-present 和 no-T2 各一个真实 batch 的单次 backward；
- 2-4 个真实病例的 prototype/memory 小样本构建 smoke；
- anchor identity control；
- module on/off intervention；
- checkpoint save/reload；
- unit/integration/known-bad tests。

禁止：

- 多步或持续 optimizer loop；
- micro-overfit；
- fold0正式训练；
- Slurm；
- 全44例性能比较；
- 修改公平 evaluator主实现；
- Cine工作；
- performance/leaderboard结论。

## 10. 必须生成的代码与证据

优先修改现有文件：

```text
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/models/srr_dictionary_memory.py
scripts/training/run_srr_propref_myops_fold0.py
```

允许新增薄层/测试：

```text
configs/srr_production/myops_batch1.yaml
scripts/srr_production/validate_myops_mainline.py
tests/srr_production/test_myops_mainline_batch1.py
```

必须生成：

```text
results/srr_production/code_maturity/batch1_model_contract.json
results/srr_production/code_maturity/batch1_anchor_oof_manifest.json
results/srr_production/code_maturity/batch1_prototype_memory_provenance.json
results/srr_production/code_maturity/batch1_real_case_forward_receipt.json
results/srr_production/code_maturity/batch1_gradient_receipt.csv
results/srr_production/code_maturity/batch1_intervention_receipt.json
results/srr_production/code_maturity/batch1_checkpoint_roundtrip.json
results/srr_production/code_maturity/batch1_known_bad_report.json
```

并更新：

```text
configs/srr_production/entrypoints.yaml
docs/plans/laneB_round04_active_srr_change_review_ledger.md
```

## 11. Known-bad 必须失败

- production mode使用 deterministic/random prototype；
- prototype provenance缺 source cases/shard/hash；
- validation case进入prototype source；
- current case查询包含自身的 cross-fitted bank；
- no-T2进入edema negative；
- no-T2 edema loss/delta/gradient非零；
- missing modality private/interaction slot权重非零；
- Pattern-SIP只来自post-hoc summary或无router梯度；
- memory query关闭前后proposal完全不变；
- production final output走pure SRR或隐式variant分支；
- anchor不是OOF或provenance/hash不完整；
- checkpoint reload重置memory/prototype/step；
-旧 B3-B8进入任何 formal/candidate production chain。

## 12. 完成状态

Batch 1 完成后仍不得正式训练。`configs/srr_production/entrypoints.yaml` 应使用：

```text
formal_training_status: BLOCKED_PENDING_BATCH2_INFERENCE_AND_FAIR_EVALUATION
```

允许的 Batch 1 最终状态：

```text
BATCH_1_MYOPS_MAINLINE_COMPLETE_FOR_BATCH2
BATCH_1_MYOPS_MAINLINE_NEEDS_REPAIR
BATCH_1_BLOCKED_MISSING_REAL_OOF_ANCHOR
BATCH_1_BLOCKED_PROTOTYPE_MEMORY_NOT_CONNECTED
```

不得输出：

```text
TRAINING_READY
SCIENTIFIC_PASS
SRR_ABOVE_NNUNET
LEADERBOARD_READY
```
