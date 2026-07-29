# CARE 架构 Wiki

architecture_version: `care-arc-w3-contour-limited-stop-20260729`
latest_verified_runtime: `CARE-ARC W0-W2 PASS; W3 fold0 zero-credit terminal FAIL at mechanism gate; allocation 61220581 reused only`
latest_scientific_status: `CARE-ARC implementation/trainability verified, but fold0 outer mechanism gate failed as CONTOUR_LIMITED; fold1 clean fold not consumed`
latest_controller_task: `20260729_care_arc_clean_fold1`
route_status: `MAIN_ONLY_FINAL_BLUEPRINT_NNUNET_ONLY_DOCKER_LOCAL_ONLY`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。当前最新事实是：CARE-ARC 单一 encoder 已完成 W0-W2 严格实现和 300-step preflight，并完成 fold0 3000-step zero-credit development；fold0 outer 机制门未通过，原因是 raw direct scar 和 edema-zone 相对 nnU-Net 的 Dice 差距分别为 -0.1805 和 -0.1554，定位/轮廓质量不足。按 2026-07-29 amendment，禁止进入 fold1 clean training、禁止 fold1 outer 访问、禁止 full-data/W6、禁止上传或 push；下一步应返回 Planner 做架构修订，而不是在 fold1 调参。

## 2026-07-29 CARE-ARC W3 机制门结论

```text
result_root: results/20260729_care_arc_clean_fold1
controller_verification_decision: OPERATIONALLY_BLOCKED_BY_W3_MECHANISM_GATE
w0_status: PASS
w1_implementation_validator: PASS
w2_preflight_strict_validator: PASS
w3_training: 3000 optimizer steps, zero credit, fold0 actual-train only
w3_gate: FAIL
failure_classification: CONTOUR_LIMITED
frozen_alignment_mode: identity
fold1_outer_access: NOT_ACCESSED
clean_fold_training: NOT_STARTED
validation_upload: FORBIDDEN_NOT_RUN
runtime_push: FORBIDDEN_NOT_RUN
```

主要证据：`fold0_development_adequacy_gate.json` 记录 scar raw direct Dice delta `-0.1805`、edema-zone raw direct Dice delta `-0.1554`，均低于 `>= -0.05` 的 W3 进入 clean fold 最低机制条件；coarse/presence AUPRC、volume ratio、changed-mask、component safety、no-T2 exact-zero 和 anchor-context invariance 均通过，因此当前失败不是执行崩溃或完全无检测信号，而是外层病例轮廓/定位不足。架构图见 `wiki/figures/care-arc-w3-stop.svg` 和 `wiki/figures/care-arc-w3-stop.png`。

当前最新终态事实是：用户确认 hosted scar Dice 0.6965 属于 MoSAIC submission，但已绑定 final repo、final pretrained weights 和 final inference recipe，但未绑定历史 upload ZIP bytes/SHA；clean 220-case OOF scar 显示 MoSAIC 0.3924、nnU-Net 0.5775，完整三模态子集 MoSAIC 0.6331、nnU-Net 0.6927。最终 Docker 当前只应执行 `NNUNET_ONLY_DOCKER`，MoSAIC/SafeScar/MMRD/Cascade 只能作为研究证据或协议卫生保留，不能作为 active runtime mask producer。

## 2026-07-26 MoSAIC hosted-gap 取证与最终蓝图

```text
result_root: results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint
strict_validator_report.json: PASS
controller_verification_decision: VERIFIED_COMPLETE
allocation: 60657290 reused only; no sbatch/salloc/new Slurm job/upload/push
final_repo_weights_recipe: BOUND
exact_historical_upload_zip_bytes: UNRESOLVED
model_family_lineage: USER_CONFIRMED_MOSAIC
final_docker_architecture: NNUNET_ONLY_DOCKER
pathology_independent_fallback: identity_to_nnunet
```

排名翻转解释边界：full-data inclusion/selection 有 fold0 诊断 lift，scar 约 +0.1045，但这是污染上界；已观测 scar postprocess 约 -0.0021，不能解释 hosted 提升；target modality/domain 和 15-case sampling 只能部分解释，validation GT 不在本地；metric/export 检查只支持标签/几何边界，不支持 MoSAIC 作为最终分割组件。旧 SafeScar Step3 是组件级 retain/suppress F1，不是最终分割 Dice/HD 证据。


## MoSAIC fold0 证据边界

