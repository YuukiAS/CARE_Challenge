# Ablation Matrix Contract

task: `prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md`
source_m3_checkpoint: `/users/a/e/aereinh/CARE/results/20260705_srr_v3_m3_myops_min_effective_pilot_training/variants/srr_v3_m3_shared_dual_dict_pilot/checkpoints/fold_0/propref_config/checkpoint_best.pt`
source_m3_optimizer_steps: `6000`
source_m3_train_loop_seconds: `2126.2185006489744`
eval_case_ids: `Case1029;Case1045;Case2002;Case2008;Case2031;Case3004;Case3012;Case3023;Case3038;Case5005;Case7005;Case8011`

This M4 packet runs bounded inference ablations on the audited M3 checkpoint. It does not train new ablation checkpoints. Rows that require a new training checkpoint are present but marked `NOT_RUN_WITH_REASON`.

Required evidence columns are split across `same_split_help_harm.csv`, `gate_residual_by_ablation.csv`, `prototype_dictionary_by_ablation.csv`, and `proposal_refinement_by_ablation.csv`.
