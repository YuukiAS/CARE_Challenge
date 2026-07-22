# CARE SRR Batch 8：干净 edema BR2 确认与 Batch 7 证据修复

Plan metadata:
- Type: active execution plan
- Lane: historical Route B lineage on main
- Round scope: post-round04 main-only
- Status: ready for controller
- Function: repair Batch7 terminal mechanism evidence and perform a clean two-seed edema minimal-versus-BR2 comparison
- Do not: train scar, SIP, refiner, source arbiter, production gate, old M10 dictionary/prototype/memory, Cine, fold expansion, validation upload, or hosted claims

## 动机

Batch 7 的六组任务虽已完成，但 scar BR2 清空、SIP/no-SIP完全相同、训练后 beta 未真实导出、机制文件仍有 `PENDING`，而 validator 没有拒绝这些问题。Edema BR2 相对 minimal 有 `+0.0016204931` 增量，绝对正例 Dice 增量为 `+0.0029631724`，接近但未达到旧门槛。Batch 8 只回答这个信号是否在干净实现和两个 seed 下成立。

## 固定来源

```text
remote/main at controller bootstrap: must bind latest
source checkpoint path: results/20260721_srr_batch7_upstream_candidate_quality/runtime/attempts/batch7_formal300_htzhulab_59789651/variants/batch7_formal300_htzhulab_59789651/checkpoints/fold_0/propref_config/checkpoint_validation_step_300.pt
source checkpoint SHA256: d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
fold0 train/validation: 176/44
same-split nnU-Net anchor: required
formal decode: six-class logits argmax
primary pathology population: T2-present edema-positive validation cases
```

## Phase 0：修复 Batch 7 终态证据

从 Batch 7 的 scar/edema warmup50、step200、step400 checkpoints 逐一真实加载并写入：

```text
results/20260722_srr_batch8_clean_edema_br2_confirmation/batch7_checkpoint_mechanism_export.csv
results/20260722_srr_batch8_clean_edema_br2_confirmation/batch7_scar_collapse_diagnosis.csv
results/20260722_srr_batch8_clean_edema_br2_confirmation/batch7_sip_effect_diagnosis.csv
results/20260722_srr_batch8_clean_edema_br2_confirmation/batch7_packet_supersession.md
```

每个 checkpoint 必须记录实际文件 SHA、global step、beta pattern、center deviation、effective beta、representer RMS、projection norm、proposal-logit分位数、预测正体素数、SIP值。不得新建模型后导出初值，不得写 `PENDING`，不得用 summary label 代替 tensor。

`batch7_packet_supersession.md` 必须明确：原六组 runtime可保留为操作证据，但 BR2/SIP scientific closure 被本审计 supersede，原因是机制证据不完整。

## Phase 1：实现独立干净模型

新增：

```text
src/care_myocardium/models/srr_batch8_clean_edema.py
```

类：

```text
CleanEdemaBR2Corrector
```

模型只复用并冻结 source checkpoint 中的白名单模块：modality encoders、existing base retrieval、anatomy decoder、edema decoder，以及产生 anatomy-union context 所需的一方权重。模型不得实例化旧 `SRRProposeRefineMyoPS` 完整对象后仅靠 flags 关闭模块；必须由薄模型显式持有所需子模块，避免旧 forward 被调用。

### Clean minimal

```text
frozen edema feature
+ resampled T2 image
+ frozen anatomy-union probability
-> clean two-block 3D conv head
-> edema correction delta
```

末层零初始化。最终六类 logits 仅修改 edema 通道：

$$z_{4}^{final}=z_{4}^{anchor}+2\tanh(\Delta_{ede}),$$

其余通道等于原始 nnU-Net logits。无 T2 时 $\Delta_{ede}=0$，final logits 和 labels 必须严格恢复 anchor。

### Clean BR2

在 clean minimal 的 edema feature 前增加四个独立模块：

```text
shared_anatomy
lge_private
t2_private
interaction_lge_t2
```

每个模块独立参数化、末层零初始化、乘 beta 前固定 per-case RMS。Interaction 输入为归一化 LGE/T2、逐点乘积和绝对差。系数为 edema-specific signed spatially-global beta；禁止 softmax、simplex、top-k、image-conditioned beta residual。

训练期：

$$\beta_d^{(c)}=\bar\beta_d+\delta_d^{(c)},\quad c\in\{CenterB,CenterC\},$$

并约束两中心 deviation 和为零。验证只使用 pooled $\bar\beta_d$，center ID 不得作为网络输入。

## Phase 2：训练前证据门

必须生成：

```text
clean_model_import_graph.json
checkpoint_whitelist_load.csv
legacy_module_call_counters.csv
clean_initial_equivalence.json
clean_no_t2_identity.csv
clean_fixed_overfit.json
clean_loss_gradient_matrix.csv
clean_checkpoint_roundtrip.json
clean_known_bad_report.json
```

