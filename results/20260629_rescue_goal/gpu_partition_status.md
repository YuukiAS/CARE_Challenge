# 20260629 Rescue Goal Partition Status

- generated_at: `2026-07-01 22:55:02 EDT`
- routing_priority: `htzhulab > a100-gpu > volta-gpu`

| partition | rank | role | pending | running | other | pending reasons |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| htzhulab | 1 | preferred | 5 | 2 | 0 | (PartitionDown):5 |
| a100-gpu | 2 | fallback_after_htzhulab_long_wait | 476 | 17 | 0 | (JobHeldUser):219; (PartitionDown):257 |
| volta-gpu | 3 | fallback_after_a100_long_wait | 156 | 33 | 0 | (Dependency):3; (PartitionDown):153 |

## Notes

- This is a read-only queue snapshot for routing decisions; it does not authorize a new GPU submission.
- `sinfo` details and any query errors are preserved in `gpu_partition_status.csv`.
