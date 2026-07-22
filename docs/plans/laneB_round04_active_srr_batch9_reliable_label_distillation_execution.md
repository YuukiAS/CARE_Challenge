# CARE MyoPS Batch 9：可靠标签蒸馏直接分割主线执行计划

## 实际意义

Batch 9 不是继续修旧 SRR，也不是把 current Batch 8 的 edema anchor correction 扩大。它重新建立一个不依赖 nnU-Net anchor 的直接分割模型，用强 residual-encoder 主干承担性能上限，用可靠标签掩码处理 no-T2 edema 缺标，用结构化模态缺失和完整视图 teacher 解决训练数据不完整与官方完整三模态部署之间的差距。

Batch 8 保留为历史诊断合同，但不再拥有 formal authority。Batch 9 是当前唯一允许启动的 Controller 任务。

## 1. 动机背景

仓库标准 nnU-Net fold0 已有可复现基线，但 scar/edema 仍低，历史 SRR 多轮结果长期表现为 edema 小幅正、scar 受损。工程真实性问题虽逐步修复，复杂 dictionary/prototype/memory/refiner/gate 链仍没有提供可分离的强增益。

Deep Research 指出，CARE MyoPS 的核心不是普通随机缺模态，而是：

```text
availability 与 center 高度绑定
edema supervision 只在 T2-present source 可靠
官方 validation/test 是未知 CenterD 的完整三模态
scar 与 edema 的形态和模态依赖不同
```

因此下一轮必须将缺输入、缺标签和中心偏移拆开处理，而不是由一个 retrieval 链同时解释。

## 2. 核心目标

Batch 9 依次回答三个问题：

1. 在不使用旧 SRR 和 nnU-Net anchor correction 的情况下，可靠标签 ResEnc 直接分割是否能达到或超过当前标准 nnU-Net；
2. 结构化 modality dropout 是否能改善训练分布而不伤害完整三模态；
3. 完整视图 teacher 的可靠标签蒸馏是否在两个 seed 上稳定提高完整三模态 scar/edema。

本批不回答 BR2-lite、SIP、prototype、memory、refiner 或 Cine 是否有效。

## 3. 权威输入

```text
results/srr_production/code_maturity/batch9_reliable_label_distillation_planner_synthesis_20260722.md
configs/care_mm/batch9_reliable_label_distillation.yaml
prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_controller.md
prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_executor_plan.yaml
prompts/routes/handoffs/CURRENT.md
```

数据与基线：

```text
Dataset501_CAREMyoPS
fold0: 176 train / 44 validation
standard baseline: nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres
```

必须从真实 metadata 与 split 重新生成中心、模态、标签可靠性 inventory，不得把 Deep Research 或旧 CURRENT 中的数量当作运行时真值。

## 4. 新模型

### 4.1 文件与类

```text
src/care_myocardium/models/care_mm_reliable_distill.py
CAREMMReliableDistillResEnc
```

共享一个模型类，teacher/student 是不同 checkpoint 实例。禁止复制两套近似但漂移的模型代码。

### 4.2 输入与模态处理

输入固定为 Dataset501 顺序：

```text
0: LGE
1: T2
2: C0
```

每个模态有独立 stem：

```text
Conv3d(1,8,3,padding=1,bias=False)
InstanceNorm3d(8,affine=True)
GELU
```

Stem 输出立即乘 availability mask。缺失模态 stem 输出必须逐体素精确为0。三个 stem 输出与三个 broadcast availability channel 拼接成27通道，输入 ResidualEncoderUNet。

不得使用 center embedding、center-specific normalization、center classifier、router 或部署时 source lookup。

### 4.3 主干

默认使用当前环境中 nnU-Net v2 / dynamic-network-architectures 提供的 `ResidualEncoderUNet`，结构和显存等级对齐 `nnUNetResEncUNetMPlans`。Executor必须在 GPU preflight 中记录：

```text
nnunetv2 version
dynamic_network_architectures version
ResidualEncoderUNet import path
plans identifier
stage channels
kernel/stride schedule
parameter count
patch size
batch size
```

