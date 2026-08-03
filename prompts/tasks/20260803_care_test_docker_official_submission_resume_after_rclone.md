---
task_key: 20260803_care_test_docker_official_submission_resume_after_rclone
project: CARE
status: AUTHORIZED_BY_USER
branch_policy: main-only
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
architecture_impact: none
wiki_update_required: true
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
organizer_email_send_authorized: false
challenge_upload_authorized: false
validation_upload_authorized: false
precedence: this_resume_overrides_conflicting_status_and_case_count_fields_in_prior_official_rehearsal_tasks
---

# CARE Myocardium Official Submission Resume After rclone Authentication

本任务不是重新构建 Docker，也不是重新选择模型。它从已经完成的工位构建和 3+3 sentinel 彩排继续，只补齐此前缺失的两件事：

1. 使用服务器现有全部公开 validation 输入完成 MyoPS 15 例与 CineMyoPS 15 例的官方 `/input` 根目录黑盒彩排和逐病例标签体积审计；
2. 使用已经配置好的持久 `gdrive:` rclone remote 上传两个最终 archive，验证远端完整性和未登录公开链接，并据此更新自然英文邮件草稿。

本任务必须同时读取，后者覆盖前者冲突字段：

```text
prompts/tasks/20260803_care_test_docker_official_submission_rehearsal_and_staging_controller.md
prompts/tasks/20260803_care_test_docker_official_submission_label_delivery_addendum.md
prompts/tasks/20260803_care_test_docker_official_submission_resume_after_rclone.md
```

此前提交 `d86cd4619370b1ea086ad0ba643a497cbb890bcc` 只完成 3+3 available sentinel rehearsal。它证明镜像接口可运行，但不得再保留以下错误或过宽状态：

```text
public_rehearsal_ready=true
all_expected_cases_written=true
```

除非本任务真实完成 15+15 全量公开病例并通过下面所有硬门。

## 一、固定环境与最终资产

工位根目录：

```text
/home/yuukias/code/CARE
```

工位最终归档：

```text
/home/yuukias/code/CARE/dist/20260803_care_test_docker_final/MyoPS-OrganAgent.tar.gz
/home/yuukias/code/CARE/dist/20260803_care_test_docker_final/CineMyoPS-OrganAgent.tar.gz
/home/yuukias/code/CARE/dist/20260803_care_test_docker_final/SHA256SUMS
```

固定校验：

```text
MyoPS-OrganAgent.tar.gz
size 4741640359
SHA256 638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b

CineMyoPS-OrganAgent.tar.gz
size 672040570
SHA256 c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136
```

固定 image tags：

```text
care-myocardium-myops:organagent
care-myocardium-cinemyops:organagent
```

