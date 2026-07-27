---
task_key: 20260727_care_dg_dual_pathology_validation
task_kind: scientific_milestone
task_type: care_dg_dual_pathology_error_correction_validation
task_status: READY_FOR_CONTROLLER
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260727_care_dg_dual_pathology_validation_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
review_required: false
review_mode: none
reviewer: none
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
validation_packaging_authorized: conditional_local_only
validation_upload_authorized: false
docker_local_build_authorized: conditional
docker_upload_authorized: false
hosted_metric_claim_authorized: false
fold_expansion_authorized: true
new_model_training_authorized: true
new_slurm_allocation_authorized: false
route_promotion_authorized: false
---

# CARE-DG 双病理错误修正与 validation 候选 Controller

## Execution Contract

这是一个新的独立 main-only 任务，覆盖此前 `NNUNET_ONLY_DOCKER`、CARE-SER-Lite、MoSAIC proposal fusion 和复杂双病理多模型蓝图。当前唯一目标方法是：

```text
CARE-DG
= frozen 5-fold nnU-Net anchor
+ one compact CARE multimodal encoder
+ independent scar and edema error/correction decoders
```

方法真值：

```text
prompts/blueprints/CARE_DG_dual_pathology_blueprint_20260727.md
```

不得把 MoSAIC、完整 MMRD、SRR dictionary/prototype memory、SIP、Batch7、旧 Cascade 或其他模型作为 runtime 模块。它们仅作为历史动机和比较证据。最终 improvement 必须可归因于 CARE-DG 本身。

本任务明确授权：实现新网络、修复相关代码、五折 OOF 训练、all-data deployment training、validation 15 例本地推理、validation upload-ready ZIP、必要的同范围训练重试、Docker-equivalent local smoke。禁止自动上传 validation 或 Docker。

## 唯一计算资源

所有 GPU 工作必须在现有 interactive allocation 中执行：

```text
job_id: 60657290
partition: htzhulab
node: g1807htzh01
job_name: CAREInteractive3d
```

如果 Controller 已经位于该 allocation，直接顺序执行。否则只允许：

```bash
srun --jobid=60657290 --overlap --ntasks=1 bash -lc '<command>'
```

严格禁止：

```text
sbatch
salloc
新 Slurm job
并行两个 GPU 训练/推理进程
写入 /overflow/htzhu/CARE
validation upload
Docker upload
runtime git push
```

启动和每次 GPU 阶段前必须检查 `squeue`、`scontrol show job`、`nvidia-smi`、剩余 walltime、现存进程和 task-local GPU lock。若 allocation 终止，不能创建替代 job；完成已可完成的 CPU/证据工作并返回精确阻塞点。

## 必读与状态优先级

启动前同步最新 `origin/main`，读取 CARE 必读协议、Slurm skill、Mapper skill、最新 CURRENT/wiki、CARE-DG blueprint、历史 Batch7/MMRD/Cascade/MoSAIC 结果和以下图视觉交接：

```text
diagram_versions_read:
  SRR-v2
  SRR-v2.5
  SRR-v3
  CARE-MMRD
  CARE-SRR-Cascade
  MoSAIC
visual_read_status: PASS_FROM_PLANNER_HANDOFF
```

`prompts/routes/handoffs/CURRENT.md` 当前仍记录旧的 baseline-only 终态；这是历史机器真值，不代表本任务目标。用户当前明确授权 CARE-DG 训练和 validation 本地包装，本任务 prompt + blueprint 对冲突的旧状态具有更高优先级。Controller 只能在真实终态后更新 CURRENT/wiki。

## Controller 是持续监督与验收负责人

Executor 负责实现和命令，但不能宣布任务完成。Controller 必须持续监督至所有 GPU 命令 terminal、aggregation、validator、Mapper、CURRENT/wiki 和本地 commit 完成。

普通代码、缓存、路径、环境、几何、方向、标签、checkpoint、训练、gradient、loss、评价器、package、validator 或 wiki 缺口必须进入同范围 repair loop：

