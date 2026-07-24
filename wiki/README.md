# CARE 架构 Wiki

architecture_version: `care-srr-cascade-scr-r1-runtime-closure-repair-pending`
latest_verified_runtime: `Batch10 fair rescue terminal packet; SCR-R1 W3 formal training has not started`
latest_scientific_status: `CARE-MMRD direct route stopped; CARE-SRR-Cascade SCR-R1 scientific contract active; runtime closure repair ready`
latest_controller_task: `20260725_care_myops_srr_cascade_runtime_closure_repair`
route_status: `MAIN_ONLY_SCR_R1_RC1_READY`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。当前最重要的事实不是“新模型已完成”，而是 Controller 在正式 W3 前正确发现：仓库已有模型骨架、preflight、cache shell 和 monitor，但真实 formal trainer 尚不存在。用户已授权同一 SCR-R1 内的运行闭环修复（SCR-R1-RC1），先修复和复验，再训练；不得用 dry-run、source-cache job 或 monitor packet替代正式结果。

## 当前判断

```text
Batch10 CARE-MMRD: 终止，保留历史公平负结果
科学主线: CARE-SRR-Cascade / SCR-R1
当前动作: SCR-R1-RC1 runtime closure repair
正式W3 credit: 0
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
htzhulab与a100-gpu GPU preflight PASS
四个formal dry-run与orchestrator idempotence PASS
真实known-bad全部被validator拒绝
```

任何普通实现问题由Controller退回同一Executor修复；只有不可生成资产、实测存储低于45GiB、两个授权partition完成所有尝试后均不可用或外部集群故障，才允许写`OPERATIONALLY_BLOCKED`。

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
