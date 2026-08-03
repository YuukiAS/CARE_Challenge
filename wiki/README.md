# CARE 架构 Wiki

architecture_version: `care-ase-r2-v8-pending-external-pretraining-review-20260803`
latest_verified_runtime: `CARE-ASE R2 v8 source/tests/G1 and diagnostic GPU code probes are complete; final formal training remains unauthorized`
latest_scientific_status: `PRETRAINING_EXTERNAL_REVIEW_REQUEST_READY_PENDING_PUSH: implementation source Commit A 648bb4d79da255438469aa9acfa939616aebf251; review packet Commit B reported after push; no formal training and no outer access`
latest_controller_task: `20260803_care_ase_r2_final_pretraining_closure_v8`
route_status: `MAIN_ONLY_CARE_ASE_R2_V8_PENDING_EXTERNAL_PRETRAINING_REVIEW`

当前 CARE-ASE R2 v8 只到训练前实现闭合与外部审阅请求阶段，不表示训练许可。v7 implementation `0b20e32d077227fbeb6611a3ee0cdf4231aee19d` 和 v7 review packet `7f4bb4d48e92273e2aad0a5d75ae6e4f3a62f1e7` 已被 v8 取代；v7 probe credit 为 zero。v8 formal training 未启动，fold1/fold4 outer access 均为 0；下一步只能由外部 GPT 审阅 v8 Commit A/B 后返回通过或返修。

关键证据：

```text
results/20260803_care_ase_r2_final_pretraining_closure_v8/pretraining_external_review_request.json
results/20260803_care_ase_r2_final_pretraining_closure_v8/controller_report.md
results/20260803_care_ase_r2_final_pretraining_closure_v8/completion_check.md
results/20260803_care_ase_r2_final_pretraining_closure_v8/MANIFEST.md
```

architecture_version: `care-test-docker-server-final-submission-readiness-confirmed-20260803`
latest_verified_runtime: `server final dist archive size/SHA, FULL 15+15 official rehearsal packet, Drive public links, and email draft independently audited on server`
latest_scientific_status: `READY_FOR_HUMAN_EMAIL_SEND: no model changes, no server Docker run, no challenge/validation prediction upload, organizer email draft ready but not sent`
latest_controller_task: `20260803_care_test_docker_server_final_submission_readiness_confirm`
route_status: `MAIN_ONLY_DOCKER_SUBMISSION_READY_FOR_HUMAN_EMAIL_SEND`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。服务器端已经只读确认最终提交资源：`/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist` 中的两个 Docker archive 与冻结 size/SHA 一致，最新 FULL 工位 packet 记录 MyoPS 15 例与 CineMyoPS 15 例官方 `/input` 根目录黑盒彩排通过，标签体积、输入只读完整性、合作者 MyoPS reference 接口边界、Google Drive 公链和英文邮件草稿全部通过。当前只授权用户人工发送已审计邮件；服务器没有运行 Docker，没有上传 challenge 或 validation predictions，也没有发送组织方邮件。

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

architecture_version: `care-test-docker-full-official-rehearsal-drive-staging-ready-20260803`
latest_verified_runtime: `final MyoPS and Cine Docker archives clean-loaded and passed official /input root black-box rehearsal on 15+15 public validation cases; Drive upload size/hash and public links verified`
latest_scientific_status: `FULL_OFFICIAL_REHEARSAL_AND_DRIVE_STAGING_PASS: no model changes, no challenge/validation prediction upload, organizer email draft ready but not sent`
latest_controller_task: `20260803_care_test_docker_official_submission_resume_after_rclone`
route_status: `MAIN_ONLY_FULL_OFFICIAL_REHEARSAL_DRIVE_STAGING_READY`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。最终 MyoPS 与 CineMyoPS archives 已从 clean archive load 后按 CARE 官方 `/input` 根目录结构完成 15+15 public validation 黑盒彩排。两项任务都恰好输出 15 个结果，逐病例路径、命名、NIfTI、标签集合、geometry、输入只读完整性和 anatomy/pathology label volume audit 全部通过。Google Drive 只上传最终 Docker archives 和 `SHA256SUMS`，远端 size/hash 与本地一致，公开链接未登录访问检查通过。英文邮件草稿已填入真实链接并可由人工发送；本任务没有发送邮件，也没有上传 challenge 或 validation predictions。

关键证据：

```text
results/20260803_care_test_docker_official_submission_resume_after_rclone/official_full_rehearsal_summary.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/official_label_volume_summary.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/google_drive_upload_receipt.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/google_drive_public_access_receipt.json
results/20260803_care_test_docker_official_submission_resume_after_rclone/strict_validator_report.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_email_draft.md
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_readiness.json
```

