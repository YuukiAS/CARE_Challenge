# M9 Manifest

Task source: `prompts/shared/EXECUTOR_PROMPTS.md`

Result directory: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/`

Current state: `M9_NEEDS_MONITOR`

Current runtime state:

- MyoPS job `58297510` on `htzhulab`: running.
- MyoPS isolated job `58297807` on `htzhulab`: running.
- MyoPS isolated job `58297806` on `htzhulab`: running.
- Cine job `58297511` on `htzhulab`: completed with local-backbone-missing evidence.
- A100 mirrors `58297196` and `58297197`: cancelled after htzhulab race decisions.

File count: 52 lightweight files.

Tracked files currently written:

- `result.md`: monitor-state summary and code repair evidence.
- `completion_check.md`: explicit non-ready completion state.
- `review_request.md`: states not to review as ready.
- `commands_run.md`: commands, Slurm submissions, and pending state.
- `m9_code_patch_summary.md`: first-pass code modifications.
- `m9_loss_weight_wiring_test_report.md`: CPU loss-weight wiring proof.
- `m9_nnunet_role_audit.md`: SRR-main/nnU-Net role code audit.
- `m9_route_promotion_decision.md`: `M9_NEEDS_MONITOR`.
- `m9_next_required_action.md`: `NEEDS_MONITOR`.
- All M9 prompt-required Markdown/CSV/JSON output names are present, but most runtime-derived tables contain `PENDING_RUNTIME` or `EVIDENCE_NOT_FOUND` rows pending Slurm completion.
- `m9_training_curves.csv`, `m9_prototype_memory_summary.json`, `m9_prototype_update_ledger.csv`, and `m9_no_t2_edema_negative_violation_report.csv` now include partial one-batch/prototype evidence from the three running formal M9 variants. These are pre-formal-training sanity rows, not completion evidence.

Required M9 evidence not yet populated from runtime:

- Full training curves, same-split help/harm, hard subgroup metrics, candidate assembly, ablation matrix, proposal/refiner recall/precision, refiner causal effect, prototype memory runtime ledgers, Pattern-SIP tables, and Cine final-output metrics.

Heavy runtime outputs, checkpoints, predictions, NIfTI files, upload zips, raw data, secrets, and full runtime trees are not committed.
