# CARE-PRISM 执行与架构加固修正案 v2

**日期：** 2026-07-29  
**状态：** ACTIVE_HIGHEST_AUTHORITY  
**适用任务：** `20260729_care_prism_fold0_fold1_v2`  
**优先级：** 本修正案 > CARE-PRISM 原蓝图 > v2 executor plan > v2 controller > 旧 PRISM / ARC / DPR / DG / MMRD / SRR 合同

## 1. 修订结论

CARE-PRISM 原重设计方向正确：强同折初始化、病种专属证据、内部解剖、病灶提议、负空间与软级联都必须保留。但原蓝图仍存在四类高风险：共享主干输入改变会破坏 nnU-Net 权重移植；双向 anatomy-pathology 交换可能污染解剖表征；物理 bbox/crop 与 GT-to-predicted ROI curriculum 会制造不可微和 train/deploy 错位；prototype、router、alignment 同时作为强依赖会让任何一个不稳定模块拖垮整个系统。

v2 将正式系统冻结为：**一个可做严格移植与同输入奇偶校验的共享 ResEnc 主干；一个只从解剖流向病理的零初始化交换路径；全体积连续软注意力而非硬 crop；proposal 的 learned evidence 与 safe-negative discrimination 为核心，prototype 与 slice correspondence 仅在独立证据门通过后启用。**

本修正案吸收以下公开机制边界：MyoPS-Net 的病种专属解码与心肌一致性；U-MyoPS / CAA-Seg 的可靠对应优先于强制配准；APEx 的 anatomy-to-pathology 交换；小病灶工作中的病灶级监督与安全 hard-negative mining；距离/表面损失只在 refinement 后期处理边界，而不是替代定位。

## 2. 正式数据流

```text
[LGE,T2,C0]，缺失通道置零
→ exact 3-channel shared ResEnc encoder（same-fold nnU-Net初始化）
→ LGE/T2/C0 lightweight private pyramids
→ pathology-specific soft retrieval
→ internal anatomy decoder
→ stop-gradient soft anatomy band + zero-init anatomy→pathology exchange
→ learned coarse evidence + category-specific safe-negative logits
→ optional gated cross-case prototype residual
→ full-volume continuous anatomy/proposal attention
→ independent scar high-resolution refiner
→ independent edema large-context refiner
→ edema-zone direct probability
→ scar priority
→ pure edema = edema-zone - scar
```

只有一个完整 backbone。禁止第二 U-Net、MoSAIC/MMRD runtime、nnU-Net pathology residual、DPR component utility、ADD/REVISE、完整 SRR dictionary、SIP、top-k、多 expert backbone 和 hard myocardium crop。

## 3. 共享主干与权重移植

1. 共享 encoder 输入必须保持源 Dataset501 nnU-Net 的精确三通道顺序和形状：`[LGE,T2,C0]`。缺失通道置零，但 availability 不得拼入 shared encoder 输入。
2. Availability 只能进入 private pyramid mask、router 和监督掩码。
3. 从 `nnUNetPlans.json` 与同折 checkpoint 恢复精确 `ResidualEncoderUNet` architecture kwargs；不得手写近似主干。
4. encoder 形状匹配加载覆盖率按参数字节必须 `>=0.90`。
5. 更强的通过条件是：CARE modules 关闭、同一完整病例、FP32、eval mode 时，shared encoder 每个对应尺度与源 nnU-Net encoder 的最大绝对误差 `<=1e-6`。
6. anatomy decoder 只加载形状和语义都兼容的 block；新 union/LV/RV 输出层重新初始化。不得用低覆盖率 decoder 移植冒充成功。

## 4. 病种专属检索

每尺度形成共享特征 `E_l` 与私有特征 `P_l^m`。Scar 和 edema 分别计算：

$$R_l^k=w_{l,sh}^kA_{l,sh}^k(E_l)+\sum_{m\in\{LGE,T2,C0\}}m_mw_{l,m}^kA_{l,m}^k(P_l^m).$$

冻结规则：

