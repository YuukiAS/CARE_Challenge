# CARE SRR Batch 3：先补真实 MyoPS 推理，再进入 Cine 主干

## 计划元数据

- 开发分支：`main`
- 审查基线：`b38b1a045236d94045c48f12831a41b190abe691`
- 前置提交：Batch 2A `b797a55f17b5e4c39a6cb97e8d1e295923f7b546`；Batch 2B `b38b1a045236d94045c48f12831a41b190abe691`
- 当前状态：Batch 2 的 nnU-Net 基线重算和评价器可复用；真实 SRR 完整体积推理尚未建立
- 开发方式：历史 Route B 已并入 `main`，不恢复 route/controller，不创建 Round05
- 禁止事项：本计划不授权正式训练、Slurm、validation 上传、榜单结论或新模型主体

## 一、结论先行

Batch 2 不能被解释为“SRR 推理与评价已经完成，只差开始训练”。

Batch 2A 确实修复了多项底层问题：原始 OOF nnU-Net 基底得到保留，病例特征按病例分别提取，记忆库忽略空槽位，无 T2 病例的水肿候选、局部区域、细化残差、最终修正、损失与梯度均被检查为零，checkpoint 也能够恢复模型、优化器和随机数状态。

但 Batch 2B 的 `scripts/srr_production/infer_myops.py` 没有读取三模态影像，没有实例化 `SRRProposeRefineMyoPS`，没有加载原型/记忆库，也没有加载 checkpoint。三个模式最终都把 nnU-Net 的标签文件复制到输出目录。因此，Batch 2B 只完成了两件事：

1. 验证 nnU-Net fold0 的 44 例指标可以从 NIfTI 预测和 GT 重新计算；
2. 验证复制出的恒等对照与原始 nnU-Net 标签逐体素一致。

它没有建立真实 SRR 完整体积推理，也不能作为正式训练后的评价入口。若现在直接训练，即使得到 checkpoint，现有推理脚本也不会使用它。

因此 Batch 3 必须分成两个连续阶段：

```text
Batch 3A：补齐 MyoPS 模型参与的真实推理与红队验证
-> 通过后
Batch 3B：建立真实 4D Cine 主干与红队验证
```

## 二、Batch 2A 审查结论

### 2.1 已真实解决的问题

1. **原始 OOF 基底保留**
   - `read_anchored_case` 保存原始 nnU-Net OOF 概率与预测。
   - manifest 覆盖五折共 220 例，并记录 split、checkpoint、预处理和文件哈希。

2. **病例级原型来源**
   - 验证器按病例单独提取特征，不再把一批合并向量重复记到多个病例名下。
   - provenance 能回溯病例、分片、类别、向量数量和特征哈希。

3. **空记忆槽屏蔽**
   - 查询只使用 `counts > 0` 的槽位。
   - 排除后缺少正或安全负来源时能够失败关闭。

4. **无 T2 水肿安全**
   - 候选概率、软区域、细化残差、有界修正、对应损失和水肿专属梯度均有独立数值检查。

5. **checkpoint 恢复**
   - schema v2 保存并恢复模型、优化器、步数、epoch、原型/记忆来源、Python/NumPy/PyTorch 随机数状态。

### 2.2 尚未完全解决的问题

1. **验证病例的记忆查询策略错误**
   - 当前 `M10CrossFittedPrototypeMemory.query` 对任何病例都按病例 ID 哈希，并排除一个分片。
   - 训练病例应排除自身分片；fold0 验证或真实推理病例并不属于训练分片，应读取全部冻结训练分片。
   - Batch 3A 必须显式区分 `training_query` 与 `validation_inference_query`。

2. **原始 anchor 与安全上下文仍在模型入口处混用**
   - 病例对象保存了原始 anchor，但 patch 和完整病例辅助函数仍会在无 T2 时清零水肿通道后作为 `anchor_features` 传入模型。
   - 最终分割基底必须始终是原始 OOF anchor；派生的安全上下文只能影响水肿候选和细化，不得替换最终基底。

3. **known-bad 仍有大量伪注入**
   - 确定性原型、缺 provenance 和当前病例泄漏调用了真实检查函数。
   - 但无 T2 非零、缺失槽权重、Pattern-SIP 无梯度、记忆无作用、pure-SRR、非 OOF anchor、checkpoint 重置和旧 B6 等项目，仍主要是构造一个字典后直接返回“已检测”。
   - Batch 3A 必须让每个错误对象进入与生产路径相同的验证函数，并由该函数真正拒绝。

4. **缺少原计划要求的预检测试文件**
   - `tests/srr_production/test_myops_batch2_preflight.py` 未建立。

