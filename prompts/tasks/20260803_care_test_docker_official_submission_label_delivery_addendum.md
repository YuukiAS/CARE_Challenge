---
task_key: 20260803_care_test_docker_official_submission_label_delivery_addendum
project: CARE
status: AUTHORIZED_BY_USER
branch_policy: main-only
precedence: overrides_conflicting_fields_in_20260803_care_test_docker_official_submission_rehearsal_and_staging_controller
organizer_email_send_authorized: false
challenge_upload_authorized: false
validation_upload_authorized: false
---

# CARE Myocardium Official Submission Rehearsal — Label and Delivery Addendum

本文件必须与以下基础任务一起执行，且本文件覆盖冲突字段：

`prompts/tasks/20260803_care_test_docker_official_submission_rehearsal_and_staging_controller.md`

当前最终服务器交付目录：

`/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist`

固定归档：

- `MyoPS-OrganAgent.tar.gz`
  - size: `4741640359`
  - SHA256: `638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b`
- `CineMyoPS-OrganAgent.tar.gz`
  - size: `672040570`
  - SHA256: `c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136`

## 1. 不得把“某个病理标签为空”误判为格式错误

官方标签语义为：

- `2221`: scar
- `1220`: edema
- `500`: left ventricle
- `200`: myocardium
- `600`: right ventricle

MyoPS 允许集合：`{0,200,500,600,1220,2221}`。
CineMyoPS 允许集合：`{0,200,500,2221}`。

一个病例的 scar 或 edema 预测体积为零，可能代表模型漏检，但 NIfTI 仍可被官方评价；它不是文件格式错误。不得为了“补齐标签”伪造体素、改阈值或修改模型。

正式彩排必须同时做以下两类检查：

### 文件与接口硬门

- 全部预期病例均有且只有一个 `<CaseID>_pred.nii.gz`。
- 无缺例、重复、未知病例或错误子目录。
- SimpleITK 和 nibabel 均可读取。
- 3D 整数标签图；无 NaN/Inf。
- label set 只能是对应任务允许集合的子集。
- geometry 与参考空间一致。
- `/input` hash 前后完全一致。
- 不需要额外 command、GPU、网络或交互输入。

### 每病例标签体积审计

写 `official_label_volume_casewise.csv`，至少包括：

`task,case_id,label_0_voxels,label_200_voxels,label_500_voxels,label_600_voxels,label_1220_voxels,label_2221_voxels,total_nonbackground_voxels,all_background,required_anatomy_present,pathology_zero_flags,status`

硬门：

- 任何输出 `all_background=true` 必须失败。
- MyoPS 每例必须出现 `200/500/600`；缺任一 anatomy label 必须失败并报告 case ID。
- CineMyoPS 每例必须出现 `200/500`；缺任一 anatomy label 必须失败并报告 case ID。
- scar/edema 可以逐病例为零，但必须报告对应 case ID；不得静默忽略。
- MyoPS 的 `1220` 或 `2221` 若在全部公开彩排病例中均为零，整体失败。
- CineMyoPS 的 `2221` 若在全部公开彩排病例中均为零，整体失败。

写 `official_label_volume_summary.json`，汇总每个标签的 positive-case count、total voxels、min/median/max volume 和 zero-case list。

## 2. 全量公开病例彩排

只跑 3-case smoke 不足以声称可提交。优先使用全部公开 validation：

- MyoPS: 15 个完整 LGE/T2/C0 病例。
- CineMyoPS: 15 个 Cine 病例。

必须采用官方根目录：

```text
/input/myops/**
/input/cinemyops/**
```

输出必须是：

```text
/output/myops/<CaseID>_pred.nii.gz
/output/cinemyops/<CaseID>_pred.nii.gz
```

不得分别把 `/input/myops` 或 `/input/cinemyops` 直接挂载成 `/input` 来替代正式彩排。

## 3. 与合作者示例 Docker 的比较边界

合作者 MyoPS archive 只用于接口比较：输出目录、文件名、case count、NIfTI 可读性、dtype、维度、geometry、允许标签、退出码、无需额外 command。

不得要求两个模型逐体素一致，不得根据 reference 输出修改最终 nnU-Net。

比较结论必须明确区分：

- `INTERFACE_MATCH`
- `INTERFACE_MISMATCH`
- `MODEL_OUTPUT_DIFFERENCE_NOT_AN_INTERFACE_FAILURE`

## 4. Google Drive 上传是独立、非阻塞阶段

当前 workstation/server 证据明确 `netdisk_upload=false`，因此在 rclone 成功并验证公开链接前，不得声称 Docker 已上传。

只有 local Docker、官方格式和全量公开病例彩排全部 PASS 后，才允许尝试 rclone。若缺少 remote 或 OAuth：

- 生成 `google_drive_upload_pending.md`。
- 给出用户在可见终端运行 `rclone config` 的精确步骤。
- 保存续传命令。
- 不阻塞邮件草稿、提交清单和服务器轻量回传。
- `email_ready_to_send=false`，直到两个公开链接都通过未登录访问检查。

## 5. 邮件草稿要求

必须生成：

`results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_email_draft.md`

语气自然、简短，不介绍失败历史、模型研发过程或 leaderboard，不使用宣传句，不写“AI-generated”。

固定主题：

`[CARE-Myocardium Test] OrganAgent – Docker Submission`

正文只包含：两个任务、已验证下载链接、文件名、image tag、SHA256、准确的 load/run 命令、输出目录、CPU-only/ENTRYPOINT 说明和简短结尾。

没有验证链接时保留 `[pending upload]`，并明确 `email_ready_to_send=false`。不得发送邮件。

## 6. 服务器最终确认

工位完成后将轻量 packet 回传服务器。服务器只做：

- `stat` 和 `sha256sum -c` 再确认 final dist 两个 archive。
- 核对工位 full-public rehearsal、label-volume audit、clean-load、Drive receipt 和 draft。
- 将轻量结果 commit/push；不得在服务器运行 Docker。

最终提交就绪要求：

```text
local_docker_ready=true
official_format_ready=true
public_rehearsal_ready=true
all_expected_cases_written=true
required_anatomy_labels_present=true
pathology_label_volume_audit_complete=true
collaborator_interface_checked=true
google_drive_upload_ready=true
email_draft_ready=true
email_ready_to_send=true
email_sent=false
```

若唯一未完成项是 Google Drive OAuth/link，则状态应为 `DOCKER_READY_UPLOAD_AUTH_PENDING`，不得把 Docker 验证降级为失败，也不得建议用户直接发送含占位链接的邮件。
