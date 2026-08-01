# CARE 完整三模态四模型竞速缺口闭合蓝图

**日期：2026-08-01**

## 1. Planner 结论

最新 gap packet 的大方向正确：`M1/M2/M3` 尚未接受正式科学检验，不能写成模型失败；但它对 `M0` 的解释仍然过于乐观。`M0` 虽完成 4000 optimizer steps 和 fold2/fold3 outer 评价，却没有执行上一版蓝图冻结的微调合同：实际 trainer 继承默认 nnU-Net `SGD(lr=1e-2, momentum=0.99)` 与 16-epoch PolyLR，而冻结合同要求 `AdamW`、backbone/decoder `1e-4`、head `5e-4`、250-step warmup、4000-step cosine；它也没有对 500-step checkpoints 做预声明的 full-volume inner selection，只直接使用 stock `checkpoint_best.pth` 语义。因此旧 M0 只能说明“高学习率、短周期 stock recipe 在目标域子集上伤害基线”，不能作为忠实 target-domain fine-tune negative。

本轮值得继续，并且必须一次闭合四条 lane：

```text
M0R  faithful target-domain nnU-Net control
M1   MYOPSNET-L-CARE
M2   I-MMSEG-CARE
M3   CARE-TDS
```

本轮不设计第五个模型，不把旧失败组件拼成新系统，不访问 official validation，不上传 Docker。任务是把前一轮偷懒停止的实现补齐并跑出同一 fold2/fold3 协议下的最终本地成绩。

## 2. 已读图与可继承原则

Planner 已视觉读取 `SRR-v2`、`SRR-v2.5`、`SRR-v3`。保留的原则：

```text
modality-specific evidence
scar / edema pathology-specific authority
soft anatomy context
negative-space accounting
full-volume help/harm, HD95 and remote-FP gates
```

本轮不恢复：

```text
dictionary / prototype / router
proposal-refiner cascade
bounded residual correction
hard wall coordinates
component-query noisy-OR
```

这些机制可以在以后统一模型设计时重新审查，但不得进入当前四模型 gap closure。

## 3. 真实状态修正

### 3.1 M0 旧结果

旧 M0 outer 结果：

```text
edema delta vs stock: -0.034462
scar delta vs stock:  -0.043167
```

该数值真实，但实验合同不忠实。必须先生成 `m0_protocol_fidelity_audit.json`，逐项绑定：

```text
actual optimizer class
actual initial LR
actual scheduler
actual epoch/step mapping
checkpoint cadence
checkpoint selection metric
full-volume inner evaluations performed
batch descriptor evidence
```

只有修复后的 `M0R` 可作为本轮 control。旧 M0 保留为 `HIGH_LR_SHORT_FINETUNE_NEGATIVE`，不得删除。

### 3.2 M1

旧本地 MyoPS-Net 主要在缺模态混合 fold0 上评价，且 CARE wrapper、slice-to-volume reconstruction 和 strict full-volume evaluator 不完整。其失败不能替代本轮完整三模态复现。

### 3.3 M2

旧 lane 只确认官方资产缺失。模型未 forward、未训练、未评价。官方 source commit 固定：

```text
zzzzzzl24/I_MMSeg@90f46c4eb72924509895fcda6bc6a3b8c3316e66
```

### 3.4 M3

stock fold2/fold3 parity 已通过，但 independent pathology heads、losses 和 formal training 均未实现。它仍是最高优先级、无需外部资产的 candidate lane。

## 4. 固定数据与评价合同

```text
Dataset: Dataset501_CAREMyoPS
input order: [LGE, T2, C0]
formal population: complete tri-modal only
complete cases: CenterB 35 + CenterC 45 = 80
formal outer folds: fold2 and fold3
scar: label 5
pure edema: label 4
injury support: labels 4|5
anatomy target: label4/5 remapped to myocardium label1; labels2/3 retained
```

沿用并重新 hash：

```text
results/20260801_care_target_domain_pathology_specialist_race/split_receipt.json
```

不得改变病例 membership。fold2 outer 必须含 `Case3008/Case2019/Case2034`；fold3 outer 必须含 `Case3009/Case2021`。

Outer 已被旧 M0 访问。为避免继续污染：

- M0R/M1/M2/M3 的 checkpoint、threshold、source selection只能使用 actual-train 与 inner；
- outer 只按冻结 checkpoint/decode做一次 deterministic replay；
- 不因 outer 结果修改模型或阈值；
- packet 必须标记 `outer_previously_accessed_for_old_M0=true`，因此本轮 outer 是受限开发证据，不是 clean final test。

