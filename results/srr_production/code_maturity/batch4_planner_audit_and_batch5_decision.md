# Batch 4 结果审计与 Batch 5 决策

## 审计基线

```text
Batch 4 training source commit: 0466260e3f4eb6c50b05a7f5a8b66652b873fe46
Batch 4 terminal packet commit: 82524678e8c4aae5c088b24db8a00643c2603ae9
Batch 4 explicit review commit: 5352d3c7b614adcbe4388a6fcef45c9db662dc38
Handoff simplification commit: 1e74da7527e801726ce6990c9f963119e7cbe9ed
```

本审计依据当前 `main` 的一方代码、Batch 4 轻量结果包和 ChatGPT Project 中视觉读取的 SRR-v2、SRR-v2.5、SRR-v3。没有在本审计线程重新训练、提交 Slurm、上传 validation 或作 hosted 指标主张。

## 一、结论先行

Batch 4 在工程上基本达成目标：M10 D3 full-4scale 模型完成了一次真实 176/44 fold0 训练，合法作业严格停在 1800 optimizer steps，训练循环达到 1800 秒，step 600/1200/1800 均覆盖 44 例，schema-v2 checkpoint 能以同一 SHA 重载到 identity、anchor-bounded、no-anchor 三种模式，identity 从模型 logits 恢复 anchor，完整 176 例原型/记忆资产没有验证泄漏。

但 Batch 4 没有达到科学目标。最终 anchor-bounded SRR 相对 nnU-Net 的提升只有：

```text
edema Dice: +0.0006796507
scar Dice:  +0.0013414936
scar remote FP volume: 620.361970 -> 605.628867 mm3
```

HD/HD95 为混合或轻微变差，CenterC 与 T2-present scar 没有改善。Batch 4 的 candidate-signal 合同要求平均 Dice 至少 `+0.01`，当前约为 `+0.00101`，因此正确科学状态是：

```text
BATCH4_TRAINED_NEGATIVE_OR_REPAIR_REQUIRED
```

它证明完整管线能训练和公平比较，但没有证明 SRR 显著优于 nnU-Net。

## 二、Batch 4 真实解决的问题

1. 正式训练模型从 Batch 3A 的 `base_channels=2 + tiny_3scale` 升级为 `m10_d3_hierarchical_memory_propref + full_4scale + base_channels=32`。
2. 训练 runner 改为 schema-v2 checkpoint，保存模型、优化器、step、RNG、split、anchor 和 prototype/memory provenance。
3. checkpoint 架构身份与运行时模式分离，同一 checkpoint SHA 支持三种控制模式。
4. identity 从模型 logits/softmax 导出，44 例 changed voxels 为 0，softmax delta 为 0。
5. 使用全部 176 个 fold0 训练病例建立冻结 prototype/memory，验证病例泄漏为 0；no-T2 edema positive/negative 均被禁止。
6. 60-step one-batch overfit 从 `3.44227` 降到 `1.01262`，相对下降约 70.6%。
7. 合法训练作业 `59682067` 完成精确 1800 optimizer steps；此前 startup failure 和 7182-step overshoot 作业均被保留为 zero credit。
8. step 600、1200、1800 均完成 44 例完整体积推理和本地评价。
9. evaluator 输出病例级 Dice、HD、HD95、component、remote FP、volume 和 help/harm。
10. controller 持续修复了 NameError、gate logging、optimizer overshoot 和 evaluator config，而不是把失败作业包装成完成。

## 三、执行是否到位

### 已到位

- 合法训练预算、病例覆盖、模型规模、checkpoint reload、三模式控制、identity exact、no-T2 safety、终态 Slurm accounting、失败作业 zero-credit、44 例评价均有机器证据。
- `59682067` 是唯一正式训练 credit；`59678596` 的 7182-step overshoot 被正确作废。
- V100 因当前 torch 不支持 compute capability 7.0 被正确排除，没有为适配 V100 偷改模型。
- 最终 packet 严格 validator 通过。

### 未完全到位或仍有遗漏

1. **checkpoint selection 与最终部署语义不一致。**
   `aggregate_srr_batch4_packet.py::select_checkpoint()` 使用 `step_{600,1200,1800}/pathology_aware` 预测选择 checkpoint；最终正式结果却使用 `anchor_bounded_srr_correction` 的模型 logits argmax。历史 step 1800 的 `pathology_aware` scar HD/HD95 和 remote-FP 明显差于 argmax，因此不能把两种 decode 规则混成同一选择证据。

2. **当前 gate 诊断记录了错误的门。**
   正式输出走 `production_correction_gate`，但 `correction_gate_diagnostics.csv` 主要记录旧 `baseline_residual_gate`、branch arbitration weights 和 branch correction mask。它不能解释为什么最终只改变平均 2.93 个 edema voxels 和 22.20 个 scar voxels。

