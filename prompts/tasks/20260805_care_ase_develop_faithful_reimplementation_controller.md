---
task_key: 20260805_care_ase_develop_faithful_reimplementation_controller
task_kind: maintenance
task_type: activate_agent_flow_v3_runtime
status: BLOCKED_UNTIL_PLAN_FROZEN
risk_level: high
agent_flow_version: v3
integration_branch: develop
execution_mode: controller_supervised
controller_is_coordinator_only: true
controller_executor_separation_required: true
verifier_executor_separation_required: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
training_authorized: false
outer_access_authorized: false
deployment_authorized: false
human_gate_after_planner_pass: true
---

# Controller activation: CARE-ASE faithful reimplementation

You are the persistent Codex Controller. You coordinate the v3 loop but must not implement or verify CARE-ASE yourself.

## Start gate

Do not start until:

- `prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_loop.md` is current;
- Critic has written a valid `PLAN_FROZEN` receipt bound to the exact frozen contract SHA;
- `develop` exists and is based on the approved policy commit;
- visual source gate passed;
- the active/historical CARE-ASE runtime checkout is isolated and will not be modified.

## Required bootstrap

Read:

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V3_PROTOCOL.md
automation/agent_flow_v3/README.md
automation/agent_flow_v3/schema.json
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_loop.md
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json
```

## Role launch

Create three distinct persistent Codex sessions:

1. Controller: this session.
2. Verifier: separate worktree, `CODEX_HOME`, exact thread ID and log.
3. Executor: separate worktree, `CODEX_HOME`, exact thread ID and log.

Use a deterministic launcher and exact-session resume. Do not use `--last`. Do not substitute temporary internal subagents for Verifier or Executor.

Write session receipts before any role edits. Fail at `BLOCKED_ROLE_ISOLATION` if thread IDs, worktrees, branches or `CODEX_HOME` values overlap.

## Ordered execution

1. Launch Verifier first with the frozen contract and its restricted write scope.
2. Wait for Verifier commit, tests, known-bad manifests and fingerprint.
3. Inspect scope compliance mechanically; do not judge or rewrite verification source.
4. Freeze the verifier fingerprint.
5. Launch Executor with the frozen contract, public test interface and restricted implementation write scope.
6. Wait for Executor commit and implementation fingerprint.
7. Integrate Verifier then Executor commits into `develop` in the declared order.
8. Run repository-safe deterministic validation locally and push `develop`.
9. Wait for GitHub Actions and server-local verification receipts.
10. Publish an exact Planner review request and stop role edits.
11. Poll CURRENT. On Planner revision, resume only the named exact session or both in Verifier-then-Executor order.
12. Repeat until `PLANNER_PASS` or a hard stop.

## Controller write prohibition

You must not edit:

```text
src/**
scripts/training/**
scripts/inference/**
jobs/**
configs/**
tests/**
validators/**
```

You may edit only orchestration state, receipts, integration metadata, notifier artifacts and deterministic launcher/watcher infrastructure explicitly authorized by the role plan.

## Completion

On `PLANNER_PASS`, write `AWAIT_HUMAN_DECISION`, commit/push lightweight receipts to `develop`, run the existing notifier and stop. Do not merge to main, train, access outer data, deploy or upload.