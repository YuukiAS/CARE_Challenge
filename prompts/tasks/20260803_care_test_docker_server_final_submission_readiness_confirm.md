---
task_key: 20260803_care_test_docker_server_final_submission_readiness_confirm
project: CARE
status: AUTHORIZED_BY_USER
branch_policy: main-only
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
organizer_email_send_authorized: false
challenge_upload_authorized: false
validation_upload_authorized: false
server_docker_run_authorized: false
---

# CARE Myocardium Server Final Submission Readiness Confirmation

本任务只在工位完成以下任务后执行：

`20260803_care_test_docker_official_submission_rehearsal_and_staging`

必须同时读取：

- `prompts/tasks/20260803_care_test_docker_official_submission_rehearsal_and_staging_controller.md`
- `prompts/tasks/20260803_care_test_docker_official_submission_label_delivery_addendum.md`
- 工位回传的 `OFFICIAL_SUBMISSION_REHEARSAL_PACKET.tar.gz`

服务器不得运行 Docker，不得上传文件，不得发送邮件。

## 固定 final dist

`/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist`

必须存在：

- `MyoPS-OrganAgent.tar.gz`
  - size `4741640359`
  - SHA256 `638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b`
- `CineMyoPS-OrganAgent.tar.gz`
  - size `672040570`
  - SHA256 `c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136`
- `SHA256SUMS`
- `receipts/WORKSTATION_VALIDATION_PACKET.tar.gz`

执行 `stat`、`sha256sum -c SHA256SUMS`，并记录结果。

## 工位 rehearsal packet 硬门

从工位回传目录定位最新：

`OFFICIAL_SUBMISSION_REHEARSAL_PACKET.tar.gz`

解包到新的服务器 runtime，只读审计。必须确认：

- 官方页面快照和 machine-readable contract 已保存。
- 使用官方 `/input` 根树完成 MyoPS 和 CineMyoPS 全量公开病例彩排。
- MyoPS 预期病例全部写出且每例一个输出。
- CineMyoPS 预期病例全部写出且每例一个输出。
- 输出目录、文件名、NIfTI 可读性、整数 dtype、geometry、允许标签全部 PASS。
- `official_label_volume_casewise.csv` 和 `official_label_volume_summary.json` 存在。
- 没有 all-background 输出。
- MyoPS 每例 `200/500/600` 均存在。
- CineMyoPS 每例 `200/500` 均存在。
- scar/edema 零体积病例已列出而非静默忽略。
- 合作者 MyoPS reference 只做接口对照，未覆盖最终 tag。
- 输入 hash 前后不变。
- clean archive load 和官方命令运行 PASS。
- strict validator PASS。

## Drive 与邮件状态

读取：

- `google_drive_upload_receipt.json`
- `google_drive_links.json`
- `submission_email_draft.md`
- `submission_email_fields.json`
- `submission_manual_send_checklist.md`
- `submission_readiness.json`

只有以下全部成立才可写 `READY_FOR_HUMAN_EMAIL_SEND`：

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

两个 Drive 链接必须通过未登录访问检查，且分别对应正确 archive、size 和 SHA。

若 Drive OAuth/remote/link 未完成，写 `DOCKER_READY_UPLOAD_AUTH_PENDING`，不得把 Docker 结论降级为失败，也不得建议发送含占位链接的邮件。

## 结果与 Git

结果目录：

`results/20260803_care_test_docker_server_final_submission_readiness_confirm`

至少生成：

- `server_final_dist_receipt.json`
- `official_rehearsal_packet_audit.json`
- `drive_link_audit.json`
- `email_draft_audit.md`
- `final_submission_readiness.json`
- `controller_report.md`
- `completion_check.md`
- `strict_validator_report.json`
- `notification_brief.json`

更新 `prompts/routes/handoffs/CURRENT.md` 和 `wiki/README.md`，但不得覆盖并行 CARE-ASE 最新状态；只在顶部或清晰独立段落记录 Docker submission readiness。

只提交轻量文件。禁止提交 Docker archive、NIfTI、checkpoint、Drive token、rclone config 或 secret。

提交信息：

`package: confirm final CARE Docker submission readiness`

推送 `origin/main`，验证 HEAD 与 origin/main 相同，然后调用既有 notifier。不得发送组织方邮件。