若当前环境无法导入官方 ResidualEncoderUNet，不得静默换回旧 SRR encoder或自创 tiny network；必须在同任务内安装与当前 nnU-Net 兼容的已锁定依赖，或返回 `OPERATIONALLY_BLOCKED` 并给出精确环境错误。不得改变 backbone 科学语义。

### 4.4 输出头与解码

主干输出共享高分辨率 decoder feature，接三个独立头：

```text
anatomy_head: 4 channels [background, healthy myocardium, LV, RV]
scar_head: 1 residual channel
edema_head: 1 residual channel
```

六类 logits：

```text
z0 = anatomy[0]
z1 = anatomy[1]
z2 = anatomy[2]
z3 = anatomy[3]
z4 = anatomy[1] + edema_residual
z5 = anatomy[1] + scar_residual
```

Final prediction固定为六类 logits argmax。No-T2推理将 `z4` 设为-20。正式完整三模态评价不做阈值搜索、形态学后处理或 nnU-Net blend。

## 5. 数据与监督

### 5.1 可靠标签规则

```text
anatomy: 所有label有效病例；label 4/5 remap为myocardium
scar: 所有metadata标记scar可靠的病例
edema: T2 present且metadata标记edema可靠的病例
```

No-T2病例的 edema loss mask、edema distillation mask、edema consistency mask必须全0。它们不能成为 edema negative。

### 5.2 中心平衡采样

每个step：

```text
50% edema-eligible pool：先均匀选合格中心，再均匀选病例
50% anatomy/scar pool：先均匀选所有训练中心，再均匀选病例
```

Patch继续使用病灶/解剖感知采样，但同一seed的moddrop control与distill必须复用完全相同的病例、patch center与augmentation manifest。

### 5.3 结构化 modality dropout

自然 availability 之外只允许进一步删除已观测模态，不允许插补：

```text
full -> full 0.50 / LGE+C0 0.25 / LGE-only 0.25
LGE+C0 -> LGE+C0 0.75 / LGE-only 0.25
LGE-only -> LGE-only 1.00
```

LGE不删除。每个step的自然mask、student mask和随机数必须进入manifest。

## 6. Loss

### 6.1 Segmentation

```text
loss_anatomy_ce_dice = 1.0
loss_scar_bce_dice = 1.0
loss_edema_bce_dice_reliable_only = 1.0
```

Anatomy target将scar/edema remap为healthy myocardium。Scar/edema为独立binary BCE+Dice，并通过六类组合logits接受额外 final multiclass consistency检查，但不得重新引入对no-T2 edema的背景惩罚。

### 6.2 Modality dropout consistency

`student_moddrop_control` 与 `student_reliable_distill` 均使用：

```text
loss_moddrop_consistency = 0.1
```

只比较同一病例 full/natural view 与 sampled student view 中具有可靠监督的输出。自然缺失病例不构造不存在的full target。

### 6.3 Teacher distillation

Teacher从相同seed的direct baseline复制，并在完整三模态、可靠标签训练病例上fine-tune。Teacher全视图，student结构化缺失视图。

```text
loss_distill_logits = 0.5
loss_distill_feature = 0.1
loss_distill_anatomy = 0.1
temperature = 2.0
teacher_confidence_threshold = 0.60
```

Distillation只用于天然完整三模态训练病例。Edema distillation还必须满足edema可靠。Teacher冻结，student全模型可训练。

`student_moddrop_control`也必须执行同一frozen teacher forward，但所有distillation权重为0；这样两组的计算路径、batch和显存条件可核对。

## 7. 实验与预算

固定两个seed：

```text
20260723
20260724
```

每seed流水线：

### Stage A：direct baseline

```text
variant: student_direct_reliable
500 epochs
250 optimizer steps/epoch
125000 optimizer steps
validation every 25 epochs
formal checkpoints: epoch 250 and 500
selected checkpoint: epoch 500 only
```

### Stage B：complete-view teacher

