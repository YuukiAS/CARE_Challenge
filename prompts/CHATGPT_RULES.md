# ChatGPT Rules

This repository uses the `prompts/` handoff protocol. ChatGPT/GPT is the
strategic planner and the user-supervised strategic controller.

## Directory Responsibilities

- `START_HERE_FOR_GPT.md`: root entrypoint for new GPT/ChatGPT planning
  threads before CARE milestone, Codex goal, handoff, or route planning.
- `GPT_PLANNER_CARE_PROTOCOL.md`: Chinese-first startup prompt and checklist
  for GPT planner threads before milestone authoring.
- `prompts/AGENT_RULES.md`: Codex execution rules.
- `prompts/CHATGPT_RULES.md`: GPT task/review/next-task rules.
- `prompts/HANDOFF_ROLES.md`: strategic and execution role definitions.
- `prompts/HANDOFF_STATE_MACHINE.md`: controlled task states.
- `prompts/CONTROLLER_TASK_PROTOCOL.md`: controller task rules.
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`: route promotion vs diagnostic
  publication migration note.
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`: experiment adequacy, route-negative,
  and scientific completion migration note.
- `prompts/HANDOFF_GATE_POLICY.md`: hard-gate policy for exact task graph,
  strict validators, completion-check readiness, and smoke-scale evidence
  classification.
- `prompts/GPT_HARD_GATE_PROMPT.md`: GPT checklist to apply before writing a
  high-risk CARE controller goal.
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`: mandatory image
  bootstrap protocol for SRR/MyoPS/Cine route planning from ChatGPT Project
  background materials, using repository image paths as canonical version
  references.
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`: two-step milestone executor/reviewer
  gate for SRR-v3 and future milestone chains.
- `wiki/README.md`: root architecture/current-state entry for GPT planner,
  controller, mapper, and reviewer threads.
- `.agents/skills/care-mapper/SKILL.md`: repo-local mapper skill for
  architecture/component/fingerprint/wiki updates.
- `prompts/MECHANISM_GATE_TEMPLATE.md`: reusable evidence-gate pattern.
- `prompts/tasks/<task_key>.md`: GPT-authored task entry.
- `results/<task_key>/result.md`: executor report and evidence index.
- `results/<task_key>/review.md`: independent evidence audit.
- `results/<task_key>/controller_report.md`: controller summary for controller
  tasks.
- `docs/notes/`: reference notes, not execution entries.
- `docs/wiki/`: durable knowledge, not execution entries.

## Strategic Planning Rule

Planner defaults:

- `planner: "ChatGPT/GPT thread"`
- `strategic_controller: "user-supervised GPT thread"`

Do not assign open-ended direction search, research route choice, or global
planning to Codex by default. Codex can supervise execution only when GPT has
written a controller task with goal, scope, evidence gate, forbidden substitutes,
and failure escalation policy.

## Language Policy

Keep protocol keys, YAML fields, file paths, controlled state enums, command
names, code identifiers, and API names in English. Write human-readable prose in
task bodies, reviews, notes, and next-task explanations in the user's language
or the target repository's project language.

If the target project prefers Chinese, write the explanatory task/review/report
prose primarily in Chinese while keeping machine-readable protocol fields and
controlled values in English. Do not force English prose globally merely because
the Bridge Kit documentation is written in English. Project-level language rules
win unless they would break protocol fields.

## CARE-Specific Planning Overlay

For CARE tasks, GPT is the strategic planner and strategic controller. Codex may execute or supervise only inside a GPT-authored task; it must not be asked to discover a new research direction on its own.

Every new GPT/ChatGPT planning thread must start from `START_HERE_FOR_GPT.md` and `GPT_PLANNER_CARE_PROTOCOL.md`. Before writing any new SRR/MyoPS/Cine milestone, Codex goal, handoff, or route judgment, GPT must complete `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`: visually read `v2` and later SRR/MyoPS diagrams from ChatGPT Project background files / project materials, use `images/SRR-v2.png`, `images/SRR-v2.5.png`, `images/SRR-v3.png`, and later repository diagram paths only as canonical version references, state the recovered route objective, and block with `BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE` if the Project background diagrams cannot be accessed or interpreted.

