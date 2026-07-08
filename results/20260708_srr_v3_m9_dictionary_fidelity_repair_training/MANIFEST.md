# M9 Manifest

Task source: `prompts/shared/EXECUTOR_PROMPTS.md`

Result directory: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/`

Current state: `M9_NEEDS_MONITOR`

Current runtime state:

- MyoPS job `58297510` on `htzhulab`: running.
- MyoPS isolated job `58297807` on `htzhulab`: running.
- MyoPS isolated job `58297806` on `htzhulab`: running.
- Cine job `58297511` on `htzhulab`: completed with initial local-backbone-missing evidence.
- Local M9 Cine temporal output rerun: completed with `FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS`, 12 safe train cases, 12 non-reference frames, and ignored runtime predictions.
- A100 mirrors `58297196` and `58297197`: cancelled after htzhulab race decisions.

File count: 53 lightweight files.

Tracked files currently written:

- `result.md`: monitor-state summary and code repair evidence.
- `completion_check.md`: explicit non-ready completion state.
- `review_request.md`: states not to review as ready.
- `commands_run.md`: commands, Slurm submissions, and pending state.
- `m9_code_patch_summary.md`: first-pass code modifications.
- `m9_loss_weight_wiring_test_report.md`: CPU loss-weight wiring proof.
- `m9_nnunet_role_audit.md`: SRR-main/nnU-Net role code audit.
- `m9_validator_selftest_report.*`: one good fixture plus all 29 required known-bad mutations passed fail-closed self-test.
- `scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py`: post-job aggregator now supports runtime-derived tables beyond budget/selection, including same-split help/harm from runtime component metrics matched to the tracked M8 nnU-Net anchor metrics.
- `m9_route_promotion_decision.md`: `M9_NEEDS_MONITOR`.
- `m9_next_required_action.md`: `NEEDS_MONITOR`.
- All M9 prompt-required Markdown/CSV/JSON output names are present, but most MyoPS runtime-derived tables contain `PENDING_RUNTIME` or `EVIDENCE_NOT_FOUND` rows pending Slurm completion.
- `m9_training_curves.csv`, `m9_prototype_memory_summary.json`, `m9_prototype_update_ledger.csv`, and `m9_no_t2_edema_negative_violation_report.csv` now include partial one-batch/prototype evidence from the three running formal M9 variants. These are pre-formal-training sanity rows, not completion evidence.
- `m9_cine_final_output_manifest.csv`, `m9_cine_registration_quality.csv`, `m9_cine_temporal_dictionary_usage.csv`, `m9_cine_temporal_case_metrics.csv`, `m9_cine_frame0_vs_temporal_help_harm.csv`, `m9_cine_failure_matrix.csv`, and `m9_cine_temporal_output_summary.json` now contain local M9 Cine final-output proxy evidence from the bounded rerun. Runtime NIfTI predictions and ANTs transforms remain ignored and untracked.

Required M9 evidence not yet populated from runtime:

- Full MyoPS training curves, same-split help/harm, hard subgroup metrics, candidate assembly, ablation matrix, proposal/refiner recall/precision, refiner causal effect, prototype memory runtime ledgers, and Pattern-SIP tables.

Heavy runtime outputs, checkpoints, predictions, NIfTI files, upload zips, raw data, secrets, and full runtime trees are not committed.
