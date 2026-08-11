# CARE Agent-Flow v3 bootstrap manifest

## Current status

The v3 policy and bootstrap assets are committed on `main`. The remote `develop` branch was created from the policy head for the future CARE-ASE faithful reimplementation experiment.

The live loop is intentionally not armed yet:

```text
REQUEST.enabled: false
CURRENT.state: PLAN_REQUESTED
next_action: CONFIGURE_VISUAL_SOURCES_AND_SCHEDULED_TASKS_THEN_ENABLE_REQUEST
```

This prevents the scheduled Planner, Critic or Codex runtime from starting before direct visual sources and exact task bindings are ready.

## Canonical files

```text
prompts/AGENT_FLOW_V3_PROTOCOL.md
automation/agent_flow_v3/ROLE_AUTHORITY_POLICY.md
automation/agent_flow_v3/README.md
automation/agent_flow_v3/schema.json
automation/agent_flow_v3/task_template.json
automation/agent_flow_v3/templates/
automation/agent_flow_v3/planner_scheduled_task_prompt.md
automation/agent_flow_v3/critic_scheduled_task_prompt.md
scripts/automation/validate_agent_flow_v3.py
scripts/automation/agent_flow_v3_runtime.py
scripts/automation/agent_flow_v3_snapshot.py
tests/automation/test_agent_flow_v3.py
.github/workflows/agent-flow-v3-ci.yml
```

## CARE-ASE first-use files

```text
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_loop.md
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_controller.md
automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json
automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json
automation/agent_flow_v3/tasks/care-ase-faithful/REQUIREMENT_LEDGER.json
automation/agent_flow_v3/tasks/care-ase-faithful/SOURCE_SNAPSHOT.json
automation/agent_flow_v3/tasks/care-ase-faithful/VISUAL_SOURCES.json
results/agent_flow_v3/care-ase-faithful/REVIEW_BUNDLE.json
```

## Activation prerequisites

1. Provide stable visual access for every required diagram and pass a scheduled-GPT visual smoke.
2. Create or update the persistent Planner and Critic scheduled tasks from the tracked prompts.
3. Compute and bind the frozen contract SHA after Critic freeze.
4. Set REQUEST `enabled=true` with a new nonce and update CURRENT last.
5. Start the persistent Controller only after CURRENT reaches `PLAN_FROZEN`.

## Safety boundary

No current or historical CARE-ASE training process, checkpoint, permit, Docker artifact or `CURRENT.md` history is modified by this bootstrap. No training, outer access, deployment, upload or merge from `develop` to `main` is authorized.

## 2026-08-05 runtime helper status

The tracked runtime helper can audit public visual raw URLs, validate role-session
receipts, dry-run exact-session watcher routing, and run the production watcher
in `care_agent_flow_v3:Watcher`.

The production watcher polls `origin/develop`, persists processed event keys in
server-local state, and performs live exact-session resumes with role-specific
`CODEX_HOME` when a legal Planner revision event is observed. These checks and
the watcher implementation support infrastructure activation, but they do not
replace the required scheduled GPT Planner/Critic visual smoke or the real
GPT-to-Codex repair-loop smoke. The `care-ase-faithful` request must remain
unarmed until those external scheduled smokes pass with receipts.

The helper also includes `observe-visual-smoke`, a read-only remote observer for
`care-visual-smoke`. It records whether real scheduled-GPT Planner/Critic visual
receipts exist on `origin/develop`, validates nonce and image SHA bindings, and
counts scheduling windows. It must not be used to synthesize or substitute the
required visual receipts.

## 2026-08-07 repair-loop wait authorization

For the active frozen contract SHA and request nonce, deterministic CI success
authorizes the Controller to advance `CI_RUNNING` to
`WAITING_FOR_EXTERNAL_GPT` without another human prompt. This transaction only
updates state, review binding and receipts; it does not generate a Planner
decision, call a Scheduled Task connector, start training, access outer data,
build Docker, upload submissions, send organizer email or merge `develop` to
`main`.

The review is bound to the implementation/integration SHA and CI evidence that
already passed. CI for the later status commit may run after Planner wait begins;
if that status-commit CI fails, the Controller must repair or republish the
transaction instead of blocking before the asynchronous Planner wait.

## 2026-08-11 Stable Review Snapshot simplification

Agent-Flow v3 now binds Planner review identity to stable content snapshots, not
moving Git history. `SOURCE_SNAPSHOT.json` computes `review_target_id` only from
request nonce, frozen contract SHA, requirement ledger SHA, implementation
critical-source digest and verifier critical-source digest. Controller merge
commits, `CURRENT` commits, receipt commits, runtime manifests and CI-record
commits are provenance locators and must not change `review_target_id`.

Current review evidence is collected in `REVIEW_BUNDLE.json`. Historical visual
smoke, session smoke, watcher smoke, bootstrap and retired final-state receipts
remain as provenance but are not Planner-blocking bundle inputs unless the task
explicitly requires them.

Permanent portability principles:

```text
Bind evidence to stable content snapshots, not moving Git history.
Evidence provenance is a DAG, never a hash cycle.
Receipt-only changes must not invalidate expensive scientific execution.
Heavy verification runs only when semantic inputs change.
Fail-closed prevents false PASS; it does not justify maximal re-execution.
```
