---
task_key: 20260727_care_ser_lite_owned_final_candidate
task_kind: scientific_milestone
task_type: care_owned_selective_error_retrieval_final_candidate
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
status: READY_FOR_CONTROLLER
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260727_care_ser_lite_owned_final_candidate_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
review_mode: none
reviewer: none
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: NOT_AUTHORIZED
experiment_adequacy_gate: "At least one CARE-owned pathology branch must produce non-zero final-mask changes and pass leakage-safe nested OOF Dice/HD95/exact-HD/remote-FP/help-harm gates. Pure nnU-Net, pure MoSAIC, or deterministic nnU-Net/MoSAIC hybrid packages are forbidden outputs."
route_negative_gate: NOT_AUTHORIZED
scientific_completion_gate: "Completion requires a real CARE-owned candidate dataset, real positive/negative retrieval evidence, reliable-label semantics, bounded pathology-specific correction, reconstructed final-mask evaluation, and an upload-ready local package only when at least one custom pathology passes."
diagnostic_publication_gate: LOCAL_LIGHTWEIGHT_PACKET_ONLY
diagnostic_publication_scope: ["source", "config", "tests", "Markdown", "CSV", "JSON", "YAML", "SHA256 text", "local package manifest"]
blocked_after_diagnostic_publication: ["validation_upload", "docker_upload", "hosted_metric_claim", "route_promotion", "scientific_stop", "new_slurm_allocation", "git_push"]
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

# CARE-SER-Lite：必须包含 CARE 自有机制的最终 validation 候选

## Execution Contract

前一任务把最终路线过早冻结为 `NNUNET_ONLY_DOCKER`，这与用户的明确科学目标冲突。本任务覆盖该结论：最终 submission 不允许只包含 nnU-Net、MoSAIC，或二者的确定性拼接。nnU-Net 和 MoSAIC只能提供冻结证据；最终 scar/edema mask 是否改变，必须由 CARE 自有机制决定。

本任务不是恢复原始 Batch7、MMRD 或 SCR-R1 整体模型，也不是重新训练复杂 backbone。它实现并验证一个最小但真实的 CARE-SER-Lite：

```text
Frozen 5-fold nnU-Net anatomy/pathology anchor
+ frozen MoSAIC scar proposal source
+ frozen CARE-MMRD feature/evidence source
+ CARE-owned positive/negative selective retrieval
+ CARE-owned scar component suppress/recover gate
+ CARE-owned T2-conditioned edema-zone region gate
+ pathology-specific bounded correction
+ exact identity fallback
```

必须保留的 CARE 血统：

1. **SRR**：正原型、负原型和安全负空间只作为病例外证据选择器，不直接做 dense segmentation。
2. **MMRD**：模态可用性显式进入；无 T2 病例不得成为 edema negative；edema 监督只使用 T2-present reliable labels；冻结 MMRD teacher feature 必须作为预注册增量特征组接受 matched ablation。
3. **Cascade/SCR**：解剖类别保持 nnU-Net identity；scar 与 edema 独立修正；修改受边界和体积约束；证据不足时逐病种 exact fallback。

最终候选至少必须有一个 CARE-owned pathology branch 通过。若所有自有分支失败，终态只能是 `NO_CARE_OWNED_CANDIDATE_DO_NOT_UPLOAD`，不得生成或推荐纯外部模型包。

## 计算与操作边界

只允许使用现有 allocation：

```text
job_id: 60657290
partition: htzhulab
node: g1807htzh01
```

若 Controller 已在该 allocation 内，直接顺序运行；否则只允许 `srun --jobid=60657290 --overlap --ntasks=1 ...`。禁止 `sbatch`、`salloc`、新 Slurm job、并行 GPU 进程、validation 上传、Docker 上传和 runtime push。若 allocation 已终止，不得提交替代 job；完成可做的 CPU/已有资产工作并精确报告剩余 GPU 缺口。

启动前同步 `origin/main`，读取 CARE 必读协议、Slurm skill、Mapper skill、最新 CURRENT/wiki、两份 CARE-SER 蓝图、220-case MoSAIC OOF、nnU-Net OOF、Batch7、MMRD、SCR-R1、旧 SafeScar Step3 和 hosted-gap 取证结果。记录：

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3, CARE-MMRD, CARE-SRR-Cascade, MoSAIC
visual_read_status: PASS_FROM_PLANNER_HANDOFF
recovered_route_objective: observed-modality evidence -> selective retrieval -> pathology-specific error decision -> bounded correction -> exact fallback
```

## Controller 责任

Controller 是验收负责人，不得再用“文件存在”代替科学执行。普通代码、缓存、路径、几何、方向、标签、checkpoint、特征、评价器、测试、聚合或 validator 缺口必须进入同范围修复闭环：

```text
detect -> repair_ledger -> same Executor minimal repair -> inspect diff/hash
-> rerun failed command -> rerun affected aggregation/validators -> inspect contents
```

不得在第一次可修复错误时停止，不得用旧 SafeScar component F1、纯模型 Dice 表、空 CSV、人工三行结论或预写 `NNUNET_ONLY_DOCKER` 冒充完成。负科学结果不是操作阻塞；必须继续完成所有预注册 ablation 和安全结论。

## W0：冻结合同、资产与评价语义

输出 bootstrap、allocation、GPU lock、输入资产、split/case/checkpoint/config/hash、repair ledger。运行 evaluator parity sentinel：至少复现 fold0 已知 scar/pure-edema Dice、HD95、exact HD、precision/recall、标签映射和 geometry。bulk evaluation 前 parity 必须 PASS。

## W1：真实多来源 candidate dataset v2

候选生成必须 GT-blind。每病例允许多个候选，固定来源：

```text
Scar:
- nnU-Net argmax scar components
- nnU-Net probability thresholds 0.15/0.20/0.25/0.30
- MoSAIC raw pre-containment/pre-cleanup scar thresholds 0.15/0.20/0.25/0.30
- MoSAIC pre-largest-component and final components
- Batch7/MMRD/SCR scar components only when exact prediction assets exist