## 5. M0R：忠实目标域 nnU-Net control

### 5.1 模型

- exact fold-specific stock `PlainConvUNet`；
- 完整 encoder、bottleneck、decoder、deep-supervision heads加载；
- parameter-byte coverage `>=0.99`；
- step0 FP32 logits `max_abs_error <=1e-6`；
- 不改六类 architecture、loss semantics或 official decode。

### 5.2 训练

M0R 与 M3 使用同一 deterministic batch descriptor manifests：

```text
batch_manifest_fold2.jsonl
batch_manifest_fold3.jsonl
```

每条 descriptor 固定：

```text
optimizer_step
accumulation_index
case_id
crop_center_zyx
crop_start_zyx
crop_end_zyx
sampling_stratum
flip_z/flip_y/flip_x
gamma
brightness_multiplier
gaussian_noise_std
seed
```

Sampling strata：

```text
30% scar-positive component-centered
30% injury/pure-edema-positive centered
20% actual-train clean-OOF remote/blood-pool hard negative
20% random myocardium/foreground
```

M0R/M3 必须读取同一 descriptor bytes，manifest SHA256 完全相同。

训练合同：

```text
optimizer: AdamW
backbone+bottleneck+decoder lr: 1e-4
segmentation heads lr: 5e-4
weight_decay: 1e-4
optimizer steps: 4000
physical batch: 2
gradient accumulation: 2
effective batch: 4
warmup: 250 optimizer steps
scheduler: cosine per optimizer step to 1e-6
gradient clip: 12
mixed precision: bf16 on H100/A100, fp16 on V100
checkpoint: every 500 steps
```

每个 500-step checkpoint必须 reload 后，对 inner 全体积评价。M0R checkpoint selection：

```text
primary: maximize mean(scar Dice, pure-edema Dice)
tie if <=0.005: lower mean(scar HD95, edema HD95)
next tie if <=1 mm: lower summed remote-FP volume
final tie: earlier step
```

## 6. M1：MYOPSNET-L-CARE faithful adaptation

Official source：

```text
QJYBall/MyoPS-Net@479f07028c5bdb12b405dc92212aa48ae6ba947a
```

必须记录 source diff；不得只沿用旧 wrapper。

### 6.1 输入与核心模块

- only C0, LGE, T2；
- no T1/T2* placeholder enters forward；
- modality-specific encoders；
- official cross-modal fusion；
- myocardium prior/consistency；
- pathology-specific scar and injury branches。

为保留论文 inclusiveness 语义并匹配 CARE labels：

```text
scar target = label5
injury target = label4|5
final pure edema = injury prediction AND NOT scar prediction
```

不得把 scar 强制包含在 pure-edema label4 中，也不得禁用所有 pathology relation loss。

### 6.2 CARE adapter

必须实现：

```text
split-bound CARE exporter
2D slice list with exact case/z provenance
original spacing/orientation receipt
slice prediction -> full-volume reconstruction
compact CARE label decode
canonical evaluator integration
```

训练：

```text
input size: 192x192
optimizer: official Adam
base lr: 1e-4 at effective batch16
H100: physical batch16
V100: physical batch8 + accumulation2
minimum epochs: 60
maximum epochs: 120
checkpoint/full-volume inner eval every 10 epochs
no early stop before epoch60
```

Pathology-specific checkpoint selection分别冻结：

```text
scar checkpoint: max inner scar Dice; tie lower HD95, then lower remote FP, then earlier epoch
edema checkpoint: max inner pure-edema Dice; tie higher sensitivity, then lower HD95, then earlier epoch
```

## 7. M2：I-MMSEG-CARE faithful adaptation

Official source：

```text
zzzzzzl24/I_MMSeg@90f46c4eb72924509895fcda6bc6a3b8c3316e66
```

必须保留：

```text
CLIP-based prior encoder
fixed modality-specific intensity-prior text embeddings
intensity-prior-guided cross-modal feature enhancement
class feature modulation
TransUNet/R50-ViT-B16 core
```

禁止用手工 rank 通道或普通 U-Net 冒充。

### 7.1 资产边界

自动尝试公开资产：

```text
R50-ViT-B_16.npz
epoch_299.pth
I_MMSeg_env.tar.gz if dependency isolation requires it
```

公开 CARE rules允许公开 external data和open pretrained models。若 `epoch_299.pth` 使用公开 MyoPS380 labels，必须在 receipt 中记录外部数据/权重 provenance；不得训练或读取未公开的私有 annotation。

