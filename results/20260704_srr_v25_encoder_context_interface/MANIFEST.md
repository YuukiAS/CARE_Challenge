# MANIFEST: 20260704_srr_v25_encoder_context_interface

task_source: `prompts/tasks/20260704_srr_v25_encoder_context_interface.md`

## Artifacts

- `result.md` - executor result and gate decision.
- `context_contract.md` - nnU-Net context entry points and strict tensor-shape gate.
- `shape_alignment_sanity.md` - shape, missingness, and context mismatch unit evidence.
- `encoder_capacity_report.md` - strong vs tiny capacity, parameter-count, and overfit evidence.
- `one_batch_overfit_comparison.csv` - compact tiny-vs-strong bounded overfit table.
- `metadata_alignment_audit.md` - bounded runner batch/context alignment audit.
- `unit_test_report.md` - verification commands and recorded results.
- `ablation_plan.md` - remaining formal overfit/evaluation comparisons.
- `overfit_ablation/tiny/variants/srr_propref_shared_dual_dict/summary.json` - tiny base4 overfit run summary.
- `overfit_ablation/strong/variants/srr_propref_shared_dual_dict/summary.json` - strong base4 overfit run summary.

## Current State

state: `BOUNDED_BASE4_OVERFIT_VERIFIED_NEEDS_FORMAL_ABLATION`

No validation package, external upload, git commit, git push, or prediction export was performed.
