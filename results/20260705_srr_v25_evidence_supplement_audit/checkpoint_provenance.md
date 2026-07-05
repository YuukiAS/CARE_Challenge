
# Checkpoint Provenance Audit

Audit basis commit: `3f30e0ee4b8c951f700fe50de8810bac8e196c23`.

All six full-fold0 variant rows under `results/20260704_srr_v25_training_ablation_matrix/full_fold0_eval/variants/*/bounded_source_summary.json` point back to bounded source checkpoints with `actual_optimizer_steps=6`, `device=cpu`, `encoder_profile=tiny_3scale`, `train_cases=12`, and `val_cases=4` except the no-prototype skip state. The full-fold0 pass expanded evaluation to 44 cases per row, but did not perform new adequate training; it loaded/evaluated the existing bounded checkpoints.

Therefore the full fold0 matrix is **eval-only existing bounded checkpoint evidence**, not formal adequate training evidence. It can support diagnostic help/harm and failure localization; it cannot support route promotion or a claim that SRR-v2.5 was fully trained.

Primary machine-readable table: `checkpoint_provenance.csv`.
