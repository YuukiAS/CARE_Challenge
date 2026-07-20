# CARE SRR Batch 2：先收口 Batch 1，再建立完整推理与公平评价权威

## 计划元数据

- 类型：主线代码修复与评价权威计划
- 开发姿态：历史 Route B 已并入 `main`，当前只有一个 SRR 主线
- 范围：post-Round04 main-only sprint；不创建 Round05
- 审查基线：`ef98e2d3e6808fd616d2732f4d6a645431a7a4ff`
- 前置计划：`docs/plans/laneB_round04_active_srr_batch1_myops_mainline_repair.md`
- 本文件作用：修正“Batch 1 已完全闭环、Batch 2 可直接做 44 例比较”的错误理解
- 当前结论：Batch 1 完成了真实模型接线和一次性真实病例验证，但尚未形成可供正式训练、完整推理和公平比较共同使用的生产主干
- 禁止事项：不修改 Cine；不提交 Slurm；不做持续训练；不上传 validation；不宣称超过 nnU-Net；不恢复 B3-B8；不创建新模型主体

## 1. 结论先行

Batch 2 不能直接运行“SRR 对 nnU-Net 的 44 例性能比较”。原因不是评价器完全不存在，而是当前还没有一个经过训练、能由统一生产入口完整恢复的 SRR checkpoint。

`ef98e2d...` 的有效成果应保留：

1. 五折共 220 例的 nnU-Net OOF 缓存已经逐例核对并生成哈希清单。
2. `SRRProposeRefineMyoPS` 已增加明确的 `anchor_bounded_srr_correction` 最终输出模式。
3. 跨折记忆查询已经能够改变病灶候选图和最终输出。
4. 有 T2 病例上，水肿编码、路由、字典、候选区域、细化头和修正门存在梯度。
5. 一次性真实病例验证中，关闭修正后可以恢复传入模型的 nnU-Net 基底。
6. 没有运行优化器更新、Slurm 或正式训练。

但这些成果目前只证明“主要模块可以在验证脚本中连起来”，不能证明“生产 runner、推理入口和 checkpoint 已经闭环”。Batch 2 必须先完成 Batch 1 收口，再建立完整推理和评价权威。

## 2. Batch 1 审查发现的实质缺口

### 2.1 验证脚本与生产 runner 仍是两条不同的数据流

`validate_myops_mainline.py` 自己完成了原型构建、记忆库填充、一次性 checkpoint 保存和恢复；但正式候选 runner `scripts/training/run_srr_propref_myops_fold0.py` 仍使用旧的 `fit_and_load_runtime_prototype_bank`：

- 只构建一个全局原型库；
- 未按查询病例排除其自身来源；
- 未以严格模式加载原型 provenance；
- 未按四个 shard 填充 `M10CrossFittedPrototypeMemory`；
- 未读取 Batch 1 的 OOF anchor manifest 与原型/记忆库清单；
- 未使用与验证脚本相同的 checkpoint 保存和恢复逻辑。

因此，当前真实状态是“验证器能跑通”，不是“单一连续 runner 已完成”。Batch 2A 必须抽取共享的一方 builder/loader/checkpoint 逻辑，让验证器、训练 runner 和推理入口调用同一实现。

### 2.2 当前病例仍可能通过全局原型库泄漏到自身查询

跨折记忆查询会排除当前病例所在 shard，但 `ProposalDictionary` 同时还会读取全局正负原型 buffer。当前验证中，查询病例 `Case2001` 同时出现在原型来源病例列表中，因此即使记忆库排除了同 shard，全局原型仍可能包含该病例特征。

生产要求必须改为：

```text
每个训练病例查询：只读取其他三个 shard 的原型与记忆
验证/推理病例查询：读取全部 fold0 训练 shard 的冻结原型与记忆
```

不得再用“记忆库排除当前 shard”替代“完整原型链排除当前病例”。

### 2.3 当前记忆 provenance 与真实逐病例特征并不一一对应

现有验证器先把多个病例的特征合并成总向量，然后针对每个病例 ID 重复使用同一批向量更新记忆库。这会让 ledger 看起来像“每个病例分别贡献了特征”，但实际写入不同 shard 的可能是同一批总向量。

Batch 2A 必须保存逐病例提取结果，再按病例真实特征更新其所属 shard。每个 provenance 行必须能回溯到：