Before planning, GPT must read `wiki/README.md` and treat `wiki/COMPONENTS.csv` plus `wiki/architecture.yaml` as the current architecture observability entry. If a task changes model architecture, loss wiring, dataflow, export behavior, Cine temporal paths, or controller observability, the task must enable mapper and declare `architecture_impact`, `wiki_update_required`, and `diagram_update_required`.

Use agent-flow v2 role names for new tasks: `planner`, `controller`, `executor`, `mapper`, `finalizer`, `validator`, and `reviewer`. Do not introduce an internal controller child named `auditor`; historical `auditor` fields are legacy aliases for the independent read-only `reviewer`.

Before planning any milestone, Codex goal, handoff, or execution instruction that will submit a Slurm job, GPT must read and apply `.agents/skills/slurm-routing-partition/SKILL.md`. That skill must also be used before every actual `sbatch` or `srun` submission in this repo. For goal tasks, all-pending scheduler states may be marked blocked only after 12 consecutive 2-hour checks, 24 hours total, where every submitted routing partition is still pending and no job has started.

When generating any CARE model, experiment, external-method, registration, temporal Cine, missing-modality, proposal/refinement, fold-expansion, validation-package, or submission-related task, decide explicitly whether it is `execution_mode: direct_executor` or `execution_mode: controller_supervised`.

Normal CARE execution tasks must declare `mechanism_class`, `target_metric`, `same_split_baseline` when relevant, `required_evidence`, `forbidden_substitutes`, `promotion_gate` or `route_promotion_gate`, `experiment_adequacy_gate`, `route_negative_gate`, `scientific_completion_gate`, `failure_escalation_policy`, and `review_required: true`. Controller-supervised tasks must also declare `controller_subtasks`, `executor_subtasks`, `mapper_subtasks` when mapper is enabled, `reviewer_prompt_path`, `controller_report_path`, `route_promotion_gate`, `diagnostic_publication_gate`, `diagnostic_publication_scope`, `blocked_after_diagnostic_publication`, `experiment_adequacy_gate`, `route_negative_gate`, `scientific_completion_gate`, `allow_git_commit`, and `allow_git_push`.

Reference the Bridge Kit state machine for handoff states and `prompts/CARE_OVERLAY_GATES.md` plus the installed `medical-imaging-deep-learning` skill for mechanism gates. Do not copy the full skill text into each task.

For milestone chains such as SRR-v3, apply
`prompts/MILESTONE_REVIEW_PROTOCOL.md`. GPT must issue one milestone at a time.
The executor/controller prompt must require `completion_check.md` and
`review_request.md`, must forbid writing `review.md`, and must forbid starting
the next milestone. GPT must then issue a separate read-only reviewer prompt.
Only a `review.md` containing the milestone's exact audited-go token authorizes
the next milestone.

When authoring a future milestone, GPT must provide both sides of the contract:
the Codex executor prompt and the independent reviewer/auditor prompt. It must stage the
new milestone prompt as a standalone Markdown file under `prompts/shared/` named
`M<id>_<short_slug>.md`, for example `M8_editor_grade_leaderboard_sprint.md`.
Use clear section headings for executor and reviewer content. Do not ask GPT to
write directly into the large `prompts/shared/EXECUTOR_PROMPTS.md` and
`prompts/shared/REVIEWER_PROMPTS.md` files for new milestone drafting; a later
Codex maintenance step will split/merge the staged file into those canonical
shared files and delete the standalone staging file after merge.