architecture_version: `care-test-docker-official-format-rehearsed-manual-drive-auth-20260803`
latest_verified_runtime: `final MyoPS and Cine Docker archives clean-loaded and passed official /input root black-box rehearsal on available sentinel cases; collaborator MyoPS reference interface passed; Drive upload needs manual rclone OAuth`
latest_scientific_status: `OFFICIAL_FORMAT_REHEARSAL_PASS_WITH_MANUAL_DRIVE_AUTH: outputs pass directory/name/NIfTI/label/geometry checks; no challenge/validation upload and no organizer email sent`
latest_controller_task: `20260803_care_test_docker_official_submission_rehearsal_and_staging`
route_status: `MAIN_ONLY_OFFICIAL_FORMAT_REHEARSED_MANUAL_DRIVE_AUTH`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。最终 MyoPS 与 CineMyoPS archives 已从 clean archive load 后按 CARE 官方 `/input` 根目录结构运行，当前可用 sentinel 为 MyoPS 3 例、Cine 3 例，因此只声明 available-sentinel 黑盒彩排通过，不声明 15/15 全量 public set。两个镜像的输出目录、文件名、NIfTI 可读性、标签集合和 geometry 检查通过；合作者 MyoPS reference 镜像只做接口对照，不做预测质量比较，最终 MyoPS tag 已恢复。Google Drive 上传尚未执行，因为 `rclone` 没有配置 Google Drive remote；英文邮件草稿已生成但未发送，也未标记 ready-to-send。未上传 challenge 或 validation predictions。

关键证据：

```text
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/official_submission_contract.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/official_command_rehearsal_summary.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/official_command_rehearsal_validation.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/collaborator_reference_interface_summary.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_readiness.json
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_email_draft.md
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/remote_rehearsal_packet_receipt.json
```

architecture_version: `care-ase-r2-v5-pending-external-pretraining-review-20260803`
latest_verified_runtime: `CARE-ASE R2 v5 implementation repair, G1/G2 fidelity evidence, and continuous Reviewer RV5-D6/RV5-D7 internal review are complete; external pretraining review is still required`
latest_scientific_status: `PRETRAINING_EXTERNAL_REVIEW_REQUEST_READY: implementation source Commit A f4ecd049bb09a47c38305b932ef116d45b37c160; review packet Commit B 51b9c7bf307bf5b25cc502207b7d7384db9d1815; formal training not authorized`
latest_controller_task: `20260803_care_ase_r2_pretraining_fidelity_repair_v5`
route_status: `MAIN_ONLY_CARE_ASE_R2_V5_PENDING_EXTERNAL_PRETRAINING_REVIEW`

当前 CARE-ASE R2 v5 只到训练前实现忠实性审阅请求阶段。旧 fold2/fold3 CARE-ASE outer 结果属于历史实现，不代表 R2 v5 已获准训练，也不能作为当前 v5 的正式科学结论。当前 v5 的 `old_207f_runtime_credit` 和 `old_e987_runtime_credit` 均为 `zero`；fold1/fold4 formal training、outer access、validation/Docker/hosted upload 都仍未授权。下一步只能由外部 GPT 对 Commit B 中的轻量 evidence packet 审阅，并返回 `PRETRAINING_EXTERNAL_REVIEW_PASS` 或 `PRETRAINING_EXTERNAL_REVIEW_REVISE`。

关键证据：

```text
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/pretraining_external_review_request.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/implementation_gap_closure.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/g1_static_implementation_gate_receipt.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/g2_real_gpu_fidelity_receipt.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/reviewer_semantic/RV5-D6/review.json
results/20260803_care_ase_r2_pretraining_fidelity_repair_v5/reviewer_semantic/RV5-D7/review.json
```

architecture_version: `care-test-docker-final-workstation-validated-returned-20260803`
latest_verified_runtime: `WSL2 Docker Engine built MyoPS pure five-fold nnU-Net image, loaded byte-preserved collaborator Cine image, validated CPU smoke/determinism, saved/loaded clean archives, and returned final archives to server final dist`
latest_scientific_status: `FINAL_DOCKER_WORKSTATION_VALIDATED_RETURNED: MyoPS host equivalence PASS with documented Case1012 2-voxel stale expected-output override; Cine black-box CPU determinism PASS; no challenge/validation/netdisk upload and no organizer email`
latest_controller_task: `20260803_care_test_docker_workstation_build_validate_return`
route_status: `MAIN_ONLY_FINAL_DOCKER_VALIDATED_RETURNED`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。MyoPS 最终镜像 `care-myocardium-myops:organagent` 已在工位 WSL2 以纯五折 nnU-Net context 构建，镜像内确认存在 folds `0-4` 的 `checkpoint_best.pth`；CineMyoPS 最终镜像 `care-myocardium-cinemyops:organagent` 由合作者原字节 archive 直接 load。两个镜像均完成 CPU smoke、两次确定性和 clean save/load/run，最终 archives 已位于本地 dist 和服务器 final dist。MyoPS host equivalence 对 Case1012 存在 2 个 voxel 的旧 expected output 微差异，已按用户确认的服务器端 expected 输出更新原因显式记录为 override；Cine 仅报告黑盒运行、schema、geometry 和 determinism，不声称 host-equivalence Dice。未上传 challenge、validation、网盘，未给组织方发送邮件。