5. **原型/记忆库仍只是少病例单 patch 的代码烟雾验证**
   - 这足以证明接线，不足以形成训练或推理所需的冻结全训练集资产。

## 三、Batch 2B 审查结论

### 3.1 已真实解决的问题

1. 统一评价器直接读取预测 NIfTI 和 GT，不接受训练脚本自报指标。
2. nnU-Net fold0 44 例基线得到重现：
   - edema Dice：`0.3944358976789887`
   - scar Dice：`0.5601692281262312`
3. 评价器能够输出逐病例 Dice、HD、HD95、连通域、小假阳性、远端假阳性、体积比、帮助/伤害和子组表。
4. nnU-Net 标签复制的恒等对照在 44 例上 changed voxels 为零，并保持 NIfTI 几何信息。

### 3.2 决定性缺口

`infer_myops.py` 目前不是 SRR 推理入口：

```text
病例列表
-> 找到 nnU-Net prediction.nii.gz
-> shutil.copy2
-> 输出相同 prediction.nii.gz
```

它没有执行：

```text
[LGE,T2,C0] + availability
-> SRRProposeRefineMyoPS
-> 冻结原型/记忆库
-> checkpoint
-> 滑窗或完整体积前向
-> NIfTI 导出
```

此外：

- `--checkpoint` 目前只充当是否允许命令继续的字符串门，不会真正加载 checkpoint；
- `srr_no_anchor_control` 和 `anchor_bounded_srr_correction` 也会复制 nnU-Net 标签；
- 评价器默认把 `srr_pred_dir` 指向恒等对照目录；
- completion 只检查 nnU-Net 基线和恒等复制，即使没有任何 SRR 预测，也会写 `BATCH_2_INFERENCE_EVALUATION_AUTHORITY_COMPLETE`；
- `max_logit_or_probability_delta` 固定写为零，而不是从概率或 logits 实测；
- 当前测试只证明标签复制和命令门生效，没有证明模型、checkpoint、原型或记忆库被调用。

因此，Batch 2B 的正确状态应为：

```text
NNUNET_BASELINE_AND_IDENTITY_EVALUATOR_COMPLETE
SRR_FULL_VOLUME_INFERENCE_NOT_IMPLEMENTED
```

## 四、Batch 3A：MyoPS 真实推理收口

### 4.1 核心目标

把 `scripts/srr_production/infer_myops.py` 改成现有生产组件的薄入口，而不是另写模型。真实数据流必须是：

```text
Dataset501 完整体积 [LGE,T2,C0] 与 availability
-> 逐病例 raw OOF anchor manifest
-> 冻结的 fold0-train 原型/记忆库
-> schema v2 checkpoint
-> SRRProposeRefineMyoPS
-> 完整体积或确定性滑窗融合
-> compact label NIfTI
-> 统一评价器
```

### 4.2 必须修改的文件

```text
scripts/srr_production/infer_myops.py
scripts/srr_production/evaluate_myops_fair.py
scripts/srr_production/validate_myops_mainline.py
scripts/training/run_srr_propref_myops_fold0.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/srr_production/anchor_manifest.py
src/care_myocardium/srr_production/prototype_memory.py
src/care_myocardium/srr_production/checkpoint.py
configs/srr_production/myops_batch2.yaml
configs/srr_production/entrypoints.yaml
tests/srr_production/test_myops_batch2_preflight.py
tests/srr_production/test_myops_batch2_inference_evaluation.py
```

### 4.3 硬性要求

1. **checkpoint 必须真的加载**
   - 核对 schema、模型结构、final-output 模式、split hash、anchor manifest hash、原型/记忆 provenance hash。
   - 任一不符直接停止。

2. **三种模式必须调用同一个模型对象**
   - `anchor_identity_control`：模型仍执行，但修正强制关闭，最终逐体素恢复原始 OOF anchor。
   - `srr_no_anchor_control`：仅用于诊断，不能写正式性能结论。
   - `anchor_bounded_srr_correction`：默认生产候选。

3. **raw anchor 与安全上下文分离**
   - `raw_anchor` 始终作为最终分割基底。
   - `safety_context` 只能控制无 T2 水肿候选、局部区域、细化和修正。

4. **查询策略分离**
   - 训练病例：排除该病例所属训练分片。
   - 验证/推理病例：使用全部冻结 fold0 训练分片，不按验证病例 ID 随机排除分片。

5. **完整体积推理可审计**
   - 记录输入影像路径、shape、spacing、availability、checkpoint hash、原型/记忆 hash、patch size、overlap、融合方式、输出 hash。
   - 输出 size、spacing、origin、direction 必须与 GT 参考一致。