服务器最终目录：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist
```

服务器公开 validation 输入源：

```text
/users/a/e/aereinh/CARE/data/CARE_Challenge/MyoPS_val/AnonymousCenter
/users/a/e/aereinh/CARE/data/CARE_Challenge/CineMyoPS_val/AnonymousCenter
```

rclone 已由用户在可见终端配置：

```text
remote: gdrive:
config: /home/yuukias/.config/rclone/rclone.conf
```

不得读取、打印、复制、提交或回传 `rclone.conf`、refresh token 或 OAuth secret。

## 二、同步与前置核验

执行：

```bash
cd /home/yuukias/code/CARE
git fetch origin main --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -20
git diff --check
```

若工作树干净且落后，执行：

```bash
git pull --ff-only origin main
```

不得 reset、clean 或覆盖已有 Docker 结果。

验证最终归档：

```bash
cd /home/yuukias/code/CARE/dist/20260803_care_test_docker_final
stat -c '%n %s' MyoPS-OrganAgent.tar.gz CineMyoPS-OrganAgent.tar.gz
sha256sum -c SHA256SUMS
```

验证 Docker 与 rclone：

```bash
docker version
docker info
docker image inspect care-myocardium-myops:organagent >/dev/null
docker image inspect care-myocardium-cinemyops:organagent >/dev/null
/home/yuukias/.local/bin/rclone version
/home/yuukias/.local/bin/rclone listremotes
/home/yuukias/.local/bin/rclone about gdrive:
```

硬要求：

- Docker 普通用户无 sudo 可用；
- `gdrive:` 恰好存在并可访问；
- 不得因为 repo 同时有 CARE-ASE 新提交而修改 Docker 模型合同。

## 三、自动识别服务器并下载全部公开输入

从 `~/.ssh/config` 中自动探测唯一能访问以下路径的 alias：

```text
/users/a/e/aereinh/CARE/data/CARE_Challenge/MyoPS_val/AnonymousCenter
/users/a/e/aereinh/CARE/data/CARE_Challenge/CineMyoPS_val/AnonymousCenter
```

记为 `CARE_SERVER`。不得猜 alias。

本地 runtime：

```text
/home/yuukias/code/CARE/.local_runtime/20260803_care_test_docker_official_submission_resume_after_rclone
```

创建官方输入根树：

```text
<runtime>/rehearsal/input/myops
<runtime>/rehearsal/input/cinemyops
<runtime>/rehearsal/output
```

使用 rsync 下载全部公开输入，不下载 GT：

- MyoPS 只复制 `*_LGE.nii.gz`、`*_T2.nii.gz`、`*_C0.nii.gz`；
- CineMyoPS 只复制 `*_Cine.nii.gz`；
- 排除 label、GT、prediction、mask、seg 文件。

必须确认：

```text
MyoPS complete case count = 15
CineMyoPS case count = 15
MyoPS 每例恰好 LGE/T2/C0 三个文件
Cine 每例恰好一个 Cine 文件
```

若服务器真实 case count 不是 15，记录真实文件树与原因并 fail closed，不得继续宣称 full-public rehearsal。

写：

```text
public_full_rehearsal_input_manifest.json
public_full_rehearsal_input_casewise.csv
```

在 Docker 运行前计算所有输入 SHA256；运行后再次计算并要求完全一致。

## 四、从最终 archive clean load

不得只复用当前内存 image。

仅删除本任务两个 tag，不得 prune：

```bash
docker image rm care-myocardium-myops:organagent || true
docker image rm care-myocardium-cinemyops:organagent || true
```

从最终归档重新加载：

```bash
docker load --input /home/yuukias/code/CARE/dist/20260803_care_test_docker_final/MyoPS-OrganAgent.tar.gz
docker load --input /home/yuukias/code/CARE/dist/20260803_care_test_docker_final/CineMyoPS-OrganAgent.tar.gz
```

确认：

- 两个 tag 精确；
- `linux/amd64`；
- ENTRYPOINT 非空；
- 无额外 command；
- MyoPS image 内五个 `checkpoint_best.pth` 均存在；
- Cine image ID/config 与此前冻结 receipt 一致。

## 五、15+15 官方根目录黑盒彩排

只使用官方根目录 mount：

```bash
docker run --rm \
  --network none \
  -v '<runtime>/rehearsal/input:/input:ro' \
  -v '<runtime>/rehearsal/output:/output' \
  care-myocardium-myops:organagent

docker run --rm \
  --network none \
  -v '<runtime>/rehearsal/input:/input:ro' \
  -v '<runtime>/rehearsal/output:/output' \
  care-myocardium-cinemyops:organagent
