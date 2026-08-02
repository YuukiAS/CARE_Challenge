# CARE-ASE：非对称瘢痕候选形成与水肿全体积重建最终模型蓝图

**日期：2026-08-01**  
**状态：DESIGN_DRAFT_FOR_GPT_CRITIC；尚未授权执行或训练**  
**工作名：CARE-ASE — Asymmetric Scar Proposal and Edema Reconstruction**

## 0. 结论先行

CARE-ASE 不再围绕 nnU-Net 做弱残差修正，也不恢复完整 SRR dictionary、prototype、SIP、query、hard ROI 或 MyoWall 硬坐标。它采用一个完整、成熟、可从 stock nnU-Net 全权重初始化的三维编码器—解码器主干，在最高两个解码尺度分成 scar 与 pure-edema 两条非对称直接输出路径，并通过软心肌壁位置、逐切片病灶范围预测和训练期安全负空间分类，把全局病例负担与局部像素边界连接起来。

```text
LGE / T2 / C0 + availability
        ↓
完整 stock-compatible 3D encoder + shared decoder trunk
        ↓
soft anatomy / wall context
   ┌───────────────┴────────────────┐
   ↓                                ↓
scar proposal + full-res decoder    pure-edema full-volume decoder
small-lesion / negative-space       T2 injury support / extent / boundary
   └───────────────┬────────────────┘
       calibrated six-class competition
                     ↓
        background / MYO / LV / RV / edema / scar
```

Stock nnU-Net 只提供初始化、结构和成熟训练能力；推理时 final scar/edema logits 由 CARE-ASE 分支直接生成，不读取或叠加 stock class-4/class-5 logits。MoSAIC 只贡献病种专属与 scar 连续化经验，不作为 teacher、anchor、ensemble 或病例选择器。

---

## 1. 设计依据与失败经验闭环

### 1.1 当前机器真值

必须以 `origin/main` 和 `prompts/routes/handoffs/CURRENT.md` 为准。当前已确认：

- 四模型纠偏后没有本地候选；M0R scar/pure-edema 相对同病例 stock 分别约为 `-0.0020/-0.0301`；M2 为 `-0.0501/+0.0189`，且 edema harm fraction 过高。
- 220 例公平 OOF 中，nnU-Net scar/pure-edema 为约 `0.5610/0.4308`；MoSAIC clean OOF 为约 `0.3782/0.0528`。
- nnU-Net/MoSAIC case-oracle 相对 nnU-Net 的增益仅 scar `+0.0220`、pure-edema `+0.0023`，不支持病例选择器或简单概率融合。
- scar 的 MoSAIC rescue 只有 18/220；nnU-Net protects 97/220。pure edema 没有稳定 MoSAIC rescue，nnU-Net protects 45/80。

因此，最后模型不能依赖已有模型选择或组合获得大幅增益；必须改变体素级病灶形成机制。

### 1.2 每条失败路线只保留什么

| 路线 | 直接保留 | 明确删除 |
|---|---|---|
| nnU-Net | 完整 encoder/decoder、深监督、增强、直接全体积输出 | 统一六类头对 scar/edema 的对称假设 |
| MoSAIC | 病种专属 authority、scar 连续化、full-data/target-domain 训练意识 | clean/full 混写、病例级选择、MoSAIC edema、固定后处理依赖 |
| SRR | 模态角色分离、availability 显式输入、scar/edema 独立证据 | shared/private/interaction dictionary、SIP、自由 router、prototype memory |
| MMRD | no-T2 不作 edema 阴性、可靠标签 mask、缺模态 stem 后硬清零 | 弱 residual head、教师不强时的蒸馏主线 |
| Cascade / DG | FN/FP 分解、病种独立安全审计、OOF 错误图 | frozen anchor、bounded correction、训练/部署 anchor 分布错位 |
| ARC / PRISM | anchor 可突破、final-output trace、outer 一次性评价 | encoder-only inheritance、decoder reset、随机浅层病理头、模块只存在不入 final |
| MyoWall | 心肌壁深度与内外膜距离是有价值的软坐标 | hard wall transform、hard crop、几何失败即无病理输出 |
| QIF | component supervision、全体积 remote-FP 审计 | query noisy-OR、GT support 泄漏、多折 frozen feature 混合 |
| I-MMSeg pilot | 原始 LGE/T2 强度信号应保留 | CLIP/text 复杂先验、手工 rank 必须优于 raw 的假设 |

