# Milestone Review Protocol

This protocol applies to SRR-v3 / SRR-ProposeRefine milestone work and any future CARE milestone chain with blocking continuation gates.

## Purpose

Milestones are intentionally smaller than previous all-in-one controller goals. Each milestone must be executed, checked, and reviewed independently. A milestone result is not authorization to continue. Continuation requires a separate read-only review.

## Roles

### Main Codex Session: Executor / Local Controller

The main Codex session executes exactly one milestone at a time. It may:

- read the milestone prompt and required inputs;
- enforce hard-gate checks before execution;
- perform authorized code, evaluation, or report work inside the milestone scope;
- run allowed validators, tests, and lightweight commands;
- write the required files under the exact `results/<task_key>/` directory;
- write `completion_check.md`;
- write `review_request.md`;
- update `MANIFEST.md`;
- commit/push only if the milestone prompt explicitly authorizes it and no gate blocks it.

The main Codex session must stop after `completion_check.md` and `review_request.md`. It must not write the milestone's final `review.md`, must not approve itself, and must not start the next milestone.

### Independent Codex Session: Read-Only Reviewer / Auditor

The reviewer/auditor is a separate Codex session started after the executor has pushed the milestone result. It may:

- read the milestone prompt;
- read `results/<task_key>/`;
- read the hard-gate policy files;
- run allowed read-only validators if the review prompt authorizes them;
- check required outputs, completion check, strict validator behavior, forbidden substitutes, evidence quality, and completion gates;
- write only `results/<task_key>/review.md` and, if explicitly requested, a small review manifest.

The reviewer/auditor must not:

- fix executor outputs;
- generate missing required files;
- modify model/training/evaluation code;
- run training;
- package validation;
- upload;
- start the next milestone;
- convert missing evidence into a pass.

## Milestone Flow

```text
1. User/GPT selects exactly one milestone.
2. Main Codex executor runs that milestone only.
3. Executor writes required outputs, completion_check.md, review_request.md, and stops.
4. User/GPT starts a separate read-only reviewer Codex session.
5. Reviewer writes review.md with the milestone audit decision.
6. User/GPT reads review.md.
7. Only if review.md contains the audited-go state may the next milestone start.
```

## Review Decisions

Each milestone defines its own controlled review states. Examples:

```text
M0_AUDITED_GO
M0_AUDITED_NEEDS_REVISION
M0_AUDITED_NEEDS_EVIDENCE
```

A milestone may not continue on executor self-assessment alone. `completion_check.md` can say ready for review, but only `review.md` can authorize continuation.

## Relationship To Controller Subagents

General CARE controller tasks may still generate executor and auditor prompt files or launch subagents when explicitly authorized by a GPT-authored controller task. However, for milestone chains, the final blocking milestone review must be written by an independent read-only reviewer session, not by the same main executor/controller session that produced the result.

Internal self-checks, subagent notes, or executor-launched audit drafts are allowed only as diagnostic aids. They do not replace the independent `review.md` required to start the next milestone.

## Forbidden Shortcuts

- Do not let an executor write its own final `review.md`.
- Do not treat `completion_check.md` as audited continuation permission.
- Do not let a controller report absorb a missing review.
- Do not continue to the next milestone while `review.md` is missing.
- Do not mark a milestone audited-go if required output files are missing.
- Do not call smoke-scale or eval-only evidence formal route evidence.

## Required Wording For Milestone Executor Prompts

Every milestone executor prompt should include:

```text
This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md. Do not write review.md and do not start the next milestone. The milestone must be reviewed by a separate read-only Codex session before continuation.
```

## Required Wording For Milestone Reviewer Prompts

Every milestone reviewer prompt should include:

```text
This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, and do not start the next milestone. Review only the completed result directory and write review.md with the controlled milestone decision.
```
