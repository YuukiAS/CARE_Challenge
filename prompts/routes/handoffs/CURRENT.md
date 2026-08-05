# CARE 当前开发状态

## 2026-08-05 最新机器真值：Attempt 3 MyoPS 单层输入 runtime-only corrected archive 已完成

这次修复的是组织方实际测试失败的 Attempt 3 MyoPS Docker archive 在合法 depth=1 输入上触发 nnU-Net 重采样 0 维并导致整批失败的问题。已先唯一绑定原 Attempt 3 archive `921a0115428b8d597c67d57d45862de1371bf6d3097b5dc8c9b27e7407589ef3`，并在原镜像 `sha256:a291ab1e51a52c0739970a45db567b4e4a8cb103e06946626509800fa6f258bf` 上真实复现崩溃；修正版只在 nnU-Net `compute_new_shape` 原有 rounding 后增加 `np.maximum(new_shape, 1)`，没有更换或修改 checkpoint、`selection.json`、`predict.py`、entrypoint、requirements、fold、TTA、threshold、label map、overlay 逻辑或依赖。

```text
local_result_root:
results/20260805_care_myops_attempt3_single_slice_hotfix

server_audit_root:
results/20260805_care_myops_attempt3_single_slice_hotfix_server_audit

server_terminal_token:
ATTEMPT3_CORRECTED_MYOPS_RUNTIME_ONLY_HOTFIX_READY_FOR_ORGANIZER_REEVALUATION

corrected_archive:
dist/20260805_care_myops_attempt3_single_slice_hotfix/MyoPS-OrganAgent-Attempt3-corrected.tar.gz

corrected_archive_size:
5103476746

corrected_archive_sha256:
52c39ab06abc0d1e4411def14bea445e27099ca9c13164dab67eb0e063c93709

drive_link:
https://drive.google.com/open?id=1Q7CExNmP5oPJ3z3PbEdiM4Kilx5onz67

organizer_email_sent:
false
```

Verified evidence:

- Attempt 3 原镜像 depth=1 zero-dimension crash 已复现；
- five nnU-Net checkpoint、two CARE-ASE step500 checkpoint、`selection.json`、推理源码、entrypoint、requirements、pip freeze、ENTRYPOINT/Cmd/Env 和 rootfs prefix invariance PASS；
- Attempt 3 原镜像和修正版各一次 15-case normal inference 15/15 bitwise/geometrically/canonical-SHA exact；
- depth1/depth2 synthetic matrix、15 normal + synthetic mixed batch、synthetic determinism、clean save/load 后完整 synthetic + 3 normal sentinel 全部 PASS；
- corrected archive 和 `SHA256SUMS` 只上传到新的 Google Drive 文件夹，公开链接未登录 HTTP 检查通过；
- `/users/a/e/aereinh/CARE` server 只做静态审计，Docker 没有在服务器运行；
- CineMyoPS 不重建，继续复用原 Cine archive 是有意边界；
- 没有发送组织方邮件，没有上传 challenge 或 validation predictions。

## 2026-08-03 最新机器真值：CARE-ASE R2 v9 等待外部训练前审阅

CARE-ASE R2 v9 已完成 last-hotfix source closure、executor plan validation、pytest、G1，以及 fold1/fold4 short-smoke GPU diagnostic probes。当前只准备交给外部 GPT 做训练许可审阅，不表示正式训练获准。v8 implementation `648bb4d79da255438469aa9acfa939616aebf251` 和 v8 review packet `8d01cd4c4a5caa3ab1eb44f365bd830a69a34664` 已被 v9 取代；v8 及更早训练/probe credit 均不得作为正式训练。formal training 未启动，fold1/fold4 outer access 均为 0。下一步只能是外部 GPT 返回 `PRETRAINING_EXTERNAL_REVIEW_PASS` 或 revise。

```text
state_id: care_ase_r2_v9_pending_external_pretraining_review
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
implementation_source_commit_sha: 2069527d4d2f6357a0fddfa9df0c49223691a96f
review_packet_commit_sha: reported_after_push
formal_training_authorized: false
formal_training_started: false
outer_access_fold1: 0
outer_access_fold4: 0
diagnostic_optimizer_step_reservations_total: 4
next_action: EXTERNAL_GPT_PRETRAINING_REVIEW
```

关键证据：

```text
results/20260803_care_ase_r2_last_hotfix_v9/pretraining_external_review_request.json
results/20260803_care_ase_r2_last_hotfix_v9/controller_report.md
results/20260803_care_ase_r2_last_hotfix_v9/completion_check.md
results/20260803_care_ase_r2_last_hotfix_v9/MANIFEST.md
```

## 2026-08-03 最新机器真值：CARE-ASE R2 v8 等待外部最终训练前审阅

CARE-ASE R2 v8 已完成最终训练前代码阻断闭合，当前只准备交给外部 GPT 做训练许可审阅，不表示正式训练获准。v7 implementation `0b20e32d077227fbeb6611a3ee0cdf4231aee19d` 和 v7 review packet `7f4bb4d48e92273e2aad0a5d75ae6e4f3a62f1e7` 的 ready claim 已被 v8 取代；v7 probes 均为 zero-credit diagnostics。formal training 未启动，fold1/fold4 outer access 均为 0。下一步只能是外部 GPT 返回 `PRETRAINING_EXTERNAL_REVIEW_PASS` 或 revise。

```text
state_id: care_ase_r2_v8_pending_external_pretraining_review
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
implementation_source_commit_sha: 648bb4d79da255438469aa9acfa939616aebf251
review_packet_commit_sha: reported_after_push
formal_training_authorized: false
formal_training_started: false
outer_access_fold1: 0
outer_access_fold4: 0
diagnostic_optimizer_step_reservations_total: 20
next_action: EXTERNAL_GPT_PRETRAINING_REVIEW
```

关键证据：

```text
results/20260803_care_ase_r2_final_pretraining_closure_v8/pretraining_external_review_request.json
results/20260803_care_ase_r2_final_pretraining_closure_v8/controller_report.md
results/20260803_care_ase_r2_final_pretraining_closure_v8/completion_check.md
results/20260803_care_ase_r2_final_pretraining_closure_v8/MANIFEST.md
```

## 2026-08-03 最新机器真值：服务器最终确认通过，可由人工发送 Docker 提交邮件

服务器端已经对最终 MyoPS 与 CineMyoPS Docker 提交资源做完只读确认：final dist 中两个 archive 的 size/SHA 与冻结值一致，最新 FULL 工位 packet 已解包审计，MyoPS 15 例与 CineMyoPS 15 例官方 `/input` 根目录黑盒彩排、标签体积审计、输入只读完整性、合作者 MyoPS reference 接口边界、Google Drive 公链和英文邮件草稿全部通过。当前状态只授权用户人工发送已审计邮件；服务器没有运行 Docker，没有上传 challenge 或 validation predictions，没有发送组织方邮件，也没有读取或提交 rclone secret。

```text
state_id: care_test_docker_server_final_submission_readiness_confirm_20260803
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_TEST_DOCKER_READY_FOR_HUMAN_EMAIL_SEND
result_root: results/20260803_care_test_docker_server_final_submission_readiness_confirm
server_final_dist: /users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist
server_full_rehearsal_packet: /users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_official_submission_rehearsal_and_staging/OFFICIAL_SUBMISSION_REHEARSAL_PACKET_FULL.tar.gz
controller_verification_decision: VERIFIED_COMPLETE
final_submission_status: READY_FOR_HUMAN_EMAIL_SEND
myops_archive_size: 4741640359
myops_archive_sha256: 638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b
cinemyops_archive_size: 672040570
cinemyops_archive_sha256: c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136
myops_official_output_count: 15
cinemyops_official_output_count: 15
label_volume_audit: PASS
google_drive_public_links_verified: true
email_draft_ready: true
email_ready_to_send: true
server_docker_run_performed: false
server_upload_performed: false
organizer_email_sent: false
challenge_upload_performed: false
validation_predictions_uploaded: false
strict_validator: PASS
```

关键证据：

