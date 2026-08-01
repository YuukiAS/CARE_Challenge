# Manifest: 20260801 CARE Docker Provenance Reconcile and Bundle

Task: `prompts/tasks/20260801_care_test_docker_provenance_reconcile_and_bundle_controller.md`

Key evidence:

- `nnunet_labelwise_equivalence_casewise.csv` - W1 casewise semantic equality.
- `nnunet_label_transition_counts.csv` - W1 label transition counts.
- `nnunet_used_channel_equivalence_summary.json` - W1 summary.
- `historical_package_generation_trace.md` - W2 bounded trace.
- `historical_environment_fingerprint.json` - W2 environment/source fingerprint.
- `historical_asset_candidate_manifest.json` - W2 package/checkpoint candidates.
- `nnunet_replay_variant_manifest.json` - W3 variant summary.
- `nnunet_replay_variant_casewise.csv` - W3 casewise variant equality.
- `nnunet_replay_variant_decision.json` - W3 decision.
- `nnunet_deployable_repeat_casewise.csv` - W4 two-run deployment comparison.
- `nnunet_deployable_source_receipt.json` - W4 reproducibility receipt.
- `nnunet_lineage_vs_deployment_decision.json` - split lineage/deployment decision.
- `finalizer_state.json`, `controller_report.md`, `completion_check.md`, `strict_validator_report.json`, `notification_brief.json` - terminal packet.
