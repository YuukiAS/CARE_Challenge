# CARE Agent-Flow v3 Protocol

## 1. Scope and precedence

Agent-Flow v3 is an explicit opt-in workflow for high-risk scientific implementation where the Controller must not implement or verify its own work. It does not silently replace Agent-Flow v2 for existing tasks. A task uses v3 only when its frozen contract declares:

```yaml
agent_flow_version: v3
integration_branch: develop
planner_reentry_required: true
critic_freeze_required: true
controller_executor_separation_required: true
verifier_executor_separation_required: true
```

The first authorized use is the CARE-ASE faithful reimplementation experiment on the remote `develop` branch. `main` remains the stable evidence and policy branch. Existing CARE-ASE training, checkpoints, permits, Docker artifacts and current-state history must not be rewritten by this experiment.

## 2. Active roles

Agent-Flow v3 uses exactly five LLM roles.

1. `planner` — a persistent scheduled GPT task. It authors the initial scientific contract and later re-enters after implementation to review the exact contract, implementation, verifier fingerprint, CI evidence and runtime receipts. It returns implementation or verification findings, or `PLANNER_PASS`.
2. `critic` — a separate persistent scheduled GPT task. It reviews the Planner draft once per contract revision cycle, directly repairs omissions and ambiguity, and freezes one exact contract SHA. It does not execute code. It returns to the Planner only when a scientific choice genuinely requires user judgment.
3. `controller` — a persistent Codex session. It is only a coordinator and state owner. It launches/resumes the Verifier and Executor, maintains exact thread/session receipts, merges their commits into `develop`, runs deterministic orchestration, routes Planner findings, and stops at the human gate. It must not edit implementation or verification source.
4. `verifier` — a separate persistent Codex session with its own worktree, `CODEX_HOME`, exact thread ID and write scope. It writes validators, tests, mutation cases, known-bad fixtures and verification receipts. It must not edit model, training, inference or deployment implementation.
5. `executor` — a separate persistent Codex session with its own worktree, `CODEX_HOME`, exact thread ID and write scope. It writes model, training, inference and deployment implementation. It must not edit frozen verification source or weaken verification gates.

There is no separate Reviewer role in v3. After deterministic CI passes, the Planner performs the implementation review and drives the repair loop. The only human action required during the loop is resolving an explicitly blocked scientific choice; otherwise the first normal human gate is after `PLANNER_PASS`.

Deterministic `validator` and `finalizer` scripts remain tools, not additional LLM roles.

## 3. Hard separation rule

The Controller, Verifier and Executor must be three distinct persistent Codex sessions. Logical role labels inside one Codex goal are insufficient.

Each role must have a unique:

- exact Codex thread/session ID;
- `CODEX_HOME`;
- worktree;
- local branch;
- PID or process receipt when active;
- log path;
- state file;
- write scope;
- last commit SHA.

The Controller may launch roles through a deterministic local launcher and later resume them with an exact session ID. It must never use `--last`, keystroke injection into an unrelated TUI, or an unrecorded temporary subagent for Verifier or Executor work.

A short-lived internal subagent may be used only for read-only mapping, code search or evidence collection. It cannot satisfy the Verifier or Executor role.

The task is invalid when any of the following are equal:

```text
controller_thread_id == verifier_thread_id
controller_thread_id == executor_thread_id
verifier_thread_id == executor_thread_id
controller_worktree == verifier_worktree
controller_worktree == executor_worktree
verifier_worktree == executor_worktree
```

## 4. Branch and worktree model

The remote integration branch is:

```text
develop
```

Only the Controller pushes `develop`. Verifier and Executor use local-only branches and worktrees; they commit locally and return exact commit SHAs to the Controller. The Controller integrates them in the frozen order and pushes the resulting exact integration SHA.

Recommended local layout:

```text
${CARE_AGENT_FLOW_WORKTREE_ROOT}/<task_id>/controller
${CARE_AGENT_FLOW_WORKTREE_ROOT}/<task_id>/verifier
${CARE_AGENT_FLOW_WORKTREE_ROOT}/<task_id>/executor

${CARE_CODEX_HOME_ROOT}/CARE_<task_id>_CONTROLLER
${CARE_CODEX_HOME_ROOT}/CARE_<task_id>_VERIFIER
${CARE_CODEX_HOME_ROOT}/CARE_<task_id>_EXECUTOR

${CARE_AGENT_FLOW_STATE_ROOT}/<task_id>/
```