```

不得传额外 command、`-it`、GPU、网络或额外模型 mount。

MyoPS 必须：

- exit code 0；
- 发现并处理 15 个完整病例；
- `/output/myops/` 中恰好 15 个 `<CaseID>_pred.nii.gz`；
- 无缺例、重复、未知病例；
- 不写 `/output` 根目录或 `/output/cinemyops`；
- 每个文件可由 SimpleITK 与 nibabel 读取；
- 3D 整数标签图；
- label set subset `{0,200,500,600,1220,2221}`；
- shape、spacing、origin、direction 与对应 LGE 参考空间一致；
- 无 NaN/Inf。

CineMyoPS 必须：

- exit code 0；
- 发现并处理 15 个病例；
- `/output/cinemyops/` 中恰好 15 个 `<CaseID>_pred.nii.gz`；
- 无缺例、重复、未知病例；
- 不写 `/output` 根目录或 `/output/myops`；
- SimpleITK 与 nibabel 可读；
- 数组值必须为整数标签，即使 NIfTI storage dtype 是 float32；若值不是整数则失败；
- label set subset `{0,200,500,2221}`；
- 输出 3D geometry 与对应 Cine 空间合同一致；
- 无 NaN/Inf。

运行后输入 SHA256 必须与运行前完全一致。

写：

```text
official_full_rehearsal_casewise.csv
official_full_rehearsal_summary.json
official_full_output_tree.txt
input_readonly_integrity_full_receipt.json
```

## 六、逐病例标签体积硬审计

生成：

```text
official_label_volume_casewise.csv
official_label_volume_summary.json
```

每行至少包括：

```text
task,case_id,label_0_voxels,label_200_voxels,label_500_voxels,label_600_voxels,label_1220_voxels,label_2221_voxels,total_nonbackground_voxels,all_background,required_anatomy_present,pathology_zero_flags,status
```

硬门：

- 任何 `all_background=true` 失败；
- MyoPS 每例必须出现 `200/500/600`；
- CineMyoPS 每例必须出现 `200/500`；
- scar 或 edema 在某一病例为零可以接受，但必须列入 zero-case list；
- MyoPS 的 `1220` 和 `2221` 各自在全部 15 例中至少一个病例为正；
- CineMyoPS 的 `2221` 在全部 15 例中至少一个病例为正；
- 不得伪造标签、补体素、改阈值或修改模型。

旧 3+3 sentinel 结果只作为历史接口证据，不得替代本节。

## 七、合作者 MyoPS 接口对照

此前 3-case 合作者 reference interface 已 PASS，且最终 MyoPS tag 已恢复。若 reference archive、image ID、最终 image ID 和运行接口均未变化，可以复用已有 receipt，不必重新下载约 985 MB 或重跑。

必须明确结论：

```text
INTERFACE_MATCH
MODEL_OUTPUT_DIFFERENCE_NOT_AN_INTERFACE_FAILURE
```

不得根据 reference 输出修改最终模型。

## 八、Google Drive 上传

仅在第五、六节全部 PASS 后执行。

目标目录：

```text
gdrive:/CARE2026_Myocardium_Test_OrganAgent_20260803/
```

上传三个文件：

```text
MyoPS-OrganAgent.tar.gz
CineMyoPS-OrganAgent.tar.gz
SHA256SUMS
```

使用可续传、可重试的 rclone 命令，至少设置：

```text
--progress
--transfers 1
--checkers 4
--retries 5
--low-level-retries 10
```

不得使用 `rclone sync` 删除 remote 中其他内容；使用 `copy` 或 `copyto`。

上传完成后必须：

1. `rclone lsjson` 核对文件名和 size；
2. `rclone check` 或逐文件 provider hash 校验，不能只看上传 exit code；
3. 生成两个 archive 的公开链接；
4. 用不携带 rclone/OAuth 凭据的 `curl -I -L` 或等价方式检查未登录访问不是 401/403；
5. 核对链接分别对应正确文件名、size 和 SHA receipt；
6. 不把 `SHA256SUMS` 链接误写成 archive 链接。

写：

```text
rclone_environment_receipt.json
google_drive_upload_receipt.json
google_drive_links.json
google_drive_public_access_receipt.json
```

不得在 Git、日志、packet 或最终回答中暴露 token 或 `rclone.conf`。

## 九、更新邮件草稿

更新而非另写冲突草稿：

```text
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_email_draft.md
```

替换两个 `[pending upload]` 为真实、经过未登录验证的链接。

邮件必须自然、简短，只写：

- 两个任务；
- 两个验证链接；
- archive 文件名；
- image tag；
- SHA256；
- 实际验证过的 load/run 命令；
- 输出目录；
- CPU-only、ENTRYPOINT、无需额外 command/network/interactive input；
- 简短结尾。

不得写内部实验历史、失败过程、leaderboard、模型宣传或 AI 生成措辞。

只有 Drive 与全部本地门 PASS 后设置：

```text
email_draft_ready=true
email_ready_to_send=true
email_sent=false
```

仍然不得发送邮件。

同步更新：

```text
submission_email_fields.json
submission_manual_send_checklist.md
submission_readiness.json
```

`submission_readiness.json` 必须真实包含：

```text
local_docker_ready=true
official_format_ready=true
public_rehearsal_ready=true
public_rehearsal_case_count_myops=15
public_rehearsal_case_count_cinemyops=15
all_expected_cases_written=true
required_anatomy_labels_present=true
pathology_label_volume_audit_complete=true
collaborator_interface_checked=true
google_drive_upload_ready=true
email_draft_ready=true
email_ready_to_send=true
email_sent=false
```

## 十、严格 validator、回传和 Git

更新或新增 validator，使其拒绝：

- 只有 3+3 却写 full public rehearsal；
- 15 例输入但输出少于 15；
- anatomy label 缺失而 PASS；
- all-background 输出；
- Cine float dtype 且存在非整数值；
- Drive 文件 size/hash 未核验；
- 公开链接未经未登录访问检查；
- 草稿仍有 `[pending upload]` 却标记 ready；
- secret/rclone config 被 staged；
- 邮件被发送。

生成新的轻量 packet：

```text
OFFICIAL_SUBMISSION_REHEARSAL_PACKET_FULL.tar.gz
```

回传服务器：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_official_submission_rehearsal_and_staging/
```

packet 不得含 Docker archive、NIfTI、checkpoint、rclone config、token 或大日志。

更新 `CURRENT.md`/wiki 时不得覆盖并行 CARE-ASE 最新状态；增加独立 Docker readiness 段落即可。

只提交轻量文件。禁止 staged：

```text
*.pt *.pth *.nii *.nii.gz *.tar *.tar.gz
.local_runtime/ dist/ rclone.conf
```

提交信息：

```text
package: complete full Docker rehearsal and Drive staging
```

推送 `origin/main`，验证 HEAD == origin/main，并调用既有服务器 notifier。

最终回答必须明确：

- 15+15 是否真实完成；
- 每个任务输出是否完整；
- anatomy/pathology label volume audit；
- Drive 上传文件、size、hash 和公开链接验证；
- 邮件草稿路径与 ready 状态；
- 未发送邮件、未上传 challenge/validation。
