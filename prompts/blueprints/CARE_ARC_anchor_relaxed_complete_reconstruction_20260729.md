# CARE-ARC：摆脱锚点约束的双病理完整重建

**全称：** CARE-ARC: Anchor-Relaxed Complete Reconstruction for Myocardial Scar and Edema Segmentation  
**日期：** 2026-07-29  
**状态：** PLANNED_AWAITING_CONTROLLER  
**开发主线：** `main`  
**工作树：** `/users/a/e/aereinh/CARE`  
**唯一 GPU allocation：** `61220581` (`htzhulab`, `g1807htzh01`, H100 NVL)  

## 1. 为什么必须离开 DG / DPR 主线

当前证据已经足够说明，继续围绕 nnU-Net 做有界病理修正不会产生 leaderboard 级跃升。

- CARE-DG 的最佳本地版本只在 nnU-Net 周围做小幅修改；提交到 hidden validation 后 scar Dice 为 `0.6211`、HD 为 `15.1513`，略高于现有 nnU-Net，但仍明显低于 MoSAIC 的 `0.6965 / 13.7827`。
- hidden validation 的逐病例图像比较显示，CARE probe 的 scar 和 edema 几乎始终更接近 nnU-Net；MoSAIC 则倾向于预测更完整、更连续、更高召回的病灶。
- DPR Gate B-R1 修复了候选级训练/推理错位，但 complete16 三项 Dice 仍全部略低于 nnU-Net。
- DPR Gate B-R2 接受更多 full-volume candidates 后，部分 inner grid 的最佳平均 Dice delta 仍约为 `-0.0319`，并同时触发 Dice、HD95、remote FP 和 help/harm 失败。该结果说明问题不是再调一个 utility threshold，而是“局部候选修补”本身无法稳定重建完整病灶。

新的科学假设是：

> scar 和 edema 应由 CARE 主体从原始多序列证据直接重建完整病灶；nnU-Net 只提供解剖上下文、初始化和灾难性回退，不再定义病理输出的邻域。

## 2. 文献启发及采用边界

本设计只吸收可解释、可在一个 backbone 内实现的思想，不复制复杂系统。

1. **MyoPS-Net**（Medical Image Analysis 84, 102694）证明了多序列特征融合、独立病理输出分支、myocardium consistency 和 scar/edema inclusiveness 适合 MyoPS。CARE-ARC 采用独立 scar/edema 解码器与软解剖关系，但不使用硬裁剪。
2. **Aligning Multi-Sequence CMR Towards Fully Automated Myocardial Pathology Segmentation**（arXiv:2302.03537）指出临床多序列 CMR 存在呼吸和局部错位。CARE-ARC 只加入一个轻量、置信度控制的局部特征对齐层，不引入第二个 registration backbone。
3. **AWSnet**（arXiv:2201.05344）和 MyoPS 的两阶段 EfficientSeg 工作支持“整体定位后直接重建病理”，而不是围绕现有 mask 做 residual。CARE-ARC 将 coarse extent 和 full-resolution reconstruction 放在同一网络中。
4. **Modeling Aleatoric Uncertainty in Cardiac MRI Segmentation: Probabilistic Detection and Contour Regression**（IEEE TMI, 2026, DOI: 10.1109/TMI.2026.3702822）将 detection uncertainty 与 contour uncertainty 分开。CARE-ARC 对每个病理分别预测存在性和轮廓距离/不确定性，避免用一个 component utility 同时承担“是否存在”和“边界是否正确”。
5. MyoPS benchmark 与后续 coarse-to-fine 研究表明，直接完整分割、解剖先验和病理特异 refinement 能达到或超过早期 challenge 方法；这类模型结构比继续加大 residual correction 更符合 hidden validation 暴露出的高召回、完整组件需求。

## 3. 必须继承的历史成功经验

### 3.1 来自 CARE-MMRD

保留：

- modality-specific stems；
- availability mask；
- 只对可靠标签监督；
- structured modality dropout；
- no-T2 edema 不作为阴性标签。

删除：

- 完整 teacher/backbone；
- 弱 standalone segmentation trunk；
- 任何把缺失 T2 当作 edema negative 的路径。

### 3.2 来自 Batch7 / SRR

