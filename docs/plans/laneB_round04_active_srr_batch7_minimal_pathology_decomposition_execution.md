# CARE SRR Batch 7 轻量中心分层 BR2 / SIP 病种分解执行计划

Plan metadata:
- Type: active execution plan
- Lane: historical Route B lineage on main
- Round scope: round04 post-portfolio main-only
- Status: ready for controller after comprehensive architecture amendment
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_batch7_mechanism_closure_repair_execution.md`
- Function: determine whether minimal pathology proposal, deployable lightweight BR2 representation retrieval, and faithful SIP have independent value
- Do not: start Batch8, reuse the current M10 prototype/spatial dictionary as the paper mechanism, train refiner/arbiter/production gate, replace the backbone, expand folds, train Cine, upload validation, or start another open-ended repair cycle

## 一、结论

R2 / BR2 仍是值得保留的论文主线，但上一版计划仍把 availability pattern误当成论文中的 data source，并允许 image-conditioned residual和softmax式权重绕开 source learner coefficient。若直接执行，SIP即使有数值也不具备论文含义。

本计划改为一次最终的、可部署的中心分层BR2实验：

```text
训练 source = 采集中心
source observation set = 该中心实际可用模态
部署 source = 仅按 availability pattern 选择的共享系数
center 只用于训练期 source index和均衡采样
center 绝不进入图像网络或推理输入
```

权威审计：

```text
results/srr_production/code_maturity/batch7_br2_sip_comprehensive_architecture_audit_20260722.md
```

## 二、论文思想与CARE适配边界

论文R2使用共享representer dictionary和source-specific稀疏learner coefficients。BR2通过每模态dictionary和observation indicator避免缺失模态插补。SIP直接在跨source的learner coefficients上定义representer integrativeness。

CARE与论文不同：

1. CARE是3D密集分割，不是标量回归；
2. 模态缺失与中心强绑定；
3. no-T2病例没有可靠edema监督；
4. challenge部署不能依赖中心ID；
5. 原论文的固定dictionary、bounded representer和Lipschitz理论不能直接当作本模型保证。

因此最终论文只能表述为 `R2/BR2/SIP-inspired medical imaging adaptation`，不能声称原excess-risk theorem已覆盖本任务，也不能声称因果上消除了center与missingness混杂。

## 三、固定来源

```text
planner amendment base: 12f1eca3482741a45bd0f440941791a42a2e581c
controller must bind latest remote main before execution: true
source checkpoint: Batch7 step300
source checkpoint SHA256: d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
fold0 train/validation: 176/44
runtime: anchor_bounded_srr_correction
formal decode: outputs["logits"].argmax
```

## 四、Source与监督定义

### 1. 训练source

训练source由 `metadata.center` 定义。Executor必须从真实metadata重建并核对：

```text
CenterA / CenterH: LGE-only
CenterB / CenterC: LGE+T2+C0
CenterE / CenterF / CenterG: LGE+C0
```

如果fold0实际metadata与上述关系不一致，必须在训练前阻塞并报告，不得静默改source定义。

Center ID只能：

- 索引训练期source coefficient；
- 执行source-balanced sampling；
- 生成分中心诊断。

Center one-hot、名称、编号或统计量不得拼接到encoder、representer、proposal或任何router输入。

### 2. 部署source

部署和44例正式评价不得使用中心专属coefficient，只能使用availability pattern对应的共享coefficient：

```text
LGE-only
LGE+C0
LGE+T2+C0
```

### 3. 病种监督source

- Scar：使用所有可靠scar监督中心；
- Edema：只使用T2-present且有可靠edema监督的中心；
- no-T2中心不建立edema coefficient、不进入edema SIP、不进入edema loss，也不能作为edema negative。

## 五、三种候选

### 1. Minimal proposal

只保留冻结的modality encoders/base retrieval、目标病种evidence head、anchor-free discovery、anchor-conditioned confirmation和reliability fusion。关闭全部BR2、prototype、memory、refiner、arbiter和production-gate学习。

### 2. Lightweight BR2 without SIP

在minimal的全分辨率病种feature上增加7个小型representers：

```text
shared anatomy
LGE private
C0 private
T2 private
LGE-C0 interaction
LGE-T2 interaction
T2-C0 interaction
```

每个representer必须：

- 有独立参数，不能是同一tensor的别名；
- 末层零初始化，使BR2初始行为等于minimal；
- private只读取本模态；
- interaction读取两模态归一化特征、逐点乘积和绝对差；
- 在乘learner coefficient前归一到固定per-case RMS；
- 缺失任何所需模态时输出权重严格为零。

### 3. Lightweight BR2 with SIP

结构、初始化、病例、patch、优化器和训练顺序与no-SIP完全相同，只增加正式SIP项。

## 六、Learner coefficient与部署规则

论文coefficient可正可负，不是softmax概率。正式实现禁止softmax、simplex、top-k归一和image-conditioned coefficient residual。

对病种 `p`、representer `d`、训练中心 `c`：

$$
\beta_{p,d}^{(c)}=\bar\beta_{p,d}^{(a_c)}+\delta_{p,d}^{(c)},
$$

其中 `a_c` 是中心的availability pattern，并满足：

$$
\sum_{c:a_c=a}\delta_{p,d}^{(c)}=0.
$$

训练forward使用 `beta^(c)`；验证与部署只使用 `bar beta^(a)`。`delta`使用显式L2 shrinkage，防止模型记忆中心风格。

BR2 feature定义为：

$$
h_p^{BR2}=h_p^{minimal}+W_p\left(\sum_d I_d(a)\beta_{p,d}\widetilde\theta_{p,d}(x)\right),
$$

其中 `W_p` 零初始化，`I_d(a)` 是availability hard mask，`theta-tilde` 已固定RMS尺度。

## 七、SIP定义与保留决定

当前代码中的：

```text
semantic_retrieval_regularization
pattern_sip_integrativeness_loss
```

只能历史复现，六个正式实验权重必须为零，并标记 `legacy_heuristic_not_paper_sip`。

对病种 `p` 和representer `d`，令 `O_(p,d)` 为同时满足所需模态和可靠病种监督的训练中心集合：

$$
\widetilde\gamma_{p,d}(\tau)=\sum_{c\in O_{p,d}}\min\left(1,\frac{|\beta_{p,d}^{(c)}|}{\tau}\right),
$$

$$
P_{SIP}^{(p)}=\sum_{d:|O_{p,d}|>1}\min\left(1,\frac{|O_{p,d}|-\widetilde\gamma_{p,d}(\tau)}{|O_{p,d}|-1}\right).
$$

要求：

- `|O_(p,d)|<=1` 时排除；
- no-T2或无可靠edema监督中心不计入edema SIP；
- 系数使用绝对值并保持signed预测；
- representer RMS固定后才允许使用 `tau=0.10`；
- SIP直接作用于训练中心coefficient，不得用batch-average gate、熵、load balance或slot prior代理。

SIP权重从 `{0.005,0.01,0.02}` 通过固定train-only、center-balanced cohort的gradient-ratio规则选择，结果写入 `sip_weight_calibration.csv`，Executor不得主观挑选。

## 八、Source-balanced训练和优化顺序

Batch size为1，采样顺序必须是：

```text
均匀选择该病种合格中心
-> 中心内均匀选择病例
-> 选择病灶或anchor-error patch
```

每个中心的采样次数必须写入manifest，最大偏差不得超过配置。

每个BR2 run仍为400步：

```text
1-50: representer冻结，训练pattern/center coefficients与目标病种heads
51-350: coefficient block和representer/pathology block交替更新
351-400: representer冻结，校准coefficients与目标病种heads
```

Minimal使用相同病例和patch序列训练目标病种heads。No-SIP和SIP必须共享第50步warmup状态，只允许SIP权重不同。

## 九、Loss authority

所有实验必须生成完整 `resolved_stage_loss_weights.csv`。只允许：

Scar：

```text
scar proposal BCE/Dice
scar discovery BCE/Dice
scar confirmation BCE/Dice
anchor-missed scar recovery
anchor false-positive scar suppression
```

Edema：

```text
T2-present edema proposal BCE/Dice
T2-present edema discovery BCE/Dice
T2-present edema confirmation BCE/Dice
T2-present anchor-missed edema recovery
T2-present anchor false-positive edema suppression
no-T2 exact-zero safety
```

BR2额外允许：

```text
loss_br2_source_l1_sparsity
loss_br2_center_deviation_shrinkage
loss_br2_selective_integration_penalty（仅SIP组）
```

另一病种、anatomy、refiner、final logits、arbiter、production gate、branch arbitration、correction opportunity、bounded correction、prototype、memory、generic dictionary loss和旧Pattern-SIP均必须为零。

每个非零loss必须单独backward，证明梯度只进入目标病种和授权模块。禁止再次用logits均值代替loss authority。

## 十、六个匹配实验

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

每个400 optimizer steps，在200/400评价全部44例。同病种三组共享checkpoint、seed、source-balanced病例序列、patch centers、optimizer、预算、decode和共有模块初始化；两个BR2组还共享全部BR2参数和第50步warmup状态。

## 十一、实现硬门

训练前必须通过：

1. 中心-模态inventory和病种source eligibility与真实metadata一致；
2. availability-only被当作训练source的实现必须失败；
3. center只作为训练coefficient index，任何center-conditioned网络输入必须失败；
4. coefficient为signed全局标量；softmax/simplex、per-image residual必须失败；
5. representer输出固定RMS，缩放representer并反向缩放beta不能绕过L1/SIP；
6. minimal不实例化或消费BR2；
7. no-SIP与SIP结构、初始化、warmup状态和数据完全一致；
8. invalid representer的effective beta精确为零；
9. no-T2 source不得出现在edema beta、SIP或loss中；
10. 新SIP公式、signed coefficient、eligible-source和tau单元测试通过；
11. 旧Pattern-SIP改名、batch-average gate代理、重复representer、validation使用center beta均作为known-bad失败；
12. anchor-free discovery覆盖LGE-only scar、T2-present edema和CenterC complete tri-modal；
13. checkpoint save/reload final logits最大差 `<=1e-6`。

## 十二、评价与保留门

除positive-case Dice、HD95、remote FP和help/harm外，必须报告：

```text
complete-trimodal subgroup
CenterB / CenterC及所有有正例中心
worst-center Dice delta
proposal precision / recall / lesion-wise recall
anchor-missed recovery / false-positive suppression
beta_pattern / beta_center / center deviation
representer RMS / effective beta / integrativeness
source-balanced sampling counts
```

Minimal保留：

```text
positive-case Dice delta >= +0.003
help >= harm
HD95和remote-FP恶化 <=5%
complete-trimodal Dice不下降
no-T2 edema严格为零
```

BR2保留：相对minimal额外Dice `>=+0.001`，安全不恶化，complete-trimodal不下降，worst positive center下降不超过`0.003`。

SIP保留：相对no-SIP额外Dice `>=+0.0005`；或Dice下降不超过`0.0005`且HD95/remote-FP改善至少2%，同时complete-trimodal、worst-center和help/harm不恶化。

Scar minimal仍为负时，停止scar SRR correction；不得用BR2、refiner或gate补救。SIP失败只删除SIP，不自动删除有效BR2。

## 十三、终态输出

```text
results/20260722_srr_batch7_minimal_pathology_decomposition/
```

至少包含：

```text
center_modality_inventory.csv
pathology_source_eligibility.csv
source_balanced_sampler_manifest.csv
resolved_stage_loss_weights.csv
loss_specific_gradient_matrix.csv
sip_formula_unit_tests.json
sip_weight_calibration.csv
representer_parameter_manifest.csv
representer_scale_checks.csv
beta_hierarchy_checks.csv
availability_mask_checks.csv
source_learner_coefficients.csv
integrativeness_diagnostics.csv
proposal_mechanism_metrics.csv
anchor_free_discovery_coverage.csv
matched_run_manifest.csv
checkpoint_selection.csv
pathology_decision_matrix.csv
br2_increment_matrix.csv
sip_increment_matrix.csv
deployment_subgroup_metrics.csv
casewise_metrics.csv
subgroup_metrics.csv
help_harm.csv
claim_boundary.md
slurm_attempts.csv
controller_report.md
completion_check.md
MANIFEST.md
```

Controller必须返回：

```text
scar_minimal: RETAIN | RETIRE
scar_br2: RETAIN | RETIRE | NOT_APPLICABLE
scar_sip: RETAIN | REMOVE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_br2: RETAIN | RETIRE | NOT_APPLICABLE
edema_sip: RETAIN | REMOVE | NOT_APPLICABLE
```

本任务结束后返回Planner，不自动进入refiner、arbiter、gate或Batch8。