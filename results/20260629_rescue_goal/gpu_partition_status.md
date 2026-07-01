# 20260629 Rescue Goal Partition Status

- generated_at: `2026-07-01 17:35:42 EDT`
- routing_priority: `htzhulab > a100-gpu > volta-gpu`

| partition | rank | role | pending | running | other | pending reasons |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| htzhulab | 1 | preferred | 1 | 8 | 0 | (Resources):1 |
| a100-gpu | 2 | fallback_after_htzhulab_long_wait | 472 | 23 | 0 | (AssocGrpGRES):100; (JobHeldUser):219; (Priority):152; (Resources):1 |
| volta-gpu | 3 | fallback_after_a100_long_wait | 112 | 64 | 0 | (AssocGrpGRES):88; (Dependency):19; (Priority):4; (Resources):1 |

## Notes

- This is a read-only queue snapshot for routing decisions; it does not authorize a new GPU submission.
- `sinfo` details and any query errors are preserved in `gpu_partition_status.csv`.