Concrete server values belong in ignored local config or shell environment, not in tracked requests.

`main` must not receive experimental CARE-ASE implementation commits until the user explicitly approves promotion after Planner PASS.

## 5. Ordered lifecycle

1. Planner reads current remote state, scientific materials and visual architecture sources, then publishes a complete draft contract.
2. Critic independently audits the draft, directly repairs ambiguity or missing gates, rechecks the whole contract, and freezes an exact contract SHA.
3. Controller captures the frozen contract and creates three isolated Codex session receipts.
4. Controller launches Verifier first.
5. Verifier creates the public verification contract, fail-closed validators, mutation cases and known-bad fixtures, then returns a verifier commit and fingerprint.
6. Controller freezes the verifier fingerprint and launches Executor.
7. Executor implements the architecture without editing verification source, then returns an implementation commit.
8. Controller integrates Verifier and Executor commits into `develop` and pushes the exact integration SHA.
9. GitHub Actions performs deterministic tracked checks. Server-local validation performs tests requiring private data, GPU, Slurm or hidden fixtures.
10. When deterministic checks pass, the Controller may publish a
    `READY_FOR_PLANNER_REVIEW` / `WAITING_FOR_EXTERNAL_GPT` transaction for the
    current frozen contract and request nonce. This transaction is an internal
    v3 repair-loop state update, not a human approval point. The Scheduled
    Planner review is bound to the implementation/integration SHA and CI
    evidence that already passed; the state-update commit may itself trigger
    deterministic CI after the Planner wait starts. If that later state-update
    CI fails, the Controller must discard or repair the review transaction and
    republish it rather than treating pre-wait CI on the status commit as a
    blocker.
11. Planner reviews the exact frozen contract SHA, integration SHA, implementation fingerprint, verifier fingerprint, complete diff, CI evidence and required runtime receipts.
12. Planner returns exactly one of:
   - `PLANNER_REVISE_EXECUTOR`;
   - `PLANNER_REVISE_VERIFIER`;
   - `PLANNER_REVISE_BOTH`;
   - `PLANNER_PASS`.
13. On revision, Controller resumes only the named exact session or both sessions in the declared order, integrates new commits, reruns CI and returns to Planner.
14. On `PLANNER_PASS`, Controller writes `AWAIT_HUMAN_DECISION`, sends the existing notifier and stops.

## 6. Critic behavior

The Critic is not a slow relay that always sends work back to the Planner. It must directly repair the staged contract when the repair is logically determined by the Planner objective, repository evidence and existing policy. It returns `NEEDS_USER_SCIENTIFIC_CHOICE` only when two or more scientifically meaningful alternatives remain and choosing among them changes the hypothesis, model, data, loss, evaluation or resource budget.

Critic freeze is valid only when it records:

```text
planner_draft_sha
critic_input_sha
frozen_contract_sha256
frozen_contract_commit
visual_sources_reviewed
open_scientific_choices: []
critic_decision: PLAN_FROZEN
```

## 7. Verifier boundary

The Verifier owns only verification code and evidence. Its write scope must be declared explicitly, normally including:

```text
tests/**
validators/**
automation/agent_flow_v3/**
results/<task_id>/verification/**
```

The Verifier must not edit:

```text
src/**
scripts/training/**
scripts/inference/**
jobs/**
model configs or scientific contracts
```

The verification package must include public tests and protected adversarial tests. Executor may read public tests and failure identifiers, but protected fixture details should not be copied into the Executor prompt. This is process isolation, not a security claim; the hard guarantee is separate write scopes and independent Planner review.

## 8. Executor boundary

The Executor owns implementation code only. Its write scope normally includes:

```text
src/**
scripts/training/**
scripts/inference/**
jobs/**
configs/**
results/<task_id>/implementation/**
```

The Executor must not:

- modify or delete frozen validators;
- weaken assertions, known-bad fixtures or mutation cases;
- change the frozen scientific contract;
- remove architecture components to make tests pass;
- shorten required runs or replace real evidence with static receipts;
- start training, outer evaluation, Docker publication or upload unless separately authorized after Planner PASS.

## 9. GitHub Actions boundary

GitHub Actions is a deterministic evidence layer, not an intelligent reviewer. It should immediately reject malformed state, stale SHA bindings, missing role receipts, overlapping write scopes, contract drift, verifier drift, syntax failures and repository-safe unit tests.

