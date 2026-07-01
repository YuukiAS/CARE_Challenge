# 20260629 Rescue Goal Partition Status

- generated_at: `2026-07-01 13:34:49 EDT`
- routing_priority: `htzhulab > a100-gpu > volta-gpu`

| partition | rank | role | pending | running | other | pending reasons |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| htzhulab | 1 | preferred | 1 | 8 | 0 | (Resources):1 |
| a100-gpu | 2 | fallback_after_htzhulab_long_wait | 467 | 23 | 0 | (AssocGrpGRES):9; (JobHeldUser):219; (Priority):238; (Resources):1 |
| volta-gpu | 3 | fallback_after_a100_long_wait | 148 | 64 | 0 | (AssocGrpGRES):101; (Dependency):19; (Priority):27; (Resources):1 |

## Notes

- This is a read-only queue snapshot for routing decisions; it does not authorize a new GPU submission.
- `sinfo` details and any query errors are preserved in `gpu_partition_status.csv`.
