# Batch4 Manifest

Tracked lightweight packet files:

- `commands_run.md`
- `controller_context.json`
- `controller_dispatch_status.json`
- `controller_ledger.csv`
- `finalizer_state.json`
- `slurm_attempts.csv`
- `training_adequacy.json`
- `training_log_summary.csv`
- `validation_checkpoint_metrics.csv`
- `selected_checkpoint.json`
- `casewise_metrics.csv`
- `subgroup_metrics.csv`
- `help_harm.csv`
- `component_remote_fp.csv`
- `proposal_diagnostics.csv`
- `roi_diagnostics.csv`
- `correction_gate_diagnostics.csv`
- `frozen_prototype_memory_manifest.json`
- `selected_checkpoint_controls/batch3a_anchor_identity_control_inference_contract.json`
- `selected_checkpoint_controls/batch3a_anchor_identity_control_tensor_checks.csv`
- `selected_checkpoint_controls/batch3a_anchor_identity_control_geometry_roundtrip.csv`
- `selected_checkpoint_controls/batch3a_anchor_bounded_srr_correction_inference_contract.json`
- `selected_checkpoint_controls/batch3a_anchor_bounded_srr_correction_tensor_checks.csv`
- `selected_checkpoint_controls/batch3a_anchor_bounded_srr_correction_geometry_roundtrip.csv`
- `selected_checkpoint_controls/batch3a_srr_no_anchor_control_inference_contract.json`
- `selected_checkpoint_controls/batch3a_srr_no_anchor_control_tensor_checks.csv`
- `selected_checkpoint_controls/batch3a_srr_no_anchor_control_geometry_roundtrip.csv`
- `selected_checkpoint_evaluation/anchor_identity_44case.json`
- `selected_checkpoint_evaluation/batch2_completion.json`
- `selected_checkpoint_evaluation/nnunet_fold0_reproduction.json`
- `completion_check.md`
- `review_request.md`
- `review.md`
- `mapper_report_final.md`
- `architecture_delta_final.md`
- `controller_report.md`

Tracked code/config support:

- `scripts/evaluation/aggregate_srr_batch4_packet.py`
- `scripts/evaluation/validate_srr_batch4_packet.py`

Excluded by design: checkpoints, prototype `.pt` assets, prediction NIfTI files, full raw OOF anchor manifest bodies, runtime locks, full logs, upload packages, and secrets. The full raw OOF anchor manifest hash is retained in the three inference contracts and `selected_checkpoint.json`.
