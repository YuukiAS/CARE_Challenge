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

## Activation boundary

The initial CARE-ASE task contract is:

```text
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_loop.md
```

The workflow must not modify the currently running or historical CARE-ASE checkout, permit, checkpoint lineage, Docker artifacts or `CURRENT.md` history. It must not start formal training before Planner PASS and a later user decision.