```text
detect gap
-> append repair_ledger.csv
-> return exact gap to same Executor
-> smallest semantics-preserving repair
-> inspect real diff and old/new hashes
-> rerun failed command
-> rerun affected aggregation and validators
-> inspect output content, not only file existence
-> continue after PASS
```

不得因为第一次可修复错误、单 fold 暂时负结果、运行中状态、监控状态、模型未立即超越 nnU-Net 或某个 optional 图生成失败而随意 block。负科学结果不是 operational blocker；必须完成预注册五折、指标和终态结论。

允许 `OPERATIONALLY_BLOCKED` 的条件只有：

1. allocation `60657290` 已终止且仍有必需 GPU 工作；
2. 必需 raw data、nnU-Net OOF probability、checkpoint 或 GT 客观缺失且不能从现有资产重建；
3. disk/permission/cluster 故障经直接验证仍不可恢复；
4. 修复必然要求新 Slurm allocation、外部数据或改变冻结科学合同。

## W0：Bootstrap、资产绑定与评价器 parity

必须输出：

```text
results/20260727_care_dg_dual_pathology_validation/controller_context.json
results/20260727_care_dg_dual_pathology_validation/controller_ledger.csv
results/20260727_care_dg_dual_pathology_validation/controller_bootstrap_snapshot.md
results/20260727_care_dg_dual_pathology_validation/existing_allocation_receipt.json
results/20260727_care_dg_dual_pathology_validation/existing_allocation_gpu_lock.json
results/20260727_care_dg_dual_pathology_validation/input_asset_manifest.json
results/20260727_care_dg_dual_pathology_validation/evaluator_parity_report.json
results/20260727_care_dg_dual_pathology_validation/repair_ledger.csv
```

冻结：

```text
220 case list
80 complete-trimodal case list
15 validation case list
five-fold split hash
nnU-Net OOF prediction/probability hashes
nnU-Net five-fold deployment checkpoint hashes
label mapping
preprocessed grid / geometry
metric implementation
CARE-DG blueprint hash
training and decode contract
```

评价器 parity 必须复现已有 fold0 nnU-Net、Batch7、MMRD 和 SCR canonical scar/pure-edema Dice、HD95、exact HD、precision/recall，容差预注册为 Dice/precision/recall `1e-6`、distance metrics `1e-4 mm`。parity 未通过不得开始正式训练。

## W1：实现、unit tests 和真实错误学习门

必须实现：

```text
src/care_myocardium/models/care_dg.py
src/care_myocardium/data/care_dg_dataset.py
src/care_myocardium/training/care_dg_trainer.py
src/care_myocardium/inference/care_dg_predictor.py
scripts/training/run_care_dg.py
scripts/inference/run_care_dg_inference.py
scripts/evaluation/evaluate_care_dg.py
scripts/evaluation/select_care_dg_candidate.py
scripts/evaluation/validate_care_dg_packet.py
configs/care_dg/care_dg_v1.yaml
tests/care_dg/
```

实现必须逐项符合 blueprint：

- 3 个浅层 modality-specific stems；
- compact shared three-scale encoder；
- 独立 scar/edema decoder；
- 每病种 FN gate、FP gate、FN magnitude、FP magnitude；
- competitive logit correction；
- soft anatomy support；
- protected anatomy；
- scar-priority pure edema；
- reliable-label/no-T2 masking；
- pathology-specific fallback；
- exact checkpoint/resume。

正式训练前必须通过：

```text
real case forward
loss finite
scar active loss backward
edema active loss backward
no-T2 edema gradient exactly zero
FN/FP label construction parity
competitive-logit intervention changes final argmax
zero-correction gives exact anchor identity
checkpoint/reload exact output parity
resume cursor parity
augmentation image/label/error-map zero-misalignment
known-bad hard support rejected
known-bad shared final pathology head rejected
known-bad MoSAIC/MMRD/prototype runtime dependency rejected
```

在真实病例上做 300 optimizer-step implementation overfit，不计正式训练 credit。Scar 和 edema active loss 各下降至少 30%，FN/FP output 不得为常数，changed voxels 必须非零。

## W2：五折正式 OOF 训练

按 blueprint 固定五折、单 seed `20260727`、每 fold 8,000 optimizer steps：

