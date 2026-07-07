# M8 Slurm Race Status

status: `M8_NEEDS_MONITOR_NO_REVIEW`

## Routing Decision

AGENTS.md compute-resource rules were applied after the initial single-partition a100-gpu job was found still pending.

- cancelled pre-race job: `58080244`
- htzhulab mirror array: `58080628`
- a100-gpu mirror array: `58080627`
- race watcher job: `58080636`
- watcher log: `logs/SRRv3M8MyOPSRace_58080628_58080627.log`

## Current Evidence

`squeue -j 58080627,58080628,58080636` showed:

- `58080628_0`: `RUNNING` on `htzhulab`, node `g1807htzh01`
- `58080628_1`: `RUNNING` on `htzhulab`, node `g1807htzh01`
- `58080628_[2]`: `PENDING (Resources)` on `htzhulab`
- `58080627`: absent from current `squeue` after watcher cancellation
- `58080636`: absent from current `squeue` after watcher completion

`sacct -j 58080627,58080628,58080636` showed:

- `58080627_[0-2]`: `CANCELLED by 397557`, partition `a100-gpu`, end `2026-07-07T00:10:33`
- `58080628_0`: `RUNNING`, partition `htzhulab`, start `2026-07-07T00:10:12`
- `58080628_1`: `RUNNING`, partition `htzhulab`, start `2026-07-07T00:10:12`
- `58080628_[2]`: `PENDING`
- `58080636`: `COMPLETED`, partition `spill`, elapsed `00:00:05`

Watcher log excerpt:

```text
2026-07-07T00:10:32.984597 watch_start htzhulab=58080628 a100=58080627
2026-07-07T00:10:33.043613 check=1 htzhulab=[('58080628_[2]', 'htzhulab', 'PENDING', '(Resources)'), ('58080628_1', 'htzhulab', 'RUNNING', 'g1807htzh01'), ('58080628_0', 'htzhulab', 'RUNNING', 'g1807htzh01')] a100=[('58080627_[0-2]', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T00:10:33.066950 cancel_a100 code=0 output=
```

## Lock Evidence

Runtime locks currently exist for:

- `m8_full_srr_context_arbitration_longrun`: claimed by job `58080629`, task `0`, partition `htzhulab`
- `m8_scar_precision_edema_safe_longrun`: claimed by job `58080630`, task `1`, partition `htzhulab`

The third variant has not started yet and remains monitor evidence only.

## Completion Boundary

This is not M8 completion. Training is still running/pending, the 28800-second MyoPS training budget is not proven, and no completed runtime aggregation has been committed.
