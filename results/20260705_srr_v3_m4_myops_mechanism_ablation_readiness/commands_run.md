# Commands Run

- command: `scripts/evaluation/run_srr_v3_m4_mechanism_ablation.py --output-dir results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness --m3-dir results/20260705_srr_v3_m3_myops_min_effective_pilot_training --m3-variant srr_v3_m3_shared_dual_dict_pilot --device cuda`
- slurm_submit: `sbatch --partition=a100-gpu --qos=gpu_access --gres=gpu:nvidia_a100-pcie-40gb:1 jobs/src/run_srr_v3_m4_myops_mechanism_ablation.sh`
- slurm_job_id: `57981754`
- slurm_result: `COMPLETED 0:0 00:07:25`
- aggregate_time_utc: `2026-07-05T23:35:57.272748+00:00`
- network_used: `false`
