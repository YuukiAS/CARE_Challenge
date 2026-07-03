# Review 20260703 Diagnostic Publication Gate

review_key: "20260703_diagnostic_publication_gate_review"
task_key: "20260703_diagnostic_publication_gate"
reviewer: "Codex self-check"
role: "implementation self-review"
read_only: false

## Scope Check

本次修改仅限 handoff/protocol/templates/validator/docs 和当前相关 controller
task 文本。未修改 label mapping、fold split、evaluator、训练逻辑、submission
packaging 逻辑或模型路线。

## Policy Check

- `route_promotion_gate` 已定义为 route promotion/fold expansion/validation
  packaging/upload/next-stage training 的 gate。
- `diagnostic_publication_gate` 已定义为无 route promotion 时发布 reviewed
  diagnostic packet 的 gate。
- `diagnostic_publication_scope` 已列出允许的最小发布范围。
- `blocked_after_diagnostic_publication` 已列出 publication 后仍禁止的动作。
- Diagnostic-only git/report 必须写明 `diagnostic publication only; no route promotion`。

## Forbidden Artifact Check

新增 validator 拒绝 diagnostic `published_files` 中的 checkpoint、prediction、
NIfTI、zip/upload package、heavy log、secret transcript、env dump、CSV、credential
和 `.env` 风险路径。未修改 `.gitignore`，未 unignore 整个 results tree。

## Residual Risk

旧历史任务中可能仍有 legacy `promotion_gate` 字段；新 validator 默认将其作为兼容
warning 处理，strict 模式可强制新字段。当前显式 git-enabled hardmode controller
task 已补齐新字段和 diagnostic-only git 语义。

## Self-Review Decision

`SUPPORTED`: 本补丁满足 diagnostic artifact publication gate 与 route promotion
gate 分离的协议目标。它不授权 validation upload、validation packaging、fold
expansion、hosted metric claim、label/evaluator/fold split change 或 next-stage
training。
