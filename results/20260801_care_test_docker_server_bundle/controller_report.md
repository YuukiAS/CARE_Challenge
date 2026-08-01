这次服务器端可以继续工作到 fresh inference 证据层，但不能生成给工位执行的 Docker bundle：5-fold nnU-Net 确实 fresh 跑出了 15/15，几何也全部一致，可是只有 4/15 病例与历史 package A 的数组完全一致。合同把这定义为 `NNUNET_PROVENANCE_REPLAY_MISMATCH`，因此不能把历史 0.6691 edema 归属绑定到当前冻结权重，也不能启动 MyoPS 可执行 bundle 或写 `SERVER_BUNDLE_READY.json`。

# Controller Report

controller_verification_decision: OPERATIONALLY_BLOCKED
controller_run_status: COMPLETE_BLOCKED_PACKET
operational_completion_status: BLOCKED
terminal_state: SERVER_BUNDLE_BLOCKED
blocking_token: NNUNET_PROVENANCE_REPLAY_MISMATCH
experiment_adequacy_decision: FROZEN_INFERENCE_RERUN_COMPLETE_FOR_NNUNET
contract_compliance_status: FAIL_CLOSED_AT_NNUNET_PROVENANCE_GATE
required_outputs_complete: BLOCKED_PACKET_COMPLETE
validators_passed: PASS
all_jobs_terminal: NO_NEW_SLURM_JOB_SUBMITTED_EXISTING_ALLOCATION_USED
aggregation_complete: NNUNET_COMPARISON_COMPLETE
git_commit_decision: COMMIT_BLOCKED_PACKET
git_push_decision: PUSH_MAIN_AFTER_COMMIT
route_promotion_decision: NOT_AUTHORIZED
scientific_resolution_status: PROVENANCE_UNRESOLVED_FOR_MYOPS_BUNDLE
blocked_actions: MyoPS executable bundle; SERVER_BUNDLE_READY.json; workstation start; Docker archive claim; organizer email; upload; hosted metric claim
next_required_action: RETURN_TO_PLANNER

## Evidence

- `results/20260801_care_test_docker_server_bundle/fresh_nnunet_provenance_receipt.json`
- `results/20260801_care_test_docker_server_bundle/fresh_nnunet_vs_historical_casewise.csv`
- `/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/SERVER_BUNDLE_BLOCKED.json`

## MoSAIC Diagnostic Replay

```text
myops_complete_15_of_15: True
cinemyops_complete_15_of_15: False
cinemyops_case_count: 4
cinemyops_stop_reason: stopped by controller after upstream nnU-Net gate failure made SERVER_BUNDLE_READY impossible
```
