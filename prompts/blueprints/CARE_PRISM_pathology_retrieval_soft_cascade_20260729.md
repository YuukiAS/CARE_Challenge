# CARE-PRISM：病种专属证据检索、内部解剖交换与软级联完整重建

## 结论

CARE-ARC W3 不是单纯的“轮廓差一点”。它同时暴露了实现未兑现和架构机制不足：当前代码实际退化为随机初始化的 early-fusion 单编码器加两个普通 dense decoder；承诺的病种证据门、解剖引导和 coarse-to-fine 都没有进入最终计算链，SDF 不确定性损失还出现了负值捷径。W3 的 raw direct scar / edema-zone Dice 分别比 nnU-Net 低 0.1805 / 0.1554，remote FP 约为 nnU-Net 的 2.1 倍 / 5.1 倍，因此不能只靠换 loss、再训几千步或调阈值修复。

新的主线为 **CARE-PRISM: Pathology-specific Retrieval, Internal-anatomy Exchange, and Soft-cascade Multi-scale Reconstruction**。它使用一个强共享 ResEnc 主干，但把 scar 与 edema 的证据检索、病灶提议和完整重建分开；通过病例级 soft myocardium ROI、显式正负证据和病灶级监督形成连续病灶，不再围绕 nnU-Net 病理 mask 做 residual，也不再采用 DPR 的 component utility。

## 1. W3 根因冻结

### 1.1 已确认的实现失败

1. `scar_gates` / `edema_gates` 只被返回用于审计，未参与 encoder、proposal 或 decoder 特征融合。
2. anatomy decoder 的 logits/features 未进入 scar/edema decoder，图中“soft anatomy guidance”未实现。
3. `coarse_extent_logit` 仅承担辅助 loss，未生成 soft ROI，也未调制 direct decoder，因此不是真正 coarse-to-fine。
4. SDF mean/logvar 与 direct logits 没有计算关系；全体积 heteroscedastic NLL 可通过极低 logvar 在大量易背景处取得负值。正式训练尾部 `scar_active` / `edema_active` 已出现负数，W2 的 loss-drop 不能再作为有效学习证据。
5. W3 从随机初始化启动，没有执行合同中允许且预期的 same-fold nnU-Net encoder/anatomy decoder 权重移植。
6. 正式训练没有空间或强度增强，没有 nnU-Net 级别的数据扰动和学习率调度。
7. 采样器并未做到每 optimizer step 一个 scar-focused 与一个 edema-focused 病例；也没有中心 × 病灶负荷的真正均衡。
8. 训练默认启用 alignment，W3 冻结部署却使用 identity，存在 train/deploy 模式错位。
9. 只评价 step3000 terminal checkpoint，没有对 500–3000 checkpoints 做 train-side checkpoint selection。
10. no-T2 将 edema logit 乘为 0，sigmoid 后仍为 0.5；只有 decode 规则额外归零，不能把“logit=0”写成模型概率 exact zero。

### 1.2 已确认的设计失败

1. 全病例 `256×256×D` dense loss 中 scar prevalence 约 0.3%，没有病灶级提议、实例级监督和安全负空间，普通 decoder 很难形成小而连续的病灶。
2. 三个小 stem 后立即 early concat，模态身份只存在于浅层；LGE/T2/C0 没有在各尺度被 scar/edema 真正选择。
3. 二元 presence 在 fold0 outer 的阳性率约 97.7%，几乎是常数任务，不能提供有意义的病例级判别。
4. burden FiLM 只能控制整体幅度，无法替代空间定位。
5. 独立 SDF auxiliary head不参与最终 mask，无法修复轮廓。
6. 当前 evaluator 将严重 remote FP / HD 恶化归为 `CONTOUR_LIMITED`，低估了定位和负空间失败。

## 2. 设计目标

CARE-PRISM 必须同时具备：

