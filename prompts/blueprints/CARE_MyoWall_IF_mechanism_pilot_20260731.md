# CARE-MyoWall-IF：心肌壁坐标病理场机制试验蓝图

## 一、规划结论

本蓝图批准的不是完整新模型长训练，而是一轮具有明确因果对照的机制试验。首要问题是：在完全保留成熟 nnU-Net 编码器和解码器能力的前提下，将病理输出从笛卡尔全图体素分类改写为心肌壁坐标场，是否能直接改善小 scar、多连通 scar、远端假阳性以及 T2-present pure edema 的带状边界。

Deep Research 提出的方向具有研究可行性，但原报告不能原样执行，必须修正三处关键假设：

1. 当前 nnU-Net `3d_fullres` 的真实 patch size 是 `[20,256,256]`，CARE 体积深度约为 9–32 个切片，不是报告假定的固定 `[112,160,160]`。本试验因此使用可变 `Z` 的 patch/volume wall lattice，不固定 112 层。
2. 第一轮不得同时训练 anatomy/SDF、坐标层和病理场。坐标几何由完整同折 stock nnU-Net 的冻结解剖预测确定性构建，从而单独检验“工作空间改变”而不是混合检验新的 anatomy decoder。
3. “隐式场”在本试验中指心肌壁坐标上的连续 scar SDF/occupancy field 与 edema low-frequency field，不引入第二套完整 INR、扩散模型或 U-Net。

本试验只允许一个完整 backbone。nnU-Net 提供完整 encoder、decoder、解剖概率和高分辨率 decoder feature；最终 scar/pure-edema logits 由 CARE-MyoWall-IF 自有病理场产生，stock nnU-Net 或 MoSAIC 的病理 logits 不参与加权融合。

## 二、外部研究依据与边界

- PolarNet（MICCAI 2025）证明将 LGE scar 转换到极坐标并显式建模边界具有可行性，且在其数据上超过 nnU-Net；但公开评审同时指出增益总体有限，因此该论文只支持“坐标变换值得做机制试验”，不支持预先承诺大幅增益。
- Neural Implicit Heart Coordinates（Medical Image Analysis 2026）证明标准化心脏坐标可在大规模心脏形态数据上稳定构建；其任务是解剖重建而非病理分割，因此不能作为 CARE Dice 增益证据。
- I-MMSeg（Medical Image Analysis 2026）证明模态特异的强度顺序和边界强度先验可改善多模态心肌病理分割；本试验只借鉴确定性的 LGE/T2 心肌内 robust-rank 信号，不引入 CLIP、GPT 或第二视觉 backbone。

本试验不复制任何外部代码或权重，只实现可由本地数据和 PyTorch 原生算子表达的坐标、采样和病理场机制。

## 三、冻结数据与评价边界

### 3.1 标签

```text
scar: internal label 5
official pure edema: internal label 4，仅真实 T2-present 病例
internal edema-zone: label 4|5，仅诊断，不得冒充 official edema
myocardium union: label 1|4|5
LV cavity: label 2
RV cavity: label 3
```

no-T2 病例：

```text
参与 anatomy 与 scar 训练
不参与 pure-edema loss、negative mining、Dice、HD95 或 threshold selection
pure-edema final logit 恒为 -16
pure-edema positive voxel 恒为 0
```

### 3.2 Pilot split

使用 `splits_MyoPS.json` 中 **fold1 train** 的 176 例，fold1 outer 完全不读取。

在任何训练前，从 fold1 train 确定性生成 32 例 `pilot_inner`：

- 16 例真实 T2-present complete tri-modal；
- 8 例 LGE-only；
- 8 例 LGE+C0；
- 在每种模态组内按 center、scar burden quartile、scar component-count bin、pure-edema burden quartile（仅 T2-present）分层；
- 每个 stratum 内按 `SHA256("CARE_MyoWall_IF_20260731:" + case_id)` 升序选取；
- 若分层配额不足，按相同 hash 从该模态组剩余病例补足；
- `pilot_train = fold1 train - pilot_inner`，预计 144 例。

必须在训练前写出并哈希：

```text
pilot_train_cases.txt
pilot_inner_cases.txt
pilot_split_receipt.json
```

