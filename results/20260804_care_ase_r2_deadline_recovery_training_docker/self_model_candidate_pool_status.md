# Self-model candidate pool status

nnU-Net is reference only and is not a submission candidate in this pool.

## Current Best Direct/Active Candidates
- scar: CARE-ASE_step00500_fold1_fold4_mean (CARE-ASE-current) Dice 0.549352; nnU-Net reference 0.567295; delta -0.017943.
- pure_edema: CARE-ASE_step00500_fold1_fold4_mean (CARE-ASE-current) Dice 0.397940; nnU-Net reference 0.403784; delta -0.005844.

## Candidate Rows
| family | candidate | pathology | cases | dice | nnUNet reference | delta | status |
|---|---|---|---:|---:|---:|---:|---|
| SRR-Cascade | control_seed20260724 | pure_edema | 8 | 0.422716 | 0.421165 | 0.001550 | second_tier_not_direct_docker_candidate |
| CARE-ASE-current | CARE-ASE_step00500_fold1_fold4_mean | pure_edema | 32 | 0.397940 | 0.403784 | -0.005844 | active_training_candidate |
| MMRD/Batch10 | MMRD_Batch10_teacher_two_seed_mean_raw_argmax | pure_edema | 16 | 0.396973 | 0.394436 | 0.002537 | possible_artifact_exists_but_not_selected |
| SRR-Cascade | control_seed20260724 | pure_edema | 16 | 0.394646 | 0.391457 | 0.003189 | second_tier_not_direct_docker_candidate |
| CARE-ASE-current | CARE-ASE_step00750_fold1_fold4_mean | pure_edema | 32 | 0.393550 | 0.403823 | -0.010274 | active_training_candidate |
| CARE-ASE-current | CARE-ASE_step01000_fold1_fold4_mean | pure_edema | 32 | 0.393025 | 0.403811 | -0.010786 | active_training_candidate |
| MMRD/Batch10 | MMRD_Batch10_distill_epoch25_two_seed_mean_raw_argmax | pure_edema | 16 | 0.376217 | 0.394436 | -0.018219 | possible_artifact_exists_but_not_selected |
| MMRD/Batch10 | MMRD_Batch10_control_epoch25_two_seed_mean_raw_argmax | pure_edema | 16 | 0.374694 | 0.394436 | -0.019742 | possible_artifact_exists_but_not_selected |
| DG | repaired_formal_scar_priority_step4000_A2_care_dg | pure_edema | 16 | 0.344373 | 0.394436 | -0.050063 | not_candidate: below nnU-Net on requested fair population |
| DG | DG_parity_recompute_scr_r1_predictions_pure_edema_binary | pure_edema | 16 | 0.140591 | 0.394436 | -0.253844 | not_direct_docker_candidate_for_requested_formal_dg |
| SRR-Cascade | control_two_seed_probability_mean_derived_bounded_channel_correction | scar | 22 | 0.615020 | 0.612181 | 0.002839 | second_tier_not_direct_docker_candidate |
| SRR-Cascade | control_two_seed_probability_mean_derived_bounded_channel_correction | scar | 43 | 0.564420 | 0.561030 | 0.003390 | second_tier_not_direct_docker_candidate |
| CARE-ASE-current | CARE-ASE_step00500_fold1_fold4_mean | scar | 88 | 0.549352 | 0.567295 | -0.017943 | active_training_candidate |
| CARE-ASE-current | CARE-ASE_step01000_fold1_fold4_mean | scar | 88 | 0.547311 | 0.567306 | -0.019995 | active_training_candidate |
| MMRD/Batch10 | MMRD_Batch10_control_epoch25_two_seed_mean_raw_argmax | scar | 44 | 0.546192 | 0.560169 | -0.013977 | possible_artifact_exists_but_not_selected |
| CARE-ASE-current | CARE-ASE_step00750_fold1_fold4_mean | scar | 88 | 0.546037 | 0.567298 | -0.021261 | active_training_candidate |
| MMRD/Batch10 | MMRD_Batch10_distill_epoch25_two_seed_mean_raw_argmax | scar | 44 | 0.545553 | 0.560169 | -0.014616 | possible_artifact_exists_but_not_selected |
| DG | repaired_formal_scar_priority_step4000_A2_care_dg | scar | 44 | 0.545220 | 0.560169 | -0.014949 | not_candidate: below nnU-Net on requested fair population |
| MMRD/Batch10 | MMRD_Batch10_teacher_two_seed_mean_raw_argmax | scar | 44 | 0.514367 | 0.560169 | -0.045803 | possible_artifact_exists_but_not_selected |
| DG | DG_parity_recompute_scr_r1_predictions_scar_binary | scar | 44 | 0.199522 | 0.560169 | -0.360647 | not_direct_docker_candidate_for_requested_formal_dg |
