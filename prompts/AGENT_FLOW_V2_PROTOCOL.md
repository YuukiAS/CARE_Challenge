# CARE Agent-Flow v2 Protocol

This is the permanent canonical source for CARE agent-flow v2. It replaces the
retired planning notes `TODO-agents-v2.md` and `TODO-agents.md`, which must not
be used as runtime rule sources.

## Active Roles

Only these role names are active for new CARE handoffs:

- `planner`: the user-supervised GPT/ChatGPT thread that designs the task,
  execution mode, role graph, evidence gates, and reviewer contract.
- `controller`: the top-level Codex goal for one GPT-authored controller task.
  It owns phase re-grounding, subagent coordination, Slurm continuity,
  finalizer handoff, validators, local packet commit, and stop-before-review.
- `executor`: an implementation/command worker. It performs authorized edits,
  job submission, aggregation, and evidence writing, but it does not self-review
  and does not own overnight continuity.
- `mapper`: a read-only architecture/evidence mapper. It may update `wiki/`
  only when the task authorizes wiki updates. It never writes `review.md`.
- `finalizer`: a deterministic script or controller-managed terminal stage for
  Slurm accounting, aggregation, validation, mapper-final handoff, wiki
  finalization, and local packet commit. It is not an LLM reviewer.
- `validator`: first-party fail-closed scripts that check task, packet,
  controller, wiki, and known-bad fixtures.
- `reviewer`: a separate read-only Codex thread or short goal that starts after
  the controller/executor packet is locally committed. It writes `review.md`.

Historical `auditor` fields are legacy aliases for the independent `reviewer`.
New tasks must not create a controller-internal auditor subagent.

## Execution Modes

Short, non-Slurm, low-resume-risk work may use:

```text
planner -> executor -> local commit -> separate reviewer
```

Long Slurm, overnight, multi-job, architecture-affecting, or high-resume-risk
work must use:

```text
planner -> controller
                 |-> executor subagent
                 |-> mapper draft
                 |-> durable Slurm watcher/finalizer
                 |-> mapper final
                 |-> validator
                 |-> local commit
            controller stops
            -> separate reviewer
```

The controller, executor, mapper, finalizer, and validator must not write
`review.md`. The reviewer must not become a controller subagent. No role may
push; the user pushes manually.

## Controller Lifecycle

Controller-supervised tasks follow this exact order:

1. controller bootstrap;
2. executor implementation;
3. implementation snapshot;
4. mapper draft;
5. durable continuity;
6. terminal finalizer;
7. mapper final;
8. validators;
9. controller local commit of the lightweight final packet;
10. controller stops;
11. separate reviewer independently runs;
12. reviewer separately commits `review.md`;
13. user manually pushes.

Because `controller_report.md` is generated before reviewer execution, it must
not require or invent a reviewer decision. Before independent review, controller
reports may only use:

```text
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
```

Final scientific decisions require the independent reviewer token and later GPT
planner judgment.

## Required Execution Contract

Every new CARE milestone or controller task must declare:

```yaml
execution_mode: direct_executor | controller_supervised
requires_execution_controller: true | false
executor_slots: 1
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

The controller must not increase executor or mapper counts beyond the
GPT-authored task graph.

Long Slurm or overnight tasks require a durable finalizer contract. Declaring
`continuity_backend` without a real dependency finalizer job or namespace-local
tmux watcher evidence is invalid.

## Controller Receipts

Controller-supervised result packets must produce or validate:

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
implementation_snapshot.md
finalizer_state.json
mapper_report_draft.md
mapper_report_final.md
architecture_delta_final.md
```

Receipts must include current task prompt hash, `AGENTS.md` hash, Slurm skill
hash when Slurm is involved, required job IDs, continuity backend evidence,
runtime output paths, aggregation command, validator commands, mapper-final
status, git head before finalization, and local commit after finalization.

## Durable Continuity

Slurm-backed controller tasks should use `slurm_dependency` with
`scripts/ops/submit_care_dependency_finalizer.py`, which submits
`jobs/src/care_milestone_finalizer.sh` with `--dependency=afterany:<jobids>`.

If dependency finalizer submission fails, a namespace-local tmux watcher may be
used only when it records session name, PID, command, log path, lock path, and
result directory.

Monitor states (`PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`,
`AWAITING_SACCT`) map to `NEEDS_MONITOR`, not `NEEDS_EVIDENCE` and not
`BLOCKED`. Scheduler block requires the Slurm routing skill threshold.

## GPT Milestone Authoring

Future long-task staging prompts must contain:

```text
## Execution Contract
## Controller Prompt
## Executor Worker Contract
## Mapper Contract
## Reviewer Prompt
```

Future short-task staging prompts must contain:

```text
## Execution Contract
## Executor Prompt
## Reviewer Prompt
```

Long Slurm or overnight prompts without both a Controller Prompt and durable
finalizer contract are invalid.

## Git Boundary

Controller/finalizer local commit only means the current task's lightweight
final packet was committed for separate review. It does not imply route
promotion, validation packaging/upload, hosted metric claim, fold expansion,
scientific stop, or next milestone authorization.

Default controller git policy:

```yaml
auto_git_commit: true
allow_git_commit: true
auto_git_push: false
allow_git_push: false
allow_diagnostic_push: false
```
