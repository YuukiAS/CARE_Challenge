---
task_key: 20260801_care_test_docker_packaging
task_kind: scientific_milestone
task_type: care2026_myocardium_test_docker_build_and_submission_readiness
status: AUTHORIZED
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
validation_upload_authorized: false
docker_upload_authorized: false
organizer_email_send_authorized: false
hosted_metric_claim_authorized: false
new_training_authorized: false
new_slurm_job_authorized: false
---

# CARE 2026 Myocardium 测试 Docker 打包与提交就绪 Controller

## Execution Contract

本任务依据 CARE 2026 官方测试阶段说明，构建供用户手动提交的两个独立 Docker image：

```text
MyoPS-OrganAgent-v1.tar.gz
CineMyoPS-OrganAgent-v1.tar.gz
```

官方说明源：

```text
https://www.zmic.org.cn/care_2026/test_submission/
https://www.zmic.org.cn/care_2026/instruction_myocardium/
```

官方要求必须冻结到任务证据：

```text
提交方式: email给 care26challenge@163.com 或 care2026challenge@outlook.com
邮件标题: [CARE-Myocardium Test] Team-Name – Docker Submission
邮件正文: Docker下载链接、运行命令/附加说明、任务名MyoPS或CineMyoPS
输入: /input只读
输出: /output
MyoPS输入: /input/myops/Case*_C0.nii.gz, Case*_LGE.nii.gz, Case*_T2.nii.gz
Cine输入: /input/cinemyops/Case*_Cine.nii.gz
MyoPS输出: /output/myops/Case*_pred.nii.gz
Cine输出: /output/cinemyops/Case*_pred.nii.gz
运行应无人工交互并正常退出
每个task最多3次成功提交；失败运行不计入次数
第一次成功后组织方提供metric feedback
多个task应提交独立Docker image
CPU-only优先；若必须GPU需在邮件说明
截止: 2026-08-03 23:59 PST
```

本任务只构建、测试、导出 Docker 和邮件草稿。不得自动上传网盘，不得向组织方发送邮件，不得上传 validation，不得改训练模型。

## Frozen submission strategy

### MyoPS image

固定使用病种专属来源组合：

```text
anatomy source: historical frozen 5-fold nnU-Net
scar source: repository-final MoSAIC scar recipe
pure-edema source: historical frozen 5-fold nnU-Net
final priority: scar > pure edema > anatomy
```

MyoPS Docker不得使用：

```text
MoSAIC edema
M0R
M1 MyoPS-Net adaptation
M2 I-MMSeg adaptation
M3 CARE-TDS
PRISM/MyoWall/QIF
per-case selector
validation-case threshold tuning
```

内部紧凑标签到官方标签的固定映射：

```text
0 -> 0
1 myocardium -> 200
2 LV -> 500
3 RV -> 600
4 pure edema -> 1220
5 scar -> 2221
```

组合规则：

```text
scar = MoSAIC final scar mask
pure_edema = nnU-Net class4 AND NOT scar
anatomy = nnU-Net classes1/2/3 where pathology absent
```

禁止 hard myocardium clipping 删除 MoSAIC scar。所有来源必须先恢复到输入原始物理几何。

### CineMyoPS image

固定使用 MoSAIC 当前 repo-final Cine recipe：

```text
coarse.pt
fine_v1.pt
fine_v2.pt
z spacings 4/8/16
frozen TTA and final decode from docker/cinemyops/predict.py or exact first-party port
```

不得用旧 single-frame nnU-Net wrapper、M0R、未训练 temporal retrieval或新阈值替代。

## Controller Prompt

### 1. Bootstrap

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

若 main 落后且工作树干净，`git pull --ff-only origin main`。不得 reset/clean/stash 用户改动，不得写 `/overflow/htzhu/CARE`。

