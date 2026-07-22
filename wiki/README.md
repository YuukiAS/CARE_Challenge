# CARE 架构 Wiki

architecture_version: `care-myops-batch9-reliable-label-distillation-terminal-no-usable-signal`
latest_verified_runtime: `Batch9 two-seed direct/teacher/control/distill runtime complete`
latest_scientific_status: `Batch9 local fixed-endpoint evidence returned no usable signal; no promotion/upload authorized`
latest_controller_task: `20260722_care_myops_batch9_reliable_label_distillation`
route_status: `MAIN_ONLY_BATCH9_NO_USABLE_SIGNAL_RETURN_TO_PLANNER`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。当前正式主线已经从旧 SRR/BR2 anchor correction 切换为直接分割并完成 Batch 9 两个 seed 的固定预算训练/评价；结果没有形成可用科学信号，不能 promotion、upload、扩 fold 或授权 Batch10。

## 当前判断

```text
Batch7: 操作完成，BR2/SIP机制闭环不完整
Batch8: 未执行，已被方法重选降级为历史诊断合同
Batch9: 已完成操作闭环，终态为 BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER
旧完整SRR: 历史实现，不进入Batch9 forward
nnU-Net: 评价基线，不进入Batch9模型forward
```

## 为什么重选主线

CARE MyoPS 训练数据同时存在：

```text
availability与center高度绑定
no-T2病例没有可靠edema监督
官方validation/test来自未知CenterD且是完整三模态
scar与edema具有不同形态和模态依赖
```

因此，主要问题不是单纯“测试时缺模态”，而是中心绑定的模态不平衡、部分标签可靠和完整三模态未知中心泛化。旧 SRR 试图用 retrieval/prototype/memory/proposal/refiner/gate 同时处理这些问题，导致工程链过长、信号被稀释且难以归因。

用户提供的 Deep Research 推荐强 backbone、可靠标签掩码、完整视图teacher蒸馏和病种特异直分割。Planner接受该方向，但修正：

- 正式训练不能使用1200–1600 step短预算；
- teacher不从少量B/C完整病例随机初始化；
- 自然缺失病例不生成伪T2或伪edema；
- 首轮不同时加入BR2-lite、SIP或refiner。

权威综合判断：

```text
results/srr_production/code_maturity/batch9_reliable_label_distillation_planner_synthesis_20260722.md
```

## 历史 Batch 7 / Batch 8

Batch 7 保留的数字：

```text
scar minimal positive Dice delta: -0.0049928620
edema minimal positive Dice delta: +0.0013426793
edema BR2 positive Dice delta: +0.0029631724
edema BR2 minus minimal: +0.0016204931
```

这些只作为假设生成证据。其终态仍有：scar BR2空预测、SIP/no-SIP完全相同、训练后beta未真实导出、静态/PENDING字段和validator语义缺口。

Batch 8 文件继续保留，但状态固定为：

```text
SUPERSEDED_UNEXECUTED_DIAGNOSTIC_CONTRACT
formal_authority: false
runtime_authorized: false
```

不得启动其Controller，也不得删除其规划证据。

## Batch 9 唯一任务

```text
BATCH9_RELIABLE_LABEL_DISTILLATION_DIRECT_SEGMENTATION
```

合同入口：

```text
results/srr_production/code_maturity/batch9_reliable_label_distillation_planner_synthesis_20260722.md
docs/plans/laneB_round04_active_srr_batch9_reliable_label_distillation_execution.md
configs/care_mm/batch9_reliable_label_distillation.yaml
prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_controller.md
prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_executor_plan.yaml
```

结果目录：

```text
results/20260722_care_myops_batch9_reliable_label_distillation/
```

## Batch 9 已实现/已评价的新模型

```text
src/care_myocardium/models/care_mm_reliable_distill.py
CAREMMReliableDistillResEnc
```

运行证据：`results/20260722_care_myops_batch9_reliable_label_distillation/strict_validator_report.json` 为 PASS；`completion_check.md` 返回 no-usable-signal。