- 病例 ID；
- 病种与正负类别；
- 原始向量数量；
- 采样后向量数量；
- 来源 feature checkpoint/config/preprocess hash；
- 所属 shard；
- 是否进入最终 bank。

### 2.4 未使用的记忆槽没有从相似度计算中排除

记忆查询当前会把尚无来源计数的零向量槽一起送入相似度的 `logsumexp`。这不等于随机原型，但会引入没有真实来源的常数项。

查询时必须使用 `counts > 0` 的槽位掩码。若排除当前 shard 后，某个病种的正原型或安全负原型为空，必须直接失败。

### 2.5 no-T2 水肿安全只验证了部分链路

当前 receipt 验证了：

- 最终水肿修正为零；
- 选定的水肿相关梯度和为零。

但计划要求的完整安全链还包括：

- 水肿候选概率为零；
- 水肿 soft ROI 为零；
- 水肿细化残差为零；
- 水肿候选损失、细化损失、记忆更新和安全负样本贡献为零；
- 所有水肿专属参数梯度为零。

当前模型以 `-20` 表示水肿候选被关闭，这可以保留为 logits 哨兵值，但相应概率、ROI、残差、修正、损失和梯度必须严格为零，并分别写入 receipt。

### 2.6 nnU-Net 恒等性目前针对的是被修改过的 anchor

`read_anchored_case` 会在无 T2 病例中把缓存 nnU-Net 的水肿通道清零。随后 `anchor_identity_control` 只证明恢复了这个修改后的 tensor，而不是原始缓存 nnU-Net 输出。

Batch 2A 必须同时保留：

```text
raw_oof_anchor: 原始 nnU-Net OOF 概率/预测，不得静默修改
safety_context: 可供水肿安全策略使用的派生上下文
```

`anchor_identity_control` 必须逐体素恢复 `raw_oof_anchor`。若生产策略决定在无 T2 病例中屏蔽水肿，该行为必须作为显式安全控制单独报告，不能冒充 nnU-Net 恒等恢复。

### 2.7 当前 known-bad 不是实际错误注入

`validate_myops_mainline.py --known-bad <name>` 目前只是根据名字打印 `REJECTED` 并返回非零，没有实际构造错误配置、错误 bank、错误 anchor 或错误 checkpoint。对应 pytest 只能证明“程序会打印拒绝”，不能证明正式验证逻辑真的识别了错误。

Batch 2A 必须把以下项目改成真实错误注入：

- 确定性原型进入生产模式；
- provenance 缺病例/shard/hash；
- fold0 validation 病例进入原型来源；
- 当前病例查询包含自身 shard；
- no-T2 水肿概率、ROI、残差、修正、损失或梯度非零；
- 缺失模态槽权重非零；
- Pattern-SIP 对路由器无梯度；
- 改变记忆库后候选图和最终输出不变；
- production 输出走 pure SRR；
- anchor 不是 OOF 或几何/哈希不符；
- checkpoint 恢复后重置 step、原型或记忆；
- 旧 B3-B8 进入候选链。

每个 fixture 都必须先产生具体错误对象，再由正式 validator 检出并非零退出。

### 2.8 checkpoint 只证明模型 tensor roundtrip，尚未证明 resume

当前 checkpoint receipt 中 `optimizer_restored=true` 只表示 payload 中存在 optimizer 字段；没有把状态加载到新 optimizer 后核对。scheduler 和 AMP scaler 为 `null`，随机数状态也没有真实恢复并验证下一次采样一致。

Batch 2A 必须建立 runner 共用的 checkpoint helper，并验证：

- 新模型加载后关键 tensor 一致；
- 新 optimizer 加载后参数组和状态一致；
- scheduler/scaler 在启用时一致，在禁用时有明确配置说明；
- Python、NumPy、PyTorch CPU/CUDA 随机数状态恢复；
- 恢复后的下一次 patch 采样和下一次 forward 一致；
- global step、epoch、best metric state、anchor manifest hash、原型和记忆状态均不重置。

### 2.9 formal authority 文件内部仍有过时描述

`configs/srr_production/entrypoints.yaml` 已把状态推进到 Batch 2，但同一文件仍保留“memory 未连接、M10 未暴露、Batch 1 checkpoint 未修”的旧说明。Batch 2A 必须清理这种自相矛盾状态，并逐项区分：