关键证据：

```text
results/20260803_care_test_docker_workstation_build_validate_return/bundle_verification.json
results/20260803_care_test_docker_workstation_build_validate_return/docker_installation_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/build_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/image_asset_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/myops_cpu_smoke_casewise.csv
results/20260803_care_test_docker_workstation_build_validate_return/myops_cpu_determinism_casewise.csv
results/20260803_care_test_docker_workstation_build_validate_return/myops_host_equivalence_casewise.csv
results/20260803_care_test_docker_workstation_build_validate_return/cine_cpu_smoke_casewise.csv
results/20260803_care_test_docker_workstation_build_validate_return/cine_cpu_determinism_casewise.csv
results/20260803_care_test_docker_workstation_build_validate_return/clean_save_load_run_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/remote_return_receipt.json
results/20260803_care_test_docker_workstation_build_validate_return/strict_validator_report.json
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist
```

architecture_version: `care-ase-final-model-fold2-fold3-outer-20260802`
latest_verified_runtime: `CARE-ASE fold2/fold3 fixed step14000 checkpoints reloaded with final-logit parity 0.0; W5 outer evaluation used tiled sliding-window average logits on 44 outer cases per fold`
latest_scientific_status: `CARE_ASE_VERIFIED_COMPLETE_NO_HOSTED_CLAIM: pooled fold2+fold3 outer Dice scar 0.5235 and pure-edema 0.7953; full same-split stock Dice/HD was not recomputed in this packet`
latest_controller_task: `20260801_care_ase_final_model`
route_status: `MAIN_ONLY_CARE_ASE_VERIFIED_COMPLETE_PENDING_FINAL_PUSH_NOTIFY`

当前 CARE-ASE 证据来自冻结的 fold2/fold3 `checkpoint_step14000.pt`，不是 inner 选择、阈值搜索或 hosted leaderboard。实现快照已在 W4.5 非阻塞提交并 push；W5 outer once 随后直接执行。两个 fold 的 checkpoint reload final logits 最大误差都是 `0.0`，freeze 前 outer access count 是 `0`。W5 使用全体积 tiled sliding-window average logits，fold2/fold3 各 44 个 outer case；pooled scar mean Dice `0.5235`，pure-edema mean Dice `0.7953`。该结果仍未授权 validation upload、Docker upload 或 hosted metric claim。

关键证据：

```text
results/20260801_care_ase_final_model/checkpoint_freeze_receipt.json
results/20260801_care_ase_final_model/full_reload_parity_receipt.json
results/20260801_care_ase_final_model/outer_access_audit_receipt.json
results/20260801_care_ase_final_model/w45_implementation_snapshot/w45_implementation_snapshot_push_receipt.json
results/20260801_care_ase_final_model/outer_eval/fold_2/evaluation_receipt.json
results/20260801_care_ase_final_model/outer_eval/fold_3/evaluation_receipt.json
results/20260801_care_ase_final_model/w5_aggregation_receipt.json
results/20260801_care_ase_final_model/module_intervention_outer.csv
results/20260801_care_ase_final_model/hard_case_atlas.md
```

当前生成图：

```text
wiki/figures/model-current.png
wiki/figures/model-gap.png
wiki/figures/execution-flow.png
```

architecture_version: `care-test-docker-myops-context-hotfix-workstation-handoff-20260803`
latest_verified_runtime: `b94d3f frozen model contract unchanged; MyoPS Dockerfile now copies models into /app/models; refreshed workstation transfer contains five nnU-Net checkpoints and byte-preserved collaborator Cine archive`
latest_scientific_status: `SERVER_BUNDLE_READY: workstation WSL can start Docker build/load/run/save; server did not run Docker, train, upload, or send organizer email`
latest_controller_task: `20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff`
route_status: `MAIN_ONLY_TEST_DOCKER_MYOPS_CONTEXT_HOTFIX_READY_FOR_WORKSTATION`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。`b94d3f916b04461d6b88a311959e0ed581e64555` 的模型合同保持不变：MyoPS 仍是 Dataset501 五折 nnU-Net，CineMyoPS 仍是合作者原字节 Docker archive。本次只修复 MyoPS Dockerfile 未把 bundle context `models/` 复制进 `/app/models` 的 packaging 缺口；新 transfer 已准备，Cine archive SHA 保持不变。服务器未运行 Docker，未训练，未上传 challenge/validation/网盘，未给组织方发送邮件。

