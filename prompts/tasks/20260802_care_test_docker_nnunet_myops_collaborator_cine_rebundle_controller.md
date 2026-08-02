---
task_key: 20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle
task_kind: scientific_milestone
task_type: docker_final_resource_revision
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
slurm_runtime_continuity_required: false
continuity_backend: none
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: true
new_training_authorized: false
frozen_inference_authorized: true
server_docker_runtime_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
cloud_upload_authorized: false
organizer_email_send_authorized: false
hosted_metric_claim_authorized: false
supersedes_commit: c2f946b9376f4b39700f04b39c6d7a16e7154e67
---

# CARE 2026 Myocardium Docker 最终资源修订 Controller

## 任务结论先行

本任务修订并取代 commit `c2f946b9376f4b39700f04b39c6d7a16e7154e67` 的旧服务器 bundle。旧 MyoPS 配方是 MoSAIC scar 加 nnU-Net pure-edema/anatomy；新最终配方改为 MyoPS 全部使用 Dataset501 五折 nnU-Net 六类输出。CineMyoPS 不再由服务器重建源码镜像，而是直接使用合作者提供的现成 Docker save archive。

服务器端只负责版本冻结、资源下载、静态归档审计、纯 nnU-Net MyoPS context、sentinel、transfer bundle 和轻量 Git 结果。服务器不得安装或运行 Docker、Podman、Buildah、Apptainer，不得 sudo，不得修改 `/etc`，不得新训练，不得上传 challenge/validation/网盘/Docker，不得发送组织方邮件，不得写入 `/overflow/htzhu/CARE`，不得把 checkpoint、Docker tar、NIfTI 或大归档提交 Git。

## 同步和必读

执行环境：

```bash
cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH
```

启动命令：

```bash
git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -15
git diff --check
```

若工作树干净且 `main` 落后，只允许 `git pull --ff-only origin main`。必须读取根协议、route 协议、`CURRENT.md`、`routes/README.md`、`wiki/README.md`、上一轮任务和上一轮 bundle 结果/源码。

## 新最终模型

### MyoPS：纯 Dataset501 五折 nnU-Net

固定字段：

```text
dataset: Dataset501_CAREMyoPS
trainer: nnUNetTrainer_500epochs
configuration: 3d_fullres
folds: 0,1,2,3,4
checkpoint: checkpoint_best.pth
TTA: current frozen default TTA
raw labels: 0 background, 1 myocardium, 2 LV, 3 RV, 4 pure edema, 5 scar
official labels: 0, 200, 500, 600, 1220, 2221
image tag: care-myocardium-myops:organagent
final archive target: MyoPS-OrganAgent.tar.gz
input: /input
output: /output/myops/<CaseID>_pred.nii.gz
```

最终输出必须是单一 nnU-Net 六类 argmax 的直接语义映射：

```text
0 -> 0
1 -> 200
2 -> 500
3 -> 600
4 -> 1220
5 -> 2221
```

禁止 MoSAIC scar overlay、scar priority overwrite、MoSAIC edema、CARE-DG、SCR、CARE-ASE、ARC、PRISM、MyoWall、病例选择器、historical package A prediction 作为运行源、validation-driven threshold/postprocess。

### CineMyoPS：合作者现成 Docker

最终 archive 必须原样使用：

```text
CineMyoPS-OrganAgent.tar.gz
Google Drive file id: 1GSglKZYsYXkK6omQH5OrIkH8X43mWFjG
expected SHA256: c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136
image tag: care-myocardium-cinemyops:organagent
input: /input
output: /output/cinemyops
```

该 archive 不得重新压缩、重打包、改 tag、改 Docker config 或修改任何字节。

### 合作者 MyoPS archive 仅作 reference

```text
Google Drive file id: 1XCCCybipO6dfmktuVTlE6mV8xwKmlIeJ
file: MyoPS-OrganAgent.tar.gz
expected SHA256: 81d19bbefd8f7cca46aee32b31a774f16222b6146b9eab6bc7265a6c214de2ff
image tag in archive: care-myocardium-myops:organagent
```

