# CARE 架构 Wiki

architecture_version: `care-srr-batch8-clean-edema-br2-ready`
latest_verified_runtime: `Batch7 six-run execution complete but BR2/SIP mechanism packet incomplete`
latest_scientific_status: `scar SRR stopped; edema clean BR2 requires two-seed confirmation`
latest_controller_task: `20260722_srr_batch8_clean_edema_br2_confirmation`
route_status: `MAIN_ONLY_BATCH8_CLEAN_EDEMA_BR2_NO_PROMOTION`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。Batch 7 的六组运行在操作层面完成，但原终态不能被当作 BR2/SIP 的充分科学闭环：scar BR2 清空、SIP/no-SIP完全相同、训练后 beta 未真实导出，终态机制文件仍有静态初值和 `PENDING`，validator没有拒绝这些问题。

## 当前判断

```text
scar SRR: stop training, use nnU-Net anchor
edema minimal: small positive signal
edema BR2: +0.00162 over minimal in one seed, requires clean two-seed confirmation
SIP: paused, not evaluated faithfully
refiner: paused, proposal precondition not established
```

Batch 7 关键数字：

```text
scar minimal positive Dice delta: -0.0049928620
edema minimal positive Dice delta: +0.0013426793
edema BR2 positive Dice delta: +0.0029631724
edema BR2 minus minimal: +0.0016204931
```

这些数值保留为假设生成证据，但 Batch 7 的 BR2/SIP科学结论已被 Batch 8 Planner 审计 supersede。

## Batch 7 证据缺口

- `controller_report.md` 仍是 `READY_FOR_CONTROLLER_VERIFICATION`，不是 Controller 最终验收；
- `source_learner_coefficients.csv` 由新建模型导出初始系数；
- 病种系数文件仍有 `PENDING_DETAILED_BETA_EXPORT`；
- `integrativeness_diagnostics.csv` 仅为 `STATIC_INITIAL_COEFFICIENTS`；
- scar BR2 no-SIP/SIP均为空预测，没有定位塌缩阶段；
- SIP/no-SIP预测完全相同，没有checkpoint-derived解释；
- minimal与BR2均继续走旧 `ProposalDictionary`；
- validator没有检查checkpoint-derived beta、空预测、PENDING或完整安全门。

Batch 8 首先修这些证据，不删除历史runtime。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

当前图仍表示仓库中已实现的历史完整架构，不表示 Batch 8 clean model 已完成。Batch 8 Mapper 必须在终态区分：legacy完整SRR、disabled旧组件、clean edema corrector 和 clean BR2候选。

## Batch 8 唯一任务

```text
BATCH8_CLEAN_EDEMA_BR2_CONFIRMATION
```

合同入口：

```text
results/srr_production/code_maturity/batch8_clean_edema_br2_planner_decision_20260722.md
docs/plans/laneB_round04_active_srr_batch8_clean_edema_br2_confirmation_execution.md
configs/srr_production/myops_batch8_clean_edema_br2.yaml
prompts/tasks/20260722_srr_batch8_clean_edema_br2_controller.md
prompts/tasks/20260722_srr_batch8_clean_edema_br2_executor_plan.yaml
```

结果目录：

```text
results/20260722_srr_batch8_clean_edema_br2_confirmation/
```

## Clean 模型

Batch 8 必须新增独立薄模型：

```text
src/care_myocardium/models/srr_batch8_clean_edema.py
CleanEdemaBR2Corrector
```

它只持有并冻结 source checkpoint 中必要的 modality encoders、base retrieval、anatomy decoder、edema decoder和anatomy-union上下文。不得实例化完整 `SRRProposeRefineMyoPS` 后仅靠 flags 关闭旧模块。

旧组件调用计数必须为0：

```text
ProposalDictionary
M10TwoPassSpatialDictionary
M10CrossFittedPrototypeMemory
prototype maps / semantic negative memory
refiner
source arbiter
branch arbitration
learned production gate
legacy Pattern-SIP
```

### Clean minimal

```text
frozen edema feature
+ T2 image
+ frozen anatomy-union probability
-> clean edema delta head
-> raw nnU-Net edema logit + 2*tanh(delta)
```

其余五类logits保持原始anchor。No-T2时delta、logit变化和label变化必须精确为0。

### Clean BR2

只增加四个病种特异representer：

```text
shared anatomy
LGE private
T2 private
LGE-T2 interaction
```

每个独立参数化、输出固定per-case RMS。Beta为signed、spatially-global，不使用softmax/simplex/top-k，不允许逐病例beta residual。训练使用CenterB/CenterC beta，验证只使用pooled beta，center不得进入图像网络。

## Batch 8 实验

```text
seed 20260722:
  edema_clean_minimal_seed20260722
  edema_clean_br2_seed20260722
seed 20260723:
  edema_clean_minimal_seed20260723
  edema_clean_br2_seed20260723
```

每组800 optimizer steps，在200/400/800评价全部44例；step800固定为正式checkpoint并reload。同seed minimal/BR2必须共享common-head初始化、病例/patch序列、augmentation、optimizer模板、预算、评价和decode。

训练仅使用T2-present、可靠edema监督的CenterB/CenterC病例；no-T2病例不进入训练、beta、loss或negative。

## 训练前硬门

- 从Batch7真实checkpoint导出机制，禁止静态新建模型和PENDING；
- 定位scar空预测发生阶段；
- clean import graph证明旧模块调用计数为0；
- checkpoint只加载白名单key；
- minimal/BR2初始logits差 `<=1e-6`；
- no-T2 exact anchor identity；
- 两真实病例100-step fixed overfit，loss下降至少30%，预测非空；
- 逐loss gradient authority；
- checkpoint roundtrip `<=1e-6`；
- known-bad真实拒绝旧模块、静态beta、PENDING、空预测完成和伪matched实验。

## 保留门

Clean BR2只有全部满足才保留：

```text
每seed BR2 positive Dice delta >= +0.002
两seed平均 BR2 positive Dice delta >= +0.003
每seed BR2-minus-minimal >= +0.0005
两seed平均 BR2-minus-minimal >= +0.001
CenterB和CenterC平均delta均>=0
combined help>=harm
HD95 non-worse
remote-FP relative worsening<=5%
no-T2 exact anchor identity
无空预测
所有机制字段来自selected checkpoint
```

终态只能是：

```text
EDEMA_CLEAN_BR2_RETAIN_PENDING_PLANNER
或
RETIRE_SRRMyoPS_PERFORMANCE_LINE_USE_NNUNET
```

Scar固定为 `SCAR_SRR_TRAINING_STOPPED_USE_NNUNET`。

## 当前不授权

```text
SIP training
refiner training
scar training
source arbiter / production gate
Batch9
fold expansion
Cine
backbone replacement
external data or weights
validation packaging/upload
hosted metric claim
route promotion
```

## 入口

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [current_state.yaml](current_state.yaml)
- [history/README.md](history/README.md)
