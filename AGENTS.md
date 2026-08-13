# CARE repository — agent instructions

## GPT / ChatGPT route bootstrap

New GPT/ChatGPT planning threads must read `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `prompts/FINAL_OUTPUT_READABILITY_POLICY.md`, `prompts/AGENT_FLOW_V2_PROTOCOL.md`, `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`, and `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md` before writing CARE milestones, Codex goals, handoffs, or route judgments. For any SRR/MyoPS/Cine route planning, they must execute `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`, visually read the SRR diagrams at `v2` and later from ChatGPT Project background files / project materials, and block without generating a milestone if those project-background diagrams cannot be accessed or interpreted. Repository paths such as `images/SRR-v2.png`, `images/SRR-v2.5.png`, and `images/SRR-v3.png` remain canonical filenames and version references, not the required GPT visual-reading entrypoint.

For future CARE milestones, GPT/ChatGPT must author executor/controller content before asking Codex to implement the milestone. Reviewer content is optional and required only when a task explicitly sets `review_required: true`. To avoid oversized direct edits to `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md`, GPT must place the new milestone prompt as a standalone Markdown staging file under `prompts/shared/` named `M<id>_<short_slug>.md`, for example `M<id>_mechanism_repair.md`. That staging file must clearly separate executor and reviewer sections. A later Codex maintenance step will split/merge those sections into the canonical shared prompt files and delete the standalone staging file after merge.

## Temporary /users Workspace Safety

Temporary rule for the `${CARE_REPO_ROOT}` development copy only: while working from this migrated copy, treat `${CARE_REPO_ROOT}` as the active CARE root. Do not write to `${CARE_LEGACY_OVERFLOW_WORKSPACE}` or other `/overflow` workspace paths from this copy. Reading `/overflow` is allowed only when needed for comparison, recovery, or historical reference; any `/overflow` write requires explicit human approval.

### Codex managed sandbox startup workaround

This workaround applies to the main CARE worktree and to all active route worktrees:

```text
${CARE_REPO_ROOT}
${CARE_ROUTE_WORKTREE_ROOT}/route_A
${CARE_ROUTE_WORKTREE_ROOT}/route_B
${CARE_ROUTE_WORKTREE_ROOT}/route_C
```

Some Codex desktop threads in this migrated `/users` copy may fail before starting any ordinary sandboxed process. The symptom is that even `pwd`, `true`, or `ls` in one of the valid CARE roots returns `Io(Os { code: 2, kind: NotFound, message: "No such file or directory" })`. Do not interpret this as a missing repository, broken SSH session, or invalid worktree.

If that happens, immediately retry the environment probe with `sandbox_permissions: "require_escalated"`, using the intended worktree as `workdir`, and record the reason as: sandboxed shell cannot start even read-only processes in the declared CARE worktree. Minimum probe:

```bash
pwd
ls
git rev-parse --show-toplevel
git branch --show-current
./envs/env_CARE/bin/python --version || python --version
rg --version
```

If the escalated probe succeeds, continue the thread using `require_escalated` for local shell commands that need process startup, including read-only inspection, tests, git index/commit operations, Slurm queries, `squeue`/`sacct`, tunnel/watchboard checks, and route-controller diagnostics. Keep all writes inside the active `/users` worktree or approved `/tmp`/runtime paths. Do not write to `/overflow` from this workaround.

If `apply_patch` cannot read or edit CARE files because of the same sandbox startup/mount issue, use a tightly scoped escalated workspace-local Python edit only for the exact target file(s), and state why before editing. Never use the workaround to bypass route isolation: a Route A/B/C controller must still write only its own worktree, result namespace, runtime namespace, logs, and locks.

For Codex sessions in this temporary `/users` copy, keep runtime state, cache, and temporary files under `/users`. The only shared file that may need preservation during auth migration is Codex login auth; active config, plugins, rules, skills, memories, SQLite state, logs, cache, and temp paths must not depend on `/nas` home-directory symlinks. Use:

```bash
cd ${CARE_REPO_ROOT}
source ${CARE_REPO_ROOT}/.care-codex-env.sh
source ${CARE_REPO_ROOT}/env_nnunet.sh
export PATH=${CARE_CODEX_RUNTIME_BIN_DIR}:${CARE_REPO_ROOT}/envs/env_CARE/bin:$PATH
```

For this temporary migrated workspace only, prefer the configured local Codex runtime at `${CARE_CODEX_RUNTIME_BIN_DIR}/codex`. Codex home standardization for `${CODEX_HOME_CONFIGURATION_ROOT}` must be explicit human-requested maintenance; otherwise do not modify original external wrappers from this copy. Repo writes, Codex state, logs, temp files, and CARE outputs should stay under `${CARE_REPO_ROOT}` or configured local runtime directories, not under shared home-directory symlinks.

The active Codex home model is defined by the shared standard in `${CODEX_HOME_CONFIGURATION_ROOT}`. The `/users` CARE runtime may read that standard, but persistent repo state belongs under `${CARE_CODEX_HOME_ROOT}`, while tmux/runtime isolation may use `${CARE_CODEX_RUNTIME_ROOT}/CARE__<session_slug>`. Treat `${CARE_LEGACY_CODEX_HOME}` as legacy migration state, not the active home for new sessions. If a future audit finds `/nas` symlinks under `.codex-home*`, `.codex-homes`, `.codex-runtime-homes`, or `.codex-global`, replace them with namespace-local files or links before starting new Codex sessions.

For this temporary `/users` copy, repo-local skills under `.agents/skills/` should be real directories, not symlinks back to `/overflow`. Do not refresh skills from `${CARE_SKILL_SOURCE_ROOT}` unless the user explicitly asks; if a refresh is needed, copy into `/users` and keep the `/overflow` source read-only.

## Codex rule source

Treat this `AGENTS.md` as the repo-level Codex rules source. Do not rely on `.cursor/rules/`, `.cursor/skills/`, `.cursor/plans/`, or Cursor plugins; migrate future rule changes here.

Current CARE rule priority:

- `AGENTS.md` is the repository entrypoint and local operating rule source.
- For new CARE handoffs, `prompts/AGENT_FLOW_V2_PROTOCOL.md` and `prompts/schemas/agent_flow_policy.yaml` define the active role model, schemas, and controller lifecycle.
- Bridge Kit sections in this file are compatibility guidance and reference indexes. They must not override the current Agent-Flow v2 active roles, main-only default, reviewer boundary, or readability gate.
- Route A/B/C rules remain binding when reading historical route evidence or when a new human-approved handoff explicitly reactivates a named route; otherwise future implementation defaults to `main`.

## Final output readability gate

For user-facing analysis, Batch retrospectives, planner recommendations, controller reports, controller conclusions, and any explicit reviewer conclusions, follow `prompts/FINAL_OUTPUT_READABILITY_POLICY.md`. The first paragraph must explain the practical scientific meaning in natural Chinese: what happened, why it matters, what should happen next, and what remains unauthorized or uncertain.

Paths, metrics, commands, schema fields, status tokens, route labels, experiment codes, English model names, and machine-readable decisions are locating evidence only. Put them after the plain-language judgment, not in the title or opening conclusion. Do not use repository experiment codes, status tokens, route labels, or mechanism names as the heading or conclusion unless their meaning has already been explained in plain language.

Do not stack unexplained English technical phrases. Controller analysis of status, cause, and repair direction must not begin with internal terms such as scar FN/FP, anchor, gate, final loss, or repair target; translate the mechanism into plain scientific language first, then provide the internal labels for lookup.

## Agent-Flow v2 controller handoff

### Current main-only posture

As of 2026-07-20, future GPT/Codex implementation defaults to `main` in `${CARE_REPO_ROOT}`. Route A/B/C worktrees and remote route branches are retained for provenance, but they are not active development targets. Do not start a new route controller, route worktree implementation, portfolio round, validation upload, route promotion, M11, hosted metric claim, or final scientific decision unless the user explicitly authorizes that scope in a new handoff. Historical route protocols remain binding when reading route evidence or if a route is later reactivated by a human-approved handoff.

Branch creation is not part of the default main-only workflow. Do not create, publish, or preserve a task branch unless the current user instruction explicitly authorizes that branch workflow. If a frozen task contract names an isolated branch/worktree, treat it as local isolation only unless the user also explicitly authorizes pushing that branch; after the user asks to merge into `main`, merge to `main`, push `main` only when authorized, and delete the temporary branch reference.

Remote publication is restricted to `main` by default. The only long-lived remote branches normally allowed on `origin` are `main`, `route_A`, `route_B`, and `route_C`; do not push `task/*`, `codex/*`, or any other branch name unless the user explicitly permits that exact branch in the current task. If an unauthorized extra remote branch is created, merge any authorized work into `main`, push `main`, and delete the extra remote branch.

For new CARE handoffs, `prompts/AGENT_FLOW_V2_PROTOCOL.md` and `prompts/schemas/agent_flow_policy.yaml` are the canonical sources. Use only these active role names: `planner`, `critic`, `controller`, `executor`, `mapper`, `finalizer`, `validator`, and `reviewer`. Historical `auditor`, `execution_controller`, and `strategic-controller` fields are legacy aliases only; do not create a controller-internal legacy `auditor` subagent in new tasks.

Short, non-Slurm, low-resume-risk work may use `planner -> executor -> local result commit -> planner`. Overnight, long Slurm, multi-job, or high-resume-risk work must use `planner -> controller/coordinator -> executor/mapper/finalizer/validator -> controller verification and repair loop -> local result commit -> planner`.

Every new CARE task or milestone must satisfy the appropriate schema under `prompts/schemas/`: direct executor and controller-supervised staging use `milestone_staging.schema.yaml`, executor waves use `executor_plan.schema.yaml`, result packets use `controller_packet.schema.yaml`, and runtime review uses `runtime_review.schema.yaml`. Defaults are one executor and one mapper for controller-supervised work; the controller must not increase subagent counts beyond the GPT-authored task graph.

The `controller` is the coordinator and acceptance owner. It owns task continuity, phase re-grounding, executor supervision, git-diff inspection, Slurm monitor state, same-scope repair loops, finalizer handoff, validator success, and the verified terminal local result commit inside one GPT-authored task. The `executor` performs authorized implementation and job submission but cannot declare the whole task complete. The `mapper` is read-only architecture/evidence mapping and uses `.agents/skills/care-mapper/SKILL.md`. The `finalizer` is deterministic terminal accounting, aggregation, validation, wiki finalization, and local packet commit; it is not an LLM subagent. The `reviewer` starts only when `review_required: true` is explicitly set and remains read-only.

Controller reports are generated as the terminal operational acceptance packet, but they must still start with a natural Chinese judgment for the Planner/user before any machine fields. The required machine decision is `controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED`. `VERIFIED_COMPLETE` requires required outputs, validators, terminal job accounting, aggregation, contract compliance, and local commit policy to be complete. Final scientific decisions, validation upload, hosted metric claims, fold expansion, route promotion, and next Batch authorization remain Planner/user decisions.

Executor parallelism gate: any `executor_count > 1`, `executor_slots > 1`, or `parallel_execution_allowed: true` task must provide `executor_plan_path` and pass `scripts/ops/validate_executor_plan.py`. MyoPS and Cine remain sequential unless GPT provides explicit isolation proof.

Root architecture/current-state knowledge lives at `wiki/README.md`; GPT, controller, mapper, and reviewer threads must consult it before architecture-affecting planning or review. If wiki fingerprint/evidence is stale, mark it stale and use current code/live evidence as source of truth.

For Route A/B/C work, planner, critic, controller, finalizer, validator, and reviewer threads must also read `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md` and `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`. Non-ready tokens such as `SCIENTIFIC_UNDERTRAINED`, `NEEDS_EVIDENCE`, and `NEEDS_MONITOR` must not be used to stop early when the route contract still requires Slurm execution, monitoring, post-completion aggregation, or packet consistency repair. The hard-requirements matrix is persistent across `round02`, `round03`, `round04`, and later route portfolio rounds; do not treat it as a one-off handoff note.

Route planners and critics must not leave design blanks for Codex/controller to fill during execution. Route contracts and critic handoffs must specify model structure, training/eval budget, input/output paths, Slurm strategy, validator semantics, known-bad fixtures, stop conditions, completion tokens, and reviewer pass/fail criteria. Vague delegation such as `TBD`, `optional`, `as appropriate`, `if needed`, `choose best`, `Codex decide`, or `controller decide` is a hard-gate failure unless the same section gives the trigger, default, allowed range, evidence requirement, failure branch, and reviewer judgment.

Route planners and critics must also preserve the M9/M10 inherited gates now recorded in `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`: truthful mechanism-closure evidence naming, fingerprint audit before inheriting old runtime, machine-readable contract/hash binding, faithful Cine/registration negative boundaries, durable finalizer, runtime no-push, and independent reviewer boundaries.

All Route A/B/C controller work must run as a Codex goal or explicit goal resume, not as a one-off interactive continuation. If a controller submits or inherits Slurm work, the goal must remain responsible through terminal accounting, same-scope operational retry when allowed, post-completion aggregation, local lightweight packet update, and verified terminal result. A controller must not exit at `NEEDS_MONITOR`, submitted-only, pending, running, or awaiting-accounting state unless a durable watcher/finalizer is already running and recorded in the packet.

### Controller completion email notification

Future main-controller goal prompts must include this completion boundary exactly in substance: Batch 完全结束、validator/aggregation/commit/push 状态确认后，先写 `results/<task>/notification_brief.json`，再由既有 `controller_notifications/notify_goal_watcher.py` / `care_notifier:Notifier` notifier 向 `${CARE_NOTIFY_TO}` 发送一封中文短邮件；不得为单个任务另开 notifier，不得手写 SMTP 或 `smtp.send_message(...)` 脚本，不得引用 watchboard 作为发送路径，不得在 submitted、pending、running、monitor 包、`NEEDS_MONITOR` 或未完成 aggregation 阶段通知。

Every achieved or blocked CARE controller goal must send this email. The fixed flow is:

```bash
# after terminal validator/aggregation/commit/push accounting is complete
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

or, for the long-running existing watcher only:

```bash
bash controller_notifications/start_in_tmux.sh
```

The persistent watcher runs in `care_notifier:Notifier`; its log and status are:

```text
controller_notifications/logs/notify_goal_watcher.log
controller_notifications/state/notify_goal_watcher_status.json
```

The required `notification_brief.json` fields are `task_name`, `final_status`, `commit_status`, `push_status`, `key_conclusion`, `blocked_or_failure_reason`, `slurm_terminal_status`, `evidence_paths`, and `next_step`. `final_status` must be exactly `complete` or `blocked` in future packets unless an existing notifier schema explicitly changes. The notification is an operational completion/blocked reminder, not a scientific report. It should summarize conclusion, terminal status, commit/push state, Slurm terminal accounting, key evidence paths, and next action. It must not include long goal prompts, large Markdown tables, token accounting, SMTP secrets, tunnel secrets, or hosted/performance claims not authorized by the controller packet.

Forbidden-to-notify states remain hard blockers: `PENDING`, `RUNNING`, `NEEDS_MONITOR`, `JOB_SUBMITTED`, `AWAITING_SACCT`, missing aggregation, missing validator, missing commit, or unconfirmed push state. These strings must not appear in `notification_brief.json`; the watcher is expected to refuse them. If the watcher finds no event after a valid terminal brief, the controller must fix the watcher/source configuration or start the existing `care_notifier:Notifier`; it must not fall back to a custom SMTP sender.

## MONITOR_PACKET_IS_NOT_COMPLETION

This rule applies to every CARE milestone and follow-up.

A Slurm submission, monitor job, watcher, pending queue state, or submitted-only packet is not a milestone completion packet. If an executor only submitted a job or wrote a monitor packet, it must not write milestone ready or request normal review.

If `completion_check.md`, `result.md`, `commands_run.md`, or a training adequacy table contains `NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or an equivalent pending/monitor state, the packet is not reviewable as complete. A completion validator or explicit reviewer must return `NEEDS_EVIDENCE` or `NEEDS_MONITOR`, not audited-go or `VERIFIED_COMPLETE`.

After a Slurm job completes, the executor must rerun the relevant aggregator or evidence collector and commit the tracked lightweight result files produced from runtime outputs before requesting review. `commands_run.md` entries showing only `sbatch submitted`, `squeue pending`, `PENDING Priority`, or pending `sacct` are not completion evidence.

Every job-derived completion packet must record job id, state, exit code, runtime, log path, runtime output path, aggregation command, aggregation exit code, and the tracked evidence files updated from runtime output. If the job completed but runtime output is missing or aggregation fails, completion must be `NEEDS_EVIDENCE`, not ready.

Controllers, validators, and any explicit reviewers must check that the tracked packet is the final post-completion aggregation, not the placeholder packet from job submission time. Validators and reviewer prompts must include known-bad cases for: ready completion while `followup*_training_adequacy.csv` contains `PENDING_MONITOR`; `commands_run.md` contains only submitted/pending job state; a Slurm job id exists without completed aggregation record; `result.md` says monitor packet; runtime output is not merged into tracked evidence.

## Plan document governance

CARE Myocardium plan files under `docs/plans/` must follow `docs/plans/care_myocardium_plan_registry_rules.md`. Plan filenames must encode lane, round scope, role/status, and topic, for example `laneA_round03_next_edema_trainable_smoke_execution.md` or `laneB_round03plus_controller_cinemyops_hosted_topology_motion_plan.md`.

If a user prompt, generated prompt, or prior ChatGPT instruction conflicts with the plan registry or current governed plans—for example by requesting an ambiguous filename, the wrong round, a controller edit for one-off execution, Round5 repo integration before gates pass, or Cine-only validation upload semantics—do **not** silently comply. Point out the specific contradiction and ask the user to decide before creating or renaming the plan. If the user explicitly overrides the rule, record the exception in the plan metadata. The former root `TODO.md` roadmap has been retired; use `docs/plans/` as the active plan source.

## Skill Source

- Repo-level skills are installed under `.agents/skills/` from `${CARE_SKILL_SOURCE_ROOT}/skills`.
- The canonical upstream source remains `${CARE_SKILL_SOURCE_ROOT}/skills`; when refreshing repo-local skills, replace duplicates with copies from that collection.
- This repository should install the medical imaging skill set from `AI_Skills_Collection/skills/domain/medical-imaging`.
- CARE Slurm partition/routing rules are also installed as a repo-local skill at `.agents/skills/slurm-routing-partition/SKILL.md`; use it before every Slurm job submission and before writing any GPT/Codex milestone, goal, or handoff that will submit Slurm jobs.
- CARE mapper and architecture-observability rules are installed as `.agents/skills/care-mapper/SKILL.md`; use it for any architecture, loss/dataflow/export, Cine temporal, or controller-observability change.
- Agent-flow v2 also installs repo-local real-directory copies of `codex-workflow-protocol`, `d2-diagrams`, `drawio-diagrams`, `plantuml-diagrams`, `markdown-mermaid-writing`, `scientific-visualization`, `chinese-prose`, `scientific-prose`, and the medical-imaging deep-learning skill. Do not replace these with symlinks to `/overflow`.
- Do not add `.cursor/skills` or Cursor plugin copies in this repository.

## Reference papers

Third-party papers for consultation live under **`literature/`** (PDFs, etc.). Use them when explaining methods, citations, or baseline details if copies exist there.

## Compute resources

The usual working environment is a compute node. The user also has access to the **`htzhulab`** partition; when CPU-only execution would be slow, use temporary GPU jobs there via `sbatch`, `srun`, or similar Slurm commands instead of letting long CPU runs crawl.

### Existing interactive allocation checks

When a CARE controller contract requires reusing an existing interactive allocation, the controller must check the lab partition directly before declaring the allocation missing. Do not rely only on a generic or truncated `squeue -u "$USER"` view.
All live interactive-job checks for a lab allocation must include an `htzhulab`-scoped query, even if a specific job id was supplied. A missing row in a generic/default queue view is not evidence that the interactive job is gone.

Minimum required checks:

```bash
squeue -u "$USER" -p htzhulab -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
squeue -j <candidate_job_id> -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
scontrol show job <candidate_job_id>
```

If the user provides an interactive job id, treat that id as authoritative enough to verify directly before making any resource conclusion. A controller must not write an `OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST` packet until the `htzhulab` partition-specific query and the specific job-id query both fail to show a usable RUNNING allocation, or `scontrol show job` proves it is no longer usable.

### Formal training interactive allocation sizing

For authorized CARE formal-training goals, do not fragment one continuous training objective into many short, loosely connected interactive or Slurm jobs unless the current user contract explicitly authorizes that fragmentation. Before requesting an interactive allocation, estimate the walltime needed to finish the authorized objective from measured or faithful-implementation throughput on the intended GPU class. Include training, checkpoint writing, required fair-comparison or inner-evaluation overhead, aggregation, and a reasonable recovery buffer.

Default behavior is to request an interactive or long allocation sized to complete the full authorized objective in one run, then use checkpoint/resume boundaries inside that allocation for recovery. If the first allocation is explicitly only for throughput calibration, immediately convert the measured throughput into the next long allocation for the remaining objective. Do not replace one long formal-training run with a chain of scattered short jobs merely because checkpoints exist.

If the authorized objective has multiple independent folds and resources permit, run those folds in parallel with isolated output, log, cache, and lock namespaces rather than serializing them into a longer wall-clock campaign. Fair-comparison and formal-inner evaluation jobs may be submitted as separate read-only jobs when authorized by the task; they must not cancel, mutate, fragment, or slow the active training allocation.

For CARE model work, default to the lab partition first. If queue inspection suggests a materially long wait on `htzhulab`, school GPU partitions may be used as fallbacks. The priority order is:

1. `htzhulab` — preferred/default for CARE jobs.
2. `a100-gpu` — school A100 partition; use only when `htzhulab` is expected to wait too long.
3. `volta-gpu` — school V100 partition; use after `a100-gpu`.

Current Slurm-visible school GPU partitions include:

- `a100-gpu`: `gpu:nvidia_a100-pcie-40gb`
- `volta-gpu`: `gpu:tesla_v100-sxm2-16gb`
- Other visible GPU partitions such as `l40-gpu`, `gpu` (GTX 1080), and `webportal_gpu` are not part of the default CARE fallback order; use them only if the user explicitly asks or the job requirements clearly fit them better.

Before switching away from `htzhulab`, check queue state with commands such as:

```bash
squeue -p htzhulab
sinfo -o '%P|%a|%l|%D|%t|%G'
```

Do **not** switch partitions for short waits or routine pending jobs. Switch only when `htzhulab` is full and the expected wait is long relative to the planned job budget. When switching to school partitions, keep the same logging style, but use the partition-specific Slurm headers below. Do not omit `--qos`: school GPU partitions may reject jobs that inherit an incompatible default QOS. The safe default QOS for CARE fallback jobs is `gpu_access`.

For long CARE model runs where all relevant GPU partitions appear saturated, do not declare the task blocked merely because jobs are pending. For goal tasks, pending-only monitor checks should be spaced 2 hours apart. Only after 12 consecutive 2-hour checks where every submitted routing partition is still pending and no submitted job has started may an executor report a scheduler block. This is a 24-hour pending evidence threshold, not a short interactive wait threshold.

When queue inspection or an existing pending attempt shows that a CARE long-run job is likely to wait a long time on a single compatible partition, controllers must use routing race rather than passively leaving only one queue entry. The default race is `htzhulab` plus `a100-gpu` whenever both are compatible and either may start first. If a controller has already submitted only one long-wait attempt and the other default race partition is compatible, it must submit the isolated mirror promptly instead of continuing single-queue monitoring. The raced jobs must use isolated output directories or an atomic per-run/per-variant lock so duplicate starts cannot write the same runtime artifacts. As soon as one partition starts running, cancel the other partition's still-pending mirror job. Record the job IDs, partition states, cancellation command, and watcher/log path in the result packet. Do not include `volta-gpu` in this race unless `htzhulab` and `a100-gpu` are unusable or the user explicitly approves it.

When adding Slurm entrypoints under `jobs/`, mirror the existing header/logging style. Default CARE/lab jobs should use `htzhulab`:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
```

For the school A100 fallback, use this directly usable header:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access
```

Notes for `a100-gpu`: `scontrol show partition a100-gpu` reports `AllowQos=gpu_access,gpu_access_plus`, `MaxTime=6-00:00:00`, nodes `g[141601-141608]`, and `gres/gpu:nvidia_a100-pcie-40gb`. Prefer `gpu_access`; use `gpu_access_plus` only when the user explicitly asks or there is a known reason to request that QOS.

For the school V100 fallback, use this directly usable header:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:tesla_v100-sxm2-16gb:1
#SBATCH --partition=volta-gpu
#SBATCH --qos=gpu_access
```

Notes for `volta-gpu`: `scontrol show partition volta-gpu` reports `AllowQos=gpu_access,hp_volta_gpu,gpu_access_plus`, `MaxTime=11-00:00:00`, nodes `g[0301-0316]`, and `gres/gpu:tesla_v100-sxm2-16gb`. Prefer `gpu_access`; use `gpu_access_plus` or `hp_volta_gpu` only when the user explicitly asks or there is a known reason to request that QOS.

Inside the script, create a timestamped log and tee stdout/stderr there:

```bash
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/<ShortJobName>_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
```

Use filenames like `logs/CineMyoPS_44291121_20260418_111101.log`. Avoid Slurm `%x_%j.out` files unless diagnosing scheduler startup failures.

## Model performance questions

When asked about **model performance** (metrics, Dice, fold CV results):

1. Verify whether **all folds** (usually 0–4) completed using logs and/or `validation/summary.json` (or each model’s metric outputs).
2. If incomplete: state missing folds and report partial results with a clear caveat.
3. If complete: report using the **same document structure and Markdown tables** as `results/metrics/nnUNet.md` (Setup table → label semantics → metric paths → per-dataset fold-wise Mean Val Dice → per-class Dice with Fold0–Fold4 + mean column → optional foreground_mean note → optional log references).

Mirror this layout for non–nnU-Net models; answer in **Simplified Chinese** with English for paths/names as needed.

### CARE-ASE outer diagnostic interpretation

For CARE-ASE faithful formal-training reports, the all-scar outer headline is not sufficient scientific interpretation by itself. Always split MyoPS scar results into at least:

- all outer scar;
- complete tri-modal scar, meaning T2-present availability `111` / `C0+LGE+T2`;
- partial-modality scar, meaning no-T2 `LGE-only` or `C0+LGE`;
- pure edema on T2-present cases.

Report case count, CARE Dice, matched nnU-Net Dice, delta, fold-level rows, and combined rows for each subgroup. If center metadata are available, also report CenterB complete scar/edema and CenterC complete scar/edema. Scar and edema must stay separate: scar subgroup decomposition can explain a mixed-scar headline, but it must not be used to dismiss a real pure-edema deficit because pure edema is already T2-present-only.

When a current checkpoint has only partial formal-training progress, such as fold2/fold3 before the frozen 14000-step target, do not recommend stopping CARE-ASE faithful training solely from mixed all-scar outer Dice. Unless there is precise evidence of a new model/loss/sampler/inference semantic regression, the correct controller posture is to continue the frozen schedule and fix diagnostic reporting. Mark partial-modality scar failure, fold-specific edema under-activation or calibration, catastrophic empty-prediction cases, HD95, sensitivity, precision, and volume-ratio availability as diagnostics without deleting cases from formal metrics.

For no-T2 comparisons, explicitly audit decode symmetry. CARE-ASE no-T2 decode excludes class 4 and uses class set `0,1,2,3,5`; if matched nnU-Net is evaluated by direct six-class argmax, label that as a diagnostic comparison asymmetry. A matched no-T2 class-set nnU-Net rerun may be reported only as diagnostic evidence and must not replace the original outer headline or drive checkpoint selection.

CARE-ASE outer subgroup tables must be recomputed from the raw casewise CSV plus immutable MyoPS case metadata, not copied from a headline summary. Keep a lightweight verification receipt when correcting these reports. If the original CSV lacks prediction/GT voxel-count fields, state that volume ratio is unavailable for that original table instead of inventing it; use a separate diagnostic rerun only when volume-ratio columns are explicitly present. Every such report must also include checkpoint provenance (`training_source_commit_sha`, `formal_execution_checkout_commit_sha`, source/config/split/plans/stock/contract hashes) and state whether there is precise evidence of a new faithfulness regression.

For reporting-only checkpoint provenance, do not use unsafe checkpoint pickle deserialization merely to read scalar metadata. Prefer existing text receipts, sidecars, or a static string/metadata scan that does not execute checkpoint payload code. If provenance can only be read through an unsafe loader, report that limitation and ask for explicit approval rather than silently dropping the provenance table or executing an unsafe fallback.

When comparing current faithful CARE-ASE, matched nnU-Net, and an earlier erroneous or deadline implementation, keep the fold/checkpoint/case-panel comparability boundary visible in the table. Historical weak/erroneous CARE-ASE numbers may be used to explain failure shape, but not as a same-case A/B result when folds differ. Old inner or same-exposure `0.9`-range tables remain diagnostic-only and must not be restored as the primary fair comparison.

## Iterative model-improvement runs

For CARE model-improvement work, use short, attributable experiment rounds instead of long speculative training runs.

- Default single training/evaluation job walltime is **8 hours or less**. If an existing Slurm script requests more time, create or use a budgeted entrypoint for the current round.
- Do **not** use very long runs such as 1000/2000 epochs to compensate for weak results. Prefer max-runtime guards, max-epoch caps, validation-based early stopping, and explicit best-checkpoint selection.
- Each round should test one main hypothesis: for example modality dropout, label/remap repair, scar-positive sampling, class-weight tuning, Stage1 prior alignment, or export/cache isolation. Avoid bundling several unrelated changes into one run unless a blocker forces it.
- Start with fold 0 or a small protocol validation loop. Expand to folds 1–4 only after predictions are non-empty, label semantics are verified, cache isolation is verified, and the target leaderboard metric improves or the change fixes a proven pipeline bug.
- Record each round in the relevant file under `results/experiments/*_iteration_log.md`: code changes, command/env vars, fold, walltime, actual epochs, checkpoint used/exported, stop reason, and target metrics before/after.
- Do not silently reuse stale prediction caches. Checkpoint-specific or config-specific prediction and metric directories are required when comparing variants.
- For MyoPS models, optimize and report `myops_scar` and `myops_edema`; for U-MyoPS edema analysis, also report all-cases, GT-positive-only, and T2-present subsets when possible. For CineMyoPS, report both the local `class_1` myocardium proxy and `class_3` scar sanity metric until the hosted `myocardium_cinemyops` metric is calibrated by submission.
- Continue small improvement rounds without asking the user after every run unless there is a decision about data compliance, label definitions, official submission strategy, external credentials, or materially longer compute.

## CARE2026 validation leaderboard

When asked for the latest CARE2026 validation/leaderboard/reference scores, first run:

```bash
python scripts/leaderboard/fetch_care2026_scores.py
```

Then answer from the generated latest files under **`results/leaderboard/`**, especially:

- `results/leaderboard/care2026_myocardium_latest.json`
- `results/leaderboard/care2026_myocardium_myops_scar_latest.csv`
- `results/leaderboard/care2026_myocardium_myops_edema_latest.csv`
- `results/leaderboard/care2026_myocardium_myocardium_cinemyops_latest.csv`

If the fetch fails because network access is unavailable or the website/API changed, state that clearly and fall back to the most recent existing `*_latest` files with a timestamp caveat.

For CARE2026 challenge interpretation and optimization, focus only on the three leaderboard tasks/metrics:

- `myops_scar`
- `myops_edema`
- `myocardium_cinemyops`

Do **not** treat myocardium, LV_blood, foreground_mean, or other mean/aggregate values as primary objectives. They may be reported as sanity checks when useful, but the main conclusions and repair plans should target the three leaderboard metrics above.

## CARE2026 validation submission packaging

Validation raw data should live under:

- `data/CARE_Challenge/MyoPS_val`
- `data/CARE_Challenge/CineMyoPS_val`

Use `scripts/submission/prepare_care_myocardium_validation.py` as the single entrypoint for validation submissions. One `CARE-Myocardium-OrganAgent.zip` upload contains both `MyoPS/` and `CineMyoPS/`, consumes one validation submission attempt, and returns the three hosted metrics (`myops_scar`, `myops_edema`, `myocardium_cinemyops`) together. Do not plan separate uploads for those three metrics; use per-metric interpretation after the single package is evaluated.

The script writes intermediate inputs/predictions under:

- `results/submissions/care_myocardium_validation/workspaces/<timestamp>__<model_combo_or_run_label>/`

and writes upload-ready packages under:

- `results/submissions/care_myocardium_validation/upload_ready/<timestamp>__<model_combo_or_run_label>/CARE-Myocardium-OrganAgent.zip`
- `results/submissions/care_myocardium_validation/upload_ready/<timestamp>__<model_combo_or_run_label>/manifest.json`

The upload zip filename intentionally has **no timestamp**, because the official example is `CARE-Myocardium-TeamName.zip`. Keep the timestamp at the **front** of the parent folder for chronological sorting and auditability.

Submission organization rule:

- Future upload-ready directory names must be timestamp-first: `<YYYYMMDD_HHMMSS>__<short_descriptive_run_label>`.
- Keep `upload_ready/README.md` updated when manually creating a package outside `scripts/submission/prepare_care_myocardium_validation.py`.
- Keep `upload_ready/` flat: do not add a duplicate chronological symlink layer such as `by_time/`.
- Rename legacy package directories in place to timestamp-first names when cleaning this folder, and then update affected manifests/notes.
- Mark the current best manual-submission candidate in `upload_ready/README.md`; avoid extra pointer directories or symlinks unless the user explicitly requests them.

To prepare the current default nnU-Net 5-fold validation upload zip, use:

```bash
sbatch jobs/submission/prepare_care_myocardium_validation.sh
```

For a local/debug run, use:

```bash
./envs/env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --team-name OrganAgent \
  --submission-model nnUNet \
  --folds 0 1 2 3 4 \
  --checkpoint checkpoint_best.pth
```

Convenience model selection:

- `--submission-model nnUNet`: use nnU-Net for both MyoPS and CineMyoPS.
- `--submission-model MyoPS-Net` or `--submission-model MyoPS`: use MyoPS-Net for the MyoPS side and nnU-Net for the CineMyoPS side.
- `--submission-model CineMyoPS`: use nnU-Net for the MyoPS side and CineMyoPS for the CineMyoPS side.
- `--submission-model U-MyoPS`: only valid when `--myops-pred-dir` points to compact-label U-MyoPS validation predictions; the current repo has protocol fold export for U-MyoPS but not a full validation Stage1→Stage2 inference pipeline.
- `--myops-model ... --cine-model ...`: explicit hybrid combination, for example `--myops-model MyoPS-Net --cine-model CineMyoPS`.

The script converts compact model labels back to CARE raw labels (`200`, `500`, `600`, `1220`, `2221` as applicable). If a prediction has no pathology label at all, it adds a one-voxel `2221` format fallback and records the case in the manifest, because the official validator rejects predictions missing scar/pathology labels.

The official Myocardium validation zip layout is documented at `https://zmic.org.cn/care_2026/valid_submission/`: top-level `MyoPS/Anonymous Center/Case****/Case****_pred.nii.gz` and `CineMyoPS/Anonymous Center/Case****/Case****_pred.nii.gz`.

Default inference policy for the current nnU-Net baseline is a 5-fold ensemble (`fold_0`-`fold_4`) using `checkpoint_best.pth`, because all five folds exist for both Dataset501 and Dataset502. Run it on `htzhulab` GPU by default; use a single best fold only for quick experiments or if ensemble inference is too slow.

<!-- AI_SKILLS_COLLECTION_START -->
# AI Skills Collection

Installed: `2026-07-10T05:12:39+00:00`
Target: `repo`
Install mode: `domain:medical-imaging`
Project skills: `.agents/skills/`
Central collection: `${CARE_SKILL_SOURCE_ROOT}`

When a task matches an installed skill, read that skill's `SKILL.md` before acting. Keep progressive disclosure: load `references/` only when the skill says they are relevant.

## Skill Routing

### medical-imaging
- `cardiac-mri`: Use for cardiac MRI / CMR domain knowledge, cine SAX/LAX, ED/ES timing, LV/RV function, myocardial strain, tagged MRI, feature tracking, and cardiac phenotype validation independent of any single project. Path: `.agents/skills/domains-medical-imaging-cardiac-mri/SKILL.md`
- `medical-imaging-classical-features`: Use when enforcing reproducible medical-imaging preprocessing, physical-space geometry, classical registration baselines, radiomics protocols, or DICOM SEG/SR provenance. Path: `.agents/skills/domains-medical-imaging-medical-imaging-classical-features/SKILL.md`
- `medical-imaging-deep-learning`: Use for medical-imaging deep learning tasks involving segmentation, MONAI/nnU-Net baselines, registration or warping, temporal/video imaging, missing-modality fusion, proposal/cascade/refinement models, external metho... Path: `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `medical-imaging-terminology-measurement`: Use medical imaging terminology and measurement conventions with source checks, modality-specific caveats, structured reporting boundaries, and uncertainty language. Path: `.agents/skills/domains-medical-imaging-medical-imaging-terminology-measurement/SKILL.md`
- `pathml`: Full-featured computational pathology toolkit. Use for advanced WSI analysis including multiplexed immunofluorescence (CODEX, Vectra), nucleus segmentation, tissue graph construction, and ML model training on patholog... Path: `.agents/skills/domains-medical-imaging-pathml/SKILL.md`
- `pydicom`: Python library for working with DICOM (Digital Imaging and Communications in Medicine) files. Applies to tasks involving medical image analysis, PACS systems, radiology workflows, and healthcare imaging applications. Path: `.agents/skills/domains-medical-imaging-pydicom/SKILL.md`

