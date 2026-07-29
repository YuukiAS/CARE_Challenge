# CARE-ARC 执行加固修正案 R1

**日期：** 2026-07-29  
**状态：** ACTIVE_AUTHORITY  
**适用任务：** `20260729_care_arc_clean_fold1`  
**优先级：** 本修正案 > CARE-ARC blueprint > v2 executor plan > v2 controller > 旧 v1 文件 > 历史 DG/DPR/MMRD/Cascade

## 1. 修正动机

新增分析确认三点：

1. CARE-DG 在单折 OOF anchor 上训练、在五折 ensemble anchor 上部署，存在明确的 anchor-distribution shift；CARE-ARC 不能只删除 nnU-Net 病理通道，却继续让 nnU-Net anatomy/uncertainty 成为可学习病理特征。
2. MoSAIC hosted 优势更接近“完整病灶负荷 + 少量连续组件 + 高召回”的病例级偏置；仅有 voxel direct head 和弱 volume loss不足以保证模型学到全病例负荷。
3. 仓库病例 z 深度并不固定为 8，已有 grid receipt 中可见 `D=9,12,16,20,24,32`。固定 `8×192×192` 不能称为 whole-volume direct reconstruction。

因此以下条款覆盖旧合同。

## 2. 正式 trainable 输入：彻底移除 anchor 分布依赖

CARE-ARC trainable forward 的正式输入只能是：

```text
LGE, T2, C0, availability
```

nnU-Net 只允许：

- same-fold encoder 的 shape-compatible 初始化；
- 最终 background/myocardium/LV/RV 标签；
- 灾难性 asset/grid fallback；
- 只读基线、分层分析和审计。

严禁把以下量输入 shared encoder、evidence gate、anatomy decoder、scar/edema direct decoder、presence、burden或SDF head：

```text
nnU-Net scar/edema probabilities
nnU-Net anatomy probabilities
nnU-Net entropy/uncertainty
nnU-Net-derived distance map
```

确定性 crop 也不得依赖 nnU-Net mask。病理输出必须在传入单折 OOF、五折 ensemble、全零 external context 三种占位输入时保持完全相同；正式 API 可以不接受这些参数。

## 3. 单主干精确结构，禁止 Executor 自行缩小

参数预算：`20M <= trainable_parameters <= 45M`。主体只能有一个 encoder。

### 3.1 stems 与 encoder

```text
每模态 stem:
Conv3d 1->16, kernel (1,3,3)
InstanceNorm + SiLU
2 x residual block, 16 channels, kernel (1,3,3)

fusion:
concat 3 stems + broadcast availability
1x1 Conv -> 48 channels

E0: 48 channels, 2 residual blocks, stride 1
E1: 64 channels, stride (1,2,2), 2 residual blocks
E2: 128 channels, stride (1,2,2), 3 residual blocks
E3: 256 channels, stride (1,2,2), 3 residual blocks
```

E0/E1 使用 `(1,3,3)`；E2/E3 使用 `(3,3,3)`，z 方向不下采样。

### 3.2 轻量对齐

- 只在 E2 的 `1/4` in-plane 尺度；
- LGE 为 reference；
- T2/C0 各一个 `3x3` conv offset+confidence head；
- offset 每轴 `4*tanh(raw)`，单位为该尺度 pixel；
- confidence 为 sigmoid；
- identity 初始化：offset head 权重/偏置为0，confidence bias为 `-4`；
- 不允许独立 registration encoder。

### 3.3 病理 evidence gate

每病理、每尺度一个 SE-style 三模态标量门：全局池化 stem/downsampled-stem 与 availability，经两层 MLP 后做 masked softmax；缺失模态权重必须精确为0，三模态可用权重和为1。scar gate 的输入顺序固定 LGE/T2/C0，edema 固定 T2/LGE/C0；不得改成多 expert/router。

### 3.4 decoders 与病例级 burden

Internal anatomy decoder：E3->E2->E1->E0，通道 `128/64/32`，输出 myocardium/LV/RV。

