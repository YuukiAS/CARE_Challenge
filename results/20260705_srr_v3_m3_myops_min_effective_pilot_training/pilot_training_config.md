# Pilot Training Config

task: `prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md`
variant: `srr_v3_m3_shared_dual_dict_pilot`
model_variant: `srr_propref_shared_dual_dict`
fold: `0`
device: `cuda`
encoder_profile: `strong_4scale`
encoder_scale_channels: `[8, 16, 32, 64]`
base_channels: `8` from training command; full scale channels are recorded above
patch_shape: derived from training command and summary; eval cases `Case1029;Case1045;Case2002;Case2008;Case2031;Case3004;Case3012;Case3023;Case3038;Case5005;Case7005;Case8011`
train_case_selection: `explicit_train_case_ids`
train_case_ids: `Case1004;Case1028;Case2001;Case2004;Case3001;Case3008;Case3032;Case5001;Case6002;Case7006;Case8001;Case8028`
eval_case_selection: `explicit_eval_case_ids`
eval_case_ids: `Case1029;Case1045;Case2002;Case2008;Case2031;Case3004;Case3012;Case3023;Case3038;Case5005;Case7005;Case8011`
checkpoint_best: `/users/a/e/aereinh/CARE/results/20260705_srr_v3_m3_myops_min_effective_pilot_training/variants/srr_v3_m3_shared_dual_dict_pilot/checkpoints/fold_0/propref_config/checkpoint_best.pt`
checkpoint_final: `/users/a/e/aereinh/CARE/results/20260705_srr_v3_m3_myops_min_effective_pilot_training/variants/srr_v3_m3_shared_dual_dict_pilot/checkpoints/fold_0/propref_config/checkpoint_final.pt`
command: `python scripts/training/run_srr_propref_myops_fold0.py --variant srr_propref_shared_dual_dict --run-label srr_v3_m3_shared_dual_dict_pilot --fold 0 --device cuda --base-channels 8 --encoder-profile strong_4scale --patch-shape 12,96,96 --batch-size 2 --max-steps 6000 --max-runtime-seconds 25200 --val-every 300 --overfit-steps 60 --prototype-bank-cases 8 --max-eval-cases 12 --train-case-ids Case1004,Case1028,Case2001,Case2004,Case3001,Case3008,Case3032,Case5001,Case6002,Case7006,Case8001,Case8028 --eval-case-ids Case1029,Case1045,Case2002,Case2008,Case2031,Case3004,Case3012,Case3023,Case3038,Case5005,Case7005,Case8011 --proposal-thresholds 0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90 --scar-decode-threshold 0.50 --edema-decode-threshold 0.50 --out-root /users/a/e/aereinh/CARE/results/20260705_srr_v3_m3_myops_min_effective_pilot_training --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv`

Scope: controlled fold0 pilot subset, not full fold training, not route promotion, not validation packaging/upload.
