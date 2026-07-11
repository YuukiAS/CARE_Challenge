# ChatGPT Rules

This repository uses the `prompts/` handoff protocol. GPT/ChatGPT is the
planning surface; Codex executes only inside a GPT-authored task or milestone
contract.

## Directory Responsibilities

- `START_HERE_FOR_GPT.md`: root entrypoint for new GPT/ChatGPT planning
  threads.
- `GPT_PLANNER_CARE_PROTOCOL.md`: Chinese-first CARE planner protocol.
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`: durable human-readable agent-flow
  protocol.
- `prompts/ACTIVE_POLICY_FILES.yaml`: registry of active rule sources,
  templates, schemas, and required skills.
- `prompts/schemas/agent_flow_policy.yaml`: canonical roles, critic trigger
  policy, git defaults, and publication allowlist.
- `prompts/schemas/milestone_staging.schema.yaml`: direct-executor and
  controller-supervised staging contract.
- `prompts/schemas/planning_review.schema.yaml`: separate GPT critic review
  contract.
- `prompts/schemas/executor_plan.schema.yaml`: executor wave plan contract.
- `prompts/schemas/controller_packet.schema.yaml`: controller packet files and
  conditional receipt contract.
- `prompts/schemas/runtime_review.schema.yaml`: independent runtime reviewer
  contract.
- `wiki/README.md` and `wiki/current_state.yaml`: current architecture and
  latest reviewed predecessor entrypoints.

## Roles

Use only active roles from `agent_flow_policy.yaml`:

```text
planner -> critic -> controller/executor/mapper/finalizer/validator -> reviewer
```

`planner` writes the draft. `critic` is a separate GPT planning-review thread
that does not execute code, submit jobs, or write runtime `review.md`.
`controller` owns long-task continuity. `executor` implements authorized work.
`mapper` maps code/evidence/architecture. `finalizer` is deterministic.
`validator` is fail-closed first-party validation. `reviewer` is the separate
read-only runtime reviewer after packet commit.

Historical `auditor`, `execution_controller`, and strategic-controller names are
legacy aliases only. Do not create a controller-internal auditor.

## Planning Review

Set these machine fields for every staged milestone:

```yaml
task_kind: scientific_milestone | maintenance | hotfix | audit
milestone_number: <positive integer or null>
milestone_id: <canonical Mxx or null>
route_change: true | false
scientific_decision_scope: none | mechanism_signal | promotion_candidate | stop_candidate
planning_review_required: true | false
```

The separate GPT `critic` is required when any trigger in
`agent_flow_policy.yaml` applies: scientific milestone, high risk, system
architecture impact, Slurm runtime continuity, more than one executor, route
change, or non-`none` scientific decision scope.

A critic review lives at:

```text
prompts/tasks/<task_key>_planning_review.md
```

It must use real YAML frontmatter from `planning_review.schema.yaml`, record the
contract hash from `scripts/validation/hash_milestone_contract.py`, and use a
controlled critic decision/token pair. A staging prompt modified after critic
review invalidates the review.

## Milestone Staging

Stage new milestones under:

```text
prompts/shared/M<id>_<short_slug>.md
```

The file must start on line 1 with real YAML frontmatter. `## Execution
Contract` is only the human-readable mirror. Machine fields come from
`milestone_staging.schema.yaml`.

Short/direct work uses:

```text
## Execution Contract
## Executor Prompt
## Reviewer Prompt
```

Long/controller-supervised work uses:

```text
## Execution Contract
## Controller Prompt
## Executor Worker Contract
## Mapper Contract
## Reviewer Prompt
```

Do not paste executor plans into the large shared prompt files. Keep executor
plans at:

```text
prompts/tasks/<task_key>_executor_plan.yaml
```

## CARE Route Bootstrap

Every SRR/MyoPS/Cine route-planning thread must execute
`prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`. GPT visually reads the SRR
route diagrams from ChatGPT Project background files / project materials; repo
paths such as `images/SRR-v2.png`, `images/SRR-v2.5.png`, and
`images/SRR-v3.png` are canonical identifiers, not the required GPT visual
input route. If project-background diagrams are unavailable, block with
`BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE`.

## Dynamic History

For system-level planning, read `wiki/current_state.yaml` to find the latest
reviewed predecessor, then read:

```text
wiki/history/COMPARISON.md
wiki/history/<predecessor>/README.md
wiki/history/<predecessor>/COMPONENTS.csv
wiki/history/<predecessor>/components/*.md
```

If a task intentionally uses a non-latest baseline, it must declare
`history_baseline_override` and `history_baseline_override_reason`.

## Runtime Review Boundary

Runtime `review.md` belongs only to the independent `reviewer` after the packet
is locally committed. Reviewer may support/reject claims, request
monitor/evidence/revision, or allow the next planning round. Reviewer must not
start another milestone, fold expand, package/upload validation, push, resume
jobs, or fix missing artifacts.

## Slurm And Monitor Packets

Before planning or executing any Slurm submission, read
`.agents/skills/slurm-routing-partition/SKILL.md`.

`MONITOR_PACKET_IS_NOT_COMPLETION` is global: submitted-only jobs, pending
jobs, running jobs, watchers, and awaiting-accounting packets are not
completion packets. After Slurm completes, rerun aggregation/evidence
collection and commit tracked lightweight evidence before requesting review.

## Git And Publication

Default push is false. User pushes manually. Lightweight publication is governed
by `agent_flow_policy.yaml`: schema-listed small Markdown/CSV/JSON files may be
committed when authorized; checkpoints, predictions, NIfTI, logs, secrets,
upload packages, and raw data remain forbidden.