## Skill Maintenance

- Update command: `python3 ${CARE_SKILL_SOURCE_ROOT}/scripts/skills.py install --target repo --mode copy --domain medical-imaging --write-agents-md --prune-managed`
- Managed manifest: `.agents/skills/.ai-skills-collection-manifest.json`
- The installer only manages paths recorded in that manifest.
- User-created skills outside the manifest are never pruned.
<!-- AI_SKILLS_COLLECTION_END -->
The following Bridge Kit-managed section is retained as generic handoff protocol and compatibility reference. If it appears to conflict with the current CARE Agent-Flow v2 rules above, follow the current CARE rule priority section, active role list, main-only default, and final-output readability gate.

<!-- ai-bridge-kit:start -->
# Handoff Protocol

This repository uses the `prompts/` handoff protocol: a lightweight file bridge
between a GPT strategic planner and Codex execution sessions.

## Read First

- `prompts/AGENT_RULES.md`: Codex execution rules.
- `prompts/CHATGPT_RULES.md`: GPT planning/review rules.
- `prompts/HANDOFF_ROLES.md`: two-layer role model.
- `prompts/HANDOFF_STATE_MACHINE.md`: controlled states.
- `prompts/CONTROLLER_TASK_PROTOCOL.md`: controller task behavior.
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`: route promotion vs diagnostic
  publication behavior.
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`: experiment adequacy, route-negative,
  and scientific completion behavior.
