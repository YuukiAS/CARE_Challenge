# CARE SRR Batch 7 最小病种分解执行计划

Plan metadata:
- Type: active execution plan
- Lane: historical Route B lineage on main
- Round scope: round04 post-portfolio main-only
- Status: ready for controller
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_batch7_mechanism_closure_repair_execution.md`
- Function: perform the final minimal decomposition of proposal and dictionary value after Batch7 repair
- Do not: start Batch8, refiner, arbiter, production-gate training, backbone replacement, fold expansion, Cine, validation upload, or another open-ended component repair cycle

## 总体判断

Batch 7 repair 已经证明当前联合 proposal chain 不够好，但其 proposal stage 仍使用混合 M10 loss，不能作为纯 proposal 的最终否定。本计划只做一次最小、可证伪的病种分解：修正 loss authority，分别训练 scar/edema 的 minimal proposal 和 dictionary proposal，随后永久决定每个病种是否保留 dictionary/proposal 路线。

## 固定来源

```text
source main commit: 0fcc3ff605112a0efeab73f3df2f83249793d321
source checkpoint: Batch7 step300
source checkpoint SHA256: d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
fold0 train/validation: 176/44
runtime: anchor_bounded_srr_correction
formal decode: outputs["logits"].argmax
```

## 核心设计

### Minimal proposal

Minimal proposal 只保留：

```text
frozen modality encoders
+ frozen availability-aware base retrieval
+ pathology evidence head
+ anchor-free discovery head
+ anchor-conditioned confirmation head
+ learned discovery/confirmation reliability
```

必须关闭：

```text
M10 spatial dictionary contribution
prototype maps
semantic negative memory
refiner
source arbiter
production gate learning
historical branch arbitration loss
bounded-correction shrink loss
refiner-effect loss
```

输出仍通过固定全开 bounded correction 与 nnU-Net anchor 比较，以保持评价语义一致；但 gate 参数不得训练。

### Dictionary proposal

Dictionary proposal 与 minimal proposal 使用完全相同的初始化、训练病例顺序、patch centers、optimizer、步数、评价和 decode，只增加：

```text
real prototype maps
M10 spatial dictionary
```

Semantic category negative memory 本轮不进入正式训练，因为真实 intervention 已显示它没有正收益。它只保留为诊断资产。

## Loss authority

每个正式 stage 必须生成 `resolved_stage_loss_weights.csv`。Minimal 和 dictionary 训练只允许以下非零损失：

```text
目标病种 proposal BCE/Dice: 1.0
目标病种 discovery BCE/Dice: 1.0
目标病种 confirmation BCE/Dice: 0.5
目标病种 anchor-missed-lesion recovery: 1.0
目标病种 anchor-false-positive suppression: 0.10
no-T2 edema safety: 0.50（仅 edema）
prototype/spatial conditioning: 0.10（仅 dictionary variant）
```

其他 pathology、refiner、final-logits、source-arbiter、production-gate、branch-arbitration、correction-opportunity、bounded-correction、refiner-effect、semantic-negative-memory、generic load-balance 和 Pattern-SIP loss 必须为零。

Gradient authority 必须对每个正式非零 loss 分别 backward，证明梯度只到达该 stage 声明的目标模块；不得再对 logits 均值 backward 代替 loss 验证。

## 实验矩阵

四个实验均从相同 source checkpoint 独立开始，每个 400 optimizer steps，在 200/400 对全部 44 例评价：

```text
scar_minimal
scar_dictionary
edema_minimal
edema_dictionary
```

共同参数：

```text
optimizer: AdamW
learning rate: 1e-4
weight decay: 1e-4
batch size: 1
patch shape: 12x96x96
encoder/base retrieval frozen: true
refiner/arbiter/gate frozen: true
```

Scar stage 必须保证 scar-positive patch sampling；edema stage 只从 T2-present edema-supervised病例采样，不得将 no-T2 病例作为 edema negative。

## 完整实现门

训练前必须通过：

1. `resolved_stage_loss_weights.csv` 精确列出全部 loss，非授权项均为零；
2. known-bad fixture：空 `{}` loss config、refiner loss 非零、final/gate loss 非零、semantic memory 非零均必须被 validator 拒绝；
3. loss-specific gradient matrix覆盖 scar minimal、scar dictionary、edema minimal、edema dictionary；
4. anchor-free discovery检查至少覆盖：一个 LGE-only scar病例、一个 T2-present病例、一个 CenterC完整多模态病例；
5. 四个实验有独立 runtime、prediction、checkpoint、log 和 lock root；
6. checkpoint save/reload final logits最大差 `<=1e-6`。

## 评价与最终删除门

每个病种单独判断，不再用 scar/edema mean 掩盖冲突。

### Minimal proposal 保留门

```text
positive-case Dice delta >= +0.003
help >= harm
HD95 relative worsening <= 5%
remote-FP relative worsening <= 5%
no-T2 edema exact zero
```

Scar minimal 未通过：

```text
RETIRE_SCAR_SRR_PROPOSAL_FOR_CHALLENGE
use nnU-Net scar anchor
no more scar dictionary/refiner/arbiter/gate repair
```

Edema minimal 未通过：

```text
RETIRE_EDEMA_SRR_PROPOSAL_FOR_CHALLENGE
use nnU-Net edema anchor
no more edema dictionary/refiner/arbiter/gate repair
```

### Dictionary 增量保留门

Dictionary 相对同病种 minimal 必须：

```text
additional positive-case Dice >= +0.001
help/harm not worse
HD95 and remote-FP not worse by >2%
```

未通过则删除该病种的 spatial dictionary/prototype maps，不得继续调 dictionary。

## 终态输出

```text
results/20260722_srr_batch7_minimal_pathology_decomposition/
```

至少包含：

```text
resolved_stage_loss_weights.csv
loss_specific_gradient_matrix.csv
anchor_free_discovery_coverage.csv
matched_run_manifest.csv
checkpoint_selection.csv
pathology_decision_matrix.csv
dictionary_increment_matrix.csv
casewise_metrics.csv
subgroup_metrics.csv
help_harm.csv
slurm_attempts.csv
controller_report.md
completion_check.md
MANIFEST.md
```

Controller 必须返回四个不可含糊的决定：

```text
scar_minimal: RETAIN | RETIRE
scar_dictionary: RETAIN | RETIRE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_dictionary: RETAIN | RETIRE | NOT_APPLICABLE
```

本任务完成后返回 Planner，不自动进入 refiner、arbiter、gate 或 Batch8。