# CARE 架构 Wiki

architecture_version: `care-srr-batch7-formal300-mechanism-closure-repair-pending`
latest_verified_runtime: `Batch7 formal300 stop gate`
latest_scientific_status: `Batch7 joint model below gate; mechanism packet invalid and pending same-scope repair`
latest_controller_task: `20260721_srr_batch7_mechanism_closure_repair`
route_status: `MAIN_ONLY_BATCH7_REPAIR_READY_NO_PROMOTION`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。当前代码已经包含 Batch7 的 semantic memory、prototype-map spatial dictionary、dual-source proposal、differentiable refiner、source arbiter 和 bounded production gate，但原 Batch7 终态没有提供可信的独立组件干预，因此不能把 formal300 失败解释为完整 SRR 思想已被否定。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

这些图仍反映最近生成的已实现架构，不代表 Batch7 机制已经通过科学验证。修复完成后 Mapper 必须重新生成并绑定 fingerprint。

## 当前科学结论

Batch7 formal300 已完成：

```text
job: 59789651 COMPLETED 0:0
optimizer steps: 300
edema positive Dice delta: +0.0054302188
scar positive Dice delta: -0.0048258512
mean positive Dice delta: +0.0003021838
help/harm: 23/35
formal1200: skipped
```

这说明当前联合训练版本没有形成稳定收益，scar 路径尤其有害。但原 terminal intervention packet 存在以下问题：

- 所有 intervention mode 复用同一组 formal metrics；
- identity 不为零；
- proposal-only/refiner-only 关键字段为空；
- source arbiter 没有真实 44 例效果；
- validator 接受 placeholder 和复制结果；
- named semantic memory 没有完整逐类落地；
- discovery retrieval 仍间接读取 nnU-Net context。

因此当前科学状态为：

```text
BATCH7_OPERATIONALLY_COMPLETE
BATCH7_MECHANISM_CLOSURE_INVALID
SAME_SCOPE_REPAIR_REQUIRED
```

## 当前唯一任务

```text
results/srr_production/code_maturity/batch7_planner_audit_and_mechanism_closure_decision.md
docs/plans/laneB_round04_active_srr_batch7_mechanism_closure_repair_execution.md
configs/srr_production/myops_batch7_repair.yaml
prompts/tasks/20260721_srr_batch7_mechanism_closure_repair_controller.md
prompts/tasks/20260721_srr_batch7_mechanism_closure_repair_executor_plan.yaml
```

修复必须先完成真实独立干预、fail-closed validator、真实 category semantic memory 和 anchor-free discovery，然后按 proposal、scar/edema refiner、source arbiter、production gate 分阶段训练。Proposal 阶段失败时立即返回 Planner，不得继续用长训练掩盖。

## 边界

当前不授权：

```text
Batch8
monolithic Batch7 1200 continuation
fold expansion
Cine
backbone replacement
external data or weights
validation packaging/upload
hosted metric claim
route promotion
final scientific stop
```

## 入口

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [current_state.yaml](current_state.yaml)
- [history/README.md](history/README.md)
