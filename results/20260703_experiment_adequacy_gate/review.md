# Review 20260703 Experiment Adequacy Gate

review_key: "20260703_experiment_adequacy_gate_review"
task_key: "20260703_experiment_adequacy_gate"
reviewer: "Codex self-check"
role: "implementation self-review"
read_only: false

## Scope Check

本次修改仅限 handoff/protocol/templates/validator/docs、当前 controller task 的协议字段、
以及本结果包。未修改 CARE scientific model implementation、label mapping、fold split、
evaluator、submission packaging、checkpoints、predictions、NIfTI 或 upload package。

## Gate Check

- `experiment_adequacy_gate` 已定义，并覆盖 one-batch/tiny-overfit、有效训练量、
  `train_loop_seconds`、`actual_steps`、`optimizer_steps`、`validation_events`、
  `loss_decrease`、prediction sanity、proposal sanity、logs/provenance 和 same-split
  baseline comparability。
- `route_negative_gate` 已定义；只有 adequacy PASS、无 forbidden substitute、同 split
  baseline、失败不能由 undertraining/pipeline/decode/cache/label/log 解释、并且 auditor
  明确支持时，才允许 route-negative scientific stop。
- `scientific_resolution_status` 已与 `controller_run_status` 和
  `operational_completion_status` 分开。

## Validator Check

新增/更新的 validator 规则覆盖：

- controller report 必须包含 operational status 和 scientific status；
- route-negative/STOP_NO_* 需要 `experiment_adequacy_decision: PASS` 和
  `route_negative_decision: STOP_SUPPORTED`；
- `controller_run_status: COMPLETE` 且 `SCIENTIFIC_UNRESOLVED` 时必须写
  `next_required_action`；
- review 支持 route-negative stop 时必须包含 training adequacy evidence fields。

## Self-Review Decision

`SUPPORTED`: 本补丁满足目标。以后 controller 可以 operationally complete，但若训练不充分，
scientific status 必须是 undertrained/unresolved/needs evidence/revision/pipeline bug，而不能把
短训或 smoke 直接写成 `STOP_NO_SIGNAL` 类科学负结论。
