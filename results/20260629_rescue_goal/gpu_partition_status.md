# 20260629 Rescue Goal Partition Status

- generated_at: `2026-07-02 03:40:04 EDT`
- routing_priority: `htzhulab > a100-gpu > volta-gpu`

| partition | rank | role | pending | running | other | pending reasons |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| htzhulab | 1 | preferred | 4 | 6 | 0 | (Dependency):1; (Priority):2; (Resources):1 |
| a100-gpu | 2 | fallback_after_htzhulab_long_wait | 442 | 22 | 0 | (AssocGrpGRES):4; (JobHeldUser):219; (Priority):218; (Resources):1 |
| volta-gpu | 3 | fallback_after_a100_long_wait | 94 | 56 | 0 | (AssocGrpGRES):12; (Dependency):3; (Priority):78; (Resources):1 |

## Notes

- This is a read-only queue snapshot for routing decisions; it does not authorize a new GPU submission.
- `sinfo` details and any query errors are preserved in `gpu_partition_status.csv`.