- `prompts/tasks/<task_key>.md`: default task entry.

## File Mapping

```text
prompts/tasks/<task_key>.md
results/<task_key>/result.md
results/<task_key>/review.md
results/<task_key>/controller_report.md   # controller tasks
results/<task_key>/MANIFEST.md
```

`docs/notes/` and `docs/wiki/` are reference stores, not default execution
entries.

## Result Publication Boundary

Generated `results/20??????_*` handoff/controller run directories are
data-derived local evidence packages. They are ignored by default and must not be
published wholesale.

When GPT needs repository-visible context for deciding the next task, the
controller may publish only the smallest reviewed diagnostic packet after review
or re-review. Prefer the controller `controller_report.md` and
`execution_plan.md`, plus each relevant subtask's `result.md` and explicit `review.md` only when review was required.
Small reviewed Markdown decision packets such as `failure_interpretation.md`,
`architecture_gap_audit.md`, `label_export_qc.md`, `training_schedule.md`, or
`provenance_reconciliation.md` may be published when they are necessary for GPT
planner review. Small first-party source code/scripts required to reproduce the
diagnostic conclusion may be published only when reviewed and free of heavy
data/output.

Do not publish checkpoints, prediction outputs, NIfTI outputs, heavy logs,
secret-bearing command transcripts, environment dumps, large or
privacy-sensitive raw CSV dumps, full result trees, upload packages, hosted
validation packages, external credentials, or `.env`-style files.