只能用于静态审计 Docker save archive 格式、RepoTag、ENTRYPOINT、输入输出目录和运行说明。不得作为最终 MyoPS 提交文件，不得用其预测替代纯 nnU-Net，不得提取其模型或权重，不得用它选择或调整 nnU-Net。

## 必做输出

结果目录：

```text
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle
```

runtime：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle
```

最终 transfer：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/transfer
```

必须生成：

```text
controller_context.json
controller_ledger.csv
revised_final_submission_model_contract.json
nnunet_environment_fingerprint.json
nnunet_source_manifest.json
nnunet_dependency_freeze.txt
collaborator_archive_manifest.json
collaborator_myops_archive_audit.json
collaborator_cinemyops_archive_audit.json
pure_nnunet_myops_15case_manifest.json
pure_nnunet_myops_sentinel_manifest.json
pure_nnunet_myops_host_smoke_receipt.json
pure_nnunet_myops_output_mapping_receipt.json
transfer_bundle_receipt.json
strict_validator_report.json
controller_report.md
completion_check.md
MANIFEST.md
notification_brief.json
```

## nnU-Net 版本和源码

必须从服务器当前环境提取精确版本，记录 Python、平台、包版本、`nnUNetv2_predict` 路径和 shebang、`pip show nnunetv2`、`pip freeze`、nnunetv2 源码根目录、CLI SHA、trainer source SHA、源码 `.py` manifest、Dataset501 `plans.json`/`dataset.json`/五个 `checkpoint_best.pth` SHA。必须继续使用当前服务器 checkpoint 实际对应的 nnU-Net v2 版本和源码，禁止升级或降级。若 editable/local source，Docker 必须 vendor 同一源码；若标准发布包，`requirements.lock` 固定精确版本。

## 合作者 archives 下载和静态审计

允许用户空间安装 `gdown==5.2.0` 到 runtime `tools/`。下载两个 Google Drive 文件到 runtime `downloads/`。每个 archive 最多重试两次；SHA 不匹配必须停止使用对应 archive，不得自行接受不同版本。

静态审计要求：gzip 可解压，tar 可列出，存在 `manifest.json` 和 config JSON，RepoTags 精确匹配预期，config OS 为 linux、architecture 为 amd64，Config.Entrypoint 非空，记录 Env、WorkingDir、Labels、RootFS layers、archive size、file count、layer count，并检查路径穿越。没有 Docker daemon 时不得声称 run PASS。

## MyoPS production source

更新 `docker/CARE2026_Myocardium/MyoPS`，删除运行时 MoSAIC 依赖和 vendor source。Context 不得包含 MoSAIC weights/source。`predict.py` 只调用固定五折 nnU-Net；完整三模态输入发现顺序固定，LGE->0000、T2->0001、C0->0002；缺模态时明确错误并非零退出，不 zero-fill、不静默跳过。无输入时非零退出。输出 `/output/myops`，每病例 atomic rename，geometry 继承 nnU-Net output。默认 `CARE_DEVICE=cpu`，可选 `cuda`。正常运行不得读取服务器绝对路径。

固定调用语义：

```bash
nnUNetv2_predict -d 501 -tr nnUNetTrainer_500epochs -c 3d_fullres -f 0 1 2 3 4 -chk checkpoint_best.pth -i <prepared-input> -o <temporary-output> -npp 1 -nps 1 -device <cpu-or-cuda> --disable_progress_bar
```

不得加入 `--disable_tta`。

## 复用输出和 sentinel

优先复用此前已生成的 Dataset501 五折 nnU-Net 15 例 fresh outputs。验证 15/15、fold/checkpoint hashes、command 语义 best+folds0-4+default TTA、geometry 合法、raw label subset `{0,1,2,3,4,5}`，且没有 historical package A prediction 被作为模型输入。满足时不得重跑 15/15，直接转换 official labels 并生成 15 例 manifest。

选择三例 sentinel：最小输入体积、中位输入体积、最大输入体积。如果无需长期作业，可用固定生产 source 做 3 例 fresh frozen replay，并比较 geometry、label set、case ID、每标签 Dice 和 changed voxel fraction。无可用 GPU 不得阻塞 bundle；WSL CPU image 后续执行正式确定性门。只有旧 fresh outputs 不存在、损坏或 asset hash 不匹配，才允许重跑完整 15/15 frozen inference。