### 2. Required reading and visual gate

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
results/leaderboard/care2026_validation_submission_alignment_20260726.md
results/20260801_mosaic_leaderboard_live_snapshot/leaderboard_snapshot.md
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/submission_lineage_evidence.json
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/submission_lineage_ledger.csv
```

视觉读取 Project 中的 SRR-v2/v2.5/v3；本任务不实现SRR，但必须理解病种独立 authority、解剖保护和输出链路边界。

### 3. nnU-Net edema hosted-truth gate

Docker构建前必须先回答：历史 nnU-Net edema 是否真的优于 MoSAIC edema。

固定 leaderboard rows：

```text
historical OrganAgent nnU-Net candidate:
2026-05-21 00:23:31
Dice 0.6691
HD 21.0898
PRE 0.6698
SEN 0.7351

MoSAIC-attributed edema candidate:
2026-06-10 04:46:23
Dice 0.6255
HD 30.2965
PRE 0.7557
SEN 0.5760
```

必须进行以下本地 provenance 闭合：

1. 审计并解包：

```text
results/submissions/care_myocardium_validation/upload_ready/20260519_084057__nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8/CARE-Myocardium-OrganAgent.zip
results/submissions/care_myocardium_validation/upload_ready/20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED/CARE-Myocardium-OrganAgent.zip
```

2. 证明两包的15例 MyoPS prediction逐病例 voxel equality和SHA256关系；后一个包的变化只能来自Cine分支时，明确记录。
3. 读取与这两个包对应的 README、manifest、时间戳和 source checkpoint记录。
4. 从冻结5-fold nnU-Net权重重新生成同一15例 validation MyoPS prediction，要求与历史包逐病例 voxel equality；如历史包不在工作树但存在明确manifest，按manifest路径查找，不得伪造。
5. 绑定 2026-05-21 leaderboard row 与本地时间线。没有原始网站上传receipt时，最高允许结论为：

```text
NNUNET_EDEMA_HOSTED_LINEAGE_HIGH_CONFIDENCE
```

只有找到直接上传receipt或邮件/日志，才允许：

```text
NNUNET_EDEMA_HOSTED_LINEAGE_CONFIRMED
```

若重新生成不匹配历史包，或历史包/manifest不存在：

```text
NNUNET_EDEMA_PROVENANCE_UNRESOLVED
```

此时停止 MyoPS hybrid Docker，不能假定0.6691来自当前权重。

必须生成：

```text
results/20260801_care_test_docker_packaging/nnunet_edema_hosted_truth_audit.json
results/20260801_care_test_docker_packaging/validation_package_voxel_equivalence.csv
results/20260801_care_test_docker_packaging/leaderboard_lineage_timeline.md
```

### 4. Freeze all production assets

MyoPS nnU-Net：冻结5个fold checkpoint、plans、dataset json、trainer class、inference TTA/decode和每个SHA256。

MoSAIC：冻结：

```text
repo commit d334bd1fb2a99dbbc230510590cd8e3ee08cc377
myops/coarse.pt sha256 aae815c3dd50d6776e2af769551e8d6918a5dee4f83f29309a254051e067080c
myops/coarse_edema.pt sha256 b9b596f1f5475ac852bf2c0be38a72c59e538dd3199f1f4989983433506ed9d4
myops/edema.pt sha256 14a6a53f643bdbbac4c8234af2aa86e8a43423b761013f7b7f580965e1ed503c
myops/fine_scar.pt sha256 94c54de3321000eabbc3c3a42a5d838410fb859a1c5b2460e6c2f6d773622ded
cinemyops/coarse.pt sha256 225dedc45271216f5718391af9e0131e996c432df89b61240bef5e52ee451f4c
cinemyops/fine_v1.pt sha256 05b31f649befeef8dd2003a0816310d03ee0385626c5c536db80faac9edacdab
cinemyops/fine_v2.pt sha256 0f102c08c6d3374bd12e9d4d45585aa2017ffbf96192a0cdda1fb8653cc714fa
```

MyoPS Docker只实际调用 MoSAIC scar所需资产；其余MoSAIC edema权重不得进入生产调用图，即使文件因上游repo存在也必须由mapper证明未加载。

### 5. Production source layout

写入：

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

Docker必须：

```text
完全离线运行
无绝对/users或/overflow路径
不下载模型/包
不要求用户输入
默认读取/input并写/output
重复运行前清理本次case临时目录但不得删除/input
每case写临时文件后atomic rename到最终输出
任何case失败时容器非零退出并列出case/error
正常结束返回0
```

依赖版本必须从已验证本地生产环境与实际import闭包生成并锁定。不得随意安装latest。基础镜像使用可CPU运行的 `python:3.12-slim-bookworm`；PyTorch使用与当前生产checkpoint兼容的官方CPU wheel精确版本。若该精确wheel无法获取，停止为 `DOCKER_DEPENDENCY_LOCK_BLOCKED`，不得静默换框架版本。

### 6. CPU-first runtime

默认：

```text
CARE_DEVICE=cpu
OMP_NUM_THREADS=<container detected logical CPUs capped at 16>
MKL_NUM_THREADS=same
```

允许通过环境变量 `CARE_DEVICE=cuda` 使用GPU，但CPU路径必须真实通过，不得只是声明。

对公开validation复制输入至少选3例MyoPS和3例Cine，覆盖最小/中位/最大体积或帧数，进行CPU实测：

```text
wall time
peak RSS
output geometry
label set
exit code
```

外推官方测试总量：MyoPS 65例、CineMyoPS 45例。若CPU预计单task超过24小时，Docker仍需保持CPU可运行，但邮件草稿必须明确请求GPU并给出GPU命令；不得偷偷减少fold、TTA或模型来源。

### 7. Input/output and geometry validator

MyoPS发现逻辑：以 `/input/myops/*_LGE.nii.gz` 为case主表，必须找到同case `_C0`、`_T2`；缺一个即fail closed。

Cine发现逻辑：`/input/cinemyops/*_Cine.nii.gz`。

输出：

```text
/output/myops/<CaseID>_pred.nii.gz
/output/cinemyops/<CaseID>_pred.nii.gz
```

每个输出必须：

```text
shape/spacing/origin/direction/affine与对应reference一致
integer label type
MyoPS labels subset of {0,200,500,600,1220,2221}
Cine labels符合validation phase现有official export语义
无NaN/Inf
文件可重新读取
```

### 8. Non-Docker vs Docker equivalence

用相同冻结输入跑：

```text
host production pipeline
Docker pipeline
```

逐病例要求：

```text
voxel equality = true
geometry equality = true
file-readable = true
```

压缩字节不要求相同，但解压后array和geometry必须相同。

MyoPS额外做source intervention：

```text
MoSAIC scar source关闭 -> final scar labels必须改变
nnU-Net edema source关闭 -> final edema labels必须改变
MoSAIC edema权重/代码on/off -> final output必须完全不变，证明生产未调用MoSAIC edema
```

### 9. Build and export

镜像标签：

```text
care-myops-organagent:v1
care-cinemyops-organagent:v1
```

官方本地运行示例：

```bash
docker run --rm \
  -v <test-root>:/input:ro \
  -v <output-root>:/output \
  care-myops-organagent:v1

docker run --rm \
  -v <test-root>:/input:ro \
  -v <output-root>:/output \
  care-cinemyops-organagent:v1
```

不得需要 `-it`。

导出到Git忽略的runtime目录：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_packaging/dist/MyoPS-OrganAgent-v1.tar.gz
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_packaging/dist/CineMyoPS-OrganAgent-v1.tar.gz
```

正确导出：

```bash
docker save care-myops-organagent:v1 | gzip -1 > MyoPS-OrganAgent-v1.tar.gz
docker save care-cinemyops-organagent:v1 | gzip -1 > CineMyoPS-OrganAgent-v1.tar.gz
```

重新在干净Docker环境执行：

```bash
gzip -dc <file>.tar.gz | docker load
docker inspect <image>
docker run ...
```

记录image ID、RepoDigest、tar.gz SHA256、大小、build log路径和load/run exit code。

### 10. Email draft for user manual submission

生成：

```text
results/20260801_care_test_docker_packaging/submission_email_draft_myops.md
results/20260801_care_test_docker_packaging/submission_email_draft_cinemyops.md
```

标题：

```text
[CARE-Myocardium Test] OrganAgent – Docker Submission
```

正文只留下载链接占位符供用户上传网盘后填写，并包含：

```text
task
filename
SHA256
docker load command
docker run command
CPU/GPU requirement
estimated runtime
output layout
contact note
```

Controller不得发送给组织方。

### 11. Required outputs

```text
results/20260801_care_test_docker_packaging/official_instruction_snapshot.md
results/20260801_care_test_docker_packaging/nnunet_edema_hosted_truth_audit.json
results/20260801_care_test_docker_packaging/validation_package_voxel_equivalence.csv
results/20260801_care_test_docker_packaging/leaderboard_lineage_timeline.md
results/20260801_care_test_docker_packaging/production_asset_manifest.json
results/20260801_care_test_docker_packaging/production_call_graph.md
results/20260801_care_test_docker_packaging/myops_source_intervention.csv
results/20260801_care_test_docker_packaging/docker_build_receipt.json
results/20260801_care_test_docker_packaging/docker_runtime_benchmark.csv
results/20260801_care_test_docker_packaging/docker_prediction_equivalence.csv
results/20260801_care_test_docker_packaging/docker_output_geometry_audit.csv
results/20260801_care_test_docker_packaging/docker_export_manifest.json
results/20260801_care_test_docker_packaging/submission_email_draft_myops.md
results/20260801_care_test_docker_packaging/submission_email_draft_cinemyops.md
results/20260801_care_test_docker_packaging/strict_validator_report.json
results/20260801_care_test_docker_packaging/known_bad_report.json
results/20260801_care_test_docker_packaging/controller_report.md
results/20260801_care_test_docker_packaging/completion_check.md
results/20260801_care_test_docker_packaging/MANIFEST.md
results/20260801_care_test_docker_packaging/notification_brief.json
```

### 12. Decisions

只允许：

```text
TEST_DOCKERS_READY_FOR_USER_EMAIL_SUBMISSION
MYOPS_DOCKER_READY_CINE_BLOCKED
DOCKER_PACKAGING_BLOCKED_PROVENANCE
DOCKER_PACKAGING_BLOCKED_RUNTIME
DOCKER_DEPENDENCY_LOCK_BLOCKED
```

`TEST_DOCKERS_READY...` 要求两个tar.gz均在runtime目录存在、clean load/run通过、预测等价通过、SHA256写入receipt。

### 13. Known-bad

至少覆盖：

```text
assume 0.6691 is nnU-Net without package replay
use MoSAIC edema in MyoPS production
use M0R because CURRENT says scar-only candidate
per-case model selection
validation-driven threshold change
hard myocardium clipping deletes scar
wrong official labels
wrong output directory/name
missing C0/T2 silently zero-fill
container downloads weights at runtime
absolute /users or /overflow dependency
interactive prompt required
container exits zero after case failure
Docker and host outputs differ
CPU path untested
reduce folds/TTA after slow CPU benchmark
tar.gz committed to Git
organizer email sent automatically
notify user before push/terminal completion
```

### 14. Git boundary

提交 source/config/tests和轻量receipts，绝不提交：

```text
Docker tar/tar.gz
Docker image layers
checkpoints
NIfTI predictions
raw data
large logs
credentials or cloud links with tokens
```

终态：

```bash
exec 9>/users/a/e/aereinh/.care-main-push.lock
flock -x 9

git fetch origin main
git rebase origin/main
./envs/env_CARE/bin/python scripts/validation/validate_care_test_docker_packaging.py --phase final
git diff --check
git commit -m "package: prepare CARE myocardium test Dockers"
git push origin HEAD:main
```

禁止force push和task branch push。验证local SHA等于remote main SHA。

随后运行既有 notifier：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

若生成receipt，commit/push main并再次验证SHA。

## Executor Worker Contract

Executor只负责provenance audit、冻结生产代码、Docker build/run/equivalence、导出到runtime和轻量证据。不得训练、上传或发送组织方邮件。

## Mapper Contract

Mapper必须核对：

```text
input discovery -> preprocessing -> model weights -> scar/edema/anatomy sources -> official labels -> output geometry
```

并证明MyoPS生产图中MoSAIC edema完全不在调用路径。