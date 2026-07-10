---
name: care-mapper
description: Use for CARE architecture mapping, component evidence tables, root wiki updates, D2 diagram generation, code/evidence fingerprint checks, and controller mapper draft/final passes. Must be used when a CARE task changes model architecture, loss wiring, dataflow, export behavior, Cine temporal paths, or handoff controller observability.
status: active
provenance: project-local
trusted: true
requires_network: false
writes_files: true
executes_code: true
profile_tags:
  - care
  - architecture
  - mapper
---
# CARE Mapper Skill

Use this skill for the `mapper` role defined by `TODO-agents-v2.md`. The mapper is a read-only architecture/evidence mapper inside a controller-supervised task. It is not a reviewer and does not make route-promotion decisions.

## Required Inputs

Before mapping, read `AGENTS.md`, `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `TODO-agents-v2.md`, the handoff role/state/controller protocol files, the current GPT-authored task or milestone prompt, current `wiki/` files, and the current result packet evidence named by the task. If the task uses Slurm, also read `.agents/skills/slurm-routing-partition/SKILL.md`.

For architecture-changing work, also read the AI Research Toolkit source files from the current checkout:

```text
${AI_RESEARCH_TOOLKIT_ROOT}/README.md
${AI_RESEARCH_TOOLKIT_ROOT}/RESOURCE_INDEX.md
${AI_RESEARCH_TOOLKIT_ROOT}/inventory/resources.yaml
```

Do not use stale Toolkit reports such as `docs/local_install_report.md`. Run the repo wrapper so Toolkit state is checked from a writable shadow instead of writing to `/overflow`:

```bash
AI_RESEARCH_TOOLKIT_ROOT=/overflow/htzhu/mingcheng_new/AI_Research_Toolkit \
  python scripts/architecture/run_toolkit_healthcheck.py --check
```

## Scope

Mapper may inspect first-party source, configs, scripts, result packets, lightweight CSV/JSON/Markdown evidence, and committed wiki files. It may update root `wiki/` files and D2/Graphviz/PlantUML diagram sources only when the task explicitly authorizes wiki updates.

Mapper must not train models, submit Slurm jobs, package validation, upload, claim hosted metrics, write `review.md`, write audited-go tokens, or infer architecture status from chat summaries. It must not scan raw data, NIfTI files, checkpoints, large logs, upload packages, secrets, credentials, `.env` files, or full runtime trees.

## Component Status

Use implementation states:

```text
implemented
partial
scaffold
legacy
disabled
unknown
```

Use evidence states:

```text
verified
unverified
stale
missing
```

File existence is not enough for `implemented`. Tensor/log output is not enough for `verified`. A component is `verified` only when a current evidence path proves it is wired into the relevant runtime path and, where applicable, affects final logits, labels, export, or route decision.

## Root Wiki Schema

The canonical project wiki lives at `wiki/`, not GitHub Wiki and not `docs/wiki/`.

Required files:

```text
wiki/README.md
wiki/MODEL.md
wiki/EXECUTION.md
wiki/COMPONENTS.csv
wiki/LINEAGE.md
wiki/architecture.yaml
wiki/figures/model-current.d2
wiki/figures/model-current.svg
wiki/figures/model-current.png
wiki/figures/model-gap.d2
wiki/figures/model-gap.svg
wiki/figures/model-gap.png
wiki/figures/execution-flow.d2
wiki/figures/execution-flow.svg
wiki/figures/execution-flow.png
```

`COMPONENTS.csv` must include:

```text
component_id,branch,role,current_status,evidence_status,target_status,source_file,symbol,entrypoint,grep_key,config_keys,inputs,outputs,losses,final_output_effect,runtime_evidence,code_fingerprint_member,last_verified_milestone,review_token,notes
```

`architecture.yaml` is the machine source for diagram generation. Avoid self-referential final commit hashes inside wiki files; record stable `code_fingerprint` from declared source/config paths and record published commit lineage in `LINEAGE.md`.

## Diagram Rules

Preferred renderer order:

```text
architecture.yaml + COMPONENTS.csv -> D2 source -> SVG + PNG -> Graphviz fallback
```

D2 is the default source format. Graphviz is fallback. PlantUML is for sequence/state diagrams. Mermaid is allowed inside Markdown, but Chromium/Mermaid CLI failure must not block D2/PNG/SVG generation.

Every canonical figure must include visible status encoding:

- `implemented`: solid line
- `partial` or `scaffold`: dashed line
- `legacy` or `disabled`: gray styling
- `unknown`: explicit unknown state, not silent omission

## Mapper Reports

Draft mapper reports are allowed while jobs are pending/running, but unproven runtime paths must stay `unverified` or `missing`.

Final mapper reports must include source files and symbols inspected, config/CLI/loss/export entrypoints checked, runtime evidence paths used, component status deltas, code fingerprint inputs, stale wiki or stale evidence findings, and any component with missing `final_output_effect` evidence.

If source code changes after a mapper draft, rerun mapper final. Do not reuse stale mapper reports.

## Scripts

Use these first-party helpers:

```bash
python scripts/architecture/validate_care_architecture_wiki.py --strict
python scripts/architecture/generate_care_architecture_wiki.py --check
python scripts/architecture/run_toolkit_healthcheck.py --check
```

To regenerate figures after editing D2 sources:

```bash
python scripts/architecture/generate_care_architecture_wiki.py
```

The generator must produce `.d2 + .svg + .png` for each canonical figure. If D2 PNG export fails because Playwright is unavailable, SVG generation plus ImageMagick `convert` fallback is acceptable and must be reported.

## Controller Output Paths

Mapper-enabled controller tasks must produce or validate:

```text
results/<task_key>/controller_context.json
results/<task_key>/controller_ledger.csv
results/<task_key>/controller_bootstrap_snapshot.md
results/<task_key>/implementation_snapshot.md
results/<task_key>/mapper_report_draft.md
results/<task_key>/architecture_delta_draft.md
results/<task_key>/mapper_report_final.md
results/<task_key>/architecture_delta_final.md
results/<task_key>/finalizer_state.json
```

`controller_context.json` must include phase, git head/status, task prompt path and sha256, `AGENTS.md` sha256, Slurm skill sha256 when relevant, wiki code fingerprint, required job IDs, required runtime paths, and files read. `controller_ledger.csv` is append-only and must include timestamp, phase, git head, task hash, job states, decision, and next action.
