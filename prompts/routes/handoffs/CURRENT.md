# CARE 当前开发状态

## 2026-07-29 当前最高优先级：CARE-PRISM v2

CARE-ARC W3 已确认同时存在实现不忠实、训练不足与设计机制缺口，不能再按单纯轮廓问题解释。原 CARE-PRISM 重设计方向保留，但 v2 进一步消除了四个潜在失败源：共享主干移植被 availability 改输入破坏、病理梯度污染 anatomy、硬 bbox/crop 造成不可微和训练部署错位、prototype/alignment 不稳定拖垮核心模型。

当前唯一主线为：**一个精确同折 nnU-Net 初始化的共享 ResEnc 主干，配合病种专属软检索、单向解剖交换、learned proposal 与 safe-negative discrimination、全体积连续软级联和独立 scar/edema refinement。Prototype 与切片对应都是独立证据门控制的可降级增强，不是核心模型的强依赖。**

```text
state_id: care_prism_v2_hardened_design_20260729
state_updated_date: 2026-07-29
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED_MAIN_ONLY
single_active_scientific_line: CARE_PRISM_V2_FOLD0_THEN_CLEAN_FOLD1
method_name: CARE-PRISM v2
execution_code: CARE-PRISM-V2-W0-W5
controller_is_coordinator: true
planning_review_required: false
review_required: false
fold1_outer_accessed: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
runtime_git_push_authorized: false
result_root: results/20260729_care_prism_fold0_fold1_v2
```

本文件是当前机器真值。新的实现、训练、评价与状态判断必须先读取本文件和下列最高权威文件。

## 当前权威入口

```text
highest_authority_amendment:
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md

base_blueprint:
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md

executor_plan:
prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan_v2.yaml

controller:
prompts/tasks/20260729_care_prism_controller_v2.md
```

规划提交：

```text
00c2d44cb2670063ce56846beec4ae4f3b70d3f6  CARE-PRISM base blueprint
fa3fc6aa23976f26e1523d5c99c98470cdc43b7c  PRISM v2 hardening amendment
1245ce5d2c1799f750b5cfa39f94047b76d1ef07  PRISM v2 executor plan
f5a2ebfc6d673d25021540c58ee98bf54329a757  PRISM v2 controller
```

冲突优先级：

```text
CARE-PRISM v2 hardening amendment
> CARE-PRISM base blueprint
> CARE-PRISM v2 executor plan
> CARE-PRISM v2 controller
> 本 CURRENT.md
> CARE-PRISM v1 files
> CARE-ARC v2 files
> 历史 DPR / DG / Cascade / MMRD / SRR contracts
```

## CARE-ARC W3 冻结事实

```text
scar raw direct Dice:       0.392694
nnU-Net scar Dice:          0.573196
delta:                     -0.180502

edema-zone raw direct Dice: 0.439734
nnU-Net edema-zone Dice:    0.595098
delta:                     -0.155363

scar remote FP:             1377.97 vs 645.67
edema-zone remote FP:       4073.88 vs 793.95
scar HD95:                  30.71 vs 13.60
edema-zone HD95:            32.73 vs 14.53
```

冻结根因：

1. router只输出审计张量，未进入特征或最终logit；
2. anatomy decoder未进入病理路径；
3. coarse proposal未调制refiner；
4. SDF auxiliary与最终mask脱节并出现负loss捷径；
5. W3随机初始化，未执行同折nnU-Net移植；
6. 无正式增强和真实中心×病灶负荷采样；
7. train/deploy alignment错位；
8. 只评价terminal checkpoint；
9. no-T2 logit=0不等于probability exact zero；
10. 普通full-volume dense decoder缺少病灶提议和安全负空间。

因此：

```text
operational W0-W2: PASS
formal W3 process completion: PASS
implementation fidelity: FAIL
training adequacy: FAIL
architecture mechanism: FAIL
old CONTOUR_LIMITED classification: SUPERSEDED
fold1 clean evidence consumed: NO
```

## CARE-PRISM v2 冻结结构

