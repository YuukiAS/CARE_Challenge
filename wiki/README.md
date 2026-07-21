# CARE 架构 Wiki

architecture_version: `care-srr-batch7-mechanism-closure-repair-terminal`
latest_verified_runtime: `Batch7 repair stopped at proposal gate`
latest_scientific_status: `Batch7 repair mechanisms connected; proposal chain inadequate`
latest_controller_task: `20260721_srr_batch7_mechanism_closure_repair`
route_status: `MAIN_ONLY_BATCH7_REPAIR_VERIFIED_NO_PROMOTION`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。当前代码已经包含 Batch7 的 semantic memory、prototype-map spatial dictionary、dual-source proposal、differentiable refiner、source arbiter 和 bounded production gate。Batch7 repair 已补齐可信独立组件干预和 strict validator；终态科学结果是 proposal chain 未达到继续门，不能继续下游 refiner、arbiter、production gate 训练。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

这些图反映最近生成的已实现架构。Batch7 repair 的机制证据、mapper/finalizer/validator 包记录在 `results/20260721_srr_batch7_mechanism_closure_repair/`。

## 当前科学结论

Batch7 mechanism closure repair 已完成并停在 proposal gate：

```text
controller_verification_decision: VERIFIED_COMPLETE
terminal_scientific_outcome: proposal_chain_inadequate
proposal job: 59828884 FAILED 2:0 as encoded continuation-gate stop
optimizer steps: 600
selected checkpoint SHA256: a2412889d55a0e3eee0ca2d57a77f34db0f10f0a069193cc906785f49fae97f1
mean positive Dice delta: +0.0012229660
scar positive Dice delta: -0.0019961366
edema positive Dice delta: +0.0044420686
help/harm: 25/27
remote-FP relative worsening max: 0.0530525167
Wave5/Wave6: not run because proposal gate failed
```

因此当前科学状态为：

```text
BATCH7_REPAIR_OPERATIONALLY_COMPLETE
BATCH7_PROPOSAL_CHAIN_INADEQUATE
BATCH8_NOT_AUTHORIZED
```

## 已取代的历史结论

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

## 当前证据入口

```text
results/srr_production/code_maturity/batch7_planner_audit_and_mechanism_closure_decision.md
docs/plans/laneB_round04_active_srr_batch7_mechanism_closure_repair_execution.md
configs/srr_production/myops_batch7_repair.yaml
prompts/tasks/20260721_srr_batch7_mechanism_closure_repair_controller.md
prompts/tasks/20260721_srr_batch7_mechanism_closure_repair_executor_plan.yaml
```

Repair 已完成真实独立干预、fail-closed validator、真实 category semantic memory 和 anchor-free discovery。Proposal 阶段失败后已按合同停止并返回 Planner。

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
