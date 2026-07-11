# Generic Agent-Flow Protocol Repair

task_key: `20260711_agent_flow_generic_protocol_repair`

controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: NOT_APPLICABLE
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_PACKET_COMMITTED_FOR_REVIEW
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH

## Summary

本次只修复通用 handoff 协议层，不读取、修改或执行具体科学 milestone 设计。

主要改动：

- 新增 `prompts/schemas/*.yaml` 和 `prompts/ACTIVE_POLICY_FILES.yaml`，把 active roles、planning review、staging、executor plan、controller packet、runtime review schema 统一为 machine-readable source。
- 将 `validate_handoff_policy.py` 拆成 `--policy`、`--candidate`、`--packet`、`--repository-readiness` 模式。
- 新增 `scripts/validation/hash_milestone_contract.py` 和 `scripts/agent_flow/milestone_id.py`。
- 将 active roles 统一为 `planner`、`critic`、`controller`、`executor`、`mapper`、`finalizer`、`validator`、`reviewer`。
- 将 wiki current review source 改为 `wiki/current_state.yaml`，移除 generic validator 中固定 review token。
- 将 history generator 改为读取 `annotations.yaml` 和动态 predecessor delta。
- 将 executor-wave receipt 改为 task-local路径，并加强 merge/prepare 的 task hash、completion token 和 clean-worktree gates。

## Boundaries

- No model code was modified.
- No M10 scientific design was read, modified, completed, or executed.
- No training or ordinary Slurm training job was submitted.
- No historical M8/M9 result packet was modified.
- No `review.md` was written.
- No push was performed.

next_required_action: separate reviewer reads this packet and writes `review.md`.
