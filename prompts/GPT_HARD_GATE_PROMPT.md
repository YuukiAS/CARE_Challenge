# GPT Hard-Gate Prompt For CARE Handoff

This prompt is for future GPT/ChatGPT planning threads before writing CARE Codex goals. Its purpose is to prevent a controller task from being treated as complete when required subtasks, completion checks, training adequacy, audits, or route-defining diagrams are missing.

New GPT/ChatGPT planning threads must start from `START_HERE_FOR_GPT.md` before applying this hard gate.

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

The planner must locate the repository `images/` directory, download or copy every SRR design diagram at version `v2` or later to local working storage, and inspect those diagrams before proposing milestones. At minimum, this covers `v2`, `v2.5`, `v3`, and any later SRR/MyoPS architecture diagrams present in the repository.

After reading the diagrams, GPT must explicitly state the recovered route objective before planning. The statement must make clear that SRR-MyoPS is an availability-aware selective retrieval, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, and explicit loss/objective framework. A strong segmenter such as nnU-Net may provide anchor/context/evidence, but SRR must not be reduced to an optional post-processing add-on or a generic black-box competitor.

If the images cannot be located, copied/downloaded, opened, or interpreted, GPT must stop before writing milestones or Codex goals. It must explicitly report the blocked state, the failed image paths, and what the user must provide or fix. Do not continue from memory or a partial text summary when the diagrams are unavailable.

## Mandatory GPT Checklist Before Writing A New Goal

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
token, such as `M0_AUDITED_GO`.

## Known Bad Packet Regression

The 20260704 SRR-v2.5 full completion packet is the current regression counterexample. It listed 17 required subtasks, including `20260704_cine_temporal_dictionary_integration` and `20260704_srr_v25_completion_check`, but the controller report entered final audit without those result directories. Any future hard-gate validator must fail that packet by name. If the validator does not fail that packet, the anti-laziness system is not repaired.

The same packet also shows why smoke-scale training must not be promoted: bounded SRR variants with only 6 optimizer steps and limited explicit eval cases can support diagnostics, but cannot be called a formal full route test. Future GPT goals must make this distinction in the frontmatter and completion gate.

A new regression class is route-definition drift: a planner writes SRR/MyoPS milestones without first acquiring and reading the repository `images/` diagrams from version `v2` onward. Future milestones should treat missing diagram bootstrap evidence as `NEEDS_EVIDENCE`, not as a harmless omission.

## Required Wording In Future Start Prompts

When giving Codex a high-risk CARE controller goal, include this sentence:

`Before executing the scientific task, enforce the hard-gate policy: exact task graph, strict validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, and SRR diagram-bootstrap evidence when the task touches SRR/MyoPS/Cine route planning. If any hard gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE; do not continue to final audit.`

When giving Codex a milestone executor goal, also include this sentence:

`This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md. Do not write review.md, do not approve yourself, and do not start the next milestone; a separate read-only Codex reviewer must write review.md before continuation.`

When giving Codex a milestone reviewer goal, include this sentence:

`This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, do not package validation, do not upload, and do not start the next milestone. Write only review.md with the controlled audit decision.`

## State Mapping

If all subtasks were executed but training is smoke-scale or undertrained, use `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED`.

If required subtasks are missing, use `operational_completion_status: INCOMPLETE` and `scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE` or `SCIENTIFIC_NEEDS_REVISION`.

If SRR/MyoPS/Cine route diagrams were required but could not be acquired or interpreted, use `operational_completion_status: BLOCKED_ROUTE_DIAGRAMS_UNAVAILABLE` and `scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE`.

If a diagnostic packet is useful but no route is promoted, use `diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET` only after audit, and keep validation packaging, upload, fold expansion, hosted metric claims, and next-stage training blocked.

Do not use `COMPLETE`, `PASS`, `PROMOTE`, `STOP_NO_SIGNAL`, or `SCIENTIFIC_STOP_SUPPORTED` unless the corresponding machine-checkable gates pass.
