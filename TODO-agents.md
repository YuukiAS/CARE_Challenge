# TODO-agents: controller-supervised execution flow repair

Status: proposed protocol repair task list. This file does not change active runtime rules by itself. Use it as the next maintenance target for `AGENTS.md`, handoff files, GPT planner protocol files, and controller templates.

## Why this is needed

The current protocol already says that Slurm monitor packets are not completion and that `RUNNING`, `PENDING`, and `AWAITING_SACCT` must not be treated as ready. However, a long Slurm milestone can still waste overnight runtime if an executor exits early and labels normal waiting as `blocked`. Reviewer/auditor checks catch this after the fact, but they do not keep execution alive while the user is away.

The fix is not to add more natural-language reminders. The fix is to split runtime continuity from read-only review.

## Current state to preserve

- GPT/ChatGPT remains the planner and strategic controller.
- Codex executor performs authorized code changes, commands, result writing, and local commits, but must not self-review or start the next milestone.
- Reviewer/auditor remains a separate read-only role and must not fix code, generate missing artifacts, train, resume execution, or act as executor.
- Slurm monitor packets, pending jobs, running jobs, watcher packets, and submitted-only packets are not completion.
- After Slurm jobs complete, the relevant aggregator/evidence collector must run before review.
- `AGENTS.md` remains the repo-level Codex rule source.

## Target operating modes

### Mode A: short task / no long Slurm wait

Use the existing lightweight flow:

1. GPT planner writes the milestone / task / gates.
2. User starts one Codex executor goal or executor thread.
3. Executor completes the milestone, writes evidence, commits locally, and stops.
4. User starts a separate read-only reviewer/auditor thread or short reviewer goal.
5. Reviewer writes `review.md`, optionally commits it if authorized, and stops.

### Mode B: long Slurm / overnight / fragile resume task

Use controller-supervised execution:

1. GPT planner must mark the milestone as `execution_mode: controller_supervised`.
2. User starts one top-level Codex execution controller goal, not a standalone overnight executor goal.
3. The controller reads the task, `AGENTS.md`, handoff rules, Slurm skill, and current live git/Slurm state before launching or resuming execution.
4. The controller may use an executor worker/subagent for implementation, but the controller owns runtime continuity.
5. The controller must keep monitoring while required Slurm jobs are `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, or `AWAITING_SACCT`.
6. These normal monitor states must remain `NEEDS_MONITOR`; they must not become `blocked` unless the Slurm skill's 24-hour pending threshold is satisfied.
7. After jobs reach terminal states, the controller runs the required aggregator/evidence collector, validator/self-tests, `git diff --check`, and local commit of lightweight evidence.
8. The controller writes an execution/controller report and stops.
9. Reviewer/auditor is still launched separately afterward and remains read-only.

## Required changes to planning files

Update `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, and `prompts/GPT_HARD_GATE_PROMPT.md` so GPT must decide the execution mode before writing any milestone:

- `execution_mode: direct_executor` for short tasks.
- `execution_mode: controller_supervised` for long Slurm, overnight, multi-job, or high resume-risk tasks.
- `requires_execution_controller: true|false`.
- `review_mode: independent_readonly_thread` by default; `short_reviewer_goal` only when automatic review commit is desired.
- `context_bootstrap_required: true` for all controller-supervised milestones.

GPT planner must not write an overnight Slurm milestone that only provides a normal executor prompt. If the task may run while the user sleeps, GPT must author a controller prompt or controller section explicitly.

## Required changes to handoff roles

Update `prompts/HANDOFF_ROLES.md` to make four runtime roles explicit:

- `planner`: GPT/ChatGPT thread. Designs route, milestone, evidence gates, executor/controller prompt, and reviewer prompt. Does not run code or review final packets.
- `executor`: Codex worker for short direct execution or for controller-owned implementation phases. It can change code, run commands, write evidence, and commit. It cannot self-review, decide route promotion, start the next milestone, or own overnight continuity.
- `execution_controller`: Codex controller goal for long Slurm/overnight execution continuity. It monitors live Slurm/git/result-dir state, prevents erroneous early `blocked` exits, resumes the same milestone when needed, runs final aggregation/validation/commit after terminal jobs, writes controller report, and stops. It cannot write `review.md`, cannot make scientific route decisions, and cannot start the next milestone.
- `reviewer/auditor`: separate read-only review. It checks the final committed packet and writes review. It must not monitor or resume executor work.