```text
[LGE,T2,C0] with missing channels zero
→ exact 3-channel same-fold nnU-Net-initialized shared ResEnc encoder
→ lightweight LGE/T2/C0 private pyramids
→ pathology-specific multi-scale soft retrieval
→ optional reliable soft slice correspondence, identity by default
→ internal anatomy decoder
→ stop-gradient zero-init anatomy→pathology exchange
→ learned positive evidence + category-specific safe-negative logits
→ optional gated cross-case prototype residual
→ full-volume continuous anatomy/proposal attention, no bbox crop
→ independent scar high-resolution refiner
→ independent edema large-context refiner
→ edema-zone direct probability
→ scar priority
→ pure edema = edema-zone - scar
```

强制边界：

- shared encoder输入必须保持精确三通道；availability不得追加到共享主干输入；
- encoder移植覆盖率按参数字节 `>=0.90`，FP32逐尺度奇偶误差 `<=1e-6`；
- pathology gradient不得进入anatomy decoder；
- anatomy、proposal与negative-space必须真实改变最终logit；
- 不允许hard bbox/crop、GT ROI部署依赖或variable-size paste；
- prototype只作proposal可选残差，未过独立门时固定关闭；
- no-T2 edema probability、mask、loss、gradient精确为零；
- 不允许第二完整backbone、MoSAIC/MMRD runtime、nnU-Net pathology residual、DPR utility、ADD/REVISE、完整SRR dictionary/SIP/top-k；
- 所有正式loss非负、有限且有目标参数梯度；
- scar与edema独立报告，不得由平均分掩盖。

## 执行图与门

```text
W0 authority / root-cause / split / nnU-Net assets
→ W1 exact implementation and executable known-bad
→ W2 400-step zero-credit real-case preflight
→ W3 fold0 6500-step development with all-checkpoint inner selection
→ only if W3 passes: W4 fold1 8000-step clean one-time outer evaluation
→ W5 terminal accounting / aggregation / validator / Mapper / local commit / email
```

W3核心门：

```text
transplant coverage >=0.90 and FP32 parity <=1e-6
anatomy soft-band GT coverage >=0.98
scar/edema lesion proposal recall >=0.80/0.90
scar/edema refiner gain over proposal >=0.03/0.02
matched modality-causal ablations PASS
anatomy exchange non-harm
negative-space remote-FP reduction >=10%, lesion-recall loss <=0.02
scar and edema-zone Dice delta vs nnU-Net >=-0.02
at least one main pathology delta >=+0.01
HD95 and remote-FP ratio <=1.10
router noncollapse and no-T2 exact zero
prototype PASS not mandatory; mode must be frozen
```

实现、权重移植、OOM、cache、sampler、augmentation、loss、resume、评价或validator问题必须由Controller在同一目标内持续修复。只有忠实实现、足额训练、全部checkpoint重载评价后仍未过门，才能按 routing、anatomy、proposal、negative-space、refinement 或 calibration 返回Planner。

## 唯一计算资源

```text
interactive job: 61220581
partition: htzhulab
node: g1807htzh01
gpu: H100 NVL
```

若allocation仍存活，所有GPU命令串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

若已终止，只记录精确resume point并返回 `OPERATIONALLY_BLOCKED`；禁止 `sbatch`、`salloc`、新Slurm job、并行GPU、写 `/overflow/htzhu/CARE`、runtime push、validation/Docker upload。

## 图视觉门

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD, CARE-SRR-Cascade, CARE-DG, CARE-ARC, MoSAIC
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_route_objective: availability-aware evidence -> selective retrieval -> anatomy-guided proposal -> pathology-specific full-lesion refinement -> negative-space safety
key_revision: exact transplant + one-way anatomy exchange + full-volume soft cascade + learned safe-negative core; optional correspondence/prototype are gated enhancements
```

## 历史证据与未授权边界

以下只作诊断背景：

```text
results/20260729_care_arc_clean_fold1
results/20260728_care_dpr_fold0_global_redesign
results/20260724_care_myops_srr_cascade_submission_rescue
results/20260722_care_myops_batch9_reliable_label_distillation
results/route_B
results/route_C
```

当前未授权：恢复ARC/DPR、额外完整backbone或ensemble、MoSAIC runtime/weights、外部数据或foundation model、新Cine训练、fold1 outer调参或二次评价、validation/Docker upload、hosted claim、route promotion、runtime push。