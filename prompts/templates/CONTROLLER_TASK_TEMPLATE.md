---
task_key: "YYYYMMDD_short_slug"
project: "CARE_Challenge"
status: "READY"
task_type: "controller"
controller_mode: true
execution_mode: "controller_supervised"
requires_execution_controller: true
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
controller: "Codex controller session"
executor: "separate Codex executor session/subagent"
executor_slots: 1
mapper: "separate read-only Codex mapper session/subagent"
mapper_slots: 1
mapper_required: true
architecture_impact: "component"
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: false
continuity_backend: "none"
review_mode: "independent_thread"
reviewer: "separate_readonly"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "segmentation | registration | cine_temporal | missing_modality | proposal_refinement | external_adapter | submission_packaging"
target_metric: "myops_scar | myops_edema | myocardium_cinemyops | explicitly caveated local proxy"
required_evidence: ["executor_result", "mapper_report_if_required", "finalizer_state_if_required", "validator_report", "reviewer_review", "controller_report", "experiment_adequacy_gate_evidence", "route_promotion_gate_evidence", "route_negative_gate_evidence", "diagnostic_publication_gate_evidence"]
forbidden_substitutes: ["controller inventing a new route", "executor self-review", "audit bypass", "missing result directory ignored", "similar required filename accepted", "strict validator errors swallowed", "final audit without completion-check readiness", "smoke-scale training treated as full route evidence", "unauthorized fold expansion or upload"]
promotion_gate: "All executor claims audited; CARE overlay and skill gates satisfied; no human-approval block."
route_promotion_gate: "All executor claims audited; CARE overlay and skill gates satisfied; no human-approval block."
hard_gate_policy: "Before final audit or completion, enforce prompts/HANDOFF_GATE_POLICY.md: exact ordered task graph, exact results/<task_key>/ directories, exact required filenames, strict validator nonzero on errors, completion-check readiness, controller report terminal fields, minimum effective training classification, and current bad packet regression when applicable."
minimum_effective_training:
  min_optimizer_steps: 0
  min_train_loop_seconds: 0
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  allow_stop_without_training: false
experiment_adequacy_gate: "Training/model route adequacy requires sufficient optimizer steps/train_loop_seconds, one-batch/tiny-overfit when applicable, loss decrease, prediction/proposal sanity, logs/provenance, cache isolation, and same-split baseline comparability."
route_negative_gate: "STOP_NO_* route-negative conclusions require experiment_adequacy_decision PASS plus explicit auditor approval that failure is not due to undertraining, smoke/preflight, decode/cache/label/log/pipeline issues."
scientific_completion_gate: "Scientific completion requires SCIENTIFIC_PROMOTED or SCIENTIFIC_STOP_SUPPORTED; controller operational completion alone is insufficient."
diagnostic_publication_gate: "Audited diagnostic code/report artifacts may be committed even when no route is promoted."
diagnostic_publication_scope: ["controller_report", "execution_plan", "subtask_result_review", "small_reviewed_markdown", "reviewed_repro_scripts"]
blocked_after_diagnostic_publication: ["validation_upload", "validation_packaging", "fold_expansion", "hosted_metric_claim", "label_or_evaluator_or_fold_split_change", "next_stage_training"]
failure_escalation_policy: "Escalate inside this policy only; new scientific direction requires NEEDS_GPT_PLANNER."
executor_subtasks: ["results/<task_key>/subagents/executor_prompt.md"]
mapper_subtasks: ["results/<task_key>/subagents/mapper_prompt.md"]
reviewer_prompt_path: "results/<task_key>/subagents/reviewer_prompt.md"
controller_report_path: "results/<task_key>/controller_report.md"
allowed_next_states: ["EXECUTION_PLANNED", "EXECUTOR_RUNNING", "MAPPER_DRAFT_RUNNING", "FINALIZER_RUNNING", "MAPPER_FINAL_RUNNING", "EXECUTED_UNAUDITED", "REVIEWER_RUNNING", "AUDITED_GO", "AUDITED_DIAGNOSTIC_PUBLISH", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_MONITOR", "NEEDS_SUBAGENT_LAUNCH", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
allow_diagnostic_commit: true
allow_diagnostic_push: true
---

# CARE Controller Task: <short title>

## Goal
State the CARE objective, target metric, and authorized mechanism route. The controller may supervise execution only inside this GPT-authored scope.

## Workflow
1. GPT planner writes this controller task.
2. User starts a Codex controller session and gives it this task.
3. The controller enforces `prompts/HANDOFF_GATE_POLICY.md` before any final audit or completion decision.
4. The controller creates or launches a separate executor session and, when enabled, a separate read-only mapper session.
5. Executor writes `result.md` and artifact paths.
6. Finalizer performs terminal accounting, aggregation, validation, wiki finalization if required, and commit if authorized.
7. Controller writes `results/<task_key>/controller_report.md` with subtask paths, session/log evidence, finalizer/validator status, controller run status, operational completion status, experiment adequacy decision, route promotion decision, route negative decision, scientific resolution status, diagnostic publication decision, git action status, published files, blocked actions, next required action, and reasons for no route promotion or no publication.
8. A separate read-only reviewer reads the final committed packet and writes `review.md`.
9. GPT strategic controller reads the controller report and review before choosing the next CARE direction.

## Subagent Fallback
If the Codex runtime cannot automatically launch subagents or new sessions, write `results/<task_key>/subagents/executor_prompt.md`, `results/<task_key>/subagents/mapper_prompt.md` when mapper is required, and `results/<task_key>/subagents/reviewer_prompt.md`, set state to `NEEDS_SUBAGENT_LAUNCH` or `NEEDS_HUMAN_APPROVAL`, and stop. Do not pretend executor/mapper/reviewer separation happened.

## CARE Gate References
Use the Bridge Kit controller protocol for state and report structure. Use `prompts/HANDOFF_GATE_POLICY.md` for exact task graph, strict validator, completion-check-before-final-audit, report schema, and smoke-scale evidence gates. GPT planners should apply `prompts/GPT_HARD_GATE_PROMPT.md` before writing high-risk controller goals. Use the medical-imaging skill for generic mechanism completion. Use `prompts/CARE_OVERLAY_GATES.md` for CARE leaderboard, label/export, T2-edema, Cine, controller, submission, and failure-escalation constraints.

## Git Policy
CARE controller commit/push is not the Bridge Kit default. Commit only if `allow_git_commit: true`, push only if `allow_git_push: true`, and only after audit/re-audit plus either `route_promotion_gate` approval or `diagnostic_publication_gate` approval. Diagnostic commits must say `diagnostic publication only; no route promotion`. Record skipped git actions and reasons in the controller report.

Diagnostic publication does not promote a model route. After diagnostic publication, validation packaging/upload, fold expansion, hosted metric claims, label/evaluator/fold split changes, and next-stage training remain blocked unless another explicit task authorizes them through route promotion.

## Scientific Status Policy
Controller operational completion is not scientific completion. Do not write `STOP_NO_SIGNAL`, `STOP_NO_PROPREF_SIGNAL`, `STOP_NO_CLEAN_ANCHOR_SIGNAL`, `STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL`, or equivalent route-negative stops unless `experiment_adequacy_decision: PASS`, `route_negative_decision: STOP_SUPPORTED`, and auditor support are present. Undertrained or evidence-missing routes must use `SCIENTIFIC_UNDERTRAINED`, `SCIENTIFIC_UNRESOLVED`, `SCIENTIFIC_NEEDS_EVIDENCE`, `SCIENTIFIC_NEEDS_REVISION`, or `SCIENTIFIC_PIPELINE_BUG`.

## Controller Report Required Ending
End `controller_report.md` with these fields:

```text
controller_run_status: COMPLETE | INCOMPLETE | BLOCKED
operational_completion_status: COMPLETE | INCOMPLETE
experiment_adequacy_decision: PASS | FAIL | PARTIAL | EVIDENCE_NOT_FOUND
route_promotion_decision: PROMOTE | NO_PROMOTION | NOT_EVALUABLE
route_negative_decision: STOP_SUPPORTED | STOP_NOT_SUPPORTED | NOT_EVALUABLE
scientific_resolution_status: SCIENTIFIC_PROMOTED | SCIENTIFIC_STOP_SUPPORTED | SCIENTIFIC_UNRESOLVED | SCIENTIFIC_UNDERTRAINED | SCIENTIFIC_PIPELINE_BUG | SCIENTIFIC_NEEDS_EVIDENCE | SCIENTIFIC_NEEDS_REVISION
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET | DO_NOT_PUBLISH | NOT_APPLICABLE
git_commit_decision: COMMIT_ROUTE_PROMOTION | COMMIT_DIAGNOSTIC_ONLY | SKIP_COMMIT
git_push_decision: PUSH_ROUTE_PROMOTION | PUSH_DIAGNOSTIC_ONLY | SKIP_PUSH
published_files:
  - path
blocked_actions:
  - validation packaging/upload/fold expansion/hosted metric claim/next-stage training remain blocked
next_required_action: ...
reason_if_not_published: ...
reason_if_no_route_promotion: ...
```

## Escalation
If the result shows SRR, proposal, registration, Cine, missing-modality, or external-adapter work needs a new scientific direction, write `NEEDS_GPT_PLANNER` and stop.