- router 只读 masked pooled normalized features 与 availability，不读 center ID 或历史模型输出；
- unavailable modality 权重精确为零；shared 权重下限固定 `0.20`；
- scar 初始偏向 LGE，edema 初始偏向 T2；
- 使用 softmax，不使用 top-k；anti-collapse entropy floor 仅在 Stage A/B 生效，Stage C 起线性衰减为零；
- gate 必须真实改变 routed features 与最终 logits；仅返回审计张量为 known-bad；
- 不以“平均 LGE/T2 权重大小”作为科学成功证据。完整病例 matched modality ablation 必须显示：移除 LGE 对 scar 的损害大于移除 T2；移除 T2 对 edema 的损害大于移除 LGE。

## 5. 可靠切片对应

1. 默认 identity；不允许从第一步就强制 alignment。
2. 在 E2 对完整三模态病例计算 LGE reference、`i-2...i+2` 的 soft slice attention。
3. 使用 attention entropy/peak confidence表示可靠度；低可靠度返回 identity/LGE-only context，不做 hard argmax warp。
4. W2 在 train-side fixed cases 比较 identity 与 correspondence。只有两病理均不伤、平均 Dice proxy `>=+0.003`、HD proxy不恶化且非 identity 使用比例合理时，才冻结 enabled；否则冻结 identity。
5. W3/W4 训练和部署必须使用同一冻结模式，禁止再次出现 train enabled / deploy identity。

## 6. 单向解剖交换与全体积软级联

Internal anatomy decoder输出 `P_union/P_LV/P_RV` 和各尺度 `A_l`。正式病理路径采用：

- anatomy→pathology 单向交换；病理梯度不得回流 anatomy decoder；
- `stopgrad(P_union,P_LV,P_RV,A_l)` 进入每个病理解码尺度；
- 每尺度交换采用零初始化 residual gate，初始等价于无交换，随后由数据学习；
- anatomy decoder只由 anatomy loss和冻结的 correspondence consistency训练。

取消物理 bbox、variable-size crop、paste-back 和 GT ROI curriculum。全体积软级联固定为：

```text
anatomy_band = 0.25 + 0.75 * soft_dilate(stopgrad(P_union))
proposal_attention_k = 0.25 + 0.75 * sigmoid(proposal_logit_k)
refiner_input_k = routed_features ⊕ anatomy_features ⊕ anatomy_band ⊕ proposal_attention_k ⊕ negative_logits
```

所有体素始终保留至少 `0.25` 信息底噪；proposal 为空时仍有全体积 anatomy band，不能 hard delete 病灶。Proposal/anatomy 的 on/off 干预必须改变 final logit，否则不得训练。

## 7. Proposal、负空间与可选 prototype

### 7.1 核心 proposal

每病理都有 learned positive evidence head、四类 safe-negative head 和 coarse proposal head。核心 proposal 在 prototype 关闭时也必须独立工作。

Scar safe-negative：正常心肌、LV/RV血池、union外背景、actual-train 历史远端 FP / LGE亮伪影。  
Edema safe-negative：仅 T2-present 病例的正常心肌、血池、union外背景、距可靠 edema GT 足够远的 T2 artifact。no-T2 myocardium 永远不是 edema negative。

Hard-negative replay 只允许一次：使用 actual-train 冻结 checkpoint 生成，按上述安全类别落盘；不得读取 inner/outer GT 或预测。

### 7.2 Prototype 为可降级增强

- EMA momentum `0.95`，read-before-update，optimizer step后更新；当前病例不得参与自己的 prototype query；
- prototype 只提供 proposal 的 gated additive residual，gate 零初始化；不得直接生成标签；
- 只有 cross-case margin AUROC `>=0.70` 且 matched no-prototype control 不伤主指标时才启用；否则固定关闭，而不是判整条路线失败；
- checkpoint 必须保存 prototype、计数、更新时间、source-case hashes。

## 8. Refinement 与损失

Scar refiner：LGE主导、高分辨率 skip、小病灶实例召回和较强负空间。  
Edema refiner：T2主导、大感受野、dilation `2/3`、高召回与软边界；只在 T2-present reliable cases更新。

总损失固定：

