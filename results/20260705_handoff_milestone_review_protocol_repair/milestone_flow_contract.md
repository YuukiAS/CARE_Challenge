# Milestone Flow Contract

## Executor/Controller Step

For any `task_type: milestone`:

1. read `prompts/MILESTONE_REVIEW_PROTOCOL.md`;
2. verify prerequisite `review.md:<PREVIOUS>_AUDITED_GO` before scientific work, unless this is the initial milestone;
3. execute exactly one milestone;
4. write required outputs under the exact `results/<task_key>/` directory;
5. write `completion_check.md`;
6. write `review_request.md`;
7. update `MANIFEST.md`;
8. stop.

The executor/controller must not:

- write `review.md`;
- mark `*_AUDITED_GO`;
- approve itself;
- start or prepare the next milestone;
- treat `completion_check.md` or `controller_report.md` as independent review.

## Reviewer/Auditor Step

A separate read-only Codex reviewer/auditor:

1. reads the milestone task and completed result directory;
2. checks required outputs, completion gate, forbidden substitutes, and evidence;
3. does not fix code or generate missing artifacts;
4. writes only `results/<task_key>/review.md`;
5. uses the milestone's controlled audit decision.

## Continuation Gate

The next milestone is blocked unless:

```text
results/<previous_task_key>/review.md
```

contains the exact audited-go token required by the next milestone, for example:

```text
M0_AUDITED_GO
```

Any missing review, wrong token, executor-authored review, or same-session self-approval blocks continuation.