### 1.3 必须直接攻击的病例错误

- `Case3008`：CenterC edema 大部分未激活；历史 sensitivity 约 `0.0885`，预测体积约 GT 的 12%。这是全局欠激活，不是边界问题。
- `Case3009`：同中心重复出现 scar 尚可、edema 弱，证明是中心×T2 表征问题。
- `Case3027`：scar 竞争过强、edema 基本消失，固定 scar-priority 不可继续。
- `Case3012`：大范围 edema 漏检，需要全体积连续区域重建。
- `Case2034/Case2025`：edema 既可能欠分割，也可能连续过扩，需要范围与体积校准。
- `Case2019`：弱 proposal/refiner 产生远离心肌的大块病理，需要成熟全体积负空间学习。
- `Case2012`：小病灶“预测到一点”但位置错误，需要 lesion-level定位，不只是正体素召回。
- `Case2009`：MoSAIC scar 明显优于 nnU-Net，而同病例 edema 由 nnU-Net 保护；证明互补发生在病种/局部区域，不是病例层面。
- `Case1045/Case1029/Case8021`：小或细 scar 漏检；必须提高小组件召回，但不能通过全图增阳性实现。

---

## 2. 目标与非目标

### 2.1 科学目标

1. 在相同病例、相同 full-volume evaluator 下，同时超过 stock nnU-Net 的 scar 与 pure-edema。
2. scar：恢复小/细/多组件病灶，同时减少血池邻近和远端 FP。
3. edema：修复 CenterC 整体欠激活，同时不破坏 CenterB 已正确病例，不以统一扩张换 sensitivity。
4. 保留缺模态训练价值，但最终目标域适配面向完整 C0/LGE/T2 validation/test。
5. 形成一个单体端到端模型，结构与 MoSAIC、nnU-Net 都不同，不依赖推理时模型组合。

### 2.2 明确非目标

首版不实现：

```text
第二完整 backbone
nnU-Net/MoSAIC ensemble 或 selector
frozen anchor residual correction
shared/private/interaction dictionary
prototype memory / query / Transformer decoder
hard ROI crop / local-only refiner
hard wall coordinates
learned registration
CLIP/LLM prompt
center ID
synthetic T2
compactness-only / HD-only loss
CineMyoPS branch
```

---

## 3. 固定数据、标签与几何语义

```text
Dataset: Dataset501_CAREMyoPS
input order: [LGE, T2, C0]
stock patch size: [20, 256, 256]
stock spacing source: nnU-Net plans/properties
compact labels:
  0 background
  1 healthy myocardium
  2 LV cavity
  3 RV cavity
  4 pure edema
  5 scar
wall/anatomy union: labels 1|4|5
injury auxiliary: labels 4|5
scar primary: label5
pure-edema primary: label4
```

数据规则：

- scar/anatomy 可使用全部 220 例可靠标签。
- pure-edema、injury、T2 boundary 与 edema slice-extent 只在 80 个真实 T2-present 病例上监督。
- no-T2 病例的所有 edema 专属 loss、context-negative loss 与 extent loss严格为0；不得作为 edema 阴性。
- availability 由 manifest 提供，不能从零填充图像推断。
- 缺失模态在专属 adapter 输入处硬清零；原始 stock-compatible 输入可保留零占位以维持网络接口，但 availability 必须显式进入，且缺失通道不得产生专属 adapter 激活。
- center ID 只用于采样与 subgroup 报告，不进入 forward。

