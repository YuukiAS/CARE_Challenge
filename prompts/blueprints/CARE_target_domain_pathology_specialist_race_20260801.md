# CARE 完整三模态病种专属模型并行竞速蓝图

**日期：2026-08-01**

## 1. 决策结论

本轮不再进行宽泛 Deep Research，也不再围绕 SRR、PRISM、MyoWall 或 CARE-QIF v2 继续加模块。当前更有价值的是一次定向、可比较、病例驱动的模型竞速：在同一完整三模态训练/选择/外层病例上，并行训练一个强目标域 nnU-Net 控制、一个 CARE 适配的 MyoPS-Net-L、一个官方 I-MMSeg 适配，以及一个基于完整 nnU-Net 解码器的 CARE 病种专属稠密模型。

目标不是证明某个新名词成立，而是回答两个 leaderboard-facing 问题：

1. scar 能否从历史最好 `0.6258` 和 MoSAIC `0.6965` 的区间，向当前第二梯队 `0.7323` 靠近；
2. edema 能否保住历史 nnU-Net `0.6691` 的高召回优势，并向当前第二梯队 `0.7258–0.7324` 靠近，而不是重复 MoSAIC `0.6255 / SEN 0.5760` 的保守漏检。

Leaderboard 数字只作为 hosted 边界，不参与本地 checkpoint、阈值或模型选择。来源固定为：

```text
results/20260801_mosaic_leaderboard_live_snapshot/leaderboard_snapshot.md
results/leaderboard/care2026_myocardium_latest.json
```

## 2. 为什么现在不再做宽泛深度研究

已有证据已经把问题压缩到足够具体：

- 原始 LGE 对 scar 的跨中心判别信号明确存在；失败的是手工 rank-composite 必须优于 raw 的假设。
- 原始 T2 对 injury 的跨中心判别信号也存在；失败的是过严 AUPRC-lift 门和当前下游结构。
- 当前 component-query 的 noisy-OR 只能增加阳性，不能删除 dense 假阳性；实际 query on/off 对绝大多数病例几乎不改变 lesion recall。
- A0–A3、MMRD 和 PRISM 说明，decoder reset、弱 residual、patch-only 评价和不充分负空间约束都会伤害全体积结果。
- MyoWall 说明 hard geometry 不能作为病理唯一入口。
- 本地旧 MyoPS-Net fold0 基线混入大量缺模态病例，且采用 2D slice training；它不能回答完整三模态目标域中 MyoPS-Net-L 是否仍有竞争力。

因此本轮是“定向复现 + 一个病例驱动的新稠密模型”，不是再搜更多概念。

## 3. 图像与历史路线约束

规划已视觉读取 SRR-v2、SRR-v2.5、SRR-v3。图中可保留的原则是：

```text
modality-specific evidence
pathology-specific scar/edema authority
soft anatomy context
negative-space accounting
full-volume help/harm and HD95 gates
```

本轮明确不复用：

```text
shared/private/interaction dictionary
prototype memory
sparse router
soft-ROI cascade
bounded nnU-Net residual correction
hard wall coordinates
query/noisy-OR final composition
```

这些模块在当前本地证据中没有形成稳定增益，不能再作为主线入口。

## 4. 病例驱动目标

正式开发外层只使用 canonical `splits_final.json` 的 fold 2 和 fold 3 中完整三模态病例。选择这两个 fold 不是为了挑容易结果，而是因为它们覆盖当前最关键的真实失败病例：

### Fold 2 关键病例

- `Case3008`：CenterC，历史 scar/edema 接近全零；检验跨中心病理感知是否恢复。
- `Case2019`：CenterB，历史模型出现远端大块病理假阳性；检验全体积负空间约束。
- `Case2034`：CenterB，edema 范围和边界不稳定；检验 injury/pure-edema 双目标。

### Fold 3 关键病例

- `Case3009`：CenterC，历史 scar/edema 接近全零；检验恢复是否可重复。
- `Case2021`：CenterB，基线已有合理 pathology；检验新模型是否破坏已正确病例。
- `Case2018` 及 fold3 其他完整病例：作为非定向全体积帮助/伤害人群。

`Case3012`、`Case2035` 等不在 fold2/3 外层的病例只作为历史 atlas 背景，不能用见过其标签的模型重新评价并写成 held-out 结果。