- 一个成熟、强初始化的共享主干，而不是随机小网络；
- 真正进入计算链的 availability-aware 病种专属多尺度检索；
- 内部 anatomy 与 pathology 的双向特征交换，而不是只画一个 anatomy head；
- scar / edema 各自的完整病灶提议与整块 myocardium-neighborhood refinement；
- 正负证据差分和 hard-negative replay；
- 病灶级与边界级监督；
- 无 T2 edema 监督卫生；
- 无常态 nnU-Net pathology residual、无 component utility、无多个完整 backbone。

## 3. 唯一正式网络

### 3.1 输入与共享强主干

输入：

```text
LGE, T2, C0, availability=[m_lge,m_t2,m_c0]
```

缺失模态输入张量置零，但必须同时显式提供 availability；这只是缺失占位，不是模态插补。

共享主干固定为当前 Dataset501_CAREMyoPS 同折 nnU-Net `3d_fullres` 的真实 ResidualEncoderUNet 编码器结构。Executor 必须从 `nnUNetPlans.json` 和同折 checkpoint 解析并记录精确 architecture kwargs；不得用手写 24M tiny encoder 替代。至少 90% 的 encoder 参数字节必须从同折 checkpoint 形状匹配加载，否则 fail closed。

主干只有一个。nnU-Net 权重只作初始化；正式 pathology forward 不读取 nnU-Net scar/edema/anatomy probability、entropy、margin 或 hard mask。

### 3.2 模态私有金字塔与真实软检索

每个原始模态建立一个轻量私有金字塔，不是完整 encoder：

```text
stem: Conv3D 1→16 + 2 residual blocks
private pyramid: 16→32→48→64，使用 depthwise-separable stride conv
```

在共享 encoder 的前四个空间尺度，分别得到：

```text
E_l                    shared feature
P_l^LGE, P_l^T2, P_l^C0 private adapter features
```

scar 与 edema 各有独立 soft router。每个 router 读取该尺度的 masked global pooling、availability embedding 和病例级 quality statistics，输出 shared/LGE/T2/C0 四个权重。权重必须真实用于：

$$R_l^k=w_{l,sh}^kA_{l,sh}^k(E_l)+\sum_{m\in\{LGE,T2,C0\}}m_mw_{l,m}^kA_{l,m}^k(P_l^m),\quad k\in\{scar,edema\}.$$

约束：

- shared 权重下限 0.20；
- unavailable modality 权重严格为 0；
- scar router 初始偏向 LGE；
- edema router 初始偏向 T2；
- 使用 softmax，不使用 top-k、SIP 或大型 expert bank；
- router collapse、所有病种使用相同权重、或 gate 不影响输出都必须 fail closed。

### 3.3 可靠的选择性切片对应

完整三模态病例在 E2 尺度执行轻量选择性切片对应，而不是上一版饱和的 3D offset field。以 LGE slice 为 reference，对 T2/C0 在 `i-2...i+2` 范围内计算 anatomy-feature cosine correspondence；只对最大可靠度 `>=0.50` 的切片做 soft aggregation，低可靠度直接退回未对齐特征。该模块无第二个 registration backbone，不对缺模态病例运行。

必须报告 slice reliability、非 identity 使用比例和 identity control；该模块若对 fold0 development 没有正收益，clean fold固定关闭，不能临时重写。

### 3.4 内部 anatomy decoder 与跨分支交换

使用一个 nnU-Net-style anatomy decoder，形状兼容部分从同折 checkpoint 初始化，输出：

```text
P_union = myocardium ∪ scar ∪ edema
P_LV
P_RV
A_l = multi-scale anatomy decoder features
```

每个 scar/edema decoder block必须接收同尺度 `A_l`、`P_union`、`P_LV`、`P_RV`，形成真正的 anatomy-pathology exchange。禁止只输出 anatomy logits却不进入病理分支；禁止用 hard myocardium mask裁掉病灶。

### 3.5 病种专属 proposal 与负空间记忆

Scar 与 edema 各自建立：

```text
coarse evidence head
positive EMA prototype
four category-specific negative EMA prototypes
prototype margin map
soft proposal head
```

Scar 安全负类：正常心肌、LV/RV 血池、union 外背景、LGE 亮伪影/历史远端 FP。

