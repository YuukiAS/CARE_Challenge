# Commands Run

| command | status | purpose |
| --- | --- | --- |
| `scancel 58080244;58081025` | exit 0 | Cancel pre-race single-partition M8 MyoPS job before resubmitting lock-safe mirror jobs. |
| `sbatch jobs/src/run_srr_v3_m8_myops_leaderboard_sprint_htzhulab.sh` | submitted `58081007` | Start M8 MyoPS htzhulab race mirror. |
| `sbatch jobs/src/run_srr_v3_m8_myops_leaderboard_sprint.sh` | submitted `58081025` | Start M8 MyoPS a100-gpu race mirror. |
| `sbatch --wrap python scripts/evaluation/watch_srr_v3_m8_myops_race.py ...` | submitted `58081026` | Watch htzhulab/a100 race and cancel the pending mirror when one starts. |
| `sbatch jobs/src/run_srr_v3_m8_cine_registration_mature.sh` | not submitted | Start M8 mature Cine registration attempt. |
| `python scripts/evaluation/initialize_srr_v3_m8_packet.py ...` | exit 0 | Initialize monitor-only M8 packet. |
| `tail -n 120 logs/SRRv3M8MyOPS_htzhulab_*.log` | exit 0 | Diagnose first race failure as `KeyError: correction_opportunity_loss`. |
| `rm -rf results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/runtime` | exit 0 | Remove stale failed runtime locks/partials before corrected race. |
| `sbatch jobs/src/run_srr_v3_m8_myops_leaderboard_sprint_htzhulab.sh` | submitted `58081007` | Start corrected M8 MyoPS htzhulab race mirror after loss-routing fix. |
| `sbatch jobs/src/run_srr_v3_m8_myops_leaderboard_sprint.sh` | submitted `58081025` | Start corrected M8 MyoPS a100-gpu race mirror after loss-routing fix. |
| `sbatch --wrap python scripts/evaluation/watch_srr_v3_m8_myops_race.py ...` | submitted `58081026` | Watch corrected htzhulab/a100 race and cancel pending mirror. |
| `squeue -j 58081007,58081025,58081026 -o "%.18i %.9P %.30j %.8T %.10M %.10l %.6D %R"` | exit 0 | Check corrected M8 race state. |
| `sacct -j 58080628,58080627,58080636,58081007,58081025,58081026 --format=JobID,JobName%24,Partition,State,ExitCode,Elapsed,Start,End -P` | exit 0 | Record first failed race and corrected race accounting. |