GitHub-hosted CI must not pretend to validate private data, GPU execution, Slurm, hidden server fixtures or scientific fidelity. Those checks run through the isolated Verifier/Controller environment and are then inspected by the Planner.

A green GitHub Actions run is necessary but never sufficient for `PLANNER_PASS`.

## 10. Planner implementation review

Planner review is bound to exact immutable inputs:

```text
frozen_contract_sha256
integration_commit_sha
implementation_fingerprint_sha256
verifier_fingerprint_sha256
ci_run_id_and_status
runtime_receipt_manifest_sha256
review_round
request_nonce
```

Any new critical implementation or verifier commit invalidates the previous Planner decision. Planner must review the current full implementation before reading previous findings, then use previous findings only to verify closure.

Planner PASS means the implementation is sufficiently faithful to the frozen contract to return to the user. It does not prove scientific superiority and does not authorize training or protected evaluation.

## 11. State machine

Allowed normal states are:

```text
PLAN_REQUESTED
PLAN_READY_FOR_CRITIC
PLAN_FROZEN
CONTROLLER_INITIALIZING
VERIFIER_RUNNING
VERIFIER_FROZEN
EXECUTOR_RUNNING
INTEGRATION_RUNNING
CI_RUNNING
READY_FOR_PLANNER_REVIEW
WAITING_FOR_EXTERNAL_GPT
PLANNER_REVISE_EXECUTOR
PLANNER_REVISE_VERIFIER
PLANNER_REVISE_BOTH
PLANNER_PASS
AWAIT_HUMAN_DECISION
```

Exceptional states are:

```text
BLOCKED_VISUAL_SOURCES
BLOCKED_ROLE_ISOLATION
BLOCKED_CONTRACT_DRIFT
BLOCKED_CI
STOPPED_STUCK
STOPPED_DEADLINE
STOPPED_MAX_ROUNDS
```

Controller may respond only to the exact current state and nonce. It must not react to generic commits.

For an already-authorized loop under the same frozen contract SHA and request
nonce, the following transitions are Controller-internal operations and must
not require another human approval:

```text
CI PASS
-> WAITING_FOR_EXTERNAL_GPT
-> Planner review
-> PLANNER_REVISE_*
-> exact production thread repair
-> integration
-> CI
-> WAITING_FOR_EXTERNAL_GPT
```

Ordinary CI, state migration, Planner trigger, Verifier/Executor repair,
production thread rebuild and runtime-binding repair are not human approval
points. Human approval is required only when the frozen scientific contract
must change, the request nonce must be rebuilt in a way that changes the
scientific task, `NEEDS_USER_SCIENTIFIC_CHOICE` is reached, or the action would
start formal training, access outer data, promote `develop` to `main`, build or
upload Docker/submissions, send organizer email, or make another decision the
contract reserves for the user.

`WAITING_FOR_EXTERNAL_GPT` is a non-terminal orchestration state for asynchronous
GitHub-mediated Scheduled GPT work. It must record
`external_wait_started_utc`, `external_wait_deadline_utc`,
`expected_state_or_artifact`, `last_observed_remote_sha`, and `last_poll_utc`.
The default deadline must be at least four hours after the wait starts. Before
that deadline, a missing Planner/Critic artifact is not operationally blocked:
the controller or stage orchestrator must keep fetching `origin/develop` and
continue as soon as the expected state or artifact appears. Lack of a local
Scheduled Task connector is not a block reason because v3 handoff can proceed
asynchronously through GitHub commits.

## 12. Visual architecture sources

For architecture-sensitive work, Planner and Critic must visually inspect the required diagrams. Chat memory, filenames, repository metadata and text summaries do not substitute for visual inspection.

A task may satisfy this through ChatGPT Project files, a public repository, a public static website or another stable directly accessible image host. The contract must bind each image by version, URL or connector path, and SHA256 when available. If the scheduled task cannot visually read the images, planning stops at `BLOCKED_VISUAL_SOURCES` rather than inventing the architecture.

## 13. Human boundary

The v3 loop requires no manual independent acceptance between Critic freeze and Planner PASS. It may continue through repeated Verifier/Executor repair rounds while the user is offline.

After `PLANNER_PASS`, all automated roles stop at `AWAIT_HUMAN_DECISION`. The loop must not automatically:

- merge `develop` into `main`;
- start formal training;
- access protected outer data;
- select a scientific candidate;
- build or upload a final Docker image;
- send an organizer email;
- authorize a new experiment.

These remain user decisions.