Because most result directories are ignored, any approved non-milestone decision
packet should be added with explicit `git add -f <file>` paths. Do not change
`.gitignore` to unignore an entire generated result tree.

For `task_type: milestone` result directories whose task key matches
`results/20??????_*_m[0-9]_*/`, the top-level executor/reviewer handoff packet
is repository-visible by default: first-level `.md`, `.csv`, and `.json` files
may be tracked when they are exact task-required outputs and are small,
reviewable, and free of secrets or raw data. This exists so the next independent
reviewer can see `completion_check.md`, `review_request.md`, contracts, and
required evidence tables without relying on local ignored state. Nested
runtime artifacts, checkpoints, predictions, NIfTI files, logs, uploads,
transcripts, environment dumps, and heavy or sensitive tables remain forbidden
unless an explicit reviewed publication gate approves the exact files.

For routine handoff/result publication commits, Codex may stage the safe
first-level Markdown packet without a separate user reminder by running:

```bash
python scripts/git/stage_handoff_result_packet.py results/<task_key>
```

This helper force-adds only small first-level Markdown files from the specified
`results/<task_key>/` directory and skips transcript/secret/env-dump style names.
It must not be used as permission to publish checkpoints, predictions, NIfTI
outputs, heavy logs, CSV/JSON dumps, upload packages, nested artifact trees, or
unreviewed sensitive material.