```text
Stage A 5,000 steps: all reliable train cases, complete-trimodal sampling weight 4
Stage B 3,000 steps: complete-trimodal train cases only
```

五折全部在 allocation `60657290` 内串行运行。不得因 fold0 未超过基线而停止 folds 1–4。每 fold 保存 1k-step checkpoints、best target checkpoint 和 last checkpoint；best selection 只使用该 fold train-side inner split，不能使用 outer held-out metrics。

每 fold receipt 必须记录：

```text
train/val cases and overlap
complete-trimodal counts
T2-reliable edema counts
expected/actual optimizer steps
stage transition
checkpoint hashes
loss curves
mechanism activation
resume history
terminal status
```

Undertrained、partial、startup failure 都是零 scientific credit；Controller 必须在相同科学合同内修复和续跑，直到完整或 allocation 阻塞。

## W3：OOF aggregation、anti-identity 和机制消融

必须生成全 220 例 OOF predictions 与 complete-80 主报告。固定比较：

```text
A0 nnU-Net identity
A1 direct residual control: same encoder/decoders but FN/FP gates replaced by one signed residual head
A2 CARE-DG full explicit FN/FP gating and competitive correction
A3 CARE-DG without Stage B target calibration
```

A1/A3 允许共享正式训练资产或使用预注册同预算 matched run，但不得增加新 backbone。核心目的是证明：显式错误门与目标校准相对旧式弱 correction 有增量。

必须输出：

```text
oof_casewise_metrics.csv
oof_model_summary.csv
oof_complete80_summary.csv
oof_all220_robustness_summary.csv
oof_fold_stability.csv
mechanism_activation_audit.csv
fn_fp_error_recall.csv
help_harm.csv
exact_hd_tail_audit.csv
remote_fp_audit.csv
ablation_summary.csv
```

指标：scar、edema-zone、pure edema 的 Dice、leaderboard-compatible HD、HD95、exact HD、precision、recall、remote FP、components、volume ratio、empty prediction、changed voxels、help/harm 和 fallback。

Anti-identity gate：

```text
>=30% complete held-out GT-positive cases changed
>=10% anchor error voxels receive correct-direction correction
scar and edema each activate on held-out cases
FN/FP maps non-constant
A2 final masks differ from A0
```

若不满足，Controller 只能在冻结允许范围内修复 wiring、sampling、loss application 或 clipping bug；不得新增模型或根据 held-out score调参。

## W4：Candidate selection 和 all-data deployment training

Primary competition estimand：complete-80。All-220 仅作为 robustness/limitation，除非出现 catastrophic harm、几何/标签错误或机制 collapse，不得单独否决目标域候选。

Exploratory dual-pathology candidate gate：

```text
scar complete-target Dice delta >= -0.005
pure-edema complete-target Dice delta >= -0.005
edema-zone Dice delta >= -0.005
at least one pathology Dice gain >= +0.005
HD95 <= 1.05 * anchor for both pathologies
exact-HD 95th percentile increase <= 5 mm
no new infinite exact-HD case
remote FP increase <= 10%
help >= harm - 1 per pathology
both mechanisms activate
no-T2 edema changed voxels = 0
```

Paper-ready gate 另行报告：complete-target Dice gain >= +0.005 且安全指标不差。

OOF 选中的 architecture、checkpoint rule、decode、margin、support、fallback envelope 和 threshold 全部冻结后，训练一个 all-data CARE-DG deployment model，使用同一 Stage A/B 8,000-step schedule。不得用 validation score选择 checkpoint 或阈值。

## W5：Validation 推理、package 与 Docker-equivalent smoke

在 validation 15 例上运行：

```text
5-fold nnU-Net ensemble anchor
+ all-data CARE-DG correction model
```

必须两次独立确定性推理，逐文件 SHA256 一致。输出：

```text
validation_casewise_mechanism_audit.csv
validation_geometry_audit.csv
validation_label_audit.json
validation_determinism_hashes.csv
validation_fallback_audit.csv
runtime_benchmark.json
peak_memory_report.json
package_manifest.json
zip_sha256.txt
validation_upload_instruction.md
```