- 已由 Batch 1 修复；
- Batch 1 只在 validator 中证明；
- 尚未进入共享生产 runner；
- 留给 Batch 2 的评价工作。

## 3. Batch 2 的正确目标

Batch 2 分成两个连续阶段。

### Batch 2A：Batch 1 收口与共享生产组件

只修代码真实性，不训练，不评价性能。目标是让以下三条路径使用同一套组件：

```text
Batch 1/2 validator
training runner
full-volume inference entrypoint
```

三者必须共同读取：

- 同一 OOF anchor manifest；
- 同一四 shard 原型/记忆库文件；
- 同一 final-output 配置；
- 同一 checkpoint schema；
- 同一病例排除规则；
- 同一 no-T2 水肿安全函数。

Batch 2A 完成前，不得进入 44 例推理。

### Batch 2B：完整体积推理与公平评价权威

完成 Batch 2A 后，建立真实 NIfTI 推理与统一评价入口。它只证明推理和评价正确，不自动授权训练，也不自动产生科学结论。

必须支持三个明确模式：

```text
anchor_identity_control
srr_no_anchor_control
anchor_bounded_srr_correction
```

其中默认生产候选只能是 `anchor_bounded_srr_correction`；`srr_no_anchor_control` 仅用于机制诊断。

## 4. Batch 2A 精确修改范围

优先原地修改：

```text
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/srr_dictionary_memory.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/srr_production/validate_myops_mainline.py
configs/srr_production/entrypoints.yaml
```

允许新增薄层：

```text
src/care_myocardium/srr_production/anchor_manifest.py
src/care_myocardium/srr_production/prototype_memory.py
src/care_myocardium/srr_production/checkpoint.py
```

这些文件只能抽取共享 builder/loader/schema，不能复制 encoder、路由器、字典、候选头或细化头。

必须新增或修订测试：

```text
tests/srr_production/test_myops_mainline_batch1.py
tests/srr_production/test_myops_batch2_preflight.py
```

## 5. Batch 2B 推理入口

允许新增：

```text
configs/srr_production/myops_batch2.yaml
scripts/srr_production/infer_myops.py
scripts/srr_production/evaluate_myops_fair.py
tests/srr_production/test_myops_batch2_inference_evaluation.py
```

推理入口必须：

1. 读取真实 Dataset501 病例和显式 availability。
2. 读取逐病例原始 OOF nnU-Net anchor，不允许按文件名猜 fold。
3. 读取训练 split 冻结的原型/记忆库，不在验证病例上拟合或更新。
4. 读取完整 checkpoint；缺字段、哈希不符或结构不匹配时失败。
5. 使用滑窗或完整体积推理，记录 patch 重叠、融合方式与确定性设置。
6. 输出 NIfTI，并保持 size、spacing、origin、direction 与标签参考一致。
7. 支持 compact label 与官方原始标签双向无损转换。
8. 不接受训练脚本自报 Dice 作为评价输入。

## 6. 公平评价规则

Batch 2 固定使用 fold0 validation 的 44 例，SRR 与 nnU-Net 必须共享：

- 同一 case list；
- 同一 GT；
- 同一 label map；
- 同一 prediction-to-GT 最近邻重采样；
- 同一 spacing；
- 同一空 GT 规则；
- raw prediction 对 raw prediction；
- 若使用后处理，则相同后处理对相同后处理。

病理类别固定为：

```text
class 4: edema
class 5: scar
```

空 GT 规则固定为：

```text
GT 为空且 prediction 为空：该病例不进入该病种 Dice 均值
GT 为空但 prediction 非空：Dice=0，并计入假阳性、连通域和远端假阳性统计
GT 非空但 prediction 为空：Dice=0；HD/HD95 按明确的失败值或 null+failure flag 记录，不得静默删除
```

必须输出：

- 每病例 Dice、HD、HD95；
- 连通域数量；
- 小假阳性数量与体积；
- 远离心肌区域的假阳性体积；
- 预测/GT 体积比；
- changed voxels；
- anchor 与 SRR 的 help/harm；
- T2-present、no-T2、CenterB、CenterC、scar-positive、edema-positive 子组。

## 7. 评价顺序

Batch 2B 必须按以下顺序执行并逐级失败关闭。

### 第一步：nnU-Net 基线重算

