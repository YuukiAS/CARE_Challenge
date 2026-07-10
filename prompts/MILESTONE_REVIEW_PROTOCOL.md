# Milestone Review Protocol

This protocol applies to SRR-v3 / SRR-ProposeRefine milestone work and any future CARE milestone chain with blocking continuation gates.

## Purpose

Milestones are intentionally smaller than previous all-in-one controller goals.
Each milestone must be executed, checked, committed, and reviewed independently. A
milestone result is not authorization to continue. Continuation requires a
separate read-only review.

This is a two-step milestone gate:

1. executor/controller step;
2. independent read-only reviewer step.

The two steps must not be collapsed into one Codex session.

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
- commit the lightweight milestone report files with `git add -f` when the task authorizes commit and no gate blocks it.

The main Codex session must stop after `completion_check.md` and
`review_request.md`. It must not write the milestone's final `review.md`, must
not approve itself, must not mark `*_AUDITED_GO`, and must not start or prepare
the next milestone. Executor self-assessment can be `READY_FOR_REVIEW`,
`NEEDS_REVISION`, `NEEDS_EVIDENCE`, or a milestone-defined blocked state, but it
is never an audited continuation decision.

### MONITOR_PACKET_IS_NOT_COMPLETION

This rule applies to M7 follow-up2/follow-up3 and all future milestones.

A monitor packet, pending Slurm job packet, watcher packet, or submitted-only Slurm packet is not completion. The executor must not write `READY_FOR_REVIEW` or an equivalent ready state after only `sbatch` submission, `squeue` pending output, pending `sacct`, monitor watcher setup, or placeholder evidence.