```text
result_root: results/20260725_care_myops_mosaic_fold0_reproduction
strict_validator: PASS
finalizer_state: READY_FOR_LOCAL_PACKET_COMMIT
slurm_terminal_accounting: 60589655/60589656/60589657/60589658/60607636 terminal, replacement finalizer success
fold0_split: data/benchmarks/protocol/splits_MyoPS.json, 176 train / 44 val
```

`/users/a/e/aereinh/MoSAIC` 下的 checkpoint 是 full-data submission 权重，只允许作为模型加载或官方 validation 部署 smoke 的边界证据；不得用来解释本次 fold0 44 例性能，也不得作为 fold0 模型初始化。本次 `mosaic_fold0_random_init` 仅由 `runtime/fold0/` 下新训练权重支持。

主比较：`nnunet_fold0` vs `mosaic_fold0_random_init`。secondary canonical recompute 只包括已有预测可复算的 Batch10 MMRD rank1 和 Batch7 minimal；SCR-R1 generic cascade control 只保留 historical_noncanonical 边界。未上传 validation，未构建 Docker，未 push。

## 当前判断

```text
Batch10 CARE-MMRD: 终止，保留历史公平负结果
科学主线: CARE-SRR-Cascade / SCR-R1
当前动作: SCR-R1-RC1 terminal local closure
正式W3 credit: 8/8 variants terminal PASS
W4科学结果: NO_CUSTOM_RESCUE_USE_BASELINE_ONLY
开发位置: /users/a/e/aereinh/CARE, main
旧Route A/B/C: 历史证据，不恢复
validation/Docker upload: 未授权
```

当前最高优先级入口：

```text
results/srr_production/code_maturity/scr_r1_runtime_block_critic_and_repair_20260725.md
configs/care_mm/srr_cascade_runtime_closure_repair.yaml
prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_controller.md
prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_executor_plan.yaml
results/20260724_care_myops_srr_cascade_submission_rescue/
```

当前架构图：

- `figures/model-current.png`
- `figures/model-gap.png`
- `figures/execution-flow.png`

修复 config 在冲突时覆盖 preexecution amendment、base config、旧 executor plan 和旧 Controller 生成的 resolved contract。它不改变科学假设、seed、budget、22/22 split、audit gate、Cine 边界或上传权限。

## 为什么需要运行闭环修复

旧 W3 formal shell最终调用 `scripts/training/run_care_srr_cascade_rescue.py --formal-job`，而该入口只支持 dry-run，真实调用主动返回 `NEEDS_REPAIR_FORMAL_ENTRYPOINT_MISSING`。旧 orchestrator还硬编码source-cache job ID，并在cache PASS后仍拒绝formal submission。Controller因此block是正确的。

复核同时发现：

```text
Wave -1: 合同绑定可保留
Wave 0: OOF manifest/asset保留，但需真实anchor tensor roundtrip
Wave 1: bounded公式可保留，但当前scar/edema共享trainable trunk需改成独立trunks
Wave 2: synthetic overfit、clone-only fiducial和阶段缺省known-bad不能授权formal
Wave 3: 尚无正式训练credit
```

SCR-R1-RC1要求在 W3 前同时补齐 production anchor/cache/data/trainer、W4 selection/audit、W5 package 和 W6 validator入口，避免训练后继续因后续入口未设计而block。

## 冻结目标数据流

```text
[LGE,T2,C0] + availability
-> five-fold OOF nnU-Net canonical anchor on ResEncM preprocessed grid
-> tiled frozen CARE-MMRD teacher feature/anatomy/edema cache
-> tiled frozen CARE-MMRD scar-margin cache
-> category-aware four-shard cross-fitted pathology prototypes
-> independent scar control / SRR correction trunk
-> independent edema-zone control / SRR correction trunk
-> bounded pathology-channel composition
-> per-pathology calibration six-candidate freeze
-> one-time audit retain-or-fallback
-> conditional five-fold-anchor official package dry-run
```

目标类保持：

```text
src/care_myocardium/models/care_srr_cascade_rescue.py
CARESRRCascadeRescue
```

固定最终语义：

```text
background, myocardium, LV, RV: exact anchor
scar: anchor + support * 2*tanh(delta_scar)
edema: anchor + T2_presence * support * 2*tanh(delta_edema)
scar job: edema exact anchor
edema job: scar exact anchor
no-T2 edema: exact anchor
```

## Anchor、source cache 与 prototype