Also update the existing wording that says the controller creates or launches executor and auditor sessions. For long Slurm flow, the controller may create/use executor workers, but it must not launch the reviewer/auditor until the final packet is committed and ready for read-only review.

## Required changes to controller template

Update `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`:

- Add `execution_mode` to frontmatter.
- Add `requires_execution_controller` to frontmatter.
- Add `context_bootstrap_required` to frontmatter.
- Add `slurm_runtime_continuity_required` to frontmatter.
- Add explicit `normal_monitor_states`: `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, `AWAITING_SACCT`.
- Add `scheduler_block_threshold`: `12 consecutive 2-hour pending-only checks with no job start`.
- Add a required `controller_bootstrap_snapshot_path`, e.g. `results/<task_key>/controller_bootstrap_snapshot.md`.
- Add a required `controller_supervision_ledger_path`, e.g. `results/<task_key>/controller_supervision_ledger.csv`.
- Add a required `finalizer_command` field when Slurm jobs are used.

## Required context handling policy

Do not rely on informal LLM context compression as the safety mechanism. It is lossy and can create the same problem under a shorter summary.

For controller-supervised milestones, require a deterministic bootstrap before every major phase:

1. Read from disk: `AGENTS.md`, `prompts/HANDOFF_ROLES.md`, `.agents/skills/slurm-routing-partition/SKILL.md`, the current GPT-authored milestone/task prompt, and the relevant result directory manifests if present.
2. Refresh live state: `git status --porcelain=v1 -b`, `git log --oneline --decorate -5`, `squeue`/`sacct` for required job IDs, required runtime-output existence, and required tracked evidence existence.
3. Write or update `controller_bootstrap_snapshot.md` with these facts.
4. Only then launch/resume executor work or run finalization.

For a new milestone, prefer a fresh controller goal/session over continuing an old compressed controller context. For a single long overnight milestone, the same controller may remain active, but it must repeatedly ground itself from the disk/live-state bootstrap snapshot rather than from memory.

## Required Slurm finalization behavior

Implement or require a milestone finalizer pattern:

- If any required job is `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, or `AWAITING_SACCT`, continue monitoring and keep state as `NEEDS_MONITOR`.
- If jobs are terminal and outputs exist, run aggregator/evidence collector, validator/self-tests, `git diff --check`, and commit lightweight evidence.
- If jobs are terminal but outputs are missing or aggregation fails, write `NEEDS_EVIDENCE` with live Slurm/log/runtime evidence and commit that evidence.
- If jobs fail, collect `sacct`, exit code, runtime, log path, and partial outputs, then write the appropriate evidence packet; do not call this scheduler block.
- Only call scheduler/resource blocked when the Slurm skill's pending-only threshold is met.

A future implementation may use either a foreground blocking finalizer command or a Slurm `afterany` dependency finalizer job. If using dependency finalizer jobs, add a lock to prevent concurrent manual resume and finalizer writes.

## Required validator / known-bad updates

Add known-bad cases that fail closed when:

- A required Slurm job is `RUNNING` but `result.md` or `completion_check.md` says `blocked` or `RESOURCE_BLOCKED`.
- A required Slurm job is `PENDING` but the 24-hour pending threshold is not proven and the packet says `blocked`.
- Final runtime outputs are missing because jobs are still running, but the packet claims blocked instead of `NEEDS_MONITOR`.
- A reviewer/auditor prompt authorizes resume, training, code changes, artifact generation, or executor recovery.
- A controller writes `review.md` or claims audited-go.
- A normal executor prompt is used for an overnight Slurm milestone without controller supervision.
- GPT writes a Slurm-backed milestone without `execution_mode` and `requires_execution_controller` fields.

## Minimal user-facing rule

Use this operational rule in future GPT planning outputs:

- Short task: `GPT planner -> executor goal/thread -> independent reviewer thread`.
- Long Slurm or overnight task: `GPT planner -> execution controller goal -> independent reviewer thread`.

