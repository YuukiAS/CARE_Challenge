# Commands Run

| command | status | purpose |
| --- | --- | --- |
| `sbatch jobs/src/run_srr_v3_m8_myops_leaderboard_sprint.sh` | submitted `58080244` | Start M8 MyoPS long-training array. |
| `sbatch jobs/src/run_srr_v3_m8_cine_registration_mature.sh` | not submitted | Start M8 mature Cine registration attempt. |
| `python scripts/evaluation/initialize_srr_v3_m8_packet.py --myops-job-id 58080244 --cine-job-id ` | exit 0 | Initialize monitor-only M8 packet. |
