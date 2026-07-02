# 20260629 Rescue Goal Partition Status

- generated_at: `2026-07-02 15:03:34 EDT`
- routing_priority: `htzhulab > a100-gpu > volta-gpu`

| partition | rank | role | pending | running | other | pending reasons |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| htzhulab | 1 | preferred | 0 | 2 | 0 |  |
| a100-gpu | 2 | fallback_after_htzhulab_long_wait | 431 | 20 | 0 | (AssocGrpGRES):2; (JobHeldUser):219; (Priority):209; (Resources):1 |
| volta-gpu | 3 | fallback_after_a100_long_wait | 13 | 64 | 0 | (AssocGrpGRES):8; (Dependency):1; (Priority):3; (Resources):1 |

## Notes

- This is a read-only queue snapshot for routing decisions; it does not authorize a new GPU submission.
- `sinfo` details and any query errors are preserved in `gpu_partition_status.csv`.
