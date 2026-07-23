# CARE 架构 Wiki

architecture_version: `care-myops-batch9-exposed-issues-repair-ready`
latest_verified_runtime: `Original Batch9 two-seed direct/teacher/control/distill runtime complete`
latest_scientific_status: `Original Batch9 implementation unusable, but implementation defects prevent treating it as a clean scientific negative`
latest_controller_task: `20260723_care_myops_batch9_exposed_issues_repair`
route_status: `MAIN_ONLY_BATCH9_REPAIR_READY_FOR_CONTROLLER`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。当前唯一授权工作不是接回 nnU-Net，也不是恢复旧 SRR 长链，而是在保持 CARE-MMRD / `CAREMMReliableDistillResEnc` 前向结构不变的前提下，修复 Batch 9 已暴露的训练、采样、解码、checkpoint 和验收缺陷，再进行两 seed 重跑。

## 当前判断

```text
Batch7: 操作完成，BR2/SIP机制闭环不完整
Batch8: 未执行，已降级为历史诊断合同
Original Batch9: 运行完成，当前实现不可用，但不是干净科学负结果
Batch9 repair: READY_FOR_CONTROLLER
旧完整SRR: 历史实现，不进入repair forward
nnU-Net: 只作同划分评价基线，不进入模型、训练输入或fallback
```

当前任务入口：

```text
results/srr_production/code_maturity/batch9_exposed_issues_repair_planner_decision_20260723.md
configs/care_mm/batch9_exposed_issues_repair.yaml
prompts/tasks/20260723_care_myops_batch9_exposed_issues_repair_controller.md
prompts/tasks/20260723_care_myops_batch9_exposed_issues_repair_executor_plan.yaml
results/20260723_care_myops_batch9_exposed_issues_repair/
```

## 为什么原 Batch 9 不能直接判定方法失败

原 Batch 9 的 direct 主干明显低于同划分标准基线，continuation 又出现空预测、跨 seed 不稳定和巨量远端假阳性。进一步代码审计发现，以下问题会直接改变训练行为和终态解释：

```text
masked loss只除以病例数，没有按真实有效体素归一化
warm-start continuation仍使用恒定高学习率
patch sampler固定优先选择edema再scar/anatomy
no-T2只把edema logit设为-20，不能保证argmax不输出edema
没有真实每25 epoch全验证和best-checkpoint选择
known-bad使用自报injected/rejected字段
final gate先跨seed求平均，能掩盖单seed塌缩
terminal receipts存在硬编码而非runtime派生
```

因此，原 packet 可以证明当前实现不可用，但不能证明 CARE-MMRD 的可靠标签与完整视图蒸馏假设已经被公平否定。

## Repair 保持不变的模型

```text
[LGE,T2,C0] + availability
-> 3 independent modality stems
-> hard mask immediately after each stem
-> concatenate stem features and availability channels
-> ResidualEncoderUNet M-level feature backbone
-> shared decoder feature
-> anatomy head + scar head + edema head
-> direct six-class logits
-> argmax
```

模型类和 forward 不变：

```text
src/care_myocardium/models/care_mm_reliable_distill.py
CAREMMReliableDistillResEnc
```

禁止：

```text
nnU-Net anchor/logits/checkpoint/prediction fallback
old SRR forward/loss
BR2/SIP
prototype/memory
proposal/refiner
source arbiter/production gate
external data or pretrained weights
```

## Repair 只修复这些问题

1. Case mask 展开到 loss tensor，BCE、consistency 和 feature distillation 按有效体素数归一化，并记录原始 loss、加权贡献和梯度。
2. Direct 使用从 0.01 开始的 polynomial decay；teacher/control/distill 使用从 0.001 开始的 polynomial decay。
3. Patch sampler 显式按 scar 0.35、可靠 edema 0.35、anatomy 0.20、background 0.10 采样并保存 manifest。
4. No-T2 病例继续不接受 edema 监督，并在 inference/evaluation argmax 前 hard mask class 4，预测 edema 体素必须精确为零。
5. 每 25 epoch 对固定 44 例完整评价、保存 checkpoint，并按两病种最低 Dice、平均 Dice、正例 HD95 的词典序选择和 reload checkpoint。
6. Known-bad 必须真实注入错误；终态必须按每个 seed 独立判断，不能用跨 seed 平均掩盖失败。
7. Finalizer 必须从真实 Slurm accounting、aggregation 和 validator 输出生成 terminal fields。

## 训练顺序

固定 seeds：

```text
20260723
20260724
```

先重跑 repaired direct：

```text
500 epochs
250 steps/epoch
125000 optimizer steps
validation every 25 epochs
```

只有两个 seed 都满足以下条件，才允许 continuation：

```text
无GT-positive空预测
no-T2 edema预测体素精确为0
scar和edema都相对原Batch9同seed改善
selected checkpoint已reload
```

随后 teacher、moddrop control 和 reliable distill 各训练 100 epoch / 25000 steps，并从 repaired direct selected checkpoint warm-start。任何 seed 的任一病种相对 matched control 下降、出现空预测或安全越权，都必须单独判失败。

## 数据与监督边界

CARE MyoPS 训练数据存在 availability 与 center 绑定、no-T2 缺少可靠 edema 监督、scar/edema 模态依赖不同等问题。Repair 保持：

```text
anatomy: 所有有效标签；scar/edema remap为myocardium
scar: metadata标记可靠的病例
edema: T2-present且metadata标记可靠的病例
center: 只用于采样和诊断，不进入network tensor
```

No-T2 不得作为 edema negative，也不得获得伪 T2 或伪 edema 标签。

## 历史证据

Batch 7 保留为假设生成证据：

```text
scar minimal positive Dice delta: -0.0049928620
edema minimal positive Dice delta: +0.0013426793
edema BR2 positive Dice delta: +0.0029631724
edema BR2 minus minimal: +0.0016204931
```

其 BR2/SIP 闭环仍不完整。Batch 8 保持 `SUPERSEDED_UNEXECUTED_DIAGNOSTIC_CONTRACT`，不得启动。

原 Batch 9 证据位于：

```text
results/20260722_care_myops_batch9_reliable_label_distillation/
```

其 Controller `VERIFIED_COMPLETE` 只代表原执行合同结束，不代表科学路线已被公平证伪。

## 评价与终态

Repair selected checkpoint reload 后必须评价固定 44 例，报告 scar/edema Dice、HD95、precision、recall、component count、remote FP、volume ratio、empty rate、help/harm，以及 complete-trimodal、CenterB、CenterC、LGE-only、LGE+C0 等分组。

B/C 仍只可作为 CenterD 本地代理，不得声称未知中心泛化已经证明。

Controller 完成后只返回 Planner。不得自动授权 Batch10、fold expansion、Cine、validation upload、hosted metric claim、route promotion 或 final scientific stop。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

Repair 不改变模型 forward，因此本轮不要求重画架构图；Mapper 只需核对真实代码、loss/dataflow、runtime 和 wiki/CURRENT 一致性。

## 入口

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [current_state.yaml](current_state.yaml)
- [history/README.md](history/README.md)
