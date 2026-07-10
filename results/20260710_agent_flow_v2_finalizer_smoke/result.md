# Agent-Flow v2 Finalizer Smoke

This lightweight smoke did not submit Slurm jobs, train models, package
validation, upload, or modify historical result packets. It ran
`scripts/ops/care_milestone_finalizer.py` against synthetic `/tmp` sacct
fixtures.

## Cases

| Case | Expected | Observed |
| --- | --- | --- |
| PENDING job | `NEEDS_MONITOR` | `NEEDS_MONITOR` |
| RUNNING job | `NEEDS_MONITOR` | `NEEDS_MONITOR` |
| AWAITING_SACCT then accounting appears | continue finalization | `READY_FOR_MAPPER_FINAL` |
| AWAITING_SACCT retry exhausted | honest accounting wait state | `AWAITING_SACCT_RETRY_EXHAUSTED` |
| COMPLETED with runtime output plus aggregator exit 0 | mapper-final-ready state | `READY_FOR_MAPPER_FINAL` |
| COMPLETED with missing runtime output | `NEEDS_EVIDENCE` | `NEEDS_EVIDENCE` |
| FAILED job | runtime failure evidence, not scheduler block | `RUNTIME_FAILURE` |
| PENDING before 12 consecutive 2-hour checks | `NEEDS_MONITOR`, not blocked | `NEEDS_MONITOR` |
| Lock release | normal and handled-failure exits release lock | `lock_released=true` |

After the follow-up repair, finalizer accounting runs use `FINALIZER_A` semantics.
`COMPLETED + outputs` now reaches `READY_FOR_MAPPER_FINAL`; local packet commit
is reserved for `FINALIZER_B` after mapper final and validators.

## Boundary

The smoke used only synthetic accounting fixtures and `/tmp` runtime files. No
real Slurm training job was submitted and no model or historical result packet
was changed.
