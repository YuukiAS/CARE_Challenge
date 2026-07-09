# M9 Manifest

Task source: `prompts/shared/EXECUTOR_PROMPTS.md`

Result directory: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/`

Current state: `M9_FOLLOWUP_READY_FOR_REAUDIT`

Route decision: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`

## Runtime State

- MyoPS job `58297510` on `htzhulab`: completed with exit code `0:0`.
- MyoPS isolated job `58297807` on `htzhulab`: completed with exit code `0:0`, elapsed `02:03:52`.
- MyoPS isolated job `58297806` on `htzhulab`: completed with exit code `0:0`, elapsed `02:04:07`.
- MyoPS true-BR2 top-up job `58348646` on `htzhulab`: completed with exit code `0:0`, elapsed `02:03:33`, output root `runtime_htzhulab_true_br2_pattern_sip`.
- Cine job `58297511` on `htzhulab`: completed with exit code `0:0`.
- Local M9 Cine temporal output rerun: completed with `FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS`, 12 safe train cases, 12 non-reference frames, and ignored runtime predictions.
- A100 mirrors `58297196` and `58297197`: cancelled after `htzhulab` race decisions.

## Aggregation State

Final post-job aggregation was rerun after all MyoPS jobs completed:

```bash
python scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_mirror \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_lesion_memory \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_t2_edema_focus \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_true_br2_pattern_sip \
  --out-dir results/20260708_srr_v3_m9_dictionary_fidelity_repair_training
```

Aggregation exit status: `0`.

## Tracked Lightweight Files

The top-level M9 Markdown/CSV/JSON packet is intended for independent review. It includes:

- `result.md`: executor result.
- `completion_check.md`: explicit `M9_FOLLOWUP_READY_FOR_REAUDIT` completion check with `M9_NO_PROMOTION_DIAGNOSTIC_ONLY` route decision.
- `review_request.md`: read-only follow-up re-audit request.
- `commands_run.md`: commands, Slurm accounting, aggregation, and verification log.
- `m9_route_promotion_decision.md`: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`.
- `m9_next_required_action.md`: `GPT_REPLAN_AFTER_M9_NO_PROMOTION`.
- `m9_training_budget_ledger.csv`: six runtime rows, aggregate `26415.268` train-loop seconds, and three formal candidates with `>=7200` seconds.
- `m9_metric_aligned_checkpoint_selection.csv`: metric-facing selected checkpoint rows for three formal M9 candidates.
- `m9_training_curves.csv`, `m9_validation_events.csv`, `m9_loss_component_gradient_sanity.csv`: runtime training and loss evidence.
- `m9_same_split_help_harm.csv`, `m9_hard_subgroup_metrics.csv`, `m9_component_remote_fp_hd95_report.csv`: same-split metric evidence against the tracked M8 nnU-Net anchor.
- `m9_proposal_refiner_recall_precision.csv`, `m9_refiner_causal_effect.csv`, `m9_refiner_asymmetry_ablation.csv`, `m9_scar_refiner_roi_stats.csv`, `m9_edema_refiner_roi_stats.csv`: proposal/refiner evidence.
- `m9_pattern_sip_usage_by_group.csv`, `m9_dictionary_slot_group_stability.csv`, `m9_integrativeness_gamma_soft.csv`, `m9_dictionary_invalid_slot_mask_report.csv`: dictionary and Pattern-SIP summaries.
- `m9_prototype_memory_summary.json`, `m9_prototype_update_ledger.csv`, `m9_hard_negative_replay_ledger.csv`, `m9_no_t2_edema_negative_violation_report.csv`: prototype and no-T2 safety evidence.
- `m9_cine_*.md`, `m9_cine_*.csv`, `m9_cine_temporal_output_summary.json`: local Cine final-output proxy evidence.
- `m9_strict_validator_report.*` and `m9_validator_selftest_report.*`: validator reports.
- `m9_followup_reconciliation_report.md`: follow-up reconciliation status and summary.
- `m9_followup_stale_status_scan.csv`: Markdown/CSV/JSON stale-status scan summary.
- `m9_followup_validator_repair_summary.md`: validator bug and fail-closed repair summary.
- `m9_followup_reaudit_request.md`: independent re-audit request.
- `m9_followup_commands_run.md`: follow-up command log.

## Non-Tracked Runtime Artifacts

Heavy runtime outputs, checkpoints, predictions, NIfTI files, ANTs transforms, upload zips, raw data, secrets, full runtime trees, and large logs are not intended for commit.

## Follow-up Ready State

The packet has completed follow-up evidence reconciliation, post-job aggregation refresh, and validator checks. It is ready for independent read-only re-audit, but it does not support route promotion. Explicit safety boundary: no validation upload, no hosted metric claim, no fold expansion, no M10.
