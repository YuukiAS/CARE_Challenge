# Batch7 Mechanism Closure Repair Manifest

本目录是 Batch7 repair 的终端证据包。它证明机制验证链路已经修好，但 proposal 训练未过继续门槛，所以后续阶段按合同停止。

Key tracked files:

- `controller_context.json`
- `superseded_evidence.md`
- `semantic_memory_manifest.json`
- `semantic_memory_category_counts.csv`
- `semantic_memory_tensor_hashes.csv`
- `semantic_memory_valid_masks.csv`
- `discovery_independence.csv`
- `prototype_map_intervention.csv`
- `semantic_memory_intervention.csv`
- `gradient_authority.csv`
- `checkpoint_roundtrip.json`
- `intervention_casewise_metrics.csv`
- `intervention_summary.csv`
- `intervention_prediction_manifest.csv`
- `proposal_refiner_metrics.csv`
- `source_arbiter_metrics.csv`
- `proposal_stage_adequacy.json`
- `training_stage_adequacy.json`
- `checkpoint_selection.csv`
- `help_harm.csv`
- `subgroup_metrics.csv`
- `slurm_attempts.csv`
- `validator_status.json`
- `finalizer_state.json`
- `mapper_report_draft.md`
- `mapper_report_final.md`
- `architecture_delta_final.md`
- `controller_report.md`
- `completion_check.md`

Runtime-heavy files intentionally not tracked:

- `runtime/**/*.pt`
- `runtime/**/*.nii.gz`
- `logs/srr_batch7_repair/*.log`
