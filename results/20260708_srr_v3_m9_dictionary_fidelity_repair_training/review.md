# M9 Reviewer Audit

decision: `M9_AUDITED_NEEDS_REVISION`

reviewer_role: read-only M9 reviewer

review_scope:
- `prompts/shared/REVIEWER_PROMPTS.md` M9 reviewer contract.
- `prompts/shared/EXECUTOR_PROMPTS.md` M9 executor contract.
- `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/` top-level tracked packet.
- M9 touched code paths under `src/care_myocardium/`, `scripts/training/`, `scripts/evaluation/`, and `jobs/src/`.

## Summary

M9 is not eligible for audited-go in the current form. The packet has substantial post-job runtime evidence and supports the executor's negative route decision directionally, but the reviewed packet is internally inconsistent: it marks `M9_READY_FOR_REVIEW` while required tracked evidence files still contain pending/runtime-needed statuses. The strict validator passes this packet because it does not scan required CSV/JSON evidence for these unresolved states.

This is not a scheduler monitor issue. The relevant Slurm jobs are terminal and the packet contains post-job aggregation output. The issue is evidence/validator consistency, so the controlled outcome is `M9_AUDITED_NEEDS_REVISION`.

## Blocking Findings

1. Required dictionary-fidelity evidence remains pending while the packet claims ready.

   `completion_check.md` marks the packet `M9_READY_FOR_REVIEW` and reports post-job aggregation exit `0`, but `m9_dictionary_fidelity_matrix.csv` still lists the formal runtime checks as `PENDING_RUNTIME` with issue `Slurm jobs pending` for true-BR2 runtime slot usage, invalid-slot mask runtime, and final metric causal effect. These are not optional checks in the M9 reviewer contract; they are central gates for dictionary fidelity and causal final-output effect.

   Evidence:
   - `completion_check.md:3`
   - `completion_check.md:21-34`
   - `m9_dictionary_fidelity_matrix.csv:4-6`

2. Multiple required narrative contracts still state runtime evidence is pending.

   The packet's own first-level Markdown files continue to describe the implementation as partial or pending:

   - `m9_code_patch_summary.md:3` says `PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE` and line 16 says the code repair is not sufficient for `M9_READY_FOR_REVIEW` until runtime evidence is complete and aggregated.
   - `m9_rrl_brr2_adaptation_contract.md:3` and line 13 say runtime Pattern-SIP, invalid-slot, and prototype-memory evidence remains pending.
   - `m9_nnunet_role_audit.md:3` and line 19 say controls still need post-job aggregation rows before M9 can be reviewed.
   - `m9_pathology_specific_refiner_contract.md:3-5` says runtime ROI stats, causal effect, and same-split metrics are pending Slurm completion.

   These statements conflict with `M9_READY_FOR_REVIEW` and with the final validator's `PASS_READY_PACKET` claim.

3. Prototype-memory evidence still carries an active running/partial status.

   `m9_prototype_memory_summary.json` reports `PARTIAL_ONE_BATCH_PROTOTYPE_EVIDENCE_FORMAL_TRAINING_RUNNING`. That is incompatible with a ready packet for the M9 prototype-memory gate, even though the same JSON contains useful safe-negative counts and no-T2 policy evidence.

   Evidence:
   - `m9_prototype_memory_summary.json:1-4`

4. The strict validator misses unresolved CSV/JSON states.

   The validator's ready-state monitor-token check scans only top-level Markdown (`all_md`) for `NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, and `AWAITING_SACCT`. It does not reject unresolved `PENDING_RUNTIME`, `PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE`, or `FORMAL_TRAINING_RUNNING` in required CSV/JSON evidence files. This explains how `m9_strict_validator_report.md` can claim `PASS_READY_PACKET` despite the contradictory tracked evidence above.

   Evidence:
   - `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py:25`
   - `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py:108-121`
   - `m9_strict_validator_report.md:3-5`

## Non-Blocking Confirmations

- I did not find evidence that the executor created a validation package, uploaded a validation submission, claimed hosted metrics, started M10, or started fold expansion. The packet repeatedly states the safety boundary and records `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`.
- The MyoPS training budget is not merely a few-minute smoke run. The tracked training ledger contains three isolated formal M9 rows with `>=7200` train-loop seconds and high optimizer-step counts, satisfying the M9 alternate budget shape if the packet is otherwise corrected.
- The selected metric-facing M9 candidates are all negative against the tracked M8 nnU-Net anchor. The no-promotion scientific direction is therefore supported, but it cannot be audited as a clean completed packet until the evidence-state contradictions are fixed.
- The Cine branch includes local temporal final-output predictions and lightweight metrics for 12 cases with label values `0;1;2;3`; it remains correctly caveated as local proxy evidence with no hosted metric claim.

## Required Repair Before Re-Review

The executor should regenerate or manually reconcile only the M9 packet evidence, then rerun the validator and self-tests:

1. Replace stale pending rows/statuses in required M9 evidence files with post-job runtime-derived statuses, or explicitly mark the packet non-ready if the evidence is genuinely incomplete.
2. Update `m9_dictionary_fidelity_matrix.csv` so true-BR2 runtime slot usage, invalid-slot mask runtime, and final metric causal effect are supported by the actual aggregated runtime tables.
3. Update the partial/pending narrative reports so they match the final aggregation state.
4. Strengthen `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py` so a ready packet fails closed on unresolved pending/runtime-needed tokens in required CSV/JSON/Markdown files, including at least `PENDING_RUNTIME`, `PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE`, and `FORMAL_TRAINING_RUNNING`.
5. Add a known-bad self-test fixture for stale `PENDING_RUNTIME` in `m9_dictionary_fidelity_matrix.csv` and stale running status in `m9_prototype_memory_summary.json`.

Do not proceed to validation packaging, upload, route promotion, fold expansion, or M10 from this packet.
