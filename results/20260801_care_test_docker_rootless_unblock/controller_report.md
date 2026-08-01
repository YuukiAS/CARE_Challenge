当前不能继续构建或导出 CARE 测试 Docker：这台服务器允许创建 user namespace，也有 `newuidmap/newgidmap`，本地 `/tmp` 也可作为 Docker layer store；真正缺的是管理员在 `/etc/subuid` 和 `/etc/subgid` 给 `aereinh` 分配的 subordinate uid/gid 范围。没有这个范围，官方 rootless Docker 安装脚本会要求修改系统文件，而本任务明确禁止 sudo 和系统级安装，所以正确终态是把这个可修复的主机前提阻塞提交给 GPT/用户，而不是假装 Docker 已就绪。

# Controller Report

controller_verification_decision: OPERATIONALLY_BLOCKED
controller_run_status: COMPLETE_BLOCKED_PACKET
operational_completion_status: BLOCKED
terminal_state: ROOTLESS_DOCKER_PREREQUISITE_BLOCKED
experiment_adequacy_decision: NOT_A_TRAINING_TASK
contract_compliance_status: BLOCKED_AT_W1_AFTER_REQUIRED_PREREQUISITE_AUDIT
required_outputs_complete: BLOCKED_PACKET_COMPLETE
validators_passed: PASS
all_jobs_terminal: NOT_APPLICABLE_NO_SLURM_JOB_USED
aggregation_complete: NOT_APPLICABLE_BLOCKED_BEFORE_INFERENCE
git_commit_decision: COMMIT_BLOCKED_PACKET
git_push_decision: PUSH_MAIN_AFTER_COMMIT
route_promotion_decision: NOT_AUTHORIZED
route_negative_decision: NOT_AUTHORIZED
scientific_resolution_status: NOT_STARTED_FOR_DOCKER_OUTPUTS
diagnostic_publication_decision: LIGHTWEIGHT_BLOCKED_PACKET_ONLY
blocked_actions: rootless Docker install/start; Docker build/load/run/save; nnU-Net fresh replay; MoSAIC replay; tar.gz export; organizer email send; cloud upload; hosted metric claim
next_required_action: HUMAN_INTERVENTION_REQUIRED

## Evidence

- rootless prerequisite audit: `results/20260801_care_test_docker_rootless_unblock/rootless_prerequisite_audit.json`
- storage receipt: `results/20260801_care_test_docker_rootless_unblock/rootless_storage_receipt.json`
- official installer receipt: `results/20260801_care_test_docker_rootless_unblock/rootless_install_receipt.json`
- admin fix note: `results/20260801_care_test_docker_rootless_unblock/rootless_admin_fix_required.md`

## Key Machine Facts

```text
unprivileged_user_namespace_works: True
newuidmap_exists: True
newgidmap_exists: True
subuid_total: 0
subgid_total: 0
selected_docker_data_root: /tmp/aereinh/care-rootless-docker-data
official_installer_downloaded: True
official_installer_sha256: f019d4d3ef4efe3c8545f177e134d88beec0fae46e9ea27374ddd5e98d616df7
```