Diagnostic artifact publication is not route promotion. It does not authorize a
challenge-facing route, validation packaging, validation upload, fold expansion,
hosted metric claims, label/evaluator/fold split changes, or next-stage
training.

Controller operational completion is not scientific route resolution. A
controller may finish executor/mapper/finalizer/validator workflow and locally
commit a lightweight final packet with `controller_verification_decision: VERIFIED_COMPLETE` while scientific next steps remain a Planner/user decision. Route-negative conclusions such as `STOP_NO_SIGNAL`,
`STOP_NO_PROPREF_SIGNAL`, `STOP_NO_CLEAN_ANCHOR_SIGNAL`, or
`STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL` require explicit Planner/user
authorization; an independent reviewer is required only when the task sets
`review_required: true`. Controller reports must not claim those final
scientific decisions.

## Codex Rules

- Execute only the GPT-authored task scope.
- Obey frontmatter permission fields and stop on unauthorized actions.
- If acting as executor, write `result.md` and stop at self-assessment; do not
  claim final controlled completion or open the next task.
- If acting as milestone executor/controller, execute exactly one milestone,
  write required outputs plus `controller_report.md`, `completion_check.md`, and
  `MANIFEST.md`, then stop after a verified terminal result or controlled repair/block decision. Do not write `review.md`, do not approve scientific next steps,
  and do not start the next milestone.
