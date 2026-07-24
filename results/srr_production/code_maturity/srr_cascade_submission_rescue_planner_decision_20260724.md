# 截止日前只做一件事：以强基线为底座，分别救 scar 与 edema

## 结论

当前最合理的 submission rescue 不是继续 CARE-MMRD，也不是恢复旧 SRR 全链，而是把已经得到证据支持的机制收束成一个小而可回退的系统：以 nnU-Net 作为冻结六类分割底座、解剖上下文和病种级 fallback；以现有完整三模态 CARE-MMRD checkpoint 提供水肿、解剖与共享特征；以干净的 cross-fitted 病种原型提供正负证据；最后由 scar 与 edema 两个独立轻量头只修改对应病理通道。任一病种未通过独立 audit 门时，最终输出保留该病种的 nnU-Net。

这是一条用户显式重新授权的主线，不是 Batch11，不恢复 Batch9 Wave6，不重开 Route A/B/C，也不推翻 Batch10 对 CARE-MMRD 直接六类分割路线的终止判断。Batch10 的终止仍成立；本任务改变的是模型边界：重新授权 nnU-Net 作为冻结 anchor/context/fallback，并恢复 SRR-v3 的病种专属、有界纠错。

## 规划绑定

```text
repository: YuukiAS/CARE_Challenge
branch: main
planning_base_commit: cf65a109e06eeabec2a900bd789c431b03c985dc
task_key: 20260724_care_myops_srr_cascade_submission_rescue
result_root: results/20260724_care_myops_srr_cascade_submission_rescue
execution_mode: controller_supervised
```

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_objective: observed-modality encoding -> clean pathology evidence retrieval -> anatomy-guided proposal -> bounded nnU-Net correction -> pathology-specific fallback
```

v2/v2.5 已包含模态特异表示、病种 proposal 与 refinement；v3 的决定性增强是让 nnU-Net 成为最终 logits 基底，并把 SRR 限制为有界纠错；CARE-MMRD 则删除了 prototype、proposal、refiner 和 anchor，重新承担整幅六类分割。本次恢复 v3 的安全链，但不恢复旧复杂字典、SIP、arbiter 或遗留输出路径。

## 为什么值得再做一次

Batch10 公平重评后，最佳非 nnU-Net 候选在 audit 上仍低于基线，但并非完全无信号：scar Dice gap 约 -0.022，edema Dice gap 约 -0.029；scar 主要失败在 HD、远端假阳性和病例伤害；完整三模态 teacher 的 edema 已接近同划分 baseline。下一步应保护 anatomy，让 scar 专门学习远端假阳性抑制，让 edema 专门学习 edema∪scar zone，再分别决定是否替换 anchor。

公开强系统中可借的是 anatomy-first cascade、病种专属专家、edema-zone 语义、checkpoint 级组合与连通域安全控制；不得复制 MoSAIC 或其他第三方实现、权重或 hosted 结论。

## 方法与实现边界

内部名称：`CARE-SRR-Cascade`。

目标实现：

```text
src/care_myocardium/models/care_srr_cascade_rescue.py
class CARESRRCascadeRescue
```

允许复用：

```text
CAREMMReliableDistillResEnc frozen source models
nnU-Net five-fold OOF anchor logits/probabilities
Batch10 official sliding-window and inverse-export helpers
Batch10 frozen calibration/audit split
first-party OOF/provenance helpers when semantics match
```

禁止实例化或调用：

```text
SRRProposeRefineMyoPS
ProposalDictionary
M10TwoPassSpatialDictionary
legacy BR2/SIP
source/branch arbiter
production_correction_gate
old propref loss
old Batch7/8 runtime
MoSAIC code or weights
```

旧代码中有用的算法只能提取为新的窄 helper，不得把旧完整 forward 带回生产链。

## 冻结输入源

### nnU-Net anchor

训练病例必须使用五折 OOF anchor；fold0 本地评价使用 fold0 validation logits/probabilities。禁止同病例 in-fold prediction、GT 构造 anchor、随机替代或静默修改 anchor。nnU-Net 在本任务中允许作为 final six-class logit base、soft anatomy/uncertainty context、anchor-error target 与 pathology fallback，但 anchor 自身成绩不得记为 custom gain。

### Frozen CARE-MMRD evidence

Wave0 必须重新核对路径和 SHA256：

```text
feature/anatomy/edema source:
results/20260723_care_myops_batch9_exposed_issues_repair/runtime/seed20260723/teacher_full_view/checkpoint_epoch50.pt
sha256: e92521fccec92d0066f3fa5c076fce16aea3bb02330b940c85321ab4726d1474