Do not use `reviewer` as the thing that monitors executor blocking. Reviewer is read-only. The monitoring role is `execution_controller`.

## Files expected to be edited in the follow-up maintenance task

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`
- `.agents/skills/slurm-routing-partition/SKILL.md` if the finalizer/monitor-state wording needs to be centralized there
- Any shared executor/reviewer prompt templates that still imply reviewer-supervised execution or overnight direct executor mode

## Done criteria for the maintenance task

The follow-up protocol repair is done only when:

- GPT planning files require `execution_mode` selection before milestone writing.
- Controller-supervised mode is mandatory for long Slurm/overnight milestones.
- Reviewer/auditor remains strictly read-only and cannot monitor/resume executor work.
- Controller cannot write `review.md` or make audited-go decisions.
- Context bootstrap is disk/live-state based, not informal context compression.
- Validators reject `RUNNING/PENDING -> blocked` misclassification unless the Slurm skill threshold is proven.
- The updated files clearly state the user command pattern: short task uses executor; long Slurm uses controller; final review remains separate.

## Documentation audit and architecture diagram extension

Add a controller-owned documentation audit role. This is a read-only documentation subagent or controller phase, not a reviewer/auditor and not a scientific route judge.

Purpose:

- Keep a current, milestone-local description of what the model and execution system actually implement.
- Help GPT planner and the user understand the current codebase without relying on chat memory.
- Detect divergence between the GPT-authored design, code implementation, runtime evidence, and final packet.

Required long-milestone outputs:

- `results/<task_key>/architecture_snapshot.md`
- `results/<task_key>/implementation_map.csv`
- `results/<task_key>/model_dataflow.mmd`
- `results/<task_key>/execution_flow.mmd`
- `results/<task_key>/loss_and_metric_contract.csv`
- `results/<task_key>/placeholder_vs_real_implementation.md`
- `results/<task_key>/documentation_audit_report.md`

Optional rendered outputs when local tools are available:

- `results/<task_key>/model_dataflow.svg`
- `results/<task_key>/execution_flow.svg`
- `results/<task_key>/model_dataflow.d2`
- `results/<task_key>/model_dataflow_d2.svg`
- `results/<task_key>/method_illustration.svg`
- `results/<task_key>/method_illustration.pptx`
- `results/<task_key>/method_illustration.drawio`

Timing:

- Run documentation audit once after executor implementation / Slurm submission, while training is waiting or running.
- Run it again after terminal jobs, aggregation, and validator outputs exist.

Tool policy:

- Mermaid `.mmd` is the mandatory baseline diagram format because it is text, version-control friendly, and GitHub-renderable in Markdown.
- Mermaid CLI rendering is optional. If `mmdc` is available, render SVG. If not available, still commit `.mmd` and report `MERMAID_CLI_NOT_AVAILABLE`.
- D2 is recommended as the optional higher-quality architecture diagram layer if the `d2` CLI is installed. It should produce `.d2` plus SVG/PDF/PNG render when available, but it must not become a hard dependency.
- Graphify, if installed, may be used only as a code/docs knowledge-graph aid. It must not replace the architecture snapshot, Mermaid/D2 diagram sources, implementation map, or documentation audit report.
- AutoFigure-Edit, LiveFigure, SciFig, FigAgent, Paper2SysArch, and Crafter are research-grade or external figure-generation systems. They may be useful for paper-ready editable figure drafting, but they must be treated as optional, human-approved enhancement tools, not required milestone gates.
- Do not run Graphify or any documentation audit / figure-generation tool over raw data, NIfTI predictions, checkpoints, upload packages, secrets, or large runtime trees.

Architecture diagram content requirements:

- MyoPS model diagram must show modality inputs, availability mask, modality stems, shared/private/interaction dictionary or gated fusion, anatomy prior, scar proposal/refiner, edema proposal/refiner, no-T2 edema blocking, losses, final logits/labels, and export mapping.
- Cine diagram must show cine sequence input, ED/reference selection, keyframe selection, registration/warping slot, temporal representation dictionary or frame aggregator, anatomy prior, final myocardium output, and explicit placeholder/scaffold status when not fully implemented.
- Execution flow diagram must show GPT planner, direct executor mode, controller-supervised mode, executor worker/subagent, Slurm jobs, monitor/finalizer, documentation audit subagent, aggregator/validator, commit, and separate reviewer/auditor.

Documentation audit must classify each module as one of:

- `REAL_IMPLEMENTATION`
- `SCAFFOLD_ONLY`
- `PLACEHOLDER_OR_STUB`
- `LEGACY_CONTROL_ONLY`
- `UNUSED_DEAD_PATH`
- `UNKNOWN_NEEDS_EVIDENCE`

## External diagram / figure tool search results

These notes come from the tool search requested by the user. They are guidance for the follow-up maintenance task; they do not install or require any tool by themselves.

### Graphify

Use case: code/docs knowledge graph, dependency discovery, and documentation audit support.

Assessment:

- Good for making a queryable map of code, docs, papers, and other files.
- Strong fit for finding cross-file relationships during documentation audit.
- Not enough for CARE architecture diagrams because it produces exploratory graph artifacts rather than controlled model dataflow figures.
- Safe recommendation: optional project-scoped skill only, used on code/docs subsets.

Relevant source: `https://github.com/Graphify-Labs/graphify`.

