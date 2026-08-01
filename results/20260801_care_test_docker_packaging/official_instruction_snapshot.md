# CARE 2026 Myocardium Test Docker Instruction Snapshot

snapshot_time_utc: 2026-08-01T12:15:42.273460+00:00
source_urls:
- https://www.zmic.org.cn/care_2026/test_submission/
- https://www.zmic.org.cn/care_2026/instruction_myocardium/

## Snapshot Summary

The public test-submission page states that CARE 2026 uses Docker for the test phase so organizers can run participant methods on the hidden test set. The Myocardium instruction page requires email submission of a Docker image archive download link for each participating task.

## Myocardium Requirements Captured

- submission channel: email to `care26challenge@163.com` or `care2026challenge@outlook.com`
- subject: `[CARE-Myocardium Test] Team-Name – Docker Submission`
- email body: download link, run command or extra instructions, and task name
- tasks: `MyoPS` and `CineMyoPS`
- input mount: `/input` read-only
- output mount: `/output`
- MyoPS input shape: `/input/myops/Case*_C0.nii.gz`, `Case*_LGE.nii.gz`, `Case*_T2.nii.gz`
- CineMyoPS input shape: `/input/cinemyops/Case*_Cine.nii.gz`
- MyoPS output shape: `/output/myops/Case*_pred.nii.gz`
- CineMyoPS output shape: `/output/cinemyops/Case*_pred.nii.gz`
- non-interactive execution is expected
- CPU-only execution is preferred; GPU requests must be explained
- up to 3 successful submissions are allowed per task; failed runs do not count
- first successful submission receives metric feedback
- separate Docker images are required when participating in multiple tasks
- deadline: `2026-08-03 23:59 PST`

## Controller Boundary

This packet did not upload Docker archives, did not upload validation predictions, and did not send an organizer email.
