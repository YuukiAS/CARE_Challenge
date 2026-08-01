---
task_key: 20260801_care_test_docker_final_model_freeze_and_bundle
task_kind: scientific_milestone
task_type: final_submission_model_freeze_and_cross_machine_bundle
status: AUTHORIZED_BY_USER
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: null
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: true
new_training_authorized: false
frozen_inference_authorized: true
workstation_bundle_generation_authorized: true
validation_upload_authorized: false
docker_upload_authorized: false
organizer_email_send_authorized: false
hosted_metric_claim_authorized: false
supersedes_tasks:
  - 20260801_care_test_docker_server_bundle
  - 20260801_care_test_docker_provenance_reconcile_and_bundle
supersedes_blocking_tokens:
  - NNUNET_PROVENANCE_REPLAY_MISMATCH
  - NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC
---

# CARE 测试 Docker：最终提交模型冻结与跨机器 Bundle 完成 Controller

## 一、Planner 最终判断

前几轮把“历史 validation ZIP 是否逐体素复现”和“同一 GPU 推理是否每个边界体素完全一致”错误地升级成了 Docker 打包硬门。它们可以用于来源审计，但不是 CARE 组织方的 Docker 提交要求，也不能继续阻止已经明确的模型进入容器。

当前 15 例两次 fresh nnU-Net replay 的几何全部一致，完整数组差异总计只有 13 个体素。这个量级说明模型、权重、预处理和输出空间是一致的，差异属于边界附近浮点/并行推理非确定性，而不是“模型不清楚”或“不能部署”。因此：

```text
NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC
```

不再是本任务的打包阻塞条件。历史 `0.6691` 来源仍保持 `UNRESOLVED`，不得继承该 hosted claim，但当前冻结模型可以作为当前 Docker 的明确部署来源。

本任务不再进行新的模型竞赛。需要提交的模型现在固定如下。

## 二、最终提交模型，禁止再次改选

### MyoPS Docker

```text
scar source:
MoSAIC repo-final MyoPS scar path
repo commit d334bd1fb2a99dbbc230510590cd8e3ee08cc377
weights:
  myops/coarse.pt
  myops/fine_scar.pt

pure-edema source:
Dataset501_CAREMyoPS current frozen 5-fold nnU-Net
trainer nnUNetTrainer_500epochs
configuration 3d_fullres
folds 0,1,2,3,4
checkpoint checkpoint_best.pth
default TTA
class 4 only

anatomy source:
the same frozen 5-fold nnU-Net
classes 1,2,3

priority:
scar > pure edema > anatomy > background
```

官方输出标签：

```text
0 background
200 myocardium
500 LV
600 RV
1220 pure edema
2221 scar
```

MyoPS 严禁：

```text
MoSAIC coarse_edema.pt
MoSAIC edema.pt
CARE-DG scar
SCR edema rescue
M0R/M1/M2/M3
PRISM/MyoWall/QIF
case-wise selector
validation-driven threshold search
historical package A predictions as runtime source
```

选择依据必须写入 evidence ledger：

- MoSAIC 是当前可归因的最佳 scar hosted source，`0.6965 / 13.7827`；
- nnU-Net 是本地公平 OOF 中最稳定的 anatomy/pure-edema 主体，pure-edema `0.4308`，MoSAIC clean pure-edema 只有 `0.0528`；
- 历史 `0.6691` 只作为未闭合背景，不作为 Docker claim；
- 13 个跨 replay 变化体素不构成模型改选理由。

### CineMyoPS Docker

```text
MoSAIC repo-final Cine recipe
repo commit d334bd1fb2a99dbbc230510590cd8e3ee08cc377
weights:
  cinemyops/coarse.pt
  cinemyops/fine_v1.pt
  cinemyops/fine_v2.pt
z-spacing branches 4/8/16
frozen TTA and final decode
```

选择依据：当前可归因的最佳 OrganAgent Cine hosted row 为 `0.2069 / 48.7463`，并且代码、权重和 final recipe 已绑定。

除非上述固定资产文件缺失或 SHA256 不匹配，Controller 不得再比较 checkpoint_best/final、TTA/no-TTA、历史 ZIP、CARE-DG、SCR、MoSAIC edema 或其他模型。缺失资产时只能报告精确缺失项，不得自动发明替代模型。

