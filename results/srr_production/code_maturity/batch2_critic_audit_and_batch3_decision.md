# Batch 2 审查与 Batch 3 决策

## 审查基线

```text
Batch 2A: b797a55f17b5e4c39a6cb97e8d1e295923f7b546
Batch 2B: b38b1a045236d94045c48f12831a41b190abe691
```

本报告只做代码与证据审查，不训练、不提交 Slurm、不上传 validation、不作榜单结论。

## 一、总判断

Batch 2A 是有价值的部分完成：它修复了原始 OOF anchor 保存、病例级原型来源、空记忆槽屏蔽、无 T2 水肿全链路检查和 checkpoint 恢复等问题。

Batch 2B 的评价器和 nnU-Net 恒等复制检查是真实的，但 `scripts/srr_production/infer_myops.py` 并没有运行 SRR 模型。三个模式都将 nnU-Net 标签文件复制到输出目录。因此：

```text
nnU-Net baseline reproduction: complete
anchor label-copy identity audit: complete
fair NIfTI evaluator: reusable
SRR full-volume model inference: not implemented
trained-checkpoint inference: not implemented
SRR-vs-nnU-Net scientific comparison: not started
```

## 二、Batch 2A 已解决的问题

1. 五折共 220 例 raw OOF nnU-Net anchor 有逐病例 manifest。
2. 病例特征按病例分别提取，记忆 provenance 不再重复使用同一批合并向量冒充不同病例来源。
3. 记忆查询只使用 `counts > 0` 的槽位。
4. crossfit-exclusive 查询可绕开全局原型 buffer，降低训练病例自身泄漏。
5. 无 T2 病例的水肿候选概率、软区域、细化残差、有界修正、损失和所检查梯度均为零。
6. checkpoint schema v2 能恢复模型、优化器、步数、epoch 和随机数状态。

## 三、Batch 2A 仍有遗漏

1. `M10CrossFittedPrototypeMemory.query` 对训练、验证和推理使用同一种“按病例 ID 哈希并排除一个分片”的规则。验证病例不属于训练分片，应读取全部冻结训练分片。
2. `sample_patch_with_anchor` 和 `full_case_anchor_tensors` 仍会在无 T2 时清零传给模型的 anchor 水肿通道。原始 anchor 与安全上下文尚未在模型接口上彻底分开。
3. 多数 known-bad 项仍没有进入真实生产 validator；它们只是构造一个错误字典后直接标记为已检测。
4. 缺少计划要求的 `tests/srr_production/test_myops_batch2_preflight.py`。
5. 当前原型/记忆证据来自少量病例和单 patch，只证明接线，不能作为完整冻结训练资产。

## 四、Batch 2B 已解决的问题

1. 从预测 NIfTI 和 GT 重新计算 nnU-Net fold0 44 例指标：
   - edema Dice `0.3944358976789887`
   - scar Dice `0.5601692281262312`
2. 评价器输出逐病例、子组、连通域、小假阳性、远端假阳性、体积和帮助/伤害表。
3. nnU-Net 标签文件复制后的恒等对照 changed voxels 为零，NIfTI 几何保持一致。

## 五、Batch 2B 的关键失败

`infer_myops.py` 的实际链路是：

```text
找到 raw nnU-Net prediction
-> shutil.copy2
-> 写到模式输出目录
```

它没有：

- 读取 Dataset501 三模态影像；
- 读取 availability；
- 实例化 `SRRProposeRefineMyoPS`；
- 加载原型/记忆库；
- 加载 checkpoint；
- 执行滑窗或完整体积前向。

`--checkpoint` 只用于决定命令是否允许继续，并未真正加载。`srr_no_anchor_control` 和 `anchor_bounded_srr_correction` 仍复制 nnU-Net 标签。

评价器默认把 `srr_pred_dir` 指向恒等目录，completion 也只检查 nnU-Net 基线与恒等复制，因此在没有任何 SRR 推理的情况下仍可写出“完成”。

## 六、状态修正

Batch 2 正确状态应为：

```text
batch2a_status: PARTIAL_SHARED_COMPONENT_CLOSURE_WITH_REMAINING_GAPS
batch2b_status: NNUNET_BASELINE_AND_IDENTITY_EVALUATOR_COMPLETE_SRR_INFERENCE_MISSING
formal_training_status: BLOCKED_PENDING_BATCH3A_REAL_SRR_INFERENCE
```

当前不应直接开始 fold0 训练，因为现有推理入口不会使用训练得到的 checkpoint。

## 七、Batch 3 决策

Batch 3 分为：

1. **Batch 3A：MyoPS 真实模型推理收口**
   - 真实三模态完整体积进入现有模型；
   - 真正加载 checkpoint、原型和记忆；
   - 训练与验证/推理使用不同记忆分片策略；
   - raw anchor 与安全上下文彻底分离；
   - 恒等模式也必须经过模型前向；
   - 评价器禁止 SRR 目录回退到恒等目录；
   - 所有 known-bad 进入真实 validator。

2. **Batch 3B：真实 4D Cine 主干**
   - 保留时间维；
   - 可审计 ED/reference；
   - 真实帧对配准与变形；
   - 每帧解剖预测并变形到参考空间；
   - 时间聚合；
   - ED 空间导出与评价；
   - 历史 B7/B8 继续禁止正式使用。

正式训练、Slurm、validation 上传和性能结论仍需用户另行授权。
