# CARE 当前开发状态

## 2026-07-29 当前最高优先级：CARE-PRISM 系统重设计

CARE-ARC v2 的 W0–W2 执行闭环有效，但 W3 fold0 3000-step development 没有证明直接完整重建能力。更重要的是，最新代码审计确认 W3 并非单纯 `CONTOUR_LIMITED`：病种 evidence gates、anatomy guidance 和 coarse proposal没有进入最终病理计算链；same-fold nnU-Net初始化未执行；SDF auxiliary loss出现负值捷径；训练缺少正式增强、真实病例均衡和checkpoint selection。因此 CARE-ARC W3只保留为实现与设计双重失败的诊断证据，不再是active architecture。

新的唯一主线是：

```text
CARE-PRISM
Pathology-specific Retrieval,
Internal-anatomy Exchange,
and Soft-cascade Multi-scale Reconstruction
```

```text
state_id: care_prism_system_redesign_20260729
state_updated_date: 2026-07-29
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED_MAIN_ONLY
single_active_scientific_line: CARE_PRISM_FOLD0_DEVELOPMENT_THEN_CLEAN_FOLD1
method_name: CARE-PRISM
execution_code: CARE-PRISM-W0-W5
controller_is_coordinator: true
planning_review_required: false
review_required: false
fold1_outer_accessed: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
runtime_git_push_authorized: false
```

## 当前权威入口

```text
blueprint:
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md

executor_plan:
prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan.yaml

controller:
prompts/tasks/20260729_care_prism_controller.md
```

规划提交：

```text
00c2d44cb2670063ce56846beec4ae4f3b70d3f6  CARE-PRISM blueprint
5981803ccbc27891da3b599e2388c0e7b47f0921  executor plan
864ac0a276098ed242161e458a0b12f30353076d  controller contract
```

冲突优先级：

```text
CARE-PRISM blueprint
> CARE-PRISM executor plan
> CARE-PRISM controller
> 本CURRENT.md
> CARE-ARC v2 files
> 历史 DPR / DG / Cascade / MMRD / SRR contracts
```

## CARE-ARC W3 冻结事实

W3结果：

```text
scar raw direct Dice:       0.392694
nnU-Net scar Dice:          0.573196
delta:                     -0.180502

edema-zone raw direct Dice: 0.439734
nnU-Net edema-zone Dice:    0.595098
delta:                     -0.155363
```

同时：

```text
scar remote FP:       1377.97 vs nnU-Net 645.67
edema-zone remote FP: 4073.88 vs nnU-Net 793.95
scar HD95:            30.71 vs nnU-Net 13.60
edema-zone HD95:      32.73 vs nnU-Net 14.53
```

当前必须使用的根因判断：

```text
operational W0-W2: PASS
formal W3 training completion: PASS
implementation fidelity: FAIL
training adequacy: FAIL
architecture mechanism: FAIL
old classification CONTOUR_LIMITED: INCOMPLETE / SUPERSEDED
fold1 clean evidence consumed: NO
```

已确认实现缺口：

1. `scar_gates` / `edema_gates`只输出审计值，未参与特征或logit；
2. anatomy decoder输出未进入病理decoder；
3. coarse head未生成soft ROI或调制direct decoder；
4. SDF logvar loss与最终mask脱节，并造成负loss捷径；
5. W3随机初始化，没有same-fold nnU-Net权重移植；
6. 无正式空间/强度增强；
7. sampler不是每step scar+edema双病例，也没有center×burden均衡；
8. train alignment enabled而冻结deployment为identity；
9. 只评价terminal step3000；
10. no-T2 logit=0不等于probability exact zero。

## CARE-PRISM 冻结结构

```text
LGE/T2/C0 + availability
→ one same-fold nnU-Net-initialized shared ResEnc backbone
→ lightweight modality-private feature pyramids
→ scar/edema real soft retrieval at multiple scales
→ internal anatomy decoder
→ anatomy-pathology feature exchange at every decoder scale
→ scar/edema coarse proposal
→ positive / safe-negative EMA prototype margins
→ one myocardium-neighborhood soft ROI per pathology
→ scar high-resolution full-lesion refiner
→ edema large-context full-lesion refiner
→ direct edema-zone
→ scar priority
→ pure edema = edema-zone - scar
```

强制边界：

- 只有一个完整shared backbone；
- same-fold nnU-Net只作权重初始化和最终非病理结构来源，不进入pathology forward；
- router必须真实作用于特征；
- anatomy和proposal必须真实进入refiner；
- proposal为空仍使用anatomy ROI，不得hard delete；
- no-T2不能生成任何edema监督或safe-negative myocardium；
- 不允许MoSAIC runtime、MMRD teacher、第二U-Net、多backbone、nnU-Net pathology residual、DPR component utility、ADD/REVISE、完整SRR dictionary/SIP/top-k；
- 所有正式loss非负、有限并具有真实梯度；
- scar与edema独立报告，不允许scar掩盖edema。

## 执行图

```text
W0 root-cause / split / nnU-Net asset freeze
→ W1 exact implementation and known-bad
→ W2 400-step zero-credit preflight
→ W3 fold0 6500-step development
→ only if W3 passes: W4 fold1 8000-step clean evaluation
→ W5 terminal accounting / aggregation / validator / Mapper / local commit / email
```

W3必须先证明：

- encoder初始化覆盖率>=90%；
- anatomy ROI coverage>=0.98；
- scar/edema proposal lesion recall>=0.80/0.90；
- refiner相对proposal Dice各提高>=0.05；
- prototype margin AUROC>=0.70；
- router不collapse；
- scar/edema均不低于nnU-Net超过0.03；
- 至少一个主病理提高>=0.005；
- HD95和remote FP<=1.20x anchor；
- no-T2 exact zero。

实现错误必须在同一Controller goal内修复。W3真正机制失败时返回Planner做下一次完整系统重设计，但不得写项目放弃或恢复nnU-Net-only为研究终态。

## 唯一计算资源

```text
interactive job: 61220581
partition: htzhulab
node: g1807htzh01
gpu: H100 NVL
```

所有GPU命令只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

严格禁止：

```text
sbatch
salloc
新Slurm job
并行GPU进程
写 /overflow/htzhu/CARE
validation upload
Docker upload
runtime git push
```

若allocation终止，只能记录精确resume point并返回`OPERATIONALLY_BLOCKED`；不得新建job。

## 图视觉门

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD, CARE-SRR-Cascade, CARE-DG, CARE-ARC, MoSAIC
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_route_objective: availability-aware modality evidence -> anatomy-guided lesion proposal -> pathology-specific full-lesion refinement -> safety audit
key_revision: actual routed features + actual anatomy exchange + proposal-to-refiner soft cascade; remove unused decorative modules and anchor-neighborhood correction
```

## 历史证据边界

以下只作诊断背景，不是active authority：

```text
results/20260729_care_arc_clean_fold1
results/20260728_care_dpr_fold0_global_redesign
results/20260724_care_myops_srr_cascade_submission_rescue
results/20260722_care_myops_batch9_reliable_label_distillation
results/route_B
results/route_C
```

## 当前未授权

```text
恢复CARE-ARC fold1
恢复DPR Gate B-R2
新Cine训练
额外完整backbone或ensemble
MoSAIC runtime/权重
外部数据或外部foundation model
fold1 outer调参或第二次评价
validation/Docker upload
hosted metric claim
route promotion
runtime git push
```
