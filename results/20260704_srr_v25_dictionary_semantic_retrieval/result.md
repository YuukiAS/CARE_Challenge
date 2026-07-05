# Result 20260704 SRR-v2.5 Dictionary Semantic Retrieval

status: `EXECUTED_UNAUDITED`
self_assessed_status: `SEMANTIC_LOSS_AND_LOGGING_VERIFIED_NEEDS_FORMAL_DICTIONARY_ABLATION`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## Summary

Implemented a semantic retrieval objective for the formal SRR PropRef route and expanded gate usage logging from expert-index-only rows to task/modality/slot-group rows. This moves the dictionary beyond a bare multi-slot router, but it still does not complete the subtask because formal dictionary ablations and downstream Dice/HD95/remote-FP metrics are missing.

## Code Changes

- `src/care_myocardium/losses/srr_losses.py`: added `semantic_retrieval_regularization` with task-family alignment, coverage, and interaction integrativeness terms.
- `scripts/training/run_srr_propref_myops_fold0.py`: formal PropRef loss now adds semantic retrieval loss and logs `semantic_retrieval_loss`.
- `scripts/training/run_srr_myops_fold0.py`: `record_gate_usage` now writes `semantic_task`, `slot_group`, `slot_kind`, `slot_modality`, `slot_modalities`, and `valid_fraction`.
- `src/care_myocardium/tests/test_srr_dictionary_bank.py`: added tests for semantic regularizer behavior and formal model metadata/mask integration.

## Runtime Smoke Evidence

- output root: `results/20260704_srr_v25_dictionary_semantic_retrieval/runtime_smoke/variants/srr_propref_shared_dual_dict/`
- actual optimizer steps: `1`
- encoder profile: `tiny_3scale`
- parameter count: `367312`
- skip export: `True`
- training batch case: `Case1012`
- logged semantic retrieval loss: `0.0036159525625407696`
- one-batch overfit status: `PASS`

## Outputs

- `slot_semantics_contract.md`
- `dictionary_loss_design.md`
- `gate_usage_by_modality_and_task.csv`
- `slot_collapse_report.md`
- `dictionary_ablation_plan.md`
- `unit_test_report.md`
- `MANIFEST.md`

## Missing For PASS

- Formal ablations: no dictionary, shared-only, no interaction slots, no task bias, no anchor-conditioned routing, semantic objective off.
- Same-split metrics: scar Dice/HD95/remote FP, edema GT-positive/T2-present Dice, CenterC edema, proposal precision/recall, and component count.
- Fold0 retrieval/collapse report over more than one smoke step.
- Separate read-only audit.

## Gate Decision

decision: `SEMANTIC_LOSS_AND_LOGGING_VERIFIED_NEEDS_FORMAL_DICTIONARY_ABLATION`

No validation package, external upload, git commit, git push, or prediction export was performed.
