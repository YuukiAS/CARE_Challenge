# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 2026-07-29 当前最高优先级：CARE-ARC

当前主线已经从 nnU-Net 邻域内的 DG / DPR 局部修正，切换为 **CARE-ARC：单主干、双病理、直接完整重建**。

```text
state_id: care_arc_anchor_relaxed_complete_reconstruction_20260729
state_updated_date: 2026-07-29
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED_MAIN_ONLY
route_worktree_development_authorized: false
single_active_scientific_line: CARE_ARC_CLEAN_FOLD1
method_name: CARE-ARC Anchor-Relaxed Complete Reconstruction
execution_code: CARE-ARC-W0-W6
controller_is_coordinator: true
planning_review_required: false
review_required: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
runtime_git_push_authorized: false
```

### 当前权威入口

```text
blueprint:
prompts/blueprints/CARE_ARC_anchor_relaxed_complete_reconstruction_20260729.md

executor_plan:
prompts/tasks/20260729_care_arc_clean_fold1_executor_plan.yaml

controller:
prompts/tasks/20260729_care_arc_clean_fold1_controller.md
```

规划提交：

```text
e89d39528f9af0a0cb36a2694f651748847e4b41
845c2dfcf508d7a06ba85487cdd96d933e47f115
4801494ab62cca8b58ad10b7b8418fc705f222a8
```

冲突优先级：

```text
CARE-ARC blueprint
> CARE-ARC executor plan
> CARE-ARC controller prompt
> 当前 CURRENT.md
> 历史 DPR / DG / Cascade / MMRD contracts
```

## 为什么切换到完整重建

### Hidden validation 新证据

提交的 CARE 自研病理拼接探针不是统一端到端模型：

```text
scar: CARE-DG A3 step5000
edema: CARE-SRR-Cascade control_seed20260724 compact class4
myocardium/LV/RV: Dataset501 five-fold nnU-Net
CineMyoPS: frozen historical prediction tree
```

结果：

```text
CARE probe scar Dice / HD: 0.6211 / 15.1513
MoSAIC scar Dice / HD: 0.6965 / 13.7827
```

逐病例可视比较显示，CARE probe 的 scar 与 edema 几乎始终更接近 nnU-Net；MoSAIC 更倾向于完整、高召回、连续的病灶。该观察只用于架构动机，不能替代 hidden prediction tree 的逐体素审计。

### DPR Gate B-R1

R1 修复了 candidate-level 训练/推理错位，但 complete16 仍为：

```text
scar:       0.693335 -> 0.692643
edema-zone: 0.752194 -> 0.752104
pure edema: 0.394436 -> 0.394172
```

三项均未达到原 `+0.005` 科学门。

### DPR Gate B-R2 partial stop

最新终态证据：

```text
commit: f3cc5afa3cff7f2fbf8be8b6ec7945170839eac2
status: USER_STOPPED_BEFORE_GATE
gate_reached: false
rows_completed: 925 / 1200
eligible_rows: 0
best_avg_inner_dice_delta_so_far: -0.03193535188070074
fold1_started: false
validation_package_started: false
scientific_final_output_credit: 0
```

R2 接受更多 full-volume candidates 后，已完成的所有组合同时触发 Dice、HD95、remote FP 和 help/harm 失败。该证据说明不能继续通过 candidate utility 或 residual scale 把局部修补放大。

DPR-R2 现在是历史诊断证据，不再是 active controller lane。

## CARE-ARC 冻结科学目标

```text
[LGE,T2,C0] + availability
-> modality-specific residual stems
-> lightweight confidence-gated LGE-reference feature alignment
-> one CARE-owned ResEncM-style shared encoder
   -> internal anatomy decoder
   -> scar evidence gate -> coarse extent -> direct full scar reconstruction
      -> presence + contour mean/log variance
   -> edema evidence gate -> coarse extent -> direct edema-zone reconstruction
      -> presence + contour mean/log variance
-> scar priority
-> pure edema = edema-zone minus scar
```

强制边界：

