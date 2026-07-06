# Commands Run

| command | status | purpose |
| --- | --- | --- |
| `python -m py_compile scripts/training/run_srr_propref_myops_fold0.py` | exit 0 | Validate M7 training script syntax. |
| `bash -n jobs/src/run_srr_v3_m7_myops_training.sh` | exit 0 | Validate M7 Slurm job script syntax. |
| `sbatch --array=0-2 --partition=a100-gpu --qos=gpu_access --gres=gpu:nvidia_a100-pcie-40gb:1 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58003931 | Submit A100 routing array. |
| `sbatch --array=0-2 --partition=htzhulab --qos=gpu_access --gres=gpu:1 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58003950 | Submit htzhulab routing mirror. |
| `sbatch --array=0 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58004740 | Fresh guarded rerun for task0 after min-duration guard was added. |
| `sbatch --array=1-2 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58005318 | Fresh guarded rerun for task1/task2 after min-duration guard was added. |
| `python scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py ...` | exit 0 | Write current M7 monitor packet. |

job_state_snapshot: `58004740_0 COMPLETED 00:32:04; 58005318_1 COMPLETED 00:32:18; 58005318_2 COMPLETED 00:31:50`