关键证据：

```text
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/docker_context_hotfix_receipt.json
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/myops_bundle_manifest.json
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/cine_sentinel_manifest.json
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/strict_validator_report.json
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/transfer/WORKSTATION_HANDOFF.json
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/transfer/SERVER_BUNDLE_READY.json
```

## 2026-08-03 MyoPS context hotfix and workstation handoff ready

```text
result_root:
results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff

transfer:
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/transfer

fixed gap:
Dockerfile now includes COPY models /app/models

model contract:
unchanged from b94d3f916b04461d6b88a311959e0ed581e64555

MyoPS checkpoint count in bundle:
5

Cine sentinels:
Case1011, Case1006, Case1003

server_docker_run_performed:
false

strict validator:
PASS
```

## 2026-08-02 纯 nnU-Net MyoPS + 合作者 Cine bundle ready

```text
result_root:
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle

terminal_state:
SERVER_BUNDLE_READY

transfer:
/users/a/e/aereinh/.tmp/codex-CARE/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/transfer

MyoPS:
Dataset501_CAREMyoPS, nnUNetTrainer_500epochs, 3d_fullres, folds 0-4, checkpoint_best.pth, default TTA
raw label map 0->0, 1->200, 2->500, 3->600, 4->1220, 5->2221

CineMyoPS:
collaborator archive CineMyoPS-OrganAgent.tar.gz
sha256 c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136

collaborator MyoPS:
reference-only, not final
sha256 81d19bbefd8f7cca46aee32b31a774f16222b6146b9eab6bc7265a6c214de2ff

server_docker_run_performed:
false

strict validator:
PASS
```

## 2026-08-01 最终冻结模型服务器端 bundle ready

```text
result_root:
results/20260801_care_test_docker_final_model_freeze_and_bundle

terminal_state:
SERVER_BUNDLE_READY

transfer_bundle:
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/transfer_bundle

archive:
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/care2026_myocardium_final_model_freeze_transfer_bundle.tar.gz

archive_sha256:
46beb1a1e3af291cba55a05d382a5e3ffe4adf759f72349610421597bda734ea

source intervention:
PASS

strict validator:
PASS
```

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。这次已经按新合同纠正了上一轮过窄的阻塞口径：没有直接把完整六类数组 mismatch 当成终点，而是先按语义标签审计 production 会使用的 nnU-Net anatomy `1/2/3` 和 pure-edema `4`。审计结果是 package A 与上一轮 fresh replay 几何 15/15 一致，但 full array 4/15、一致的 used channels 也只有 4/15；11 个不一致病例合计 120 个体素差异，横跨 anatomy、pure edema、scar 和背景。三个冻结 variant 均没有 exact 复现 package A，因此历史 `0.6691` lineage 保持 `UNRESOLVED`，不得作 hosted claim。

随后本任务按合同把历史 lineage 和当前部署源分开：对 `checkpoint_best.pth + folds 0-4 + default TTA` 做第二次独立 15/15 fresh replay。两次当前部署源 replay 的 geometry 是 15/15，但 array 只有 7/15 一致，合计 13 个体素变化。这个状态触发合同允许的硬阻塞 `NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC`；因此没有生成 `SERVER_BUNDLE_READY.json`，没有让工位开始 Docker 构建，也没有上传网盘、validation、Docker 或给组织方发邮件。

关键证据：

```text
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_used_channel_equivalence_summary.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_replay_variant_decision.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_deployable_source_receipt.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_lineage_vs_deployment_decision.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/controller_report.md
```

## 2026-08-01 Docker provenance 纠偏后阻塞

```text
result_root:
results/20260801_care_test_docker_provenance_reconcile_and_bundle

terminal_state:
SERVER_BUNDLE_BLOCKED

blocking_token:
NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC

package A audit:
geometry equality 15/15
full array equality 4/15
used channels 1/2/3/4 equality 4/15
changed semantic voxels vs package A 120

variant replay:
v1 checkpoint_final default TTA NOT_EXACT
v2 checkpoint_best no TTA NOT_EXACT
v3 checkpoint_final no TTA NOT_EXACT

deployable repeat:
checkpoint_best folds0-4 default TTA
geometry equality 15/15
array equality 7/15
changed voxels 13
```

不得把 `NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC` 解释成历史 `0.6691` 已复现。下一步需要 GPT Planner 决定是否授权一个确定性部署模式或修订 bundle source 合同。

