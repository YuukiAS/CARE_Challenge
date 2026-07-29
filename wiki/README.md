# CARE 架构 Wiki

architecture_version: `care-prism-v2-hardened-design-20260729`  
latest_verified_runtime: `CARE-ARC W3 terminal diagnostic complete; PRISM v2 planned, unimplemented`  
latest_scientific_status: `CARE-ARC W3 superseded by implementation+design root-cause audit; CARE-PRISM v2 is the only active scientific line`  
latest_controller_task: `20260729_care_prism_fold0_fold1_v2`  
route_status: `MAIN_ONLY_PRISM_V2_PLANNED_UNVERIFIED`

本页是当前 CARE 架构根入口。最新判断不是“CARE-ARC 轮廓略差”，而是旧系统同时存在未接入的 router/anatomy/proposal、随机主干、负损失捷径、采样与增强不足、训练部署错位和小病灶负空间缺失。CARE-PRISM v2 因此不再修补普通 dense decoder，而是建立精确同折初始化、病种专属证据、单向解剖交换、proposal/negative-space 和全体积连续软级联的完整链路。

当前机器真值：`prompts/routes/handoffs/CURRENT.md`。

## 当前权威

```text
highest authority:
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md

base blueprint:
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md

executor plan:
prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan_v2.yaml

controller:
prompts/tasks/20260729_care_prism_controller_v2.md
```

```text
fa3fc6aa23976f26e1523d5c99c98470cdc43b7c  hardening amendment v2
1245ce5d2c1799f750b5cfa39f94047b76d1ef07  executor plan v2
f5a2ebfc6d673d25021540c58ee98bf54329a757  controller v2
a446572241b5c80916d1fba21860aad1db39b9d2  CURRENT v2
```

## CARE-ARC W3 冻结负结果

```text
scar Dice:       0.392694 vs nnU-Net 0.573196, delta -0.180502
edema-zone Dice: 0.439734 vs nnU-Net 0.595098, delta -0.155363
scar HD95:       30.71 vs 13.60
edema HD95:      32.73 vs 14.53
scar remote FP:  1377.97 vs 645.67
edema remote FP: 4073.88 vs 793.95
fold1 outer accessed: NO
```

该结果的操作闭环成立，但不是忠实 CARE-ARC 机制负结果。已确认：router未参与最终计算、anatomy与coarse head均是辅助-only、SDF与最终mask脱节、same-fold nnU-Net移植未执行、W3无正式增强与真实中心/负荷采样、alignment训练部署错位、只评价terminal checkpoint、no-T2 logit零不等于概率零。

## CARE-PRISM v2 数据流

```text
LGE/T2/C0，缺失通道置零
→ exact 3-channel shared ResEnc encoder
   └─ same-fold Dataset501 nnU-Net initialization and FP32 scale parity
→ lightweight modality-private pyramids
→ scar/edema multi-scale soft retrieval
→ optional reliable soft slice correspondence, identity default
→ internal anatomy decoder
→ stop-gradient, zero-initialized anatomy→pathology exchange
→ learned positive evidence + four safe-negative categories
→ optional zero-init gated cross-case prototype residual
→ full-volume continuous anatomy/proposal attention
→ scar high-resolution full-lesion refiner
→ edema large-context full-lesion refiner
→ direct edema-zone
→ scar priority
→ pure edema = edema-zone - scar
```

### 共享主干

- 输入保持源 nnU-Net 精确 `[LGE,T2,C0]` 三通道，availability 不得拼入 shared encoder；
- 参数字节移植覆盖率 `>=0.90`；
- CARE modules关闭、同一FP32病例时，各对应encoder尺度最大误差 `<=1e-6`；
- nnU-Net只作同折初始化、最终非病理结构来源和审计，不提供病理概率或残差。

### 检索与解剖

