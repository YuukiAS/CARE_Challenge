# CARE Agent-Flow v3 automation

This directory is the repository-facing state and validation layer for the explicitly authorized `develop`-branch experiment defined in `prompts/AGENT_FLOW_V3_PROTOCOL.md`.

## Practical flow

```text
scheduled GPT Planner
-> scheduled GPT Critic directly repairs/freezes contract
-> persistent Codex Controller
-> persistent isolated Codex Verifier
-> persistent isolated Codex Executor
-> Controller integrates to develop
-> GitHub Actions + server-local verification
-> scheduled GPT Planner reviews exact SHA
-> Controller resumes Verifier/Executor on REVISE
-> PLANNER_PASS
-> AWAIT_HUMAN_DECISION
```

There is no separate Reviewer role. Planner performs the post-implementation review. Controller, Verifier and Executor must be different persistent Codex sessions.

## Remote branch boundary

- `main`: stable policy, current evidence and approved code.
- `develop`: remote integration branch for this workflow.
- role branches: local-only unless a later user instruction explicitly authorizes remote publication.

Only Controller pushes `develop`. No role merges `develop` to `main` automatically.

## Files

- `schema.json`: state and request requirements.
- `task_template.json`: reusable request template.
- `tasks/<task_id>/REQUEST.json`: exact frozen task request.
- `tasks/<task_id>/CURRENT.json`: current machine state, updated last in every transaction.
- `results/<task_id>/`: role receipts, fingerprints, CI receipts and Planner review artifacts.
- `scripts/automation/validate_agent_flow_v3.py`: repository-safe deterministic validator.
- `scripts/automation/agent_flow_v3_runtime.py`: server-local helper for visual URL/SHA audit,
  role-session receipt validation, exact-session watcher checks, and the production
  watcher process.
- `.github/workflows/agent-flow-v3-ci.yml`: GitHub-hosted deterministic CI.

## Required session receipt

Each Controller, Verifier and Executor receipt must include:

```text
role
thread_id
codex_home
worktree
local_branch
pid_or_process_status
log_path
state_path
write_scope
forbidden_scope
last_commit_sha
started_utc
updated_utc
```

A receipt with missing or duplicate thread IDs, worktrees or `CODEX_HOME` paths is invalid.

## CI boundary

GitHub Actions validates tracked state, role separation, SHA bindings, JSON structure, Python syntax and repository-safe unit tests. GPU, private data, hidden adversarial fixtures and Slurm checks remain server-local and must be represented by exact receipts for Planner review.

Server-local v3 checks may run:

```bash
python scripts/automation/agent_flow_v3_runtime.py audit-visual-sources --repo-root .
python scripts/automation/agent_flow_v3_runtime.py validate-role-receipts --receipt <controller> --receipt <verifier> --receipt <executor>
python scripts/automation/agent_flow_v3_runtime.py watcher-once --repo-root . --task-id <task_id> --dry-run
```

The watcher uses exact thread IDs and must not use `--last`. A dry-run receipt proves
routing and command construction only; it is not a substitute for a live scheduled
Planner/Critic decision.

## Production watcher

The production watcher is implemented inside `agent_flow_v3_runtime.py` and does
not rely on a shell wrapper loop. It polls every 60 seconds by default, fetches
`origin/develop`, reads `REQUEST.json` and `CURRENT.json` from that remote ref,
validates nonce/SHA/review-round bindings, persists processed event keys under
the server-local state root, and resumes only the exact role thread requested by
the Planner decision.

Start it in the dedicated tmux window:

```bash
python scripts/automation/agent_flow_v3_runtime.py start-watcher \
  --repo-root . \
  --task-id <task_id>
```

Inspect or stop it:

```bash
python scripts/automation/agent_flow_v3_runtime.py status-watcher --task-id <task_id>
python scripts/automation/agent_flow_v3_runtime.py stop-watcher --task-id <task_id>
```

For live revision events, the watcher runs:

```text
codex exec -C <role-worktree> resume <exact-thread-id> -
```

with the role-specific `CODEX_HOME` in the process environment and the exact
Planner repair artifact on stdin. Each resume writes PID, prompt SHA, exit code,
stdout/stderr logs, and timing under the server-local state/log roots. Duplicate
events, stale nonce/SHA/review-round bindings, wrong thread receipts, disabled
requests, and an already active role process fail closed without stopping the
long-running watcher.

## Authorized Planner wait transaction

For a task that is already inside the same frozen contract SHA and request
nonce, the Controller may automatically publish the review-state transaction:

```text
CI PASS -> WAITING_FOR_EXTERNAL_GPT
```

This is an internal Agent-Flow v3 repair-loop step, not a human approval point
and not a local Scheduled Task connector call. The Planner review binds to the
implementation/integration SHA and CI evidence that already passed. The
`WAITING_FOR_EXTERNAL_GPT` status commit may trigger its own deterministic CI
after the wait starts; if that status-commit CI fails, the Controller repairs or
republishes the review transaction instead of treating the pre-wait status commit
as a blocker.

For the isolated visual smoke, use the observer below to poll `origin/develop`
without invoking any Scheduled Task connector:

```bash
python scripts/automation/agent_flow_v3_runtime.py observe-visual-smoke \
  --repo-root . \
  --from-origin \
  --fetch \
  --output results/agent_flow_v3/care-visual-smoke/visual_smoke_final.json
```

The observer requires real scheduled-GPT `planner_visual_receipt.json` and
`critic_visual_receipt.json` commits, binds them to the request nonce and image
SHA256 values, and counts completed scheduling windows. Missing receipts return a
nonzero exit code because the smoke has not passed.

## Activation boundary

The initial CARE-ASE task contract is:

```text
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_loop.md
```

The workflow must not modify the currently running or historical CARE-ASE checkout, permit, checkpoint lineage, Docker artifacts or `CURRENT.md` history. It must not start formal training before Planner PASS and a later user decision.
