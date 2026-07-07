# M8 Cine Slurm Status

status: `M8_NEEDS_MONITOR_NO_REVIEW`

## Submission

Mandatory M8 Cine mature registration was first submitted to the default CARE lab partition with:

```bash
sbatch jobs/src/run_srr_v3_m8_cine_registration_mature_htzhulab.sh
```

Submitted job id: `58081208`.

That job was still `PENDING (Priority)` and had been submitted before the Cine entrypoints had an atomic routing lock, so it was cancelled before any start evidence:

```bash
scancel 58081208
```

The Cine entrypoints now use the shared lock `results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/runtime/routing_locks/cine_registration_mature.lock`. The lock-safe race was submitted as:

- htzhulab mirror: `58081476`
- a100-gpu mirror: `58081477`
- watcher job: `58081479`
- watcher log: `logs/SRRv3M8CineRace_58081476_58081477.log`

The job script runs:

```bash
python scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py \
  --max-cases 12 \
  --pairs-per-case 3 \
  --demons-iterations 40 \
  --antspy-iterations 25
```

and copies the mature-registration outputs into the M8 result filenames when successful.

## Current Scheduler Evidence

`squeue -j 58081007,58081476,58081477,58081479,58081494,58081496` showed:

- `58081476`: `PENDING`, partition `htzhulab`, reason `(Priority)`
- `58081477`: `PENDING`, partition `a100-gpu`, reason `(Priority)`
- `58081479`: `RUNNING`, partition `spill`
- `58081007_0`: `RUNNING`, partition `htzhulab`
- `58081007_1`: `RUNNING`, partition `htzhulab`
- `58081007_[2]`: `PENDING`, partition `htzhulab`, reason `(Resources)`
- `58081494_[2]`: `PENDING`, partition `a100-gpu`, reason `(Priority)`
- `58081496`: `RUNNING`, partition `spill`

`sacct -j 58081007,58081476,58081477,58081479,58081494,58081496` showed:

- `58081476|SRRv3M8CineReg|htzhulab|PENDING`
- `58081477|SRRv3M8CineReg|a100-gpu|PENDING`
- `58081479|SRRv3M8CineWatch|spill|RUNNING`

Watcher log excerpt:

```text
2026-07-07T00:34:39.878790 watch_start htzhulab=58081476 a100=58081477
2026-07-07T00:34:39.927064 check=1 htzhulab=[('58081476', 'htzhulab', 'PENDING', '(Priority)')] a100=[('58081477', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T00:36:39.992282 check=2 htzhulab=[('58081476', 'htzhulab', 'PENDING', '(Priority)')] a100=[('58081477', 'a100-gpu', 'PENDING', '(Priority)')]
```

## Latest Check After Aggregator Installation

`squeue -j 58081007,58081476,58081477,58081479,58081494,58081496` showed:

- `58081476`: `PENDING`, partition `htzhulab`, reason `(Priority)`
- `58081477`: `PENDING`, partition `a100-gpu`, reason `(Priority)`
- `58081479`: `RUNNING`, partition `spill`

`sacct -j 58081007,58081476,58081477,58081479,58081494,58081496` showed:

- `58081476`: `PENDING`, partition `htzhulab`, start `Unknown`
- `58081477`: `PENDING`, partition `a100-gpu`, start `Unknown`
- `58081479`: `RUNNING`, partition `spill`, elapsed `00:34:01`, start `2026-07-07T00:34:39`

Cine watcher latest excerpt:

```text
2026-07-07T00:54:41.081725 check=11 htzhulab=[('58081476', 'htzhulab', 'PENDING', '(Priority)')] a100=[('58081477', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T00:56:41.142459 check=12 htzhulab=[('58081476', 'htzhulab', 'PENDING', '(Priority)')] a100=[('58081477', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T00:58:41.409066 check=13 htzhulab=[('58081476', 'htzhulab', 'PENDING', '(Priority)')] a100=[('58081477', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T01:00:41.473848 check=14 htzhulab=[('58081476', 'htzhulab', 'PENDING', '(Priority)')] a100=[('58081477', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T01:02:41.535571 check=15 htzhulab=[('58081476', 'htzhulab', 'PENDING', '(Priority)')] a100=[('58081477', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T01:04:41.608644 check=16 htzhulab=[('58081476', 'htzhulab', 'PENDING', '(Priority)')] a100=[('58081477', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T01:06:41.671198 check=17 htzhulab=[('58081476', 'htzhulab', 'PENDING', '(Priority)')] a100=[('58081477', 'a100-gpu', 'PENDING', '(Priority)')]
```

No Cine registration matrix or temporal dictionary evidence has been produced from this race yet.

## Completion Boundary

This is not Cine evidence completion. Mature registration has been submitted in a lock-safe partition race but has not started/completed, and no M8 Cine registration matrix or temporal dictionary aggregation has been produced from the submitted job.