### Mermaid / Mermaid CLI

Use case: mandatory baseline for controlled diagrams.

Assessment:

- Best baseline for Codex-generated architecture and execution-flow diagrams.
- Plain text `.mmd` is easy to diff, review, and commit.
- GitHub Markdown can render Mermaid diagrams; `mmdc` can render SVG/PNG/PDF if installed.
- Should be required even if no external drawing skill is installed.

Relevant source: `https://github.com/mermaid-js/mermaid-cli`.

### D2

Use case: optional higher-quality software/model architecture diagrams.

Assessment:

- Text-to-diagram language with a CLI and better layout options for software architecture.
- Useful for polished architecture diagrams after the Mermaid source is already correct.
- Should be optional because it may not be installed on the cluster / Codex runtime.

Relevant source: `https://github.com/terrastruct/d2`.

### AutoFigure-Edit

Use case: editable scientific illustration from method text.

Assessment:

- Strong candidate if the user wants paper-ready editable SVG figures later.
- It turns method text into editable SVG and includes an embedded SVG editor.
- Heavy external dependency path: image generation, SAM3 / segmentation, provider API keys, Docker or Python setup.
- Not suitable as a default milestone documentation gate.
- Candidate for a separate user-approved future figure-polishing task.

Relevant source: `https://github.com/ResearAI/AutoFigure-Edit`.

### LiveFigure

Use case: editable PowerPoint-style scientific diagrams with procedural generation.

Assessment:

- Interesting because it has a standardized drawing skill library, PPTX output, and visual refinement loop.
- Could be useful for final paper figures if the user wants editable PPTX.
- Too heavy for mandatory controller documentation: requires API keys, LibreOffice, model/VLM configuration, and project-specific setup.
- Candidate for separate user-approved exploration, not a dependency of agent-flow repair.

Relevant source: `https://github.com/tsinghua-fib-lab/LiveFigure`.

### SciFig

Use case: editable methodology figure generation from scientific text.

Assessment:

- Highly aligned with scientific method figures: it decomposes generation into planning, layout synthesis, component rendering, and iterative refinement, and targets editable XML figures.
- Useful as a conceptual reference for how to structure documentation audit: parse components, synthesize layout, render/refine, evaluate figure quality.
- Do not make it a required CARE tool until its code path is inspected and installed explicitly.

Relevant source: `https://arxiv.org/abs/2601.04390`.

### FigAgent

Use case: automatic method illustration figure generation for AI scientific papers.

Assessment:

- Very relevant conceptually: parser, planner, drawer, evaluator, refiner; DrawIO / XML-style editable output; reusable drawing toolbox.
- Good design reference for a future first-party `paper_figure` skill.
- Do not require it now because installation/runtime maturity and repo availability must be checked separately.

Relevant source: `https://arxiv.org/abs/2603.29590`.

### Paper2SysArch

Use case: scientific paper to structured system architecture diagram.

Assessment:

- Very relevant to our exact need: current model / method architecture diagrams, not generic pretty graphics.
- Useful conceptual pattern: represent diagrams as hierarchical graph JSON with nodes, edges, containment, and data/control flow.
- Recommendation: implement a lightweight first-party `architecture_graph.json` / `.mmd` workflow inspired by this idea, rather than depending on the external system.