Before writing a high-risk CARE controller task, apply
`prompts/GPT_HARD_GATE_PROMPT.md` and require `prompts/HANDOFF_GATE_POLICY.md`
as a completion gate. A controller task must list blocking subtasks exactly and
must not allow final audit, route promotion, scientific stop, fold expansion,
validation packaging, or upload when required result directories, exact output
filenames, completion-check readiness, strict validator success, or minimum
effective training evidence are missing.

Do not issue high-risk CARE implementation, fold expansion, validation packaging, upload, or route-promotion tasks without a review or audit gate. A result file is evidence for review; it is not authorization for the next task unless there is a review, audit, controller report, or explicit user override.

Diagnostic artifact publication is a separate controller outcome. It lets GPT
planner see reviewed diagnostic code, minimal decision packets, and subtask
reports when no route is promoted. It does not mean the route is selected,
challenge-facing, validation-ready, or authorized for fold expansion,
validation packaging, upload, hosted metric claims, label/evaluator/fold split
changes, or next-stage training.

Operational controller completion is also separate from scientific route
resolution. A controller can complete subagent launch, executor results, auditor
reviews, and a controller report while the scientific route remains
`SCIENTIFIC_UNRESOLVED` or `SCIENTIFIC_UNDERTRAINED`. Do not let a controller
task collapse these into a single `status: complete`.

## Generating Tasks

When the user wants Codex to execute, fix, audit, validate, run commands, modify
files, or continue work, write:

```text
prompts/tasks/<task_key>.md
```

Before writing the task, decide:

- Is this a normal `execution` task or a `controller` task?
- Is this a `milestone` task that requires the two-step milestone review gate?
- Does it need separate executor and auditor sessions?
- Is review required?
- Can an execution controller escalate within policy, or must failure return to
  GPT planner?
- What evidence is required before route promotion?
- What evidence is required before a route-negative stop is scientifically
  supported?
- What minimum training budget, one-batch/tiny-overfit check, loss decrease,
  prediction sanity, proposal sanity, provenance, and same-split baseline are
  required for `experiment_adequacy_gate`?
- If route promotion fails, can a reviewed diagnostic packet still be published?
- Which diagnostic files may be published, and which actions remain blocked?
- What substitutes are forbidden?
- Should automatic commit/push proceed after audit passes through the route
  promotion gate or diagnostic publication gate?

Medium/high risk tasks and controller tasks must explicitly fill the new
frontmatter fields. Low-risk tasks may use defaults, `none`, or empty lists.

## Task Frontmatter

Existing fields remain valid:

```yaml
task_key: "002_fix_ci"
project: "project-name"
status: "READY"
executor: "Codex executor session"
risk_level: "low"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
```

New protocol fields:

```yaml
task_type: "execution"
controller_mode: false
execution_mode: direct_executor
requires_execution_controller: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
controller: "none"
executor_slots: 1
mapper_slots: 0
mapper_required: false
architecture_impact: none
wiki_update_required: false
diagram_update_required: false
slurm_runtime_continuity_required: false
continuity_backend: none
review_mode: independent_thread
reviewer: "separate_readonly"
review_required: false
mechanism_class: "general"
promotion_gate: "..."
route_promotion_gate: "..."
experiment_adequacy_gate: "..."
route_negative_gate: "..."
scientific_completion_gate: "..."
minimum_effective_training:
  min_optimizer_steps: 0
  min_train_loop_seconds: 0
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  allow_stop_without_training: false
diagnostic_publication_gate: "none"
diagnostic_publication_scope: []
blocked_after_diagnostic_publication: ["validation_upload", "validation_packaging", "fold_expansion", "hosted_metric_claim", "next_stage_training"]
failure_escalation_policy: "..."
forbidden_substitutes: []
required_evidence: []
allowed_next_states: []
auto_git_commit: true
auto_git_push: true
allow_git_commit: false
allow_git_push: false
```