---

## 4. 网络总结构

### 4.1 `StockCompatibleTrunk`

实现类：

```text
src/care_myocardium/models/care_ase/stock_trunk.py
class StockCompatibleTrunk
```

要求：

1. 从对应 fold 的 `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres` checkpoint 加载完整网络。
2. encoder、bottleneck、所有 decoder stages、deep-supervision heads 的参数字节覆盖率 `>=0.99`。
3. 在 CARE-ASE 新模块全部关闭且 compatibility head 启用时，FP32 每尺度 logits 最大误差 `<=1e-6`、argmax changed voxels `=0`。
4. trunk 输出 plan-derived feature dictionary，不允许 Executor 猜通道：

```text
encoder_features: E0...EL
shared_decoder_features: Dcoarse...D0
D0: full-resolution decoder feature
stock_anatomy_logits_0_3: only for initialization/audit; not final pathology authority
```

5. 实际 stage/channel/stride 由 plans 和真实 module introspection绑定到 `architecture_receipt.json`；与 checkpoint 不一致必须 fail closed，不能自动换成较小网络。
6. 最终模型训练时完整 trunk 可训练；不得全程冻结。

### 4.2 分叉位置

- encoder 与低/中分辨率 decoder 完全共享。
- 在最高两个 decoder resolutions 分为：
  - `AnatomyContextBranch`
  - `ScarBranch`
  - `EdemaBranch`
- 每条 pathology branch 都消费原始对应 skip、shared decoder feature 和本病种 modality-role adapters。
- 不允许只在 D0 后接两层卷积冒充独立 decoder。

---

## 5. 模态角色适配器

实现：

```text
class ModalityRoleAdapterBank
class ScarModalityAdapter
class EdemaModalityAdapter
```

每个高两级尺度、每个被允许模态包含：

```text
Conv3d(1, 16, kernel_size=3, padding=1)
InstanceNorm3d(16, affine=True)
SiLU
Conv3d(16, C_l, kernel_size=1)
```

原始单模态图像按 plan spacing/resolution三线性下采样到对应尺度。最后 `1x1` 卷积零初始化，使 step0 不改变 stock-initialized病理输出。

固定角色：

```text
scar branch:
  mandatory primary: LGE adapter
  auxiliary structural: C0 adapter
  T2 adapter: forbidden in scar v1

edema branch:
  mandatory primary: T2 adapter when available
  auxiliary structural: C0 adapter
  weak context: LGE adapter with learned scalar initialized 0
```

融合不是自由 router：

```text
F_scar_l = D_l + A_lge_l + sigmoid(g_c0_l) * A_c0_l
F_edema_l = D_l + m_T2*A_t2_l + sigmoid(g_c0e_l)*A_c0_l + tanh(g_lgee_l)*A_lge_l
```

标量初始化：

```text
g_c0_l = -1.3863   # sigmoid = 0.2
g_c0e_l = -1.3863  # sigmoid = 0.2
g_lgee_l = 0       # tanh = 0
```

禁止用 center、availability pattern 或 pooled feature产生自由 top-k mixture。

---

## 6. 软解剖与软心肌壁上下文

实现：

```text
class AnatomyContextBranch
class SoftWallContextHead
```

输出：

```text
anatomy_logits_0_3
p_wall_union          # labels 1|4|5
p_lv
p_rv
signed_endo_distance
signed_epi_distance
wall_depth_rho
```

### 6.1 监督

- anatomy target：label4/5 remap为1，保留0/1/2/3。
- wall union：labels1/4/5。
- 距离 target 用真实 spacing计算 EDT，clip到 `[-10mm, +10mm]` 后除以10。
- wall depth 仅在 GT wall union 内监督：

```text
rho = d_endo / (d_endo + d_epi + 1e-6)
```

无法计算或不满足拓扑的切片只 mask distance/rho regression，不阻塞整个病例。