该 pilot 是机制诊断。完整 stock fold1 backbone 曾见过 fold1 train 病例，因此结果不得称为 clean OOF、outer 或 hosted 泛化证据。

### 3.3 指标真值依赖

正式训练前必须读取：

```text
results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json
```

并满足：

```text
metric_contract_status: PASS
canonical_t2_present_count: 80
```

如果该结果尚未完成，允许先实现、完成几何缓存和 zero-credit smoke，但不得启动正式 matched-arm 训练。

## 四、完整 backbone 与特征接口

### 4.1 主干

精确资产：

```text
Dataset501_CAREMyoPS
configuration: 3d_fullres
network: nnUNetPlans 对应 PlainConvUNet
fold: 1
input order: [LGE,T2,C0]
patch size: 从 nnUNetPlans 运行时读取，预期 [20,256,256]
```

完整加载 fold1 `checkpoint_final.pth`：

- encoder、bottleneck、decoder、segmentation heads 全部 shape-matched 加载；
- 参数字节覆盖率 `>=0.99`；
- stock forward 的 FP32 logits parity `max_abs_error <= 1e-6`；
- 禁止只继承 encoder；
- 禁止 decoder reset；
- pilot 所有 arm 中 backbone 与 decoder 全冻结并使用 `torch.no_grad()`。

### 4.2 高分辨率 decoder feature

通过只读 forward hook 获取：

```text
network.decoder.stages[-1]
```

期望输出：

```text
F0: B x 32 x Z x 256 x 256
```

如果实际模块路径或通道与 `nnUNetPlans` 不一致，必须 fail closed；不得随意选择“相近层”。

### 4.3 冻结解剖概率

stock 六类 logits 经 softmax 得到：

```text
P_LV = P(label 2)
P_wall = P(label 1)+P(label 4)+P(label 5)
P_RV = P(label 3)
```

这些概率只提供坐标和最终 anatomy composition；stock label4/5 pathology logits 不进入 CARE-MyoWall-IF final pathology logits。

## 五、确定性几何缓存

类名：

```text
FrozenStockGeometryCacheBuilder
WallCoordinateTransform
WallInverseTransform
```

### 5.1 每切片几何

对每个 preprocessed case 和每个 short-axis slice：

1. 从 `P_LV >= 0.35` 与 stock argmax label2 的并集获取 LV cavity，保留最大连通域；
2. 从 `P_wall >= 0.30` 与 stock argmax in `{1,4,5}` 的并集获取 wall，保留包围 LV 的主要环状组件；
3. LV 质心使用物理坐标下的 connected-component centroid；
4. 对质心沿 z 使用长度 3 的 median smoothing；
5. 对缺失质心的相邻最多 2 个切片作线性插值；超过 2 个连续无效切片则标记 geometry invalid；
6. 在 `A=256` 个角度上，从质心沿半径采样 `P_LV/P_wall`；
7. endocardial radius 为离开 LV 后进入 wall 的第一次稳定 crossing；
8. epicardial radius 为同一径向连续 wall 区间的最后 crossing；
9. 合法壁厚为 `1.5 mm <= r_epi-r_endo <= 25 mm`；
10. 角度首尾使用 circular smoothing，不允许普通 zero padding。

### 5.2 壁网格

径向网格：

```text
R=32
rho in [-0.15,1.15]
interior wall: 0 <= rho <= 1
inner/outer guard bands: rho<0 or rho>1
```

z 维保持当前 patch/volume 的真实切片数，不固定为 112。训练 patch 读取对应 z 区间的全病例 geometry cache；当病例深度小于 patch depth 时沿用 nnU-Net padding mask，不将 padding 计入 loss。

壁网格特征由 `grid_sample` 双线性/三线性采样；label target 使用 nearest sampling；inverse transform 使用同一 centroid/radii 和 trilinear accumulation，重叠 patch 以 Gaussian importance weighting 聚合。

### 5.3 几何门

每个病例记录：

```text
valid_angle_fraction
valid_slice_fraction
wall_roundtrip_dice
wall_roundtrip_hd95_mm
centroid_jump_mm
interpolated_slice_count
```

pilot 进入正式训练的几何门：

```text
case geometry valid rate >= 0.95
median wall roundtrip Dice >= 0.96
5th-percentile wall roundtrip Dice >= 0.90
median roundtrip HD95 <= 2.0 mm
```

