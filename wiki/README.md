# CARE 架构 Wiki

architecture_version: `care-srr-batch7-center-hierarchical-br2-sip-decomposition-ready`
latest_verified_runtime: `Batch7 repair stopped at proposal gate`
latest_scientific_status: `truthful repair evidence; current complex dictionary low leverage; deployable BR2/SIP ablation ready`
latest_controller_task: `20260722_srr_batch7_minimal_pathology_decomposition`
route_status: `MAIN_ONLY_FINAL_CENTER_HIERARCHICAL_BR2_SIP_DECOMPOSITION_NO_PROMOTION`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。Batch7 repair 已经补齐真实独立干预、语义记忆、anchor-free discovery代码路径和strict validator，但600步proposal stage仍继承历史混合M10 loss，不能作为纯proposal或R2/BR2的最终否定。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

图仍表示当前已实现代码，不表示待实现的轻量BR2已经存在。轻量中心分层BR2必须由本任务实现、Mapper复核并在终态更新架构图与fingerprint。

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

Planner复核仍发现：

- proposal stage使用空loss JSON，M10历史混合loss继续参与；
- discovery/confirmation direct loss未显式开启；
- gradient authority对proposal logits均值反向传播；
- anchor-free检查没有覆盖T2-present edema和CenterC完整多模态病例。

## 旧复杂组件的当前结论

```text
M10 16-slot spatial dictionary: 不进入本次正式实验
prototype maps: 不进入本次正式实验
semantic negative memory: 不进入本次正式实验
legacy semantic_retrieval_regularization: 正式权重0
legacy pattern_sip_integrativeness_loss: 正式权重0
refiner / source arbiter / production gate训练: 未授权
```

真实干预显示semantic negative memory对edema略有伤害，prototype maps对edema仅约`+0.0007` Dice、对scar无稳定收益，scar候选链持续为负。因此旧组件不再作为论文核心。

## 保留的论文思想

当前仍保留 Representation Retrieval Learning 的核心：

```text
共享但可选择的representers
+ source-specific sparse learner coefficients
+ observation-set hard masking
+ 部分共享而非全部共享
+ 可单独消融的SIP
```

但全面审计修正了上一版计划的三处概念错误：

1. 训练source应是采集中心，availability是source的observation set；
2. learner coefficient是signed全局标量，不是softmax概率；
3. image-conditioned residual会绕开source coefficient，正式实验禁止；
4. neural representer必须固定RMS，防止通过缩放representer与反缩放beta绕开L1/SIP；
5. no-T2中心没有可靠edema监督，不进入edema beta、SIP或loss；
6. validation不能依赖center ID，只能使用availability-pattern pooled coefficient。

权威审计：

```text
results/srr_production/code_maturity/batch7_br2_sip_comprehensive_architecture_audit_20260722.md
```

## 待实现的轻量中心分层 BR2

训练期：

```text
source = metadata.center
observation set = availability
beta_center = beta_pattern + center_deviation
同pattern内center_deviation和为零并做L2收缩
```

验证与部署：

```text
只使用beta_pattern
center不得进入图像网络、router或推理输入
```

只允许7个全分辨率病种representers：

```text
shared anatomy
LGE private
C0 private
T2 private
LGE-C0 interaction
LGE-T2 interaction
T2-C0 interaction
```

每个representer独立参数化、末层零初始化、乘beta前固定per-case RMS。Private只读本模态；interaction读取归一化双模态特征、乘积和绝对差。

Learner coefficient必须：

```text
pathology-specific
spatially global
signed and unconstrained
no softmax/simplex/top-k
no image-conditioned residual
hard availability mask
invalid effective beta exact zero
```

## SIP 当前决定

SIP保留为严格消融，而不是默认卖点。

新增正式loss：

```text
loss_br2_source_l1_sparsity
loss_br2_center_deviation_shrinkage
loss_br2_selective_integration_penalty
```

SIP只作用于同时观察到所需模态并拥有可靠目标病种监督的训练中心系数。No-T2中心不得进入edema SIP。`|O|<=1` 的representer排除。

论文表述只能是：

```text
R2/BR2/SIP-inspired medical imaging adaptation
```

不得声称原论文理论界直接适用于3D分割，也不得声称已因果消除center与missingness混杂。

## 当前唯一任务

```text
BATCH7_FINAL_CENTER_HIERARCHICAL_BR2_SIP_PATHOLOGY_DECOMPOSITION
```

合同入口：

```text
results/srr_production/code_maturity/batch7_br2_sip_comprehensive_architecture_audit_20260722.md
docs/plans/laneB_round04_active_srr_batch7_minimal_pathology_decomposition_execution.md
configs/srr_production/myops_batch7_minimal_decomposition.yaml
prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_controller.md
prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml
```

六个实验：

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

每个400步、200/400评价全部44例。同病种三组必须使用相同source-balanced病例和patch序列；BR2 no-SIP/SIP还必须共享全部初始化与第50步warmup状态。

## 评价和保留门

除总体正例Dice、HD95、远端假阳性和help/harm外，必须报告complete-trimodal、CenterB/CenterC、所有有正例中心、worst-center、proposal precision/recall/lesion recall、beta和representer尺度。

```text
Minimal: Dice >= +0.003，安全门通过，complete-trimodal不下降
BR2: 相对minimal额外 >= +0.001，worst-center与complete-trimodal不恶化
SIP: 相对no-SIP额外 >= +0.0005，或小幅Dice代价换取明确安全改善
```

终态必须分别决定scar/edema的minimal、BR2和SIP是否保留。Scar minimal仍为负时停止scar SRR，不得再用BR2/refiner/gate补救。

## 当前不授权

```text
Batch8
旧M10 dictionary/prototype/memory继续训练
refiner training
source arbiter training
production gate training
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
