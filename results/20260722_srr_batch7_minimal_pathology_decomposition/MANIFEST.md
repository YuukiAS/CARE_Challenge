# Manifest

task: `prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_controller.md`

- `center_modality_inventory.csv`: metadata.center inventory and observation set.
- `pathology_source_eligibility.csv`: scar/edema source eligibility by representer.
- `resolved_stage_loss_weights.csv`: resolved loss authority table; legacy Pattern-SIP is zero.
- `sip_formula_unit_tests.json`: full-center-table SIP checks including batch-size-one rejection of batch proxy.
- `source_learner_coefficients.csv`: initial full center coefficient table.
- `representer_scale_checks.csv`: pre-beta RMS and initial zero-delta checks.
- `br2_staged_gradient_checks.json`: projection-zero staged BR2 gradient chain checks.
- `availability_mask_checks.csv`: hard modality availability masks by representer.
- `matched_run_manifest.csv`: static matching contract; runtime rows still pending Slurm execution.
- `result.md`: controller-maintained partial result; not a completion packet.
- `scripts/training/run_srr_batch7_minimal_decomposition.py`: thin orchestration driver for minimal/warmup/no-SIP/SIP branch execution.
- `jobs/srr_production/run_myops_batch7_minimal_decomposition_{htzhulab,a100}.sh`: Slurm entrypoints for pathology arms.