architecture_version: `care-test-docker-server-bundle-nnunet-mismatch-20260801`
latest_verified_runtime: `server-side fresh nnU-Net 5-fold replay completed 15 outputs; geometry matched package A 15/15, array matched 4/15; MoSAIC MyoPS diagnostic replay completed 15/15; Cine diagnostic stopped at 4/15 after upstream gate failure`
latest_scientific_status: `SERVER_BUNDLE_BLOCKED: workstation Docker bundle must not start because nnU-Net edema provenance was not reproduced`
latest_controller_task: `20260801_care_test_docker_server_bundle`
route_status: `MAIN_ONLY_TEST_DOCKER_SERVER_BUNDLE_RETURN_TO_PLANNER`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。服务器端跨机器 Docker bundle 任务已经绕开本机 Docker/rootless 限制，直接复用现有 GPU allocation 做 fresh inference 证据；但关键 nnU-Net hosted provenance gate 未通过：15 例 fresh 输出全部存在，几何全一致，数组只有 4/15 与历史 package A 一致。因此不能生成 `SERVER_BUNDLE_READY.json`，不能让工位开始构建/验证 Docker，也不能把历史 hosted edema 分数绑定到当前冻结权重。

关键证据：

```text
results/20260801_care_test_docker_server_bundle/fresh_nnunet_provenance_receipt.json
results/20260801_care_test_docker_server_bundle/fresh_nnunet_vs_historical_casewise.csv
results/20260801_care_test_docker_server_bundle/fresh_mosaic_replay_receipt.json
results/20260801_care_test_docker_server_bundle/controller_report.md
```

## 2026-08-01 服务器端跨机器 bundle 阻塞

```text
result_root:
results/20260801_care_test_docker_server_bundle

terminal_state:
SERVER_BUNDLE_BLOCKED

blocking_token:
NNUNET_PROVENANCE_REPLAY_MISMATCH

nnU-Net fresh replay:
15 outputs generated
15/15 geometry equality vs historical package A
4/15 array equality vs historical package A

MoSAIC diagnostic:
MyoPS 15/15 complete
CineMyoPS 4/15 partial, stopped after upstream nnU-Net hard gate failure
```

不得把该状态解释成 Docker submission readiness。不得生成或上传 Docker archive，不得给组织方发邮件；后续需要 GPT Planner 决定是否追溯历史 package A 生成环境或修订合同。

architecture_version: `care-test-docker-rootless-prerequisite-blocked-20260801`
latest_verified_runtime: `rootless Docker prerequisite audit completed; official rootless installer downloaded but not executed because /etc/subuid and /etc/subgid have no current-user range for aereinh`
latest_scientific_status: `ROOTLESS_DOCKER_PREREQUISITE_BLOCKED: Docker packaging did not reach inference, image build, export, upload, or hosted metric stages`
latest_controller_task: `20260801_care_test_docker_rootless_unblock`
route_status: `MAIN_ONLY_TEST_DOCKER_RUNTIME_BLOCKED_RETURN_TO_PLANNER`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。这次测试 Docker unblock 已经把旧的“docker command not found”粗粒度阻塞细化为 rootless Docker 主机前提阻塞：user namespace、uidmap 二进制和本地 `/tmp` data root 可用，但 `/etc/subuid` 与 `/etc/subgid` 没有给 `aereinh` 配置至少 65536 的 subordinate ID 范围。由于任务禁止 sudo 和系统级安装，Docker build/load/run/save、CPU smoke、host/Docker 等价验证、tar.gz 导出和邮件草稿都没有启动。

关键证据：

```text
results/20260801_care_test_docker_rootless_unblock/rootless_prerequisite_audit.json
results/20260801_care_test_docker_rootless_unblock/rootless_storage_receipt.json
results/20260801_care_test_docker_rootless_unblock/rootless_install_receipt.json
results/20260801_care_test_docker_rootless_unblock/controller_report.md
results/20260801_care_test_docker_rootless_unblock/strict_validator_report.json
```

## 2026-08-01 测试 Docker rootless 前提阻塞

```text
result_root:
results/20260801_care_test_docker_rootless_unblock

terminal_state:
ROOTLESS_DOCKER_PREREQUISITE_BLOCKED

hard requirement failure:
subuid_total 0
subgid_total 0

passed host checks:
unshare -Ur true passed
newuidmap exists
newgidmap exists
/tmp/aereinh/care-rootless-docker-data selected on xfs

official installer:
downloaded and SHA256 recorded
not executed after hard prerequisite failure
```

不得把该状态解释成 Docker submission readiness，也不得上传 Docker、给组织方发邮件或作 hosted metric claim。管理员补齐 `/etc/subuid` 和 `/etc/subgid` 后，才能从该 controller 合同 W1 重新跑。

