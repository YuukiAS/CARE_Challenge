# CARE SRR Batch 7 轻量 BR2 病种分解执行计划

Plan metadata:
- Type: active execution plan
- Lane: historical Route B lineage on main
- Round scope: round04 post-portfolio main-only
- Status: ready for controller
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_batch7_mechanism_closure_repair_execution.md`
- Function: determine whether minimal pathology proposal, lightweight BR2 representation retrieval, and faithful SIP have independent value
- Do not: start Batch8, reuse the current M10 prototype/spatial dictionary as the paper mechanism, train refiner/arbiter/production gate, replace the backbone, expand folds, train Cine, upload validation, or start another open-ended repair cycle

## 总体判断

Batch 7 repair 已证明当前联合 proposal chain 不够好，但 proposal stage 仍使用混合 M10 loss，不能作为纯 proposal 或 R2/BR2 的最终否定。当前复杂 16-slot spatial dictionary、prototype maps 和 semantic negative memory 也没有显示足够增益。

本计划保留 Representation Retrieval Learning for Heterogeneous Data Integration 的核心论文主线，但不保留当前具体 dictionary 实现。最终实验比较三种同病种模型：普通 minimal proposal、轻量 BR2 retrieval、轻量 BR2 retrieval 加正式 SIP。

## 固定来源

```text
planner amendment base: c99aeb937e45ac01d87782ada35cac5c60aa6a54
controller must bind latest remote main before execution: true
source checkpoint: Batch7 step300
source checkpoint SHA256: d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
fold0 train/validation: 176/44
runtime: anchor_bounded_srr_correction
formal decode: outputs["logits"].argmax
```

## 三种候选

### 1. Minimal proposal

只保留冻结的 modality encoders/base retrieval、目标病种 evidence head、anchor-free discovery、anchor-conditioned confirmation 和 reliability fusion。关闭所有 representer dictionary、prototype、memory、refiner、arbiter 和 production-gate 学习。

### 2. Lightweight BR2 retrieval without SIP

在 minimal 基础上增加轻量 representer dictionary：

```text
shared anatomy
LGE private
C0 private
T2 private
LGE-C0 interaction
LGE-T2 interaction
T2-C0 interaction
```

要求：

- 每个 representer 是独立可训练模块，不能只是同一 feature tensor 的别名；
- router 输入只包含图像特征与 availability，不得输入 center；
- 缺少所需模态的 representer 在 normalization 前 hard-mask；
- observed-modality pattern 为 source：LGE-only、LGE+C0、LGE+T2+C0；
- 每个 source pattern 有可审计的 source-level learner coefficients $\beta_d^{(s)}$；
- 可加 image-conditioned residual，但最终 gate 必须输出 source coefficient、residual 和合成权重；
- 使用每-source $\ell_1$ 稀疏项选择少量 representers；SIP 权重为零。

不得使用当前 M10 16-slot spatial dictionary、prototype maps 或 semantic negative memory。

### 3. Lightweight BR2 retrieval with SIP

与 `br2_no_sip` 使用完全相同的结构、初始化、source coefficients、病例序列、patch 和优化器，只增加正式 BR2-SIP。

对 representer $d$，令 $O_d$ 为能够观察其所需模态的 source patterns：

$$\widetilde\gamma_d(\tau)=\sum_{s\in O_d}\min\left(1,\frac{|\beta_d^{(s)}|}{\tau}\right),$$

$$P_{SIP}=\sum_{d:|O_d|>1}\min\left(1,\frac{|O_d|-\widetilde\gamma_d(\tau)}{|O_d|-1}\right).$$

$|O_d|\le1$ 的 representer 不进入 SIP。SIP 必须直接作用于 source-level learner coefficients，不能用 entropy、load balance、slot prior、prototype similarity 或 batch-average gate 代理。

## 现有 SIP 处理决定

当前代码中的：

```text
semantic_retrieval_regularization
pattern_sip_integrativeness_loss
```

保留用于历史复现，但在本计划六个正式实验中必须固定为零，并在输出中标为 `legacy_heuristic_not_paper_sip`。新增正式 loss 必须命名为：

```text
loss_br2_source_l1_sparsity
loss_br2_selective_integration_penalty
```

禁止将旧 Pattern-SIP 重命名后继续使用。

## Loss authority

所有实验必须生成 `resolved_stage_loss_weights.csv`。共同允许的目标病种损失：

```text
proposal BCE/Dice: 1.0
discovery BCE/Dice: 1.0
confirmation BCE/Dice: 0.5
anchor-missed-lesion recovery: 1.0
anchor-false-positive suppression: 0.10
no-T2 edema safety: 0.50（仅 edema）
```

BR2 variants额外允许：

```text
loss_br2_source_l1_sparsity: 0.01
loss_br2_selective_integration_penalty:
  no_sip = 0.0
  sip = 从 {0.005,0.01,0.02} 按固定 gradient-ratio rule 选择
