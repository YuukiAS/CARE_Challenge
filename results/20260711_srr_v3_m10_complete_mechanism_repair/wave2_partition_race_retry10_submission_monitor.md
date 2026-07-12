# M10 Wave 2 Retry10 Submission Monitor

Checkpoint time: `2026-07-12T23:02:30Z`

This is a monitor packet for the same active M10 goal and the same `m10_myops_training_executor`. It records a same-scope operational retry after retry9 D1 exited before the declared D1 optimizer-step and validation-event floors.

## Retry9 Terminal Accounting

Retry9 D1 `58732391` reached Slurm `COMPLETED 0:0`, but it is not adequate D1 completion evidence:

| Field | Observed | Required |
| --- | ---: | ---: |
| optimizer steps | `13600` | `25000` |
| train-loop seconds | `10805.073559065` | `9000` |
| validation events | `9` | `15` |
| eval cases | `44` | `44` |

The D1 summary records `stop_reason=max_runtime_seconds`, `max_steps=25000`, and `max_runtime_seconds=10800.0`. Because this undertrained D1 cannot satisfy the blocking Wave 2 contract, downstream retry9 jobs were cancelled:

```text
58732393 D2 hierarchical PSIP: CANCELLED
58732395 D3 full memory PropRef: CANCELLED
58732397 hard-negative refresh: CANCELLED
58732399 no-context control: CANCELLED
58732400 alignment control: CANCELLED
```

Retry9 finalizer `58733769` reached `FAILED 1:0` and wrote `finalizer_state.json`; it classified the attempt fail-closed. The authoritative current controller interpretation is `SCIENTIFIC_UNDERTRAINED` for retry9 D1, not valid training credit for the M10 minimum-effective budget.

## Same-Scope Runtime-Cap Repair

The controller applied an operational repair in owned Wave 2 entrypoint `scripts/training/run_srr_v3_m10_complete_repair.py`: default `max_runtime_seconds` is now `28500.0`, still below the 8-hour Slurm walltime, so original per-phase `max_steps`, validation-event floors, split, variants, formulas, case set, evaluation rules, result paths, executor count, and wave graph are unchanged.

`--print-contract` for D1 now reports:

```text
max_runtime_seconds=28500.0
max_steps=25000
min_train_loop_seconds_for_plateau=9000.0
val_every=1666
```

Fingerprints for retry10:

| Artifact | SHA256 |
| --- | --- |
| `scripts/training/run_srr_v3_m10_complete_repair.py` | `7bf2371cb281c92045ef5ab29b82feef1c9f49ee3fa7df97284be2bbad2529ea` |
| `configs/srr_v3_m10_complete_repair.yaml` | `df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b` |
| `data/benchmarks/protocol/splits_MyoPS.json` | `6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b` |

## Retry10 Submission

Compute preflight `58743253` completed `0:0` on `htzhulab/gpu_access_patron` with `mem=1200G`. The replacement chain keeps D0 `58706293` as the retained valid D0 evidence and replaces D1-through-alignment:

| Phase | Retry10 job | Dependency | Current state |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | retained | `COMPLETED 0:0` |
| D1 spatial BR2 | `58743282` | `afterok:58743253` | `RUNNING` |
| D2 hierarchical PSIP | `58743287` | `afterok:58743282` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58743290` | `afterok:58743287` | `PENDING (Dependency)` |
| Hard-negative refresh | `58743292` | `afterok:58743290` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58743294` | `afterok:58743292` | `PENDING (Dependency)` |
| Alignment control | `58743295` | `afterok:58743294` | `PENDING (Dependency)` |
| Finalizer | `58743452` | `afterany` over all old and retry10 jobs | `PENDING (Dependency)` |

Submission receipts:

```text
wave2_partition_race_retry10_submission.json
wave2_partition_race_retry10_job_ledger.csv
wave2_partition_race_retry10_finalizer_submission.json
```

## Decision

Current state is `NEEDS_MONITOR`, not complete and not reviewable. Wave 3 remains blocked until retry10 D1-through-alignment reaches terminal successful accounting and Wave 2 post-job aggregation succeeds.