```text
results/20260803_care_test_docker_server_final_submission_readiness_confirm/server_final_dist_receipt.json
results/20260803_care_test_docker_server_final_submission_readiness_confirm/official_rehearsal_packet_audit.json
results/20260803_care_test_docker_server_final_submission_readiness_confirm/label_volume_audit.json
results/20260803_care_test_docker_server_final_submission_readiness_confirm/drive_link_audit.json
results/20260803_care_test_docker_server_final_submission_readiness_confirm/final_submission_readiness.json
results/20260803_care_test_docker_server_final_submission_readiness_confirm/strict_validator_report.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_email_draft.md
```

## 2026-08-03 最新机器真值：最终 Docker archives 已完成 15+15 官方 public validation 黑盒彩排与 Drive staging

最终 MyoPS 与 CineMyoPS Docker archives 已从 clean archive 重新 load，并按 CARE 官方 `/input` 根目录结构完成 MyoPS 15 例与 CineMyoPS 15 例 public validation 黑盒彩排。两个镜像均使用无额外 command、无交互、`--network none` 的官方接口运行；两项任务都恰好写出 15 个 `<CaseID>_pred.nii.gz`，无缺例、重复或未知病例。逐病例 NIfTI、标签集合、geometry、输入只读完整性和 anatomy/pathology label volume audit 全部通过。Google Drive 已只上传两个最终 Docker archive 和 `SHA256SUMS`，远端 size/hash 与本地一致，公开链接已用未登录 HTTP 检查通过。英文邮件草稿已填入真实链接并处于人工可发送状态；未发送邮件，未上传 challenge 或 validation predictions，未读取/提交/回传 rclone secrets。

```text
state_id: care_test_docker_official_submission_resume_after_rclone_20260803
active_development_branch: main
active_worktree: /home/yuukias/code/CARE
single_active_scientific_line: CARE_TEST_DOCKER_FULL_OFFICIAL_REHEARSAL_AND_DRIVE_STAGING_READY
result_root: results/20260803_care_test_docker_official_submission_resume_after_rclone
local_final_dist: /home/yuukias/code/CARE/dist/20260803_care_test_docker_final
server_full_rehearsal_packet: /users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_official_submission_rehearsal_and_staging/OFFICIAL_SUBMISSION_REHEARSAL_PACKET_FULL.tar.gz
controller_verification_decision: VERIFIED_COMPLETE
clean_archive_load: PASS
myops_public_validation_input_cases: 15
cinemyops_public_validation_input_cases: 15
myops_official_output_count: 15
cinemyops_official_output_count: 15
myops_official_runtime_seconds: 1864.8245782852173
cinemyops_official_runtime_seconds: 1576.9830911159515
output_completeness: PASS
input_readonly_integrity: PASS
label_volume_audit: PASS
collaborator_myops_reference_interface: PASS_REUSED_RECEIPT
google_drive_upload_ready: true
google_drive_remote_size_hash_verified: true
google_drive_public_links_verified: true
email_draft_ready: true
email_ready_to_send: true
organizer_email_sent: false
challenge_upload_performed: false
validation_predictions_uploaded: false
rclone_secret_read_or_returned: false
strict_validator: PASS
```

关键证据：

```text
results/20260803_care_test_docker_official_submission_resume_after_rclone/public_full_rehearsal_input_manifest.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/official_full_rehearsal_summary.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/official_label_volume_summary.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/google_drive_upload_receipt.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/google_drive_public_access_receipt.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/full_rehearsal_packet_receipt.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/remote_full_rehearsal_packet_receipt.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/strict_validator_report.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_email_draft.md
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_readiness.json
```

## 2026-08-03 最新机器真值：最终 Docker archives 已完成官方输入格式黑盒彩排

最终 MyoPS 与 CineMyoPS Docker archives 已从本地 clean archive 重新 load，并按 CARE 官方 `/input` 根目录结构完成黑盒彩排。当前工位只有 3 个 MyoPS sentinel 与 3 个 Cine sentinel 可用，因此本轮如实记录为 available-public-sentinel rehearsal，不声称 15/15 全量 public rehearsal。两个镜像均使用无额外 command、无交互、`--network none` 的官方接口运行；输出目录、命名、NIfTI 可读性、标签集合和 geometry 检查通过。合作者 MyoPS reference archive 已下载校验并隔离为 reference tag，接口对照通过，最终 MyoPS tag 已恢复。Google Drive 上传未执行，因为本机 rclone 尚无 Google Drive remote，需要人工 OAuth；英文邮件草稿已生成但未发送、未标记 ready-to-send。未上传 challenge、validation predictions 或网盘文件。

```text
state_id: care_test_docker_official_submission_rehearsal_and_staging_20260803
active_development_branch: main
active_worktree: /home/yuukias/code/CARE
single_active_scientific_line: CARE_TEST_DOCKER_OFFICIAL_FORMAT_REHEARSED_MANUAL_DRIVE_AUTH
result_root: results/20260803_care_test_docker_official_submission_rehearsal_and_staging
local_final_dist: /home/yuukias/code/CARE/dist/20260803_care_test_docker_final
server_rehearsal_packet: /users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_official_submission_rehearsal_and_staging/OFFICIAL_SUBMISSION_REHEARSAL_PACKET.tar.gz
controller_verification_decision: VERIFIED_COMPLETE_WITH_MANUAL_DRIVE_AUTH_REQUIRED
clean_archive_load: PASS
official_input_root_rehearsal: PASS
available_myops_cases: Case1001,Case1004,Case1012
available_cinemyops_cases: Case1003,Case1006,Case1011
myops_official_runtime_seconds: 373.44361090660095
cinemyops_official_runtime_seconds: 253.10728001594543
collaborator_myops_reference_interface: PASS
collaborator_reference_image_id: sha256:e3f9b5759bfa870363a8144577031d39f32129a63fa2b0f8c2b98552378cfebc
final_myops_tag_restored: true
google_drive_upload_ready: false
manual_rclone_oauth_required: true
email_draft_ready: true
email_ready_to_send: false
organizer_email_sent: false
challenge_upload_performed: false
validation_upload_performed: false
```

关键证据：

```text
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/official_submission_contract.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/clean_archive_load_receipt.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/official_command_rehearsal_summary.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/official_command_rehearsal_validation.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/collaborator_reference_interface_summary.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/google_drive_upload_receipt.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_email_draft.md
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_readiness.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/remote_rehearsal_packet_receipt.json
```

## 2026-08-03 最新机器真值：CARE-ASE R2 v5 等待外部训练前审阅

CARE-ASE R2 v5 的实现忠实性返修、G1/G2 证据包和持续 Reviewer RV5-D6/RV5-D7 内部审查已经完成；本状态只表示可以交给外部 GPT 做训练前实现审阅，不表示正式训练获准开始。fold1/fold4 的 14000-step 正式训练、outer access、validation/Docker/hosted upload 仍未授权。

```text
state_id: care_ase_r2_v5_pending_external_pretraining_review
active_branch: main
implementation_source_commit_sha: f4ecd049bb09a47c38305b932ef116d45b37c160
review_packet_commit_sha: 51b9c7bf307bf5b25cc502207b7d7384db9d1815
formal_training_authorized: false
formal_training_started: false
outer_access_fold1: 0
outer_access_fold4: 0
old_207f_runtime_credit: zero
old_e987_runtime_credit: zero
next_action: EXTERNAL_GPT_PRETRAINING_REVIEW
```

关键证据：

```text
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/pretraining_external_review_request.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/implementation_gap_closure.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/g1_static_implementation_gate_receipt.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/g2_real_gpu_fidelity_receipt.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/reviewer_semantic/RV5-D6/review.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/reviewer_semantic/RV5-D7/review.json
```

## 2026-08-03 最新机器真值：最终 CARE Docker 工位构建、验证、回传已完成

MyoPS 纯五折 nnU-Net Docker 已在 Windows WSL2 工位完成 build/run/save/load 黑盒验证，CineMyoPS 合作者原字节 archive 已直接 load/run 验证。两个镜像均为 `linux/amd64`，均通过 CPU smoke、重复确定性和 clean save/load/run；MyoPS host equivalence 已记录并通过，唯一差异是 Case1012 expected host output 的 2-voxel stale microdifference，按用户确认的服务器端旧 expected 输出原因作为显式 override 保留。最终 Docker archives 已回传服务器 final dist，未上传 challenge、validation、网盘，未给组织方发送邮件。