### 6.2 权限

- 所有 soft context 输入 pathology branch前 `detach()`，避免 pathology loss破坏 anatomy。
- 只作为通道和logit偏置；不得 hard multiply、hard crop或fail-stop。
- 推理时 anatomy错误不能令scar/edema概率强制为0。

---

## 7. ScarBranch：全图候选形成 + 高分辨率直接重建

实现：

```text
class ScarCoarseProposalHead
class ScarHighResolutionDecoder
class ScarSliceExtentHead
class ScarContextClassifier
```

### 7.1 coarse proposal

在 `1/4` 和 `1/2` 分辨率分别输出：

```text
scar_occupancy_logit
scar_center_heatmap
scar_slice_presence_logit
```

GT center heatmap：每个 26-connectivity scar component 的物理质心，使用各向异性 Gaussian；in-plane sigma 4mm，z sigma 1个切片。所有GT component保留，不删除小组件。

Proposal只作为特征与深监督，不生成bbox，不裁剪主分支。

### 7.2 high-resolution decoder

最高两个尺度每级固定：

```text
Upsample/stock decoder transition
Concat(shared decoder, stock skip, scar modality adapters,
       upsampled proposal occupancy, center heatmap,
       detached p_wall, d_endo, d_epi, rho)
Conv3d(Cin, 64, 3, padding=1)
InstanceNorm3d(64, affine=True)
SiLU
2 x ResidualBlock3d(64)
Conv3d(64, 32, 3, padding=1)
InstanceNorm3d(32, affine=True)
SiLU
```

最终 `Conv3d(32,1,1)` 直接输出 `z_scar`。最终classifier从stock class5 classifier做shape-compatible复制；不兼容部分Kaiming初始化并写receipt。

### 7.3 context classifier

训练期在D0 feature上输出四类：

```text
scar
normal myocardium
blood-pool-adjacent
remote/background
```

标签只来自GT、真实物理距离和actual-train的canonical OOF nnU-Net FP manifests。context logits不直接替代scar mask；它作为feature拼回scar final block，并通过独立CE塑造正负空间。

### 7.4 小病灶与负空间采样

Scar patch/window采样：

```text
35% GT scar component-centered
20% small scar (<1000 mm3) component-centered
20% canonical OOF scar FN / low-overlap component
15% canonical OOF remote or blood-pool-adjacent FP
10% random wall/background
```

所有hard-negative/error maps必须是该病例未被对应stock模型训练过的canonical OOF结果。不得使用当前模型in-sample错误在线刷新。

---

## 8. EdemaBranch：T2主导全体积连续区域重建

实现：

```text
class EdemaFullVolumeDecoder
class InjuryAuxiliaryHead
class EdemaSliceExtentHead
class EdemaContextClassifier
class EdemaBoundaryHead
```

### 8.1 decoder

不使用proposal bbox或局部crop。最高两个尺度固定：

```text
Concat(shared decoder, stock skip, edema modality adapters,
       detached p_wall, d_endo, d_epi, rho,
       upsampled injury auxiliary)
Conv3d(Cin,64,3,padding=1)
InstanceNorm3d(64,affine=True)
SiLU
ResidualBlock3d(64,dilation=1)
ResidualBlock3d(64,dilation=2)
ResidualBlock3d(64,dilation=4)
Conv3d(64,32,3,padding=1)
InstanceNorm3d(32,affine=True)
SiLU
```

输出：

```text
z_pure_edema
z_injury_aux       # label4|5, training/feature support only
z_edema_boundary   # normalized signed distance / boundary regression
```

pure-edema final classifier从stock class4 classifier做shape-compatible复制；injury final classifier从stock class4/5均值初始化；boundary final层零初始化。

### 8.2 监督和采样

只在T2-present病例生效：