## 三、执行边界

必须遵守：

- 当前仓库 `/users/a/e/aereinh/CARE`，只在 `main` 工作。
- 不写 `/overflow/htzhu/CARE`。
- 不使用 sudo，不修改 `/etc`，不在服务器安装/运行 Docker、rootless Docker、Podman、Buildah 或 Apptainer。
- 不进行新训练，不做阈值搜索，不使用 validation GT。
- 不上传网盘、validation 或 Docker，不发送组织方邮件。
- 不作历史 `0.6691` 或任何未绑定 hosted metric claim。
- 允许复用已有 fresh outputs、checkpoint、代码和 runtime。
- 允许完成必要的 frozen inference、生产源码、sentinel、bundle 和 validator。
- 不得再次因为 package A mismatch、13 个体素 GPU replay 差异或历史 lineage unresolved 写 blocked packet。
- 只有固定资产缺失/哈希错误、生产代码无法运行、Cine 资产无法加载、bundle validator 失败，才允许阻塞服务器 bundle。

## 四、启动与必读

```bash
cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH

git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -20
git diff --check
```

若 main 落后且工作树干净，只允许：

```bash
git pull --ff-only origin main
```

完整读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
wiki/README.md
.agents/skills/care-mapper/SKILL.md
.agents/skills/slurm-routing-partition/SKILL.md
prompts/tasks/20260801_care_test_docker_packaging_controller.md
prompts/tasks/20260801_care_test_docker_server_bundle_controller.md
prompts/tasks/20260801_care_test_docker_provenance_reconcile_and_bundle_controller.md
results/20260801_care_test_docker_packaging/**
results/20260801_care_test_docker_server_bundle/**
results/20260801_care_test_docker_provenance_reconcile_and_bundle/**
results/20260801_care_nnunet_mosaic_complementarity_closure/**
results/20260801_mosaic_leaderboard_live_snapshot/**
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/submission_lineage_evidence.json
```

新结果目录：

```text
results/20260801_care_test_docker_final_model_freeze_and_bundle
```

复用 runtime：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine
```

## 五、W1：只做一次提交模型证据冻结，不再跑模型竞赛

生成：

```text
results/20260801_care_test_docker_final_model_freeze_and_bundle/final_submission_model_ledger.md
results/20260801_care_test_docker_final_model_freeze_and_bundle/final_submission_model_contract.json
```

ledger 必须至少列出：

```text
candidate/source
pathology/task
local fair evidence
hosted attribution evidence
source code path/commit
checkpoint path/SHA256
runtime recipe
provenance confidence
selected/not selected
reason
```

必须明确：

```text
selected_myops_scar = mosaic_repo_final_scar
selected_myops_pure_edema = dataset501_nnunet_5fold_best_default_tta_class4
selected_myops_anatomy = dataset501_nnunet_5fold_best_default_tta_classes123
selected_cinemyops = mosaic_repo_final_cine
historical_0_6691_lineage = UNRESOLVED_NOT_CLAIMED
```

该 ledger 是解释性冻结，不得触发新的候选训练或 replay 矩阵。

## 六、W2：固定资产与源码闭包

验证并记录：

### nnU-Net

```text
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth
...
fold_4/checkpoint_best.pth
plans.json
dataset.json
trainer/inference source
```

### MoSAIC MyoPS

```text
/users/a/e/aereinh/MoSAIC/code/source @ d334bd1fb2a99dbbc230510590cd8e3ee08cc377
/users/a/e/aereinh/MoSAIC/code/weights/myops/coarse.pt
/users/a/e/aereinh/MoSAIC/code/weights/myops/fine_scar.pt
```

### MoSAIC Cine

```text
/users/a/e/aereinh/MoSAIC/code/weights/cinemyops/coarse.pt
/users/a/e/aereinh/MoSAIC/code/weights/cinemyops/fine_v1.pt
/users/a/e/aereinh/MoSAIC/code/weights/cinemyops/fine_v2.pt
```

使用已有 asset manifest 的固定 SHA256。任何 SHA mismatch 才是硬阻塞。

生成实际 import/source closure，确保 Docker 运行时不依赖：

```text
/users
/overflow
/nas
/project
网络下载
未复制的 repo 文件
```

## 七、W3：完成 Cine 15/15 与生产 host smoke

复用已完成的 MoSAIC MyoPS 15/15 fresh replay，不重复运行。

将 MoSAIC Cine 从当前 4/15 继续至 15/15。不得因 nnU-Net replay 差异停止。

对最终固定 MyoPS graph 与 Cine graph 各做至少 3 个公开 validation sentinel host smoke，病例按输入大小/帧数最小、中位、最大选择，不按预测或分数选择。

服务器 host smoke 的目的仅是：

- 权重可加载；
- 推理正常退出；
- 输出几何正确；
- label schema 正确；
- source intervention 有效；
- 生成工位 bundle 的 expected diagnostic outputs。

服务器 GPU 两次推理不要求 bitwise exact，不再作为 hard gate。

## 八、W4：生产源码

完成并审计：

```text
docker/CARE2026_Myocardium/MyoPS/Dockerfile
docker/CARE2026_Myocardium/MyoPS/entrypoint.sh
docker/CARE2026_Myocardium/MyoPS/predict.py
docker/CARE2026_Myocardium/MyoPS/requirements.lock
docker/CARE2026_Myocardium/MyoPS/README.md
docker/CARE2026_Myocardium/MyoPS/vendor/**

docker/CARE2026_Myocardium/CineMyoPS/Dockerfile
docker/CARE2026_Myocardium/CineMyoPS/entrypoint.sh
docker/CARE2026_Myocardium/CineMyoPS/predict.py
docker/CARE2026_Myocardium/CineMyoPS/requirements.lock
docker/CARE2026_Myocardium/CineMyoPS/README.md
docker/CARE2026_Myocardium/CineMyoPS/vendor/**
```

要求：

- 完全离线运行；
- 默认 `CARE_DEVICE=cpu`；
- 可选 `CARE_DEVICE=cuda`；
- `/input` 只读、`/output` 可写；
- 每病例 atomic output；
- 任一病例失败非零退出；
- 无绝对服务器路径；
- 依赖精确锁定；
- 不下载权重或包；
- MyoPS context 只含 MoSAIC scar 权重，不含 `coarse_edema.pt` 或 `edema.pt`。

MyoPS source intervention：

```text
CARE_DISABLE_MOSAIC_SCAR=1
  -> scar changed voxels > 0

CARE_DISABLE_NNUNET_EDEMA=1
  -> pure-edema changed voxels > 0

CARE_ENABLE_MOSAIC_EDEMA=0 versus 1
  -> final complete arrays exactly equal
```

## 九、W5：新的合理复现门

不再比较历史 package A，也不再要求服务器 GPU 与工位 CPU bitwise identical。

最终 Docker 的复现门改为：

### 容器内部 CPU 确定性

工位后续对 3 个 MyoPS 和 3 个 Cine sentinel，将同一 image、同一 input、同一环境连续运行两次：

```text
array equality = true
geometry equality = true
```

若 CPU 两次不一致，先固定：

```text
random seeds
OMP/MKL threads
torch deterministic algorithms
inference eval mode
file ordering
```

这些属于工程确定化，不改变模型来源、fold、TTA、阈值或 decode。

### 服务器 host 与 Docker CPU 保真

只要求：

```text
geometry exact
label set exact
all required pathology labels loadable
no NaN/Inf
per-label Dice between host diagnostic and Docker >= 0.9999
changed voxel fraction <= 1e-5
no new remote connected component caused solely by port
```

该比较用于发现端口错误，不要求跨硬件浮点路径每个边界体素完全相同。若超过阈值，必须修复 port；不得换模型。

## 十、W6：transfer bundle

创建：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/transfer_bundle
```

必须包含：

```text
BUNDLE_MANIFEST.json
WORKSTATION_INSTRUCTIONS.md
server_receipts/
contexts/MyoPS/**
contexts/CineMyoPS/**
sentinel/myops/**
sentinel/cinemyops/**
verification/**
```

普通文件复制，不得使用软链接。

MyoPS models：

```text
5 x checkpoint_best.pth
plans.json
dataset.json
MoSAIC myops/coarse.pt
MoSAIC myops/fine_scar.pt
```

Cine models：

```text
coarse.pt
fine_v1.pt
fine_v2.pt
```

`BUNDLE_MANIFEST.json` 记录每个文件的 relative path、size、SHA256、role、source path、source commit/license，且 `copied_not_symlink=true`。

生成确定性归档：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/CARE-Docker-Workstation-Bundle.tar
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/CARE-Docker-Workstation-Bundle.tar.sha256
```

## 十一、SERVER_BUNDLE_READY

满足以下条件即必须生成，不得再添加 provenance 门：

- final model contract 已冻结；
- 所有固定资产 SHA PASS；
- MoSAIC MyoPS 15/15 已有；
- MoSAIC Cine 15/15 完成；
- host sentinel smoke PASS；
- production source 和 intervention PASS；
- bundle manifest/validator/SHA PASS；
- lightweight commit/push 完成。

写：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/SERVER_BUNDLE_READY.json
```

必须包含：

```json
{
  "status": "READY",
  "workstation_build_authorized": true,
  "selected_myops_scar": "mosaic_repo_final_scar",
  "selected_myops_pure_edema": "dataset501_nnunet_5fold_best_default_tta_class4",
  "selected_myops_anatomy": "dataset501_nnunet_5fold_best_default_tta_classes123",
  "selected_cinemyops": "mosaic_repo_final_cine",
  "historical_0_6691_lineage": "UNRESOLVED_NOT_CLAIMED",
  "gpu_replay_changed_voxels_total": 13,
  "gpu_bitwise_repeat_required": false,
  "archive_path": "...",
  "archive_sha256": "...",
  "expected_workstation_root": "/home/yuukias/code/CARE",
  "final_server_dist": "/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_rootless_unblock/dist"
}
```

## 十二、validator 与 known-bad

新增：

```text
scripts/validation/validate_care_test_docker_final_model_freeze_and_bundle.py
```

至少覆盖：

- 再次把 package A 15/15 exact 当 ready 条件；
- 再次把 13 个 GPU changed voxels 当模型不可部署；
- 选择非冻结模型或重新比较 checkpoint/TTA；
- 声称历史 `0.6691` 已复现；
- MyoPS 使用 MoSAIC edema 权重；
- MyoPS 未使用五折 nnU-Net；
- Cine 仍停在 4/15；
- source intervention 失败；
- bundle 有软链接、绝对路径、缺失 SHA；
- 权重/NIfTI/tar 进入 Git；
- marker 在 commit/push 前生成；
- 自动上传或发送邮件。

结果目录至少包含：

```text
controller_context.json
controller_ledger.csv
final_submission_model_ledger.md
final_submission_model_contract.json
production_asset_manifest.json
fresh_mosaic_cine_15case_manifest.json
host_sentinel_manifest.json
source_intervention_receipt.json
transfer_bundle_receipt.json
mapper_report_final.md
finalizer_state.json
strict_validator_report.json
controller_report.md
completion_check.md
MANIFEST.md
notification_brief.json
```

## 十三、Git 与通知

提交前：

```bash
git diff --check
git status --short
./envs/env_CARE/bin/python scripts/validation/validate_care_test_docker_final_model_freeze_and_bundle.py
```

只提交轻量源码与证据：

```text
prompts/tasks/20260801_care_test_docker_final_model_freeze_and_bundle_controller.md
docker/CARE2026_Myocardium/** source only
scripts/validation/validate_care_test_docker_final_model_freeze_and_bundle.py
results/20260801_care_test_docker_final_model_freeze_and_bundle/** lightweight only
prompts/routes/handoffs/CURRENT.md
wiki/README.md
```

提交信息：

```text
package: freeze final CARE Docker models and prepare bundle
```

推送：

```bash
git push origin main
```

禁止 force push。

commit/push 验证后运行：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

## 十四、最终回答

必须先用自然中文说明：

1. 最终 MyoPS 与 Cine 各交什么模型；
2. 为什么 13 个变化体素不再阻止打包；
3. 历史 `0.6691` 是否仍未闭合且未作 claim；
4. MoSAIC Cine 是否完成 15/15；
5. transfer bundle 是否 ready，路径、大小、SHA256；
6. 工位是否可以开始 WSL Docker build；
7. Git commit/push SHA；
8. 明确说明未上传网盘、未发送组织方邮件、未上传 Docker/validation。

不得再用“需要 Planner 决定模型”作为终态；模型已在本合同冻结。