```text
state_id: care_test_docker_workstation_build_validate_return_20260803
active_development_branch: main
active_worktree: /home/yuukias/code/CARE
single_active_scientific_line: CARE_TEST_DOCKER_FINAL_WORKSTATION_VALIDATED_RETURNED
result_root: results/20260803_care_test_docker_workstation_build_validate_return
local_final_dist: /home/yuukias/code/CARE/dist/20260803_care_test_docker_final
server_final_dist: /users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist
controller_verification_decision: VERIFIED_COMPLETE
docker_engine_usable_without_sudo: true
myops_image: care-myocardium-myops:organagent
myops_image_id: sha256:52f8d872a51c482d488e3d2a14893958a6b1d6c8c91fffed9985ee330fcec911
myops_image_size_bytes: 4755438923
myops_archive_sha256: 638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b
myops_checkpoint_count_in_image: 5
myops_cpu_determinism: PASS
myops_host_equivalence: PASS_WITH_APPROVED_STALE_EXPECTED_OUTPUT_MICRODIFFERENCE
cinemyops_image: care-myocardium-cinemyops:organagent
cinemyops_image_id: sha256:5b10e6272f555c5ac54a23cca5d3819518bdb7d8d74d9e6a5496fea4991318ae
cinemyops_image_size_bytes: 1712467172
cinemyops_archive_byte_preserved: true
cinemyops_archive_sha256: c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136
cinemyops_cpu_determinism: PASS
clean_save_load_run: PASS
server_return_complete: true
validation_packet_returned: true
strict_validator: PASS
validation_upload_authorized: false
challenge_upload_authorized: false
netdisk_upload_authorized: false
organizer_email_send_authorized: false
```

关键证据：

```text
results/20260803_care_test_docker_workstation_build_validate_return/bundle_verification.json
results/20260803_care_test_docker_workstation_build_validate_return/docker_installation_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/build_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/image_asset_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/myops_validation_summary.json
results/20260803_care_test_docker_workstation_build_validate_return/cine_validation_summary.json
results/20260803_care_test_docker_workstation_build_validate_return/clean_save_load_run_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/docker_export_manifest.json
results/20260803_care_test_docker_workstation_build_validate_return/remote_return_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/strict_validator_report.json
/home/yuukias/code/CARE/.local_runtime/20260803_care_test_docker_workstation_build_validate_return/WORKSTATION_VALIDATION_PACKET.tar.gz
```

## 2026-08-03 最新机器真值：MyoPS Dockerfile 已修复 models 复制缺口，工位交接包已刷新

`b94d3f916b04461d6b88a311959e0ed581e64555` 的模型合同保持不变：MyoPS 仍是 Dataset501_CAREMyoPS 五折 nnU-Net、`nnUNetTrainer_500epochs`、`3d_fullres`、folds `0-4`、`checkpoint_best.pth`、default TTA，raw `0/1/2/3/4/5` 直接映射 official `0/200/500/600/1220/2221`。本次只修复 packaging 缺口：`docker/CARE2026_Myocardium/MyoPS/Dockerfile` 现在把 bundle context 中的 `models/` 复制到 `/app/models`，使运行时 `/app/models/nnunet/nnUNet_results` 能看到五折 checkpoint。

新 transfer 已准备，CineMyoPS 合作者 archive 继续保持原字节 SHA `c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136`。服务器未运行 Docker、未训练、未上传 challenge/validation/网盘、未给组织方发送邮件；工位 WSL 可以开始 MyoPS build/run/save 和 Cine load/run/save。

```text
state_id: care_test_docker_myops_context_hotfix_workstation_handoff_20260803
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_TEST_DOCKER_MYOPS_CONTEXT_HOTFIX_READY_FOR_WORKSTATION
base_model_contract_commit: b94d3f916b04461d6b88a311959e0ed581e64555
result_root: results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff
runtime_root: /users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff
transfer_root: /users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/transfer
terminal_state: SERVER_BUNDLE_READY
controller_verification_decision: VERIFIED_COMPLETE
myops_context_models_copy_fixed: true
model_contract_changed: false
myops_checkpoint_count_in_bundle: 5
myops_sentinel_cases: Case1012,Case1001,Case1004
cine_sentinel_cases: Case1011,Case1006,Case1003
cinemyops_archive_byte_preserved: true
server_docker_run_performed: false
new_training_performed: false
validation_upload_authorized: false
challenge_upload_authorized: false
netdisk_upload_authorized: false
organizer_email_send_authorized: false
```

关键证据：

```text
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/docker_context_hotfix_receipt.json
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/myops_bundle_manifest.json
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/cine_sentinel_manifest.json
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/workstation_handoff_receipt.json
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/strict_validator_report.json
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/transfer/WORKSTATION_HANDOFF.json
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/transfer/SERVER_BUNDLE_READY.json
```

下一步只允许工位 WSL 使用本 transfer 做 Docker build/load/run/save，并把工位回传证据放到 `/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_workstation_return`。不得把该服务器热修复解释为服务器已运行 Docker。

## 2026-08-02 最新机器真值：MyoPS 已修订为纯五折 nnU-Net，CineMyoPS 固定为合作者 Docker archive

旧 `c2f946b9376f4b39700f04b39c6d7a16e7154e67` 的 mixed MyoPS bundle 已被用户修订取代。本次服务器端没有运行 Docker，也没有安装 Docker/Podman/Buildah/Apptainer；服务器只完成版本冻结、合作者 archive 下载与静态审计、纯 nnU-Net MyoPS context、3-case host smoke、transfer bundle 和轻量 Git 证据。

新的最终 MyoPS 不再使用 MoSAIC scar overlay 或任何 MoSAIC edema/source/weight，而是直接使用 Dataset501_CAREMyoPS 五折 nnU-Net 六类 argmax：raw `0/1/2/3/4/5` 映射为 official `0/200/500/600/1220/2221`。CineMyoPS 使用合作者提供的预构建 Docker archive，服务器只验证 archive SHA 和 Docker-save 静态结构，后续 build/load/run/save 确定性门只授权在工位 WSL 执行。未上传 challenge/validation/网盘，未给组织方发送邮件。

```text
state_id: care_test_docker_nnunet_myops_collaborator_cine_rebundle_20260802
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_TEST_DOCKER_NNUNET_MYOPS_COLLABORATOR_CINE_READY_FOR_WORKSTATION
supersedes_commit: c2f946b9376f4b39700f04b39c6d7a16e7154e67
result_root: results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle
runtime_root: /users/a/e/aereinh/.tmp/codex-CARE/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle
transfer_root: /users/a/e/aereinh/.tmp/codex-CARE/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/transfer
terminal_state: SERVER_BUNDLE_READY
controller_verification_decision: VERIFIED_COMPLETE
selected_myops: dataset501_nnunet_v2_5fold_best_default_tta_all_six_classes
selected_myops_scar: nnunet_raw_class5
selected_myops_pure_edema: nnunet_raw_class4
selected_myops_anatomy: nnunet_raw_classes123
selected_cinemyops: collaborator_provided_prebuilt_mosaic_docker
myops_context_contains_mosaic: false
collaborator_myops_reference_only: true
collaborator_myops_reference_sha256: 81d19bbefd8f7cca46aee32b31a774f16222b6146b9eab6bc7265a6c214de2ff
cinemyops_archive_sha256: c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136
nnunet_version: 2.7.0
python_version: 3.12.13
torch_version: 2.11.0
pure_nnunet_fresh_output_count: 15
host_smoke_sentinel_cases: Case1012,Case1001,Case1004
server_docker_run_performed: false
workstation_build_authorized: true
validation_upload_authorized: false
challenge_upload_authorized: false
netdisk_upload_authorized: false
organizer_email_send_authorized: false
hosted_metric_claim_authorized: false
```

关键证据：

```text
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/revised_final_submission_model_contract.json
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/nnunet_environment_fingerprint.json
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/nnunet_source_manifest.json
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/collaborator_archive_manifest.json
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/pure_nnunet_myops_15case_manifest.json
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/pure_nnunet_myops_host_smoke_receipt.json
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/transfer_bundle_receipt.json
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/strict_validator_report.json
/users/a/e/aereinh/.tmp/codex-CARE/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/transfer/SERVER_BUNDLE_READY.json
```

