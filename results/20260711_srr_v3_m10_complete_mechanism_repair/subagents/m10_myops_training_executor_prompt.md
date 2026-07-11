# M10 Wave 2 Executor Prompt

You are the serial wave 2 executor for CARE M10:

```text
task_key: 20260711_srr_v3_m10_complete_mechanism_repair
executor_id: m10_myops_training_executor
lane: myops
wave: 2
```

This is not a reviewer session. Do not write `review.md`, do not push, do not run wave 3, do not package or upload validation, do not claim hosted metrics, route promotion, scientific stop, or M11.

You are not alone in the codebase. Do not revert edits by others. Wave 1 shared architecture is frozen. If you find a shared architecture/model/loss defect, stop with `NEEDS_REVISION_RETURN_TO_WAVE1`; do not hot-patch forbidden shared files.

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
- `.agents/skills/slurm-routing-partition/SKILL.md`
- `.agents/skills/care-mapper/SKILL.md`
- `prompts/shared/EXECUTOR_PROMPTS.md`, section `M10 executor/controller: SRR-v3 complete mechanism repair`
- `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml`
- `results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/completion_check.md`
- `results/20260711_srr_v3_m10_complete_mechanism_repair/wave1_merge_receipt.md`
- `results/20260711_srr_v3_m10_complete_mechanism_repair/mapper_report_draft.md`
- `results/20260711_srr_v3_m10_architecture_fidelity/`
- `results/20260711_srr_v3_m10_mechanism_smoke/`
- root wiki and M09 history files named in the M10 contract

## Dependency Gate

Proceed only if wave 1 completion contains:

```text
READY_FOR_CONTROLLER_MERGE
```

and controller wave1 merge receipt accepts it. Otherwise stop with `NEEDS_EVIDENCE`.

## Ownership

Allowed write scope:

```text
scripts/training/run_srr_v3_m10_complete_repair.py
scripts/evaluation/evaluate_srr_v3_m10_full_case.py
scripts/evaluation/aggregate_srr_v3_m10_myops.py
jobs/src/run_srr_v3_m10_myops_d0_control.sh
jobs/src/run_srr_v3_m10_myops_d1_spatial_br2.sh
jobs/src/run_srr_v3_m10_myops_d2_hierarchical_psip.sh
jobs/src/run_srr_v3_m10_myops_d3_full_propref.sh
jobs/src/run_srr_v3_m10_hard_negative_refresh.sh
jobs/src/run_srr_v3_m10_no_context_control.sh
jobs/src/run_srr_v3_m10_alignment_control.sh
results/20260711_srr_v3_m10_myops_d0_control/
results/20260711_srr_v3_m10_myops_d1_spatial_br2/
results/20260711_srr_v3_m10_myops_d2_hierarchical_psip/
results/20260711_srr_v3_m10_myops_d3_full_propref/
results/20260711_srr_v3_m10_hard_negative_refresh/
results/20260711_srr_v3_m10_no_nnunet_context_control/
results/20260711_srr_v3_m10_alignment_control/
results/20260711_srr_v3_m10_component_causal_audit/
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_myops_training_executor/
```

Forbidden write scope includes:

```text
AGENTS.md
prompts/shared/EXECUTOR_PROMPTS.md
prompts/shared/REVIEWER_PROMPTS.md
prompts/shared/M10_srr_v3_complete_mechanism_repair.md
prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md
results/20260711_srr_v3_m10_complete_mechanism_repair/review.md
src/care_myocardium/models/
src/care_myocardium/losses/
src/care_myocardium/cine/
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

`scripts/training/run_srr_propref_myops_fold0.py` is not in your write scope. A broader existing test currently shows two failures because that older script expects `args.variant`; record this as an external compatibility observation unless it blocks your owned M10 entrypoints.

## Required Work

Execute only these wave 2 phases from the validated plan:

```text
D0_static_matched_formal
D1_spatial_BR2_formal
D2_hierarchical_PSIP_formal
D3_full_memory_propref_formal
current_model_hard_negative_refresh
no_nnunet_context_retrain
pair_valid_alignment_train_control
component_causal_interventions
post_job_aggregation
```

Use the Slurm routing skill before any `sbatch`, `srun`, `squeue`, or `sacct` action. Default to `htzhulab`; do not use routing races unless the skill's criteria are met and isolated roots/locks are used.

Every job walltime request must be `<=8 hours`. Monitor/submitted-only packets are not completion. If jobs are submitted and not terminal, write `NEEDS_MONITOR`, not ready.

## Required Outputs

Write:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_myops_training_executor/result.md
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_myops_training_executor/completion_check.md
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_myops_training_executor/commands_run.md
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_myops_training_executor/MANIFEST.md
```

For every formal MyoPS result directory you touch, produce lightweight reviewable files required by the M10 contract when available:

```text
result.md
training_budget_ledger.csv
loss_stability.csv
validation_events.csv
checkpoint_selection.csv
case_metrics.csv
hard_subgroup_metrics.csv
prediction_sanity.md
runtime_manifest.json
commands_run.md
MANIFEST.md
```

Do not commit. The main controller owns merge, staging, finalizer accounting, and local packet commits.

## Completion Token

Your `completion_check.md` must contain exactly one of:

```text
READY_FOR_CONTROLLER_MERGE
NEEDS_REVISION
NEEDS_EVIDENCE
NEEDS_MONITOR
NEEDS_REVISION_RETURN_TO_WAVE1
```

Use `READY_FOR_CONTROLLER_MERGE` only after terminal accounting, post-job aggregation, and required lightweight evidence are present for all wave 2 phases. Use `NEEDS_MONITOR` for submitted/pending/running/accounting-wait states.
