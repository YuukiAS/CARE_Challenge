# Commands Run

| Command | Exit | Purpose |
|---|---:|---|
| `./envs/env_CARE/bin/python -m pytest tests/srr_production/test_myops_batch6_objective_alignment.py tests/srr_production/test_myops_batch5_diagnostics.py tests/srr_production/test_myops_batch4_contract.py` | 0 | Focused Batch6/Batch5/Batch4 regression suite; latest run passed 26 tests. |
| `./envs/env_CARE/bin/python -m py_compile scripts/evaluation/reconcile_srr_batch6_batch5_evidence.py scripts/training/run_srr_batch6_fixed_overfit.py` | 0 | Syntax check new executor scripts. |
| `./envs/env_CARE/bin/python scripts/evaluation/audit_srr_batch5_loss_authority.py --config configs/srr_production/myops_batch6.yaml --result-root results/20260721_srr_batch6_final_objective_alignment --fixed-case-count 2` | 0 | Zero-step Batch5/Batch6 loss authority reconciliation; parameter hash unchanged. |
| `./envs/env_CARE/bin/python scripts/evaluation/reconcile_srr_batch6_batch5_evidence.py --result-root results/20260721_srr_batch6_final_objective_alignment --batch5-root results/20260721_srr_batch5_post_batch4_diagnostic_repair --batch4-root results/20260721_srr_batch4_forced_fold0_training` | 0 | Build pure intervention and proposal/ROI reconciliation tables. |
| `./envs/env_CARE/bin/python scripts/evaluation/validate_srr_batch6_packet.py --result-root results/20260721_srr_batch6_final_objective_alignment` | 0 | Validate Batch6 stop packet; returned `BATCH6_STOP_PACKET_VALIDATION_PASS`, `formal_training_submitted=false`, `slurm_attempt_count=4`. |
| `squeue -p htzhulab` | 0 | Slurm queue inspection via escalated scheduler access. |
| `sinfo -o '%P\|%a\|%l\|%D\|%t\|%G'` | 0 | Slurm partition inspection via escalated scheduler access. |
| `sbatch jobs/srr_production/run_myops_batch6_fixed_overfit_htzhulab.sh` | 0 | Submitted fixed-overfit attempt `59737558`. |
| `sbatch jobs/srr_production/run_myops_batch6_fixed_overfit_htzhulab.sh` | 0 | Submitted fixed-overfit attempt `59737686`. |
| `sbatch jobs/srr_production/run_myops_batch6_fixed_overfit_htzhulab.sh` | 0 | Submitted fixed-overfit attempt `59737738`. |
| `sbatch jobs/srr_production/run_myops_batch6_fixed_overfit_htzhulab.sh` | 0 | Submitted fixed-overfit attempt `59737830`. |
| `sacct -j 59737558 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList -P` | 0 | Terminal accounting: `FAILED`, exit `1:0`, elapsed `00:00:34`. |
| `sacct -j 59737686 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList -P` | 0 | Terminal accounting: `FAILED`, exit `1:0`, elapsed `00:00:32`. |
| `sacct -j 59737738 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList -P` | 0 | Terminal accounting: `FAILED`, exit `1:0`, elapsed `00:00:34`. |
| `sacct -j 59737830 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList -P` | 0 | Terminal accounting: `FAILED`, exit `1:0`, elapsed `00:00:28`. |