数据流:

```text
[LGE,T2,C0] + availability
-> 3 independent modality stems
-> hard mask immediately after each stem
-> concatenate stem features and availability channels
-> official nnU-Net v2 ResidualEncoderUNet M-level backbone
-> shared decoder feature
-> anatomy head + scar head + edema head
-> direct six-class logits
-> argmax
```

输出定义：

```text
anatomy: background, healthy myocardium, LV, RV
scar: myocardium logit + scar residual
edema: myocardium logit + edema residual
```

No-T2时edema logit设为-20，但No-T2不参与edema supervision或distillation。

Center只允许用于训练采样、监督资格和诊断分组；禁止进入network tensor、normalization、router和validation inference。

## 旧组件在 Batch 9 的状态

以下调用计数必须为0：

```text
SRRProposeRefineMyoPS
ProposalDictionary
M10TwoPassSpatialDictionary
M10CrossFittedPrototypeMemory
prototype maps
semantic negative memory
scar/edema refiner
source arbiter
branch arbitration
bounded nnU-Net correction
production gate
legacy Pattern-SIP
```

BR2-lite、SIP和refiner不等于永久删除，但必须等Batch 9 direct mainline完成后由Planner另行授权，并做容量匹配对照。

## 可靠标签与模态训练

```text
anatomy: 所有有效标签；scar/edema remap为myocardium
scar: metadata标记可靠的病例
edema: T2-present且metadata标记可靠的病例
```

结构化 student view：

```text
full -> full 0.50 / LGE+C0 0.25 / LGE-only 0.25
LGE+C0 -> LGE+C0 0.75 / LGE-only 0.25
LGE-only -> LGE-only 1.00
```

只删除已观测模态，不做模态插补。LGE始终保留。

## Teacher/student

每seed先训练500-epoch direct student。Teacher从同seed direct终点复制，然后只在天然完整三模态可靠训练病例上fine-tune 100 epochs。

```text
student_moddrop_control
student_reliable_distill
```

均从同一student checkpoint开始，使用相同病例、patch、dropout mask、augmentation、optimizer、teacher forward和100-epoch预算。唯一差异是distillation loss权重。

Distillation只作用于天然完整三模态训练病例。自然缺失病例不接收伪T2、伪edema或teacher edema pseudo-label。

## 训练预算

固定seeds：

```text
20260723
20260724
```

每seed：

```text
direct student: 500 epochs / 125000 steps
complete-view teacher: 100 epochs / 25000 steps
moddrop control: 100 epochs / 25000 steps
reliable distill: 100 epochs / 25000 steps
```

Short smoke和100-step overfit的formal credit为0。

## 训练前硬门

必须验证：

```text
runtime center/modality/label inventory
official ResEnc environment and plans
clean import graph
legacy module call count zero
availability hard mask
reliable supervision masks
runtime resolved loss and per-loss gradient
real full/LGE+C0/LGE-only overfit
checkpoint roundtrip
semantic known-bad fixtures
```

Known-bad必须拒绝旧SRR捷径、center泄漏、no-T2 edema监督、loss未进total、matched manifest不一致、checkpoint未reload、prediction复用、空预测和短训伪完成。

## 评价

Selected checkpoint必须reload后评价44例，报告：

```text
scar/edema Dice, HD95, precision, recall
component count, remote FP, volume ratio, empty rate
changed voxels, case-wise help/harm
complete-trimodal, CenterB, CenterC
LGE-only, LGE+C0
small/large scar, low/high baseline
```

B/C只是CenterD本地代理，不得声称已证明未知中心泛化。

## 终态

只允许：

```text
BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER
BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER
BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER
```

Controller完成后返回Planner，不得启动Batch10、BR2-lite、SIP、refiner、fold expansion、Cine或上传。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

这些图在Batch 9实现前仍属于历史实现视图。Mapper终态必须从真实代码和runtime重新生成，不得仅改标题。

## 入口

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [current_state.yaml](current_state.yaml)
- [history/README.md](history/README.md)
