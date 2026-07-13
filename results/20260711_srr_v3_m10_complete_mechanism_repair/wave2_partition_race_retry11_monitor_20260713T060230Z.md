# M10 Wave 2 Retry11 Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Repair Basis

Retry10 D1 `58743282` reached terminal `OUT_OF_MEMORY(0:125)` after `06:09:20`. Runtime evidence showed memory growth consistent with gate-usage evidence logging expansion: the D1 `retrieval_usage.csv` reached `156G`, while `training_log.csv` was only `410K`.

The retry11 repair is scoped to the owned Wave 2 training wrapper only:

```text
scripts/training/run_srr_v3_m10_complete_repair.py
```

The repair summarizes gate-usage tensors to per-slot means over batch and spatial dimensions before appending evidence rows. It does not change variants, model formulas, training budgets, split, case set, evaluation rules, checkpoint-selection rules, result paths, executor count, or wave graph.

Local checks:

```text
py_compile: PASS
spatial gate smoke: PASS, 2x16x4x5x6 gate -> 16 evidence rows
```

## Preflight Accounting

| Partition | Preflight job | State | Decision |
| --- | ---: | --- | --- |
| `htzhulab` | `58775059` | `COMPLETED 0:0` | used for formal retry11 |
| `a100-gpu` | `58775057` | `CANCELLED` while pending | not used; no formal a100 job submitted |
| `volta-gpu` | `58775058` | `FAILED 1:0` | not used; CUDA kernel probe failed on V100 with current PyTorch build |

## Formal Retry11 Jobs

| Phase | Job ID | Dependency | State at submission check |
| --- | ---: | --- | --- |
| D1 spatial BR2 | `58775065` | `afterok:58775059` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58775066` | `afterok:58775065` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58775067` | `afterok:58775066` | `PENDING (Dependency)` |
| hard-negative refresh | `58775068` | `afterok:58775067` | `PENDING (Dependency)` |
| no-nnU-Net-context control | `58775069` | `afterok:58775068` | `PENDING (Dependency)` |
| alignment control | `58775070` | `afterok:58775069` | `PENDING (Dependency)` |
| Wave 2 finalizer | `58775071` | `afterany` over old and retry11 jobs | `PENDING (Dependency)` |

Runtime root:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry11/htzhulab
```

Fingerprints:

```text
code_hash=c1d8124dd0e3d0407cfa0fca1e6ea310121e00a4ece290c4b0dc19cf638dd1a3
config_hash=df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b
split_hash=6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b
```

## Decision

Current state is `NEEDS_MONITOR`, not complete and not reviewable. Retry10 remains terminal unsuccessful with zero D1-through-alignment credit. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until retry11 reaches terminal accounting and post-job aggregation succeeds.
