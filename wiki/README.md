# CARE 架构 Wiki

architecture_version: `care-srr-batch7-lightweight-br2-sip-decomposition-ready`
latest_verified_runtime: `Batch7 repair stopped at proposal gate`
latest_scientific_status: `current complex dictionary underperforms; lightweight BR2 and faithful SIP still require matched testing`
latest_controller_task: `20260722_srr_batch7_minimal_pathology_decomposition`
route_status: `MAIN_ONLY_LIGHTWEIGHT_BR2_SIP_DECOMPOSITION_READY`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。Batch7 repair 已补齐真实独立干预、真实 category memory、anchor-free discovery code path 和 strict validator，但 proposal stage 使用的仍是混合 M10 loss。当前任务不是继续维护现有 16-slot/prototype dictionary，也不是放弃 Representation Retrieval Learning；它要比较普通 pathology proposal、轻量 BR2 representer dictionary，以及同一 BR2 dictionary 的 SIP-on/off。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

这些图仍反映最近已实现的 Batch7 复杂架构，不代表本次轻量 BR2 候选已经实现。Mapper 必须在任务完成后更新图和 fingerprint。

## 已确认的历史结果

Batch7 repair proposal stage：

```text
proposal job: 59828884
optimizer steps: 600
mean positive Dice delta: +0.0012229660
scar positive Dice delta: -0.0019961366
edema positive Dice delta: +0.0044420686
help/harm: 25/27
remote-FP relative worsening max: 0.0530525167
```

这次运行和干预是真实的，但不能解释为纯 proposal 或 R2/BR2 的最终负结果，因为 stage wrapper 传入空 loss JSON，历史混合 M10 loss仍参与。

## 当前复杂 dictionary 的结论

真实干预显示：

- semantic negative memory 对 scar几乎无益，关闭后 edema反而更好；
- prototype maps 对 edema约有 `+0.0007` 的微小贡献，对 scar无稳定收益；
- scar proposal、refiner、learned source和gate-one均为负；
- 现有16-slot spatial dictionary、prototype maps和semantic memory不再作为正式分解候选。

这只否定当前具体实现的性能价值，不否定R2/BR2的表示检索思想。

## SIP 当前状态

当前源码仍有：

```text
semantic_retrieval_regularization
pattern_sip_integrativeness_loss
```

它们是历史启发式正则：使用手工槽位先验、batch-average gate、KL/entropy/collapse等量，并未直接在source-specific learner coefficients $\beta_d^{(s)}$ 上实现论文SIP。因此：

```text
legacy semantic retrieval regularization: historical only, formal weight 0
legacy Pattern-SIP: historical only, formal weight 0
new BR2 source L1 sparsity: required
new BR2 selective integration penalty: required SIP-on/off ablation
```

新的source只由availability pattern定义：LGE-only、LGE+C0、LGE+T2+C0；center不能输入router。$|O_d|\le1$ 的representer不进入SIP。

## 当前轻量 BR2 候选

轻量 representer dictionary 只允许：

```text
shared anatomy
LGE private
C0 private
T2 private
LGE-C0 interaction
LGE-T2 interaction
T2-C0 interaction
```

要求每个模块有独立参数；无效模块在normalization前hard-mask；router分别输出source-level learner coefficients、image-conditioned residual和final retrieval weights。禁止prototype bank、prototype maps、semantic negative memory和当前M10 spatial dictionary。

## 六个匹配实验

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

同病种三组从同一checkpoint开始，使用相同seed、病例顺序、patch centers、optimizer、400步预算、评价与decode。两个BR2组共享全部BR2参数初始化，只允许SIP权重不同。

## 正式 SIP

对representer $d$，令 $O_d$ 为能够观察其所需模态的source patterns：

$$\widetilde\gamma_d(\tau)=\sum_{s\in O_d}\min\left(1,\frac{|\beta_d^{(s)}|}{\tau}\right),$$

$$P_{SIP}=\sum_{d:|O_d|>1}\min\left(1,\frac{|O_d|-\widetilde\gamma_d(\tau)}{|O_d|-1}\right).$$

该loss必须有数值单元测试和no-SIP/SIP匹配消融。不能用旧Pattern-SIP重命名代替。

## 保留门

```text
minimal: positive-case Dice >= +0.003 and safety pass
BR2: additional Dice over minimal >= +0.001 and safety not worse
SIP: additional Dice over no-SIP >= +0.0005
     or Dice drop <=0.0005 with >=2% HD95/remote-FP improvement
```

终态必须分别给出：

```text
scar_minimal: RETAIN | RETIRE
scar_br2: RETAIN | RETIRE | NOT_APPLICABLE
scar_sip: RETAIN | REMOVE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_br2: RETAIN | RETIRE | NOT_APPLICABLE
edema_sip: RETAIN | REMOVE | NOT_APPLICABLE
```

SIP失败只删除SIP，不自动删除有效BR2。Scar minimal仍为负时停止scar SRR，不允许再用BR2/refiner/gate补救。

## 当前证据入口

```text
results/srr_production/code_maturity/batch7_repair_planner_audit_and_minimal_decomposition_decision_20260722.md
docs/plans/laneB_round04_active_srr_batch7_minimal_pathology_decomposition_execution.md
configs/srr_production/myops_batch7_minimal_decomposition.yaml
prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_controller.md
prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml
```

## 边界

当前不授权：

```text
Batch8
current M10 dictionary/prototype/memory continuation
refiner training
source-arbiter training
production-gate training
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