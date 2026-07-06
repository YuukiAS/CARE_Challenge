# Commands Run

| command | status | purpose |
| --- | --- | --- |
| `python -m py_compile scripts/training/run_srr_propref_myops_fold0.py` | exit 0 | Validate M7 training script syntax. |
| `bash -n jobs/src/run_srr_v3_m7_myops_training.sh` | exit 0 | Validate M7 Slurm job script syntax. |
| `sbatch --array=0-2 --partition=a100-gpu --qos=gpu_access --gres=gpu:nvidia_a100-pcie-40gb:1 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58003931 | Submit A100 routing array. |
| `sbatch --array=0-2 --partition=htzhulab --qos=gpu_access --gres=gpu:1 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58003950 | Submit htzhulab routing mirror. |
| `python scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py ...` | exit 0 | Write current M7 monitor packet. |
| `tmux new-session -d -s m7-routing-watch ... watch_srr_v3_m7_routing.py --interval-seconds 7200 --pending-block-threshold 12` | running | Poll routing arrays every 2 hours while pending, cancel the pending mirror once one partition starts, and allow blocked status only after 12 consecutive all-pending checks. |

job_state_snapshot: `a100:PD(Priority); htzhulab:PD(Resources)`