保留：

- scar 和 edema 的病理特异证据选择；
- anatomy-guided coarse proposal；
- scar 小结构高分辨率 refinement；
- edema 大范围上下文 refinement；
- negative-space / hard-negative supervision。

删除：

- dictionary、prototype memory、router、多 expert；
- proposal 直接全图写回；
- 依赖局部候选覆盖才能看见完整病灶的设计。

### 3.3 来自 Cascade

保留：

- 强解剖先验；
- scar 与 edema 分别做安全审计；
- no-T2 exact safety；
- 非病理标签可使用稳定 nnU-Net 输出。

删除：

- 多个 frozen source backbone；
- pathology logits 的 bounded residual composition；
- 任何使最终病理 mask 必须贴近 nnU-Net 的 fallback 常态化。

## 4. CARE-ARC 网络结构

整个模型只有一个主干。

```text
[LGE, T2, C0] + availability
    -> modality-specific residual stems
    -> lightweight LGE-reference feature alignment
    -> one shared CARE ResEncM-style encoder
         |-> internal anatomy decoder
         |-> scar evidence gate -> scar coarse extent -> scar direct reconstruction
         |-> edema evidence gate -> edema coarse extent -> edema direct reconstruction
    -> pathology-specific detection / contour calibration
    -> direct scar mask + direct edema-zone mask
    -> scar priority; pure edema = edema-zone minus scar
```

### 4.1 输入

正式输入：

- LGE、T2、C0；
- availability mask；
- nnU-Net 的 anatomy probabilities：background、myocardium、LV、RV；
- nnU-Net entropy / uncertainty；
- myocardium distance map。

**禁止将 nnU-Net scar 或 edema probability 作为主病理解码器的必要输入。** 若为了 control 记录这些通道，只能 detach 后进入 audit，不得进入 CARE-ARC direct pathology logits。

### 4.2 单一强主干

- 一个 CARE-owned ResEncM-style encoder；
- 三个 modality-specific residual stems；
- deeper encoder blocks允许从同一 fold 的 Dataset501 nnU-Net encoder做 shape-compatible 初始化；
- 第一层和所有 CARE-specific modules由 CARE 自己训练；
- fold1 clean gate只能使用不含 fold1 outer cases 的 fold1 nnU-Net encoder初始化；
- 不允许载入 fold0 DPR/MMRD checkpoint污染 clean fold1。

这满足“可利用 nnU-Net 作为 backbone”，但最终病理输出由 CARE-ARC 直接解码器生成，不是 nnU-Net 的 residual。

### 4.3 轻量跨序列对齐

在 `1/4` 分辨率进行一次 LGE-reference alignment：

- C0 和 T2 各预测一个二维局部 offset field；
- offset 限制为每轴 `[-4, 4]` 像素；
- 同时预测 alignment confidence；
- 输出为 `confidence * warped_feature + (1-confidence) * original_feature`；
- identity 初始化；
- 不建立独立 registration encoder，不预测全分辨率形变，不做复杂 SyN/velocity 模型。

必须报告 offset magnitude、confidence、identity-vs-aligned feature parity 和病例级帮助/伤害。

### 4.4 病理特异证据门

每个尺度有两个轻量 evidence gates：

- scar gate：LGE 为主要证据，C0/T2 为上下文；
- edema gate：T2 为主要证据，LGE/C0 为上下文；
- gate读取 availability 和全局池化特征；
- gate只做同一 encoder 内的通道重权，不创建 expert backbone。

### 4.5 内部 anatomy decoder

内部 anatomy decoder预测 myocardium、LV、RV，用于：

- direct pathology support；
- feature alignment监督；
- soft anatomical relation；
- 防止模型只复制外部 nnU-Net anatomy context。

最终非病理标签仍可来自五折 nnU-Net；内部 anatomy head是 CARE 的训练约束和病理定位源。

### 4.6 Scar direct reconstruction branch

输出：

1. `scar_extent_coarse`：`1/4`分辨率完整 scar extent；
2. `scar_logit_direct`：全分辨率直接 scar mask；
3. `scar_presence_logit`：逐切片/逐病例 lesion objectness；
4. `scar_sdf_mean` 与 `scar_sdf_logvar`：截断 signed-distance contour regression及轮廓不确定性。

