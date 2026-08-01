你是 CARE Docker 跨机器打包任务的服务器端 Controller。

当前仓库：

/users/a/e/aereinh/CARE

远端：

YuukiAS/CARE_Challenge

当前开发姿态：

main-only

任务目标：

服务器不再尝试安装或运行 Docker。服务器负责完成所有需要现有数据、GPU、模型权重和历史资产的工作，并生成一个可以通过 SSH 直接下载到工位 WSL 的、自包含 Docker 构建与验证资源包。

本任务继承并替代以下任务的后续执行阶段，但不得删除或篡改旧阻塞证据：

prompts/tasks/20260801_care_test_docker_packaging_controller.md
prompts/tasks/20260801_care_test_docker_rootless_unblock_controller.md

旧结论 ROOTLESS_DOCKER_PREREQUISITE_BLOCKED 仍然有效，只是不再阻止服务器执行 fresh inference、生产源码准备和跨机器 bundle 构建。

必须遵守：

- 不使用 sudo。
- 不修改 /etc、系统服务或系统级 Docker。
- 不再尝试 rootless Docker、Podman、Buildah、Apptainer 或其他容器替代方案。
- 不写 /overflow/htzhu/CARE。
- 不进行新训练。
- 不上传 Google Drive、网盘或其他云存储。
- 不发送组织方邮件。
- 不上传 validation。
- 可以使用当前已有 GPU allocation；若没有可用 allocation，沿用此前授权范围，只允许提交一个冻结推理作业，并把 nnU-Net、MoSAIC MyoPS、MoSAIC Cine replay 串行放在同一个作业中。
- 可以 commit/push origin/main，但只能推送源码、脚本、Markdown、JSON、CSV、validator 和小型证据。
- 严禁把权重、checkpoint、NIfTI、Docker archive、transfer bundle 或大日志提交到 Git。

新任务名称：

20260801_care_test_docker_server_bundle

结果目录：

results/20260801_care_test_docker_server_bundle

服务器 runtime：

/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine

最终跨机器资源目录：

/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer

最终仍需由工位回传 Docker 归档的服务器目录：

/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_rootless_unblock/dist

一、同步与协议读取

进入仓库并执行：

cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH

git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -15
git diff --check

若 main 落后且工作树干净，只允许：

git pull --ff-only origin main