```text
0.50 L_anatomy
+ 0.35 (L_proposal_scar + mT2 L_proposal_edema)
+ 1.00 (L_refine_scar + mT2 L_refine_edema)
+ 0.15 (L_negative_scar + mT2 L_negative_edema)
+ 0.10 L_burden
+ 0.05 L_soft_relation
+ 0.02 L_router_anticollapse(Stage A/B only)
+ optional 0.05 L_prototype when prototype_enabled
```

固定的 refiner loss，不留 `or`：

```text
Scar: DiceCE + 0.50 Focal-Tversky + 0.15 component-adaptive Tversky/lesion-MIL + 0.05 Generalized Surface Loss
Edema: DiceCE + 0.35 Focal-Tversky + 0.05 Generalized Surface Loss
```

Component/MIL 与 surface loss 仅在 Stage C 第500步后启用；Stage A/B不得用边界正则掩盖 proposal 失败。所有 loss 必须非负、有限，且有对应参数梯度。删除独立 SDF uncertainty head。

Burden 使用 continuous log lesion/union ratio 和 positive-case low/medium/high tertile；binary presence只作 empty audit，不作为 final gate。

## 9. No-T2 与采样

- forward 必须显式返回 `edema_probability=zeros_like(...)` 和 `edema_mask=zeros`；不得用 `logit=0` 冒充零概率；
- no-T2 edema proposal/refiner/negative/prototype/burden loss及梯度精确为零；
- 每 optimizer step 两个串行 micro-batch：一个 scar-focused full case，一个 T2-present edema-focused full case；
- 先等概率选 eligible center，再选 positive burden tertile或safe-negative case；负空间 voxel在病例内部分类采样，不通过重复少数空病例实现；
- 所有可用模态共享空间增强，各模态独立强度增强；结构化 modality dropout 只在完整病例上进行，drop T2 的 view edema loss为零。

## 10. Checkpoint、评价和可修复性

Checkpoint 必须保存：model、optimizer、scheduler、scaler、stage、step、sampler cursor、augmentation RNG、prototype state、hard-negative bank hash、split/config/contract hashes。Resume 后下一批病例、增强参数与学习率必须一致。

W2 是400步 zero-credit实现门。W3 fold0固定6500步：A1000/B1500/C2500/D1500；每500步保存，所有 checkpoint 仅在 train-side inner 选择，outer在freeze receipt后只评一次。W3通过后，W4 fold1固定8000步并重新从fold1同折nnU-Net初始化。

W3硬门：

```text
encoder transplant coverage >=0.90 and FP32 scale parity <=1e-6
anatomy soft-band GT coverage >=0.98
scar lesion proposal recall >=0.80
edema lesion proposal recall >=0.90
scar refiner Dice gain over proposal >=0.03
edema refiner Dice gain over proposal >=0.02
matched modality-causal ablations PASS
anatomy-exchange on/off non-harm
negative-space on/off remote-FP reduction >=10% with lesion-recall loss <=0.02
raw final scar and edema-zone Dice delta vs nnU-Net >=-0.02
at least one main pathology Dice delta >=+0.01
HD95 and remote-FP ratio <=1.10
router noncollapse; no-T2 exact zero
prototype result reported but prototype PASS is not mandatory
```

W4 clean gate沿用原严格门：两主病理不劣、至少一个 `>=+0.010`、HD95 `<=1.05x`、remote FP `<=1.10x`、无新增 infinite exact-HD、逐病理 help/harm合格。

Controller必须将失败分类为：`EXECUTION_OR_INIT`、`ROUTING`、`ANATOMY_EXCHANGE`、`PROPOSAL`、`NEGATIVE_SPACE`、`REFINEMENT`、`CALIBRATION`。普通实现、OOM、cache、sampler、loss、resume、评价、validator问题属于同范围修复，必须退回同一Executor继续修复；只有忠实实现、充分训练、全部checkpoint重载评价后仍未过机制门，才返回Planner。

## 11. 证据与边界

必须视觉阅读的版本：`SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD, CARE-SRR-Cascade, CARE-DG, CARE-ARC, MoSAIC`。恢复目标为：availability-aware evidence → selective retrieval → anatomy-guided proposal → pathology-specific refinement → negative-space safety。

禁止 validation/Docker upload、hosted claim、runtime push、fold1 outer调参和把 nnU-Net-only恢复为研究终态。