使用统一评价器重现 fold0 记录值：

```text
edema Dice: 0.3944358977
scar Dice: 0.5601692281
```

容差必须在配置中预先固定。若无法重现，停止，先修 split、标签、几何、空 GT 或后处理语义。

### 第二步：anchor 恒等控制

`anchor_identity_control` 导出的 44 例预测必须与原始 nnU-Net OOF prediction 逐体素一致。必须报告：

- 最大 logit/probability 差；
- changed voxels；
- raw label mismatch；
- 每病例和总体 metric 差。

任一不为零时停止。

### 第三步：未训练 SRR 只做管线诊断

若当前只有 Batch 1 的零步 checkpoint，可以运行完整推理以验证 I/O、几何和控制模式，但结果只能标为：

```text
UNTRAINED_PIPELINE_DIAGNOSTIC
```

不得将其与 nnU-Net 的 Dice 差解释为模型优劣。

### 第四步：训练后 SRR 比较需要单独授权

只有存在用户明确授权的真实 fold0 训练、达到事先规定的优化步数/时长/验证事件，并产生完整 checkpoint 后，才能运行正式 SRR-on 与 nnU-Net 的公平比较。

Batch 2 计划本身不授权该训练。

## 8. 必须生成的证据

Batch 2A：

```text
results/srr_production/code_maturity/batch2a_shared_builder_contract.json
results/srr_production/code_maturity/batch2a_prototype_crossfit_audit.json
results/srr_production/code_maturity/batch2a_no_t2_exact_zero_receipt.json
results/srr_production/code_maturity/batch2a_known_bad_execution_report.json
results/srr_production/code_maturity/batch2a_checkpoint_resume_receipt.json
```

Batch 2B：

```text
results/srr_production/inference/batch2_inference_contract.json
results/srr_production/inference/batch2_geometry_roundtrip.csv
results/srr_production/evaluation/nnunet_fold0_reproduction.json
results/srr_production/evaluation/anchor_identity_44case.json
results/srr_production/evaluation/casewise_metrics.csv
results/srr_production/evaluation/subgroup_metrics.csv
results/srr_production/evaluation/help_harm.csv
results/srr_production/evaluation/component_remote_fp.csv
results/srr_production/evaluation/batch2_completion.json
```

并更新：

```text
configs/srr_production/entrypoints.yaml
prompts/routes/handoffs/CURRENT.md
docs/plans/laneB_round04_active_srr_change_review_ledger.md
```

## 9. 完成状态

Batch 2A 允许状态：

```text
BATCH_2A_BATCH1_CLOSURE_COMPLETE
BATCH_2A_NEEDS_REPAIR
BATCH_2A_BLOCKED_PROTOTYPE_SELF_LEAKAGE
BATCH_2A_BLOCKED_RUNNER_VALIDATOR_DIVERGENCE
```

Batch 2B 允许状态：

```text
BATCH_2_INFERENCE_EVALUATION_AUTHORITY_COMPLETE
BATCH_2_NEEDS_REPAIR
BATCH_2_BLOCKED_NNUNET_REPRODUCTION_MISMATCH
BATCH_2_BLOCKED_ANCHOR_IDENTITY_MISMATCH
BATCH_2_UNTRAINED_PIPELINE_DIAGNOSTIC_ONLY
```

Batch 2 完成后，在没有单独训练授权时，正式训练状态应保持阻塞。不得输出：

```text
TRAINING_READY
SRR_ABOVE_NNUNET
SCIENTIFIC_PASS
LEADERBOARD_READY
HOSTED_METRIC_CONFIRMED
```

## 10. 人类可理解的最终边界

Batch 1 已经把“模型内部的大部分零件能否连起来”向前推进了一步，但还没有证明“以后真正训练和推理时会走同一条路”。Batch 2 的第一责任不是赶紧算一个 Dice，而是消除验证脚本与生产 runner 的分叉，保证原型没有病例自泄漏、无 T2 安全覆盖完整链路、已知错误测试不是打印固定字符串、checkpoint 能真正恢复运行状态。

这些问题修好后，Batch 2 才负责建立完整体积推理和统一评价器。由于当前没有受信任的训练后 SRR checkpoint，Batch 2 只能先重现 nnU-Net 基线和恒等控制；正式 SRR 性能比较必须等待用户另行授权一次真实 fold0 训练。