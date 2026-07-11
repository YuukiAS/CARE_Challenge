# GPT Hard-Gate Prompt For CARE Handoff

This prompt is for future GPT/ChatGPT planning threads before writing CARE Codex goals. Its purpose is to prevent a controller task from being treated as complete when required subtasks, completion checks, training adequacy, audits, or route-defining diagrams are missing.

New GPT/ChatGPT planning threads must start from `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, and `prompts/AGENT_FLOW_V2_PROTOCOL.md` before applying this hard gate.

## Core Rule

Do not write another high-risk CARE goal that relies on natural-language warnings alone. Every anti-laziness requirement must become one of the following:

1. an exact required file path;
2. a machine-readable frontmatter field;
3. a validator check that exits nonzero on failure;
4. a required report field in `controller_report.md`, `result.md`, or `review.md`;
5. a regression test against a known bad packet.

If a requirement cannot be checked by file existence, parsed status, command exit, metric/provenance field, or explicit audit decision, do not call it a gate. Call it advice only.

## Mandatory SRR Diagram Bootstrap Before New CARE Goals

Before writing or revising any SRR/MyoPS/Cine milestone, Codex goal, handoff, or route decision, GPT must apply `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`.

The planner must visually read every SRR design diagram at version `v2` or later from ChatGPT Project background files / project materials before proposing milestones. At minimum, this covers `v2`, `v2.5`, `v3`, and any later SRR/MyoPS architecture diagrams present in the project materials. Repository paths such as `images/SRR-v2.png`, `images/SRR-v2.5.png`, and `images/SRR-v3.png` remain canonical filenames and version references; they are not the required GPT visual-reading entrypoint.

After reading the diagrams, GPT must explicitly state the recovered route objective before planning. The statement must make clear that SRR-MyoPS is an availability-aware selective retrieval, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, and explicit loss/objective framework. A strong segmenter such as nnU-Net may provide anchor/context/evidence, but SRR must not be reduced to an optional post-processing add-on or a generic black-box competitor.

If the images cannot be accessed or visually interpreted from ChatGPT Project background materials, GPT must stop before writing milestones or Codex goals. It must explicitly report `BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE`, the missing versions, the canonical repository references, and that the user must add the diagrams to the ChatGPT Project background materials or upload them into the current conversation. Do not continue from memory, GitHub connector blob/SHA/base64 metadata, filenames, old chat summaries, or partial text recaps when the diagrams are unavailable.

## Mandatory GPT Checklist Before Writing A New Goal

For every new CARE milestone or controller goal, GPT must declare the agent-flow v2 execution contract:

```yaml
execution_mode: direct_executor | controller_supervised
requires_execution_controller: true | false
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/<task_key>_executor_plan.yaml
mapper_slots: 1
mapper_required: true | false
architecture_impact: none | component | system
wiki_update_required: true | false
diagram_update_required: true | false
slurm_runtime_continuity_required: true | false
continuity_backend: none | slurm_dependency | tmux_watcher
review_mode: independent_thread | short_goal
reviewer: separate_readonly
```

Every milestone staging file matching `prompts/shared/M[0-9]*_*.md` must place
the machine contract in YAML frontmatter on line 1. The body `## Execution
Contract` section is only a human-readable mirror. Missing frontmatter,
malformed frontmatter, body/frontmatter mismatches, missing `executor_plan_path`,
or a failing `scripts/ops/validate_executor_plan.py` result are hard-gate
failures.

Any staging prompt that triggers the generic critic gate requires a separate GPT
planning critic before Codex execution. The required sequence is:

```text
planner GPT -> separate GPT critic -> Codex merge/validator -> controller
```

This planning critic is not a controller subagent and not the independent
post-execution reviewer. Required frontmatter:

```yaml
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/tasks/<task_key>_planning_review.md
planning_review_token: <controlled token>
planning_reviewed_commit: <commit>
```

If a critic-required staging prompt lacks a matching planning review hash/token,
its only allowed statuses are `DRAFT_FOR_PLANNING_REVIEW`,
`PLANNING_REVIEW_RUNNING`, `NEEDS_PLANNING_REVISION`, or
`BLOCKED_HANDOFF_REVIEW`. `READY_FOR_CODEX_MERGE` is forbidden until the
separate GPT planning review is present and current.

Overnight, long Slurm, multi-job, or high-resume-risk work must be `controller_supervised` and must have a durable continuity backend. Architecture/loss/dataflow/export/registration/temporal changes must enable mapper and update root `wiki/` unless explicitly classified as `architecture_impact: none` with fingerprint evidence. New tasks must not introduce a controller-internal `auditor`; use `mapper` for internal read-only architecture mapping and `reviewer` for the final independent read-only audit.

Long Slurm / overnight staging prompts must contain these sections exactly: `## Execution Contract`, `## Controller Prompt`, `## Executor Worker Contract`, `## Mapper Contract`, and `## Reviewer Prompt`. They must include a durable finalizer contract naming required job IDs or how they will be captured, runtime output paths, aggregator command, validator commands, lock/log paths, and local packet commit policy. Short staging prompts must contain `## Execution Contract`, `## Executor Prompt`, and `## Reviewer Prompt`.