```text
35% pure-edema positive window
20% low-volume-ratio / canonical OOF edema FN window
20% edema boundary window
15% T2-present safe FP / blood-pool-adjacent window
10% random wall/background
```

complete-case采样必须CenterB/CenterC 1:1；CenterC不足时有放回采样。no-T2病例不得进入任何edema sampler。

Edema不做component compactness，不以最大component为目标，不使用scar式高阈值proposal。

---

## 9. 逐切片病灶范围头：连接全局与局部

实现：

```text
class SliceExtentHead
```

scar与edema各一个独立head。输入为对应branch在`1/4`尺度feature，对H/W做masked average+max pooling，得到`[B,C,Z]`，再运行：

```text
Conv1d(C,64,3,padding=1)
GroupNorm(8,64)
SiLU
Conv1d(64,64,3,padding=1)
SiLU
presence_head: Conv1d(64,1,1)
area_head: Conv1d(64,1,1) + sigmoid
```

每个切片target：

```text
presence: 该切片GT病灶是否非空
area_fraction: pathology voxels / wall-union voxels
```

最终病理logit：

```text
z_scar_final = z_scar
             + 0.30 * broadcast(logit(presence_scar_z))
             + 0.20 * broadcast(logit(clamp(area_scar_z, .01, .99)))
             + 0.15 * logit(clamp(p_wall, .01, .99))

z_edema_final = z_pure_edema
              + 0.35 * broadcast(logit(presence_edema_z))
              + 0.30 * broadcast(logit(clamp(area_edema_z, .01, .99)))
              + 0.10 * logit(clamp(p_wall, .01, .99))
```

这些系数是冻结架构常数，首轮不学习、不调参。范围头不能hard清零切片。

设计目的：

- `Case3008/3009/3012`：通过存在与面积头恢复整层欠激活。
- `Case2019`：压制远端单切片异常块。
- `Case2034/2025`：面积比例约束统一扩张。
- `Case2012`：center/proposal负责位置，extent只负责范围，不把“有一点预测”误当正确定位。

---

## 10. 最终六类组合：无固定scar-priority

最终logits固定：

```text
z0,z1,z2,z3 = anatomy_logits_0_3
z4 = z_edema_final
z5 = z_scar_final
six_logits = concat(z0...z5)
final = argmax(six_logits)
```

训练同时使用最终六类DiceCE与独立binary pathology losses。

禁止：

- `scar = mask_scar; edema = mask_edema & ~scar` 的无条件覆盖。
- post-hoc per-case threshold。
- 根据outer病例选择scar或edema source。

六类竞争自然解决重叠；scar与edema的branch loss保证各自召回，final six-class loss校准竞争。

---

## 11. 精确损失

### 11.1 基础定义

```text
L_final6: six-class DiceCE
L_anatomy4: 0/1/2/3 anatomy DiceCE
L_wall: wall-union DiceBCE
L_distance: masked SmoothL1 for d_endo/d_epi/rho

L_scar_dense: binary Dice + Focal(alpha=.25,gamma=2)
L_scar_component: component-adaptive Tversky(alpha=.3,beta=.7)
L_scar_center: focal BCE on component-center heatmap
L_scar_extent: BCE(presence) + SmoothL1(area)
L_scar_context: 4-class CE

L_edema_dense: binary Dice + Focal(alpha=.35,gamma=2)
L_injury: binary Dice + BCE
L_edema_boundary: masked SmoothL1 signed distance
L_edema_extent: BCE(presence) + SmoothL1(area)
L_edema_context: 4-class CE
L_relation: mean(relu(max(p_scar,p_pure_edema)-p_injury))
```

Component weight：

```text
w_k = clip(sqrt(1000 mm3 / max(component_volume_mm3, 1)), 1, 4)
```

### 11.2 总损失