Edema zone:
- nnU-Net argmax edema-zone regions
- nnU-Net zone thresholds 0.15/0.20/0.25/0.30
- T2-supported contiguous low-threshold regions inside soft myocardium shell
- no MoSAIC edema
```

同病例候选以 IoU >= 0.5 deterministic merge，保留 source bitmask、原始 mask hash 和未合并成员。禁止 final-largest-component-only 导致“一例一个组件”。

每个候选计算：nnU-Net/MoSAIC probability、ensemble uncertainty、source agreement、soft anatomy overlap/shell distance、LGE/T2 robust intensity statistics、体积、slice continuity、compactness、surface-to-volume、blood-pool proximity、remote-island indicator、scar/edema conflict。

## W2：真实 CARE 表征与正负检索

使用冻结 CARE-MMRD teacher/encoder 的真实 feature map；优先复用已验证 32-channel source cache，缺失时从现有 checkpoint 在 allocation 60657290 内重建。不得把手工标量均值称为 representation prototype。

组件 embedding 为 feature map 在候选区域的均值与标准差，病例外构建：

```text
positive bank: GT pathology components from outer-training cases
negative bank: false-positive components + blood pool + remote background + reliable normal myocardium
scar: LGE-driven
edema: only T2-present reliable cases; no-T2 never enters positive or negative bank
```

每个 outer fold 内独立拟合标准化与 prototype bank。检索特征固定为 top-5 positive cosine mean、top-5 negative cosine mean 和 margin `s_pos-s_neg`。输出 prototype provenance、case/fold/category/hash 和 same-case exclusion audit。

必须做 matched ablation：真实 retrieval channels vs 全零 retrieval channels，其余 candidate、split、features、model、seed、threshold grid 完全相同。

## W3：CARE-owned scar suppress/recover gate

不训练新 backbone。训练两个低容量模型：

```text
ScarSuppress: 对 nnU-Net anchor component 判断 retain/suppress
ScarRecover: 对 non-anchor proposal 判断 reject/recover
```

动作监督由真实 counterfactual final mask 产生，而不是“任意 GT overlap”：

```text
Suppress target: remove component 后 Dice gain >= 0.005，且 HD95/exact-HD/remote-FP 安全
Recover target: add proposal 后 Dice gain >= 0.005，且 HD95/exact-HD/remote-FP 安全
Default: anchor identity
```

预注册模型只有：L2 logistic regression 与 depth<=3 的小型 gradient-boosted trees；内层 CV 选择正则/阈值，若效用并列优先 logistic。外层必须沿原始 fold/case 分组。标准化、缺失处理、特征选择、prototype 和 calibration 全部在 outer-training 内拟合。

固定 ablation：

```text
A0 nnU-Net identity
A1 CARE base: probability + uncertainty + anatomy + morphology + raw modality stats
A2 A1 + SRR positive/negative retrieval
A3 A1 + MMRD teacher evidence
A4 A1 + SRR retrieval + MMRD evidence
A5 A4 + available historical Batch7/Cascade evidence
```

每个 ablation 重建最终 mask并报告 Dice、HD95、exact HD、precision、recall、remote FP、component count、volume ratio、help/harm 和 changed voxels。分类 F1/AUC 只能是诊断。

Scar local PASS：

```text
complete-trimodal OOF Dice gain >= 0.010 over nnU-Net
all-220 Dice delta >= -0.002
HD95 <= 1.05 * anchor on complete-trimodal and all-case
no catastrophic exact-HD outlier
remote FP non-increased
help cases >= harm cases
non-zero suppress and/or recover on held-out cases
final masks differ from both nnU-Net and MoSAIC
```

## W4：CARE-owned T2-conditioned edema-zone gate

MoSAIC edema 禁止。只使用 T2-present reliable OOF 病例训练和选择；no-T2 病例输出必须逐体素等于 nnU-Net edema anchor。

构建 `EdemaSuppress` 与 `EdemaRecover` 低容量区域 gate，输入 nnU-Net zone probability/uncertainty、T2/LGE区域统计、soft anatomy、形态、MMRD teacher evidence和 SRR-style reliable positive/negative retrieval margin。最终：

```text
final_zone = (anchor_zone - accepted_suppress_regions) union accepted_recover_regions
pure_edema = final_zone - final_scar
```

必须分别评价 edema-zone 和 pure-edema，并审计 scar 修改引起的 subtraction 耦合。

Edema local PASS：

```text
T2-present reliable pure-edema Dice gain >= 0.010
T2-present reliable edema-zone Dice gain >= 0.010
HD95 non-worse
no catastrophic exact-HD outlier
no-T2 changed voxels = 0
help cases >= harm cases
non-zero CARE action
```

## W5：最终 CARE 组合、部署校准与 proposal-source stress test

选择只能发生在 OOF。最终模型必须含 CARE-owned gate；不允许选择 A0。若多个 CARE ablation 通过，按以下顺序：满足安全门 -> complete-trimodal Dice -> all-case safety -> HD95 -> remote FP -> 简单度。

训练最终 gate 时冻结 OOF 选出的结构、特征组、超参数与阈值。为避免 fold-model 到 deployment source 的校准错位，候选特征优先使用病例内分位数、agreement、retrieval margin和标准化形态；同时做两个 proposal-source stress test：

```text
CF: clean MoSAIC 5-fold probability ensemble proposals
FD: final full-data MoSAIC proposals
```

两者都必须经过同一个 CARE gate，且最终 mask 必须不同于纯 nnU-Net 和纯 MoSAIC。FD 只有在 action-rate、volume、confidence 与 CF/OOF envelope 不发生显著漂移时才可生成；否则只生成 CF。

## W6：validation 本地候选与 package

只在至少一个 CARE-owned pathology PASS 时生成 upload-ready 包：

```text
CARE-SER-Lite-CF
CARE-SER-Lite-FD  # 仅在 FD calibration stress PASS 时
```

允许的病种状态：

```text
scar PASS, edema PASS -> CARE dual
scar PASS, edema FAIL -> CARE scar + nnU-Net edema
scar FAIL, edema PASS -> nnU-Net scar + CARE edema
scar FAIL, edema FAIL -> NO_CARE_OWNED_CANDIDATE_DO_NOT_UPLOAD
```

即使一个病种 fallback，另一个通过的 CARE 分支仍必须真实改变最终 mask。Cine 固定使用当前已验证 prediction tree。不得生成纯 nnU-Net、纯 MoSAIC 或 deterministic hybrid submission 包。

输出 geometry/label/hash/audit、机制激活、逐病例逐病种 fallback、两次确定性运行 hash equality、运行时间与峰值显存。只生成本地 ZIP 和上传说明，不上传。

## W7：终态、Mapper 和验收

必须输出自然中文结论：

1. CARE 自有 scar/edema 分支分别是否通过；
2. SRR retrieval、MMRD teacher/reliable labels、Cascade bounded correction 各自带来什么增量；
3. 哪些病例被帮助或伤害；
4. CF 与 FD proposal source 的风险差异；
5. 推荐占用 validation 的唯一 CARE-owned 包；
6. 若无候选，明确 `NO_CARE_OWNED_CANDIDATE_DO_NOT_UPLOAD`，而不是推荐纯外部模型。

Strict validator 必须拒绝：空/两行 candidate-v2；一例一个 largest-component 数据集；GT 参与 candidate generation；prototype 不是真实 embedding；外层 split 前拟合标准化或 prototype；component F1 冒充 final-mask增益；no-T2 edema 变化；A0/纯外部模型被包装成 CARE；CARE action 全零；文件存在但 required metrics/rows缺失；第一次可修复错误即停止；submitted/running 状态写完成。

终态 `controller_verification_decision: VERIFIED_COMPLETE` 只在代码、真实运行、nested OOF、final-mask metrics、package审计、Mapper/wiki/CURRENT、strict validator和本地轻量 commit全部完成后允许。运行角色不得 push。

## Executor Worker Contract

Executor 负责在上述固定设计内实现 candidate-v2、MMRD feature extraction、cross-fitted prototypes、scar/edema低容量 gate、counterfactual final-mask评价、validation inference、package和validators。不得改变候选阈值集合、模型容量、split、主指标、上传边界或纯外部模型禁令。每个 wave 返回 Controller 检查真实 diff、hash和证据，Executor不能自行宣布整个任务完成。

## Mapper Contract

Mapper 必须把最终实际调用图写入 wiki：nnU-Net/MoSAIC仅为冻结 evidence sources；CARE retrieval/gates拥有最终病理修改权；MMRD reliable-label/no-T2规则和 Cascade identity fallback为 active protocol。未通过的分支标为 failed/disabled，不能把计划写成 verified，也不能恢复 `NNUNET_ONLY_DOCKER` 作为用户认可的最终科学目标。