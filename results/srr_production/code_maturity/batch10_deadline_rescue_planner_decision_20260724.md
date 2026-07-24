# Batch 10：截止日前公平重评、定向修复与提交决策

## 结论

Batch 10 不再扩展旧 SRR，也不重新设计一套新网络。当前只剩两到三天，唯一合理目标是先纠正 Batch 9 repair 中仍然存在的推理、空间恢复、蒸馏对齐、病种置信和采样语义问题，重新评价所有现有 checkpoint；只有正确重评后已经接近 nnU-Net，同一模型的短续训才有资格启动。最终必须在一个 Controller goal 内给出明确结论：形成可写 paper、可做 Docker 的非 nnU-Net 候选，或停止本次方法路线。

本计划绑定远端 `main` 提交 `3705a37bf4519144ea52155a2a7a3d2d118e3776`。用户已人工终止原 Batch 9 repair Wave 6 的后续运行；现有 epoch 25 control/distill checkpoint 和此前 direct/teacher checkpoint只作为 Batch 10 输入，不得自动恢复原 Wave 6 到 epoch 100。

## 图与路线边界

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
```

旧 SRR 图保留的科学原则是模态特异编码、只消费已观测模态、解剖优先、scar/edema 分治和小病灶保护。Batch 10 保持 CARE-MMRD 的三 stem、availability hard mask、ResidualEncoderUNet、anatomy/scar/edema 分头和六类直接输出，不恢复 prototype、memory、BR2、SIP、proposal、refiner、nnU-Net anchor 或 fallback。

## 为什么不能直接相信当前 epoch 25 分数

当前截图中的 matched 结果为：

```text
seed 20260723: control scar 0.4743, edema 0.3188
seed 20260723: distill scar 0.4754, edema 0.3316
seed 20260724: control scar 0.4291, edema 0.3354
seed 20260724: distill scar 0.4221, edema 0.3576
```

蒸馏相对 control 的平均变化约为 scar `-0.0030`、edema `+0.0175`。这说明完整视图知识对 edema 有可重复信号，但对 scar 没有稳定收益；同时两项仍低于同划分 nnU-Net。因此不能继续原样训练并期待自然翻盘。

代码审计又发现，当前分数还不是干净的最终否定：

1. `evaluate_care_mm_batch9.py` 使用一次全体积 forward，而训练使用 plans patch；对于 InstanceNorm 网络，二者统计语义不同。
2. 预测只按数组形状做 nearest-neighbor `zoom`，再复制 GT geometry，没有用 nnU-Net v2 的 crop、transpose、resampling 和正式 export 逆变换。
3. evaluator 用默认 `CAREMMReliableDistillResEnc()` 实例化 checkpoint，而不是从 checkpoint 中的 plans/config重建模型。
4. 模型结构解析使用 `nnUNetResEncUNetMPlans`，数据读取却由硬编码 `nnUNetPlans_3d_fullres` 路径提供；必须证明 data identifier 与 preprocessing fingerprint 一致。
5. 训练只对 student `x` 和 `seg` 做空间增强，`natural_x`/teacher view 没有应用相同空间变换，却进行逐体素 consistency/distillation。
6. 蒸馏覆盖 gate 只检查 teacher 对任意类别的最大概率，不能证明 teacher 在 scar/edema GT 位置对相应病种有置信度。
7. sampler 只在病例池中均匀抽病例，没有落实“先中心均衡、再病例均衡”。
8. 最新远端代码导入 `src.care_myocardium.data.case_metadata`，但该文件没有出现在提交 diff 或远端可读取路径中；必须执行 clean-checkout import audit，禁止依赖服务器未提交文件。
9. Wave 0–5 轻量运行证据没有完整推送到远端，`CURRENT.md` 和 wiki 仍停在 Batch 9 repair ready；Batch 10 必须先绑定本地真实 runtime、job 和 checkpoint lineage。

## Batch 10 的唯一任务图

### 第一阶段：冻结旧运行并做 clean-checkout 审计

记录用户终止 Wave 6 的时间、job ID、终态、已完成 checkpoint 和未完成预算。不得把 epoch 25 写成 100 epoch 完成，也不得自动恢复旧 Wave 6。使用 `git archive` 或独立临时 checkout 验证所有一方 import 都来自 tracked files；缺失 `case_metadata.py` 时必须提交该文件或移除依赖后重建 metadata，不得依赖本地未跟踪文件。

### 第二阶段：建立真正公平的推理与空间恢复

新增一个 CARE-MMRD inference/export 入口，必须：

```text
checkpoint plans/config reload
-> plans-derived preprocessing data identifier
-> nnU-Net v2 sliding-window inference
-> plans patch size, step_size=0.5
-> Gaussian importance weighting
-> mirror TTA using trainer-declared axes
-> official nnU-Net v2 export/inverse preprocessing
-> original NIfTI geometry
```

禁止一次全体积 forward 作为正式分数，禁止 shape-only `zoom`，禁止用 GT `CopyInformation` 掩盖缺失的逆预处理。输出必须与原图在 shape、spacing、origin、direction 上精确一致，并用 known-bad 证明错误 crop/transpose/properties 会被拒绝。

标准 nnU-Net 的 checkpoint、logits和预测仍不得进入 CARE-MMRD forward；但允许只读现有 fold0 nnU-Net NIfTI prediction和轻量 metrics，用同一 evaluator重新计算 baseline、case-wise help/harm、HD95、remote FP和component count。

### 第三阶段：零训练重评所有现有 checkpoint

必须发现并绑定以下候选，不得静默缺失：

```text
2 x repaired direct selected checkpoint
2 x complete-view teacher selected checkpoint
2 x moddrop control epoch25 checkpoint
2 x reliable distill epoch25 checkpoint
```

先对八个单模型做无 TTA 的44例正式重评，再只对每个病种排名前两名做 mirror TTA。Teacher 必须单独报告，因为官方 validation/test 是完整三模态，完整视图 teacher 可能优于面向缺模态的 student。

### 第四阶段：有限、可审计的 ensemble 与后处理

不得做无界参数搜索。固定生成：

```text
direct two-seed probability mean
teacher two-seed probability mean
control epoch25 two-seed probability mean
distill epoch25 two-seed probability mean
best-two-model probability mean
one pathology-specific compositor
```

病种 compositor 使用最佳 anatomy source 的 classes 0–3、最佳 edema source 的 class 4、最佳 scar source 的 class 5，按概率拼接后重新归一化；不得使用 nnU-Net 概率。

44例按 `(center, scar_positive, edema_positive)` 分层，层内按 case-id SHA256 排序后交替分成 calibration/audit 两半。只在 calibration 上选择固定小网格后处理：anatomy-head myocardium support 阈值 `{0.20,0.30,0.40}`、物理距离扩张 `{5,10} mm`、scar 最小连通域 `{0,5,10} mm3`、edema 最小连通域 `{0,20,50} mm3`。最终必须在未参与选择的 audit 半集和完整44例同时报告结果。

### 第五阶段：条件式短续训

只有公平重评后的最佳非 nnU-Net 候选在 audit 集满足：

```text
scar gap to nnU-Net <= 0.04
edema gap to nnU-Net <= 0.03
no GT-positive empty prediction
no-T2 edema voxels = 0
HD95 relative worsening <= 10%
```

才允许短续训。否则直接跳过训练，进入停止或 Docker 决策。

短续训从各 seed repaired direct selected checkpoint重新开始，不继承已停止 Wave 6 的 optimizer状态。每 seed运行 matched control/distill各25 epoch、6250 steps，初始学习率 `2e-4`，polynomial decay；两个 seed可在 `htzhulab` 和 `a100-gpu` 并行，但代码、配置、case、patch、增强、student mask和预算必须完全一致。

必须先完成三项修复：

1. student与natural/teacher view共享完全相同的空间变换；允许独立强度扰动，但必须分别记录seed和参数。
2. sampler先按符合监督资格的center均匀采样，再在center内均匀采病例，最后采scar/edema/anatomy/background目标。
3. scar与edema使用各自teacher margin概率和各自confidence mask。阈值只在完整三模态训练病例上从 `{0.20,0.30,0.40,0.50,0.60}` 选择满足 GT-positive coverage `>=0.20` 且 confident-positive precision `>=0.50` 的最大阈值；某病种无法满足时，该病种distillation权重必须为0，不得用任意类别confidence冒充病理覆盖。

在 epoch10 和 epoch25做44例正式重评并reload selected checkpoint。Distill相对matched control必须逐seed、逐病种非劣，不能用跨seed平均掩盖scar下降。

## 最终提交与停止门

Paper候选必须同时满足：

```text
audit split scar Dice >= same-split nnU-Net - 0.002
audit split edema Dice >= same-split nnU-Net - 0.002
full44 at least one pathology Dice gain >= 0.005
full44 other pathology non-negative
help >= harm
HD95 and remote-FP relative worsening each <= 5%
no GT-positive empty prediction
no-T2 edema exact zero
```

Docker候选可以略宽，但必须是有实质意义的非 nnU-Net方法：full44两病种都不低于 baseline `0.01` 以上，至少一个病种不低于 baseline，audit split不出现明显退化，并通过端到端容器dry-run。达到Docker门只授权生成本地submission-ready image和manifest；Hosted upload仍需用户最终确认。

若完成公平推理、teacher/ensemble、固定后处理以及允许的25 epoch短续训后，scar仍低于baseline超过`0.03`或edema低超过`0.02`，必须终止本次CARE-MMRD竞赛路线，不启动Batch11，不重新打开Batch7/SRR长链。

## 截止日安排

```text
7月24–25日：公平推理/export、八checkpoint重评、ensemble和后处理
7月25日晚：第一次paper/docker go-no-go
7月25–26日：仅在near-baseline gate通过时做25 epoch短续训
7月26日：冻结paper数字、图表和方法边界
7月27日：只做paper排版与提交，不再改科学方法
7月28日–8月3日：仅对通过Docker门的候选做容器、速度和官方格式QA
```

## 授权边界

允许：修复当前CARE-MMRD的import、preprocessing绑定、滑窗推理、正式export、同步增强、center-balanced sampler、病种置信蒸馏、有限ensemble/后处理、条件式25 epoch matched续训、Docker本地构建和paper/docker go-no-go。

禁止：nnU-Net作为模型输入、anchor或fallback；Batch7/BR2/SIP/prototype/memory/proposal/refiner恢复；新backbone；外部数据或预训练权重；fold扩展；Cine训练；自动validation/Docker上传；hosted成绩主张；Batch11。