如果 Google Drive 要求人工批准：

```text
M2 status = ASSET_APPROVAL_REQUIRED
```

M2停止，但M0R/M1/M3继续。不得生成 lite substitute。

### 7.2 CARE adaptation

```text
input = C0/LGE/T2
scar target = label5
injury target = label4|5
pure edema decode = injury AND NOT scar
fixed text prompts from official source; no runtime GPT call
CARE fold2/fold3 exporter and full-volume reconstruction
```

训练：

```text
input size: 128x128 as official configuration
optimizer/base lr: official config
minimum epochs: 60
maximum epochs: 120
checkpoint/full-volume inner eval every 10 epochs
selected checkpoint reload required
```

Scar/edema checkpoint selection与M1相同。

## 8. M3：CARE-TDS implementation contract

### 8.1 主体与 heads

- same exact fold stock PlainConvUNet as M0R；
- intercept final full-resolution decoder feature `F0`；
- concatenate detached soft myocardium and LV probabilities；
- full encoder/decoder low-LR trainable；
- stock classes4/5 logits禁止进入final prediction。

Head input：`concat(F0, p_myo_detached, p_lv_detached)`。

每个 head：

```text
Conv3d(C+2,64,3,padding=1)
GroupNorm(8,64)
SiLU
ResidualBlock3d(64)
Conv3d(64,out_channels,1)
```

Heads：

```text
scar_head: 1 channel
pure_edema_head: 1 channel
injury_head: 1 channel
boundary_head: 2 channels (scar signed distance, injury signed distance)
```

初始化：scar/pure-edema第一层使用Kaiming，final classifier分别拷贝stock class5/class4 weight可兼容部分并记录；injury final classifier初始化为stock class4/class5均值；boundary final层零初始化。

Final output：

```text
scar_prob = sigmoid(z_scar)
pure_edema_prob = sigmoid(z_pure)
scar = scar_prob >= 0.5
pure_edema = pure_edema_prob >= 0.5 AND NOT scar
anatomy = stock anatomy logits classes0-3 where pathology absent
```

### 8.2 Targets

```text
scar = label5
pure edema = label4
injury = label4|5
anatomy = label4/5 -> label1
signed distance: EDT(outside)-EDT(inside), clipped to ±10mm and divided by10
```

### 8.3 Loss

```text
L_anatomy = DiceCE on 0/1/2/3 anatomy target
L_scar_dense = Dice + Focal(alpha=.25,gamma=2)
L_scar_cat = component-weighted Tversky(alpha=.3,beta=.7)
L_scar_mil = positive-component max-pool BCE + hard-negative-component max-pool BCE
L_remote = mean scar probability on declared safe remote/blood-pool hard-negative masks
L_pure = Dice + Focal
L_injury = Dice + Focal
L_boundary = SmoothL1(tanh(z_boundary), normalized signed distance)
L_relation = mean(relu(max(p_scar,p_pure)-p_injury))

L_total = 1.0 L_anatomy
        + 1.0 L_scar_dense
        + 0.30 L_scar_cat
        + 0.20 L_scar_mil
        + 0.10 L_remote
        + 1.0 L_pure
        + 0.50 L_injury
        + 0.20 L_boundary
        + 0.10 L_relation
```

Component weight：

```text
w_k = clip(sqrt(1000 mm3 / max(volume_k,1 mm3)), 1, 4)
```

Hard negatives只从 actual-train 构建：

```text
clean-OOF stock remote-FP components >5mm from GT scar
LV blood-pool high-LGE components
high-LGE components outside soft myocardium and >5mm from GT scar
```

每类 loss必须有独立 on/off gradient和final-label intervention。

### 8.4 训练

与M0R完全相同的 batch manifests、optimizer steps、parameter-group LRs、scheduler和checkpoint cadence。M3 checkpoint分别按scar与edema inner规则冻结；不得用outer选择。

## 9. 统一评价

每个正式 lane、每个fold、每个selected pathology checkpoint都必须 full-volume评价：

```text
Dice
HD95 mm
exact HD mm
precision
sensitivity
lesion recall
small-lesion recall
remote FP count/volume
blood-pool-adjacent FP
component count
volume ratio
case-wise help/harm vs stock and M0R
CenterB/CenterC subgroup
```

固定 sentinel cases：

```text
Case3008
Case3009
Case2019
Case2034
Case2021
```