下一步只允许工位 WSL 使用 transfer 中的 MyoPS nnU-Net bundle 和原字节 Cine archive 做 Docker build/load/run/save 与 CPU 确定性验证。不得把合作者 MyoPS reference 当作最终 MyoPS；若在 WSL 加载它，只能立即 retag 为 `care-myocardium-myops:collaborator-reference` 后做黑盒接口参考。

## 2026-08-01 最新机器真值：Docker provenance 纠偏后因当前部署源非确定性阻塞

本次已经执行新的 provenance reconcile 合同，没有直接沿用上一轮 `NNUNET_PROVENANCE_REPLAY_MISMATCH` 当阻塞理由。先按语义标签统一 package A 的官方标签 `200/500/600/1220/2221` 和 fresh nnU-Net 的 raw 类别 `1/2/3/4/5`，逐病例审计 anatomy `1/2/3`、pure edema `4`、scar `5`、used channels `1/2/3/4` 和 label transitions。结果是：几何 15/15 一致，完整数组 4/15 一致，生产会使用的 used channels 也只有 4/15 一致；11 个不一致病例合计 120 个语义体素变化，差异不是只落在将被 MoSAIC 替换的 scar 通道。

历史追溯没有找到能 exact 复现 package A 的 replay。按合同最多三个 frozen variants 已全部跑完：`checkpoint_final + default TTA`、`checkpoint_best + no TTA`、`checkpoint_final + no TTA` 均没有达到 full-array 或 used-channel 15/15 exact。因此历史 `0.6691` lineage 保持 `UNRESOLVED`，不得作 hosted claim。

随后按合同验证当前部署源自身：`checkpoint_best.pth + folds 0-4 + default TTA` 第二次 fresh replay 与上一轮 fresh replay 对比，geometry 15/15 一致，但 array 只有 7/15 完全一致，合计 13 个体素变化。这触发本任务明确允许的硬阻塞 `NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC`。因此没有生成 `SERVER_BUNDLE_READY.json`、没有生成工位 Docker transfer tar、没有让工位开始构建、没有上传网盘/validation/Docker、没有给组织方发邮件。

```text
state_id: care_test_docker_provenance_reconcile_deployable_nondeterministic_20260801
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_TEST_DOCKER_RECONCILE_BLOCKED_RETURN_TO_PLANNER
result_root: results/20260801_care_test_docker_provenance_reconcile_and_bundle
runtime_root: /users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine
terminal_state: SERVER_BUNDLE_BLOCKED
blocking_token: NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC
historical_hosted_lineage_status: UNRESOLVED
historical_0_6691_claim_authorized: false
package_a_geometry_equal_count: 15
package_a_full_array_equal_count: 4
package_a_used_channel_equal_count: 4
package_a_changed_semantic_voxels_total: 120
variant_replay_count: 3
variant_exact_reproduction_count: 0
deployable_repeat_geometry_equal_count: 15
deployable_repeat_array_equal_count: 7
deployable_repeat_changed_voxels_total: 13
server_bundle_ready: false
workstation_should_start: false
docker_or_rootless_attempted: false
new_training_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
organizer_email_send_authorized: false
hosted_metric_claim_authorized: false
```

关键证据：

```text
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_labelwise_equivalence_casewise.csv
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_label_transition_counts.csv
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_used_channel_equivalence_summary.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/historical_package_generation_trace.md
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_replay_variant_decision.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_deployable_source_receipt.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/controller_report.md
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/SERVER_BUNDLE_BLOCKED.json
```

下一步只允许 GPT Planner 决定是否授权确定性 nnU-Net 部署模式、CPU/禁 TTA 等新 source contract，或停止 Docker bundle 线。不得把当前 `NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC` 表述为历史 `0.6691` 已复现。

## 2026-08-01 历史机器真值：服务器端跨机器 Docker bundle 因 nnU-Net fresh replay 不一致阻塞

本次不再尝试安装或运行 Docker/rootless Docker，而是按跨机器方案在服务器端准备工位 WSL 可下载的构建资源。服务器已复用现有 `htzhulab` GPU allocation `61220581` 重新跑 frozen Dataset501 五折 nnU-Net `checkpoint_best.pth` 的 15 例公开 validation 推理；15 个 fresh 输出都生成，几何与历史 package A 全部一致，但数组只有 4/15 完全一致。因此历史 0.6691 edema 归属不能被当前 fresh replay 证明，MyoPS 可执行 bundle 和 `SERVER_BUNDLE_READY.json` 被合同硬门禁止。

MoSAIC 诊断部分：MyoPS Docker-recipe fresh replay 已完成 15/15；CineMyoPS 诊断在上游 nnU-Net 硬门已失败后停止于 4/15，没有作为提交候选或 ready 条件使用。没有使用 sudo，没有修改 `/etc`，没有运行 Docker/Podman/Buildah/Apptainer，没有新训练，没有上传网盘、validation 或给组织方发邮件。

```text
state_id: care_test_docker_server_bundle_nnunet_mismatch_20260801
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_TEST_DOCKER_SERVER_BUNDLE_RETURN_TO_PLANNER
result_root: results/20260801_care_test_docker_server_bundle
runtime_root: /users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine
terminal_state: SERVER_BUNDLE_BLOCKED
blocking_token: NNUNET_PROVENANCE_REPLAY_MISMATCH
nnunet_fresh_output_count: 15
nnunet_geometry_equal_count: 15
nnunet_array_equal_count: 4
mosaic_myops_diagnostic_case_count: 15
mosaic_cinemyops_diagnostic_case_count: 4
server_bundle_ready: false
workstation_should_start: false
docker_or_rootless_attempted: false
new_training_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
organizer_email_send_authorized: false
hosted_metric_claim_authorized: false
```

关键证据：

```text
results/20260801_care_test_docker_server_bundle/fresh_nnunet_provenance_receipt.json
results/20260801_care_test_docker_server_bundle/fresh_nnunet_vs_historical_casewise.csv
results/20260801_care_test_docker_server_bundle/fresh_mosaic_myops_manifest.json
results/20260801_care_test_docker_server_bundle/fresh_mosaic_cine_manifest.json
results/20260801_care_test_docker_server_bundle/fresh_mosaic_replay_receipt.json
results/20260801_care_test_docker_server_bundle/controller_report.md
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/SERVER_BUNDLE_BLOCKED.json
```

下一步只允许 GPT Planner 决定是否追溯历史 package A 的原始生成命令/环境，或改写 bundle 合同。当前不得让工位执行 Docker 构建，也不得生成提交邮件或 Docker archive。

## 2026-08-01 最新机器真值：测试 Docker rootless unblock 在主机 subuid/subgid 前提处阻塞

本次没有停在“没有 docker 命令”的旧判断上，而是按新合同完成了 rootless Docker 前置审计并下载校验了官方 rootless installer。服务器允许 `unshare -Ur true`，`newuidmap/newgidmap` 存在，本地 `/tmp` 是可用的 xfs Docker data root；真正阻塞点是 `/etc/subuid` 和 `/etc/subgid` 没有给当前用户 `aereinh` 分配至少 65536 的 subordinate uid/gid 范围。任务禁止 sudo 和系统级安装，因此不能修改这两个系统文件，也不能把 Apptainer/Singularity 替代成 Docker。

```text
state_id: care_test_docker_rootless_prerequisite_blocked_20260801
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_TEST_DOCKER_ROOTLESS_UNBLOCK_RETURN_TO_PLANNER
result_root: results/20260801_care_test_docker_rootless_unblock
terminal_state: ROOTLESS_DOCKER_PREREQUISITE_BLOCKED
controller_verification_decision: OPERATIONALLY_BLOCKED
unprivileged_user_namespace_works: true
newuidmap_exists: true
newgidmap_exists: true
subuid_total: 0
subgid_total: 0
selected_docker_data_root: /tmp/aereinh/care-rootless-docker-data
official_rootless_installer_downloaded: true
official_rootless_installer_executed: false
docker_images_built: false
docker_tarballs_exported: false
new_training_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
organizer_email_send_authorized: false
hosted_metric_claim_authorized: false
```

关键证据：