SIP tau: 0.10
```

选择规则：在固定 train-only calibration cohort 上分别计算 pathology loss 与 SIP 的梯度范数，选择使 SIP/pathology gradient ratio 最接近 0.10 且位于 `[0.03,0.20]` 的候选；若无候选位于区间，选择最接近 0.10 的候选，但 ratio 必须仍在 `[0.01,0.30]`，否则训练前阻塞。选择结果必须写入 `sip_weight_calibration.csv`，不得由 Executor 主观挑选。

以下必须为零：另一病种、anatomy、refiner、final-logits、arbiter、production gate、branch arbitration、correction opportunity、bounded correction、refiner effect、prototype、memory、semantic negative memory、generic load balance、legacy semantic regularization、legacy Pattern-SIP。

每个非零 loss 必须单独 backward，证明梯度只进入目标病种与授权的轻量 BR2 模块。不得对 logits 均值 backward 充当 loss 验收。

## 实验矩阵

六个实验均从相同 source checkpoint 独立开始，每个 400 optimizer steps，在 200/400 对全部 44 例评价：

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

同病种三组必须共享：

```text
seed
病例序列
patch centers
optimizer
步数
评价与 decode
minimal 共有模块初始化
br2_no_sip 与 br2_sip 的全部 BR2 参数初始化
```

Scar 必须保证 scar-positive 与 anchor-error patch sampling；edema 只从 T2-present edema-supervised病例采样，不得将 no-T2病例作为 edema negative。no-T2 edema整条链必须严格为零。

## 实现硬门

训练前必须通过：

1. 六组完整 resolved loss，空 `{}` 配置和任一历史混合 loss 非零均被 validator拒绝；
2. `br2_no_sip` 与 `br2_sip` 除 SIP weight外结构、初始化和数据 manifest完全相同；
3. minimal forward 不创建或消费 BR2 parameters；
4. invalid representers在 softmax前为 `-inf`/等价 hard mask，最终权重严格零；
5. source coefficients只由 availability pattern索引，center不进入模型输入；
6. source coefficient、image residual、final retrieval weights分别输出并保存；
7. 实现论文公式的数值单元测试，包括 $\gamma\le1$ 同罚、完全共享罚为零、$|O_d|\le1$ 排除；
8. known-bad：旧 Pattern-SIP冒充新 SIP、batch-average gate代理、center-conditioned router、重复 representer、未 hard-mask均必须失败；
9. anchor-free discovery覆盖 LGE-only scar、T2-present edema、CenterC complete tri-modal；
10. checkpoint save/reload final logits最大差 `<=1e-6`。

## 保留与删除门

### Minimal proposal

```text
positive-case Dice delta >= +0.003
help >= harm
HD95 relative worsening <=5%
remote-FP relative worsening <=5%
no-T2 edema exact zero
```

### Lightweight BR2 retrieval

`br2_no_sip` 或 `br2_sip` 中较优者相对 minimal：

```text
additional positive-case Dice >= +0.001
help/harm not worse
HD95 and remote-FP not worse by >2%
```

未通过则删除该病种轻量 BR2 retrieval；这只否定当前医学影像适配，不写成否定原论文。

### SIP

`br2_sip` 相对 `br2_no_sip`：

```text
additional positive-case Dice >= +0.0005
或 Dice下降不超过0.0005且HD95或remote-FP改善>=2%
help/harm not worse
```

未通过则从最终 objective 删除 SIP，并明确禁止论文声称 SIP 带来性能提升；BR2 retrieval若自身通过仍可保留。

Scar minimal仍为负时，停止 scar SRR correction；不允许用 BR2、refiner或gate继续挽救。Edema按同样标准独立判断。

## 终态输出

```text
results/20260722_srr_batch7_minimal_pathology_decomposition/
```

至少包含：

```text
resolved_stage_loss_weights.csv
loss_specific_gradient_matrix.csv
sip_formula_unit_tests.json
sip_weight_calibration.csv
representer_parameter_manifest.csv
availability_mask_checks.csv
source_learner_coefficients.csv
retrieval_weight_diagnostics.csv
anchor_free_discovery_coverage.csv
matched_run_manifest.csv
checkpoint_selection.csv
pathology_decision_matrix.csv
br2_increment_matrix.csv
sip_increment_matrix.csv
casewise_metrics.csv
subgroup_metrics.csv
help_harm.csv
slurm_attempts.csv
controller_report.md
completion_check.md
MANIFEST.md
```

Controller 必须返回：

```text
scar_minimal: RETAIN | RETIRE
scar_br2: RETAIN | RETIRE | NOT_APPLICABLE
scar_sip: RETAIN | REMOVE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_br2: RETAIN | RETIRE | NOT_APPLICABLE
edema_sip: RETAIN | REMOVE | NOT_APPLICABLE
```

本任务结束后返回 Planner，不自动进入 refiner、arbiter、gate 或 Batch8。