全局 source selection只用fold2+fold3 inner汇总：

Scar：max Dice；差<=.01选低HD95；差<=1mm选低remote FP；再选高sensitivity。

Edema：max Dice；差<=.01选高sensitivity；差<=.02选低HD95；再选volume ratio更接近1。

Final composition使用fold-specific stock anatomy + frozen global scar source + frozen global edema source + scar priority。禁止per-case/per-fold selector。

## 10. 调度合同：interactive持续占用 + htzhulab队列接力

只复用现有RUNNING interactive allocation，不新建interactive allocation。允许为尚未运行的完整 lane提交 `htzhulab` queued jobs。

优先顺序：

```text
interactive lane 1: M3
then takeover order: M0R -> M1 -> M2
```

所有通过preflight的非当前interactive lane先提交到`htzhulab`：

```text
one job per lane, each job runs fold2 then fold3
partition=htzhulab
gpu=1
cpu=12
mem=96G
time=12h
```

每个lane使用原子claim：

```text
/users/a/e/aereinh/.locks/care_td_gap_closure_20260801/<lane>.claim
```

queued job和interactive takeover必须先原子获取claim；loser写`RACE_LOST`并退出，zero training credit。

当当前interactive lane完成：

1. 按 `M0R -> M1 -> M2` 检查状态；
2. 若lane job `PENDING`，执行`scancel`并等待`sacct`确认`CANCELLED`；
3. interactive allocation通过`srun --jobid --overlap --exclusive --gres=gpu:1`运行该lane；
4. 若queue job已`RUNNING`且持有claim，不重复运行，interactive转下一个pending lane；
5. 若queue job `COMPLETED`，直接转下一个；
6. 若queue job startup失败，在同范围修复后优先用空闲interactive exact resume；
7. 重复直到所有eligible lanes terminal。

不得因为queue pending让interactive GPU空闲。不得提交a100-gpu/volta-gpu，不得再申请`salloc`。

M2资产未通过时不得提交GPU job。

## 11. 继续/停止判据

每个lane只有在implementation gate完整通过后才有formal training credit。允许终态：

```text
TARGET_DOMAIN_CANDIDATE_READY
SCAR_ONLY_CANDIDATE_READY
EDEMA_ONLY_CANDIDATE_READY
NO_GO_AFTER_FAITHFUL_FOUR_LANE_EVALUATION
M2_ASSET_APPROVAL_REQUIRED_OTHER_LANES_COMPLETE
OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST
OPERATIONALLY_BLOCKED_IMPLEMENTATION
```

Candidate gate相对fold-specific stock baseline：

Scar：Dice `>=+0.02`、HD95 `<=+2mm`、remote FP `<=1.10x`、harm `<0.40`，且Case3008/3009至少一例改善`>=0.10`、另一例不恶化超过0.03。

Edema：Dice `>=+0.02`、sensitivity `>=+0.03`、precision `>=-0.05`、HD95 `<=+2mm`、harm `<0.40`，且Case3008/3009至少一例Dice`>=0.25`、Case2034 volume-ratio error改善。

本轮不授权official validation、Docker或hosted claim。

## 12. Validator 必须拒绝

1. 将旧M0写成faithful negative；
2. M0R继续使用SGD 1e-2/16-epoch PolyLR；
3. M0R/M3 batch manifest hash不同；
4. M1缺少CMFF/MPC或用缺模态病例；
5. M1把pure edema直接当论文inclusive edema；
6. M2用rank通道冒充I-MMSeg；
7. M2无source/asset/license/provenance；
8. M3读取stock label4/5 final logits；
9. M3 loss只声明不进入total；
10. hard-negative字符串存在但mask/loss无直接梯度；
11. patch proxy冒充full-volume；
12. checkpoint未reload；
13. outer用于选择；
14. per-case/per-fold selector；
15. queue job与interactive重复训练同lane；
16. pending job冒充terminal；
17. interactive空闲但仍有pending eligible lane；
18. M2资产失败阻塞全部lane；
19. runtime/checkpoint/NIfTI进入Git；
20. push前通知或推送task branch；
21. 自动访问official validation/upload/Docker。

## 13. 终态提交与通知

所有eligible lane terminal、aggregation、atlas、mapper、validator和known-bad完成后：

```text
commit: experiment: complete faithful target-domain four-lane gap closure
push: HEAD:main only
force push: forbidden
```

验证remote SHA后写`notification_brief.json`，运行既有：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

完成或真实阻塞均必须notify。