- If the task explicitly sets `review_required: true` and the current session is executor/controller, do not also review.
- If acting as reviewer, remain read-only; do not fix code, generate missing
  artifacts, or continue execution.
- If acting as milestone reviewer for an explicit `review_required: true` task,
  read only the completed result directory and write `review.md`; reviewer
  tokens gate continuation only for that explicit reviewer-gated task.
- If acting as controller, coordinate executor/mapper/finalizer/validator
  handoff only inside the GPT-authored controller task. Inspect git diff, commands, frozen contract fields, outputs, tests, Slurm terminal accounting, aggregation, and validators after each executor wave; return same-scope gaps to the executor until complete. Prepare a separate reviewer handoff only when `review_required: true`; do not use a controller-internal legacy `auditor` for final review.
- The execution controller must not invent new research/product directions. If a
  new direction is needed, write `NEEDS_GPT_PLANNER`.
- Controller reports must start with a natural Chinese judgment that explains
  what was completed or blocked, why, what should happen next, and what remains
  unauthorized. Then separate `controller_run_status`,
  `operational_completion_status`, `experiment_adequacy_decision`,
  `route_promotion_decision`, `route_negative_decision`, and
  `scientific_resolution_status`. For default sprint-flow tasks, the report must include `controller_verification_decision`, `operational_completion_status`, `experiment_adequacy_decision`, `contract_compliance_status`, `required_outputs_complete`, `validators_passed`, `all_jobs_terminal`, `aggregation_complete`, `git_commit_decision`, `git_push_decision`, and `next_required_action`.