For staged long milestones, `Execution Contract`, `Controller Prompt`,
`Executor Worker Contract`, and `Mapper Contract` are executor-side material
and must merge into `prompts/shared/EXECUTOR_PROMPTS.md`. Only `Reviewer
Prompt` merges into `prompts/shared/REVIEWER_PROMPTS.md`. Executor plans stay
as `prompts/tasks/<task_key>_executor_plan.yaml`; putting a full executor plan
inside a shared prompt is a hard-gate failure.

Any system-level redesign must list dynamically resolved history files read from
`wiki/current_state.yaml` and `wiki/history/` before writing the milestone.
Mandatory dynamic files are `wiki/history/COMPARISON.md`,
`wiki/history/<predecessor>/README.md`,
`wiki/history/<predecessor>/COMPONENTS.csv`, and the relevant
`wiki/history/<predecessor>/components/*.md` files. Full system redesign must
read all predecessor component analyses. A non-latest predecessor requires
`history_baseline_override` and `history_baseline_override_reason`. Missing
`history_files_read` or equivalent explicit file list is a hard-gate failure.

Controller reports written before the independent reviewer must not claim reviewer approval, audited-go, route promotion, or scientific stop. They must use `route_promotion_decision: NOT_REVIEWED`, `route_negative_decision: NOT_REVIEWED`, and `scientific_resolution_status: AWAITING_REVIEW`. Any controller prompt that requires `reviewer_review` as evidence before controller commit, permits controller/reviewer push, or sets `auto_git_push` / `allow_git_push` / `allow_diagnostic_push` true is a hard-gate failure.

For every controller task, GPT must define an explicit ordered task graph. The graph must include every required subtask key, the exact expected `results/<task_key>/` directory, and whether that subtask is blocking or optional. A blocking subtask that has no result directory must be treated as `INCOMPLETE`, not as skipped, replaced, or diagnostic.

For every high-risk model/training route, GPT must include `minimum_effective_training` with concrete fields. At minimum use `min_optimizer_steps`, `min_train_loop_seconds`, `min_eval_cases`, `require_one_batch_overfit`, `require_prediction_sanity`, `require_loss_decrease`, `require_same_split_baseline`, and `require_cache_isolation`. A run that falls below this budget may be useful as smoke evidence, but it cannot support route promotion or scientific stop.

For every goal with final audit, GPT must require a separate read-only completion check before final audit. The final audit must be blocked if `results/<completion_check_task>/decision.md` is missing or does not contain a state equivalent to `READY_FOR_FINAL_AUDIT`. Final audit is not allowed to silently absorb missing completion checks.

For every anti-laziness validator, GPT must require strict mode by default. A validator with `error_count > 0` must exit nonzero unless the command is explicitly named `diagnostic_non_strict`. Legacy findings require an explicit allowlist file with reason, expiry, and owner; vague labels such as `legacy issue` are not sufficient.

