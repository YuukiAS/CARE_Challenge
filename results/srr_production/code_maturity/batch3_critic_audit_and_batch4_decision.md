# Batch 3 审查与 Batch 4 训练决策

## 审查基线

```text
Batch 3A: 1cce038ac6c3cbb91ab2a9bc1033315571d09f71
Batch 3B: 1395ffb29879ab208103bd3acb3c46ad4ab1934f
record commit: d251bde18199d2afa9de60b28d02336f88994941
```

本审查只依据当前 `main` 的代码、轻量结果和 SRR-v2/v2.5/v3 项目图。未在本会话执行服务器训练、Slurm、validation 上传或 hosted 评价。

## 一、总判断

Batch 3A 是重要但不完整的通过：它第一次让 44 个真实 Dataset501 完整体积进入 SRR 模型，并使 checkpoint、raw anchor、安全上下文、记忆查询策略和 NIfTI 评价处于同一数据链。但它仍是小模型零步诊断，不能直接代表 SRR-v3 生产候选。

Batch 3B 真实验证了 4D I/O、非参考帧配准和时间聚合，但分割是强度阈值代理，不是模型。它的心肌 Dice 极低，不能消耗 Batch 4 正式训练预算。

因此 Batch 4 只训练 MyoPS，并且训练前必须修复训练 checkpoint 与推理 schema 不兼容、identity 导出绕过、同 checkpoint 三模式、完整 176 例原型/记忆资产和 44 例 checkpoint 选择。

## 二、Batch 3A 已解决的问题

1. `infer_myops.py` 不再复制 nnU-Net 标签，真实读取 `[LGE,T2,C0]` 和 availability。
2. 44 个 fold0 验证病例均有模型前向记录。
3. schema v2 零步 checkpoint 被实际加载。
4. 训练和验证/推理的记忆查询策略得到区分。
5. raw anchor 与 no-T2 safety context 在模型接口分开。
6. anchor-bounded、no-anchor 和 identity 模式可以写出 NIfTI；评价器要求显式 SRR contract 和 hashes。
7. no-T2 病例的水肿候选、软区域、细化残差和有界修正有完整体积检查。

## 三、Batch 3A 未符合的期望

### 1. 运行的是缩小诊断模型

当前 Batch 3A 配置：

```text
base_channels=2
encoder_profile=tiny_3scale
variant=srr_propref_shared_dual_dict
```

而当前 SRR-v3 主线冻结结构应为：

```text
m10_d3_hierarchical_memory_propref
full_4scale
anchor_bounded_srr_correction
```

所以 Batch 3A 证明的是入口和张量路径，不是最终模型的显存、速度或行为。

### 2. identity 结果仍有导出绕过

模型确实执行前向，但 identity 分支在写文件前直接选择 raw anchor labels。这样只能证明最终导出标签一致，不能证明 `outputs["logits"]` 或 softmax 概率精确恢复 anchor。Batch 4 必须始终导出模型 logits 的 argmax，并直接比较 final/anchor softmax。

### 3. 三种模式没有使用同一 checkpoint 权重

零步诊断将 final-output mode 写入 architecture config，并为模式创建不同 checkpoint。正式控制必须加载同一训练 checkpoint，只在运行时切换 identity、anchor-bounded 和 no-anchor；否则差异可能来自初始化而非机制。

### 4. 原型和记忆仍是 smoke 资产

零步 checkpoint 使用少数 source cases 和每例一个小 patch 构建。它不代表 176 例 fold0 训练集，也没有独立冻结资产哈希。

### 5. 训练 checkpoint 仍不能进入推理入口

训练 runner 当前的 validation/best/final checkpoint 只保存 `model_state_dict`、step、args 和 patch loss；Batch 3A 推理要求 schema v2 的模型、优化器、步数、随机数、split、anchor manifest 和 prototype/memory provenance。直接训练会再次产生不可被正式推理入口读取的 checkpoint。

### 6. checkpoint 选择仍不公平

`validate_patch_loss` 最多只检查 10 个验证病例，best checkpoint 由 patch loss 选择。它不包含完整 44 例 Dice、HD95、远端假阳性、连通域和病例级 help/harm。

### 7. 零步输出几乎没有改变标签

anchor-bounded 模式在 44 例中总共改变 5 个体素：

```text
edema Dice: 0.3944358976789887 -> 0.3943897861345629
scar Dice: 0.5601692281262312 -> 0.5601692281262312
```

这与零步、闭合偏置修正门一致，只能作为管线诊断。

## 四、Batch 3B 审查

### 已真实完成

- 读取真实 4D Cine 并保持 `t,z,y,x`；
- frame0 与标签几何对齐；
- 中间帧通过逐切片二维 optical flow 变形到参考空间；
- 非参考帧能够改变聚合输出；
- raw-label NIfTI 导出和本地 Dice/HD95 可运行。

### 未达到模型主线要求

1. `anatomy_proxy_from_frame` 使用图像百分位阈值、opening/closing 和最大连通域，不是训练网络。
2. 只使用 frame0 和 `frame_count//2`，不是完整多帧建模。
3. 配准为逐切片二维 optical flow，不是成熟三维/时序配准；Jacobian 是代理计算。
4. temporal aggregation 只把非参考代理中的空背景补入参考代理，`nonreference_weight` 实际不参与连续加权。
5. CineMA 未加载。
6. 三例心肌 Dice 为约 `0.012`、`0.047`、`0.019`，HD95 约 118–141 mm，连通域 670–1251 个。

Batch 3B 正确状态是 `REAL_4D_IO_DIAGNOSTIC_PROXY_SEGMENTATION_NOT_MODEL_READY`。

## 五、Batch 4 决策

用户已明确授权一次 MyoPS fold0 训练和 Slurm 分区竞速。Batch 4 固定：

```text
model: M10 D3 full-4scale anchor-bounded SRR
train/validation: 176/44
prototype-memory: all 176 train cases
training: 1800 optimizer steps and >=1800 seconds
full-volume evaluation: step 600, 1200, 1800, each 44 cases
selection: pathology-balanced Dice delta -> harm -> HD95 -> remote FP
controls: same selected checkpoint for identity/anchor-bounded/no-anchor
```

必须先通过独立规划审查和同配置预检。规划审查不得把任务缩回 smoke；执行者不得用 pending、运行中、启动失败、短跑或零步结果结束。

## 六、权威文件

```text
docs/plans/laneB_round04_active_srr_batch4_forced_fold0_training_execution.md
configs/srr_production/myops_batch4.yaml
prompts/tasks/20260721_srr_batch4_forced_fold0_training_controller.md
prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml
prompts/tasks/20260721_srr_batch4_forced_fold0_training_planning_review_request.md
prompts/routes/handoffs/CURRENT.md
```

## 七、当前边界

```text
user training authorization: received
user Slurm authorization: received
execution: blocked pending independent planning review and preflight
validation upload: forbidden
hosted claim: forbidden
Cine training: excluded from Batch 4
controller push: forbidden
independent runtime review: required after terminal packet
```
