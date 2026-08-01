---
task_key: 20260801_care_test_docker_rootless_unblock
task_kind: scientific_milestone
task_type: rootless_linux_docker_install_fresh_replay_build_and_export
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
local_user_space_docker_install_authorized: true
system_wide_sudo_install_authorized: false
fresh_local_inference_authorized: true
new_training_authorized: false
one_gpu_inference_job_authorized: true
external_cloud_upload_authorized: false
organizer_email_send_authorized: false
official_validation_upload_authorized: false
hosted_metric_claim_authorized: false
supersedes_task: 20260801_care_test_docker_packaging
supersedes_blocked_decision: DOCKER_PACKAGING_BLOCKED_PROVENANCE
---

# CARE 2026 Myocardium 测试 Docker 本地解阻与正式打包 Controller

## Execution Contract

上一轮真实阻塞有两个原因：

1. 当前 checkout 没有完成 frozen 5-fold nnU-Net 在 15 例公开 validation 上的 fresh 15/15 replay，所以历史 `0.6691` edema 行仍只能标记为来源未闭合；
2. Linux 服务器没有 `docker` 命令，执行者按旧合同停止，没有构建任何未验证镜像。

用户现已明确授权：

- 在这台 Linux 服务器上安装并运行**用户空间 rootless Docker**；
- 本地执行必要的 frozen inference / fresh 15-case replay；
- 构建、load、run、save 两个测试 Docker；
- 把最终 `.tar.gz` 留在本地 runtime 目录供用户手动上传。

用户没有授权：

- 系统级 sudo 安装或修改 `/etc`；
- 新模型训练；
- 上传网盘；
- 给组织方发送邮件；
- validation 上传或 hosted 指标声明。

本任务必须生成两个独立镜像归档：

```text
MyoPS-OrganAgent-v1.tar.gz
CineMyoPS-OrganAgent-v1.tar.gz
```

官方任务要求必须冻结：

```text
submission email:
care26challenge@163.com or care2026challenge@outlook.com

subject:
[CARE-Myocardium Test] OrganAgent – Docker Submission

MyoPS input:
/input/myops/Case*_C0.nii.gz
/input/myops/Case*_LGE.nii.gz
/input/myops/Case*_T2.nii.gz

MyoPS output:
/output/myops/Case*_pred.nii.gz

CineMyoPS input:
/input/cinemyops/Case*_Cine.nii.gz

CineMyoPS output:
/output/cinemyops/Case*_pred.nii.gz

non-interactive, normal exit, /input read-only, /output writable
separate image for each task
CPU execution preferred; GPU requirement must be explained
deadline: 2026-08-03 23:59 PST
```

## Frozen production decision

### MyoPS

```text
anatomy: frozen historical 5-fold nnU-Net
pure edema: frozen historical 5-fold nnU-Net
scar: MoSAIC repo-final scar recipe
priority: scar > pure edema > anatomy
```

禁止：

```text
MoSAIC edema
M0R/M1/M2/M3
PRISM/MyoWall/QIF
case-wise model selection
validation-driven threshold tuning
hard myocardium clipping of MoSAIC scar
```

官方标签：

```text
0 background
200 myocardium
500 LV
600 RV
1220 pure edema
2221 scar
```

### CineMyoPS

固定使用 MoSAIC repo-final Cine recipe：

```text
coarse.pt
fine_v1.pt
fine_v2.pt
z-spacing branches 4/8/16
frozen TTA and final decode
```

不得改成旧 single-frame wrapper或未训练 temporal module。

## Controller Prompt

### W0 — Bootstrap、同步、协议与视觉门

```bash
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
```

若 main 落后且工作树干净，只允许 `git pull --ff-only origin main`。不得 reset、clean或写 `/overflow/htzhu/CARE`。