## 5. 固定数据合同

```text
Dataset: Dataset501_CAREMyoPS
input order: [LGE, T2, C0]
complete tri-modal total: 80
centers: CenterB=35, CenterC=45
primary scar: label 5
primary pure edema: label 4
auxiliary injury zone: labels 4|5
myocardium union: labels 1|4|5
```

每个正式 fold：

1. outer：canonical fold2 或 fold3 validation 中的完整三模态病例；
2. development pool：该 fold training 中的完整三模态病例；
3. inner selection：从 development pool 按 `center × scar-volume quartile × injury-volume quartile` 确定性抽取 20%，seed `20260801`；
4. actual train：剩余 80%；
5. outer 只在 checkpoint 和全局 decode 冻结后评价一次。

本轮正式训练不使用 LGE-only 或 LGE+C0 病例。它们已经通过原 stock nnU-Net checkpoint 提供共同预训练背景，但不得进入本轮目标域 fine-tune，从而避免 missingness/center shortcut 再次主导模型。

## 6. 四个并行模型

### M0：TD-NNUNET，完整三模态强控制

用途：检验“只做完整三模态目标域 fine-tune”本身能带来多少收益，并提供所有模型的同划分强控制。

结构：

- exact `PlainConvUNet` from `nnUNetPlans.json`；
- 加载对应 fold 的 stock checkpoint，参数字节覆盖率 `>=0.99`；
- FP32 stock-logit parity `max_abs_error <=1e-6`；
- 完整 encoder、bottleneck、decoder、segmentation heads 全部保留；
- 六类输出和 official scar-priority decode 不变；
- 不新增 loss、后处理、TTA 或 ensemble。

### M1：MYOPSNET-L-CARE，CARE 适配的论文复现

用途：重新回答旧 MyoPS-Net 失败是否主要来自缺模态训练和 wrapper，而不是其 pathology-specific fusion 本身。

必须保留论文核心：

- C0/LGE/T2 modality-specific encoders；
- layer-level cross-modal feature fusion；
- scar 与 edema pathology-specific output branches；
- myocardium prior and consistency；
- strict CARE `label4=pure edema`, `label5=scar`。

禁止：

- T1/T2* 零占位进入网络；
- no-T2 样本进入本轮训练；
- 把 edema union 冒充 pure edema；
- 旧 compact wrapper 指标冒充 canonical full-volume 结果。

该 lane 是性能复现，不与 M0/M3 声称参数匹配或因果消融。

### M2：I-MMSEG-CARE，官方强度先验方法适配

用途：验证 published intensity-prior feature recalibration 是否能把已存在的 raw LGE/T2 信号转成稳定分割，而不是继续使用失败的手工 rank-composite。

必须：

- 使用官方 `zzzzzzl24/I_MMSeg` 代码或逐文件等价 first-party port；
- 固定官方 source commit、license、依赖和 BiomedCLIP/文本编码资产 SHA256；
- 使用论文固定的 modality-specific intensity-order 与 boundary prior 文本，不在 runtime 调用 GPT；
- 保留 intensity-prior-guided cross-modal feature enhancement 与 class feature modulation；
- 适配为 C0/LGE/T2 和 CARE label 4/5；
- 所有外部权重必须是规则允许的公开预训练资产，并记录 provenance。

禁止仅把手工 rank 通道加到 U-Net 后称作 I-MMSeg。

若官方资产无法下载、许可证不清或代码无法 faithful forward，该 lane 写 `LANE_BLOCKED_EXTERNAL_ASSET`，其余 lanes 继续；不得伪造一个 lite 版本。

### M3：CARE-TDS，完整解码器上的病种专属稠密模型

用途：直接针对当前病例缺口，而不是重新建 decoder、query 或 hard geometry。

共同主体：

- 与 M0 相同的 fold-specific stock `PlainConvUNet` 完整权重；
- 完整 encoder/decoder 保留并低学习率微调；
- anatomy classifier 保留 stock 初始化；
- pathology final authority 由新 heads 独立产生，不读取 stock label4/5 logits，不做 residual add。

Scar head：

