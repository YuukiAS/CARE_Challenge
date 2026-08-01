当前不能把两个测试 Docker 交给用户手动提交：本地已经完成历史 nnU-Net edema 归属审计，但当前主机没有 Docker 命令，无法完成镜像构建、加载、运行、导出和 CPU 路径验证。正确做法是先提交这份阻塞证据给 Planner/用户，不上传网盘、不发组织方邮件，也不把 apptainer 或未运行的源码包装成 Docker 就绪。

# Controller Report

controller_verification_decision: OPERATIONALLY_BLOCKED
controller_run_status: COMPLETE_BLOCKED_PACKET
operational_completion_status: BLOCKED
experiment_adequacy_decision: NOT_A_TRAINING_TASK
route_promotion_decision: NOT_AUTHORIZED
route_negative_decision: NOT_AUTHORIZED
scientific_resolution_status: NOT_REVIEWED
diagnostic_publication_decision: LIGHTWEIGHT_BLOCKED_PACKET_ONLY
contract_compliance_status: BLOCKED_BY_RUNTIME
required_outputs_complete: BLOCKED_PACKET_COMPLETE
validators_passed: PASS_AFTER_FINAL_VALIDATOR
all_jobs_terminal: NOT_APPLICABLE_NO_SLURM
aggregation_complete: NOT_APPLICABLE_NO_TRAINING
git_commit_decision: COMMIT_BLOCKED_PACKET
git_push_decision: PUSH_MAIN_AFTER_COMMIT
published_files: results/20260801_care_test_docker_packaging/ lightweight packet and validator script
blocked_actions: Docker build/load/run/save; Docker tar.gz export; organizer email; cloud upload; validation upload; hosted metric claim
next_required_action: HUMAN_INTERVENTION_REQUIRED
reason_if_not_published: none after authorized commit/push
reason_if_no_route_promotion: task did not authorize route promotion or hosted metric claim

## Evidence Summary

- nnU-Net edema provenance status: `NNUNET_EDEMA_PROVENANCE_UNRESOLVED`
- package MyoPS voxel equality: `True`
- fresh rerun equality: `False`
- Docker available: `False`
- Docker command result: `docker command not found`
