# Commands Run

| command | status | purpose |
| --- | --- | --- |
| `scancel 58080244;58081025` | exit 0 | Cancel pre-race single-partition M8 MyoPS job before resubmitting lock-safe mirror jobs. |
| `sbatch jobs/src/run_srr_v3_m8_myops_leaderboard_sprint_htzhulab.sh` | submitted `58081007` | Start M8 MyoPS htzhulab race mirror. |
| `sbatch jobs/src/run_srr_v3_m8_myops_leaderboard_sprint.sh` | submitted `58081025` | Start M8 MyoPS a100-gpu race mirror. |
| `sbatch --wrap python scripts/evaluation/watch_srr_v3_m8_myops_race.py ...` | submitted `58081026` | Watch htzhulab/a100 race and cancel the pending mirror when one starts. |
| `sbatch jobs/src/run_srr_v3_m8_cine_registration_mature_htzhulab.sh` | submitted `58081208` | Start M8 mature Cine registration attempt. |
| `python scripts/evaluation/initialize_srr_v3_m8_packet.py ...` | exit 0 | Initialize monitor-only M8 packet. |
| `squeue -j 58081007,58081025,58081026,58081208 -o "%.18i %.9P %.30j %.8T %.10M %.10l %.6D %R"` | exit 0 | Check current M8 MyoPS and Cine job states. |
| `sacct -j 58081007,58081025,58081026,58081208 --format=JobID,JobName%24,Partition,State,ExitCode,Elapsed,Start,End -P` | exit 0 | Record current M8 MyoPS/Cine accounting state. |