For every controller report, GPT must require the ending fields from `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`: `controller_run_status`, `operational_completion_status`, `experiment_adequacy_decision`, `route_promotion_decision`, `route_negative_decision`, `scientific_resolution_status`, `diagnostic_publication_decision`, `git_commit_decision`, `git_push_decision`, `published_files`, `blocked_actions`, `next_required_action`, `reason_if_not_published`, and `reason_if_no_route_promotion`.

For every milestone chain, GPT must apply `prompts/MILESTONE_REVIEW_PROTOCOL.md`.
Write executor prompts for exactly one milestone. Require exact
`results/<task_key>/completion_check.md` and
`results/<task_key>/review_request.md`; forbid the executor/controller from
writing `review.md`, approving itself, or starting the next milestone. Then
write a separate read-only reviewer prompt. The next milestone may be launched
only when the previous milestone's `review.md` contains the exact audited-go
token, such as `<MILESTONE>_AUDITED_GO`.

## Known Bad Packet Regression

The 20260704 SRR-v2.5 full completion packet is the current regression counterexample. It listed 17 required subtasks, including `20260704_cine_temporal_dictionary_integration` and `20260704_srr_v25_completion_check`, but the controller report entered final audit without those result directories. Any future hard-gate validator must fail that packet by name. If the validator does not fail that packet, the anti-laziness system is not repaired.

The same packet also shows why smoke-scale training must not be promoted: bounded SRR variants with only 6 optimizer steps and limited explicit eval cases can support diagnostics, but cannot be called a formal full route test. Future GPT goals must make this distinction in the frontmatter and completion gate.

A new regression class is route-definition drift: a planner writes SRR/MyoPS milestones without first visually reading the `v2` and later route diagrams from ChatGPT Project background materials. Future milestones should treat missing diagram bootstrap evidence as `NEEDS_EVIDENCE`, not as a harmless omission.

Hard-gate validators and reviewers must treat each of these as a route-definition blocker:

1. the planner did not state that route diagrams were read from ChatGPT Project background materials;
2. the planner relied only on repository filenames, GitHub blob SHA, base64 metadata, old chat summaries, or natural-language recaps;
3. the planner claimed visual image reading from GitHub connector without actual visual input;
4. the planner generated an SRR/MyoPS/Cine milestone without `diagram_versions_read` and `visual_read_status`.

## Required Wording In Future Start Prompts

When giving Codex a high-risk CARE controller goal, include this sentence:

`Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, strict validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, mapper/wiki/fingerprint gates when architecture is affected, and SRR diagram-bootstrap evidence when the task touches SRR/MyoPS/Cine route planning. If any hard gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE; do not continue to final audit.`

When giving Codex a milestone executor goal, also include this sentence:

`This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md. Do not write review.md, do not approve yourself, and do not start the next milestone; a separate read-only Codex reviewer must write review.md before continuation.`

When giving Codex a milestone reviewer goal, include this sentence:

`This is a separate read-only reviewer session. Do not fix code, do not generate missing artifacts, do not train, do not package validation, do not upload, and do not start the next milestone. Write only review.md with the controlled review decision.`

## State Mapping

If all subtasks were executed but training is smoke-scale or undertrained, use `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED`.

If required subtasks are missing, use `operational_completion_status: INCOMPLETE` and `scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE` or `SCIENTIFIC_NEEDS_REVISION`.

If SRR/MyoPS/Cine route diagrams were required but could not be visually read from ChatGPT Project background materials or current-conversation uploads, use `operational_completion_status: BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE` and `scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE`.

If a diagnostic packet is useful but no route is promoted, use `diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET` only after audit, and keep validation packaging, upload, fold expansion, hosted metric claims, and next-stage training blocked.

Do not use `COMPLETE`, `PASS`, `PROMOTE`, `STOP_NO_SIGNAL`, or `SCIENTIFIC_STOP_SUPPORTED` unless the corresponding machine-checkable gates pass.


Executor parallelism gate: any `executor_count > 1`, `executor_slots > 1`, or `parallel_execution_allowed: true` task must provide `executor_plan_path` and pass `scripts/ops/validate_executor_plan.py`. MyoPS and Cine remain sequential unless GPT provides explicit isolation proof.
