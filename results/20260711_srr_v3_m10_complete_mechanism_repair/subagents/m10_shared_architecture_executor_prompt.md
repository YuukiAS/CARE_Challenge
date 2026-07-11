# M10 Wave 1 Executor Prompt

You are the serial wave 1 executor for CARE M10:

```text
task_key: 20260711_srr_v3_m10_complete_mechanism_repair
executor_id: m10_shared_architecture_executor
lane: shared
wave: 1
```

This is not a reviewer session. Do not write `review.md`, do not push, do not package or upload validation, do not claim hosted metrics, do not start M11, and do not run wave 2 or wave 3.

You are not alone in the codebase. Work only in the files and result paths assigned to this wave, do not revert other edits, and adapt to current main state.

## Required Reads

Read before editing:

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `.agents/skills/care-mapper/SKILL.md`
- `.agents/skills/slurm-routing-partition/SKILL.md`
- `prompts/shared/EXECUTOR_PROMPTS.md`, section `M10 executor/controller: SRR-v3 complete mechanism repair`
- `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml`
- `wiki/README.md`
- `wiki/MODEL.md`
- `wiki/COMPONENTS.csv`
- `wiki/architecture.yaml`
- `wiki/current_state.yaml`
- `wiki/history/README.md`
- `wiki/history/COMPARISON.md`
- `wiki/history/M09/components/*.md`
- `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md`

## Ownership

You own only wave 1 shared architecture, losses, tests, config, fidelity, and smoke evidence.

Allowed write scope:

```text
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/losses/srr_losses.py
src/care_myocardium/tests/test_srr_v3_m10_fidelity.py
configs/srr_v3_m10_complete_repair.yaml
results/20260711_srr_v3_m10_architecture_fidelity/
results/20260711_srr_v3_m10_mechanism_smoke/
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/
```

Forbidden write scope:

```text
AGENTS.md
prompts/shared/EXECUTOR_PROMPTS.md
prompts/shared/REVIEWER_PROMPTS.md
prompts/shared/M10_srr_v3_complete_mechanism_repair.md
prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md
results/20260711_srr_v3_m10_complete_mechanism_repair/review.md
wiki/README.md
wiki/MODEL.md
wiki/EXECUTION.md
wiki/COMPONENTS.csv
wiki/LINEAGE.md
wiki/architecture.yaml
wiki/current_state.yaml
wiki/history/
wiki/figures/
```

## Required Work

Execute only these wave 1 phases from the validated plan:

```text
source_audit_and_fixed_contract_mapping
D0_D3_shared_implementation
one_batch_overfit_gradient_and_known_bad_tests
architecture_fidelity_packet
```

Implement the fixed M10 shared architecture contract for D0-D3 as far as wave 1 owns it:

- canonical modality order `[LGE, T2, C0]`;
- exact 16-slot dictionary per scale;
- deterministic invalid-slot zero forward value, gate weight, gradient, and memory update;
- two-pass lesion-conditioned spatial retrieval;
- Pattern-SIP as independent implementation, not `dict_loss` alias;
- cross-fitted prototype memory and safe no-T2 negative policy;
- anatomy/proposal/soft-ROI/final-output formulas needed by shared architecture;
- loss component accounting with alias/placeholder prevention;
- one-batch overfit and known-bad tests scoped to wave 1.

Do not run formal M10 training rows, ordinary Slurm training jobs, validation packaging, upload, or wave 2/3 work.

## Required Outputs

Write:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/result.md
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/completion_check.md
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/commands_run.md
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/MANIFEST.md
```

Also write lightweight Markdown/CSV/JSON evidence under:

```text
results/20260711_srr_v3_m10_architecture_fidelity/
results/20260711_srr_v3_m10_mechanism_smoke/
```

The wave completion receipt must contain exactly one of:

```text
READY_FOR_CONTROLLER_MERGE
NEEDS_REVISION
NEEDS_EVIDENCE
NEEDS_MONITOR
```

Use `READY_FOR_CONTROLLER_MERGE` only if all wave 1 required implementation, tests, fidelity evidence, and smoke/known-bad checks pass and are written in lightweight tracked files. If anything is missing or only partially proven, use `NEEDS_REVISION` or `NEEDS_EVIDENCE`.

Do not commit. The main controller owns merge, staging, finalizer accounting, and local packet commits.