Edema 安全负类：T2-present 病例中的正常心肌、血池、union 外背景、距可靠 edema GT 足够远的 T2 artifact。no-T2 myocardium 永远不能作为 edema negative。

原型只在 actual-train 标签上以 momentum `0.95` 更新，prototype 本身 detached；网络通过正负 margin loss学习可分特征。proposal 输入必须包含 routed feature、positive-negative similarity margin、soft anatomy、病例级 burden embedding和 uncertainty。原型不得直接决定最终标签。

### 3.6 单病例 soft ROI，而非数千 component candidates

每个病种每个病例只有一个 myocardium-neighborhood ROI：

- 根据 `P_union` 的全病例 bbox 外扩 12 mm；
- 训练前 300 steps 使用 GT union ROI；301–1000 steps 线性切换到 predicted union ROI；1001 steps后及全部评价只使用 predicted ROI；
- proposal 仅作为连续注意力：`attention=0.25+0.75*sigmoid(proposal)`，保留 0.25 全局底噪，不能 hard delete；
- proposal为空时仍使用完整 anatomy ROI，避免再次出现 proposal miss 后 refiner无输入。

### 3.7 Scar / edema 完整重建

两条分支结构独立但对称，不是共享最后小头：

**Scar refiner**

- LGE-dominant routed features；
- 更高分辨率 skip；
- 小病灶/实例召回监督；
- 较强负空间 margin；
- 输出 full-ROI direct scar logit。

**Edema refiner**

- T2-dominant routed features；
- 更大 receptive field，dilation 2/3；
- 高召回、模糊边界监督；
- 只在 T2-present reliable cases更新；
- 输出 full-ROI direct edema-zone logit。

两者都必须将 soft ROI 结果 paste 回完整体积。最终：

```text
CARE edema-zone direct mask
→ CARE scar priority
→ pure edema = edema-zone - scar
```

不使用 nnU-Net pathology residual，不使用 ADD/REVISE，不使用 component utility。

### 3.8 病例级 burden，不再依赖几乎恒真的 presence

每个病种输出：

- 4-bin burden class：empty / low / medium / high；
- continuous log lesion-to-union volume ratio。

burden embedding 通过 FiLM 同时调制 proposal 与 final refiner。binary presence只作低权重辅助和 empty-case audit，不得作为主要门。

## 4. 损失函数

禁止上一版独立、可取负值且不连接 direct logit 的 SDF NLL。

总损失固定为：

```text
0.50 L_anatomy
+ 0.35 (L_prop_scar + mT2 L_prop_edema)
+ 1.00 (L_ref_scar + mT2 L_ref_edema)
+ 0.15 (L_proto_scar + mT2 L_proto_edema)
+ 0.10 L_burden
+ 0.05 L_soft_relation
+ 0.02 L_router_balance
```

每个 refiner loss：

```text
DiceCE
+ 0.50 Focal-Tversky
+ 0.15 component-adaptive Tversky / lesion-MIL
+ 0.05 HausdorffDT or regional surface loss
```

所有 loss 必须非负、有限，并能追踪到对应参数梯度。scar–edema关系只在 T2-present 且 edema confidence高时使用弱不对称软约束，不作硬包含。

## 5. 数据与增强

训练单位是患者，不按 slice/component 重复计权。每个 optimizer step使用 gradient accumulation 2：

```text
micro-1: scar-focused case
micro-2: T2-present edema-focused case
```

按 center × lesion burden tertile × positive/safe-negative 均衡。no-T2病例只参与 anatomy、scar和缺模态一致性，不参与任何 edema 正/负监督。

固定增强：

- 所有可用模态共享空间变换：rotation ±15°、scale 0.85–1.15、flip；
- 各模态独立强度变换：gamma 0.7–1.5、contrast、Gaussian noise、bias field；
- 只对完整病例做结构化 modality dropout：C0 20%，T2 10%；若drop T2则该 view 的 edema loss=0；LGE不drop；
- 25%完整病例对T2/C0做±1 slice与±3 pixel轻度错位增强；
- 禁止无增强地反复读取固定全病例张量。

