# 20260629 Rescue Goal Partition Status

- generated_at: `2026-07-01 19:22:42 EDT`
- routing_priority: `htzhulab > a100-gpu > volta-gpu`

| partition | rank | role | pending | running | other | pending reasons |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| htzhulab | 1 | preferred | 5 | 2 | 0 | (Nodes required for job are DOWN, DRAINED or reserved for jobs in higher priority partitions):1; (Priority):3; (Resources):1 |
| a100-gpu | 2 | fallback_after_htzhulab_long_wait | 461 | 23 | 0 | (AssocGrpGRES):100; (JobHeldUser):219; (Priority):140; (Resources):2 |
| volta-gpu | 3 | fallback_after_a100_long_wait | 111 | 45 | 0 | (AssocGrpGRES):1; (Priority):109; (Resources):1 |

## Notes

- This is a read-only queue snapshot for routing decisions; it does not authorize a new GPU submission.
- `sinfo` details and any query errors are preserved in `gpu_partition_status.csv`.