For controller tasks, set `task_type: "controller"`, `controller_mode: true`,
`execution_mode: controller_supervised`, `controller: "Codex controller session"`,
and specify a controller report path. Existing task files that only have
`promotion_gate` or `auditor` are legacy
compatible: treat it as a route-promotion gate, and use safe defaults of no
diagnostic publication, no git commit, no git push, and `auditor` as
independent reviewer unless explicit fields say otherwise.

Existing model/training task files that lack `experiment_adequacy_gate` or
`minimum_effective_training` are legacy compatible but conservative: they cannot
support route-negative scientific stop unless result/review/controller evidence
explicitly reconstructs experiment adequacy and the auditor approves the
route-negative conclusion.

For milestone tasks, set `task_type: "milestone"`, `milestone_id`, exact
`expected_result_dir`, `required_outputs` including `completion_check.md`,
`review_request.md`, and `MANIFEST.md`, and the prerequisite review token for
non-initial milestones. The executor prompt must state that the same Codex
session cannot write `review.md`, cannot approve itself, and cannot start the
next milestone.

## Reviews And Audits

Review is an evidence audit, not a casual recap. The reviewer/auditor is
read-only and must not repair code, generate missing artifacts, or continue
execution. Use `REVIEW_TEMPLATE.md` and a claim ledger with:

- `SUPPORTED`
- `PARTIAL`
- `UNSUPPORTED`
- `CONTRADICTED`

Controlled audit decisions:

- `AUDITED_GO`
- `AUDITED_DIAGNOSTIC_PUBLISH`
- `AUDITED_SCIENTIFIC_STOP`
- `NEEDS_EVIDENCE`
- `NEEDS_REVISION`
- `SCIENTIFIC_UNDERTRAINED`
- `SCIENTIFIC_PIPELINE_BUG`
- `SCIENTIFIC_UNRESOLVED`
- `NEEDS_HUMAN_APPROVAL`
- `NEEDS_GPT_PLANNER`
- `STOP`

## Report To Next Task

Only the strategic controller, the user-supervised GPT thread, may write the
next high-level task after reading a review or controller report. Do not ask
Codex to continue indefinitely from its own result.

For milestone chains, the next milestone may be written or launched only after
the previous milestone's independent `review.md` contains the exact audited-go
token. `completion_check.md`, `review_request.md`, `result.md`, or
`controller_report.md` alone is not enough.

If the review is:

- `NEEDS_EVIDENCE`: next task should collect evidence before expansion.
- `NEEDS_REVISION`: next task should revise inside the audited scope.
- `NEEDS_HUMAN_APPROVAL`: wait for or record approval.
- `NEEDS_GPT_PLANNER`: GPT must decide the next direction.
- `STOP`: do not continue that route unless the user explicitly chooses a new
  direction.
- `SCIENTIFIC_UNDERTRAINED` or `SCIENTIFIC_UNRESOLVED`: do not treat the route
  as disproven; write a revision/evidence task or return to GPT planning with
  the unresolved scientific status.

Assume successful controller tasks synchronize remote state by default only when
the controller report says either route promotion or diagnostic publication
triggered an authorized push. For the next planning round, prefer checking the
remote repository state when `git_push_decision` reports a push, and otherwise
use the local controller report as the latest evidence.

## Notes And Wiki

Write `docs/notes/<date>_<topic>.md` for reference analysis, meetings, design
discussion, or research notes. Notes are not execution entries.

Write durable architecture/current-state knowledge to root `wiki/`. Historical
`docs/wiki/` pages are reference material, not the canonical architecture entry.
Wiki pages are not execution entries; tasks may reference them explicitly.

## GitHub / Remote Tooling

- Do not treat an issue, PR description, or chat text as the only Codex task
  source.
- Do not create issues, PRs, labels, workflows, or remote changes unless the user
  or task explicitly authorizes them.
- If execution is needed, write a task file first.
- If a controller task passes audit and `auto_git_push: true`, expect the remote
  to become the default source for subsequent planning only when the controller
  report records an authorized push through the route promotion gate or
  diagnostic publication gate.
