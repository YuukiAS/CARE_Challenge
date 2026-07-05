# MANIFEST: 20260704_srr_v25_dictionary_semantic_retrieval

task_source: `prompts/tasks/20260704_srr_v25_dictionary_semantic_retrieval.md`

## Artifacts

- `result.md` - executor result and gate decision.
- `slot_semantics_contract.md` - slot groups, task priors, and missing-modality mask contract.
- `dictionary_loss_design.md` - semantic/SIP-style loss design and current smoke evidence.
- `gate_usage_by_modality_and_task.csv` - structured formal-runner gate usage rows from bounded smoke.
- `slot_collapse_report.md` - one-step smoke collapse/caveat report.
- `dictionary_ablation_plan.md` - required formal ablation matrix.
- `unit_test_report.md` - unit/compile/runtime-smoke commands and results.
- `runtime_smoke/variants/srr_propref_shared_dual_dict/summary.json` - bounded formal runner summary.
- `runtime_smoke/variants/srr_propref_shared_dual_dict/training_log.csv` - includes `semantic_retrieval_loss`.
- `runtime_smoke/variants/srr_propref_shared_dual_dict/retrieval_usage.csv` - raw structured usage rows.

## Current State

state: `SEMANTIC_LOSS_AND_LOGGING_VERIFIED_NEEDS_FORMAL_DICTIONARY_ABLATION`

No validation package, external upload, git commit, git push, or prediction export was performed.