scar evidence source:
results/20260723_care_myops_batch9_exposed_issues_repair/runtime/seed20260723/student_reliable_distill/checkpoint_epoch25.pt
sha256: 366722497a47f292e07a0d1c1a3da57c2502b61042bc89b5cfc56b5a89e6a3a0
```

两者只提供 frozen full-resolution features/logits。所有参数、梯度、normalization 状态和 checkpoint hash 在正式运行中必须不变。

## 模型数据流

```text
[LGE,T2,C0] + availability
-> frozen nnU-Net anchor logits z_anchor
-> frozen CARE-MMRD teacher feature/anatomy/edema logits
-> frozen scar-source margin
-> clean four-shard cross-fitted pathology prototype similarities
-> soft myocardium-union, uncertainty and physical distance maps
-> independent scar correction head
-> independent edema-zone auxiliary + pure-edema correction head
-> bounded corrections only on channels 5 and 4
-> six-class argmax
```

最终组合固定为：

$$z^{final}_{0:3}=z^{anchor}_{0:3},$$

$$z^{final}_{scar}=z^{anchor}_{scar}+r_{scar}\,2\tanh(\Delta_{scar}),$$

$$z^{final}_{edema}=z^{anchor}_{edema}+m_{T2}\,r_{edema}\,2\tanh(\Delta_{edema}).$$

`r_scar` 和 `r_edema` 是 soft anatomy union 与物理距离生成的固定支持图，不是 learned gate。scar 支持距离 10 mm，edema 支持距离 15 mm；支持区外 correction 精确为零。无 T2 时 edema logits 与 labels 必须逐体素等于 anchor。

Scar head 输入固定为 teacher feature、LGE、anchor probabilities、teacher anatomy、scar margin、anchor uncertainty、soft union、distance map、scar positive/safe-negative similarity。Edema head 输入固定为 teacher feature、T2/LGE、anchor probabilities、teacher edema/anatomy、uncertainty、soft union、distance map、edema-zone positive/safe-negative similarity。两个 head 均为两层轻量 3D residual block 加零初始化 `1x1x1` correction projection；不重新预测 anatomy。

Edema 辅助目标固定为：

$$Y_{zone}=Y_{edema}\cup Y_{scar}.$$

`zone_aux_logit` 只提供辅助监督；最终仍由 pure-edema correction 修改 channel 4，scar channel 优先独立决定。

## Clean cross-fitted prototype evidence

使用 frozen teacher full-resolution feature 建四个 train shards。训练病例查询时排除自身 shard；validation/inference 使用全部 train shards。所有 bank 必须记录 source cases、shard、feature checkpoint SHA、split/preprocess hash、正负数量和 seed。

Scar positive 是 GT scar；safe negative 包括健康心肌、LV/RV blood、union 外背景及 nnU-Net remote-FP。Edema positive 是 edema∪scar；safe negative 只来自 T2-present 可靠标注病例中的 union 外、blood 与距 zone 至少 10 mm 的心肌。no-T2 myocardium 绝不能成为 edema negative。

Prototype similarity 为 cosine max-over-bank。Bank 冻结，不作为训练参数。Control 与 SRR 仅在 prototype similarity 是否置零上不同，其他所有条件 matched。

## Loss authority

Scar：final-margin BCE+Dice 1.0，anchor-error directional 0.5，confident-anchor preserve 0.1，remote-FP suppression 0.25，surface surrogate 0.1。

Edema：final-margin BCE+Dice 1.0，edema-zone auxiliary BCE+Dice 0.5，anchor-error directional 0.35，confident-anchor preserve 0.1，surface surrogate 0.05。

所有非零 loss 必须作用于 final composed logits 或明确声明的 zone auxiliary output。只监督 raw residual、alias loss、未进 total 的监控项或 disconnected loss 均禁止。每项非零 loss 必须单独 backward；source、anchor、anatomy channels 与未授权模块梯度必须为零。

## 数据、采样与增强

fold0 train 176 例，fold0 val 44 例。固定复用 Batch10 的 22/22 calibration/audit manifest：

```text
results/20260724_care_myops_batch10_deadline_rescue/rescue_split_manifest.csv
```

Audit 不得参与 checkpoint、source、threshold、postprocess、variant 或病种选择。

Sampler 顺序固定为 `target -> eligible center uniformly -> case uniformly -> patch`。Scar target 比例 0.40 positive、0.30 anchor-error hard negative、0.20 anatomy、0.10 background。Edema 比例 0.45 zone-positive、0.35 anchor-error、0.15 anatomy、0.05 background；只从 T2-present、edema-reliable 的 CenterB/CenterC 采样。

Patch size、kernel、stride、data identifier 与 inverse preprocessing 必须从 `nnUNetResEncUNetMPlans` 的 `ConfigurationManager` 解析，禁止硬编码目录或 `20x128x128`。

一个空间变换必须同步作用于 raw images、labels、anchor logits、source logits/features、prototype maps 与 distance maps。强度增强只作用 raw modalities，但需记录空间/强度 seed。任何 student/source/anchor 像素错位均在正式训练前 fail closed。

## 正式对照、训练和选择

固定 seeds：`20260724`、`20260725`。每个 seed 使用一个隔离 Slurm job，内部按顺序运行：

```text
scar_cascade_control
scar_srr_cascade
edema_zone_control
edema_srr_zone_cascade
```

同 seed、同 pathology 的 control/SRR 必须共享 source checkpoint、common-head 初始化、病例/patch序列、空间/强度增强、optimizer、6250 steps、validation cadence、decode 与 evaluator。每组 batch size 1、gradient accumulation 2、AdamW lr `1e-4`、weight decay `1e-4`、cosine 到 `1e-6`；在 1250/2500/3750/5000/6250 评价 calibration 22 例。

Checkpoint 先拒绝 positive-GT empty、no-T2 edema 非零、source hash漂移和 reload 失败，再按 positive-GT Dice delta、exact HD delta、HD95、remote-FP、help-harm 和较早 step 词典序选择。Selection 与 deployment 必须使用同一 composed six-class logits argmax。

## 训练前硬门

正式 Slurm 前必须通过：anchor identity与initial final logits差 `<=1e-6`；channels 0-3 exact identity；no-T2 edema exact identity；source freeze/hash；prototype no-self-shard/no no-T2 leakage；共享空间 fiducial 误差 0；scar/edema 各200-step fixed overfit、loss下降至少30%、预测非空且 correction非零；每个 loss 单独 backward；prototype on/off 和 bank-swap改变 final output；checkpoint roundtrip `<=1e-6`；真实 known-bad 全部非零拒绝。Fixed overfit、smoke 和 preflight 均为 zero formal credit。

## 正式指标与病种独立 audit 门

必须报告 Dice、官方 exact HD、HD95、precision/recall、remote-FP mm³、component、volume ratio、help/harm、empty prediction、changed voxels、CenterB/CenterC、small/large scar、no-T2 safety，并分开 positive-GT 与 all-case-empty-safe populations。

Scar custom branch保留门：audit positive-GT Dice delta `>=0`；exact HD delta `<=0`；HD95 相对恶化 `<=5%`；remote-FP `<=anchor`；help `>=harm`；positive-GT empty `=0`。

Edema custom branch保留门：audit positive-GT Dice delta `>=0`；exact HD delta `<=0`；HD95 相对恶化 `<=5%`；remote-FP `<=1.05*anchor`；help `>=harm`；positive-GT empty `=0`；no-T2 edema voxels `=0`；CenterB 与 CenterC Dice delta 各 `>=-0.005`。

每个病种只能选择：

```text
USE_SRR_CASCADE
USE_CASCADE_CONTROL
FALLBACK_TO_NNUNET
```

至少一个病种 custom 通过时，才允许写 custom/partial custom submission candidate；两病种都失败时只能写 `NO_CUSTOM_RESCUE_USE_BASELINE_ONLY`。不得放宽门槛、用 audit 重选参数、平均 seed 掩盖失败或用 empty-safe Dice 代替 positive-GT。

## 本地 package 边界

只有至少一个 custom pathology 通过 audit，才允许本地生成 submission-ready package：MyoPS 使用 fold0 nnU-Net anchor 加通过的 scar/edema correction，未通过的病种 fallback；Cine 固定使用现有 Dataset502 nnU-Net 五折 inference/ensemble，不做新 Cine 训练。

Dry-run 必须检查 MyoPS 15 例、CineMyoPS 15 例、官方 raw labels `0/200/500/600/1220/2221`、shape/spacing/origin/direction、目录/文件名、两次确定性 hash、container exit 0 与无 GT 访问。允许本地 Docker image 和 manifest；validation/Docker upload 与 hosted claim仍需用户确认。

## Known-bad 与完成边界

Validator必须真实注入并拒绝：in-fold/GT anchor、自身 shard leakage、no-T2 edema非零、anatomy channels变化、source hash错或可训练、空间增强不同步、prototype置零却称 active、audit参与选择、selected checkpoint未reload、selection/deployment decode不同、positive-GT empty仍ready、exact HD缺失仍ready、旧 ProposalDictionary/BR2/SIP进入forward、monitor packet标完成、package标签/几何/case数/目录错误。

Controller是唯一 coordinator/acceptance owner。它监督一个 Executor，逐 Wave 检查真实 diff、hash、运行、Slurm终态、post-completion aggregation、strict validator、Mapper/wiki/CURRENT/fingerprint和本地轻量 commit。普通缺陷必须退回同一 Executor 修复。训练依赖用 `afterok`，finalizer/accounting用 `afterany`；失败、取消、抢占和启动错误 attempt 均为零 credit。Controller不得改变 seed、预算、split、source、公式、门槛或上传权限。

本任务不授权：恢复 Batch9 Wave6、Batch11、旧 Batch7/8、旧完整 SRR forward、SIP/BR2/source arbiter训练、MoSAIC代码/权重、外部数据/权重、改变 local audit 划分、audit调参、新 Cine训练、fold expansion、validation/Docker上传、hosted claim 或 route promotion。