```text
results/20260801_care_test_docker_rootless_unblock/rootless_prerequisite_audit.json
results/20260801_care_test_docker_rootless_unblock/rootless_storage_receipt.json
results/20260801_care_test_docker_rootless_unblock/rootless_install_receipt.json
results/20260801_care_test_docker_rootless_unblock/rootless_admin_fix_required.md
results/20260801_care_test_docker_rootless_unblock/controller_report.md
results/20260801_care_test_docker_rootless_unblock/strict_validator_report.json
```

下一步只允许在管理员为 `aereinh` 配置有效 `/etc/subuid` 和 `/etc/subgid` 后，从该合同 W1 重新执行。当前不得上传 Docker、不得给组织方发邮件、不得声称测试 Docker 已可提交。

## 2026-08-01 最新机器真值：四模型证据纠偏后无本地候选

本次重新评价把旧结论中最关键的漏洞补上了：M0R 必须和同病例 stock nnU-Net 比较，M2 不能因为 inner selection 失败就省略 outer 评价，距离和小病灶指标也不能再用体素单位冒充物理单位。纠偏后，M0R 在真正未见的 fold2+fold3 outer 病例上没有超过同病例 stock；M2 的 scar 明显低于 stock，edema 虽略高但没有达到候选门槛且损害比例过高。因此旧的 scar-only 候选说法已撤销，当前应回到 Planner 决定下一步，不得上传 validation、Docker 或声称 hosted 指标。

```text
state_id: care_four_lane_evidence_reconciled_no_candidate_20260801
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_FOUR_LANE_RECONCILIATION_RETURN_TO_PLANNER
result_root: results/20260801_care_four_lane_evidence_reconciliation
previous_decision_superseded: superseded_scar_only_candidate_label
scientific_decision: FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE
M0R_outer_scar_delta_vs_stock_dice: -0.0020118904817150174
M0R_outer_edema_delta_vs_stock_dice: -0.030114178203399733
M2_outer_scar_delta_vs_stock_dice: -0.05011471399535905
M2_outer_edema_delta_vs_stock_dice: 0.018926404811234976
M2_scar_gate_pass: false
M2_edema_gate_pass: false
controller_verification_decision: VERIFIED_COMPLETE
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
```

关键证据：

```text
results/20260801_care_four_lane_evidence_reconciliation/four_lane_scientific_interpretation.md
results/20260801_care_four_lane_evidence_reconciliation/m0r_vs_stock_outer_summary.csv
results/20260801_care_four_lane_evidence_reconciliation/m2_vs_stock_outer_summary.csv
results/20260801_care_four_lane_evidence_reconciliation/inner_stock_privilege_audit.csv
results/20260801_care_four_lane_evidence_reconciliation/m1_fidelity_audit.json
results/20260801_care_four_lane_evidence_reconciliation/m3_fidelity_audit.json
results/20260801_care_four_lane_evidence_reconciliation/strict_validator_report.json
```

## 2026-08-01 已撤销历史状态：四模型缺口闭合本地评价曾标记 scar-only 候选

完整三模态四模型缺口闭合任务曾完成 M0R/M1/M2/M3 fold2+fold3 训练、checkpoint reload 审计、inner full-volume evaluation、global source freeze 和 outer deterministic replay。旧 M0 仍只能标记为 `HIGH_LR_SHORT_FINETUNE_NEGATIVE`；当时的获胜 source 是修复后的 M0R faithful control。该段只保留历史脉络；候选判断已被上方四模型证据纠偏结果撤销。

```text
state_id: care_target_domain_gap_closure_scar_only_candidate_20260801
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_TARGET_DOMAIN_GAP_CLOSURE_SUPERSEDED_SCAR_ONLY_CANDIDATE_LABEL
result_root: results/20260801_care_target_domain_race_gap_closure
old_m0_classification: HIGH_LR_SHORT_FINETUNE_NEGATIVE
existing_interactive_job_id: 61220581
M0R_training: complete_fold2_fold3_4000_steps_each
M1_training: 61576324_COMPLETED_0_0
M2_training: 61627615_COMPLETED_0_0
M3_training: complete_fold2_fold3_4000_steps_each
inner_evaluation: complete_all_four_lanes
global_scar_source: m0r_faithful_control_step3500
global_edema_source: m0r_faithful_control_step4000
outer_replay: complete_fold2_fold3_outer
outer_scar_dice_mean: 0.6500
outer_edema_dice_mean: 0.4340
scientific_decision: superseded_scar_only_candidate_label
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
remaining_operational_boundary: final_validator_commit_push_remote_sha_notification
```

Key evidence:

```text
results/20260801_care_target_domain_race_gap_closure/completion_check.md
results/20260801_care_target_domain_race_gap_closure/scientific_decision.json
results/20260801_care_target_domain_race_gap_closure/inner_evaluation/global_source_selection.json
results/20260801_care_target_domain_race_gap_closure/outer_replay/outer_replay_receipt.json
results/20260801_care_target_domain_race_gap_closure/outer_replay/sentinel_case_atlas.md
results/20260801_care_target_domain_race_gap_closure/mapper_report_final.md
```

下一步只允许 GPT Planner 基于本地 evidence 决定是否扩展 scar line、修 edema line，或停止；不得把这个结果解释成 hosted validation claim，不得自动上传 validation/Docker。

## 2026-08-01 最新机器真值：四模型缺口闭合继续执行，旧 W0 interactive-lost 阻塞已撤销

完整三模态四模型缺口闭合任务已经同步到 `main` 最新合同，并完成 W0 启动审计、协议读取、SRR-v2/v2.5/v3 视觉读取、旧 M0 fidelity 审计、split 复用 hash、executor plan validator 修复和目标 validator。旧 M0 不能再解释为忠实目标域微调负结果；它实际使用 nnU-Net 默认 `SGD`、初始学习率 `1e-2`、`PolyLRScheduler` 和 16 epoch 训练，没有 500-step checkpoint 的全体积 inner selection，因此只能标记为 `HIGH_LR_SHORT_FINETUNE_NEGATIVE`。

此前 `OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST` packet 是过早的资源门误判，现已被用户提供并经 controller 验证的 `61220581 / htzhulab / g1807htzh01` RUNNING GPU allocation 撤销。`srun --jobid=61220581 --overlap` 的 CUDA probe 已确认该 allocation 暴露 `NVIDIA H100 NVL`。当前状态是非终局继续执行：M3 先用该 interactive GPU；M0R/M1/M2 在 preflight 后提交 `htzhulab` 队列作业；若 interactive 跑完而某个队列作业仍 pending，则取消一个 pending 作业并在 interactive allocation 中串行接力。不得把旧 blocked packet 解释为四模型全失败。

截至 2026-08-01 当前复查，M3 fold2/fold3 已在 `61220581` 中完成 4000-step 训练；M0R 旧 fold2 job `61565286` 与 fold3 takeover 训练已被新的 faithful rerun supersede，新的 M0R fold2+fold3 均在 `61220581 / htzhulab / g1807htzh01` interactive allocation 内完成 4000 optimizer steps，训练 receipt 记录 `AdamW`、`WarmupCosine_per_optimizer_step`、250-step warmup、cosine min lr `1e-6`，并写出每 500 step checkpoint grid。旧 M1 fold jobs `61565288`/`61565289` 因资源合同不符已取消；替换后的 12 CPU/96G/12h lane-level job `61576324` 已 `COMPLETED 0:0` 并完成 fold2+fold3。interactive takeover monitor PID `4185840` 的最终含义是 `M1_QUEUE_COMPLETED_NO_TAKEOVER_NEEDED`：它没有取消 M1，因为 M1 已经启动并随后正常完成。M2 source 已 pin 到 `third_party/I_MMSeg_PINNED`，Google Drive 的两个核心公开权重 `R50-ViT-B_16.npz` 和 `epoch_299.pth` 已下载并记录 SHA256；released `epoch_299.pth` GPU smoke PASS；MyoPS380 dataset 没有下载也不得混入 CARE 训练。

