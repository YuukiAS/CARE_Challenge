---
task_key: 20260805_care_myops_single_slice_hotfix_resume_authorization_addendum
task_kind: hotfix
task_type: submission_runtime_hotfix_resume
status: AUTHORIZED_BY_USER
branch_policy: main-only
precedence: overrides_conflicting_geometry_failure_mode_upload_and_server_access_fields_in_prior_single_slice_hotfix_tasks
model_change_authorized: false
training_authorized: false
corrected_docker_drive_upload_authorized: true
organizer_email_send_authorized: false
challenge_upload_authorized: false
validation_prediction_upload_authorized: false
---

# MyoPS single-slice hotfix resume authorization

This addendum resumes the blocked goal defined by:

- `prompts/tasks/20260805_care_myops_single_slice_hotfix_repackage_controller.md`
- `prompts/tasks/20260805_care_myops_single_slice_hotfix_provenance_addendum.md`

It does not authorize a new model, retraining, a new checkpoint, or organizer email delivery.

## 1. Geometry-mismatch synthetic case is not a blocking gate

The organizer reported a valid single-slice input failure caused by nnU-Net resampling producing a zero-size spatial dimension. The current corrected image has already reproduced and repaired that failure family.

A deliberately malformed case whose LGE, T2, and C0 files have inconsistent shape, spacing, origin, or direction is outside the frozen official valid-input contract used by this runtime-only correction. The previously submitted wrapper did not perform a cross-modality geometry preflight and may accept such malformed input. This inherited behavior is not evidence that the single-slice clamp failed.

For this goal:

- keep `/app/predict.py`, `/app/entrypoint.sh`, `requirements.lock`, model weights, plans, dataset metadata, dependencies, ENTRYPOINT, Cmd and Env unchanged;
- do not add a new geometry-rejection wrapper or preflight;
- record the malformed geometry test as `INHERITED_BASE_BEHAVIOR_OUT_OF_SCOPE_NONBLOCKING`;
- require that all valid aligned depth-1/depth-2 synthetic cases preserve exact input geometry;
- require 15/15 normal public cases to remain bitwise and geometrically identical between base and corrected images;
- require mixed valid normal-plus-single-slice batches to complete without a missing output.

The geometry-mismatch result must remain visible in the evidence packet as a documented inherited limitation. It must not be reported as fixed, and it must not block the corrected single-slice organizer artifact.

## 2. Google Drive upload is explicitly authorized

The user explicitly authorizes uploading only the corrected MyoPS Docker archive and its SHA256 manifest to a new non-overwriting directory:

`gdrive:/CARE2026_Myocardium_MyoPS_Corrected_20260805/`

Authorized files:

- `MyoPS-OrganAgent-corrected.tar.gz`
- `SHA256SUMS`

Current corrected archive frozen by the workstation result:

```text
path: /home/yuukias/code/CARE/dist/20260805_care_myops_single_slice_hotfix/MyoPS-OrganAgent-corrected.tar.gz
sha256: fcf1c67a2123ab655a8e6c32dc46e6d98feaa43f41c698c6969aebfaa51f79ff
```

Before upload, re-run local `stat`, SHA256 verification and the final strict validator. Do not overwrite or delete the previously submitted MyoPS archive. Do not upload predictions, validation data, GT, checkpoints, logs, packets containing secrets, or CineMyoPS.

After upload, require remote size/hash verification, a new public link, and an unauthenticated HTTP access check. Do not read, print, commit or return `rclone.conf`, tokens or secrets.

## 3. Server paths are remote from WSL

`/users/a/e/aereinh/CARE` is not expected to exist as a local WSL path. Its absence in the WSL filesystem is not a server outage.

From WSL, discover the unique SSH alias in `~/.ssh/config` for which this remote probe succeeds:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <alias> '
  test -d /users/a/e/aereinh/CARE &&
  test -d /users/a/e/aereinh/.tmp/codex-CARE
'
```

Use that alias as `CARE_SERVER`. All server access must use `ssh`, `rsync` or `scp`, for example:

```bash
ssh "$CARE_SERVER" 'test -d /users/a/e/aereinh/CARE'
rsync -ahP --partial --append-verify <local-file> "$CARE_SERVER:<remote-directory>/"
```

Do not test the remote `/users/...` path with local WSL `test -d` and do not classify that expected local absence as `SERVER_UNAVAILABLE`.

If no SSH alias succeeds after bounded retries, preserve the completed local and Drive evidence, push the lightweight task packet, write `WAITING_FOR_REMOTE_SERVER_AUDIT`, and send the existing internal notifier with `final_status: blocked`. Do not send an organizer email.

## 4. Resume completion conditions

The existing completed evidence may be reused only after hashes and receipts are revalidated. The resumed goal must:

1. re-run the strict validator with the geometry-mismatch case classified as the named nonblocking inherited behavior;
2. upload the corrected archive and manifest to the authorized new Drive directory;
3. verify public access and bind the link to archive size/SHA;
4. transfer the corrected archive and lightweight packet to the server through SSH;
5. run the independent server-side static provenance audit without Docker;
6. commit and push only lightweight source/receipts/state files to `origin/main`;
7. call the existing CARE notifier after terminal completion or a genuine remote-access block;
8. never send the organizer email.

Only the server-audited terminal token below authorizes returning the corrected link to the user:

`CORRECTED_MYOPS_RUNTIME_ONLY_HOTFIX_READY_FOR_ORGANIZER_REEVALUATION`