## Transfer

不要覆盖旧 c2f946b bundle。新 transfer 必须包含：

```text
SERVER_BUNDLE_READY.json
TRANSFER_MANIFEST.json
WORKSTATION_INSTRUCTIONS.md
MyoPS-nnUNet-workstation-bundle.tar.gz
MyoPS-nnUNet-workstation-bundle.tar.gz.sha256
CineMyoPS-OrganAgent.tar.gz
CineMyoPS-OrganAgent.tar.gz.sha256
reference/collaborator_myops_archive_audit.json
reference/collaborator_myops_remote_path.json
```

`MyoPS-nnUNet-workstation-bundle.tar.gz` 只包含 pure nnU-Net Docker context、五个 `checkpoint_best.pth`、`plans.json`、`dataset.json`、必要 nnunetv2 source 或 exact dependency lock、3 个 sentinel inputs、pure nnU-Net host expected outputs、verification scripts 和 receipts。不得包含任何 MoSAIC MyoPS 权重或源码。

合作者 MyoPS reference archive 留在 runtime downloads，不默认复制到主 transfer，以免和最终 MyoPS 混淆；manifest 记录其可选 rsync 路径和 SHA。

## SERVER_BUNDLE_READY 必填语义

`SERVER_BUNDLE_READY.json` 必须包含：

```json
{
  "status": "READY",
  "workstation_build_authorized": true,
  "supersedes_commit": "c2f946b9376f4b39700f04b39c6d7a16e7154e67",
  "selected_myops": "dataset501_nnunet_v2_5fold_best_default_tta_all_six_classes",
  "selected_myops_scar": "nnunet_raw_class5",
  "selected_myops_pure_edema": "nnunet_raw_class4",
  "selected_myops_anatomy": "nnunet_raw_classes123",
  "selected_cinemyops": "collaborator_provided_prebuilt_mosaic_docker",
  "myops_image_tag": "care-myocardium-myops:organagent",
  "cinemyops_image_tag": "care-myocardium-cinemyops:organagent",
  "myops_archive_target": "MyoPS-OrganAgent.tar.gz",
  "cinemyops_archive": "CineMyoPS-OrganAgent.tar.gz",
  "cinemyops_archive_sha256": "c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136",
  "collaborator_myops_reference_sha256": "81d19bbefd8f7cca46aee32b31a774f16222b6146b9eab6bc7265a6c214de2ff",
  "expected_workstation_root": "/home/yuukias/code/CARE",
  "final_server_dist": "/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_rootless_unblock/dist"
}
```

不得再写 MoSAIC scar selected for MyoPS、historical 0.6691 reproduced、collaborator MyoPS selected、server Docker run passed。

## Validator

新增 `scripts/validation/validate_care_test_docker_nnunet_myops_collaborator_cine_rebundle.py`。Known-bad 至少覆盖：MyoPS context 仍含 MoSAIC weight/source；MyoPS scar/edema/anatomy 不是 nnU-Net raw class 5/4/1-3；仍执行 scar overlay/priority overwrite；nnU-Net 版本未记录；Docker requirements 未绑定真实版本；folds 少于 5；使用 `checkpoint_final`；禁用 TTA；缺模态时 silent zero-fill；official map 错；合作者 Cine archive SHA 不匹配或被改字节；合作者 MyoPS reference 被标记为 final；静态 audit 被误写成 Docker run PASS；transfer 缺 sentinel/verification；checkpoint、Docker tar 或 NIfTI staged 到 Git；自动上传 challenge/网盘或发送组织方邮件。

## Git 和通知

提交前运行 scoped `git diff --check`、`git status --short` 和 strict validator。只提交轻量文件和源码，禁止 git add `*.pt`、`*.pth`、`*.nii`、`*.nii.gz`、`*.tar`、`*.tar.gz`、`downloads/`、`transfer/`。提交信息：

```text
package: switch MyoPS to pure nnU-Net and bind collaborator Cine Docker
```

推送 `git push origin main`，禁止 force push。commit/push 和远端 SHA 校验后调用既有 notifier：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```