- router只读图像特征与availability，不读center ID；
- missing modality权重严格为零，shared权重下限0.20；
- matched modality ablation必须证明LGE对scar、T2对edema的病种特异贡献；
- anatomy只单向进入病理，pathology gradient不得污染anatomy decoder；
- 每尺度交换为零初始化residual gate，必须通过on/off最终logit干预。

### Proposal、负空间与软级联

- Proposal核心由learned positive evidence和category-specific negative logits构成，不依赖prototype才能工作；
- scar安全负类：正常心肌、血池、union外背景、LGE亮伪影/历史远端FP；
- edema安全负类：只来自T2-present病例；no-T2 myocardium永远不是负类；
- 取消bbox/crop/paste与GT ROI curriculum；使用全体积连续attention，所有体素保留至少0.25信息底噪；
- prototype为可降级增强：read-before-update、当前病例排除、零初始化gate；cross-case probe或matched control失败时固定关闭。

### 损失

```text
0.50 anatomy
+ 0.35 proposal
+ 1.00 refinement
+ 0.15 safe-negative discrimination
+ 0.10 burden
+ 0.05 soft scar-edema relation
+ 0.02 router anti-collapse in Stage A/B
+ optional 0.05 prototype when enabled
```

Scar固定使用 DiceCE + Focal-Tversky + component-adaptive Tversky/lesion-MIL + Generalized Surface Loss；edema固定使用 DiceCE + Focal-Tversky + Generalized Surface Loss。实例/表面项仅在 Stage C 后半启用，不能替代 proposal 机制。删除断开的 SDF uncertainty head。

## 实现和训练门

```text
W0 root-cause, split and nnU-Net asset freeze
→ W1 exact implementation, causal interventions and known-bad
→ W2 400-step real-case zero-credit preflight
→ W3 fold0 6500-step development, all-checkpoint inner selection
→ W4 only after W3 pass: fold1 8000-step clean atomic outer evaluation
→ W5 terminal accounting, aggregation, validator, Mapper and local commit
```

W3需同时满足：

```text
transplant coverage >=0.90; FP32 parity <=1e-6
anatomy soft-band GT coverage >=0.98
scar/edema proposal recall >=0.80/0.90
scar/edema refiner gain >=0.03/0.02 Dice
modality-causal ablations PASS
anatomy exchange non-harm
negative-space remote-FP reduction >=10%, recall loss <=0.02
scar and edema-zone delta vs nnU-Net >=-0.02
at least one main pathology delta >=+0.01
HD95 and remote-FP ratio <=1.10
no-T2 probability/mask/loss/gradient exact zero
prototype evidence reported but not mandatory
```

Controller必须监督普通实现、OOM、cache、sampler、augmentation、loss、resume、评价和validator问题在同一目标内修复。只有忠实实现、足额训练、全部checkpoint重载评价后仍失败，才允许按 routing、anatomy、proposal、negative-space、refinement 或 calibration 返回Planner。

## 资源与权限

唯一已授权GPU allocation为 `61220581 / htzhulab / g1807htzh01 / H100 NVL`。若仍存活，只能串行使用：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

Allocation终止时只记录resume point并返回operational block；禁止申请新job、写`/overflow/htzhu/CARE`、runtime push、validation/Docker upload或hosted claim。

## 视觉与历史边界

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD, CARE-SRR-Cascade, CARE-DG, CARE-ARC, MoSAIC
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_objective: availability-aware evidence -> selective retrieval -> anatomy-guided proposal -> pathology-specific refinement -> negative-space safety
```

历史证据保留在：

```text
results/20260729_care_arc_clean_fold1
results/20260728_care_dpr_fold0_global_redesign
results/20260724_care_myops_srr_cascade_submission_rescue
results/20260722_care_myops_batch9_reliable_label_distillation
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint
results/20260725_care_myops_mosaic_fold0_reproduction
results/route_B
results/route_C
wiki/history/
```

这些历史路线不再是active authority；当前不得恢复ARC/DPR、增加完整backbone/ensemble、使用MoSAIC/MMRD runtime、启动新Cine训练、读取fold1 outer调参、上传validation/Docker或runtime push。