architecture_version: `care-four-lane-evidence-reconciled-no-candidate-20260801`
latest_verified_runtime: `M0R/M1/M2/M3 frozen fold2+fold3 evidence reconciled; same-case stock comparison complete; M2 outer replay complete; physical-space metric correction complete`
latest_scientific_status: `FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE: M0R did not beat same-case stock on outer scar or edema, and M2 did not pass scar/edema packaging gates`
latest_controller_task: `20260801_care_four_lane_evidence_reconciliation`
route_status: `MAIN_ONLY_FOUR_LANE_RECONCILIATION_RETURN_TO_PLANNER`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。最新四模型证据纠偏已经完成：M0R 与同病例 stock nnU-Net 的 outer 对比为负，M2 补做 outer 后也没有达到候选门槛；M1/M3 的失败被归类为实现不忠实导致的负结果，而不是对应论文路线的科学失败。旧的 scar-only 候选说法已撤销；不得解释为 hosted validation claim，也不得自动上传 validation 或 Docker。

## 2026-08-01 四模型证据纠偏终态

```text
result_root:
results/20260801_care_four_lane_evidence_reconciliation

scientific_decision:
FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE

M0R same-case stock comparison:
scar Dice delta -0.0020118904817150174
pure-edema Dice delta -0.030114178203399733

M2 outer gate:
scar gate false, Dice delta -0.05011471399535905
pure-edema gate false, Dice delta 0.018926404811234976, harm fraction 0.46875

metric correction:
HD95 and exact HD are reported in mm from nnU-Net preprocessing properties; small lesion uses physical volume <1000 mm3.
```

关键证据：

```text
results/20260801_care_four_lane_evidence_reconciliation/controller_report.md
results/20260801_care_four_lane_evidence_reconciliation/four_lane_scientific_interpretation.md
results/20260801_care_four_lane_evidence_reconciliation/m0r_vs_stock_outer_summary.csv
results/20260801_care_four_lane_evidence_reconciliation/m2_vs_stock_outer_summary.csv
results/20260801_care_four_lane_evidence_reconciliation/strict_validator_report.json
```

## 2026-08-01 已撤销历史证据：目标域四模型缺口闭合曾标记候选

```text
result_root:
results/20260801_care_target_domain_race_gap_closure

scientific_decision:
superseded_scar_only_candidate_label

global scar source:
m0r_faithful_control checkpoint_step03500

global edema source:
m0r_faithful_control checkpoint_step04000

outer replay:
results/20260801_care_target_domain_race_gap_closure/outer_replay/outer_replay_receipt.json

outer summary:
scar Dice mean 0.6500, sensitivity mean 0.7264
edema Dice mean 0.4340, sensitivity mean 0.4124

sentinel atlas:
results/20260801_care_target_domain_race_gap_closure/outer_replay/sentinel_case_atlas.md
```

## 2026-08-01 目标域四模型缺口闭合历史继续执行证据

```text
result_root:
results/20260801_care_target_domain_race_gap_closure

controller report:
results/20260801_care_target_domain_race_gap_closure/controller_report.md

old M0 fidelity audit:
results/20260801_care_target_domain_race_gap_closure/m0_protocol_fidelity_audit.json
old_m0_classification: HIGH_LR_SHORT_FINETUNE_NEGATIVE

interactive allocation receipt:
results/20260801_care_target_domain_race_gap_closure/existing_interactive_receipt.json
usable_existing_interactive_allocation: true
job_id: 61220581
partition: htzhulab
node: g1807htzh01
gpu: NVIDIA H100 NVL

scientific decision:
results/20260801_care_target_domain_race_gap_closure/scientific_decision.json
scientific_decision: CONTROLLER_ACTIVE_CONTINUATION
previous_decision_superseded: OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST

scheduler receipt:
results/20260801_care_target_domain_race_gap_closure/scheduler_receipt.json
M3: fold2/fold3 complete 4000 steps
M0R: old fold2 job 61565286 and fold3 takeover PID 4039804 superseded; faithful fold2/fold3 rerun completed in interactive allocation 61220581; log logs/M0RGapLane_61220581_20260801_014519.log
M1: old fold jobs 61565288/61565289 cancelled; lane job 61576324 COMPLETED with 12 CPU/96G/12h
takeover monitor: PID 4185840 exited as M1_QUEUE_COMPLETED_NO_TAKEOVER_NEEDED, state results/20260801_care_target_domain_race_gap_closure/interactive_takeover_monitor_state.json
M2: source pinned; R50-ViT-B_16.npz and epoch_299.pth downloaded; released checkpoint GPU smoke PASS; Dataset501 adapter preflight PASS; lane job 61627615 COMPLETED_0_0; MyoPS380 dataset not downloaded

checkpoint asset manifest:
results/20260801_care_target_domain_race_gap_closure/checkpoint_reload_audit.json
status: PASS
M0R/M1/M2/M3: 500-step checkpoint grid complete; final/max-step checkpoint torch.load and SHA256 audit PASS

planner handoff:
results/20260801_care_target_domain_race_gap_closure/planner_gap_resolution_handoff.md
records remaining gaps, implementation plan, external asset locations, download commands, and hard boundaries

strict validator:
results/20260801_care_target_domain_race_gap_closure/strict_validator_report.json
bootstrap status: PASS after active-continuation update
```