现在剩余的不是“再把四个模型训练一遍”，而是目标合同后半段：inner full-volume selection、outer deterministic replay、统一 aggregation、失败/缺口 atlas、mapper 更新、strict final validator、最终轻量 commit/push 和 notifier。M2 的外部核心权重缺口已经补齐，Dataset501 CARE adapter preflight 已在 existing `61220581 / htzhulab` 上通过；formal fold2/fold3 lane job `61627615` 已在 `htzhulab / g1807htzh01` `COMPLETED 0:0`，log 为 `logs/M2IMM_61627615_20260801_031043.log`。M0R 的训练协议缺口已经修复，但仍缺 full-volume inner selection 和 manifest-bound crop/augmentation fidelity 闭环；M1/M2/M3 也仍缺合同级评价与若干实现 fidelity 差距。最新 checkpoint asset manifest 已写入 `checkpoint_reload_audit.json`：M0R/M1/M2/M3 的 500-step checkpoint grid 均齐全，`load_policy: final` 与 `hash_policy: final` 审计状态为 `PASS`，最终/最大 step checkpoint 已完成 torch.load 与 SHA256 记录。

```text
state_id: care_target_domain_gap_closure_active_after_interactive_recovery_20260801
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_TARGET_DOMAIN_GAP_CLOSURE_ACTIVE_CONTINUATION
method_name: faithful target-domain four-lane gap closure
controller_is_coordinator: true
result_root: results/20260801_care_target_domain_race_gap_closure
old_m0_classification: HIGH_LR_SHORT_FINETUNE_NEGATIVE
previous_decision_superseded: OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST
usable_existing_interactive_allocation: true
existing_interactive_job_id: 61220581
existing_interactive_partition: htzhulab
existing_interactive_node: g1807htzh01
existing_interactive_gpu: NVIDIA H100 NVL
formal_lane_training_started: true
queue_jobs_submitted_by_this_goal: true
interactive_steps_started_by_this_goal: true
M3_fold2_fold3_training: complete_4000_steps_each
M0R_initial_fold2_job: 61565286 COMPLETED_0_0 SUPERSEDED_BY_FAITHFUL_RERUN
M0R_initial_fold3_cancelled_job: 61565287 CANCELLED_FOR_INTERACTIVE_TAKEOVER
M0R_initial_fold3_interactive_pid: 4039804 EXITED_AFTER_COMPLETION SUPERSEDED_BY_FAITHFUL_RERUN
M0R_faithful_rerun: 61220581 COMPLETED_FOLD2_FOLD3_4000_STEPS_EACH
M0R_faithful_rerun_log: logs/M0RGapLane_61220581_20260801_014519.log
M0R_scheduler_optimizer: AdamW_WarmupCosine_per_optimizer_step_250_warmup_min_lr_1e-6
M1_old_fold_jobs: 61565288,61565289 CANCELLED_RESOURCE_CONTRACT_REPLACED
M1_lane_job: 61576324 COMPLETED_0_0 12CPU_96G_12H
interactive_takeover_monitor_pid: 4185840 EXITED_M1_QUEUE_COMPLETED_NO_TAKEOVER_NEEDED
M2_status: TRAINING_COMPLETE_FOLD2_FOLD3_PENDING_RELOAD_AND_EVALUATION
M2_asset_download_receipt: results/20260801_care_target_domain_race_gap_closure/m2_i_mmseg_care/asset_download_receipt.json
M2_released_checkpoint_smoke_receipt: results/20260801_care_target_domain_race_gap_closure/m2_i_mmseg_care/released_checkpoint_smoke_receipt.json
M2_preflight_receipt: results/20260801_care_target_domain_race_gap_closure/m2_i_mmseg_care/adapter_preflight_report.json
M2_formal_job: 61627615 htzhulab g1807htzh01 COMPLETED_0_0
M2_formal_log: logs/M2IMM_61627615_20260801_031043.log
M2_training_accounting: results/20260801_care_target_domain_race_gap_closure/m2_i_mmseg_care/training_accounting.csv
M2_training_receipts: results/20260801_care_target_domain_race_gap_closure/m2_i_mmseg_care/fold2_training_receipt.json, results/20260801_care_target_domain_race_gap_closure/m2_i_mmseg_care/fold3_training_receipt.json
remaining_required_work: inner_full_volume_selection, outer_replay, aggregation, atlas, mapper, strict_final_validator, final_commit_push, notification
checkpoint_asset_manifest: results/20260801_care_target_domain_race_gap_closure/checkpoint_reload_audit.json
planner_gap_resolution_handoff: results/20260801_care_target_domain_race_gap_closure/planner_gap_resolution_handoff.md
M0R_M1_M3_step_checkpoint_grid: COMPLETE
scientific_decision: CONTROLLER_ACTIVE_CONTINUATION
controller_verification_decision: ACTIVE_CONTINUATION
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
```

关键证据：

```text
results/20260801_care_target_domain_race_gap_closure/controller_context.json
results/20260801_care_target_domain_race_gap_closure/m0_protocol_fidelity_audit.json
results/20260801_care_target_domain_race_gap_closure/frozen_data_contract.json
results/20260801_care_target_domain_race_gap_closure/existing_interactive_receipt.json
results/20260801_care_target_domain_race_gap_closure/scientific_decision.json
results/20260801_care_target_domain_race_gap_closure/blocker_superseded_by_user_override.md
results/20260801_care_target_domain_race_gap_closure/lane_preflight_summary.json
results/20260801_care_target_domain_race_gap_closure/scheduler_receipt.json
results/20260801_care_target_domain_race_gap_closure/interactive_takeover_monitor_state.json
results/20260801_care_target_domain_race_gap_closure/external_assets_plan.md
results/20260801_care_target_domain_race_gap_closure/strict_validator_report.json
results/20260801_care_target_domain_race_gap_closure/known_bad_report.json
```

继续执行时必须按 `htzhulab` 分区和具体 job id 查询 interactive allocation；不能只看默认 `squeue -u` 后写 resource-lost。禁止新建 interactive allocation、提交 a100/volta、访问 official validation、上传 validation/Docker 或作 hosted metric claim。

## 2026-07-31 最新机器真值：CARE-MyoWall-IF frozen-stock geometry gate 失败，禁止进入四臂正式训练

CARE-MyoWall-IF 机制试验已完成 metric dependency、fold1 stock nnU-Net 资产冻结、pilot split、stock parity、代码/known-bad validator 和完整 `pilot_inner` frozen-stock predicted geometry gate。metric truth 依赖来自隔离 metric-truth worktree 的正式 PASS receipt；当前 main 仍没有本地同名 receipt，因此后续 Planner 若要求严格 current-main metric 归档，需要先合并/落地该 receipt。

`pilot_inner` 共 32 例；fold1 outer 未读取。冻结 fold1 nnU-Net 的最终 logit 与独立 source model FP32 parity 为 0，argmax changed voxels 为 0。但 predicted geometry 前置门失败：case geometry valid rate `0.84375`，低于合同要求 `>=0.95`；5th-percentile wall roundtrip Dice `0.7068920140479127`，低于合同要求 `>=0.90`。因此科学决策为 `STOP_GEOMETRY_NOT_RELIABLE`，不得通过 GT geometry、Cartesian fallback 或降低 gate 门限继续正式四臂训练。

```text
state_id: care_myowall_if_geometry_stop_20260731
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_MYOWALL_IF_GEOMETRY_STOP_RETURN_TO_PLANNER
method_name: CARE-MyoWall-IF
controller_is_coordinator: true
result_root: results/20260731_care_myowall_if_mechanism_pilot
metric_dependency_status: PASS
metric_receipt_source: external_isolated_metric_truth_worktree
fold: 1
pilot_inner_count: 32
pilot_train_count: 144
fold1_outer_accessed: false
stock_parity_status: PASS
fp32_stock_logit_parity_max_abs_error: 0.0
argmax_changed_voxels: 0
geometry_gate: FAIL
case_geometry_valid_rate: 0.84375
median_wall_roundtrip_dice: 0.9998856896450612
fifth_percentile_wall_roundtrip_dice: 0.7068920140479127
median_roundtrip_hd95_mm: 0.0
scientific_decision: STOP_GEOMETRY_NOT_RELIABLE
controller_verification_decision: VERIFIED_COMPLETE
C0_W1_W2_W3_formal_training_started: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
```

关键证据：

