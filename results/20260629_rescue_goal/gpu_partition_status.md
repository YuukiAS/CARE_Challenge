# 20260629 Rescue Goal Partition Status

- generated_at: `2026-07-01 20:20:56 EDT`
- routing_priority: `htzhulab > a100-gpu > volta-gpu`

| partition | rank | role | pending | running | other | pending reasons |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| htzhulab | 1 | preferred | 5 | 2 | 0 | (PartitionDown):5 |
| a100-gpu | 2 | fallback_after_htzhulab_long_wait | 471 | 23 | 0 | (JobHeldUser):219; (PartitionDown):252 |
| volta-gpu | 3 | fallback_after_a100_long_wait | 143 | 33 | 0 | (PartitionDown):143 |

## Notes

- This is a read-only queue snapshot for routing decisions; it does not authorize a new GPU submission.
- `sinfo` details and any query errors are preserved in `gpu_partition_status.csv`.