## 6. 训练日程

Fold0 development 总计 6500 optimizer steps：

1. **Stage A — strong initialization and evidence warm-up，1000 steps**
   - 前300冻结shared encoder/anatomy decoder；
   - 后700解冻top-3 encoder stages；
   - 训练private pyramids、routers、anatomy exchange、coarse proposal、burden。
2. **Stage B — proposal / prototype / negative-space，1500 steps**
   - lower encoder冻结；
   - 训练proposal、EMA prototypes、prototype margin；
   - step750刷新一次actual-train hard-negative replay。
3. **Stage C — full-lesion soft-cascade refinement，2500 steps**
   - predicted anatomy ROI only；
   - 训练scar/edema完整ROI refiner；
   - 使用病灶级、边界级损失。
4. **Stage D — low-LR joint calibration，1500 steps**
   - 解冻top-4 encoder stages与全部CARE heads；
   - shared encoder lr `1e-5`，new modules lr `3e-5`；
   - cosine decay，AdamW，weight decay `1e-4`，bf16，grad clip `1.0`。

Checkpoint every 500 steps。所有 checkpoints 只能在 train-side inner cases选择，不得硬编码terminal checkpoint。

## 7. W3发展门与clean fold门

### W3 fold0 development

必须同时满足：

- same-fold nnU-Net encoder init coverage >=90% parameter bytes；
- anatomy ROI GT coverage >=0.98；
- scar lesion-wise proposal recall >=0.80；
- edema lesion-wise proposal recall >=0.90；
- scar/edema refiner Dice各自比其proposal Dice提高 >=0.05；
- scar/edema prototype margin AUROC >=0.70；
- router非collapse且scar平均LGE权重 > T2、edema平均T2权重 > LGE；
- raw final scar/edema-zone Dice delta vs nnU-Net均 >= -0.03；
- 至少一个主病理 delta >= +0.005；
- HD95 <=1.20x anchor；remote FP <=1.20x anchor；
- no-T2 edema probability/mask/loss/gradient exact zero；
- raw direct、soft-cascade、no-prototype control分别报告。

普通代码、数据、权重移植、augmentation、loss、resume或评价错误必须在同一Controller目标内修复，不能写成设计失败。

### W4 clean fold1

W3通过后，完整冻结结构和训练合同，在fold1重新训练8000 steps；checkpoint/decode只用fold1 train-side inner，outer原子锁一次评价。Clean gate：

- scar / edema-zone / pure-edema Dice delta均 >= -0.005；
- scar或edema-zone至少一个 delta >= +0.010；
-另一个主病理 delta >=0；
- per-pathology help >= harm-1；
- HD95 <=1.05x，remote FP <=1.10x，无新增infinite exact-HD；
- proposal/refiner/router/prototype均有病例外机制证据。

只有clean gate通过，才允许single-model full-data fit和本地package dry-run；仍禁止validation/Docker upload。

## 8. 继承与删除

保留：

- Batch7/SRR：availability-aware病种证据、负空间、anatomy-guided proposal、scar/edema差异化 refinement；
- MMRD：强ResEnc、可靠标签、no-T2监督卫生、structured modality dropout；
- Cascade：强同折初始化、解剖稳定性、case-wise help/harm、exact-HD和病种独立安全审计；
- DG/DPR：显式错误形态审计、full-volume aggregation、train/inference parity。

删除：

- nnU-Net pathology residual作为主线；
- component utility和数千局部candidate；
- 多个完整backbone；
-完整SRR shared/private/interaction dictionary、SIP、top-k router；
- 不连接最终mask的SDF uncertainty head；
- hard myocardium crop；
- MoSAIC runtime或权重。

## 9. 资源边界

唯一GPU allocation：`61220581`，`htzhulab`，`g1807htzh01`。

所有GPU命令串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新Slurm job、并行GPU进程、写`/overflow/htzhu/CARE`、runtime push、validation/Docker upload。