不得把旧 W0 阻塞解释为四模型科学失败。继续该目标时必须复用 `61220581`，M3 先跑 interactive，M0R/M1/M2 在 preflight 后提交 `htzhulab` 队列；若 interactive 跑完而某条 lane 仍 pending，则取消一个 pending 作业并在 interactive 中串行接力。禁止私自 `salloc`、提交 a100/volta、访问 official validation、上传 validation/Docker 或作 hosted metric claim。

## 2026-07-31 MyoWall-IF 终态证据

CARE-MyoWall-IF 机制试验已完成 metric dependency、fold1 stock nnU-Net 资产冻结、fold1 train-derived pilot split、stock parity、实现/known-bad/final validator 和完整 `pilot_inner` predicted geometry gate。geometry gate 未通过：case geometry valid rate `0.84375` 低于 `>=0.95`，5th-percentile wall roundtrip Dice `0.7068920140479127` 低于 `>=0.90`；因此合同终态为 `STOP_GEOMETRY_NOT_RELIABLE`。C0/W1/W2/W3 8000-step formal training 未启动，fold1 outer 未读取，validation/Docker upload 未启动。

```text
result_root:
results/20260731_care_myowall_if_mechanism_pilot

terminal packet:
results/20260731_care_myowall_if_mechanism_pilot/controller_terminal_packet.json

strict validator:
results/20260731_care_myowall_if_mechanism_pilot/strict_validator_report.json
status: PASS
terminal_stop_validated: true

geometry gate:
results/20260731_care_myowall_if_mechanism_pilot/geometry_gate_report.json
formal_geometry_gate: FAIL
case_count: 32
case_geometry_valid_rate: 0.84375
median_wall_roundtrip_dice: 0.9998856896450612
fifth_percentile_wall_roundtrip_dice: 0.7068920140479127
median_roundtrip_hd95_mm: 0.0

stock parity:
results/20260731_care_myowall_if_mechanism_pilot/stock_parity_report.json
status: PASS
fp32_stock_logit_parity_max_abs_error: 0.0
argmax_changed_voxels: 0
```

## 2026-07-29 PRISM W3 终态证据

## 2026-07-29 W3 终态证据

```text
result_root:
results/20260729_care_prism_v2_backbone_repair_and_resume

W1/W2 validator:
results/20260729_care_prism_v2_backbone_repair_and_resume/w1_w2_strict_validator_report.json

W3 training:
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_training_summary.json
optimizer_steps: 6500
synthetic_credit_used: false

W3 checkpoint audit:
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_checkpoint_audit_report.json
audited_steps: 500,1000,1500,2000,2500,3000,3500,4000,4500,5000,5500,6000,6500

Inner selection:
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_inner_select_formal_v2/summary.json
checkpoint_count: 13
case_count: 35
selected_checkpoint: checkpoint_step03000.pt

Outer once:
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_outer_once_formal_v2/summary.json
case_count: 44
outer_accessed: true

Strict validator:
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_strict_validator_report.json
status: FAIL
failure_classification: CALIBRATION
```

## 当前权威

```text
prompts/tasks/20260729_care_prism_v2_backbone_and_w1_repair_amendment.md
prompts/tasks/20260729_care_prism_v2_backbone_repair_executor_plan.yaml
prompts/tasks/20260729_care_prism_v2_backbone_repair_controller.md
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
```

```text
549dc4aed1a74682f8d35932f3d4fc7b7d61f564  repair amendment
1f1f39264cf248fb11d0322f41d4fe4c2aae021d  repair executor plan
acbc44cea3c3d86882cd56e5faab5b1d72b642c6  repair controller
5269f9b909c3a123e5e39db12532e61a2d633f74  CURRENT repair state
```

## 冻结主干资产

```text
fold0:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth
sha256 8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111

fold1:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_final.pth
sha256 5310569ff62f2f9a6ff2bc7dd3754404140071427a2025caf5e25d2916cfe400

plans:
data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json
```

来源：

```text
results/20260727_care_dg_dual_pathology_validation/nnunet_oof_anchor_manifest.json
results/20260722_care_myops_batch9_reliable_label_distillation/standard_nnunet_baseline_contract.json
```

Controller 必须重新验证当前文件的 stat/hash；历史 manifest 不是文件存在替代品。禁止只按目录名搜索 `resenc`，禁止用 MMRD/Batch9 checkpoint 或新训练 ResEnc 代替。

## PRISM v2 目标结构