只有 OOF dual candidate gate PASS、scar/edema 均在 validation 至少一例非零激活且 pathology fallback rate <=30% 时，才生成：

```text
results/submissions/care_myocardium_validation/upload_ready/<timestamp>__CARE-DG-v1/CARE-Myocardium-OrganAgent.zip
```

Cine 使用当前冻结、已验证的 prediction tree，不训练新 Cine。不得自动上传。

Docker-equivalent smoke 必须验证：输入 contract、checkpoint加载、两次 hash equality、15+15 case 数、官方 raw labels、shape/spacing/origin/direction、退出码 0、无 GT 访问和可接受 runtime/显存。

## W6：Mapper、strict validator、终态和 email

Mapper 必须更新 root wiki、architecture.yaml、COMPONENTS、LINEAGE、current_state 和 CURRENT，真实记录：

```text
nnU-Net = frozen anchor
CARE-DG = only active trainable pathology correction model
MoSAIC/MMRD/SRR dictionary/Cascade = historical evidence, not runtime dependencies
scar and edema = independent verified branches only if evidence PASS
```

Strict validator 必须检查内容和行数，不是只检查文件存在。至少拒绝：

```text
少于 220 OOF rows
少于 80 complete-target rows
undertrained fold被计入
FN/FP maps常数
zero changed voxels promoted
no-T2 edema changed voxels >0
shared scar/edema final head
hard anatomy crop
MoSAIC或完整MMRD runtime dependency
只有 mean Dice 没有 HD95/exact-HD/remote-FP/help-harm
fallback rate过高仍包装
validation package与nnU-Net逐体素完全相同却称CARE
submitted/running/monitor 状态写 VERIFIED_COMPLETE
```

允许终态：

```text
CARE_DG_VALIDATION_CANDIDATE_READY_PENDING_USER_UPLOAD
CARE_DG_LOCAL_PAPER_READY_AND_VALIDATION_CANDIDATE_READY
NO_CARE_DG_CANDIDATE_SAFE_FOR_VALIDATION
OPERATIONALLY_BLOCKED_EXISTING_ALLOCATION_OR_REQUIRED_ASSET
```

Controller report 必须先用自然中文回答：

1. CARE-DG 是否真正改变 scar 和 edema；
2. 是否解决旧 Batch7/Cascade 的 correction 太弱和 fallback collapse；
3. complete-80 与 all-220 分别表现如何；
4. scar/edema 帮助和伤害哪些病例；
5. 是否 paper-ready、是否值得占用一次 validation；
6. ZIP 路径和仍未授权的上传。

完全结束、所有 GPU 进程终止、aggregation/validator/Mapper/CURRENT/wiki 和本地轻量 commit 确认后，写：

```text
results/20260727_care_dg_dual_pathology_validation/notification_brief.json
```

并由既有 `controller_notifications/notify_goal_watcher.py` / `care_watchboard:Notify` notifier 向 `1155246312@link.cuhk.edu.hk` 发送一封中文短邮件。不得创建新 notifier，不得在 submitted、pending、running、monitor、`NEEDS_MONITOR` 或 aggregation 未完成阶段通知。终态即使是 `NO_CARE_DG_CANDIDATE_SAFE_FOR_VALIDATION` 或真实 operational block，也应在终态 packet 完整后发送简短完成/阻塞邮件。

## Executor Worker Contract

Executor 只能在 blueprint 和 executor plan 的固定设计内实现、测试、训练、推理、评价和本地包装。不得自行引入 MoSAIC、完整 MMRD、prototype、dictionary、SIP、Transformer、新分割 backbone、多个专家、shared pathology head 或 hosted-score tuning。Executor 每个 wave 返回 Controller 检查真实 diff、运行证据、hash、metrics 和 required outputs，不能自行宣布整个任务完成。

## Mapper Contract

Mapper 只根据真实代码调用图与终态证据更新 wiki。未训练、未运行或未通过的组件保持 planned/failed/disabled，不能把 blueprint 写成 verified。Mapper 不上传、不做 hosted claim、不写 reviewer token。