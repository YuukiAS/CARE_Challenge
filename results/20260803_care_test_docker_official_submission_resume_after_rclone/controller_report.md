# CARE Docker Official Submission Resume After Rclone

本轮使用已完成的最终 Docker archives 和用户已配置的 `gdrive:`，完成 15+15 public validation 官方 `/input` 根目录黑盒彩排、逐病例标签体积审计、Drive 上传校验和英文邮件草稿更新。没有重新训练、重新构建、重新选择 checkpoint/fold/TTA，也没有修改 label map。

## Result

- controller_verification_decision: VERIFIED_COMPLETE
- MyoPS full public rehearsal: PASS, 15 outputs, runtime 1864.825 seconds
- CineMyoPS full public rehearsal: PASS, 15 outputs, runtime 1576.983 seconds
- Output completeness: PASS, no missing/duplicate/unknown cases
- Input readonly integrity: PASS
- Label volume audit: PASS
- MyoPS pathology positive voxels: {'1220': 21089, '2221': 13618}
- Cine pathology positive voxels: {'2221': 60766}
- Google Drive upload: PASS, remote size/hash verified
- Public link check: PASS, unauthenticated curl check passed
- Email draft: ready to send manually, not sent
- Forbidden uploads: no challenge data, no validation predictions

## Evidence

- `results/20260803_care_test_docker_official_submission_resume_after_rclone/official_full_rehearsal_summary.json`
- `results/20260803_care_test_docker_official_submission_resume_after_rclone/official_label_volume_summary.json`
- `results/20260803_care_test_docker_official_submission_resume_after_rclone/google_drive_upload_receipt.json`
- `results/20260803_care_test_docker_official_submission_resume_after_rclone/google_drive_public_access_receipt.json`
- `results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_email_draft.md`