- 1×1×1 binary head，从 stock label5 classifier 权重初始化；
- `L_scar = DiceCE + 0.30 * ComponentAdaptiveTversky + 0.20 * LesionMIL + 0.10 * SafeRemoteFPLoss`；
- GT scar 使用 26-connectivity 3D components；
- small lesion 固定 `<1000 mm3`；
- OOF stock scar FP manifest 只由 actual-train cases 构建；
- sampler：50% scar-positive，25% stock remote/blood-pool FP，25% random full-volume patch。

Edema head：

- pure-edema binary head，从 stock label4 classifier 权重初始化；
- injury auxiliary head，从 stock label4/label5 classifier 均值初始化；
- boundary head预测 signed-distance/boundary target；
- `L_edema = DiceCE(pure) + 0.50*DiceCE(injury) + 0.20*BoundaryDT + 0.10*soft_relation`；
- `soft_relation = mean(relu(p_pure - p_injury))`；
- sampler：50% pure-edema/injury positive，25% injury boundary，25% random。

Final decode：

```text
scar = sigmoid(z_scar) >= 0.5
pure_edema = sigmoid(z_pure_edema) >= 0.5 AND NOT scar
anatomy = M0-style anatomy classes where pathology is absent
scar priority is fixed
```

不允许 hard myocardium clipping；soft anatomy probability可作为 feature，但不能把 pathology 概率乘成零。

## 7. 训练合同

### M0 与 M3 的 matched contract

每个 fold：

```text
optimizer: AdamW
backbone/decoder lr: 1e-4
classifier/new-head lr: 5e-4
weight_decay: 1e-4
optimizer steps: 4000
physical batch: stock nnU-Net plan value
accumulation: enough for effective batch 4
warmup: 250 steps
cosine minimum lr: 1e-6
checkpoint and inner full-volume evaluation: every 500 steps
seed: 20260801 + fold
bf16: enabled on H100/A100
checkpoint selection: all 8 checkpoints, inner only
```

M0/M3 必须重放同一病例顺序、同一 crop、同一空间增强、同一强度增强、同一 batch descriptor manifest。M3 可因 additional heads 使用不同 loss，但不得改变输入病例或增强。

### M1 与 M2

- 使用同一 actual-train / inner / outer case IDs；
- 最少 60 epochs，最多 120 epochs；
- 每 10 epochs 保存并在 inner 做完整病例重建评价；
- 训练至少 60 epochs，不能用 early-stop 在 60 之前结束；
- checkpoint selection只看 inner；
- paper-default optimizer/augmentation优先，任何 CARE 适配必须记录；
- outer只在 selected checkpoint reload 后评价一次。

## 8. 并行计算合同

本轮只允许复用用户现有 RUNNING interactive Slurm allocation。

严格禁止：

```text
salloc
sbatch
任何新 Slurm allocation/job
```

Controller 必须读取现有 allocation 的 `AllocTRES`、剩余时间和可见 GPU。正式 race 要求：

```text
available GPUs >= 4
remaining walltime >= 10 hours
```

四个 executor 各占一个独立 GPU，使用同一 allocation 内的 `srun --jobid ... --overlap --exclusive --gres=gpu:1` step。四个模型 lane 必须同时开始；不得因为 GPU 不足偷偷改成串行。资源不足时写：

```text
OPERATIONALLY_BLOCKED_EXISTING_ALLOCATION_INSUFFICIENT
```

随后提交阻塞 packet、push main、notify，不得申请新 job。

每个 executor 使用本地独立 branch/worktree；这些 branch 只用于并行隔离，禁止推送远端。Controller 按固定顺序合并：M0 -> M1 -> M2 -> M3 -> integration/finalizer。

## 9. 评价与全局病种组合

Canonical evaluator 必须对 fold2+fold3 完整三模态 outer 汇总：

```text
Dice
HD95 mm
exact HD mm
precision
sensitivity/recall
lesion recall
small-lesion recall
remote FP count and volume
blood-pool-adjacent FP
component count
volume ratio
case-wise help/harm
CenterB/CenterC subgroup
```

### Scar source selection

在两个 fold 的 inner 结果合并后，从 M0/M1/M2/M3 选择一个全局 scar source：

1. scar Dice最高；
2. 若差值 `<=0.01`，HD95更低者优先；
3. 若 HD95差值 `<=1 mm`，remote FP volume更低者优先；
4. 再以 sensitivity 更高者优先。

### Edema source selection

同样只用合并 inner：