- 主体只有一个 shared backbone；
- nnU-Net 只作为 same-fold encoder初始化、anatomy context、非病理输出和灾难性asset/grid fallback；
- nnU-Net scar/edema probabilities不得定义 CARE pathology output邻域；
- MoSAIC不得进入runtime、teacher、ensemble或初始化；
- 不允许MMRD teacher、第二个U-Net、多backbone、prototype、dictionary、router、component utility、ADD/REVISE arbitration；
- scar和edema结构对称、参数独立、分别训练和评价；
- no-T2 edema output/loss/gradient exact zero；
-三模态病例必须使用CARE direct pathology masks，不能因不同于nnU-Net而自动回退。

## 执行图

```text
W0 adoption and truth freeze
-> W1 implementation
-> W2 real-case preflight
-> W3 fold0 zero-credit development diagnostic
-> W4 fold1 clean 7000-step formal training
-> W5 clean gate / mapper final / packet
-> W6 only if clean gate passes: single-backbone full-data fit and local package dry-run
```

Fold0只作开发诊断，不再具有clean scientific privilege。第一次clean gate固定为fold1 outer，并且只能在fold1 train-side inner冻结checkpoint、scar/edema threshold、minimum component volume和presence rescue后评价一次。

## Clean fold1门

必须全部满足：

```text
scar / edema-zone / pure-edema Dice delta >= -0.005
scar或edema-zone至少一个 Dice delta >= +0.010
另一个主病理 Dice delta >= 0.000
每病理 help >= harm - 1
HD95 <= 1.05x anchor
无新增 infinite exact-HD
remote FP <= 1.10x anchor
positive-GT empty rate不高于anchor
scar和edema至少50% positive cases的changed pathology voxels ratio >=5%
两病理direct/presence/contour/alignment真实激活
no-T2 edema exact-zero
no-alignment control完整报告
```

未通过时不得在fold1上继续调参；必须分类为 execution、encoder、alignment、detection、contour 或 domain-calibration gap，返回Planner进行下一次完整修订。不得写项目放弃或将nnU-Net-only恢复为研究终态。

## 唯一计算资源

```text
interactive job: 61220581
partition: htzhulab
node: g1807htzh01
gpu: H100 NVL
state at latest receipt: RUNNING
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

若allocation终止，只能记录精确resume point并返回 operationally blocked；不得新建job。

## 图视觉门

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD, CARE-SRR-Cascade, MoSAIC
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_route_objective: availability-aware modality evidence -> anatomy-guided pathology localization -> scar/edema pathology-specific reconstruction -> safety supervision
key_revision: remove baseline-preserving pathology residual as the primary output mechanism
```

## Wiki边界

当前 root wiki仍主要描述 2026-07-26 baseline-only / SCR历史状态，视为 stale evidence。CARE-ARC实现完成前只能写 `planned/unverified`；W5 Mapper final 后才允许按真实代码和runtime证据更新：

```text
wiki/README.md
wiki/MODEL.md
wiki/EXECUTION.md
wiki/COMPONENTS.csv
wiki/LINEAGE.md
wiki/architecture.yaml
wiki/current_state.yaml
wiki/figures/*
```

## 历史状态保留

以下仍是有效历史证据，但不再是当前执行authority：

```text
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint
results/20260725_care_myops_mosaic_fold0_reproduction
results/20260728_care_dpr_fold0_global_redesign
results/20260724_care_myops_srr_cascade_submission_rescue
results/20260724_care_myops_batch10_deadline_rescue
```

MoSAIC hosted scar `0.6965`、本地 clean OOF弱于nnU-Net、DG/DPR围绕anchor修正不足、MMRD可靠标签卫生和Cascade安全回退，均作为CARE-ARC设计背景保留。

## 当前未授权

```text
恢复DPR Gate B-R2
启动历史Route A/B/C controller
新Cine训练
额外backbone或ensemble
使用MoSAIC权重/代码
外部数据
fold1 outer调参
validation upload
Docker upload
hosted metric claim
route promotion
runtime git push
```
