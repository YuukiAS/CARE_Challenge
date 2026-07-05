# Commands Run

- training_command: `python scripts/training/run_srr_propref_myops_fold0.py --variant srr_propref_shared_dual_dict --run-label srr_v3_m3_shared_dual_dict_pilot --fold 0 --device cuda --base-channels 8 --encoder-profile strong_4scale --patch-shape 12,96,96 --batch-size 2 --max-steps 6000 --max-runtime-seconds 25200 --val-every 300 --overfit-steps 60 --prototype-bank-cases 8 --max-eval-cases 12 --train-case-ids Case1004,Case1028,Case2001,Case2004,Case3001,Case3008,Case3032,Case5001,Case6002,Case7006,Case8001,Case8028 --eval-case-ids Case1029,Case1045,Case2002,Case2008,Case2031,Case3004,Case3012,Case3023,Case3038,Case5005,Case7005,Case8011 --proposal-thresholds 0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90 --scar-decode-threshold 0.50 --edema-decode-threshold 0.50 --out-root /users/a/e/aereinh/CARE/results/20260705_srr_v3_m3_myops_min_effective_pilot_training --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv`
- aggregate_command: `scripts/evaluation/aggregate_srr_v3_m3_pilot.py --out-root results/20260705_srr_v3_m3_myops_min_effective_pilot_training --variant srr_v3_m3_shared_dual_dict_pilot --training-command python scripts/training/run_srr_propref_myops_fold0.py --variant srr_propref_shared_dual_dict --run-label srr_v3_m3_shared_dual_dict_pilot --fold 0 --device cuda --base-channels 8 --encoder-profile strong_4scale --patch-shape 12,96,96 --batch-size 2 --max-steps 6000 --max-runtime-seconds 25200 --val-every 300 --overfit-steps 60 --prototype-bank-cases 8 --max-eval-cases 12 --train-case-ids Case1004,Case1028,Case2001,Case2004,Case3001,Case3008,Case3032,Case5001,Case6002,Case7006,Case8001,Case8028 --eval-case-ids Case1029,Case1045,Case2002,Case2008,Case2031,Case3004,Case3012,Case3023,Case3038,Case5005,Case7005,Case8011 --proposal-thresholds 0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90 --scar-decode-threshold 0.50 --edema-decode-threshold 0.50 --out-root /users/a/e/aereinh/CARE/results/20260705_srr_v3_m3_myops_min_effective_pilot_training --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv`
- aggregate_time_utc: `2026-07-05T16:37:07.017362+00:00`
- network_used: `false`

Additional executor commands:

- `grep -n 'M2_AUDITED_GO' results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md`
- `python -m py_compile scripts/training/run_srr_propref_myops_fold0.py scripts/evaluation/aggregate_srr_v3_m3_pilot.py`
- `bash -n jobs/src/run_srr_v3_m3_myops_min_effective_pilot.sh`
- `sbatch jobs/src/run_srr_v3_m3_myops_min_effective_pilot.sh`
- `scancel 57928435`
- `sbatch --partition=a100-gpu --qos=gpu_access --gres=gpu:nvidia_a100-pcie-40gb:1 jobs/src/run_srr_v3_m3_myops_min_effective_pilot.sh`
- `sacct -j 57944737 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,MaxRSS,AllocTRES%40`
