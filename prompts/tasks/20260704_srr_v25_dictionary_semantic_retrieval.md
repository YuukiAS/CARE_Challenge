---
task_key: "20260704_srr_v25_dictionary_semantic_retrieval"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "semantic multi-slot retrieval dictionary / SIP and slot supervision"
required_evidence: ["code_diff", "slot_semantics_contract", "gate_usage_by_modality_and_task", "slot_collapse_report", "dictionary_ablation", "unit_tests"]
forbidden_substitutes: ["multi-slot structure without semantic supervision", "only entropy/coverage regularization", "no dictionary ablation", "claiming dictionary works from gate CSV alone"]
---

# Task: Semantic Multi-Slot Retrieval Dictionary

## Goal

Make the dictionary a real scientific mechanism, not just a multi-expert router. Current code has multi-slot structure, but it has not proven that slots learn scar, edema, anatomy, modality-private, and interaction semantics. This task must add supervision/regularization and ablations that can show whether dictionary retrieval helps Dice and reduces remote false positives.

## Required Work

Implement or document:

- slot groups for shared, LGE-private, T2-private, C0-private, and interactions;
- task-specific routing priors for anatomy, scar, and edema;
- missing-modality invalid-slot masking;
- semantic slot diagnostics: per-task, per-class, per-center, per-modality-group gate usage;
- slot collapse detection and repair;
- dictionary regularizers stronger than generic entropy/coverage, including SIP-style coverage/integrativeness or an equivalent documented objective;
- ablations: no dictionary, shared-only dictionary, no interaction slots, no task bias, no anchor-conditioned routing.

## Required Metrics

Report changes in scar Dice/HD95/remote FP, edema GT-positive/T2-present Dice, CenterC edema, proposal precision/recall, and component count. Dictionary is not considered useful merely because gates are nonzero.

## Required Outputs

Write `results/20260704_srr_v25_dictionary_semantic_retrieval/` with `result.md`, `slot_semantics_contract.md`, `dictionary_loss_design.md`, `gate_usage_by_modality_and_task.csv`, `slot_collapse_report.md`, `dictionary_ablation_plan.md`, `unit_test_report.md`, and `MANIFEST.md`.

## Completion Gate

Pass requires evidence that dictionary behavior is semantically interpretable and experimentally testable. If the implementation only adds slots and gate logs, mark `NEEDS_REVISION`.