1. pure-edema Dice最高；
2. 若差值 `<=0.01`，sensitivity更高者优先；
3. 若 sensitivity差值 `<=0.02`，HD95更低者优先；
4. 再以 `abs(volume_ratio-1)` 更小者优先。

选出的 scar/edema source 固定后，使用 M0 anatomy 做统一 scar-priority composition，再对 fold2+fold3 outer 评价一次。不得 per-case 选择模型，不得 outer-driven threshold 或 source selection。

## 10. 科学门

### Scar promotion gate

相对同病例 M0：

```text
pooled Dice delta >= +0.02
pooled sensitivity delta >= 0
pooled lesion recall delta >= +0.03 OR small-lesion recall delta >= +0.10
HD95 delta <= +2 mm
remote FP volume <= M0 * 1.10
harm fraction < 0.40
Case3008 Dice >= 0.30 and improves M0 by >=0.10
Case3009 Dice >= 0.30 and improves M0 by >=0.10
```

### Edema promotion gate

```text
pooled pure-edema Dice delta >= +0.02
pooled sensitivity delta >= +0.03
precision delta >= -0.05
HD95 delta <= +2 mm
harm fraction < 0.40
Case3008 pure-edema Dice >= 0.25
Case3009 pure-edema Dice >= 0.25
Case2034 volume-ratio error improves versus M0
```

### Combined candidate gate

只允许以下终态：

```text
TARGET_DOMAIN_CANDIDATE_READY
SCAR_ONLY_CANDIDATE_READY
EDEMA_ONLY_CANDIDATE_READY
NO_GO_TARGET_DOMAIN_RACE
OPERATIONALLY_BLOCKED_EXISTING_ALLOCATION_INSUFFICIENT
OPERATIONALLY_BLOCKED_ASSET_OR_IMPLEMENTATION
```

`TARGET_DOMAIN_CANDIDATE_READY` 要求 scar 与 edema 都通过。即使通过，本任务也不授权 official validation upload、Docker 或 hosted claim，只产出可供用户下一步打包的模型/配置清单。

## 11. 必须产出的病例图册

固定包含：

```text
Case3008
Case3009
Case2019
Case2034
Case2021
```

另外加入 scar 最大 help/harm 各 3 例、edema 最大 help/harm 各 3 例，去重不超过 17 例。

每例显示：

```text
LGE / T2 / C0
GT
stock fold nnU-Net
M0 TD-NNUNET
M1 MYOPSNET-L-CARE
M2 I-MMSEG-CARE or explicit LANE_BLOCKED
M3 CARE-TDS
final composed candidate
scar FP/FN
edema FP/FN
```

图册必须视觉检查病例、切片、方向、标签和模型来源一致。

## 12. 禁止重复的失败方式

Strict validator 必须拒绝：

1. 新 decoder 或 encoder-only inheritance冒充完整模型；
2. M0/M3 batch manifest不一致；
3. M1继续混入缺模态病例；
4. I-MMSeg被替换成手工rank通道；
5. stock pathology logits进入M3 final composition；
6. patch proxy冒充full-volume；
7. outer用于checkpoint、阈值或source selection；
8. per-case model selector；
9. no-T2进入正式race；
10. remote FP/harm缺失；
11. Case3008/3009未单独报告；
12. 只报告Dice而不报告HD95/PRE/SEN；
13. 只写paper name但未实现核心模块；
14. 训练不足60 epochs或M0/M3不足4000 steps；
15. checkpoint未reload；
16. 新建Slurm job；
17. 四模型因GPU不足改串行；
18. runtime/checkpoint/NIfTI提交Git；
19. 未push main就发送完成邮件；
20. 自动上传official validation或Docker。

## 13. 推送与通知

Controller 终态必须：

1. 所有 GPU steps terminal；
2. aggregation、atlas、strict validator、known-bad 完成；
3. 轻量代码/配置/结果 commit；
4. rebase 最新 `origin/main`；
5. push `HEAD:main`，禁止推送 task branch；
6. 验证 local SHA == remote main SHA；
7. 写 `notification_brief.json`；
8. 调用既有 `controller_notifications/notify_goal_watcher.py --once`；
9. notifier receipt 若产生，再 commit/push main 并重新验证 SHA。

完成或真实阻塞都必须通知。