If `completion_check.md`, `result.md`, `commands_run.md`, or a training adequacy table contains `NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or equivalent monitor/pending state, the result must remain `NEEDS_MONITOR` or `NEEDS_EVIDENCE`.

After the Slurm job completes, the executor must rerun the milestone aggregator or evidence collector and commit tracked lightweight evidence derived from runtime outputs before requesting review. The packet must record job id, state, exit code, runtime, log path, runtime output path, aggregation command, aggregation exit code, and updated tracked evidence files. If runtime output is missing or aggregation fails, completion must be `NEEDS_EVIDENCE`.

### Independent Codex Session: Read-Only Reviewer

The reviewer is a separate Codex session started after the executor has committed the milestone result and the user has pushed or otherwise made it available. Historical prompts may call this role `auditor`; that is a legacy alias only. It may:

- read the milestone prompt;
- read `results/<task_key>/`;
- read the hard-gate policy files;
- run allowed read-only validators if the review prompt authorizes them;
- check required outputs, completion check, strict validator behavior, forbidden substitutes, evidence quality, and completion gates;
- write only `results/<task_key>/review.md` and, if explicitly requested, a small review manifest;
- commit the review file with `git add -f` when the review prompt authorizes commit.

The reviewer must not:

- fix executor outputs;
- generate missing required files;
- modify model/training/evaluation code;
- run training;
- package validation;
- upload;
- start the next milestone;
- convert missing evidence into a pass.

The reviewer must also reject monitor packets as completion. If the tracked packet still shows monitor/pending states, only submitted/pending commands, a Slurm job id without completed aggregation, `result.md` saying monitor packet, or runtime outputs not merged into tracked evidence, the reviewer must decide `NEEDS_EVIDENCE` or `NEEDS_MONITOR`, never audited-go.

The reviewer is the only role allowed to write a milestone `review.md`.
The reviewer may approve continuation only with the exact audited-go
state defined by that milestone, such as `M0_AUDITED_GO`.

## Milestone Flow

```text
1. User/GPT selects exactly one milestone.
2. Main Codex executor runs that milestone only.
3. Executor writes required outputs, completion_check.md, review_request.md, and MANIFEST.md.
4. Executor force-adds and commits the lightweight result files, then stops.
5. User manually pushes or otherwise makes the executor commit available.
6. User/GPT starts a separate read-only reviewer Codex session.
7. Reviewer writes review.md with the milestone audit decision.
8. Reviewer force-adds and commits review.md, then stops.
9. User manually pushes or otherwise makes the review commit available.
10. User/GPT reads review.md.
11. Only if review.md contains the audited-go state may the next milestone start.
```

## Required Files Per Milestone

Every milestone executor result directory must include:

```text
results/<task_key>/result.md
results/<task_key>/completion_check.md
results/<task_key>/review_request.md
results/<task_key>/MANIFEST.md
```

Milestone-specific required outputs may add contract files, CSV/JSON summaries,
unit-test reports, or other evidence files. Missing required files are blockers
for review.

Every milestone reviewer writes:

```text
results/<task_key>/review.md
```

`review.md` is absent by design at the end of the executor step. The absence of
`review.md` blocks the next milestone until a separate reviewer writes it.

## Publication Rule For Ignored Result Directories

CARE `.gitignore` ignores generated `results/20??????_*/` directories. Milestone
report files are still intended to be committed. Therefore executor and reviewer
sessions must use `git add -f` for the exact lightweight Markdown/CSV/JSON files
required by the milestone. Do not add checkpoints, predictions, NIfTI files,
large logs, uploads, secrets, or full bulky result trees.

The executor/reviewer should commit locally but should not push automatically.
The user manually pushes after checking the commit.

Recommended executor commit command:

```bash
git add -f results/<task_key>/result.md results/<task_key>/completion_check.md results/<task_key>/review_request.md results/<task_key>/MANIFEST.md results/<task_key>/*.md results/<task_key>/*.csv results/<task_key>/*.json
git commit -m "Add <task_key> milestone result"
```

Recommended reviewer commit command:

```bash
git add -f results/<task_key>/review.md
git commit -m "Add <task_key> milestone review"
```

## Review Decisions

Each milestone defines its own controlled review states. Examples:

```text
M0_AUDITED_GO
M0_AUDITED_NEEDS_REVISION
M0_AUDITED_NEEDS_EVIDENCE
```

A milestone may not continue on executor self-assessment alone.
`completion_check.md` can say ready for review, but only `review.md` can
authorize continuation.

## Prerequisite Rule For Next Milestones

Every milestone after M0 must check the previous blocking milestone review
before doing any scientific work:

```text
results/<previous_task_key>/review.md:<PREVIOUS_MILESTONE>_AUDITED_GO
```

If the file is missing or does not contain the exact audited-go token, the
executor must stop with the milestone's blocked state, write no scientific
outputs beyond a minimal blocked result packet, and must not start repair work
unless the current milestone explicitly authorizes such repair.

## Relationship To Controller Subagents

General CARE controller tasks may still generate executor, mapper, and reviewer handoff prompt files or launch subagents when explicitly authorized by a GPT-authored controller task. However, for milestone chains, the final blocking milestone review must be written by an independent read-only reviewer session, not by the same main executor/controller session that produced the result.

Internal self-checks, subagent notes, or executor-launched audit drafts are allowed only as diagnostic aids. They do not replace the independent `review.md` required to start the next milestone.

## Forbidden Shortcuts

- Do not let an executor write its own final `review.md`.
- Do not let an executor/controller mark `*_AUDITED_GO`.
- Do not treat `completion_check.md` as audited continuation permission.
- Do not treat monitor packets, pending Slurm packets, submitted-only jobs, or watcher packets as milestone completion.
- Do not let a controller report absorb a missing review.
- Do not continue to the next milestone while `review.md` is missing.
- Do not mark a milestone audited-go if required output files are missing.
- Do not call smoke-scale or eval-only evidence formal route evidence.
- Do not start the next milestone from the same Codex session that produced the
  current milestone result.

## Required Wording For Milestone Executor Prompts

Every milestone executor prompt should include:

```text
This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md, force-add/commit the lightweight required result files, then stop. Do not push automatically. Do not write review.md and do not start the next milestone. The milestone must be reviewed by a separate read-only Codex session before continuation.
```

## Required Wording For Milestone Reviewer Prompts

Every milestone reviewer prompt should include:

```text
This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, and do not start the next milestone. Review only the completed result directory, write review.md with the controlled milestone decision, then force-add/commit review.md. Do not push automatically.
```