若 geometry-invalid 病例超过 5%，停止 wall-field 路线，不得由 Cartesian fallback 掩盖。

## 六、输入特征包

所有 arm 使用同一 `F0` 与同一确定性信号。

### 6.1 Robust rank

在 stock 预测 wall 支持内逐病例逐切片计算：

```text
LGE_rank = empirical CDF rank after 1st/99th percentile clipping
T2_rank = same, only when T2 present
LGE_highfreq = robust-zscore(LGE - GaussianBlur3D(sigma=(0,1.5,1.5)))
```

wall 外置零。无 T2 时 `T2_rank=0` 且 availability bit 为 0。

### 6.2 统一 48 通道输入

所有 arm 构造固定 48 通道 feature pack：

```text
32: F0
1: LGE_rank
1: T2_rank
1: LGE_highfreq
1: P_wall
1: P_LV
2: availability bits [a_T2,a_C0]
8: positional channels
2: zero-reserved channels
```

Cartesian positional channels：

```text
z_norm,x_norm,y_norm,r_norm,
sin(pi*x),cos(pi*x),sin(pi*y),cos(pi*y)
```

Wall positional channels：

```text
z_norm,rho,
sin(theta),cos(theta),
sin(2theta),cos(2theta),
sin(4theta),cos(4theta)
```

两个 arm 输入通道、第一层宽度和可训练参数量必须匹配到 `±5%`。

## 七、四个 matched arms

### Arm C0：Cartesian matched control

类名：

```text
CartesianMatchedPathologyHead
```

scar 与 edema 使用独立参数，不共享最后病理头。

Scar head：

```text
48 -> 64 -> 64 -> 32 -> 2
kernels: (3,5,3),(3,3,3),(3,3,3),1x1x1
outputs: scar occupancy logit, scar SDF
```

Edema head：

```text
surface branch: 48->48->48->24, kernels (3,9,3),(3,7,3),(3,5,3)
radial/local branch: 48->24->1, kernels (1,1,5),(1,1,3)
outputs: edema occupancy logit, edema boundary auxiliary
```

Cartesian head读取相同 anatomy probabilities、rank 和坐标信号，但不做 wall transform。

### Arm W1：完整 wall-coordinate field

类名：

```text
ScarWallFieldHead
EdemaWallFieldHead
```

Scar：

```text
48 -> 64 -> 64 -> 32
kernels (z,theta,rho): (3,5,3),(3,3,3),(3,3,3)
theta circular padding
outputs: scar occupancy logit + sampled Cartesian SDF auxiliary
```

Edema：

```text
surface branch u(z,theta): 48->48->48->24->1
kernels: (3,9,1),(3,7,1),(3,5,1),1x1x1
radial branch r(z,theta,rho): 48->24->1
kernels: (1,1,5),(1,1,3)
logit_e = u + r
```

W1 使用完整 component/guard/rank losses。

### Arm W2：wall field 去除 component/guard loss

结构与 W1 完全相同、初始化 seed 相同；只关闭：

```text
L_component_tversky
L_component_MIL
L_guard_negative
```

用于判断收益是否仅来自 loss recipe。

### Arm W3：wall field 去除 intensity-rank signals

结构和 losses 与 W1 相同，但将：

```text
LGE_rank=0
T2_rank=0
LGE_highfreq=0
```

availability、F0、P_wall、P_LV 和坐标仍保留。用于判断强度先验是否提供新的病理信息。

## 八、最终预测权限

所有 arm 均不使用 stock pathology logits。

Cartesian arm：

```text
scar_logit = C0_scar(x)
edema_logit = a_T2*C0_edema(x)+(1-a_T2)*(-16)
```

Wall arms：

```text
scar_logit(x) = inverse_wall(W_scar)(x) inside expanded wall support; outside = -16
edema_logit(x) = a_T2*inverse_wall(W_edema)(x) inside expanded wall support; otherwise = -16
```

expanded wall support 仅允许在 predicted endo/epi 两侧各扩张 `2 mm`，避免轻微 anatomy 边界误差；超过该范围的病理 logit 恒为 -16。

最终六类组合：