完整读取：

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
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
results/20260801_care_test_docker_packaging/**
results/leaderboard/care2026_validation_submission_alignment_20260726.md
results/20260801_mosaic_leaderboard_live_snapshot/leaderboard_snapshot.md
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/submission_lineage_evidence.json
```

视觉读取 Project 中 `SRR-v2`、`SRR-v2.5`、`SRR-v3`，在 context 中记录病种独立 authority、解剖保护和安全导出；本任务不实现 SRR。

### W1 — Linux/rootless Docker 前置审计

固定目录：

```bash
TASK_RUNTIME=/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_rootless_unblock
DOCKER_LOCAL=/users/a/e/aereinh/.local/docker-rootless
DOCKER_DIST=$TASK_RUNTIME/dist
ROOTLESS_RUN=$TASK_RUNTIME/rootless-run
mkdir -p "$TASK_RUNTIME" "$DOCKER_LOCAL" "$DOCKER_DIST" "$ROOTLESS_RUN"
chmod 700 "$ROOTLESS_RUN"
```

必须记录：

```bash
uname -a
uname -m
cat /etc/os-release
id
command -v docker || true
command -v dockerd-rootless.sh || true
command -v rootlesskit || true
command -v slirp4netns || true
command -v fuse-overlayfs || true
command -v newuidmap || true
command -v newgidmap || true
grep "^$(id -un):" /etc/subuid || true
grep "^$(id -un):" /etc/subgid || true
unshare -Ur true
findmnt -T /users/a/e/aereinh
findmnt -T /tmp
cat /proc/self/cgroup
```

用户空间 rootless Docker 的硬要求：

```text
architecture = x86_64/amd64
unprivileged user namespace works
newuidmap and newgidmap exist
/etc/subuid and /etc/subgid each provide >=65536 IDs for current user
writable local filesystem available for Docker data root
```

Docker data root 选择顺序固定：

```text
1. /tmp/<user>/care-rootless-docker-data if filesystem is local and writable
2. /scratch/<user>/care-rootless-docker-data if path exists, local, writable
3. /users/a/e/aereinh/.tmp/docker-data only if findmnt shows local non-NFS/non-Lustre filesystem
```

禁止把 Docker layer store放在 NFS、CIFS或Lustre。选择结果和 `findmnt` 写入 `rootless_storage_receipt.json`。

若现有 `docker info` 已经有可用 Server，直接记录并使用，不重复安装。只有 client 无 server或命令缺失时进入 W2。

### W2 — 用户空间 rootless Docker 安装

禁止 `curl | sh`，禁止 sudo，禁止修改 shell rc、`/etc`或系统服务。

从官方入口下载脚本到 runtime：

```bash
curl -fL --retry 3 --retry-delay 3 \
  https://get.docker.com/rootless \
  -o "$TASK_RUNTIME/docker-rootless-install.sh"
chmod 700 "$TASK_RUNTIME/docker-rootless-install.sh"
sha256sum "$TASK_RUNTIME/docker-rootless-install.sh" \
  > "$TASK_RUNTIME/docker-rootless-install.sha256"
head -n 40 "$TASK_RUNTIME/docker-rootless-install.sh"
grep -nE 'docker|rootless|download|static' "$TASK_RUNTIME/docker-rootless-install.sh" | head -n 100
```

安装时固定：

```bash
export HOME=/users/a/e/aereinh
export XDG_RUNTIME_DIR=$ROOTLESS_RUN
export PATH=/users/a/e/aereinh/bin:$DOCKER_LOCAL/bin:$PATH
export FORCE_ROOTLESS_INSTALL=1
sh "$TASK_RUNTIME/docker-rootless-install.sh"
```

不得让安装脚本写入 Git仓库。安装产物必须位于用户 home/bin或 `$DOCKER_LOCAL`；若脚本选择其他位置，停止并记录。

启动 daemon 使用任务专属 tmux：

```bash
export XDG_RUNTIME_DIR=$ROOTLESS_RUN
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock
export PATH=/users/a/e/aereinh/bin:$DOCKER_LOCAL/bin:$PATH

tmux kill-session -t care_rootless_docker 2>/dev/null || true
tmux new-session -d -s care_rootless_docker \
  "export HOME=/users/a/e/aereinh; \
   export XDG_RUNTIME_DIR=$ROOTLESS_RUN; \
   export DOCKER_HOST=unix://$ROOTLESS_RUN/docker.sock; \
   export PATH=/users/a/e/aereinh/bin:$DOCKER_LOCAL/bin:\$PATH; \
   dockerd-rootless.sh \
     --data-root '$DOCKER_DATA_ROOT' \
     --exec-root '$TASK_RUNTIME/docker-exec' \
     --pidfile '$TASK_RUNTIME/docker.pid' \
     > '$TASK_RUNTIME/dockerd-rootless.log' 2>&1"
```

等待最多 180 秒，每5秒检查：

```bash
docker version
docker info
```

通过条件：

```text
Client and Server both present
Server security options contain rootless
Docker Root Dir equals selected task-local data root
hello-world or busybox container runs non-interactively and exits 0
```

若缺 `newuidmap/newgidmap`、subuid/subgid或unprivileged namespace，终态为 `ROOTLESS_DOCKER_PREREQUISITE_BLOCKED`，必须写出管理员需要执行的最小修复，但不得自己sudo。不得用 Apptainer/Singularity 冒充 Docker完成。

### W3 — Fresh 15/15 nnU-Net provenance closure

旧阻塞包已经证明：

```text
历史 package A/B 的15例 MyoPS prediction bytes/voxel/geometry全部一致
cached historical predictions与 package A一致
fresh rerun case count = 0
```

因此本轮不是重新调查历史ZIP，而是必须实际完成 fresh 15/15 rerun。

冻结：

```text
Dataset501 5-fold nnU-Net fullres checkpoints fold0-4
nnUNetPlans.json
dataset.json
trainer/inference source
TTA
decode
official raw-label export
15-case validation input manifest
```

对每个资产记录 stat、SHA256和来源。使用历史 package 的15个 case ID作为固定case list，不得增删。

Fresh rerun必须使用当前冻结 production命令；不得读取历史 prediction作为模型输入或复制输出。运行方式：

- 若已有可用 H100 interactive allocation，使用 `srun --overlap`；
- 否则允许提交一个且仅一个 `htzhulab` frozen-inference job：1 GPU、12 CPU、96G、6小时；
- 仅推理，禁止训练、threshold search和checkpoint selection；
- wrapper必须调用 `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`，禁止裸 `python`；
- `care_test_docker_rootless_unblock` tmux watcher持续负责到 terminal accounting、15/15输出、聚合和validator。

Fresh输出与历史 package A逐病例比较：

```text
case ID equality
array voxel equality
shape/spacing/origin/direction/affine equality
label set equality
per-case SHA256 of uncompressed array+geometry canonical representation
```

NIfTI gzip字节不同不构成失败。

只有15/15 array+geometry完全一致时，写：

```text
NNUNET_EDEMA_PROVENANCE_REPRODUCED
```

若模型内容一致但压缩文件字节不同，仍是 reproduced。若任一病例array或geometry不同，终态为：

```text
NNUNET_PROVENANCE_REPLAY_MISMATCH
```

此时禁止构建 MyoPS hybrid Docker，因为当前模型无法绑定历史0.6691来源。

必须输出：

```text
fresh_nnunet_15case_manifest.json
fresh_nnunet_vs_historical_casewise.csv
fresh_nnunet_provenance_receipt.json
```

### W4 — Fresh MoSAIC production replay

冻结：

```text
source repo: /users/a/e/aereinh/MoSAIC/code/source
commit: d334bd1fb2a99dbbc230510590cd8e3ee08cc377

myops/coarse.pt
aae815c3dd50d6776e2af769551e8d6918a5dee4f83f29309a254051e067080c

myops/coarse_edema.pt
b9b596f1f5475ac852bf2c0be38a72c59e538dd3199f1f4989983433506ed9d4

myops/edema.pt
14a6a53f643bdbbac4c8234af2aa86e8a43423b761013f7b7f580965e1ed503c

myops/fine_scar.pt
94c54de3321000eabbc3c3a42a5d838410fb859a1c5b2460e6c2f6d773622ded

cinemyops/coarse.pt
225dedc45271216f5718391af9e0131e996c432df89b61240bef5e52ee451f4c

cinemyops/fine_v1.pt
05b31f649befeef8dd2003a0816310d03ee0385626c5c536db80faac9edacdab

cinemyops/fine_v2.pt
0f102c08c6d3374bd12e9d4d45585aa2017ffbf96192a0cdda1fb8653cc714fa
```

在15例公开 validation上fresh运行 repo-final MyoPS和Cine路径，冻结原repo TTA、spacing和decode。不得修改阈值。

注意：MyoPS production最终只消费 MoSAIC scar；`coarse_edema.pt`和`edema.pt`可以用于验证原repo final prediction，但不得进入最终 hybrid生产调用图。

必须输出：

```text
fresh_mosaic_myops_15case_manifest.json
fresh_mosaic_cine_15case_manifest.json
mosaic_frozen_replay_receipt.json
```

### W5 — 生产源码与自包含 build context

跟踪源码写入：

```text
docker/CARE2026_Myocardium/MyoPS/Dockerfile
docker/CARE2026_Myocardium/MyoPS/entrypoint.sh
docker/CARE2026_Myocardium/MyoPS/predict.py
docker/CARE2026_Myocardium/MyoPS/requirements.lock
docker/CARE2026_Myocardium/MyoPS/README.md

docker/CARE2026_Myocardium/CineMyoPS/Dockerfile
docker/CARE2026_Myocardium/CineMyoPS/entrypoint.sh
docker/CARE2026_Myocardium/CineMyoPS/predict.py
docker/CARE2026_Myocardium/CineMyoPS/requirements.lock
docker/CARE2026_Myocardium/CineMyoPS/README.md
```

任务runtime下构建自包含context：

```text
$TASK_RUNTIME/build-context/myops/
$TASK_RUNTIME/build-context/cinemyops/
```

context包含冻结源码、依赖lock和所需权重副本；不得使用指向 `/users` 的symlink。权重、build context和镜像层不得提交Git。

基础环境必须固定到经过当前checkpoint import/replay验证的Python/PyTorch/nnU-Net/MoSAIC版本。不得安装`latest`。允许选择：

```text
CPU-compatible pinned PyTorch image, or
pinned CUDA-runtime PyTorch image with real CPU fallback
```

选择规则固定：

```text
如果当前模型在本地CPU完成1例MyoPS和1例Cine推理且无不支持op，使用CPU image；
否则使用与当前GPU replay兼容的固定CUDA runtime image，并实现 CARE_DEVICE=cpu|cuda|auto，其中CPU路径仍必须通过1例smoke。
```

Docker build期间可下载基础镜像和依赖；容器运行期间必须完全离线，不得下载权重、代码或Python包。

MyoPS组合固定为：

```text
scar = MoSAIC repo-final scar mask
pure_edema = nnU-Net class4 AND NOT scar
anatomy = nnU-Net classes1/2/3 where pathology absent
final priority = scar > pure_edema > anatomy > background
```

所有来源先恢复到输入LGE原始物理几何；禁止只按array shape拼接。

容器必须：

```text
无 /users、/overflow、/nas 绝对依赖
无交互输入
/input只读
/output可写
每case临时写出后atomic rename
任一case失败则容器非零退出并列出case/error
正常完成返回0
重复运行不复用旧case缓存
```

### W6 — Build、load、CPU smoke和完整等价性

镜像标签固定：

```text
care-myops-organagent:v1
care-cinemyops-organagent:v1
```

构建：

```bash
docker build --pull \
  -t care-myops-organagent:v1 \
  "$TASK_RUNTIME/build-context/myops"

docker build --pull \
  -t care-cinemyops-organagent:v1 \
  "$TASK_RUNTIME/build-context/cinemyops"
```

必须测试：

1. **CPU single-case smoke**：每个task各1个最小病例，`CARE_DEVICE=cpu`，exit 0。
2. **Three-case CPU equivalence**：每个task固定最小/中位/最大体积或帧数各1例；host production与Docker逐体素、逐几何一致。总时限12小时。
3. **Full 15-case Docker replay触发规则**：
   - 若three-case线性外推每个task总时长 `<=8小时`，必须在Docker内完成该task全部15例；
   - 若外推 `>8小时`，不在CPU上继续浪费时间，检查rootless Docker GPU支持；若`docker run --gpus all` CUDA probe通过，则用 `CARE_DEVICE=cuda` 完成15例；
   - 若CPU外推>8小时且GPU容器不可用，允许不跑15例Docker全量，但three-case CPU equivalence仍必须通过，邮件草稿必须明确请求GPU并给出外推65/45病例时间；终态只能标记 `DOCKERS_READY_WITH_GPU_RUNTIME_REQUEST`，不能写CPU-ready。

MyoPS source intervention必须通过：

```text
关闭 MoSAIC scar source -> final scar voxels change
关闭 nnU-Net edema source -> final pure-edema voxels change
加载/关闭 MoSAIC edema权重 -> final hybrid output完全不变
```

输出审计：

```text
MyoPS labels subset {0,200,500,600,1220,2221}
Cine labels follow current official validation export contract
shape/spacing/origin/direction/affine与对应reference一致
integer dtype
no NaN/Inf
all output files readable
```

### W7 — Save、压缩、clean reload

导出路径固定：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_rootless_unblock/dist/MyoPS-OrganAgent-v1.tar.gz
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_rootless_unblock/dist/CineMyoPS-OrganAgent-v1.tar.gz
```

命令：

```bash
docker save care-myops-organagent:v1 | gzip -1 > "$DOCKER_DIST/MyoPS-OrganAgent-v1.tar.gz"
docker save care-cinemyops-organagent:v1 | gzip -1 > "$DOCKER_DIST/CineMyoPS-OrganAgent-v1.tar.gz"
sha256sum "$DOCKER_DIST"/*.tar.gz
```

随后删除本地镜像tag或使用独立clean Docker data-root验证：

```bash
gzip -dc "$DOCKER_DIST/MyoPS-OrganAgent-v1.tar.gz" | docker load
gzip -dc "$DOCKER_DIST/CineMyoPS-OrganAgent-v1.tar.gz" | docker load
docker inspect care-myops-organagent:v1
docker inspect care-cinemyops-organagent:v1
```

重新各跑1例，必须成功。记录image ID、RepoDigest/ID、archive size、SHA256、load/run exit code。

### W8 — 邮件草稿，不发送

生成两个草稿：

```text
results/20260801_care_test_docker_rootless_unblock/submission_email_draft_myops.md
results/20260801_care_test_docker_rootless_unblock/submission_email_draft_cinemyops.md
```

标题固定：

```text
[CARE-Myocardium Test] OrganAgent – Docker Submission
```

正文包含：

```text
task name
archive filename
SHA256
cloud download link placeholder
exact docker load command
exact docker run command
CPU/GPU requirement
measured and extrapolated runtime
/input and /output layout
contact note
```

不得调用Gmail或SMTP，不得上传网盘。

### W9 — Required outputs

必须生成：

```text
results/20260801_care_test_docker_rootless_unblock/controller_context.json
results/20260801_care_test_docker_rootless_unblock/rootless_prerequisite_audit.json
results/20260801_care_test_docker_rootless_unblock/rootless_storage_receipt.json
results/20260801_care_test_docker_rootless_unblock/rootless_install_receipt.json
results/20260801_care_test_docker_rootless_unblock/rootless_docker_info.txt
results/20260801_care_test_docker_rootless_unblock/fresh_nnunet_15case_manifest.json
results/20260801_care_test_docker_rootless_unblock/fresh_nnunet_vs_historical_casewise.csv
results/20260801_care_test_docker_rootless_unblock/fresh_nnunet_provenance_receipt.json
results/20260801_care_test_docker_rootless_unblock/fresh_mosaic_myops_15case_manifest.json
results/20260801_care_test_docker_rootless_unblock/fresh_mosaic_cine_15case_manifest.json
results/20260801_care_test_docker_rootless_unblock/mosaic_frozen_replay_receipt.json
results/20260801_care_test_docker_rootless_unblock/production_asset_manifest.json
results/20260801_care_test_docker_rootless_unblock/production_call_graph.md
results/20260801_care_test_docker_rootless_unblock/myops_source_intervention.csv
results/20260801_care_test_docker_rootless_unblock/docker_build_receipt.json
results/20260801_care_test_docker_rootless_unblock/docker_runtime_benchmark.csv
results/20260801_care_test_docker_rootless_unblock/docker_prediction_equivalence.csv
results/20260801_care_test_docker_rootless_unblock/docker_output_geometry_audit.csv
results/20260801_care_test_docker_rootless_unblock/docker_export_manifest.json
results/20260801_care_test_docker_rootless_unblock/submission_email_draft_myops.md
results/20260801_care_test_docker_rootless_unblock/submission_email_draft_cinemyops.md
results/20260801_care_test_docker_rootless_unblock/strict_validator_report.json
results/20260801_care_test_docker_rootless_unblock/known_bad_report.json
results/20260801_care_test_docker_rootless_unblock/controller_report.md
results/20260801_care_test_docker_rootless_unblock/completion_check.md
results/20260801_care_test_docker_rootless_unblock/MANIFEST.md
results/20260801_care_test_docker_rootless_unblock/notification_brief.json
```

### W10 — Strict validator 与 known-bad

必须拒绝：

```text
沿用旧fresh_rerun_case_count=0却写provenance reproduced
只比较ZIP字节，不比较array+geometry
15例中有一例不一致仍绑定0.6691
重新训练或调threshold
MyoPS hybrid调用MoSAIC edema
用M0R/M2替代冻结生产源
hard anatomy clipping删除scar
错误官方label值
错误输入/输出路径
缺C0/T2时静默zero-fill
Docker运行期联网下载
Docker context包含/users symlink
rootless daemon数据放NFS/Lustre
Apptainer冒充Docker
CPU路径未实际运行
three-case host/Docker不等价
容器case失败但exit 0
只build不load/run/save
archive未clean reload
.tar.gz或权重被提交Git
自动上传网盘或发送组织方邮件
submitted/running状态冒充完成
push前发送notifier
```

允许终态：

```text
TEST_DOCKERS_READY_FOR_USER_EMAIL_SUBMISSION
DOCKERS_READY_WITH_GPU_RUNTIME_REQUEST
ROOTLESS_DOCKER_PREREQUISITE_BLOCKED
NNUNET_PROVENANCE_REPLAY_MISMATCH
DOCKER_DEPENDENCY_LOCK_BLOCKED
DOCKER_RUNTIME_OR_EQUIVALENCE_BLOCKED
```

### W11 — Git、push与通知

允许提交：

```text
docker/CARE2026_Myocardium/**
scripts/validation/validate_care_test_docker_rootless_unblock.py
tests/docker_packaging/**
results/20260801_care_test_docker_rootless_unblock/**
prompts/routes/handoffs/CURRENT.md
wiki/README.md
```

禁止提交：

```text
Docker tar/tar.gz
image layers
weights/checkpoints
NIfTI predictions
build context
Docker data-root
large build/runtime logs
credentials/cloud links with tokens
```

终态后：

```bash
exec 9>/users/a/e/aereinh/.care-main-push.lock
flock -x 9

git fetch origin main
git rebase origin/main
./envs/env_CARE/bin/python scripts/validation/validate_care_test_docker_rootless_unblock.py --phase final
git diff --check
git commit -m "package: build CARE myocardium test Dockers"
git push origin HEAD:main
```

禁止force push和额外远端branch。验证local SHA等于remote main SHA。

随后写终态 `notification_brief.json` 并执行：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

若 notifier 生成跟踪receipt，commit/push main并再次验证远端SHA。

## Executor Worker Contract

Executor只负责用户空间rootless Docker、冻结15例replay、生产源码、镜像build/run/equivalence/save和轻量证据。不得训练、上传、发送组织方邮件或改变模型来源。

## Mapper Contract

Mapper必须核对两条实际生产调用图：

```text
MyoPS input -> nnU-Net anatomy/edema + MoSAIC scar -> official label merge -> original geometry output
Cine input -> MoSAIC coarse/fine ensemble -> official export -> original geometry output
```

并通过source intervention证明 MoSAIC edema完全不进入 MyoPS hybrid最终输出。