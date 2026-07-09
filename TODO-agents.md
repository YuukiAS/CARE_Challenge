# TODO-agents: controller-supervised execution flow repair

Status: proposed protocol repair task list. This file does not change active runtime rules by itself. Use it as the next maintenance target for `AGENTS.md`, handoff files, GPT planner protocol files, and controller templates.

## Why this is needed

The current protocol already says that Slurm monitor packets are not completion and that `RUNNING`, `PENDING`, and `AWAITING_SACCT` must not be treated as ready. However, a long Slurm milestone can still waste overnight runtime if an executor exits early and labels normal waiting as `blocked`. Reviewer/auditor checks catch this after the fact, but they do not keep execution alive while the user is away.

The fix is not to add more natural-language reminders. The fix is to split runtime continuity from read-only review.

## Current state to preserve

- GPT/ChatGPT remains the planner and strategic controller.
- Codex executor performs authorized code changes, commands, result writing, and local commits, but must not self-review or start the next milestone.
- Reviewer/auditor remains a separate read-only role and must not fix code, generate missing artifacts, train, resume execution, or act as executor.
- Slurm monitor packets, pending jobs, running jobs, watcher packets, and submitted-only packets are not completion.
- After Slurm jobs complete, the relevant aggregator/evidence collector must run before review.
- `AGENTS.md` remains the repo-level Codex rule source.

## Target operating modes

### Mode A: short task / no long Slurm wait

Use the existing lightweight flow:

1. GPT planner writes the milestone / task / gates.
2. User starts one Codex executor goal or executor thread.
3. Executor completes the milestone, writes evidence, commits locally, and stops.
4. User starts a separate read-only reviewer/auditor thread or short reviewer goal.
5. Reviewer writes `review.md`, optionally commits it if authorized, and stops.

### Mode B: long Slurm / overnight / fragile resume task

Use controller-supervised execution:

1. GPT planner must mark the milestone as `execution_mode: controller_supervised`.
2. User starts one top-level Codex execution controller goal, not a standalone overnight executor goal.
3. The controller reads the task, `AGENTS.md`, handoff rules, Slurm skill, and current live git/Slurm state before launching or resuming execution.
4. The controller may use an executor worker/subagent for implementation, but the controller owns runtime continuity.
5. The controller must keep monitoring while required Slurm jobs are `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, or `AWAITING_SACCT`.
6. These normal monitor states must remain `NEEDS_MONITOR`; they must not become `blocked` unless the Slurm skill's 24-hour pending threshold is satisfied.
7. After jobs reach terminal states, the controller runs the required aggregator/evidence collector, validator/self-tests, `git diff --check`, and local commit of lightweight evidence.
8. The controller writes an execution/controller report and stops.
9. Reviewer/auditor is still launched separately afterward and remains read-only.

## Required changes to planning files

Update `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, and `prompts/GPT_HARD_GATE_PROMPT.md` so GPT must decide the execution mode before writing any milestone:

- `execution_mode: direct_executor` for short tasks.
- `execution_mode: controller_supervised` for long Slurm, overnight, multi-job, or high resume-risk tasks.
- `requires_execution_controller: true|false`.
- `review_mode: independent_readonly_thread` by default; `short_reviewer_goal` only when automatic review commit is desired.
- `context_bootstrap_required: true` for all controller-supervised milestones.

GPT planner must not write an overnight Slurm milestone that only provides a normal executor prompt. If the task may run while the user sleeps, GPT must author a controller prompt or controller section explicitly.

## Required changes to handoff roles

Update `prompts/HANDOFF_ROLES.md` to make four runtime roles explicit:

- `planner`: GPT/ChatGPT thread. Designs route, milestone, evidence gates, executor/controller prompt, and reviewer prompt. Does not run code or review final packets.
- `executor`: Codex worker for short direct execution or for controller-owned implementation phases. It can change code, run commands, write evidence, and commit. It cannot self-review, decide route promotion, start the next milestone, or own overnight continuity.
- `execution_controller`: Codex controller goal for long Slurm/overnight execution continuity. It monitors live Slurm/git/result-dir state, prevents erroneous early `blocked` exits, resumes the same milestone when needed, runs final aggregation/validation/commit after terminal jobs, writes controller report, and stops. It cannot write `review.md`, cannot make scientific route decisions, and cannot start the next milestone.
- `reviewer/auditor`: separate read-only review. It checks the final committed packet and writes review. It must not monitor or resume executor work.

Also update the existing wording that says the controller creates or launches executor and auditor sessions. For long Slurm flow, the controller may create/use executor workers, but it must not launch the reviewer/auditor until the final packet is committed and ready for read-only review.

## Required changes to controller template

Update `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`:

- Add `execution_mode` to frontmatter.
- Add `requires_execution_controller` to frontmatter.
- Add `context_bootstrap_required` to frontmatter.
- Add `slurm_runtime_continuity_required` to frontmatter.
- Add explicit `normal_monitor_states`: `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, `AWAITING_SACCT`.
- Add `scheduler_block_threshold`: `12 consecutive 2-hour pending-only checks with no job start`.
- Add a required `controller_bootstrap_snapshot_path`, e.g. `results/<task_key>/controller_bootstrap_snapshot.md`.
- Add a required `controller_supervision_ledger_path`, e.g. `results/<task_key>/controller_supervision_ledger.csv`.
- Add a required `finalizer_command` field when Slurm jobs are used.

## Required context handling policy

Do not rely on informal LLM context compression as the safety mechanism. It is lossy and can create the same problem under a shorter summary.

For controller-supervised milestones, require a deterministic bootstrap before every major phase:

1. Read from disk: `AGENTS.md`, `prompts/HANDOFF_ROLES.md`, `.agents/skills/slurm-routing-partition/SKILL.md`, the current GPT-authored milestone/task prompt, and the relevant result directory manifests if present.
2. Refresh live state: `git status --porcelain=v1 -b`, `git log --oneline --decorate -5`, `squeue`/`sacct` for required job IDs, required runtime-output existence, and required tracked evidence existence.
3. Write or update `controller_bootstrap_snapshot.md` with these facts.
4. Only then launch/resume executor work or run finalization.

For a new milestone, prefer a fresh controller goal/session over continuing an old compressed controller context. For a single long overnight milestone, the same controller may remain active, but it must repeatedly ground itself from the disk/live-state bootstrap snapshot rather than from memory.

## Required Slurm finalization behavior

Implement or require a milestone finalizer pattern:

- If any required job is `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, or `AWAITING_SACCT`, continue monitoring and keep state as `NEEDS_MONITOR`.
- If jobs are terminal and outputs exist, run aggregator/evidence collector, validator/self-tests, `git diff --check`, and commit lightweight evidence.
- If jobs are terminal but outputs are missing or aggregation fails, write `NEEDS_EVIDENCE` with live Slurm/log/runtime evidence and commit that evidence.
- If jobs fail, collect `sacct`, exit code, runtime, log path, and partial outputs, then write the appropriate evidence packet; do not call this scheduler block.
- Only call scheduler/resource blocked when the Slurm skill's pending-only threshold is met.

A future implementation may use either a foreground blocking finalizer command or a Slurm `afterany` dependency finalizer job. If using dependency finalizer jobs, add a lock to prevent concurrent manual resume and finalizer writes.

## Required validator / known-bad updates

Add known-bad cases that fail closed when:

- A required Slurm job is `RUNNING` but `result.md` or `completion_check.md` says `blocked` or `RESOURCE_BLOCKED`.
- A required Slurm job is `PENDING` but the 24-hour pending threshold is not proven and the packet says `blocked`.
- Final runtime outputs are missing because jobs are still running, but the packet claims blocked instead of `NEEDS_MONITOR`.
- A reviewer/auditor prompt authorizes resume, training, code changes, artifact generation, or executor recovery.
- A controller writes `review.md` or claims audited-go.
- A normal executor prompt is used for an overnight Slurm milestone without controller supervision.
- GPT writes a Slurm-backed milestone without `execution_mode` and `requires_execution_controller` fields.

## Minimal user-facing rule

Use this operational rule in future GPT planning outputs:

- Short task: `GPT planner -> executor goal/thread -> independent reviewer thread`.
- Long Slurm or overnight task: `GPT planner -> execution controller goal -> independent reviewer thread`.

Do not use `reviewer` as the thing that monitors executor blocking. Reviewer is read-only. The monitoring role is `execution_controller`.

## Files expected to be edited in the follow-up maintenance task

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`
- `.agents/skills/slurm-routing-partition/SKILL.md` if the finalizer/monitor-state wording needs to be centralized there
- Any shared executor/reviewer prompt templates that still imply reviewer-supervised execution or overnight direct executor mode

## Done criteria for the maintenance task

The follow-up protocol repair is done only when:

- GPT planning files require `execution_mode` selection before milestone writing.
- Controller-supervised mode is mandatory for long Slurm/overnight milestones.
- Reviewer/auditor remains strictly read-only and cannot monitor/resume executor work.
- Controller cannot write `review.md` or make audited-go decisions.
- Context bootstrap is disk/live-state based, not informal context compression.
- Validators reject `RUNNING/PENDING -> blocked` misclassification unless the Slurm skill threshold is proven.
- The updated files clearly state the user command pattern: short task uses executor; long Slurm uses controller; final review remains separate.
