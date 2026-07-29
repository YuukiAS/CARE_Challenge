# CARE 当前开发状态

## 2026-07-29 Controller结果：CARE-ARC W3机制门停止

CARE-ARC v2 已完成 W0 authority/split/crop freeze、W1 单 encoder 实现、W2 300-step zero-credit preflight 和 W3 fold0 3000-step zero-credit development。W3 fold0 outer 机制门未通过：scar raw direct Dice delta vs nnU-Net 为 `-0.1805021551`，edema-zone 为 `-0.1553631425`，均低于进入 fold1 的 `>= -0.05` 最低条件。失败分类为 `CONTOUR_LIMITED`。

```text
state_id: care_arc_w3_contour_limited_stop_20260729
state_updated_date: 2026-07-29
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED_MAIN_ONLY
single_active_scientific_line: RETURN_TO_PLANNER_FOR_CARE_ARC_REPAIR
fold1_clean_training_authorized: false
fold1_outer_accessed: false
full_data_training_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
runtime_git_push_authorized: false
controller_verification_decision: OPERATIONALLY_BLOCKED_BY_W3_MECHANISM_GATE
result_root: results/20260729_care_arc_clean_fold1
```

必须保持停止边界：不得在 fold1 上调参、不得读取 fold1 outer、不得启动 W4/W5/W6、不得把 nnU-Net-only 恢复成本研究终态。下一步只能由 Planner 基于 W3 证据修订 CARE-ARC 轮廓/定位机制后重新授权。

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 2026-07-29 当前最高优先级：CARE-ARC v2

当前主线已从 DG/DPR 的 nnU-Net 邻域修正切换为 **CARE-ARC：单主干、双病理、完整病例直接重建**。v2执行合同进一步移除了 external nnU-Net context 对病理forward的依赖，并将训练单位从固定z-slab修正为完整病例体积。

```text
state_id: care_arc_anchor_relaxed_complete_reconstruction_v2_20260729
state_updated_date: 2026-07-29
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED_MAIN_ONLY
route_worktree_development_authorized: false
single_active_scientific_line: CARE_ARC_V2_CLEAN_FOLD1
method_name: CARE-ARC Anchor-Relaxed Complete Reconstruction v2
execution_code: CARE-ARC-V2-W0-W6
controller_is_coordinator: true
planning_review_required: false
review_required: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
runtime_git_push_authorized: false
```

## 当前权威入口

```text
highest_authority_amendment:
prompts/tasks/20260729_care_arc_execution_hardening_amendment.md

blueprint:
prompts/blueprints/CARE_ARC_anchor_relaxed_complete_reconstruction_20260729.md

executor_plan:
prompts/tasks/20260729_care_arc_clean_fold1_executor_plan_v2.yaml

controller:
prompts/tasks/20260729_care_arc_clean_fold1_controller_v2.md
```

规划提交：

```text
e89d39528f9af0a0cb36a2694f651748847e4b41  base blueprint
6166cb26e701a6c37f27a6c231392c3883a28cd0  execution hardening amendment
5f9805e2a32edc1836299476eff3587dc395639e  executor plan v2
988477ef4175f47f514d41c18bcd113b6543589e  controller v2
```

冲突优先级：

```text
CARE-ARC execution hardening amendment
> CARE-ARC blueprint
> CARE-ARC executor plan v2
> CARE-ARC controller v2
> 本CURRENT.md
> v1 CARE-ARC files
> 历史 DPR / DG / Cascade / MMRD contracts
```

## 为什么切换并加固

### Hidden validation新证据

CARE自研病理拼接探针：

```text
scar: CARE-DG A3 step5000
edema: CARE-SRR-Cascade control_seed20260724 compact class4
myocardium/LV/RV: Dataset501 five-fold nnU-Net
CineMyoPS: frozen historical prediction tree
```

Hosted结果：

```text
CARE probe scar Dice / HD: 0.6211 / 15.1513
MoSAIC scar Dice / HD: 0.6965 / 13.7827
```

逐病例观察表明CARE probe几乎始终贴近nnU-Net；MoSAIC更倾向完整、高召回和少量连续病灶。历史MoSAIC prediction tree并未完整保留，因此该观察只用于架构动机，不冒充逐体素hidden审计。

### DG/DPR证据

DPR Gate B-R1修复candidate-level训练/推理错位后，complete16仍为：

```text
scar:       0.693335 -> 0.692643
edema-zone: 0.752194 -> 0.752104
pure edema: 0.394436 -> 0.394172
```

DPR Gate B-R2终止证据：

```text
commit: f3cc5afa3cff7f2fbf8be8b6ec7945170839eac2
status: USER_STOPPED_BEFORE_GATE
rows_completed: 925 / 1200
eligible_rows: 0
best_avg_inner_dice_delta_so_far: -0.03193535188070074
fold1_started: false
scientific_final_output_credit: 0
```

这说明继续放大local candidates会同时破坏Dice、HD95、remote FP和help/harm，不能再依靠utility/threshold修补。

