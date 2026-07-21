# Batch 6 结果复核与 Batch 7 决策

## 总体判断

Batch 6 没有因为运行故障中断，而是按合同完成了固定病例过拟合和 300 步单折训练后，在科学继续门处停止。它证明最终输出监督和纠错门已经基本接通，但只训练 gate 和两个 refiner 无法把模型从 nnU-Net 附近拉开。下一轮不应把 300 步机械延长到 900 步，也不应换骨干；应当修复上游候选质量，让 prototype、memory、spatial dictionary、proposal 和 refiner 真正产生可兑现的新信息。

## 审计基线

```text
remote: YuukiAS/CARE_Challenge
branch: main
Batch6 terminal commit: f139c54fd6b55b99409fcf546a1a0e117d7aa06b
Batch6 result root: results/20260721_srr_batch6_final_objective_alignment
Batch6 selected checkpoint: step_300
Batch6 selected checkpoint SHA256: 729c81e49bf846339ed2f39ef0f2656319befd2b9cfe73268d7cf501e6b40fbd
fold0 train/validation: 176/44
```

Planner 已视觉读取 ChatGPT Project 材料中的 SRR-v2、SRR-v2.5、SRR-v3。恢复的目标仍是：按模态可用性进行多尺度编码和共享/私有/交互检索，用真实 prototype、memory 和负空间形成病灶 proposal，再由 scar/edema 专用软 ROI refiner 修正，最后在安全边界内纠正 nnU-Net；nnU-Net 只能作为 baseline、anchor、上下文和安全来源。

## Batch 6 真正完成了什么

Batch 6 的两病例固定过拟合通过，说明直接监督最终 scar/edema 输出、训练 production gate 在 baseline 出错处打开、在正确处保持，以及 no-T2 edema 严格归零的方向已经可以学习。正式 300 步训练也完整覆盖 176 个训练病例和 44 个验证病例，所有 Slurm 作业终态、聚合和 validator 已完成。

300 步结果为：

```text
edema positive-case Dice delta: +0.0027247486728372468
scar positive-case Dice delta:  +0.0006739681677682672
mean Dice delta:                +0.001699358420302757
required continuation gate:     +0.003
help / harm:                    25 / 18
no-T2 edema exact zero:         true
```

因此这不是“loss 完全没修好”的结果。edema 从 Batch 4 的约 `+0.00068` 提高到约 `+0.00272`，说明下游监督修复有真实但有限的作用；scar 仍只有约 `+0.00067`，说明上游候选和 scar refinement 仍是主要瓶颈。

## 同 checkpoint 干预说明什么

Batch 6 step300 的相同 44 例干预给出更明确的方向：

```text
full learned gate:
  edema +0.00272475
  scar  +0.00067397

full gate=1:
  edema +0.00772109
  scar  +0.00028663

proposal only, gate=1:
  edema +0.00434505
  scar  +0.00261628

refiner only, gate=1:
  edema +0.00495245
  scar  -0.00876189
```

这说明：

1. edema 仍有一部分修正被 production gate 压住，但完全打开也只有约 `+0.0077`，不足以支持只调 gate。
2. scar proposal 有小幅正信号，但 scar refiner 明显有害；当前 full 路径把 proposal 与 refiner 固定平均，直接稀释了 scar proposal 的收益。
3. 只继续训练 Batch 6 的 18 个参数不会修复 prototype、dictionary、proposal 和 scar refiner 的根本问题。

## 当前代码中的上游问题

### 1. prototype/memory 与当前特征空间可能错位

Batch 4 先随机初始化模型，再用训练前特征建立冻结 prototype/memory，随后才进行 1800 步正式训练。编码器和检索表示改变后，prototype/memory 没有从训练后 checkpoint 重新提取。Batch 6 又沿用同一旧资产并冻结上游，因此当前相似度可能是在用训练后的特征查询训练前的原型空间。

### 2. 命名负记忆仍包含人为向量

`ProposalDictionary` 中的心肌外、正常心肌、血池、LGE 亮伪影、T2 纹理噪声、远端假阳性六组负记忆默认由 deterministic-axis 向量初始化。正式 prototype 加载只替换普通 positive/negative，没有替换这些命名负记忆；验证和推理可能继续把人造负向量混入负相似度。

### 3. spatial dictionary 没有真正消费 prototype maps

`M10TwoPassSpatialDictionary.forward()` 支持 `prototype_maps`，但当前 `SRRProposeRefineMyoPS.forward()` 调用时只传 anatomy 和 initial evidence。空间路由器中为 scar/edema 正负 prototype 预留的上下文实际为零，memory 查询又发生在 spatial dictionary 之后。因此 prototype/memory 没有参与两轮空间路由。

### 4. proposal 过度依赖 nnU-Net

当前 proposal 是固定加权和，其中直接包含 nnU-Net 病灶概率和由 nnU-Net 硬预测生成的 component map。它容易确认 baseline 已发现的病灶，却缺少独立发现 baseline 漏检区域的正式分支和监督。

### 5. refiner 不是在 proposal 上真正精修

当前 refiner 用阈值产生离散 bounding box，框内从 evidence logits 开始加 residual，而不是从 proposal logits 开始修正。离散裁剪也不能通过梯度教会模型移动 ROI。实际结果已证明 scar refiner 单独使用明显伤害 Dice。

### 6. proposal/refiner 融合是固定平均

正式 full correction 仍使用 `0.5 * (proposal + refiner)`。不同病种和病例中两者质量明显不同，固定平均没有能力绕过有害 scar refiner。

## Batch 7 唯一方向

Batch 7 定义为：**上游候选质量与来源选择修复**。它必须依次完成：

1. 从 Batch 6 训练后 checkpoint 和全部 176 个训练病例重建、哈希并冻结与当前特征空间一致的 prototype/memory；禁止 validation label 泄漏。
2. 用真实语义负样本替换所有人为命名负记忆；缺失类别必须禁用而不是用确定性或重复向量补齐。
3. 在 spatial dictionary 之前查询 prototype/memory，并把正负 similarity maps 真正传入两轮空间路由。
4. 将 proposal 拆成不读取 nnU-Net 病灶概率的独立发现分支，以及使用 anchor 的确认分支，并用可学习可靠度融合。
5. 将正式 refiner 改为以 proposal logits 为起点的可微软 ROI residual，不再把离散 crop 作为正式主路径。
6. 用病种专用 source arbiter 选择 proposal 或 refiner，删除固定 `0.5/0.5` 平均；scar refiner 不得继续伤害 proposal。
7. 先做固定病例 overfit，再做 300 步全 44 例评价；只有上游信号达到明确门槛才继续到总计 1200 步。

## 停止和继续边界

Batch 7 的 300 步继续门不再只看 final mean。必须同时证明 proposal 本身获得明显提升、scar refiner 不再有害、edema learned gate 能兑现大部分 gate-open 上界、HD95/remote FP 不恶化且 no-T2 edema 仍严格为零。若这些条件失败，应停止继续训练，并将该结果解释为当前 SRR 上游表示仍不足，而不是继续调 gate 或堆训练时间。

Batch 7 不授权换 backbone、扩 fold、Cine、外部数据/权重、validation packaging/upload、hosted claim、route promotion、M11 或自动启动 Batch 8。