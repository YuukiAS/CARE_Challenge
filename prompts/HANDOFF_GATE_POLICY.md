# CARE Handoff Gate Policy

This policy defines how future CARE controller goals should be accepted or blocked. It is intentionally mechanical: a requirement is a gate only when it can be checked from exact paths, parsed fields, command exits, metrics, provenance, or an audit decision.

## Agent-Flow v2 Gate

New CARE controller goals must declare `execution_mode`, `requires_execution_controller`, `executor_slots`, `executor_count`, `parallel_execution_allowed`, `executor_plan_path`, `mapper_slots`, `mapper_required`, `architecture_impact`, `wiki_update_required`, `diagram_update_required`, `slurm_runtime_continuity_required`, `continuity_backend`, `review_mode`, and `reviewer`. `prompts/AGENT_FLOW_V2_PROTOCOL.md` is the canonical source for these fields.

Overnight, long Slurm, multi-job, or high-resume-risk tasks must use `execution_mode: controller_supervised` and a durable continuity backend. Architecture-changing tasks must enable mapper and update root `wiki/` unless they provide a machine-readable no-change fingerprint receipt. A controller must not increase executor/mapper slots beyond the GPT-authored task graph. New tasks must not use an internal `auditor`; historical `auditor` fields are legacy aliases for the final independent `reviewer`.

Controller reports are written before independent review. They must not require `reviewer_review` as evidence before local packet commit, must not claim audited-go, and must use `route_promotion_decision: NOT_REVIEWED`, `route_negative_decision: NOT_REVIEWED`, and `scientific_resolution_status: AWAITING_REVIEW`.

For new controller tasks, push permissions are invalid by default: `auto_git_push`, `allow_git_push`, and `allow_diagnostic_push` must be false. Local commit only means the lightweight final packet is ready for separate reviewer inspection.

## Gate Principles

A controller task must expose its full ordered task graph. Every required subtask must have an exact `results/<task_key>/` directory and the exact required output filenames declared by its task file. A missing required result directory is a blocking error.

A controller report must not replace a missing required subtask with a similar name, a diagnostic summary, or a later final review. If a subtask is optional, that optional status must be explicit in the controller task before execution.

A final review must be preceded by a completion check when the controller task lists one. The completion check must write a decision file declaring readiness. Without that readiness file, the final review is blocked.

## MONITOR_PACKET_IS_NOT_COMPLETION

A monitor packet, pending Slurm job packet, watcher packet, or submitted-only Slurm packet is not a completion packet. This applies to M7 follow-up2/follow-up3 and every future milestone.

An executor must not write milestone ready when it has only submitted a Slurm job, monitor job, watcher, or pending monitor packet. If `completion_check.md`, `result.md`, `commands_run.md`, or an adequacy table contains `NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or an equivalent monitor/pending state, the packet is not reviewable as complete.

After a Slurm job completes, the executor must rerun the relevant aggregator or evidence collector and write the runtime outputs into tracked lightweight result files before requesting review. `commands_run.md` that only records `sbatch submitted`, `squeue pending`, `PENDING Priority`, or pending `sacct` is not completion evidence.

A job-derived completion packet must record job id, state, exit code, runtime, log path, runtime output path, aggregation command, aggregation exit code, and the tracked evidence files updated from runtime output. If the job completed but runtime output is missing or aggregation fails, the completion state must be `NEEDS_EVIDENCE`, not ready.

Reviewers must check that the tracked packet is the final post-completion aggregation rather than a job-submission placeholder. A reviewer must return `NEEDS_EVIDENCE` or `NEEDS_MONITOR`, not audited-go, if monitor placeholders remain or runtime output has not been merged into tracked evidence.

Validators and reviewer known-bad cases must include: `completion_check.md` ready while `followup*_training_adequacy.csv` contains `PENDING_MONITOR`; `commands_run.md` contains only submitted/pending job state; a Slurm job id exists but no completed aggregation record exists; `result.md` says monitor packet; runtime output is not merged into tracked evidence.

Validation scripts used for completion decisions must fail closed. If errors are reported, the command must return failure unless it is explicitly invoked as a non-completion diagnostic scan. Historical tolerated findings require a named allowlist with reason, expiry, and owner.

Trainable model evidence must be classified by adequacy. Small probes and smoke runs can support debugging, but not route promotion or scientific stop. Adequacy requires training budget, validation events, loss behavior, prediction sanity, provenance paths, cache isolation, and same-split baseline comparison.

Operational completion and scientific route status are separate. A controller may finish its assigned workflow while the model route remains undertrained, unresolved, or in need of evidence.

Milestone executor completion and milestone review are also separate. For
`task_type: milestone`, the executor/controller step must stop after writing
`completion_check.md` and `review_request.md`. It must not write `review.md`,
must not mark `*_AUDITED_GO`, and must not start the next milestone. A separate
read-only reviewer must inspect the result directory and write
`review.md`; only the exact audited-go token in that review permits the next
milestone.

## Required Controller Report Ending

Every high-risk controller report should end with these fields:

```text
controller_run_status:
operational_completion_status:
experiment_adequacy_decision:
route_promotion_decision:
route_negative_decision:
scientific_resolution_status:
diagnostic_publication_decision:
git_commit_decision:
git_push_decision:
published_files:
blocked_actions:
next_required_action:
reason_if_not_published:
reason_if_no_route_promotion:
```

## Regression Case

The current regression case is `20260704_srr_v25_full_completion_goal`. Its task graph listed 17 required subtasks, including `20260704_cine_temporal_dictionary_integration` and `20260704_srr_v25_completion_check`, but those result directories were absent while final review still ran.

Any repaired gate must fail this case until the missing evidence is supplied or the controller task is explicitly revised.

## Required Behavior For Future Goals

Before any future SRR, Cine, missing-modality, registration, proposal/refinement, external-adapter, fold-expansion, validation-packaging, or submission-related controller goal starts, the executor must first enforce:

1. exact task graph extraction;
2. exact result-directory checks;
3. exact required-output filename checks;
4. completion-check-before-final-review;
5. strict validator behavior;
6. minimum effective training classification;
7. controller report schema validation;
8. known-bad-packet regression;
9. `MONITOR_PACKET_IS_NOT_COMPLETION`.

If any of these gates fail, the controller must stop with `NEEDS_EVIDENCE` or `NEEDS_REVISION`. It must not continue to final review, route promotion, fold expansion, validation packaging, validation upload, or scientific stop.

For milestone chains, also enforce:

10. exact prerequisite `review.md:<MILESTONE>_AUDITED_GO` before starting any
   non-initial milestone;
11. exact `completion_check.md` and `review_request.md` before executor stop;
12. missing independent `review.md` blocks the next milestone;
13. same-session executor/controller review is invalid for continuation.


Executor parallelism gate: any `executor_count > 1`, `executor_slots > 1`, or `parallel_execution_allowed: true` task must provide `executor_plan_path` and pass `scripts/ops/validate_executor_plan.py`. MyoPS and Cine remain sequential unless GPT provides explicit isolation proof.
