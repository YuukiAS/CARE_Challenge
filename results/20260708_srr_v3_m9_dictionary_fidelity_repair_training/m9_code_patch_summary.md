# M9 Code Patch Summary

status: `RUNTIME_RECONCILED_FOR_M9_FOLLOWUP`

Modified/added code paths:

- `src/care_myocardium/losses/srr_losses.py`: expanded SRR loss now accepts M9 loss weight keys and aliases; scar small-ROI and edema large-ROI keys affect the total loss.
- `src/care_myocardium/models/srr_propref.py`: added formal M9 variants and SRR-main final-output mode where `final_logits` are SRR logits, not `nnunet_anchor_logits + bounded_delta`.
- `scripts/training/run_srr_propref_myops_fold0.py`: added M9 variants, CLI/config loss-weight collection, and explicit M9 checkpoint-selection proxy status requiring post-job aggregation.
- `src/care_myocardium/models/srr_dictionary_memory.py`: added safe EMA prototype memory with no-T2 edema-negative rejection.
- `src/care_myocardium/cine/temporal_output.py` and `scripts/training/run_cine_temporal_output_m9.py`: added fail-closed local Cine final-output inspection.
- `scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py`: added lightweight runtime summary aggregation.
- `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py`: added fail-closed M9 validator scaffold and self-test; M9 follow-up hardens this validator to scan required Markdown, CSV, and JSON evidence for unresolved stale runtime states.
- `jobs/src/run_srr_v3_m9_dictionary_fidelity_training*.sh` and `jobs/src/run_srr_v3_m9_cine_temporal_output*.sh`: added M9 Slurm entrypoints.

Runtime reconciliation evidence:

- `m9_training_budget_ledger.csv`: terminal post-job aggregation over `runtime_htzhulab_mirror`, `runtime_htzhulab_lesion_memory`, `runtime_htzhulab_t2_edema_focus`, and `runtime_htzhulab_true_br2_pattern_sip`.
- `m9_pattern_sip_usage_by_group.csv`, `m9_dictionary_invalid_slot_mask_report.csv`, and `m9_refiner_causal_effect.csv`: runtime-derived rows for dictionary usage, invalid-slot mask status, and final metric causal effect.
- `m9_metric_aligned_checkpoint_selection.csv`: metric-facing checkpoint selection remains negative vs the tracked M8 nnU-Net anchor.
