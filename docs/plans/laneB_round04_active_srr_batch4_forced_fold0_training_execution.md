# CARE SRR Batch 4：强制 fold0 训练与同划分公平比较

Plan metadata:
- Type: active main-line scientific training execution plan
- Lane: historical Route B lineage merged into main; single active SRR line
- Round scope: post-Round04 main-only Batch 4
- Status: DRAFT_FOR_PLANNING_REVIEW
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_batch3_myops_inference_closure_and_cine_mainline.md`
- Function: 在 Batch 3A 模型在环推理之后，完成一次不能被 smoke 替代的 fold0 受控训练，并从同一 44 例重算 SRR 与 nnU-Net 的病例级差异
- Do not: 不得用 12-step、本地 one-batch、submitted-only、pending、运行中或零步 checkpoint 冒充本批训练；不得上传 validation；不得作 hosted 指标主张；不得启动 Route A/B/C worktree
- Rule exception: 用户于 2026-07-21 明确要求 Batch 4 必须包含训练，并允许在等待过长时对 `htzhulab`、`a100-gpu`、`volta-gpu` 使用同一逻辑运行的分区竞速。项目继续使用 main-only Batch 编号，不创建 Round05 或 M11。

## 一、结论先行

Batch 3 已经把 MyoPS 从“复制 nnU-Net 标签”推进到“真实三模态影像经过 `SRRProposeRefineMyoPS` 前向并导出 NIfTI”。这是进入训练前的必要进展，但还不是成熟生产候选：

1. Batch 3A 使用的是 `base_channels=2`、`tiny_3scale` 的零步诊断模型，而不是 SRR-v3 主线冻结的 `m10_d3_hierarchical_memory_propref + full_4scale`。
2. 零步 anchor-bounded 模式在 44 例中只改变 5 个标签体素；水肿 Dice 轻微下降，瘢痕完全不变。它只证明数据流接通。
3. 当前训练 runner 写出的 checkpoint 不是推理入口要求的 schema v2；即使直接训练，checkpoint 仍不能无缝进入 Batch 3A 推理。
4. 当前最佳 checkpoint 由最多 10 个验证病例的 patch loss 选择，不是 44 例完整体积 Dice、HD95、远端假阳性和病例级伤害选择。
5. 当前原型/记忆构建默认只选 16 例、每例一个 patch，不是完整 176 例训练集冻结资产。
6. Batch 3B 只建立了三例 Cine 诊断链：强度阈值解剖代理、单个非参考帧和逐切片二维光流。它没有 CineMA、没有训练后 anatomy model，心肌 Dice 约 0.01–0.05，因此本批不训练 Cine。

Batch 4 的唯一科学重点是 MyoPS：先修训练与推理的最后接口，再强制完成一次足额 fold0 训练，最后用同一 44 例进行公平比较。失败可以形成可信负证据，但不得以未训练或管线缺口结束。

## 二、从 SRR 图恢复的路线目标

已视觉阅读 ChatGPT Project 材料中的 SRR-v2、SRR-v2.5、SRR-v3。当前路线必须保留：

```text
[LGE,T2,C0] + availability
-> 模态专属多尺度编码
-> shared/private/interaction 选择性检索
-> 真实训练/OOF 原型与安全负记忆
-> 解剖结构约束
-> 瘢痕、水肿分别产生候选区域
-> 病种专属软区域细化
-> 有界修正
-> 同病例 nnU-Net anchor
-> 最终分割
```

nnU-Net 是稳定基底、上下文和安全锚点，不得成为绕过 SRR 的隐式唯一模型。

## 三、Batch 3 审查结论

### 3.1 Batch 3A 已达到的期望

- 44 个 fold0 验证病例均真实调用模型一次。
- schema v2 零步 checkpoint 被实际读取，而不再只是命令字符串门。
- raw OOF anchor 与无 T2 安全上下文在模型接口上分离。
- 训练查询排除自身分片；验证/推理读取全部冻结训练分片。
- 三种模式能够运行现有模型并导出保持几何的 NIfTI。
- 评价器要求显式 SRR 预测目录和推理合同，不再默认回退到恒等目录。

### 3.2 Batch 3A 未达到的期望

1. **诊断模型缩小**：配置是 `base_channels=2`、`tiny_3scale`、`srr_propref_shared_dual_dict`，不能代表 SRR-v3 主线结构。
2. **恒等控制仍有输出绕过**：模型虽然前向，但导出时直接选择 raw anchor labels；没有证明模型输出 logits/概率本身与 anchor 精确一致。
3. **三个控制模式没有共享同一训练 checkpoint**：checkpoint 的 architecture config 将 final-output mode 写入结构约束，no-anchor control 会要求另一份 checkpoint。公平控制必须复用同一组权重，仅切换运行时输出语义。
4. **原型/记忆仍是 smoke 资产**：零步 checkpoint 使用少数病例、单 patch 构建记忆；未覆盖 fold0 的 176 个训练病例。
5. **训练与推理 checkpoint 不兼容**：训练 runner 保存普通 `model_state_dict` 字典；推理入口要求 schema v2 的模型、优化器、原型/记忆来源、split 与 anchor manifest 哈希。
6. **checkpoint 选择不公平**：训练 runner 仍以 patch loss 选 best，验证最多读取 10 例；不能替代完整 44 例评价。
7. **zero-step 结果没有科学信号**：anchor-bounded 只改变 5 个体素，水肿 Dice 从 `0.3944358977` 降到 `0.3943897861`，瘢痕 Dice 保持 `0.5601692281`。

### 3.3 Batch 3B 的真实边界

Batch 3B 真实读取了 4D Cine，并证明非参考帧经过图像配准后能改变输出。但当前分割来自强度百分位阈值和形态学规则，不是训练模型；只使用 frame0 和中间帧；配准是逐切片二维光流；Jacobian 是代理计算；CineMA 未加载。三例心肌 Dice 分别约为 `0.012`、`0.047`、`0.019`。因此它是 I/O 和配准烟雾诊断，不是可训练候选。本批冻结 Cine，不消耗正式训练资源。

## 四、Batch 4 固定模型和数据合同

### 4.1 唯一训练模型

```yaml
class_name: SRRProposeRefineMyoPS
variant: m10_d3_hierarchical_memory_propref
encoder_profile: full_4scale
final_output_mode_during_training: anchor_bounded_srr_correction
base_channels: 32
```

不得在执行期改成 `tiny_3scale`、`safe_4scale`、普通 `shared_dual_dict` 或其他简化模型。若显存不足，只允许降低 batch size 到合同固定的 1；不得改变模型、patch、loss、步数或数据划分来适配某个分区。

### 4.2 数据划分

```text
Dataset501 fold0 train: 176 cases
Dataset501 fold0 validation: 44 cases
```

- 训练必须读取全部 176 例，不允许 `--limit-train-cases`。
- 完整体积评价必须读取全部 44 例，不允许 `--max-eval-cases` 缩小。
- OOF nnU-Net anchor 必须来自对应病例未参与训练的 fold checkpoint。
- no-T2 病例不得作为水肿正例或安全负例。

### 4.3 训练病例覆盖采样

Batch size 固定为 1。每 20 个训练步使用固定配额：

```text
8 步：从 176 例的确定性 shuffle-cycle 依次取病例
5 步：T2-present edema-positive pool
4 步：scar-positive pool，优先 LGE-only scar
3 步：已登记 hard-negative pool
```

每轮 shuffle-cycle 使用固定 seed，完成 176 例后重新洗牌。最终 `batch_composition.csv` 必须满足：

```text
unique_train_cases = 176
minimum_case_usage >= 1
T2-present edema supervised batches > 0
LGE-only scar batches > 0
```

### 4.4 冻结原型和记忆资产

优化器第一步之前，使用全部 176 例建立冻结资产。每例最多提取两个确定性 patch：

1. 病灶 patch：优先水肿或瘢痕；无病灶时取心肌区域。
2. 安全负区域 patch：心肌、血池和心脏外区域，水肿只允许 T2-present 病例贡献。

必须产生：

```text
runtime asset: results/20260721_srr_batch4_forced_fold0_training/runtime/frozen_prototype_memory.pt
tracked manifest: results/20260721_srr_batch4_forced_fold0_training/frozen_prototype_memory_manifest.json
```

manifest 必须记录 176 个病例、分片、类别、向量数、特征哈希、资产 SHA256、split hash、代码提交和配置 hash。验证病例不得进入资产。

## 五、训练前必须完成的接口修复

这些修复属于 Batch 4，不得以“需要下一批”跳过：

1. 训练 runner 使用 `save_srr_checkpoint` schema v2 保存模型、优化器、步数、epoch、原型/记忆、split、anchor manifest、配置和随机数状态。
2. 训练后 checkpoint 可以由 `scripts/srr_production/infer_myops.py` 直接读取。
3. checkpoint 的结构身份与运行时输出模式分离：同一训练 checkpoint 必须支持 identity、anchor-bounded、no-anchor 三种运行时模式，不得为控制模式重新初始化或训练模型。
4. identity 模式始终导出 `outputs["logits"].argmax`；禁止在推理脚本中直接用 raw anchor labels 覆盖模型输出。
5. identity 必须实测：标签 changed voxels 为 0，anchor 与 final softmax 最大差不超过 `1e-6`。
6. 完整体积 checkpoint 评价器必须从预测 NIfTI 和 GT 重算，不读取训练脚本自报 Dice。
7. best checkpoint 不再由 patch loss 单独决定；patch loss只作训练诊断。
8. 计划中已有 known-bad 必须进入真实 checkpoint、资产、模型和评价器验证函数。

## 六、强制训练预算

### 6.1 one-batch 预检

正式 job 前必须在同一 Python、同一模型和同一配置上完成：

```text
overfit steps: 60
relative total-loss decrease: >= 5%
finite loss: required
nonzero gradients: encoder/router/dictionary/proposal/refiner/correction gate
no-T2 edema full-chain exact zero: required
checkpoint schema-v2 save/reload max tensor delta: <= 1e-6
```

若首次预检失败，控制者必须在当前允许写入范围内修复并重复预检；不得用预检失败取消用户已授权的训练。只有需要改变模型结构、数据划分或训练预算时才返回规划者。

### 6.2 正式 fold0 Wave 1

```yaml
optimizer: AdamW
learning_rate: 0.0002
weight_decay: 0.0001
grad_clip: 12.0
patch_shape_zyx: [12, 96, 96]
batch_size: 1
optimizer_steps_required: 1800
minimum_train_loop_seconds: 1800
maximum_runtime_seconds: 21600
validation_patch_interval: 300
full_volume_eval_steps: [600, 1200, 1800]
early_stop_before_1800: false
```

loss 权重固定为：

```yaml
scar: 1.35
edema: 1.35
proposal: 0.45
prototype_margin: 0.20
component_proposal: 0.20
semantic_retrieval: 0.04
semantic_coverage: 0.03
semantic_integrative: 0.02
anchor_preservation: 0.10
roi: 0.25
remote_roi: 0.05
```

任何启动失败、环境错误、OOM、preemption 或 race loser 都是零训练 credit。正式训练完成必须同时满足 `optimizer_steps >= 1800` 和 `train_loop_seconds >= 1800`。

## 七、Slurm 分区竞速合同

### 7.1 环境预检

每个可能启动训练的分区必须使用：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

并打印 Python 路径、版本、torch、CUDA、GPU、配置 hash、代码 SHA、split hash、anchor manifest hash、输出目录与 winner lock。禁止裸 `python`。

### 7.2 竞速顺序

1. 先提交 `htzhulab`。
2. 若 15 分钟后仍未开始，提交同一逻辑运行到 `a100-gpu`。
3. 若 `htzhulab` 与 `a100-gpu` 在首次提交后 30 分钟仍均未开始，则在 V100 16GB 完成相同配置显存预检后提交 `volta-gpu`。
4. V100 预检若 OOM，不得改变配置；只记录 V100 不兼容，并继续前两路。

所有尝试必须：

```text
same logical_run_id
same code/config/split/asset hashes
isolated attempt directories
one atomic winner lock
first running lock holder is official winner
started loser exits before optimizer step
pending losers cancelled
```

训练到训练的依赖使用 `afterok`；所有尝试的终态收集和 finalizer 使用 `afterany`。submitted、pending、running 或 monitor packet 均不是完成。

## 八、完整体积评价与 checkpoint 选择

在 step 600、1200、1800 保存 schema v2 checkpoint，并对完整 44 例运行 anchor-bounded 推理。最终选中的 checkpoint 必须重新加载后再评估。

### 8.1 资格门

checkpoint 只有同时满足以下条件才可进入选择：

- 44/44 病例推理和几何检查通过；
- checkpoint/config/split/anchor/prototype hashes 一致；
- no-T2 edema 候选、区域、残差和修正全部为零；
- identity 模式模型输出标签差为零、softmax 最大差不超过 `1e-6`；
- 预测标签只含 0–5；
- 不存在空文件、NaN、无穷值或 SRR 目录回退到 identity 目录；
- 至少 4 个病例的 anchor-bounded 最终标签发生变化；
- scar 和 T2-present edema 的预测均非全空。

### 8.2 固定选择顺序

在合格 checkpoint 中按以下字典序选择，不得由控制者重新发明分数：

1. 最大化 `min(scar Dice delta, edema Dice delta)`；
2. 最大化两病种平均 Dice delta；
3. 最小化 harm 病例数量；
4. 最小化两病种平均 HD95；
5. 最小化远端假阳性体积增量；
6. 仍相同时选更早 checkpoint。

### 8.3 最终控制

同一个选中 checkpoint 必须运行：

```text
anchor_identity_control
anchor_bounded_srr_correction
srr_no_anchor_control
```

三者使用同一模型权重、同一原型/记忆资产、同一病例和同一 decode，不得重新初始化。

## 九、结果判断

### 9.1 训练完成，不代表模型成功

满足预算和评价合同后，操作层可以完成，即使性能差。科学状态分开写：

- `BATCH4_TRAINED_CANDIDATE_SIGNAL`：scar、edema 均不下降超过 0.002，平均 Dice delta 至少 +0.01，HD95 与远端假阳性不恶化超过 5%，help 病例不少于 harm 病例。
- `BATCH4_TRAINED_STRONG_SIGNAL`：scar 和 edema Dice 均至少 +0.03，同时 HD95、远端假阳性和 help/harm 门通过。
- `BATCH4_TRAINED_NEGATIVE_OR_REPAIR_REQUIRED`：达到训练预算但不满足候选门。它允许进入失败诊断和下一轮定向修复，不允许伪装为 undertrained。
- `BATCH4_OPERATIONALLY_INCOMPLETE`：未达到 1800 步、1800 秒、44 例三次评价或终态聚合。

### 9.2 必须输出的失败诊断

无论结果好坏，都必须写：

- loss 曲线和各组件梯度；
- 候选区域召回率、精度与病灶级召回；
- 软区域 GT 覆盖和心脏外比例；
- correction gate 开放率、changed voxels 和病例数；
- scar/edema 分开 Dice、HD95、远端假阳性、连通域和体积比；
- T2-present、no-T2、CenterB、CenterC、LGE-only scar 子组；
- case-wise help/harm；
- 失败归因只能落在预先定义的类别：优化失败、候选召回不足、细化无效、修正门过闭、修正过度、远端假阳性、数据/标签/评价问题。

Batch 4 不自动执行第二轮训练。它必须产出足以让 Batch 5 选择唯一修复方向的证据，避免在一个长任务里根据结果临时改变科学方案。

## 十、Agent-Flow v2 执行结构

本任务是长 Slurm、高恢复风险、系统级训练任务：

```text
独立 GPT 规划审查
-> controller
   -> executor：接口修复、预检、资产构建、竞速训练、聚合
   -> mapper draft/final：核对真实数据流、checkpoint 与 wiki 指纹
   -> durable finalizer：afterany 终态 accounting、聚合和本地轻量提交
   -> validator：严格检查预算、语义和 known-bad
