# Controller report

第 1 次校准包已经在本地完成：它使用的是 Dataset501 的 folds 0-4 `checkpoint_best.pth` 五折 nnU-Net 强基线预测，而不是 fold0，也不是不存在的 fold_all 单模型。由于当前 interactive job 没有可见 GPU，并且用户明确要求不要再提交 Slurm job，本次没有重跑 GPU 推理，而是复用仓库里已由 CUDA 生成并记录为 folds 0-4 的 MyoPS 5-fold prediction tree；新的包只重建 submission tree、固定 Cine pathology-direct 分支、重新做标签/几何/哈希审计。这个包仍只是 calibration control，不是 CARE-SCF，也没有上传 validation。

## Evidence summary

- checkpoint audit: `results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_checkpoint_manifest.json`
- inference receipt: `results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_inference_receipt.json`
- package manifest: `results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_package_manifest.json`
- label audit: `results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_label_audit.json`
- geometry audit: `results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_geometry_audit.csv`
- strict validator: `results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/strict_validator_report.json`
- upload-ready ZIP: `results/submissions/care_myocardium_validation/upload_ready/20260726_nnunet5f_control__nnUNet5F-control/CARE-Myocardium-OrganAgent.zip`
- ZIP SHA256: `155b1997afc0ccdea77b210e880c7405db49be0bfc64f5331f86e97047238e62`

## Decision fields

controller_verification_decision: VERIFIED_COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PASS
contract_compliance_status: PASS
required_outputs_complete: true
validators_passed: true
all_jobs_terminal: not_applicable_no_new_slurm_submitted
aggregation_complete: true
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
route_promotion_decision: NOT_AUTHORIZED
route_negative_decision: NOT_AUTHORIZED
scientific_resolution_status: PLANNER_DECISION_REQUIRED
blocked_actions: validation_upload, docker_upload, hosted_metric_claim, CARE_SCF_execution, git_push
next_required_action: RETURN_TO_PLANNER_FOR_MANUAL_UPLOAD_DECISION