```text
L_total = 1.00 L_final6
        + 0.50 L_anatomy4
        + 0.25 L_wall
        + 0.10 L_distance
        + 1.00 L_scar_dense
        + 0.25 L_scar_component
        + 0.10 L_scar_center
        + 0.15 L_scar_extent
        + 0.10 L_scar_context
        + m_T2 * (
            1.00 L_edema_dense
          + 0.40 L_injury
          + 0.10 L_edema_boundary
          + 0.20 L_edema_extent
          + 0.10 L_edema_context
          + 0.05 L_relation
          )
```

首版禁止增加其他loss。特别禁止compactness、global HD surrogate、prototype margin、SIP、distillation。

每一项必须有：

- 非零有效样本计数；
- 直接梯度到目标模块；
- on/off intervention对对应中间输出或final labels的影响。

---

## 12. 训练日程

### 12.1 共同配置

```text
optimizer: AdamW
weight_decay: 1e-4
mixed precision: bf16 on H100/A100; fp16 only if hardware requires
physical batch: 1
accumulation: 4
effective batch: 4
gradient clip: 12
checkpoint: every 1000 optimizer steps
full-volume inner evaluation: every 2000 steps
```

### 12.2 Stage A：新分支预热，2000步

冻结：encoder、shared decoder trunk。  
训练：modality adapters、anatomy context、scar/edema high-res branches、extent、context heads。

```text
new modules lr: 5e-4
stock-compatible branch classifier lr: 2e-4
scheduler: 200-step warmup + cosine to 5e-6
```

必须完成，不能因中间Dice低而NO-RUN后续stage。

### 12.3 Stage B：渐进解冻，8000步

解冻：shared decoder全层、encoder最高两级；低级encoder保持冻结。

```text
new modules lr: 3e-4
shared decoder lr: 1e-4
upper encoder lr: 5e-5
scheduler: 500-step warmup + cosine to 1e-6
```

采样：

```text
50% complete tri-modal
25% LGE-only
25% LGE+C0
```

complete tri-modal内部CenterB/CenterC 1:1。Scar/anatomy所有可靠病例可贡献；edema只在T2-present时贡献。

### 12.4 Stage C：完整三模态目标域适配，4000步

只使用80例完整三模态；CenterB/CenterC 1:1。所有层可训练，但低级encoder lr `1e-5`。

```text
new modules lr: 1e-4
shared decoder/upper encoder lr: 5e-5
lower encoder lr: 1e-5
scheduler: cosine to 1e-6
```

目标是改善CenterC edema而保持CenterB，吸收MoSAIC full-data/target-domain成功经验，但不复制其网络。

总预算每fold固定`14000 optimizer steps`，不得缩成4000步、16epoch或单个浅层head。

---

## 13. 正式运行规模与checkpoint选择

本蓝图建议后续Controller执行：

1. fold2、fold3两个完整实现模型并行训练，各14000步。
2. checkpoint候选：Stage B的4000/6000/8000/10000步，以及Stage C的12000/14000步。
3. 只用各fold actual-train内部冻结inner selection做full-volume选择；outer不参与选择。
4. scar与edema允许选择不同step，但必须来自同一CARE-ASE模型家族；anatomy使用较晚的两个step中inner anatomy最优者。
5. fold2/fold3 outer只在checkpoint冻结后一次性评价。
6. 无论本地科学门是否通过，后续如用户授权最终full-data model，使用fold2/fold3选中step的中位数作为固定训练步数；不得根据hidden validation调整。

Checkpoint score：

```text
scar_score = scar_Dice
           - 0.002 * max(0, scar_HD95_mm - stock_HD95_mm)
           - 0.00002 * remote_FP_volume_mm3
           - 0.05 * max(0, harm_fraction - .35)

edema_score = pure_edema_Dice
            + 0.20 * sensitivity
            - 0.05 * abs(volume_ratio - 1)
            - 0.002 * max(0, HD95_mm - stock_HD95_mm)
```

只在inner使用，系数冻结。

---

## 14. 评价与promotion门

必须使用canonical physical-space evaluator：