```text
results/20260731_care_myowall_if_mechanism_pilot/controller_terminal_packet.json
results/20260731_care_myowall_if_mechanism_pilot/strict_validator_report.json
results/20260731_care_myowall_if_mechanism_pilot/geometry_gate_report.json
results/20260731_care_myowall_if_mechanism_pilot/geometry_casewise_metrics.csv
results/20260731_care_myowall_if_mechanism_pilot/stock_parity_report.json
results/20260731_care_myowall_if_mechanism_pilot/pilot_split_receipt.json
results/20260731_care_myowall_if_mechanism_pilot/metric_dependency_receipt.json
```

本状态覆盖下面旧的 PRISM 连续 controller 中间授权。除非 Planner 明确授权新的 geometry-repair-only follow-up，不得启动 C0/W1/W2/W3 8000-step formal training、不得访问 fold1 outer、不得上传 validation/Docker、不得作 hosted metric claim。

## 2026-07-29 最新机器真值：CARE-PRISM v2 W3 足额完成，但 fold0 门失败，禁止进入 W4

CARE-PRISM v2 已从修复后的 fold0 stock nnU-Net checkpoint 重新完成 W1/W2，并执行 W3 fold0 6500-step formal v2。W3 训练本身、每 500 step checkpoint 审计、all-checkpoint inner selection、freeze receipt 和 fold0 outer 一次性评价链路完整；但是 frozen selected checkpoint 在 outer 上同时伤害 scar 和 edema-zone，相对同折 nnU-Net 明显下降，因此 W3 strict validator fail-closed，W4/fold1 clean training 不得启动，需返回 Planner 重新规划 calibration/refinement。

```text
state_id: care_prism_v2_w3_gate_failed_20260729
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_PRISM_V2_W3_RETURN_TO_PLANNER
method_name: CARE-PRISM v2
controller_is_coordinator: true
result_root: results/20260729_care_prism_v2_backbone_repair_and_resume
w1_w2_status: STRICT_PASS
w3_training_status: PASS_6500_STEPS
w3_inner_selection: PASS_ALL_13_CHECKPOINTS
w3_selected_checkpoint: results/20260729_care_prism_v2_backbone_repair_and_resume/runtime/fold0_w3_fold0_6500_formal_v2/checkpoints/checkpoint_step03000.pt
w3_selected_checkpoint_sha256: 33ce3dc6fa72b5bda9eca7489d01ec2ae12acf90edbba46eda3456ef5e5504e6
fold0_outer_accessed: true
fold0_outer_access_semantics: one_time_after_freeze
fold1_outer_accessed: false
w4_started: false
w3_strict_validator: FAIL
failure_classification: CALIBRATION
controller_verification_decision: NEEDS_REPAIR
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
```

关键证据：

```text
results/20260729_care_prism_v2_backbone_repair_and_resume/w1_w2_strict_validator_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_training_summary.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_checkpoint_audit_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_inner_select_formal_v2/summary.json
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_outer_once_formal_v2/summary.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_strict_validator_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/controller_w3_return_packet.json
results/20260729_care_prism_v2_backbone_repair_and_resume/mapper_final_report.json
```

outer once selected checkpoint 结果：

```text
scar Dice: CARE-PRISM 0.4196441776 vs same-fold nnU-Net 0.5340911530, delta -0.1144469754, harm 37/44 cases
edema-zone Dice: CARE-PRISM 0.2471543848 vs same-fold nnU-Net 0.5592277699, delta -0.3120733851, harm 37/44 cases
remote_fp_count: 0 for scar and edema-zone
```

本状态覆盖下面旧的“自动继续 W3–W5”中间态。除非 Planner 明确授权新的 repair plan，不得继续 W4、不得访问 fold1 outer、不得重调 fold0 outer、不得上传 validation/Docker、不得作 hosted metric claim。

## 2026-07-30 最新机器真值：CARE-PRISM v2 持续 Controller，先修复 W1/W2，再自动继续 W3–W5

最新中间提交 `71717f0d7c6232cb8b68dd4d6442f8a5223ce297` 已解决同折 stock nnU-Net 主干定位、完整移植和 FP32 奇偶校验，并完成一次 400-step 真实病例 zero-credit 循环。Planner/Critic 随后发现标签语义、proposal/negative 直接梯度、anatomy exchange、负空间平衡、正式采样、exact resume、阶段训练、inner/outer lock、评价和 validator 仍未闭环。

用户现已明确授权：**Controller 不得再在修复中间态暂停等待人工验收。它必须在同一个 goal 内持续执行“实现—独立审计—修复—重跑”闭环；W1/W2 全部门独立通过后自动进入 W3，W3 通过后自动进入 W4，最终完成 W5。目标完整达到后推送轻量提交到 `origin/main`；目标真实阻塞时发送阻塞邮件。**

```text
state_id: care_prism_v2_continuous_controller_20260730
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_PRISM_V2_CONTINUOUS_W1_W2_REPAIR_THEN_W3_W4_W5
method_name: CARE-PRISM v2
controller_is_coordinator: true
planning_review_required: false
review_required: false
w1_intermediate_claim: REJECTED_PENDING_REPAIR
w2_intermediate_claim: REJECTED_PENDING_RERUN
w3_authorized_condition: W1_W2_INDEPENDENT_STRICT_PASS
w3_manual_planner_acceptance_required: false
fold0_outer_accessed: false
fold1_outer_accessed: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
runtime_git_push_authorized: false
terminal_verified_complete_push_authorized: true
terminal_email_on_verified_complete: true
terminal_email_on_true_block: true
result_root: results/20260729_care_prism_v2_backbone_repair_and_resume
```

## 当前最高权威

```text
continuous_controller:
prompts/tasks/20260729_care_prism_controller_v2.md

active_repair_controller:
prompts/tasks/20260730_care_prism_w1_w2_repair_controller.md

critic_repair_amendment:
prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md

inherited_backbone_repair:
prompts/tasks/20260729_care_prism_v2_backbone_and_w1_repair_amendment.md
prompts/tasks/20260729_care_prism_v2_backbone_repair_executor_plan.yaml

inherited_scientific_contract:
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan_v2.yaml
```

```text
b8c373eab27a8a958e6b6731c867eb7087922fa7  continuous self-auditing controller
addb54793751699ba5515c2860830c40e37ba94d  W1/W2 repair and auto-continue controller
a76f3fd639ce09b900ce232bf65550fa4be37120  W1/W2 critic repair amendment
71717f0d7c6232cb8b68dd4d6442f8a5223ce297  rejected intermediate W1/W2 packet
```

冲突优先级：

```text
本 CURRENT 中的用户连续执行/终态推送授权
> updated continuous controller
> updated W1/W2 repair controller
> 20260730 W1/W2 critic repair amendment 的科学与实现要求
> 20260729 backbone/W1 repair amendment
> inherited executor plans
> PRISM v2 hardening/base blueprint
> intermediate W1/W2 packet
> previous blocked packet
> ARC and historical routes
```

`20260730_care_prism_w1_w2_critic_repair_amendment.md` 中“修复后返回 Planner”的中间停止要求已被本次用户授权覆盖；其标签、梯度、loss、采样、resume、评价和 known-bad 要求仍全部有效。

## 已验证可保留部分

- fold0/fold1 checkpoint 文件、大小和 SHA256 当前核验通过；
- 按 `nnUNetPlans.json` 恢复真实 `PlainConvUNet`；
- encoder 参数字节覆盖率 1.0，FP32 各尺度误差 0；
- 输入顺序 `[LGE,T2,C0]` 正确；
- pathology level1–3 干预会改变最终 logit；
- prototype 默认关闭，slice correspondence 冻结 identity；
- no-T2 前向概率和 mask 为零。

## 当前必须修复的问题