Relevant source: `https://arxiv.org/abs/2511.18036`.

### Crafter / CraftEditor

Use case: multi-agent figure generation and raster-to-editable-SVG conversion.

Assessment:

- Useful if we already have a draft raster figure and want editable SVG conversion.
- More relevant to final paper polishing than to routine milestone documentation.
- Heavy dependency path, including external models / services in many modes.
- Optional future figure-polishing candidate, not required for controller documentation audit.

Relevant source: `https://github.com/HaozheZhao/Crafter`.

## Recommended diagram stack for CARE

Use this stack unless the user explicitly approves a heavier tool installation:

1. Required: first-party `architecture_graph.json` or `implementation_map.csv` extracted from code/docs by documentation audit.
2. Required: Mermaid `.mmd` for `model_dataflow` and `execution_flow`.
3. Optional: render Mermaid SVG via `mmdc` if installed.
4. Optional but recommended for polished architecture: D2 `.d2` + SVG if `d2` is installed.
5. Optional exploration: Graphify for code/docs relationship discovery only.
6. Separate future task only: AutoFigure-Edit / LiveFigure / SciFig / FigAgent / Paper2SysArch / Crafter for paper-ready edited figures.

Do not require an external figure-generation system to make long milestones pass. The pass condition is controlled, reviewable architecture documentation, not publication aesthetics.

## Tool assessment notes for GPT/Codex maintainers

Graphify assessment:

- Useful for building a project-level queryable knowledge graph from code/docs and for helping a documentation audit subagent find cross-file relationships.
- Not sufficient as the primary architecture drawing tool. It produces `graph.html`, `GRAPH_REPORT.md`, and `graph.json`; these are useful exploration artifacts but do not by themselves provide the controlled scientific model architecture diagram needed for CARE milestones.
- Recommended only as an optional helper if installed project-scoped under `.agents/skills/graphify/` and used on code/docs only.

Preferred diagram baseline:

- Use Mermaid `.mmd` as required output for milestone architecture and execution flow diagrams.
- Use Mermaid CLI `mmdc` to render SVG only when installed.
- Use D2 only as an optional higher-quality architecture diagram layer.
- If no external diagram tool is installed, the minimum pass is still valid `.mmd` plus a documentation audit report; do not let Codex skip diagrams by claiming no skill is installed.

## Follow-up Codex implementation prompt

Use this prompt for the unified Codex maintenance task that updates the active protocol files. This is a maintenance/protocol task, not a model-training milestone.