```text
[LGE,T2,C0] exact stock nnU-Net shared encoder
→ lightweight modality-private pyramids
→ scar/edema multi-scale soft retrieval
→ real top-down internal anatomy decoder
→ stop-gradient anatomy→pathology exchange
→ learned positive proposal + four-category safe-negative logits
→ full-volume continuous proposal/anatomy attention
→ independent multi-scale scar and edema refiners
→ direct edema-zone → scar priority → pure edema
```

Prototype 与 slice correspondence 都不是核心强依赖：prototype 默认关闭；slice correspondence 当前冻结 identity，除非以后真实实现并通过独立门。

## 当前部分实现的已知漏洞

1. `CAREPRISM.forward` 只把 level0 routed/anatomy features送入 refiner；深层共享主干和 level1–3 router/exchange没有进入最终 mask。
2. anatomy decoder只是逐尺度1×1 projection并从level0输出，不是真实 top-down decoder。
3. slice correspondence flag当前是no-op。
4. `care_prism_dataset.py`仍是synthetic-only，不能产生W2 real-case credit。
5. 正式训练、评价和packet validator脚本缺失。
6. surface与lesion/MIL仍是placeholder。
7. 四通道negative logits的target被写成全零，没有病种安全负空间类别监督。
8. burden heads仍是auxiliary-only，没有调制proposal或refiner。
9. prototype cross-case排除与完整状态尚未实现，因此保持关闭。

W1必须先修复这些问题，再进入W2。

## 执行门

```text
R0 actual stock checkpoint locate/stat/hash
→ R1 plan-driven stock network restore + W1 implementation closure
→ W2 400-step real-case zero-credit preflight
→ W3 fold0 6500-step all-checkpoint inner selection + one-time outer
→ W4 only after W3 pass: fold1 8000-step clean one-time outer
→ W5 terminal accounting / aggregation / validator / Mapper / local commit
```

共享主干验收：

```text
parameter-byte coverage >=0.99
FP32 per-scale max_abs_error <=1e-6
all declared deep scales causally affect final logits
```

实现、数据、OOM、cache、sampler、loss、resume、evaluation和validator缺陷必须在同一Controller目标内修复，不能再次包装为科学失败。

## 冻结历史结果

CARE-ARC W3仍保留为诊断负结果：scar/edema-zone相对nnU-Net Dice delta为 `-0.1805/-0.1554`，HD95与remote FP显著恶化；但它不能作为忠实ARC机制负结果，因为router、anatomy、coarse proposal和同折初始化均未真实闭环。

前一 blocked packet保留在：

```text
results/20260729_care_prism_fold0_fold1_v2
```

其训练credit为0，fold1 outer未访问。

## 资源与权限

只允许复用既有 allocation `61220581 / htzhulab / g1807htzh01`；若仍运行，GPU命令必须串行。禁止新Slurm job、写`/overflow/htzhu/CARE`、runtime push、validation/Docker upload、fold1 outer调参或二次评价。

## 2026-08-01 nnU-Net / MoSAIC complementarity closure

这次补上的不是新模型，而是一套冻结证据表：把 220 例 fair OOF、80 例 M10 机制诊断和 15 例 fresh validation no-GT disagreement 放在同一个可审计结果包里。可读结论是：nnU-Net 仍是更稳的底线；MoSAIC clean OOF 只在 scar 少数病例上显示有限互补，pure edema 没有显示可用互补；M10 只能解释机制，不能证明泛化。

```text
result_root:
results/20260801_care_nnunet_mosaic_complementarity_closure

strict_validator:
results/20260801_care_nnunet_mosaic_complementarity_closure/strict_validator_report.json

controller_report:
results/20260801_care_nnunet_mosaic_complementarity_closure/controller_report.md
```

Evidence files:

- `oof_complementarity_casewise.csv`: 220-case scar and 80-case pure-edema fair OOF comparison, with buckets and component fields.
- `oof_case_oracle_bounds.csv`: case-oracle upper bound only; not a selector.
- `m10_diagnostic_casewise.csv`: 80-case full-data M10 diagnostic, marked as not valid for generalization claims.
- `validation_disagreement_casewise.csv`: 15-case fresh validation pairwise disagreement only; no GT and no performance claim.
- `hard_case_bucket_index.csv`: hard-case index grouped by frozen OOF buckets.

Key numbers:

- scar all-case: nnU-Net mean Dice `0.561047`, MoSAIC clean OOF mean Dice `0.378168`, case-oracle gain `0.021954`, MoSAIC rescue fraction `18/220 = 0.081818`.
- pure edema T2-present 80-case: nnU-Net mean Dice `0.430812`, MoSAIC clean OOF mean Dice `0.052756`, case-oracle gain `0.002293`, MoSAIC rescue fraction `0/80`.

This closure does not authorize training, threshold tuning, case-level selector construction, validation upload, Docker upload, or hosted metric claims.
