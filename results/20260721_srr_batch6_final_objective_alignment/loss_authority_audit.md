# Loss Authority Audit

status: COMPLETE

runner_symbol: scripts.training.run_srr_propref_myops_fold0.propref_loss
loss_source: src/care_myocardium/losses/srr_losses.py
optimizer_steps: 0
parameter_updates: 0
parameter_hash_unchanged: True

## Findings

does_any_direct_final_pathology_loss_supervise_model_logits: True
does_production_correction_gate_receive_task_corrective_gradient: True
does_correction_opportunity_target_production_gate_or_legacy_arbitration: legacy_arbitration
do_active_magnitude_penalties_prefer_zero_correction: False
does_refiner_effect_loss_reward_or_penalize_nonzero_residual: penalize_nonzero_residual

Batch6 now adds direct deployed `outputs["logits"]` scar/edema GT repair losses and a production gate repair/preserve loss. Legacy correction-opportunity, branch arbitration, bounded-correction shrink, and refiner-effect shrink weights resolve to zero under the Batch6 canonical config.