```text
Dice
HD95 mm
exact HD mm
precision
sensitivity
lesion recall
small-lesion recall (<1000 mm3)
component count
remote FP count/volume (>10mm physical distance)
blood-pool-adjacent FP
volume ratio
case-wise help/harm (>+0.01 / <-0.01)
CenterB/CenterC
```

### 14.1 Scar门

相对同病例stock：

```text
Dice delta >= +0.015
harm fraction <= 0.35
HD95 delta <= 0
remote FP volume <= stock
small-lesion recall delta >= +0.10 OR lesion recall delta >= +0.05
Case2009 improves or remains within -0.03 of its MoSAIC-clean diagnostic result
Case2019 remote FP does not increase
Case2012 lesion localization improves, not only positive volume
```

### 14.2 Edema门

```text
pure-edema Dice delta >= +0.020
harm fraction <= 0.35
CenterC sensitivity delta >= +0.10
CenterB Dice delta >= -0.01
HD95 delta <= +1 mm
mean abs(volume_ratio-1) improves
Case3008 and Case3009 sensitivity each improve >= +0.15
Case2034 volume-ratio error improves
Case3027 does not collapse from scar competition
```

### 14.3 总终态

只允许：

```text
CARE_ASE_DUAL_PATHOLOGY_READY
CARE_ASE_SCAR_ONLY_SIGNAL
CARE_ASE_EDEMA_ONLY_SIGNAL
CARE_ASE_NO_GO_FAITHFUL_NEGATIVE
OPERATIONALLY_BLOCKED_ASSET_OR_RUNTIME
```

只有完整实现、14000步、checkpoint reload、full-volume inner/outer、物理指标和最终intervention闭合后，negative才可称科学负结果。

---

## 15. 防止Codex降级实现的不可协商约束

以下任一出现，implementation validator必须非零退出，Controller必须在同一Goal中修复，不得把`NEEDS_IMPLEMENTATION`、`NO_RUN`、`PARTIAL`当终态：

1. 只继承encoder或重置decoder。
2. 全程冻结stock trunk，只训练浅head。
3. 用两层卷积代替scar/edema最高两尺度独立decoder。
4. stock class4/5 logits进入final add、fallback或teacher authority。
5. modality adapters、soft-wall、extent、context、injury/boundary任一缺失。
6. loss只写在config/receipt而未进入`L_total`。
7. hard-negative只写字符串，没有真实mask、sampling和梯度。
8. no-T2仍进入任何edema loss或safe-negative。
9. query、prototype、dictionary、hard ROI、hard wall、scar-priority被擅自恢复。
10. patch proxy冒充full-volume评价。
11. training budget少于14000步，或因早期指标差跳过Stage B/C。
12. checkpoint不reload。
13. outer参与checkpoint、阈值、系数或source选择。
14. module-present、nonzero gradient、changed voxels冒充科学成功。
15. 未报告Case3008/3009/3027/3012/2034/2025/2019/2012/2009。
16. 只报告Dice，未报告HD95、PRE/SEN、volume ratio、remote FP、help/harm。
17. 运行波次以`PREFLIGHT_NEEDS_IMPLEMENTATION`结束，而未修复实现。
18. preflight通过后正式训练未启动，形成`NO_RUN`。
19. 将GPU排队、pending或startup failure算训练credit。
20. 将外部模型组合包装成CARE-ASE。

---

## 16. 后续Controller必须采用的No-Run任务图

本文件不授权执行，但后续Controller必须满足：

```text
W0 evidence/split/asset freeze
W1 full implementation
W2 mandatory repair-loop preflight
W3 fold2+fold3 formal 14000-step training
W4 checkpoint reload + inner selection
W5 one-time outer evaluation + interventions + atlas
W6 validator + commit/push/notify
```

规则：

