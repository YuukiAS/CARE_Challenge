# Batch 9 可靠标签蒸馏主线：深度研究复核与 Planner 决定

## 结论

Deep Research 的主判断成立：当前 Batch 8 不应继续作为最终性能主线，新的正式主线应改为**强直接分割主干 + 可靠标签监督 + 结构化模态缺失训练 + 完整三模态教师蒸馏 + 病种特异输出头**。但报告中的实现蓝图不能原样照搬，尤其不能再次用 1200–1600 optimizer steps 判断一个从头训练的强 3D 主干，也不能从少量 CenterB/CenterC 完整病例从头训练一个独立 teacher。

因此采用 **Batch 9**，而不是覆盖 Batch 8：

- Batch 8 保留为未执行的 clean-edema-BR2 诊断合同，`formal_authority=false`；
- Batch 9 成为唯一正式 Controller 入口；
- Batch 9 不复用 `SRRProposeRefineMyoPS` forward，不使用 nnU-Net anchor correction；
- Batch 9 首轮不训练 BR2-lite、SIP、prototype、memory、proposal、refiner、arbiter 或 production gate；
- representation retrieval 只保留为后续受控支线，不在本批与主线同时变化。

## Deep Research 中接受的判断

### 1. 任务形式化需要改写

官方目标是未知 CenterD 的完整三模态 scar/edema 分割。训练数据中 availability、center 和 edema 标签可靠性高度绑定：所有病例都能贡献 anatomy/scar 监督，但 edema 只能由 T2-present 且 metadata 标记为可靠的病例监督。当前问题因此是：

```text
中心绑定的模态不平衡
+ 部分可靠的 edema 标签
+ 未见中心完整三模态泛化
+ scar/edema 病种机制不同
```

它不是普通随机 missing-modality segmentation，也不能把 no-T2 病例当作 edema negative。

### 2. 应保留科学原则，不保留旧类和旧长链

继续保留：

```text
modality-specific stems
observed-modality hard masking
anatomy-first representation
scar/edema pathology-specific heads
label-reliability masking
center-balanced sampling
structured modality dropout
complete-view teacher distillation
```

退出 Batch 9 正式 forward：

```text
SRRProposeRefineMyoPS
ProposalDictionary
M10TwoPassSpatialDictionary
M10CrossFittedPrototypeMemory
prototype maps
semantic negative memory
source arbiter
branch arbitration
bounded nnU-Net correction
production gate
legacy Pattern-SIP
```

### 3. 强主干必须成为预测主体

现有 Dataset501 baseline 是 `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres`，fold0 scar/edema Dice 约为 `0.5602/0.3944`。Batch 9 使用官方 nnU-Net v2 residual-encoder M 级别结构作为直接分割主干，不使用外部预训练权重。nnU-Net anchor只作为同划分评价基线，不进入 Batch 9 forward。

## 对 Deep Research 的四项修正

### 修正一：拒绝 1200–1600 step 的欠训练预算

报告建议 teacher 1200 steps、student 1600 steps、distillation 800 steps。这个预算与仓库 500-epoch nnU-Net baseline 不可比，也会重复历史 SRR 的短训问题。

Batch 9 采用 nnU-Net epoch 语义：

```text
iterations_per_epoch: 250
student direct baseline: 500 epochs = 125000 optimizer steps
teacher complete-view fine-tune: 100 epochs = 25000 steps
student moddrop control: 100 epochs = 25000 steps
student distillation: 100 epochs = 25000 steps
```

100-step fixed overfit和小规模 forward只用于实现验收，formal training credit为0。

### 修正二：teacher 不从少量完整病例从头训练

Teacher 与 student 使用同一架构但独立参数。每个 seed 的 teacher 必须从该 seed 已完成的 direct baseline checkpoint复制初始化，再只在完整三模态、edema监督可靠的病例上 fine-tune 100 epochs。这样 teacher 是“完整视图专家”，不是只靠 B/C 小样本从零学习的第二个大模型。

Teacher 不得读取 validation GT，不得使用外部权重，不得把 center ID 作为网络输入。

### 修正三：蒸馏不能生成伪 T2 或伪 edema 标签

Distillation 只发生在**天然完整三模态且 edema 监督可靠**的训练病例上：teacher读取完整视图，student读取同一病例的结构化模态缺失视图。对自然缺失病例，只使用真实可靠的 anatomy/scar 标签；no-T2病例不接收 teacher edema伪标签、伪T2或 edema consistency。

结构化 student view：

```text
完整病例: full 0.50, LGE+C0 0.25, LGE-only 0.25
LGE+C0病例: LGE+C0 0.75, LGE-only 0.25
LGE-only病例: LGE-only 1.00
```

LGE 在本批始终保留；缺失模态 raw channel可以为零，但对应 stem 输出必须在第一层后由 availability hard-mask 精确归零，availability作为显式条件进入融合层。

### 修正四：第一轮不同时加入 refiner、BR2-lite 与 SIP

Batch 9 必须先回答 direct reliable-label distillation 是否提高完整三模态上限。首轮加入 retrieval/refiner 会再次混淆容量、监督和机制。