结构：

- 使用高分辨率 LGE skip；
- 两级 coarse-to-fine decoder；
- 不输入 nnU-Net scar logits；
- 不构建 ADD/REVISE candidates；
- 不使用 component utility。

### 4.7 Edema-zone direct reconstruction branch

输出与 scar 对称：

1. `edema_extent_coarse`；
2. `edema_zone_logit_direct`；
3. `edema_presence_logit`；
4. `edema_sdf_mean` 与 `edema_sdf_logvar`。

差异只允许是：

- T2 主导；
- 更大的有效感受野，使用两层 dilated residual blocks；
- 只在 T2-present reliable cases监督；
- no-T2 时所有 edema direct outputs、loss和gradient为零。

Scar 和 edema 的 decoder 参数独立，训练采样和总损失权重对称。

## 5. 最终输出规则

### 5.1 三模态病例

三模态病例必须使用 CARE direct pathology masks：

```text
edema-zone direct mask
-> scar direct mask overwrite
-> pure edema = edema-zone minus scar
```

不得因为 CARE mask与 nnU-Net不同而自动回退。

允许的灾难性回退仅限：

- non-finite output；
- shape/grid mismatch；
- anatomy support为空；
- required model asset/hash不匹配。

### 5.2 No-T2病例

- scar仍由 CARE direct branch输出；
- edema branch全路径为零；
- pure-edema可精确回退 nnU-Net anchor；
- no-T2病例不贡献任何 edema loss。

### 5.3 空病灶防护

为避免 Case1014 类“模型认为有病灶但最终完全空”的情况：

- 若 pathology presence probability `>=0.70`，但正式阈值下 direct mask为空；
- 只允许使用该 CARE branch 自身的 coarse extent和较低一级预注册阈值恢复一个 CARE component；
- 禁止用 nnU-Net pathology mask填回三模态病例。

### 5.4 轻量确定性后处理

只允许：

- soft myocardium band外完全孤立的component删除；
- 3 mm以内相邻component连接；
- minimum component volume阈值由inner cases冻结；
- horizontal/vertical flip TTA概率平均。

禁止 validation-driven手工逐病例修补。

## 6. 训练目标

每个病理分支总权重相同。

### 6.1 Direct reconstruction

```text
L_direct = Dice + 0.5 * focal BCE + 0.5 * focal Tversky
```

Focal Tversky固定：

- FN权重 `0.70`；
- FP权重 `0.30`。

这是为了提高完整病灶召回，但由 contour、volume和negative losses约束假阳性。

### 6.2 Auxiliary losses

每病种：

- coarse extent Dice+BCE：`0.30`；
- presence BCE：`0.15`；
- heteroscedastic signed-distance NLL：`0.15`；
- log-volume ratio loss：`0.05`；
- hard-negative focal loss：`0.10`。

共同：

- internal anatomy DiceCE：`0.30`；
- scar-outside-edema soft inclusiveness：`0.10`，仅T2-present；
- alignment feature consistency：`0.05`，仅complete-trimodal；
- alignment offset magnitude penalty：`0.01`。

Scar 与 edema active loss必须分别报告，不能用平均值掩盖任一分支。

## 7. 采样与训练计划

### 7.1 Whole-heart训练单位

不再使用candidate-centered patch作为主训练分布。

- 输入为以myocardium为中心的 whole-heart crop；
- shape：`8 x 192 x 192`；
- batch size：`2`；
- 单次样本同时监督完整scar或完整edema-zone；
- scar/edema active samples按 `1:1` 平衡；
- complete-trimodal、C0+LGE、LGE-only在Stage A按 `0.50 / 0.25 / 0.25` 抽样；
- no-T2样本只提供scar/anatomy监督。

### 7.2 正式训练预算

每个 clean fold：

- Stage A0：`500` steps，冻结deeper encoder，只训练stems、alignment、anatomy和pathology decoders；
- Stage A1：`3500` steps，解冻全部shared encoder，全部reliable train cases；
- Stage B：`3000` steps，仅complete-trimodal train cases，center-balanced，降低LR；
- 总计：`7000 optimizer steps`；
- checkpoint every `500` steps。