Anchor必须覆盖全部220例OOF病例。优先反向映射冻结OOF probabilities到预处理网格；若official-export roundtrip不是零体素差异，固定fallback是用病例对应OOF fold checkpoint在预处理网格重算，并仅按冻结prediction hash选择唯一兼容inference mode，禁止使用GT或metric。

Frozen source必须从checkpoint payload和ResEncM `ConfigurationManager`恢复配置，采用滑窗、Gaussian、step 0.5、无mirror；整幅默认构造器捷径禁止。Cache要求220例×4 fields=880 entries，并进行真实direct parity。Feature固定为32通道voxelwise L2-normalized表示。

Prototype按病例×病种×正/负类别保存，不再把所有negative合成一个病例均值。Voxel采样由case/category/seed hash驱动的无放回抽样，禁止取flatten mask前N个。训练query排除整个自身shard；no-T2病例不进入edema bank。

## 正式训练前硬门

旧 `preflight_receipt.json` 不再单独授权W3。新的 `formal_authorization_gate.json` 必须证明：

```text
220例anchor official roundtrip每例0 changed voxels
220例source cache / 880 fields / parity PASS
category-aware prototype cross-fit PASS
四份matched schedule hash冻结
真实32通道scar/edema各200 optimizer-step overfit，loss下降>=30%
真实augmentation function fiducial零错位
active-pathology losses独立backward
checkpoint/resume精确roundtrip
任一兼容GPU partition preflight PASS
四个formal dry-run与orchestrator idempotence PASS
真实known-bad全部被validator拒绝
```

任何普通实现问题由Controller退回同一Executor修复；只有不可生成资产、实测存储低于45GiB、所有兼容GPU partition完成所有尝试后均无preflight PASS或外部集群故障，才允许写`OPERATIONALLY_BLOCKED`。

## 正式运行与评价

固定四个logical jobs，而不是“每seed一个job塞四个variants”：

```text
scar_seed20260724: htzhulab, control -> SRR
edema_seed20260724: htzhulab, control -> SRR
scar_seed20260725: a100-gpu, control -> SRR
edema_seed20260725: a100-gpu, control -> SRR
```

每variant固定6250 optimizer steps、gradient accumulation 2，在1250/2500/3750/5000/6250保存checkpoint并评价calibration。允许signal/preemption后按相同code/config/schedule/asset hash精确resume；partial attempt为零credit。

Control与SRR读取同一initial state、病例/patch schedule、spatial/intensity augmentation、optimizer、budget、decode和evaluator。唯一差别是prototype similarity maps为zero或real。

评价同时报告Dice、official exact HD、HD95、precision/recall、remote FP、component、volume ratio、help/harm、empty prediction、changed voxels、CenterB/CenterC和no-T2 safety。GT-positive empty的HD/HD95为infinite并使candidate ineligible；不得用empty-safe平均替代positive-GT指标。

## Calibration、audit 与 fallback

每病种固定六候选：control seed1/seed2、SRR seed1/seed2、同variant两seed probability mean派生的bounded channel correction。禁止control/SRR交叉blend。Calibration冻结candidate后才允许读取audit；audit不得重选任何参数。

每病种只能选择：

```text
USE_SRR_CASCADE
USE_CASCADE_CONTROL
FALLBACK_TO_NNUNET
```

一个病种失败不拖累另一个，也不能被平均值掩盖。至少一个custom病种通过audit，才允许W5本地package/Docker dry-run。

## Cine 与提交边界

本任务不训练Cine。W5 MyoPS anchor固定使用现有Dataset501五折probability ensemble；Cine固定使用现有Dataset502五折链。Custom head使用冻结fold0训练资产，official病例source evidence按同一frozen checkpoint和tiled runtime生成，prototype只读fold0 train bank，禁止GT访问。

必须检查15+15病例、官方raw labels、shape/spacing/origin/direction、目录/文件名、两次确定性hash和container/local-equivalent exit 0。本地构建不等于上传；validation/Docker upload和hosted claim仍未授权。

## Mapper 责任

SCR-R1-RC1完成后，Mapper必须基于真实生产调用图更新：

```text
wiki/MODEL.md
wiki/EXECUTION.md
wiki/COMPONENTS.csv
wiki/LINEAGE.md
wiki/architecture.yaml
wiki/current_state.yaml
prompts/routes/handoffs/CURRENT.md
```

本轮不要求新架构PNG；未完成前不得把目标runtime写成已验证。

## 入口

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [current_state.yaml](current_state.yaml)
- [history/README.md](history/README.md)