3. **最终修正机制没有病例级闭环。**
   结果包缺少从 proposal/refiner 到 production gate、bounded correction、changed voxels、Dice/HD95/remote-FP delta 的同病例链路，无法判断真正瓶颈是 proposal、refiner 还是 final correction authority。

4. **prototype manifest provenance 不完整。**
   `frozen_prototype_memory_manifest.json` 的顶层 `feature_hash` 为空，并且没有明确 config hash。病例数、split、asset SHA、source commit 和泄漏检查存在，但没有完全达到原合同所要求的 feature/config/code/split/asset 全绑定。

5. **preflight 的 schema-v2 roundtrip 主要由静态测试覆盖。**
   preflight receipt 明确记录该 GPU preflight attempt 没有产生 runtime schema-v2 reload evidence。训练后控制实验最终证明 checkpoint 可重载，因此不影响 Batch 4 终态有效性，但预检执行本身没有完全按原顺序闭合。

6. **selected-control Slurm job 本身失败。**
   job `59686817` 已生成三模式预测和合同，但 evaluator config 报错；后续在本地修复后重跑评价。结果可以作为现有诊断证据，但不如一个从 inference 到 evaluator 全程 exit 0 的单次控制作业干净。

7. **报告语义存在混淆。**
   `validation_checkpoint_metrics.csv` 的 edema all-case Dice 约 0.78，是因为 no-T2 empty-GT/empty-pred 病例进入 all-case 汇总；正式 baseline 对比 0.3944 是 positive-GT/T2-present 病例均值。两种数值必须分栏命名，不能混用。

8. **机器真值和 root wiki 过时。**
   `prompts/routes/handoffs/CURRENT.md` 仍把 Batch 4 写成规划审查前状态，`wiki/README.md` 仍停在 M9。后续 task 若只读机器入口会得出错误状态。

## 四、数据结论

### 总体

```text
edema: 0.3944358977 -> 0.3951155483
scar:  0.5601692281 -> 0.5615107217
```

这不是显著超过 baseline，而是围绕 anchor 的极小修正。

### 子组

- edema CenterB 有小幅改善，CenterC 基本不变并略降。
- scar no-T2/LGE-only 子组约提升 `+0.00217`，是主要正贡献来源。
- scar T2-present 与 CenterC 略降。
- Case5005、Case6001 scar 约提升 0.02，但 Case1080 下降约 0.0084，说明收益集中且仍存在病例伤害。
- selected checkpoint 的 pathology-aware ranking 中有 18 个 pathology-case harm；step 1800 与 step 1200 的 Dice 差距极小，但 step 1200 的 HD95/remote-FP 更安全。

### 机制直觉

上游 proposal 和 ROI 并非完全无信号：scar proposal 在许多病例上有较高召回，refinement residual 也非零。真正可疑的是最终输出权威：production correction 只改变极少体素，而现有 packet 没有直接记录 production gate 的分布和每个病种的 raw/bounded correction。因此下一轮不应继续增加 dictionary 复杂度，也不应立刻重训；应先证明哪个环节把有效候选压成近 identity 输出。

## 五、Batch 5 决策

Batch 5 定义为：

```text
POST_BATCH4_EVALUATION_AND_OUTPUT_AUTHORITY_DIAGNOSTIC_REPAIR
```

默认不训练。目标是利用已有 step 600/1200/1800 checkpoint 和 44 例数据完成以下工作：

1. 用正式 `anchor_bounded_srr_correction` logits argmax 重新做 checkpoint ranking，`pathology_aware` 只保留为诊断 decode。
2. 将 positive-GT pathology 指标与 all-case empty-safe 指标分开。
3. 对同一 checkpoint 做 identity、bounded-full、no-anchor、proposal-only、refiner-only、production-gate-closed 和 bounded-open-control 的真实运行时干预。
4. 记录 production gate、raw correction、bounded correction、changed voxels、Dice、HD95、component 和 remote-FP 的病例级闭环。
5. 补齐 prototype feature/config/code/split/asset hashes 和 strict validator。
6. 更新 CURRENT 和 root wiki/fingerprint。
7. 只输出一个 Batch 6 训练修复方向：`output_gate_calibration`、`proposal_precision`、`refiner_effectiveness` 或 `evaluation_only_issue`。

只有当 Batch 5 证明一个具体、可干预的瓶颈后，才值得进行下一次训练。当前优先假设是 `output_gate_calibration / final correction authority`，但必须用同 checkpoint 干预证据确认，不能直接把该假设当结论。

## 六、当前边界

Batch 5 不授权：

```text
new training
fold expansion
Cine training
validation packaging/upload
hosted metric claim
route promotion
M11
final scientific stop
```

当前目标仍是显著超过 nnU-Net。`+0.001` 级别的变化不满足路线目标，也不能进入 submission candidate 或论文正结果。