### v1计划审计发现的执行漏洞

1. 原`8×192×192`并非full volume；现有病例z深度可为9、12、16、20、24、32。
2. 只删除nnU-Net病理通道仍不足；nnU-Net anatomy/uncertainty进入可学习路径会保留单折OOF到五折ensemble的输入漂移。
3. 病例级病灶负荷没有真正进入direct decoder决策。
4. inner排除、fold1 outer一次性访问和freeze顺序缺少机器锁。
5. alignment、crop、checkpoint和decode存在留给Executor临时选择的空白。

以上均由R1 amendment和v2 plan冻结修正。

## CARE-ARC v2冻结结构

```text
[LGE,T2,C0] + availability
-> modality-specific residual stems
-> optional identity-initialized bounded LGE-reference feature alignment
-> one CARE-owned anisotropic ResEncM-style encoder
   -> internal anatomy decoder
   -> scar evidence gate -> coarse extent -> direct full-volume scar
      -> presence + global burden FiLM + SDF mean/logvar
   -> edema evidence gate -> coarse extent -> direct full-volume edema-zone
      -> presence + global burden FiLM + SDF mean/logvar
-> scar priority
-> pure edema = edema-zone minus scar
```

强制边界：

- trainable pathology forward只读原始模态和availability；
- nnU-Net只作same-fold encoder初始化、最终0–3类和灾难性asset/grid fallback；
-任何nnU-Net pathology/anatomy probability、entropy或distance不得进入病理forward；
- 主体只有一个20M–45M shared encoder；
- 不允许MoSAIC、MMRD teacher、第二U-Net、多backbone、prototype、dictionary、router、component utility或ADD/REVISE；
- scar/edema结构对称、参数独立、病例均衡；
- no-T2 edema output/loss/gradient exact zero；
- 完整病例保留全部z切片，batch1、gradient accumulation2；
- 病例级burden head必须通过FiLM影响direct logits；
- 三模态病例使用CARE direct pathology masks，不因不同于nnU-Net而常态回退。

## 执行图

```text
W0 authority/split/shape/crop freeze
-> W1 exact implementation
-> W2 real-case full-volume preflight
-> W3 fold0 zero-credit development adequacy and alignment freeze
-> W4 fold1 clean 7000-step training + atomic one-time outer evaluation
-> W5 independent clean gate / Mapper final / packet / local commit
-> W6 only if clean gate and time guard pass: single-encoder full-data fit + local package dry-run
```

W3必须先证明coarse/presence病例外信号、direct mask非identity、volume/component不过度失真；机制不足时返回Planner做完整修订，不能盲目消耗fold1 clean证据。

Fold1 actual-train必须排除inner12和outer。Checkpoint及预注册decode grid只在inner12冻结；outer evaluator需要freeze receipt、atomic lock且只允许运行一次，之后禁止重选或重评。

## Clean fold1门

Primary population固定为complete-trimodal GT-positive病例；all-case只作robustness。必须全部满足：

```text
scar / edema-zone / pure-edema Dice delta >= -0.005
scar或edema-zone至少一个 Dice delta >= +0.010
另一个主病理 Dice delta >= 0.000
每病理 material help >= harm - 1，help/harm阈值为±0.005
HD95 <= 1.05x anchor
无新增 infinite exact-HD
remote FP <= 1.10x anchor
positive-GT empty rate不高于anchor
scar和edema至少50% positive cases changed-mask ratio >=5%
两病理coarse/direct/presence/burden/contour真实激活
no-T2 edema exact-zero
冻结alignment模式和no-alignment control完整报告
```

未通过时不得在fold1继续调参；必须分类为execution、encoder、alignment、detection、contour或domain-calibration gap，完成terminal packet后返回Planner。不得写项目放弃或恢复nnU-Net-only为研究终态。

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

若allocation终止，只能记录精确resume point并返回operationally blocked；不得新建job。

## 图视觉门

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD, CARE-SRR-Cascade, MoSAIC
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_route_objective: availability-aware modality evidence -> anatomy-guided localization -> scar/edema pathology-specific complete reconstruction -> safety supervision
key_revision: remove baseline-preserving residual and local candidate arbitration as primary pathology mechanisms
```

## Wiki和历史边界

Root wiki仍主要描述2026-07-26历史状态，视为stale。实现完成前只能写planned/unverified；W5 Mapper final后才允许按真实代码和runtime更新wiki及图。

以下保留为历史证据，不再是active authority：

```text
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint
results/20260725_care_myops_mosaic_fold0_reproduction
results/20260728_care_dpr_fold0_global_redesign
results/20260724_care_myops_srr_cascade_submission_rescue
results/20260724_care_myops_batch10_deadline_rescue
```

## 当前未授权

```text
恢复DPR Gate B-R2
历史Route A/B/C controller
新Cine训练
额外backbone或ensemble
使用MoSAIC权重/代码
外部数据
fold1 outer调参或第二次评价
validation/Docker upload
hosted metric claim
route promotion
runtime git push
```