- For controller tasks, `auto_git_commit: true` and `allow_git_commit: true`
  authorize only a local lightweight final-packet commit for the current task.
  `auto_git_push`, `allow_git_push`, and `allow_diagnostic_push` must remain
  false for new tasks. If commit is skipped, state the reason in
  `controller_report.md`. No role pushes; the user pushes manually.
<!-- ai-bridge-kit:end -->

### CARE GPT-Codex Overlay

This repo uses the Bridge Kit handoff protocol plus a CARE-specific overlay. Generic role/state/task/result/review/controller rules live in the Bridge Kit-managed files under `prompts/`, but new CARE handoffs still use Agent-Flow v2 active roles and schemas as the higher-priority current rule. Generic medical-imaging mechanism gates live in `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md` and its upstream AI_Skills_Collection source.

CARE-specific additions live in `prompts/CARE_OVERLAY_GATES.md` and the CARE task/review/controller templates under `prompts/templates/`. Keep this layer limited to CARE Challenge contracts: `myops_scar`, `myops_edema`, `myocardium_cinemyops`, raw-vs-compact labels, no-T2 edema semantics, CineMyoPS temporal evidence, one-zip validation packaging, CenterB/CenterC reporting, and historical stop/revise failure rules. Do not copy the full medical-imaging skill into CARE rules.