优化器：AdamW。

- A0/A1 encoder lr `2e-5`；
- CARE-specific modules lr `1e-4`；
- Stage B全模型 lr `2e-5`；
- weight decay `1e-4`；
- bfloat16；
- grad clip `1.0`；
- seed `20260729`。

### 7.3 开发与clean证据

- fold0只允许zero-credit implementation/development run，不再作为clean科学门；
- 第一次clean gate固定为fold1 outer；
- checkpoint、direct threshold、minimum component volume和presence rescue threshold只能使用fold1 train-side inner cases选择；
- fold1 outer只评价一次；
- 不得用fold1 outer修改任何参数。

若fold1失败，必须完整分类原因后冻结一次全局修订，并使用fold2 outer作为下一次clean gate；不得继续在fold1上调参。

## 8. 对照与评价

必须比较：

- A0：同一fold五折体系中的nnU-Net anchor；
- A1：CARE-ARC no-alignment；
- A2：完整CARE-ARC；
- MoSAIC只作为历史/本地公平边界，不作为同fold初始化或runtime组件。

主要指标：scar、edema-zone、pure-edema分别报告：

- Dice；
- HD95与exact HD；
- precision/recall；
- volume ratio；
- component count；
- remote FP；
- positive-case empty rate；
- case-wise help/harm。

机制指标：

- coarse extent AUPRC和component recall；
- presence AUROC/AUPRC；
- direct mask vs nnU-Net changed-voxel ratio；
- SDF contour error与uncertainty calibration；
- alignment offset/confidence；
- scar/edema evidence gate权重；
- T2-present/no-T2 subgroup；
- CenterB/CenterC subgroup。

## 9. Clean fold1科学门

必须全部满足：

1. scar、edema-zone、pure-edema Dice delta均 `>= -0.005`；
2. scar或edema-zone至少一个 Dice delta `>= +0.010`；
3. 另一个主病理 Dice delta `>= 0.000`；
4. 每病理 help `>= harm - 1`；
5. HD95 `<= 1.05 x anchor`；
6. 无新增infinite exact-HD；
7. remote FP `<=1.10 x anchor`；
8. positive-GT empty rate不高于anchor；
9. scar和edema direct masks在至少50%的positive cases中，相对anchor changed pathology voxels `>=5%`；
10. scar和edema direct branch、presence、contour、alignment均真实激活；
11. no-T2 edema exact-zero；
12. no-alignment control必须被报告，不能用alignment claim掩盖无效。

通过clean gate后，才允许按完全冻结的结构和超参数训练一个single-backbone full-data model，并准备本地validation package。上传仍需用户单独授权。

## 10. 失败诊断，不允许放弃

任何不理想结果必须分类：

- `EXECUTION_FAILURE`：实现、mask、split、resume、eval或export错误；同任务原地修复。
- `ENCODER_LIMITED`：coarse extent、presence和direct logits均无病例外信号；检查初始化、feature scale和全局感受野，不得只调threshold。
- `ALIGNMENT_LIMITED`：alignment offsets过大/置信度失真，identity control更好；下一clean fold固定关闭warp或收紧offset，不增加registration backbone。
- `DETECTION_LIMITED`：presence/coarse recall不足、positive empty高；整体提高召回课程与presence/coarse监督，不只调后处理。
- `CONTOUR_LIMITED`：recall足够但HD95/precision差；整体加强contour NLL、volume和boundary，而不是重新回到nnU-Net residual。
- `DOMAIN_CALIBRATION_LIMITED`：fold内安全但hidden形态仍偏小；使用complete-trimodal full-data Stage B、TTA和预注册threshold，不允许逐病例hidden调参。

禁止输出项目终止、放弃CARE或恢复nnU-Net-only作为研究终态。失败只能触发下一次完整设计判断。

## 11. 资源和权限

唯一GPU资源：

```text
61220581
partition: htzhulab
node: g1807htzh01
```

所有GPU命令只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

严格禁止：

- `sbatch`；
- `salloc`；
- 新Slurm job；
- 并行两个GPU进程；
- 写 `/overflow/htzhu/CARE`；
- runtime push；
- validation/Docker upload；
- 未通过clean gate就训练full-data submission model。
