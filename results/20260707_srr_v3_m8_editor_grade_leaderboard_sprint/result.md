# M8 Executor Result

status: `M8_NEEDS_MONITOR_NO_REVIEW`

M8 start gates passed, config contract was written, and Slurm jobs were submitted or prepared for MyoPS long training and Cine mature registration. This packet is monitor-only until completed jobs are re-aggregated. It is not ready for review and does not claim route promotion, validation packaging/upload, hosted metrics, challenge readiness, scientific stop, fold expansion, or M9.

- git_head: `b3c3b0584752163a26bf7c231401b61be26c626b`
- current_head: `672daafd8dd6bd9b433b5aab95bcabeda82ed815`
- updated_at_utc: `2026-07-07T04:36:09Z`
- myops_cancelled_pre_race_job_id: `58080244;58081025`
- myops_htzhulab_job_id: `58081007`
- myops_a100_job_id: `58081025`
- myops_race_watcher_job_id: `58081026`
- myops_race_log_path: `logs/SRRv3M8MyOPSRace_58081007_58081025.log`
- myops_task2_a100_mirror_job_id: `58081494`
- myops_task2_race_watcher_job_id: `58081496`
- myops_task2_race_log_path: `logs/SRRv3M8MyOPSTask2Race_58081007_2_58081494.log`
- cancelled_lockless_cine_job_id: `58081208`
- cine_htzhulab_job_id: `58081476`
- cine_a100_job_id: `58081477`
- cine_race_watcher_job_id: `58081479`
- cine_race_log_path: `logs/SRRv3M8CineRace_58081476_58081477.log`
- partition_note: `M8 monitor: MyoPS tasks 0/1 are running on htzhulab; task 2 has a task-specific htzhulab/a100 race pending under the per-variant lock. The previous lockless Cine job was cancelled while pending, and mandatory Cine mature registration now has a lock-safe htzhulab/a100 race pending with watcher.`
