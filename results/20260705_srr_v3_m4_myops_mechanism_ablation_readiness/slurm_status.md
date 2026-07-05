# Slurm Status

job_id: `57981754`
partition: `a100-gpu`
qos: `gpu_access`
state: `COMPLETED`
exit_code: `0:0`
elapsed: `00:07:25`
max_rss_batch: `2516988K`

Submission command:

```bash
sbatch --partition=a100-gpu --qos=gpu_access --gres=gpu:nvidia_a100-pcie-40gb:1 jobs/src/run_srr_v3_m4_myops_mechanism_ablation.sh
```

Verification command:

```bash
sacct -j 57981754 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
```

Log path, not committed:

```text
logs/SRRv3M4Ablation_57981754_20260705_192911.log
```