Scar 与 edema 各有独立 decoder，E3->E2->E1->E0，通道 `128/64/32`。Scar 拼接 LGE stem skip；edema 拼接 T2 stem skip，并在 E2 使用 dilation `2,3` 的两个 residual blocks。

每病理必须同时输出：

```text
coarse_extent_logit (E2 / 1/4尺度)
direct_full_logit
presence_logit (case-level)
log_burden_pred (case-level)
sdf_mean
sdf_logvar
```

`log_burden_pred` 来自 E3 global pooling，并经 FiLM 实际调制该病理 final decoder block；只写 auxiliary head 而不影响 direct logits为 known-bad。

## 4. 真正 full-volume 数据单位

禁止 z=8 crop。每个 sample 保留病例完整 z 深度 `D`，不得丢弃任何切片。

In-plane crop 只使用图像中心，不读 nnU-Net：在 fold1 actual-train 上依次审计 `192,224,256`，选择第一个能覆盖 `100%` GT myocardium、scar及可靠 edema voxel 的尺寸；选择规则只基于覆盖率，不基于性能。冻结后 W3/W4/W6相同。若256仍非100%，fail closed。

训练：

```text
batch size: 1 full case
gradient accumulation: 2
effective batch: 2
variable D allowed; no z resampling/cropping
```

所有 presence、burden、component和volume指标必须基于完整病例，不得基于 slab/patch。

## 5. 病例均衡采样，候选数不得冒充样本数

Fold outer-train 先固定 `inner12`；ARC actual-train必须排除 inner12 和 outer。Sampler统计只从 actual-train生成。

每个 optimizer step包含两个串行 microbatches：

1. scar-focused full case；
2. edema-focused full case（仅T2-present）。

每病理：positive case概率 `0.75`，reliable hard-negative概率 `0.25`。Positive病例按 actual-train GT lesion/myocardium volume fraction的低/中/高三分位等概率抽样；先等概率选择 eligible center，再在 center×burden stratum 内均匀抽病例。不得按component数或slice数加权患者。

Stage A的模态组边际比例仍为 `0.50/0.25/0.25`；若与scar positive/hard-negative条件冲突，按预计算联合池循环，不得静默fallback。Stage B只使用complete-trimodal，并继续病例/center/burden均衡。

## 6. Loss精确定义

原 direct/coarse/presence/anatomy损失保留。新增并覆盖旧弱volume项：

```text
GT burden = log((lesion_volume_mm3 + 1)/(GT_myocardium_volume_mm3 + 1))
L_burden_head = SmoothL1(log_burden_pred, GT burden), weight 0.10
L_burden_consistency = |log((sum(sigmoid(direct))*voxel_mm3+1)/(GT_myocardium_volume_mm3+1)) - stopgrad(log_burden_pred)|, weight 0.05
```

SDF：物理mm距离，inside为正，截断 `[-15,15] mm` 后除以15；`sdf_logvar` clamp `[-5,3]`；heteroscedastic NLL固定为 `0.5*exp(-logvar)*(mean-target)^2 + 0.5*logvar`。

Scar/edema总病理权重相同；no-T2 edema所有输出、loss、gradient精确为0。

## 7. Alignment不是强行卖点

W3用同一checkpoint同时评价 aligned 和 identity/no-alignment。仅当 fold0 development 中：

```text
scar和edema-zone aligned-vs-noalign Dice均 >= -0.002
两主病理平均Dice增益 >= +0.003
两主病理HD95 ratio均 <=1.02
confidence非全0/全1，offset无饱和
```

才冻结 `alignment_mode=enabled` 进入W4；否则冻结为 identity。该规则不得由Executor改写。Clean gate只要求冻结模式正确执行并完整报告control，不强制alignment必须启用。

## 8. W3开发充分性门

W3不用于promotion，但不得让明显失效实现直接消耗clean fold。

必须额外输出：

- raw direct mask、postprocessed mask和nnU-Net三者；
- direct head单独Dice/HD95/volume/component；
- 按nnU-Net GT volume ratio分为欠分割 `<0.8`、接近 `[0.8,1.2]`、过分割 `>1.2` 的帮助/伤害；
- burden预测相关性与误差；
- full-case component/remote-FP；
- anchor-context invariance测试。