6. **评价器失败关闭**
   - 不允许 `srr_pred_dir` 默认回退到恒等目录。
   - SRR 比较必须读取对应 inference contract，并核对 checkpoint 与预测哈希。
   - 恒等控制完成和 SRR 推理完成使用不同状态值。
   - 空 GT/空预测的 HD、HD95 必须附带明确 failure flag。

7. **真实红队错误注入**
   - 每个 known-bad 都必须修改实际配置、资产、模型输出或 checkpoint，再由生产 validator 检出。
   - 禁止仅构造字典后直接返回“已检测”。

### 4.4 Batch 3A 完成门

必须同时满足：

```text
44 case model forward count = 44
checkpoint actual load count = 1
prototype/memory actual load count = 1
anchor_identity changed voxels = 0
anchor_identity probability/logit delta = 0
non-identity intervention changes at least one downstream tensor
no-T2 edema full-chain exact zero
all known-bad fixtures enter real validator and fail
geometry roundtrip pass
```

若没有受信任的训练后 checkpoint，可用零步 checkpoint 验证 I/O，但状态只能是：

```text
SRR_MODEL_IN_LOOP_UNTRAINED_DIAGNOSTIC
```

Batch 3A 不授权训练。

## 五、Batch 3B：真实 4D Cine 主干

只有 Batch 3A 通过后，才进入 Cine。

### 5.1 核心目标

建立真实 Cine 数据链，而不是继续使用历史 B7/B8 的随机单帧与合成位移：

```text
Dataset502 真实 4D Cine
-> 时间轴和帧顺序核对
-> ED/reference frame
-> 真实帧对配准与变形
-> 每帧解剖预测
-> 变形到 ED 空间
-> 时间聚合
-> ED 空间 myocardium 输出
-> NIfTI 导出与统一评价
```

### 5.2 必须证明的事实

1. 数据加载器保留时间维，不得只抽中间帧冒充 Cine。
2. ED/reference 来自数据协议或可审计规则，不得写死 frame 0 后不说明。
3. 配准读取真实帧对并生成真实变形场；合成形变只能用于单元测试。
4. 至少有一个非参考帧经变形后进入最终时间聚合。
5. CineMA 若使用，必须实际加载官方权重并进入下游输出；单独跑一次特征探针不算接通。
6. 最终输出在 ED 几何空间，并有逐病例 Dice、HD/HD95、时序一致性和变形质量报告。
7. 历史 B7/B8 继续保持禁止正式使用。

### 5.3 Batch 3B 边界

本计划只授权代码修复、真实病例前向、配准/变形烟雾验证、导出和评价正确性检查。持续训练、Slurm、validation 上传和性能结论仍需用户另行授权。

### 5.4 Batch 3B 执行状态

```text
status: BATCH3B_REAL_CINE_MAINLINE_DIAGNOSTIC_COMPLETE
implementation_commit: 1395ffb29879ab208103bd3acb3c46ad4ab1934f
evidence_root: results/srr_production/cine_batch3b
```

Batch 3B 已完成 3 个真实 Dataset502 Cine 病例的轻量诊断链：

```text
Case1001/Case1002/Case1003 4D Cine
-> frame0 label-geometry reference/ED-space audit
-> frame15 non-reference image-based optical-flow registration
-> non-reference label proxy warp into reference space
-> temporal aggregation alters ED-space output
-> geometry-preserving raw-label NIfTI export
-> local diagnostic Dice/HD95 evaluator
```

证据文件：

```text
results/srr_production/cine_batch3b/batch3b_cine_contract.json
results/srr_production/cine_batch3b/batch3b_time_axis_audit.csv
results/srr_production/cine_batch3b/batch3b_registration_warp_qc.csv
results/srr_production/cine_batch3b/batch3b_temporal_aggregation.csv
results/srr_production/cine_batch3b/batch3b_ed_space_evaluation.csv
results/srr_production/cine_batch3b/batch3b_known_bad_report.json
```

边界不变：这是诊断主干正确性证据，不是训练结果、正式注册质量证明、validation-facing export、hosted metric 或性能结论。CineMA 本批未使用，因为没有在本批加载官方 CineMA 权重。

## 六、后续训练顺序

正式 MyoPS fold0 训练不能排在 Batch 3A 之前。正确顺序是：

```text
Batch 3A 真实模型推理入口通过
-> 用户明确授权训练预算与资源
-> fold0 训练
-> 训练后 checkpoint 进入同一推理入口
-> 公平 SRR-vs-nnU-Net 评价
```

Cine 训练同理，必须在 Batch 3B 代码与真实数据链通过后另行授权。