1. LV/RV 由 stock anatomy argmax 保留；
2. 在 wall 支持内先产生 scar；
3. 非 scar 且 T2-present 的 wall 位置产生 pure edema；
4. 剩余 wall 为 healthy myocardium；
5. scar priority 固定；
6. 不做最小组件删除、TTA、ensemble 或 validation-driven post-processing。

## 九、监督与损失

### 9.1 Scar

```text
L_scar = 1.0*DiceCE
       + 0.40*SmoothL1(sampled_Cartesian_SDF)
       + 0.25*ComponentBalancedTversky
       + 0.20*ComponentMIL
       + 0.15*GuardBandNegative
       + 0.05*ThetaSeamConsistency
```

- `ComponentBalancedTversky`：每个 GT scar connected component 单独计算 Tversky 后取等权均值；component bbox 物理扩张 3 mm。
- `ComponentMIL`：每个 GT component 的 2 mm 膨胀区域内，至少一个预测概率达到高值；实现为 `mean_j -log(max(p in dilate(C_j))+eps)`。
- `GuardBandNegative`：rho<0 与 rho>1 的 guard samples、血池和预测 wall 外 LGE 高亮点为负类；不得使用 no-T2 myocardium 作为 edema negative。
- SDF 从 Cartesian GT 按物理 spacing 计算，再采样到 wall grid，截断到 `[-8,8] mm`。

### 9.2 Pure edema

仅 T2-present：

```text
L_edema = 1.0*DiceCE
         + 0.35*BoundaryLoss
         + 0.15*EdgePreservingTV(z,theta)
         + 0.20*RankContrast
         + 0.10*GuardBandNegative
```

- `RankContrast`：在真实 T2-present 病例内，使 edema 的 T2_rank 高于安全正常 myocardium；安全负类必须有真实 T2。
- `EdgePreservingTV` 只沿 z/theta 平滑，GT boundary 邻域权重降低，不沿 rho 强制整层平滑。
- no-T2 时所有 edema loss、negative、gradient、metric 分母均为零。

### 9.3 Anatomy

pilot backbone 与 anatomy 预测完全冻结，不训练新 anatomy loss。

## 十、训练合同

四个 arm 使用：

```text
same pilot_train/inner
same case order
same patch descriptors
same augmentation seed
same optimizer
same 8000 optimizer steps
same validation cadence
same checkpoint selection formula
same decode
```

在训练前生成并哈希 8000-step `batch_descriptor_manifest.jsonl`，每条包含：

```text
step
case_ids
z crop
foreground target
augmentation seed
T2 availability
```

四 arm 逐条重放，禁止各自随机采样。

统一优化：

```text
backbone/decoder: frozen, no_grad
optimizer: AdamW
new-module lr: 3e-4
weight_decay: 1e-4
physical batch size: 2
grad accumulation: 2
effective batch size: 4
warmup: 500 steps
scheduler: cosine decay to 1e-6
grad clip: 12
AMP: bf16 on H100/A100, otherwise fp16
checkpoint every: 1000 steps
fixed evaluation every: 1000 steps
```

四个 arm 均从独立相同 seed 初始化，不从其他 arm 续接。

## 十一、评价与选择

只使用 `pilot_inner`。fold1 outer 不读取。

每个 checkpoint 重载后评价，禁止直接使用训练内存模型。

Scar：

```text
Dice
HD95 mm
exact HD mm
precision/recall
lesion-wise recall
small-lesion recall
multi-component case recall
predicted/GT component count
remote-FP component/volume
blood-pool FP volume
volume ratio
case-wise help/harm vs C0
```

Pure edema，T2-present only：

```text
Dice
HD95 mm
exact HD mm
precision/recall
boundary surface Dice
component count
blood-pool/guard FP
volume ratio
case-wise help/harm vs C0
```

No-T2：

```text
max edema probability <= 1.2e-7
edema positive voxels = 0
edema loss = 0
edema gradient = 0
```

统一 checkpoint score：

```text
S = 0.30*scar_Dice
  + 0.25*edema_Dice_T2
  + 0.15*small_scar_recall
  + 0.10*multi_component_recall
  - 0.08*normalized_scar_HD95
  - 0.07*normalized_edema_HD95
  - 0.05*normalized_remote_FP
```