进入W4的最低机制条件：

```text
scar和edema coarse AUPRC > prevalence
scar和edema presence AUPRC > prevalence
两主病理raw direct Dice delta均 >= -0.05
median positive-case volume ratio均在[0.25,4.0]
两病理至少50% positive cases changed-mask ratio >=5%
无component数量级爆炸
no-T2 exact-zero
```

执行错误由Controller退回Executor修复并重跑W1-W3。若机制条件仍失败，停止在W3并返回Planner做完整架构修订；这是避免浪费clean fold，不是项目终止。

## 9. Decode与checkpoint选择冻结

TTA固定为 horizontal/vertical flip probability mean，不参与选择；同时报告no-TTA control。

Inner候选：

```text
scar direct threshold: [0.25,0.30,0.35,0.40,0.45,0.50]
edema threshold: [0.20,0.25,0.30,0.35,0.40,0.45,0.50]
scar min component mm3: [0,10,25,50]
edema min component mm3: [0,25,50,100]
presence rescue threshold: fixed 0.70
bridge distance: fixed 3 mm
```

Presence rescue只能使用本CARE branch的coarse extent及所选direct threshold的下一低一级阈值。

共享checkpoint选择：先要求scar/edema独立decode均有非空预测、无新增infinite HD、remote FP和empty安全；再按以下固定顺序排序：

1. 最大化 `min(scar Dice delta, edema-zone Dice delta)`；
2. 最大化两者平均Dice delta；
3. 最小化两者平均HD95 ratio；
4. 更早checkpoint。

不得由Executor创建额外阈值、utility、病例级手工规则或单病理checkpoint。

## 10. Fold1 outer一次性访问锁

W4训练与inner selection进程必须通过deny-list禁止读取fold1 outer labels/predictions。生成：

```text
split_freeze_receipt.json
inner_decode_freeze_receipt.json
outer_access_guard.json
```

Outer evaluator必须：

- 只有在inner freeze receipt hash匹配后才启动；
- 创建atomic `OUTER_EVALUATION_STARTED.lock`；
- 已存在lock时拒绝第二次运行；
- 写入每个outer文件读取记录和唯一command/hash；
- outer完成后任何参数、checkpoint、alignment或decode变化均使结果失效，且不得重评fold1。

Clean gate的Dice/HD95/help-harm使用complete-trimodal、GT-positive病例；all-case结果仅作robustness，empty-empty Dice不得制造promotion。

Help/harm定义：Dice delta `>=+0.005`为help，`<=-0.005`为harm，其余neutral。

## 11. W6 full-data确定性规则

Full-data不得自行选择checkpoint。若fold1 inner选择step为 `s`：

```text
full_data_step = round_to_nearest_500(9000*s/7000), clamp [500,9000]
```

使用fold1冻结的alignment、threshold、component、presence-rescue和TTA。Full-data pathology forward仍只读原始模态+availability；五折nnU-Net ensemble只生成最终0-3类标签。

仅当：

```text
time_left >= 1.25 * W4_median_seconds_per_optimizer_step * 9000 + 7200 seconds
```

才启动W6；否则记录 `FULL_DATA_DEFERRED_ALLOCATION_TIME_GUARD`，不得新建job。

## 12. Controller反偷懒责任

每个wave后Controller必须亲自检查git diff、关键symbol、训练命令和真实输出，不能只相信Executor报告或validator status。必须拒绝：

- tiny/stub encoder或参数量不足；
- z=8/slab训练冒充full volume；
- nnU-Net context进入病理forward；
- burden head未调制decoder；
- inner病例混入actual-train；
- balanced采样静默fallback；
- short smoke冒充正式steps；
- evaluator读取outer多次或先于freeze；
- validator只读预写status；
- W3机制失败仍盲目进入W4；
- clean失败后在同一outer上调参；
- runtime push、额外Slurm job或并行GPU。

普通实现、OOM、resume、cache、评估和validator错误属于同范围修复。架构/科学合同变化必须返回Planner，不得由Controller或Executor临时设计。