完整读取：

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
prompts/tasks/20260801_care_test_docker_rootless_unblock_controller.md
results/20260801_care_test_docker_packaging/**
results/20260801_care_test_docker_rootless_unblock/**
results/20260801_care_test_docker_packaging/production_asset_manifest.json

将本合同保存为：

prompts/tasks/20260801_care_test_docker_server_bundle_controller.md

二、冻结生产决策

MyoPS 最终组合不得改变：

anatomy    = historical frozen 5-fold nnU-Net
pure edema = historical frozen 5-fold nnU-Net class 4
scar       = MoSAIC repo-final scar
priority   = scar > pure edema > anatomy

官方标签：

0    background
200  myocardium
500  LV
600  RV
1220 pure edema
2221 scar

MyoPS 禁止调用：

MoSAIC coarse_edema.pt
MoSAIC edema.pt
M0R
M1
M2
M3
PRISM
MyoWall
QIF
任何病例级选择器
任何 validation 驱动阈值搜索

MyoPS bundle 中只允许包含以下 MoSAIC 权重：

myops/coarse.pt
myops/fine_scar.pt

不得把 myops/coarse_edema.pt 或 myops/edema.pt 放进 MyoPS Docker context。

CineMyoPS 固定使用：

cinemyops/coarse.pt
cinemyops/fine_v1.pt
cinemyops/fine_v2.pt
z-spacing branches 4/8/16
冻结的 TTA 和 final decode

三、完成 fresh 15/15 nnU-Net provenance replay

必须真正重新运行 frozen Dataset501 五折 nnU-Net：

model root:

data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres

folds:

0,1,2,3,4

checkpoint:

checkpoint_best.pth

固定使用历史 package 中的 15 个 validation case ID。

不得：

- 把历史 prediction 复制成 fresh 输出。
- 把历史 prediction 作为模型输入。
- 改 checkpoint、TTA、decode、阈值、plans 或 trainer。
- 只跑部分病例。

逐病例比较 fresh 输出与历史 package A：

- case ID
- shape
- voxel array
- spacing
- origin
- direction
- affine
- label set
- canonical array+geometry SHA256

不要求 `.nii.gz` 压缩字节相同。

只有 15/15 array 与 geometry 完全一致时，写：

NNUNET_EDEMA_PROVENANCE_REPRODUCED

输出：

results/20260801_care_test_docker_server_bundle/fresh_nnunet_15case_manifest.json
results/20260801_care_test_docker_server_bundle/fresh_nnunet_vs_historical_casewise.csv
results/20260801_care_test_docker_server_bundle/fresh_nnunet_provenance_receipt.json

任一病例不一致时：

- 写 NNUNET_PROVENANCE_REPLAY_MISMATCH。
- 不生成 MyoPS 可执行 bundle。
- 仍可完成 Cine 诊断，但不得生成 SERVER_BUNDLE_READY.json。

四、完成 fresh MoSAIC replay

冻结 MoSAIC repo：

/users/a/e/aereinh/MoSAIC/code/source

commit：

d334bd1fb2a99dbbc230510590cd8e3ee08cc377

先验证生产资产清单中所有相关 SHA256。

Fresh replay：

- MyoPS 公开 validation 15/15。
- CineMyoPS 公开 validation 15/15。
- 使用 repo-final preprocess、TTA、z-spacing branch 和 decode。
- 不使用历史输出替代 fresh inference。
- 不进行新训练或阈值搜索。

输出：

results/20260801_care_test_docker_server_bundle/fresh_mosaic_myops_manifest.json
results/20260801_care_test_docker_server_bundle/fresh_mosaic_cine_manifest.json
results/20260801_care_test_docker_server_bundle/fresh_mosaic_replay_receipt.json

五、实现并验证正式生产源码

在仓库中创建：

docker/CARE2026_Myocardium/MyoPS/Dockerfile
docker/CARE2026_Myocardium/MyoPS/entrypoint.sh
docker/CARE2026_Myocardium/MyoPS/predict.py
docker/CARE2026_Myocardium/MyoPS/requirements.lock
docker/CARE2026_Myocardium/MyoPS/README.md
docker/CARE2026_Myocardium/MyoPS/models/.gitkeep
docker/CARE2026_Myocardium/MyoPS/vendor/

docker/CARE2026_Myocardium/CineMyoPS/Dockerfile
docker/CARE2026_Myocardium/CineMyoPS/entrypoint.sh
docker/CARE2026_Myocardium/CineMyoPS/predict.py
docker/CARE2026_Myocardium/CineMyoPS/requirements.lock
docker/CARE2026_Myocardium/CineMyoPS/README.md
docker/CARE2026_Myocardium/CineMyoPS/models/.gitkeep
docker/CARE2026_Myocardium/CineMyoPS/vendor/

要求：

- Docker production source 完全自包含。
- vendor 只包含推理所需的一方或允许复用代码。
- 记录每个 vendored source 的来源、commit、license 和 SHA256。
- 不允许任何 `/users`、`/overflow`、`/nas`、`/project` 绝对路径。
- 不允许运行时下载权重、代码或 Python 包。
- 默认读取 `/input`，写入 `/output`。
- `/input` 只读时可正常运行。
- 每病例使用临时输出并 atomic rename。
- 任一病例失败时容器必须非零退出并打印 case ID 和错误。
- 正常结束返回 0。
- 重复运行不能残留旧病例输出或临时状态。
- 默认 `CARE_DEVICE=cpu`。
- 可选 `CARE_DEVICE=cuda`，但不能影响 CPU 路径存在。
- Python、PyTorch、nnU-Net、NumPy、SciPy、SimpleITK、nibabel 等版本必须从当前已验证生产环境和实际 import closure 冻结。
- 不得使用 `latest` 或无版本依赖。
- 基础镜像的 Python major/minor 必须与当前验证环境兼容；不得为了方便任意升级。
- Dockerfile 中所有依赖必须在 build 阶段安装，运行阶段完全离线。

必须提供默认关闭的测试干预开关：

CARE_DISABLE_MOSAIC_SCAR=1
CARE_DISABLE_NNUNET_EDEMA=1
CARE_ENABLE_MOSAIC_EDEMA=1

其语义固定：

- 默认全部关闭，生产输出不受测试开关影响。
- 关闭 MoSAIC scar 后，最终 scar 必须改变。
- 关闭 nnU-Net edema 后，最终 pure edema 必须改变。
- 打开或关闭 CARE_ENABLE_MOSAIC_EDEMA，最终输出必须完全相同。
- MyoPS 源码不得加载任何 MoSAIC edema checkpoint。

在服务器 host 环境中直接运行与 Docker `predict.py` 同一核心函数，证明源码可以在无 Docker 条件下完成推理。

六、冻结 sentinel 病例与 host 期望输出

从 15 例公开 validation 中为每个任务选择 3 例：

MyoPS：

- 最小输入体积病例
- 中位输入体积病例
- 最大输入体积病例

CineMyoPS：

- 最少帧数病例
- 中位帧数病例
- 最多帧数病例

不得按预测结果或分数选病例。

为每个 sentinel 复制：

- 原始输入。
- host production baseline 输出。
- 三项 MyoPS intervention 输出。
- shape/spacing/origin/direction/affine。
- label set。
- canonical array+geometry SHA256。
- wall time。
- peak RSS。
- 使用的 source/checkpoint SHA256。

MyoPS host 输出规则：

scar = fresh MoSAIC final scar
pure edema = fresh 5-fold nnU-Net class 4 AND NOT scar
anatomy = fresh 5-fold nnU-Net classes 1/2/3 where pathology absent
priority = scar > pure edema > anatomy

禁止 hard myocardium clipping MoSAIC scar。

七、生成跨机器 transfer bundle

创建：

/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/transfer_bundle

结构固定为：

transfer_bundle/
  BUNDLE_MANIFEST.json
  WORKSTATION_INSTRUCTIONS.md
  server_receipts/
  contexts/
    MyoPS/
      Dockerfile
      entrypoint.sh
      predict.py
      requirements.lock
      README.md
      vendor/
      models/
    CineMyoPS/
      Dockerfile
      entrypoint.sh
      predict.py
      requirements.lock
      README.md
      vendor/
      models/
  sentinel/
    myops/
      input/
      expected_baseline/
      expected_disable_mosaic_scar/
      expected_disable_nnunet_edema/
      expected_mosaic_edema_toggle/
    cinemyops/
      input/
      expected_baseline/
  verification/
    verify_bundle.py
    compare_nifti_array_geometry.py
    validate_label_schema.py
    validate_source_interventions.py

模型文件必须复制为普通文件，不得使用指向服务器其他位置的软链接。

MyoPS models 只能包含：

- 5 个 nnU-Net fold checkpoint_best.pth
- plans.json
- dataset.json
- MoSAIC myops/coarse.pt
- MoSAIC myops/fine_scar.pt

Cine models 只能包含：

- cinemyops/coarse.pt
- cinemyops/fine_v1.pt
- cinemyops/fine_v2.pt

BUNDLE_MANIFEST.json 必须记录每个文件：

- relative path
- size
- SHA256
- role
- source path
- source commit
- license/provenance
- copied_not_symlink = true

同时记录：

- server git SHA
- origin/main SHA
- task prompt SHA256
- nnU-Net provenance token
- MoSAIC commit
- sentinel case IDs
- expected workstation root:
  /home/yuukias/code/CARE
- required image tags:
  care-myops-organagent:v1
  care-cinemyops-organagent:v1
- final archive filenames:
  MyoPS-OrganAgent-v1.tar.gz
  CineMyoPS-OrganAgent-v1.tar.gz

先运行：

verification/verify_bundle.py

必须验证：

- manifest 中所有文件存在。
- 所有 SHA256 正确。
- 没有软链接。
- 没有绝对服务器路径。
- MyoPS context 不含 MoSAIC edema 权重。
- 没有历史 prediction 被错误放进模型目录。
- 没有 checkpoint/NIfTI 被放进 Git 工作树。
- Docker contexts 可被普通用户读取。

八、归档与服务器就绪标记

优先生成单一归档：

/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/CARE-Docker-Workstation-Bundle.tar

使用确定性 tar 元数据；不要依赖 Google Drive。

生成：

CARE-Docker-Workstation-Bundle.tar.sha256

最后写：

/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/SERVER_BUNDLE_READY.json

只有以下条件全部满足时才能写 ready：

- fresh nnU-Net 15/15 provenance replay PASS。
- fresh MoSAIC MyoPS 15/15 PASS。
- fresh MoSAIC Cine 15/15 PASS。
- 两套生产源码完成。
- host sentinel baseline 完成。
- MyoPS 三项 intervention 完成。
- bundle validator PASS。
- archive SHA256 PASS。
- repo lightweight commit/push 成功。

SERVER_BUNDLE_READY.json 必须包含：

{
  "status": "READY",
  "server_repo": "/users/a/e/aereinh/CARE",
  "server_commit_sha": "...",
  "origin_main_sha": "...",
  "archive_path": ".../CARE-Docker-Workstation-Bundle.tar",
  "archive_sha256_path": ".../CARE-Docker-Workstation-Bundle.tar.sha256",
  "archive_sha256": "...",
  "archive_size_bytes": 0,
  "bundle_manifest_path": ".../transfer_bundle/BUNDLE_MANIFEST.json",
  "expected_workstation_root": "/home/yuukias/code/CARE",
  "final_server_dist": "/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_rootless_unblock/dist",
  "myops_ready": true,
  "cinemyops_ready": true
}

若任一硬门失败，写：

SERVER_BUNDLE_BLOCKED.json

不得写伪 ready，也不得让工位开始执行。

九、结果、验证和 Git

结果目录至少包含：

results/20260801_care_test_docker_server_bundle/controller_context.json
results/20260801_care_test_docker_server_bundle/controller_ledger.csv
results/20260801_care_test_docker_server_bundle/implementation_snapshot.md
results/20260801_care_test_docker_server_bundle/production_asset_manifest.json
results/20260801_care_test_docker_server_bundle/fresh_nnunet_15case_manifest.json
results/20260801_care_test_docker_server_bundle/fresh_nnunet_vs_historical_casewise.csv
results/20260801_care_test_docker_server_bundle/fresh_nnunet_provenance_receipt.json
results/20260801_care_test_docker_server_bundle/fresh_mosaic_myops_manifest.json
results/20260801_care_test_docker_server_bundle/fresh_mosaic_cine_manifest.json
results/20260801_care_test_docker_server_bundle/source_intervention_receipt.json
results/20260801_care_test_docker_server_bundle/sentinel_manifest.json
results/20260801_care_test_docker_server_bundle/transfer_bundle_receipt.json
results/20260801_care_test_docker_server_bundle/mapper_report_final.md
results/20260801_care_test_docker_server_bundle/finalizer_state.json
results/20260801_care_test_docker_server_bundle/strict_validator_report.json
results/20260801_care_test_docker_server_bundle/controller_report.md
results/20260801_care_test_docker_server_bundle/completion_check.md
results/20260801_care_test_docker_server_bundle/MANIFEST.md
results/20260801_care_test_docker_server_bundle/notification_brief.json

新增严格 validator：

scripts/validation/validate_care_test_docker_server_bundle.py

known-bad 至少覆盖：

- fresh rerun 只有 14 例却宣称 reproduced。
- gzip 字节不同被误判为 array 不同。
- geometry 不一致仍通过。
- MyoPS bundle 包含 MoSAIC edema.pt。
- MyoPS bundle 未包含五折 nnU-Net。
- bundle 内存在服务器绝对路径。
- bundle 内存在软链接。
- intervention 未改变对应病种。
- MoSAIC edema 开关改变输出。
- archive SHA 不匹配。
- ready marker 在 commit/push 前生成。
- 大文件进入 Git staged set。

提交前执行：

git diff --check
git status --short
./envs/env_CARE/bin/python scripts/validation/validate_care_test_docker_server_bundle.py

只提交轻量文件：

git add prompts/tasks/20260801_care_test_docker_server_bundle_controller.md
git add docker/CARE2026_Myocardium
git add scripts/validation/validate_care_test_docker_server_bundle.py
git add results/20260801_care_test_docker_server_bundle
git add prompts/routes/handoffs/CURRENT.md wiki/README.md

提交信息：

package: prepare workstation CARE Docker bundle

推送：

git push origin main

禁止把 transfer bundle、weights、NIfTI 或 archive 加入 Git。

完成 commit/push 后才允许写 SERVER_BUNDLE_READY.json；若 marker 需要记录最终 commit SHA，则在 push 后更新 runtime marker，不必把 runtime marker提交 Git。

最后按既有 notifier 规则执行：

./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once

最终回答必须先用自然中文说明：

- 服务器是否已经准备好两个任务的完整 bundle。
- fresh nnU-Net provenance 是否 15/15 reproduced。
- fresh MoSAIC 两条路径是否完成。
- archive 路径、大小和 SHA256。
- Git commit/push 状态。
- 工位下一步只需要执行哪个本地提示词。

不得声称 Docker 已构建或可提交；服务器阶段只证明 bundle 已准备好。