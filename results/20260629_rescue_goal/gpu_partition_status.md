# 20260629 Rescue Goal Partition Status

- generated_at: `2026-07-01 18:47:56 EDT`
- routing_priority: `htzhulab > a100-gpu > volta-gpu`

| partition | rank | role | pending | running | other | pending reasons |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| htzhulab | 1 | preferred | 3 | 4 | 0 | (Priority):1; (Resources):2 |
| a100-gpu | 2 | fallback_after_htzhulab_long_wait | 452 | 23 | 0 | (AssocGrpGRES):100; (BeginTime):1; (JobHeldUser):219; (Priority):131; (Resources):1 |
| volta-gpu | 3 | fallback_after_a100_long_wait | 109 | 49 | 0 | (AssocGrpGRES):1; (BeginTime):1; (Priority):107 |

## Notes

- This is a read-only queue snapshot for routing decisions; it does not authorize a new GPU submission.
- `sinfo` details and any query errors are preserved in `gpu_partition_status.csv`.