```text
variant: teacher_full_view
warm start: same-seed direct epoch500
100 epochs
25000 optimizer steps
complete-trimodal reliable cases only
selected checkpoint: epoch100 only
```

### Stage C：matched continuation

从同一 direct epoch500 checkpoint分别启动：

```text
student_moddrop_control: 100 epochs
student_reliable_distill: 100 epochs
```

两者共享所有student侧随机序列。Selected checkpoint固定为epoch100并reload。

短smoke、100-step overfit、failed startup、partial checkpoint、race loser均为formal credit 0。

## 8. Slurm

两个seed流水线可以并发，单seed内部用`afterok`：

```text
seed20260723: htzhulab
seed20260724: a100-gpu
```

若一个主partition长期pending，允许按Slurm skill做隔离race。V100只在相同patch、batch、AMP、模型和预算通过preflight时允许作为fallback；不得为适配V100缩小模型或batch语义。

正式Python：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

最终accounting/finalizer对所有attempt使用`afterany`。Submitted/pending/running不是完成。

## 9. 实现前硬门

必须输出并通过：

```text
center_modality_label_inventory.csv
clean_model_import_graph.json
legacy_module_call_counters.csv
resenc_environment_contract.json
availability_hard_mask_checks.csv
reliable_supervision_mask_checks.csv
resolved_loss_contract.json
loss_gradient_matrix.csv
fixed_real_case_overfit.json
checkpoint_roundtrip.json
known_bad_report.json
```

Fixed overfit使用至少：

```text
1个完整三模态病例
1个LGE-only病例
1个LGE+C0病例
```

100 steps，formal credit 0。各自可监督loss下降至少30%，完整病例scar/edema预测非空；no-T2 edema supervised voxel count精确为0。

Known-bad必须拒绝：

```text
实例化旧SRR/ProposalDictionary
缺失模态stem非零
center进入网络tensor
no-T2进入edema loss或distillation
非零loss未进入total
静态config冒充runtime resolved loss
不同matched variant使用不同sampler
checkpoint未reload
prediction目录/hash复用
空scar或空edema预测仍完成
PENDING/PLACEHOLDER/STATIC_INITIAL进入终态
短训冒充500 epoch
```

## 10. 评价

每个selected checkpoint reload后评价全部44例，且使用同一decode。至少输出：

```text
casewise_metrics.csv
subgroup_metrics.csv
help_harm.csv
training_adequacy.csv
checkpoint_selection.csv
prediction_manifest.csv
supervision_audit.csv
distillation_mechanism.csv
```

分组：

```text
positive-GT
all cases
complete-trimodal
CenterB
CenterC
LGE-only
LGE+C0
small-scar
large-scar
low-baseline
high-baseline
```

指标：

```text
Dice
HD95
precision
recall
component count
remote FP
volume ratio
empty prediction rate
changed voxels vs standard nnU-Net
```

CenterB/C是本地代理，终态不得声称已经证明CenterD泛化。

## 11. 机械决策

### Direct baseline gate

两seed平均complete-trimodal scar和edema均不低于standard nnU-Net对应子组，并至少一项提升`>=0.005`。否则主线为`NO_USABLE_SIGNAL`。

### Moddrop gate

相对direct baseline，任一病种两seed平均下降不得超过`0.002`，empty rate不得增加。

### Distillation gate

相对moddrop control：

```text
每seedscar delta >=0
每seededema delta >=0
两seed平均scar delta >=0.003
两seed平均edema delta >=0.005
或两病种平均delta >=0.005且较弱病种非负
combined help >= harm
HD95 relative worsening <=2%
empty prediction rate不增加
```

只允许终态：

```text
BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER
BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER
BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER
```

## 12. 未授权

```text
Batch8 runtime
BR2-lite
SIP
prototype/memory
proposal/refiner
source arbiter/production gate
Batch10
fold expansion
Cine
external data/pretrained weights
validation upload
hosted metric claim
route promotion
final scientific stop
```

Controller完成后必须返回Planner。