- scar refiner：不进入 Batch 9；
- BR2-lite：不进入 Batch 9；
- SIP：正式权重为0且不实例化；
- Batch 8 edema corrector：不进入 Batch 9。

只有 Batch 9 terminal packet经 Planner确认后，后续 Batch 才可选择一个单独机制做容量匹配对照。

## Batch 9 架构

模型：

```text
src/care_myocardium/models/care_mm_reliable_distill.py
CAREMMReliableDistillResEnc
```

数据流：

```text
[LGE,T2,C0] + availability
-> three independent 1-channel stems (8 channels each)
-> hard mask immediately after each stem
-> concatenate 24 stem channels + 3 broadcast availability channels
-> nnU-Net v2 ResidualEncoderUNet M-level encoder/decoder
-> shared high-resolution decoder feature
-> 4-class anatomy head
-> 1-channel scar residual head
-> 1-channel edema residual head
-> compose six-class logits directly
-> argmax final labels
```

六类 logits 固定定义：

```text
z0 = anatomy background
z1 = anatomy healthy myocardium
z2 = anatomy LV
z3 = anatomy RV
z4 = anatomy myocardium + edema residual
z5 = anatomy myocardium + scar residual
```

no-T2推理时 `z4=-20`。这只是缺模态安全语义；官方完整三模态评价不触发该分支。

Center只用于训练采样、监督资格和诊断分组，禁止进入网络 tensor、normalization选择、router或验证推理。

## 训练矩阵

每个 seed 依次运行：

```text
student_direct_reliable
teacher_full_view
student_moddrop_control
student_reliable_distill
```

固定 seeds：

```text
20260723
20260724
```

同 seed 的 `student_moddrop_control` 与 `student_reliable_distill` 必须从同一 direct baseline checkpoint开始，使用同一 student初始化、病例序列、patch centers、student-view masks、augmentation、optimizer和100-epoch预算。两者都执行 frozen teacher forward；唯一差异是 distillation loss权重是否非零，以避免计算路径差异冒充机制收益。

## Loss authority

Direct baseline：

```text
loss_anatomy_ce_dice = 1.0
loss_scar_bce_dice = 1.0
loss_edema_bce_dice_reliable_only = 1.0
```

Moddrop control增加：

```text
loss_moddrop_consistency = 0.1
```

Distillation在同一基础上增加：

```text
loss_distill_logits = 0.5
loss_distill_feature = 0.1
loss_distill_anatomy = 0.1
temperature = 2.0
teacher_confidence_threshold = 0.60
```

Edema segmentation与edema distillation只在T2-present且edema-supervision-reliable病例上生效。任何声明为非零的loss必须同时存在于resolved runtime contract、total loss求和和独立backward梯度矩阵。

## Sampler 与 domain robustness

每个训练 step先选监督池：

```text
50%: edema-eligible pool，中心均衡后病例均衡
50%: all-reliable anatomy/scar pool，中心均衡后病例均衡
```

不得硬编码报告中的中心数量；Executor必须从当前 metadata/split生成inventory并验证。中心不作为模型输入。

增强使用nnU-Net默认空间增强，并增加独立的每模态强度偏移、gamma、噪声和bias-field。不得加入domain adversarial、中心分类器或测试时中心选择。

## 评价与留存门

正式step使用每阶段最后checkpoint，必须reload后推理全部44例。报告：

```text
scar/edema Dice
HD95
precision/recall
component count
remote FP
volume ratio
empty prediction rate
changed voxels
positive-GT/all-case
complete-trimodal
CenterB/CenterC
LGE-only/LGE+C0
small-scar/large-scar
low-baseline/high-baseline
case-wise help/harm
```

本地complete-trimodal CenterB/C只是官方CenterD的代理，packet不得声称已证明unseen-center泛化。

继续门：

1. `student_direct_reliable` 两seed平均在complete-trimodal scar和edema均不低于当前standard nnU-Net fold0对应子组，且至少一项提高`>=0.005`；
2. `student_moddrop_control` 相对direct baseline任一病种下降不得超过`0.002`；
3. `student_reliable_distill`在两个seed上相对moddrop control的complete-trimodal scar和edema均不得为负；
4. 两seed平均distill增量：scar `>=0.003`、edema `>=0.005`，或两病种平均`>=0.005`且较弱病种非负；
5. combined help>=harm，HD95相对恶化不超过2%，empty prediction rate不增加；
6. no-T2 edema supervised voxel count必须为0。

终态只允许：

```text
BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER
BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER
BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER
```

Controller不得自行启动BR2-lite、SIP、refiner、Batch10、fold expansion、Cine或validation upload。

## 论文边界

若主方案通过，允许的故事是：

> Reliable-label distillation for partially observed multi-sequence cardiac MR segmentation：用病种特异可靠标签监督切断no-T2 edema污染，并以完整视图teacher向availability-aware direct student传递跨模态病理知识。

不得声称：

- 已因果分离center与missingness；
- 已在未知CenterD标签上证明泛化；
- 原R2/BR2/SIP理论适用于当前模型；
- prototype、memory、SIP或refiner贡献已被Batch9验证。