硬门：

- 旧 ProposalDictionary、M10 spatial dictionary、prototype/memory、refiner、arbiter、branch arbitration、production gate调用计数均为0；
- checkpoint只加载白名单模块，所有加载/忽略 key明确记录；
- BR2初始 final logits与minimal最大差 `<=1e-6`；
- no-T2 final logits与anchor最大差 `0`、changed labels `0`；
- fixed overfit使用两个真实T2-present edema病例，100步，loss下降至少30%，prediction非空，formal credit 0；
- 每个非零loss单独backward，冻结模块和未授权模块梯度为0；
- save/reload最大差 `<=1e-6`；
- known-bad必须真实拒绝：旧模块混入、静态beta导出、`PENDING`字段、空预测完成、no-T2 delta非零、错误matched seed/sampler、validator只查文件。

任一不通过，不得提交正式训练。

## Phase 3：两个 seed 的正式匹配实验

固定实验：

```text
seed 20260722:
  edema_clean_minimal_seed20260722
  edema_clean_br2_seed20260722
seed 20260723:
  edema_clean_minimal_seed20260723
  edema_clean_br2_seed20260723
```

每组：

```text
optimizer: AdamW
learning rate: 1e-4
weight decay: 1e-4
batch size: 1
patch: 12x96x96
optimizer steps: 800
full-volume evaluation: 200, 400, 800
```

同一 seed 的 minimal/BR2 必须共享：source checkpoint、common-head initialization、case sequence、center sequence、patch centers、augmentation、optimizer state template、budget、evaluation和decode。BR2额外参数零初始化。

采样：

```text
uniform CenterB/CenterC
-> uniform eligible case
-> 50% edema-positive patch / 50% nnU-Net edema-error patch
```

仅使用 T2-present、reliable edema supervision。No-T2病例只用于终态安全评价，不进入训练、beta、loss或negative。

## Slurm

一个 Executor 管理两个独立 seed jobs。允许并行提交，因为两者只读同一不可变checkpoint，且拥有完全隔离的：

```text
runtime root
prediction root
checkpoint root
log root
lock root
```

默认：

```text
seed20260722 -> htzhulab
seed20260723 -> a100-gpu
```

两者都必须使用：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

正式前各partition做同语义GPU preflight。任一独立job启动失败可按同范围规则在兼容partition重试；不得改变seed、模型、预算或采样。所有训练job之后使用 `afterany` finalizer完成accounting、aggregation、strict validator和local lightweight commit。

## Loss

仅允许：

```text
loss_clean_edema_final_bce_dice = 1.0
loss_clean_edema_anchor_error = 0.50
loss_clean_edema_confident_anchor_preserve = 0.10
loss_clean_br2_beta_l1 = 0.001       # BR2 only
loss_clean_br2_center_deviation_l2 = 0.001  # BR2 only
```

不得调用旧 `propref_loss` 或 M10 expanded total loss。Loss实现应位于独立函数，resolved loss必须来自实际训练命令而非计划静态表。

## 评价与证据

每个 seed/variant 必须输出全部44例独立预测和：

```text
casewise Dice/HD95/remote-FP/component/changed voxels
T2-positive edema population
CenterB
CenterC
complete tri-modal
help/harm
proposal/correction precision-recall
anchor FN recovery
anchor FP suppression
prediction positive voxel counts
actual beta/projection/representer diagnostics from selected checkpoint
```

Checkpoint selection固定为step800，不做best选择，避免选择偏差；step200/400只做学习轨迹诊断。Step800 checkpoint必须reload后重新推理。

## 终态保留门

Clean BR2保留需同时满足：

```text
each seed BR2 positive-case Dice delta >= +0.002
mean across seeds BR2 positive-case Dice delta >= +0.003
each seed BR2-minus-minimal >= +0.0005
mean BR2-minus-minimal >= +0.001
CenterB mean delta >= 0
CenterC mean delta >= 0
combined help >= harm
HD95 non-worse
remote-FP relative worsening <=5%
no-T2 exact anchor identity
no empty prediction
all mechanism fields numeric and checkpoint-derived
```

终态：

```text
PASS -> EDEMA_CLEAN_BR2_RETAIN_PENDING_PLANNER
FAIL -> RETIRE_SRRMyoPS_PERFORMANCE_LINE_USE_NNUNET
```

Scar固定：

```text
SCAR_SRR_TRAINING_STOPPED
challenge scar = nnU-Net anchor
```

## 未授权

```text
SIP training
refiner training
source arbiter / production gate
scar training
Batch9
fold expansion
Cine
external data or weights
validation package/upload
hosted metric claim
route promotion
final scientific stop beyond this MyoPS performance-line decision
```

任务完成后返回 Planner。