1. `edema_zone_target` 必须取 label 4 或 5；`myocardium_union` 必须为标签 1/4/5。
2. proposal/negative 未 detach 的直接 loss 必须进入总损失并对对应 head 产生直接梯度。
3. anatomy exchange 不得 gate/projection 双零初始化形成死分支，且必须单独验证。
4. scar 必须有真实 component/lesion-level 监督；scar/edema 必须有真实双侧 surface/distance loss。
5. 四类 negative 必须病例内平衡；edema negative 只允许 T2-present。
6. 必须使用 canonical metadata 的 center×burden×positive/safe-negative sampler。
7. 必须实现正式 exact resume，而非只检查 checkpoint key。
8. A/B/C/D 必须真实切换 active loss、冻结范围与 LR。
9. 必须实现 actual-train/inner-select/outer、all-checkpoint selection、freeze receipt 和 one-time outer lock。
10. evaluator 必须覆盖 Dice、HD95、exact HD、lesion recall、remote FP、component、volume ratio、help/harm 和同划分 nnU-Net。
11. W2 PASS 必须来自训练充分性证据，不得无条件写入。
12. known-bad 与 strict validator 必须能拒绝上述所有语义绕过。

完整科学要求见：

```text
prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md
```

## 持续执行图

```text
R3 semantic/data/loss/exchange/sampler/resume/evaluator repair
→ Controller independent code/tensor/gradient/known-bad audit
→ rerun W1
→ rerun W2 400-step zero-credit from fold0 stock checkpoint
→ independent strict W1/W2 gate
→ if PASS automatically start W3 fold0 6500 from fold0 stock checkpoint
→ every 500 steps continuous stage/loss/LR/sampler/gradient/reload audit
→ all-checkpoint inner selection and atomic one-time fold0 outer
→ only if W3 passes start W4 fold1 8000 clean
→ W5 terminal accounting / aggregation / strict validator / Mapper / CURRENT/wiki / lightweight commit
→ VERIFIED_COMPLETE only: push origin/main, verify remote SHA, send completion email
```

旧 W2 step400 checkpoint只能作为诊断，禁止续接 W3。标签、loss、sampler、architecture 或 stage 语义修复后，受污染训练必须从同折 nnU-Net 初始化重跑；纯启动/环境故障才允许 exact resume。

Controller 不能依赖 Executor 自产的 `PASS` 或单一 validator。每个 gate 必须同时具备：

```text
代码语义审计 + executable known-bad + 独立重载/重算
```

普通实现、数据、OOM、cache、sampler、augmentation、loss、resume、evaluation、validator和notifier问题必须在同一 goal 内持续修复。只有以下情况允许停止：

- 既有 allocation 或必要资产在所有合法定位后真实不可用；
- 缺少外部权限且无法在现有授权内解决；
- 必须改变冻结科学设计、数据划分、预算或 outer 语义；
- 忠实实现、充分训练、全部 checkpoint 重载评价后仍发生机制失败。

## 冻结同折主干资产

```text
fold0 checkpoint:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth
sha256: 8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111
size_bytes: 357381749

fold1 checkpoint:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_final.pth
sha256: 5310569ff62f2f9a6ff2bc7dd3754404140071427a2025caf5e25d2916cfe400
size_bytes: 357381813

plans:
data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json
```

## 资源、推送与邮件

先检查既有 allocation：

```text
jobid: 61220581
partition: htzhulab
node: g1807htzh01
```

若仍运行，只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新 Slurm job、并行 GPU、写 `/overflow/htzhu/CARE`、validation/Docker upload、hosted claim和任何 outer 调参。Runtime 期间禁止 push。

只有 `controller_verification_decision: VERIFIED_COMPLETE`，且所有进程终态、aggregation、strict validator、Mapper、CURRENT/wiki、轻量 commit 全部确认后，才允许自动推送轻量代码与结果到 `origin/main`。不得推送 checkpoint、NIfTI、raw data、大日志、cache、secret或上传包。Push 后必须核对远端 SHA，再发送中文完成邮件。

若出现真实终态阻塞或忠实机制失败，同范围修复已穷尽并写好稳定阻塞 packet 后，发送一次中文阻塞邮件；修复中、submitted、pending、running、monitor或中间 PASS 不得通知。

## 2026-08-01 nnU-Net / MoSAIC 互补证据闭合

本轮只做冻结证据闭合，不训练、不调阈值、不构造病例级 selector、不上传 validation 或 Docker。结论是：nnU-Net 仍是当前可靠底线；MoSAIC clean OOF 在 scar 少数病例上有有限互补信号，但 pure edema 没有形成可用互补。M10 只保留为 full-data 机制诊断，不能作为泛化证据。

```text
result_root:
results/20260801_care_nnunet_mosaic_complementarity_closure

controller_verification_decision: VERIFIED_COMPLETE
strict_validator_status: PASS
terminal_decision: LIMITED_COMPLEMENTARITY_FOR_DIAGNOSTIC_REVIEW_ONLY
```

核心证据：

```text
220-case fair OOF matrix:
results/20260801_care_nnunet_mosaic_complementarity_closure/oof_complementarity_casewise.csv

80-case M10 diagnostic:
results/20260801_care_nnunet_mosaic_complementarity_closure/m10_diagnostic_casewise.csv

15-case fresh validation no-GT disagreement:
results/20260801_care_nnunet_mosaic_complementarity_closure/validation_disagreement_casewise.csv

strict validator:
results/20260801_care_nnunet_mosaic_complementarity_closure/strict_validator_report.json
```

主要数字：

- scar all-case：nnU-Net mean Dice `0.561047`，MoSAIC clean OOF mean Dice `0.378168`，case-oracle gain `0.021954`，MoSAIC rescue fraction `18/220 = 0.081818`。
- pure edema T2-present 80-case：nnU-Net mean Dice `0.430812`，MoSAIC clean OOF mean Dice `0.052756`，case-oracle gain `0.002293`，MoSAIC rescue fraction `0/80`。
- validation 15-case：复用 2026-07-28 frozen fresh no-GT disagreement 输出；没有提交新训练或新 GPU 推理 job，没有 GT 性能结论。

边界：

- `oof_case_oracle_bounds.csv` 是上界，不是可部署 selector。
- `m10_diagnostic_casewise.csv` 中 M10 行标记 `trained_on_case_possible=true` 与 `not_valid_for_generalization_claim=true`。
- validation disagreement 只能说明两个预测的差异，不能写成谁更好。

## 2026-08-05 MyoPS single-slice runtime-only Docker hotfix

这次修复的是已经提交给组织方的 MyoPS Docker 在合法单层输入上可能因 nnU-Net 重采样尺寸被算成 0 而整批失败的问题。修复只在运行时给 nnU-Net `compute_new_shape` 结果增加 `np.maximum(new_shape, 1)` 保护；没有更换 checkpoint、fold、TTA、label map、`/app/predict.py`、`/app/entrypoint.sh`、`requirements.lock`、依赖或模型配置。畸形跨模态 geometry mismatch 被记录为继承的非阻塞基础行为：`INHERITED_BASE_BEHAVIOR_OUT_OF_SCOPE_NONBLOCKING`。

```text
local_result_root:
results/20260805_care_myops_single_slice_hotfix_repackage

server_audit_root:
results/20260805_care_myops_single_slice_hotfix_server_audit

server_terminal_token:
CORRECTED_MYOPS_RUNTIME_ONLY_HOTFIX_READY_FOR_ORGANIZER_REEVALUATION

corrected_archive:
dist/20260805_care_myops_single_slice_hotfix/MyoPS-OrganAgent-corrected.tar.gz

corrected_archive_size:
4742235545

corrected_archive_sha256:
fcf1c67a2123ab655a8e6c32dc46e6d98feaa43f41c698c6969aebfaa51f79ff

drive_link:
https://drive.google.com/open?id=1ATXgeTn99xFZAB3SLH1-aSpTuIb5EO5a

organizer_email_sent:
false
```

Verified evidence:

- old single-slice failure reproduced before patching;
- model invariance PASS for five `checkpoint_best.pth` files, plans/dataset, `/app/predict.py`, `/app/entrypoint.sh`, `requirements.lock`, pip freeze, ENTRYPOINT/Cmd/Env, and rootfs prefix;
- 15/15 normal public MyoPS cases bitwise/geometrically/canonical-SHA exact between base and corrected images;
- depth1/depth2 valid synthetic single-slice matrix PASS;
- mixed normal-plus-single-slice batch PASS with no missing output;
- determinism and clean save/load/full synthetic rerun PASS;
- corrected archive uploaded only with `SHA256SUMS` to the new Drive folder and public access checked;
- `/users/a/e/aereinh/CARE` server performed static provenance audit only, with Docker not run.
