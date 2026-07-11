# Start Here For GPT

This is the root entrypoint for any new GPT/ChatGPT planning thread reading this repository. Read this file before writing CARE milestones, Codex goals, handoffs, route judgments, or review instructions.

## Required Reading Order

1. `START_HERE_FOR_GPT.md`
2. `GPT_PLANNER_CARE_PROTOCOL.md`
3. `AGENTS.md`
4. `README.md`
5. `prompts/CHATGPT_RULES.md`
6. `prompts/GPT_HARD_GATE_PROMPT.md`
7. `prompts/MILESTONE_REVIEW_PROTOCOL.md`
8. `prompts/AGENT_FLOW_V2_PROTOCOL.md`
9. `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`

Do not rely only on old chat summaries, memory, or natural-language recaps when planning SRR/MyoPS/Cine routes.

## Future Milestone Prompt Authoring

For any future CARE milestone, GPT/ChatGPT must write both the Codex executor prompt content and the independent reviewer prompt content. Do not provide only an executor prompt or only a reviewer prompt.

Because direct GPT edits to the large canonical shared files can fail or corrupt context, author each new milestone first as a standalone Markdown staging file under `prompts/shared/` named `M<id>_<short_slug>.md`, for example `M8_editor_grade_leaderboard_sprint.md`. The staged file is temporary: a later Codex maintenance step will split/merge its content into `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md`, then delete the standalone staging file after successful merge.

Every staged milestone file matching `prompts/shared/M[0-9]*_*.md` must start on
line 1 with real YAML frontmatter. `## Execution Contract` is a human-readable
mirror only. The validator must reject a staging file with no frontmatter, a
frontmatter/body mismatch, a missing `executor_plan_path`, or an executor plan
that fails `scripts/ops/validate_executor_plan.py`.

M10, later system-level redesign, and any high-risk milestone also require a
pre-execution planning review by a separate GPT thread before Codex controller
execution:

```text
planner GPT -> separate GPT critic -> Codex merge/validator -> controller
```

This planning critic is not a controller subagent and is not the runtime
reviewer after execution. Use frontmatter fields
`planning_review_required: true`, `planning_reviewer: separate_gpt_thread`,
`planning_review_path`, `planning_review_token`, and
`planning_reviewed_commit`. Without a non-empty planning review token,
M10/system-level staging can only be `DRAFT_FOR_GPT_REVIEW`,
`NEEDS_PLANNING_REVISION`, or `BLOCKED_HANDOFF_REVIEW`, never `READY` or
`READY_FOR_CODEX_MERGE`.

Short tasks must use this structure:

```text
## Execution Contract
## Executor Prompt
## Reviewer Prompt
```

Long Slurm, overnight, multi-job, controller-supervised, or high-resume-risk tasks must use this structure:

```text
## Execution Contract
## Controller Prompt
## Executor Worker Contract
## Mapper Contract
## Reviewer Prompt
```

Long Slurm or overnight tasks without a Controller Prompt and durable finalizer contract are invalid.

When a staged long milestone is later merged into the shared prompts, merge
`Execution Contract`, `Controller Prompt`, `Executor Worker Contract`, and
`Mapper Contract` into `prompts/shared/EXECUTOR_PROMPTS.md`. Merge only
`Reviewer Prompt` into `prompts/shared/REVIEWER_PROMPTS.md`. Keep any
`executor_plan.yaml` as `prompts/tasks/<task_key>_executor_plan.yaml`; do not
paste executor plans into the large shared prompt files.

## Agent-Flow v2 Handoff Model

Before writing a CARE handoff, read `prompts/AGENT_FLOW_V2_PROTOCOL.md` and the current architecture entry at `wiki/README.md`. Use only the v2 role names from the permanent protocol: `planner`, `controller`, `executor`, `mapper`, `finalizer`, `validator`, and `reviewer`. New tasks must not introduce an internal `auditor` role; historical `auditor` fields are legacy aliases for the independent `reviewer`.

Every new CARE milestone or controller task must explicitly declare:

```yaml
execution_mode: direct_executor | controller_supervised
requires_execution_controller: true | false
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/<task_key>_executor_plan.yaml
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

Use `controller_supervised` for overnight, long Slurm, multi-job, or high-resume-risk work. Default to exactly one executor and one mapper unless the GPT-authored task graph explicitly grants more isolated slots. Any `executor_count > 1`, `executor_slots > 1`, or `parallel_execution_allowed: true` task must include a validated executor plan with isolated write scopes, worktrees, runtime outputs, logs, locks, and merge order. The controller owns continuity and phase grounding; the executor performs authorized implementation/jobs; the mapper is read-only architecture/evidence mapping; the finalizer is deterministic `FINALIZER_A` accounting/aggregation plus `FINALIZER_B` validation/local packet commit; the reviewer is a separate read-only thread after the final packet is committed. Controller reports written before review must use `route_promotion_decision: NOT_REVIEWED`, `route_negative_decision: NOT_REVIEWED`, and `scientific_resolution_status: AWAITING_REVIEW`.

For architecture-affecting work, use `.agents/skills/care-mapper/SKILL.md` and the helpers in `scripts/architecture/`. A route or handoff update is not complete if `wiki/COMPONENTS.csv`, `wiki/architecture.yaml`, required figures, Toolkit healthcheck, or mapper/finalizer evidence is stale.

## History Reading For M10 / System-Level Redesign

Before writing M10 or any later system-level milestone, GPT must read:

- `wiki/history/COMPARISON.md`
- `wiki/history/M08/README.md`
- `wiki/history/M09/README.md`
- `wiki/history/M09/COMPONENTS.csv`
- every file matching `wiki/history/M09/components/*.md`

If the milestone touches only a small component subset, GPT may read M09
README, COMPARISON, COMPONENTS, and the relevant component files. For M10 or
system-level redesign, all M09 component files are mandatory. GPT output must
list the exact history files read before proposing execution.

## MONITOR_PACKET_IS_NOT_COMPLETION

Any GPT/ChatGPT milestone, handoff, or review instruction must enforce this rule: a monitor packet, pending Slurm job packet, watcher packet, or submitted-only job packet is not completion.

If `completion_check.md` includes `NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or equivalent pending/monitor language, GPT must not ask a reviewer to grant audited-go. The correct reviewer decision is `NEEDS_EVIDENCE` or `NEEDS_MONITOR`.

After a Slurm job completes, the executor must rerun the relevant aggregator/evidence collector and commit tracked lightweight evidence containing job id, state, exit code, runtime, log path, runtime output path, aggregation command, and updated tracked evidence files. `commands_run.md` with only `sbatch submitted`, `squeue pending`, `PENDING Priority`, or pending `sacct` is not completion evidence.

This applies to M7 follow-up2/follow-up3 and all future milestones.

## Slurm Job Planning Skill

Before writing any GPT/ChatGPT milestone, Codex goal, handoff, or execution instruction that will submit a Slurm job, read and apply `.agents/skills/slurm-routing-partition/SKILL.md`. The same skill must be used before every actual `sbatch` or `srun` submission in this repo.

The skill is the local source for CARE partition priority, fallback routing, routing races, QOS/header defaults, monitor packet handling, and scheduler block rules. For goal tasks, if all submitted routing partitions remain pending, poll every 2 hours; only after 12 consecutive 2-hour checks, 24 hours total, with every submitted routing partition still pending and no job started may the goal be marked blocked for scheduler saturation.

## SRR/MyoPS/Cine Route Bootstrap

Before writing any SRR/MyoPS/Cine milestone, Codex goal, handoff, or route decision, read the SRR route diagrams from the current ChatGPT Project background files / project materials. Use these canonical repository filenames and versions as identifiers:

- `images/SRR-v2.png`
- `images/SRR-v2.5.png`
- `images/SRR-v3.png`
- any later SRR/MyoPS route diagrams present under `images/`

The repository image paths remain the canonical filenames and version references, but they are not the required GPT visual-reading entrypoint. Do not rely on GitHub connector PNG blobs, SHA/base64 metadata, filenames, old chat summaries, memory, or text recaps as a substitute for visual reading through ChatGPT Project background materials or images uploaded into the current conversation.

Follow `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md` exactly. After reading the diagrams, first state the route objective in your own words.

The recovered route objective must preserve this meaning: SRR-MyoPS is availability-aware selective retrieval plus a semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, and explicit losses/objectives. nnU-Net or another strong segmentation model may be used only as anchor, context, evidence, or safety source. Do not downgrade SRR into optional post-processing or a generic fallback around nnU-Net.

If the diagrams cannot be accessed or visually interpreted from ChatGPT Project background materials, block before generating any milestone. Report `BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE`, list the missing versions, and ask the user to add the diagrams to the ChatGPT Project background materials or upload them into the current conversation.