存在 no-T2 violation、geometry-invalid rate>5%、参数超预算、推理>1.8x stock 或 checkpoint reload mismatch 时直接失格。

## 十二、继续与停止门

### Geometry gate

必须全部通过：

```text
geometry valid cases >=95%
median roundtrip Dice >=0.96
5th percentile roundtrip Dice >=0.90
median roundtrip HD95 <=2.0 mm
```

失败：停止训练四 arm，返回 `STOP_GEOMETRY_NOT_RELIABLE`。

### Wall-field primary gate：W1 vs C0

Scar 必须同时满足：

```text
final Dice >= C0 +0.015
small-lesion recall >= C0 +0.10
multi-component recall >= C0 +0.08
remote-FP volume <=0.75*C0
HD95 not worse by >0.5 mm
catastrophic harm (Dice drop>0.10) <=10% cases
```

Pure edema 必须满足以下二选一，同时无明显伤害：

```text
Dice >= C0 +0.015
OR HD95 improves >=2.0 mm and recall improves >=0.05
```

并要求：

```text
edema harm fraction <=35%
no-T2 exact zero
```

双病种均通过才允许 `PILOT_PASS_DUAL_PATHOLOGY`。只有一个通过则为 `PARTIAL_SIGNAL_NO_PROMOTION`，不得进入完整训练。

### Causal interpretation

- W1 优于 C0，且 W2 明显退化：component/guard loss 有独立贡献；
- W1 优于 C0，且 W3 明显退化：rank/high-frequency 输入有独立贡献；
- W1 与 C0 相当：坐标场未形成新上限；
- W1 只降低 remote FP、Dice/recall 不升：收益只是 anatomy hard support，判定不通过；
- W1 的中间 wall metrics 改善但 inverse final labels 不改善：判定不通过。

## 十三、复杂度门

必须实测：

```text
new parameters <= 0.50 * stock backbone parameters
peak GPU memory
training step time
full-case inference time
wall transform time
inverse transform time
```

W1 inference time必须 `<=1.8x` stock nnU-Net；超出即停止，不允许缩小 stock backbone 或减少病例来达标。

## 十四、实现类与禁止留白

必须使用以下类名和职责：

```text
StockNNUNetFeatureAdapter
FrozenStockGeometryCacheBuilder
WallCoordinateTransform
WallInverseTransform
RobustWallRankFeatures
CartesianMatchedPathologyHead
ScarWallFieldHead
EdemaWallFieldHead
MyoWallPilotModel
MyoWallPilotLoss
MyoWallPilotEvaluator
```

不得使用：

```text
TBD
optional
if needed
choose suitable
Codex decide
controller decide
```

不得用普通 Conv3d head 冒充 wall transform，不得只写模块名而无真实 grid/inverse-grid 计算。

## 十五、known-bad

validator 必须拒绝：

1. stock decoder 未完整加载；
2. decoder reset；
3. 选择错误 decoder feature 层；
4. 固定假设 Z=112；
5. wall transform 未使用真实 centroid/endo/epi；
6. 训练使用 GT geometry、推理使用 predicted geometry；
7. wall arm 与 Cartesian control 参数或采样不匹配；
8. scar/edema 共享形成头；
9. no-T2 进入 edema loss/negative；
10. stock pathology logits参与最终融合；
11. wall output不进入 final logits；
12. 只验证 gradient/nonzero delta；
13. 使用 outer 调参；
14. full-data/train-on-case冒充 clean；
15. geometry failure被大量 fallback掩盖；
16. remote FP 改善完全来自事后组件删除；
17. 训练 arm 使用不同 batch/augmentation；
18. checkpoint 未重载；
19. pending/running interactive step冒充完成；
20. pilot失败后自动进入完整训练。

## 十六、最终决策

本蓝图只允许：

```text
PILOT_PASS_DUAL_PATHOLOGY
PARTIAL_SIGNAL_NO_PROMOTION
STOP_GEOMETRY_NOT_RELIABLE
STOP_WALL_FIELD_NO_GAIN
OPERATIONALLY_BLOCKED
```

即使 `PILOT_PASS_DUAL_PATHOLOGY`，也只返回 Planner；不授权 fold expansion、outer、validation、Docker 或完整 48k-step 训练。