- W1发现缺口必须实现，不得返回Planner。
- W2失败进入同一Goal的bounded repair loop，最多3次；不能直接结束。
- W3只依赖W2 implementation PASS，不依赖任何早期科学Dice门。
- Stage A/B/C全部强制运行；不得因前一stage结果不理想跳过。
- Formal job必须在implementation PASS后立即启动或预排；Controller不能退出等待人工继续。
- 真正允许阻塞的只有数据/checkpoint不可读、GPU/runtime客观消失、重复修复后仍无法完成真实forward/backward。

---

## 17. 多轮自审结论

### 审查一：是否再次围绕anchor打转？

否。只复制权重和完整能力；final pathology由新分支直接产生，不受bounded residual限制。

### 审查二：是否再次重建decoder而丢能力？

否。完整stock encoder/decoder保留；病种分叉只发生在最高两个尺度，且从stock兼容classifier初始化。

### 审查三：是否把scar/edema当同一任务？

否。scar有coarse proposal、component center和强负空间；edema有T2全体积decoder、injury辅助、extent和boundary，不做scar式ROI。

### 审查四：是否再次依赖脆弱前置条件？

否。soft-wall不是hard gate；proposal不裁剪；extent不hard清零；无单个模块失败会让整条病理路径失效。

### 审查五：是否再次用复杂模块代替真实信息？

否。没有dictionary/prototype/query/CLIP。新信息只有原始LGE/T2、成熟多尺度feature、GT派生的软位置监督和OOF真实错误采样。

### 审查六：是否可能重复A0-A3的全体积FP爆炸？

显著降低风险：proposal不直接noisy-OR；scar同时学习normal/blood-pool/remote context；最终使用六类竞争；评价与选择含remote FP和harm。

### 审查七：是否可能重复M0R完整三模态微调伤害？

目标域适配仅为Stage C；前两阶段利用全部可靠scar/anatomy病例并保持低学习率分层解冻，且每个checkpoint full-volume inner选择。

### 审查八：是否有全局—局部连接？

有。slice presence/area负责病例沿z范围和负担，dense decoder负责局部边界，scar center负责位置；三者分工明确。

### 审查九：是否能讲成一个完整方法故事？

可以：成熟全体积表示保证空间重建；模态角色适配提供病种证据；非对称scar/edema解码对应不同病灶统计；软心肌壁位置提供解剖坐标；slice extent连接全局负担与局部mask；安全负空间约束远端错误。

### 审查十：最大剩余风险

- 14k步仍可能不足以重新校准复杂分支；通过stock初始化、低学习率和Stage A/B/C降低风险。
- CenterC仅45例，edema泛化仍可能不稳；通过CenterB/C平衡和complete-case Stage C处理。
- 多损失可能相互拉扯；已冻结为少量低权重辅助项，禁止执行期新增。
- soft-wall距离target在异常拓扑切片不可用；采用masked regression，不阻断病例。
- slice extent可能过度平滑极小scar；它只提供0.30/0.20软偏置，center/dense路径仍保留。

---

## 18. 证据来源索引

执行或审查前必须读取：

```text
prompts/routes/handoffs/CURRENT.md
wiki/README.md
results/20260801_care_nnunet_mosaic_complementarity_closure/**
results/20260801_care_four_lane_evidence_reconciliation/**
results/20260730_care_failure_forensics_deep_research_packet/**
results/20260731_care_myopath_a0_a3_full_volume_closure/**
results/20260731_care_myowall_geometry_diagnostic_closure/**
results/20260731_care_qif_v2_signal_audit/**
results/experiments/MyoPS-Net_iteration_log.md
docs/presentation/20260801/presentation-final.pdf
```

视觉材料：

```text
SRR-v2
SRR-v2.5
SRR-v3
CARE-MMRD
CARE-SRR-Cascade
CARE-DG
CARE-ARC
CARE-PRISM
CARE-MyoWall-IF
MoSAIC
V4 hard-case atlas
```

本蓝图是最后模型设计草案，不自动授权训练、validation、Docker或hosted claim。