```text
You are the Codex maintenance executor for CARE agent-flow protocol repair. Your task is to implement the protocol changes specified in root `TODO-agents.md`, including the documentation audit / architecture diagram extension and the external diagram/figure tool policy. Do not train models, do not submit validation packages, do not upload, and do not start a scientific milestone.

Required reading before edits:

1. `AGENTS.md`
2. `TODO-agents.md`
3. `START_HERE_FOR_GPT.md`
4. `GPT_PLANNER_CARE_PROTOCOL.md`
5. `prompts/HANDOFF_ROLES.md`
6. `prompts/GPT_HARD_GATE_PROMPT.md`
7. `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`
8. `.agents/skills/slurm-routing-partition/SKILL.md`
9. Any shared executor/reviewer prompt files whose wording conflicts with the new flow.

Implement these changes without weakening existing rules:

1. Add explicit execution-mode selection to GPT planning: `direct_executor` for short tasks and `controller_supervised` for long Slurm / overnight / multi-job / high resume-risk tasks.
2. Require controller-supervised execution for overnight Slurm milestones. The user should start one top-level execution controller goal, not a standalone overnight executor goal.
3. Keep reviewer/auditor strictly read-only. Reviewer must never monitor, resume, train, fix code, generate missing artifacts, or act as execution controller.
4. Define execution controller as runtime-continuity supervisor only. It may monitor live Slurm/git/result-dir state, resume the same milestone, run final aggregation/validation/commit, and write controller/supervision reports. It must not write `review.md`, claim audited-go, choose a new scientific route, or start the next milestone.
5. Add deterministic context bootstrap requirements for controller-supervised milestones: before each major phase, read disk rules/task files and refresh live `git status`, `git log`, `squeue/sacct`, required runtime-output existence, and tracked evidence existence. Do not rely on compressed context as the safety mechanism.
6. Add Slurm finalizer behavior: `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, and `AWAITING_SACCT` stay `NEEDS_MONITOR`; terminal jobs trigger aggregator/validator/commit; terminal jobs with missing outputs become `NEEDS_EVIDENCE`; scheduler/resource blocked is allowed only with the Slurm skill's 24-hour pending-only threshold.
7. Add known-bad validator/reviewer expectations for `RUNNING/PENDING -> blocked`, reviewer prompt authorizing executor recovery, controller writing `review.md`, normal executor prompt used for overnight Slurm, and GPT Slurm milestone missing `execution_mode` / `requires_execution_controller`.
8. Add controller-owned documentation audit requirements for long milestones. This must be a read-only documentation subagent or controller phase, not reviewer work.
9. Require long-milestone documentation outputs: `architecture_snapshot.md`, `implementation_map.csv`, `model_dataflow.mmd`, `execution_flow.mmd`, `loss_and_metric_contract.csv`, `placeholder_vs_real_implementation.md`, and `documentation_audit_report.md`.
10. Require architecture diagrams to be Mermaid `.mmd` at minimum. If `mmdc` exists, render SVG; otherwise report `MERMAID_CLI_NOT_AVAILABLE` and still commit the `.mmd`. D2 is optional but recommended for polished architecture when installed. Graphify is optional and may only be used as a code/docs knowledge-graph aid, never as the primary architecture diagram or as a substitute for controlled documentation outputs.
11. Record the external diagram/figure tool policy in GPT-facing and controller-facing files: AutoFigure-Edit, LiveFigure, SciFig, FigAgent, Paper2SysArch, and Crafter may be discussed as optional future paper-figure tools, but they are not required milestone dependencies and must not be installed or invoked without explicit user approval.
12. If project-scoped Graphify is already installed, document how to use it safely on code/docs only. If it is not installed, do not install it unless the user explicitly asked. Do not run any graph/documentation/figure tool over raw data, NIfTI predictions, checkpoints, upload packages, secrets, or large runtime trees.
13. Ensure GPT-facing files clearly tell GPT to choose `execution_mode` while designing milestones, and to write controller prompts for long Slurm/overnight tasks.

Expected edited files include, but are not limited to:

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`
- `.agents/skills/slurm-routing-partition/SKILL.md` if needed for centralized Slurm finalizer wording
- Shared executor/reviewer prompt files only if they contain conflicting default flow language.

Add small helper templates if useful, for example under `prompts/templates/`:

- `DOCUMENTATION_AUDIT_TEMPLATE.md`
- `ARCHITECTURE_SNAPSHOT_TEMPLATE.md`
- `IMPLEMENTATION_MAP_SCHEMA.md`
- `ARCHITECTURE_GRAPH_SCHEMA.md`
- `MERMAID_MODEL_DATAFLOW_TEMPLATE.mmd`
- `MERMAID_EXECUTION_FLOW_TEMPLATE.mmd`
- `D2_MODEL_ARCHITECTURE_TEMPLATE.d2`

Validation requirements:

- Run `git diff --check`.
- Search the repository for wording that still implies reviewer-supervised execution or standalone overnight executor mode, and either fix it or document why it is legacy/non-authoritative.
- Search the repository for wording that lets Codex skip diagrams because no external drawing skill is installed; replace it with the Mermaid baseline rule.
- Verify the final protocol states the user-facing rule exactly: short task uses executor; long Slurm/overnight task uses execution controller; final review remains separate and read-only.
- Verify documentation-audit wording says Graphify is optional helper only, Mermaid is the required baseline, D2 is optional enhancement, and heavy scientific figure systems require explicit user approval.

Git policy:

- Commit only lightweight Markdown/template/protocol files.
- Do not push.
- Do not modify model code, results packets, checkpoints, data, logs, upload zips, or large artifacts.

Completion output:

- Update `TODO-agents.md` status or add a short completion note only if you also preserve the original task list.
- Write a concise maintenance summary in the commit message and final response.
```
