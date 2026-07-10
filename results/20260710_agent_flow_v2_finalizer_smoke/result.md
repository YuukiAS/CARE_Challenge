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
| COMPLETED with runtime output plus aggregator/validator exit 0 | local packet commit-ready state | `READY_FOR_LOCAL_PACKET_COMMIT` |
| COMPLETED with missing runtime output | `NEEDS_EVIDENCE` | `NEEDS_EVIDENCE` |
| FAILED job | runtime failure evidence, not scheduler block | `RUNTIME_FAILURE` |
| PENDING before 12 consecutive 2-hour checks | `NEEDS_MONITOR`, not blocked | `NEEDS_MONITOR` |

## Boundary

The smoke used only synthetic accounting fixtures and `/tmp` runtime files. No
real Slurm training job was submitted and no model or historical result packet
was changed.