For high-risk CARE work, a Codex executor result cannot authorize fold expansion, validation packaging, upload, or next-stage training by itself. Use a separate read-only reviewer when `review_required: true`, or a controller report when the task is controller-supervised, and escalate new scientific directions to the user-supervised Planner/GPT thread.

## Git push standing authorization

For this repository, ordinary `git push` commands are permanently authorized and must not be sent to manual approval, Auto-review, Guardian, or another approval reviewer.

After completing requested work, validation, and a normal commit, the agent may push the current branch to the existing origin without asking for separate confirmation.

This standing authorization only covers the user-authorized target branch for the current task. It must not be interpreted as permission to create or push a new task branch when the repository is in main-only posture or when the user expected the work to land on `main`.

This authorization does not permit the agent to autonomously use force push, force-with-lease, delete remote branches or tags, rewrite published history, or change Git remotes. Those operations still require an explicit user instruction.

### Local git operation rule

In the Codex Desktop workspace sandbox, `.git` is protected as read-only. If `git status`, `git add`, `git commit`, `git fetch`, or `git push` needs to write Git index, lock, credential, or remote-tracking ref files, use the approved local git escalation path for the active `${CARE_REPO_ROOT}` worktree instead of changing the workflow.

Do not replace the normal local commit/push workflow with a temporary `/tmp` clone, GitHub connector contents-API commit, or other remote-only update path merely because sandboxed `.git` writes are blocked. Those alternatives are allowed only when the user explicitly requests that mechanism after being told it will not use the current worktree's local Git history.

## Controller notifier email standing authorization

For this repository, CARE controller notification email commands that directly invoke `./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once` or start the existing watcher with `bash controller_notifications/start_in_tmux.sh` are permanently authorized and must not be sent to manual approval, Auto-review, Guardian, or another approval reviewer.

This authorization is limited to the existing CARE notifier in `${CARE_REPO_ROOT}`. It does not permit creating separate SMTP scripts, calling `smtp.send_message(...)` from ad hoc Python, exposing SMTP secrets, sending non-CARE emails, broad shell/network allow rules, referencing watchboard as the send path, or notifying before terminal aggregation, validator, commit/push, and Slurm accounting requirements are satisfied.