-> controller 停止
-> 独立只读 reviewer
```

控制者、执行者、mapper、finalizer 和 validator 不得写 `review.md`，不得 push。独立 reviewer 只能在轻量结果包本地提交后开始。

## 十一、必须提交的轻量证据

结果根目录：

```text
results/20260721_srr_batch4_forced_fold0_training/
```

至少包含：

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
implementation_snapshot.md
preflight_receipt.json
frozen_prototype_memory_manifest.json
training_adequacy.json
training_log_summary.csv
validation_checkpoint_metrics.csv
selected_checkpoint.json
casewise_metrics.csv
subgroup_metrics.csv
help_harm.csv
component_remote_fp.csv
proposal_diagnostics.csv
roi_diagnostics.csv
correction_gate_diagnostics.csv
slurm_attempts.csv
commands_run.md
mapper_report_draft.md
mapper_report_final.md
architecture_delta_draft.md
architecture_delta_final.md
finalizer_state.json
completion_check.md
review_request.md
controller_report.md
```

checkpoint、原型 `.pt`、预测 NIfTI、完整日志和 winner lock 保持 ignored/untracked；只能提交哈希和轻量清单。

## 十二、完成门

控制者只有在下列全部成立时才能本地提交结果包并停止等待 reviewer：

```text
planning review token valid
Batch 4 preflight pass
one official Slurm winner completed
optimizer steps >= 1800
train loop seconds >= 1800
full-volume evaluation events = 3
all three events evaluate 44 cases
selected checkpoint reloaded
same-checkpoint three-mode controls complete
strict validators pass
all attempts terminal-accounted
post-completion aggregation complete
mapper final complete
completion_check = READY_FOR_INDEPENDENT_REVIEW
review_request exists
```

`NEEDS_MONITOR`、submitted、pending、running、awaiting sacct 或零步诊断不得作为本批完成。