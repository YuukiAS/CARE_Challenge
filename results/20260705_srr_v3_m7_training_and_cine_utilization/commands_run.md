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
| `python scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py --max-cases 3 --pairs-per-case 2 --demons-iterations 10` | exit 0 | Run M7 continued Cine non-reference registration repair attempt. |
| `python scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py --max-cases 3 --pairs-per-case 2 --demons-iterations 10 --antspy-iterations 5` | exit 0 | Run M7 continued Cine non-reference registration repair attempt. |
| `python scripts/evaluation/run_srr_v3_m7_continued_repair.py --device cpu --max-formal-val-cases 8` | exit 137 | CPU M7 continued helper attempted after gradient repair; killed before formal-val metric completion, likely memory pressure. |
| `sbatch --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access jobs/src/run_srr_v3_m7_continued_repair.sh` | job 58012638 failed | Volta fallback failed because current PyTorch build does not support Tesla V100 compute capability 7.0. |
| `sbatch --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access jobs/src/run_srr_v3_m7_continued_repair.sh` | submitted job 58012822 | Lock-protected A100 fallback for M7 continued MyoPS formal-val metric helper. |
| `sbatch jobs/src/run_srr_v3_m7_continued_repair.sh` | submitted job 58012814 | Lock-protected htzhulab fallback for M7 continued MyoPS formal-val metric helper. |
| `sbatch --partition=l40-gpu --gres=gpu:1 --qos=gpu_access jobs/src/run_srr_v3_m7_continued_repair.sh` | submitted job 58012903 | L40 compatibility fallback after Volta proved incompatible with current PyTorch CUDA build. |
| `OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python scripts/evaluation/run_srr_v3_m7_continued_repair.py --device cpu --max-formal-val-cases 8` | exit 137 | Retried local CPU helper after lazy per-case memory reduction; still killed before formal-val metric completion. |
| `scancel 58012822 58012814 58012903` | exit 0 | Cancel 4-hour pending race jobs before shorter backfill-friendly resubmission. |
| `sbatch --time=1:00:00 --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access jobs/src/run_srr_v3_m7_continued_repair.sh` | submitted job 58013360 | Short A100 race job for M7 continued MyoPS helper. |
| `sbatch --time=1:00:00 jobs/src/run_srr_v3_m7_continued_repair.sh` | submitted job 58013358 | Short htzhulab race job for M7 continued MyoPS helper. |
| `sbatch --time=1:00:00 --partition=l40-gpu --gres=gpu:1 --qos=gpu_access jobs/src/run_srr_v3_m7_continued_repair.sh` | submitted job 58013359 | Short L40 race job for M7 continued MyoPS helper. |
| `sbatch jobs/src/run_srr_v3_m7_continued_repair_cpu.sh` | submitted job 58013504 | High-memory CPU fallback for M7 continued MyoPS helper after local CPU exit 137 and GPU queues remained pending. |
| `sbatch --time=1:00:00 --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access jobs/src/run_srr_v3_m7_continued_repair.sh` | submitted job 58014829 | Re-queued compatible A100 fallback while CPU high-memory helper runs; intended to execute if CPU times out before formal-val metrics complete. |
| `python scripts/evaluation/run_srr_v3_m7_continued_repair.py --device cpu --max-formal-val-cases 8` | exit 0 | Run M7 continued MyoPS graph-gradient and formal subgroup repair helper. |
| `python -m py_compile scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py` | exit 0 | Validate aggregator syntax after adding M7 continued fail-closed guard. |
| `python scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py --job-state-snapshot 'M7 continued CPU helper 58013504 completed; A100 fallback 58014829 canceled'` | exit 0 | Exercise M7 continued fail-closed aggregator guard without overwriting continued metric CSVs. |
| `scancel 58014829` | exit 0 | Cancel pending A100 fallback after CPU helper completed successfully. |
