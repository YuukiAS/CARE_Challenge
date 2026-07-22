# CARE 架构 Wiki

architecture_version: `care-srr-batch7-minimal-pathology-decomposition-ready`
latest_verified_runtime: `Batch7 repair stopped at proposal gate`
latest_scientific_status: `truthful repair evidence, but proposal loss authority impure`
latest_controller_task: `20260722_srr_batch7_minimal_pathology_decomposition`
route_status: `MAIN_ONLY_FINAL_MINIMAL_DECOMPOSITION_NO_PROMOTION`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。Batch7 repair 已经补齐真实独立干预、semantic category memory、anchor-free discovery路径和严格 validator，因此它不是原 Batch7那种复制表失败。但 Planner 代码复核发现，600步所谓 proposal-only stage传入空 loss配置，继续使用历史 M10混合损失；当前结果不能作为纯 proposal设计的最终否定。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

图表示当前代码中存在的完整架构，不表示所有组件都应继续保留。最新任务将分别判断 minimal proposal 和 dictionary proposal是否值得保留。

## 已确认的 Batch7 repair 结果

```text
terminal commit: 0fcc3ff605112a0efeab73f3df2f83249793d321
proposal job: 59828884
optimizer steps: 600
mean positive Dice delta: +0.0012229660
scar positive Dice delta: -0.0019961366
edema positive Dice delta: +0.0044420686
help/harm: 25/27
remote-FP relative worsening max: 0.0530525167
```

真实完成：

```text
independent 44-case intervention predictions
identity and gate-closed exact zero
real category semantic memory with valid masks and hashes
anchor-free discovery implementation path
strict known-bad validator
```

## Planner 复核结论

### 仍未实现到位

- proposal stage 使用空 loss JSON，M10历史 refiner、preservation、arbitration、bounded correction和dictionary regularization等默认项仍可能参与；
- 新的 discovery/confirmation direct loss没有显式开启；
- gradient authority对 proposal logits均值反向传播，而不是逐项验证正式 loss；
- anchor-free检查仅覆盖两个 LGE-only病例，没有覆盖 T2-present edema和CenterC完整多模态病例。

### 已经出现的设计负证据

- semantic negative memory关闭后 edema更好，scar几乎不变；
- prototype maps对 edema约只有 `+0.0007` 贡献，对 scar没有稳定收益；
- scar proposal、refiner、source和gate相关真实模式持续为负；
- edema保留约 `+0.004` 的小幅正信号；
- no-anchor仍严重崩溃。

因此当前完整 dictionary/proposal链路不能继续默认保留，但高层的病种特异 proposal 思想尚未被纯实验否定。

## 当前唯一任务

```text
BATCH7_FINAL_MINIMAL_PATHOLOGY_DECOMPOSITION
```

证据和合同入口：

```text
results/srr_production/code_maturity/batch7_repair_planner_audit_and_minimal_decomposition_decision_20260722.md
docs/plans/laneB_round04_active_srr_batch7_minimal_pathology_decomposition_execution.md
configs/srr_production/myops_batch7_minimal_decomposition.yaml
prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_controller.md
prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml
```

任务只运行四个匹配实验：

```text
scar_minimal
scar_dictionary
edema_minimal
edema_dictionary
```

四个实验先修复显式 loss authority，再从相同 checkpoint 独立训练400步并评价全部44例。Minimal失败则该病种 proposal直接 RETIRE；dictionary只有相对 minimal额外提高至少 `+0.001` 且安全不恶化才保留。任务结束后不得继续以“组件尚需完善”为理由延长同一复杂路线。

## 当前不授权

```text
Batch8
refiner training
source arbiter training
production gate training
monolithic continuation
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