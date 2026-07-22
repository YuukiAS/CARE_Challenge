# Batch 8 Planner 审计：修复 Batch 7 终态证据并做干净的 edema BR2 确认

## 结论

Batch 7 六组运行在操作层面完成，但其终态不能作为 BR2/SIP 的充分负结果：scar BR2 发生空预测塌缩；no-SIP 与 SIP 的最终预测完全相同；终态 source coefficient 文件来自新建初始模型或仍含 `PENDING_DETAILED_BETA_EXPORT`；validator 只检查文件存在和指标行数，没有检查训练后系数、空预测、SIP 实际作用和机制字段是否为数值。当前 minimal/BR2 forward 还继续使用旧 `ProposalDictionary`，因此也没有形成“普通 pathology head 对比干净 BR2”的最终实验。

用户已显式授权 Batch 8。Batch 8 不再修整张 SRR 图，只做两件事：

1. 从 Batch 7 的真实 checkpoint 修复机制证据，解释 scar 清空和 SIP 零差异；
2. 停止 scar 与 SIP/refiner 训练，只运行两个 seed 的干净 edema minimal head 与 clean BR2 head 对照。

## 图视觉读取

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_route_objective: observed-modality-only encoding -> selective shared/private/interaction retrieval -> anatomy-guided pathology proposal -> pathology-specific refinement -> bounded nnU-Net-safe output
```

Batch 8 保留其中的 observed-modality-only、病种特异 retrieval、解剖上下文和 nnU-Net 安全比较；暂不训练 SIP、refiner、source arbiter 或 production gate。

## Batch 7 终态必须被修复的证据缺口

### 1. Controller 终态越权

`controller_report.md` 仍是 `READY_FOR_CONTROLLER_VERIFICATION`，`completion_check.md` 只声明 executor scope complete，但 CURRENT/wiki 已写成 controller verified negative。Batch 8 必须明确 supersede：

```text
Batch7 operational runs: COMPLETE
Batch7 BR2/SIP scientific packet: NEEDS_EVIDENCE_REPAIR
```

### 2. 训练后系数没有导出

当前全局 `source_learner_coefficients.csv` 由静态脚本重新实例化模型后导出初始参数；病种文件仍写 `PENDING_DETAILED_BETA_EXPORT`。Batch 8 必须从 scar/edema 的 warmup50、step200、step400 checkpoint 真实加载并导出：

```text
beta_pattern
center_deviation
effective_beta
representer RMS
pathology_projection weight/bias norm
proposal-logit quantiles
predicted-positive voxel counts
SIP value and gradient norm
```

### 3. Scar BR2 空预测是塌缩，不是普通负结果

Scar BR2 no-SIP/SIP 在全部正例上 Dice 为 0。必须定位第一次清空发生在 warmup50、step200 或 step400，并报告是 proposal logits、final correction、decode 还是 checkpoint 状态导致。Batch 8 不重训 scar，只做诊断并正式冻结 nnU-Net scar。

### 4. SIP 尚未被评价

No-SIP 与 SIP 最终指标完全相同，现有 integrativeness 文件又是静态初值。Batch 8 不再训练 SIP。只有 clean BR2 在两个 seed 中通过后，Planner 才能另行授权 SIP。

### 5. 旧 ProposalDictionary 污染了 minimal/BR2 对照

Batch 7 minimal 与 BR2 均继续经过旧 `ProposalDictionary`、confirmation fusion 和遗留输出链。Batch 8 必须建立独立薄模型，不得实例化或调用：

```text
ProposalDictionary
M10TwoPassSpatialDictionary
M10CrossFittedPrototypeMemory
prototype maps / semantic negative memory
scar/edema refiner
source arbiter
branch arbitration
learned production gate
legacy Pattern-SIP
```

## Batch 8 干净模型

新增一方模型：

```text
src/care_myocardium/models/srr_batch8_clean_edema.py
class CleanEdemaBR2Corrector
```

共同冻结主干从 Batch 7 step300 checkpoint 只加载白名单：

```text
encoders
retrieval
decoders.anatomy
decoders.edema
evidence_heads 的 anatomy/union 所需权重
```

任何旧 dictionary/refiner/gate 参数不得加载、实例化或进入 forward。白名单外 checkpoint key 只记录为 ignored，不得静默进入模型。

共同数据流：

```text
[LGE,T2,C0] + availability
-> frozen modality encoders/base retrieval
-> frozen edema feature + frozen anatomy-union context
-> clean edema correction head
-> raw nnU-Net six-class logits
-> only edema channel += 2*tanh(delta)
-> six-class argmax
```

无 T2 时 `delta` 必须严格为零，最终 logits/labels 必须逐体素等于原始 nnU-Net anchor。

### Minimal

Clean head 输入仅为：

```text
frozen edema feature
T2 image
frozen anatomy-union probability
```

结构固定为：

```text
concat -> 3x3 Conv -> GroupNorm -> SiLU -> 3x3 Conv -> GroupNorm -> SiLU -> 1x1 delta
```

末层零初始化，初始输出严格恢复 nnU-Net。

### Clean BR2

在 minimal 的 edema feature 前只增加四个独立 residual representer：

```text
shared anatomy
LGE private
T2 private
LGE-T2 interaction
```

Private 只读对应模态；interaction 读取归一化 LGE/T2、逐点乘积和绝对差。每个 representer 乘 beta 前固定 per-case RMS。系数为病种特异、signed、空间全局标量，不做 softmax/simplex/top-k，不允许逐病例系数残差。

训练 source 仅为 CenterB、CenterC；训练使用 center beta，验证使用两中心 pooled tri-modal beta，center 不得进入图像网络。BR2 输出 projection 末层零初始化，初始 final logits 必须与 minimal 相同。

## Loss authority

仅允许：

```text
loss_clean_edema_final_bce_dice: 1.0
loss_clean_edema_anchor_error: 0.50
loss_clean_edema_confident_anchor_preserve: 0.10
loss_clean_br2_beta_l1: 0.001        # BR2 only
loss_clean_br2_center_deviation_l2: 0.001  # BR2 only
```

另一病种、旧 proposal、prototype、memory、refiner、arbiter、gate、bounded-correction、generic dictionary、legacy semantic/Pattern-SIP 和 SIP 全部精确为零或不存在。

## 训练与评价

固定两个 seed：

```text
20260722
20260723
```

每个 seed 独立比较：

```text
edema_clean_minimal
edema_clean_br2_no_sip
```

每组 800 optimizer steps，200/400/800 对全部 44 例评价。同 seed 两组必须共享 source checkpoint、common-head 初始化、病例序列、patch centers、optimizer、augmentation、预算、decode 和 evaluator；BR2 初始增量严格为零。

正式采样只从 T2-present、edema-supervised CenterB/CenterC 训练病例中进行：先均匀中心，再均匀病例，再选择 edema-positive 或 nnU-Net error patch。Batch size 1，patch `12x96x96`，AdamW，lr `1e-4`，weight decay `1e-4`。

## 训练前硬门

必须先完成：

1. Batch 7 真实 checkpoint 机制导出，无 `PENDING`、静态初值或新建模型替代；
2. clean model import graph/forward trace 证明旧模块调用次数为零；
3. checkpoint 白名单加载报告；
4. minimal/BR2 初始 final logits 差 `<=1e-6`；
5. no-T2 final logits/labels 与 anchor 完全一致；
6. 两个真实 T2-present病例 100-step fixed overfit，formal credit 0，loss下降至少30%，预测非空；
7. 每个正式 loss 单独 backward，冻结模块与未授权模块梯度为零；
8. save/reload final logits差 `<=1e-6`；
9. validator真实拒绝旧 ProposalDictionary进入、静态系数导出、`PENDING`字段、空预测仍标完成、no-T2 delta非零、不同seed或不同采样伪装matched。

## 保留门

Clean BR2 只有同时满足才保留：

```text
两seed BR2 positive-case Dice delta均 >= +0.002
两seed平均 BR2 positive-case Dice delta >= +0.003
两seed BR2相对minimal增量均 >= +0.0005
两seed平均 BR2相对minimal增量 >= +0.001
CenterB与CenterC两seed平均Dice delta均 >= 0
help >= harm（按两seed合并）
HD95不恶化
remote-FP相对恶化 <= 5%
no-T2 exact anchor identity
所有最终预测非空且有数值机制证据
```

若通过，终态为 `EDEMA_CLEAN_BR2_RETAIN_PENDING_PLANNER`；若未通过，终态为 `RETIRE_SRRMyoPS_PERFORMANCE_LINE_USE_NNUNET`。两者都不自动授权 SIP、refiner、fold expansion、Cine、validation upload 或 hosted claim。

## 论文边界

Batch 8 只判断轻量 BR2 是否为 edema 提供稳定增量。它不声称 R2/BR2 原理论适用于3D分割，不声称 SIP有效，不声称 scar retrieval有效，也不因一次负结果否定所有 representation retrieval 方法。