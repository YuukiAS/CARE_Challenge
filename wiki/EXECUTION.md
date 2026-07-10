# CARE Execution Flow

## Roles

- `planner`: GPT/ChatGPT strategic planner. Writes route, milestone, controller, executor, mapper, and reviewer contracts.
- `controller`: top-level Codex goal for long/high-resume-risk work. Owns continuity, grounding, subagent coordination, finalizer handoff, validator execution, and operational closeout inside the GPT-authored task.
- `executor`: implementation and authorized command subagent. Writes initial evidence/result packet. Does not self-review or own overnight continuity.
- `mapper`: read-only architecture/evidence mapper. Updates `wiki/`, component tables, and architecture delta when authorized.
- `finalizer`: deterministic stage/script for terminal Slurm accounting, aggregation, validation, and packet finalization. It is not an LLM reviewer.
- `validator`: first-party script that fails closed on protocol, packet, wiki, fingerprint, and known-bad violations.
- `reviewer`: independent read-only Codex thread or short reviewer goal. Writes `review.md`; does not monitor, train, fix, or generate missing artifacts.

## Execution Modes

Short tasks may use:

```text
planner -> executor -> reviewer
```

Long Slurm, overnight, multi-job, or high-resume-risk tasks must use:

```text
planner -> controller
                 |-> executor
                 |-> mapper draft
                 |-> durable watcher/finalizer
                 |-> mapper final
                 |-> validator + commit
            -> separate reviewer
```

## Controller Receipts

Every major controller phase must re-read disk/live state and write fresh receipts:

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
implementation_snapshot.md
finalizer_state.json
```

Normal Slurm states such as `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, and `AWAITING_SACCT` map to monitor states, not blocked completion. Scheduler block requires the Slurm skill threshold: 12 consecutive 2-hour all-pending checks with no job start.
