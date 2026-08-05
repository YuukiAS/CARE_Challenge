旧 MyoPS Docker 的单层输入崩溃已经先复现、再修复、再通过本地和服务器双层 provenance 审计。科学含义很直接：这不是一次模型更新，而是对已提交 nnU-Net runtime preprocessing 的最小防崩保护；普通 15 例输出逐体素完全不变，所以 corrected archive 可以用于请求组织方重新评估 MyoPS，但仍需要用户人工发送回复，Codex 没有发邮件。

## Evidence Summary

- Base archive exact: size `4741640359`, SHA256 `638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b`, image ID `sha256:52f8d872a51c482d488e3d2a14893958a6b1d6c8c91fffed9985ee330fcec911`.
- Old failure reproduced: direct old `compute_new_shape` produced zero dimension; old image Docker run exited `1` with divide-by-zero/zero-size evidence.
- Patch scope: `compute_new_shape` preserves original rounding then applies `np.maximum(new_shape, 1)`.
- Corrected image ID: `sha256:511e16d6e3d660044e34ebee94cad7d897c5526246cf789fc2e9e858f3428c8d`.
- Corrected archive: `/home/yuukias/code/CARE/dist/20260805_care_myops_single_slice_hotfix/MyoPS-OrganAgent-corrected.tar.gz`, size `4742235545`, SHA256 `fcf1c67a2123ab655a8e6c32dc46e6d98feaa43f41c698c6969aebfaa51f79ff`.
- Model invariance: checkpoint hashes, plans/dataset, `predict.py`, `entrypoint.sh`, `requirements.lock`, pip freeze, entrypoint/cmd/env, and rootfs prefix all pass.
- Functional gates: synthetic depth1/depth2 `13/13` PASS, normal exact regression `15/15` PASS, mixed batch `28/28` PASS, determinism subset PASS, clean save/load plus full synthetic rerun PASS.
- Failure-mode expansion: `geometry_mismatch` is recorded as `INHERITED_BASE_BEHAVIOR_OUT_OF_SCOPE_NONBLOCKING`; no wrapper or model change was made for malformed cross-modality geometry.
- Drive upload: only `MyoPS-OrganAgent-corrected.tar.gz` and `SHA256SUMS` uploaded to `gdrive:/CARE2026_Myocardium_MyoPS_Corrected_20260805/`.
- Public link: `https://drive.google.com/open?id=1ATXgeTn99xFZAB3SLH1-aSpTuIb5EO5a`; unauthenticated HTTP check returned final `200`.
- Server audit: `/users/a/e/aereinh/CARE` ran static provenance audit only, did not run Docker, and returned `CORRECTED_MYOPS_RUNTIME_ONLY_HOTFIX_READY_FOR_ORGANIZER_REEVALUATION`.

## Machine Fields

controller_verification_decision: VERIFIED_COMPLETE
operational_completion_status: CORRECTED_MYOPS_RUNTIME_ONLY_HOTFIX_READY_FOR_ORGANIZER_REEVALUATION
experiment_adequacy_decision: NOT_APPLICABLE_NO_TRAINING
contract_compliance_status: MODEL_AND_INFERENCE_CONTRACT_UNCHANGED
required_outputs_complete: true
validators_passed: true
all_jobs_terminal: true
aggregation_complete: true
git_commit_decision: PENDING_LIGHTWEIGHT_COMMIT
git_push_decision: PENDING_LIGHTWEIGHT_PUSH
organizer_email_sent: false
next_required_action: COMMIT_PUSH_NOTIFY
