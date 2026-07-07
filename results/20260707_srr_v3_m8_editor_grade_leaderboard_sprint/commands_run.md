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
| `scancel 58081208` | exit 0 | Cancel the previous pending Cine job because it was submitted before the Cine scripts had an atomic routing lock. |
| `bash -n jobs/src/run_srr_v3_m8_cine_registration_mature.sh` | exit 0 | Syntax-check the a100 Cine lock-safe script. |
| `bash -n jobs/src/run_srr_v3_m8_cine_registration_mature_htzhulab.sh` | exit 0 | Syntax-check the htzhulab Cine lock-safe script. |
| `sbatch --parsable jobs/src/run_srr_v3_m8_cine_registration_mature_htzhulab.sh` | submitted `58081476` | Start the htzhulab side of the lock-safe Cine mature-registration race. |
| `sbatch --parsable jobs/src/run_srr_v3_m8_cine_registration_mature.sh` | submitted `58081477` | Start the a100-gpu side of the lock-safe Cine mature-registration race. |
| `sbatch --wrap python scripts/evaluation/watch_srr_v3_m8_myops_race.py --htzhulab-job-id 58081476 --a100-job-id 58081477 ...` | submitted `58081479` | Watch the Cine partition race and cancel the pending mirror when one side starts. |
| `sbatch --parsable --array=2 jobs/src/run_srr_v3_m8_myops_leaderboard_sprint.sh` | submitted `58081494` | Add an a100-gpu mirror for only the still-pending MyoPS task2 variant. |
| `sbatch --wrap python scripts/evaluation/watch_srr_v3_m8_myops_race.py --htzhulab-job-id 58081007_2 --a100-job-id 58081494 ...` | submitted `58081496` | Watch the task-specific MyoPS task2 race without treating task0/1 as task2 progress. |
| `squeue -j 58081007,58081476,58081477,58081479,58081494,58081496 -o '%i|%P|%j|%t|%M|%D|%R'` | exit 0 | Check current MyoPS and Cine race states after supplemental submissions. |
| `sacct -j 58081007,58081476,58081477,58081479,58081494,58081496 --format=JobID,JobName%30,Partition,State,ExitCode,Elapsed,Start,End -P` | exit 0 | Record current accounting state after supplemental submissions. |
