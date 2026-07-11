# M10 Wave 2 Monitor Receipt

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Controller state: `NEEDS_EVIDENCE`

Worker agent: `019f515e-39d5-7631-b6a1-5e1b4756701d`

Worker completion token: `NEEDS_MONITOR`

## Original Slurm State

The wave 2 worker submitted seven serial `afterany` jobs to `htzhulab`:

| Phase | Job ID | State | Reason | Partition |
| --- | ---: | --- | --- | --- |
| D0 static matched control | 58644072 | `PENDING` | `Resources` | `htzhulab` |
| D1 spatial BR2 | 58644073 | `PENDING` | `Dependency` | `htzhulab` |
| D2 hierarchical PSIP | 58644074 | `PENDING` | `Dependency` | `htzhulab` |
| D3 full memory PropRef | 58644106 | `PENDING` | `Dependency` | `htzhulab` |
| Hard-negative refresh | 58644107 | `PENDING` | `Dependency` | `htzhulab` |
| No-nnU-Net-context control | 58644108 | `PENDING` | `Dependency` | `htzhulab` |
| Alignment control | 58644109 | `PENDING` | `Dependency` | `htzhulab` |

Controller verification command:

```text
squeue -j 58644072,58644073,58644074,58644106,58644107,58644108,58644109 -o '%i|%j|%T|%M|%D|%R|%P'
```

## Terminal Failure Update

Formal monitor at `2026-07-11T15:45:38Z` found all seven jobs terminal `FAILED` with exit code `1:0`; see `wave2_terminal_failure_receipt.md`.

The shared log failure is:

```text
ModuleNotFoundError: No module named 'mpmath'
ImportError: SymPy now depends on mpmath as an external library.
```

Fail-closed aggregation was rerun and wrote `STARTUP_FAILED_NEEDS_EVIDENCE` to the phase packets.

## Decision

This is now a terminal failure packet, not completion evidence. The controller must not launch wave 3, request independent review, package or upload validation, claim hosted metrics, claim route promotion, claim scientific stop, or start M11 until a later authorized execution produces valid wave 2 runtime evidence.

Next action: explicit authorization is required for any replacement Slurm training submission. The project-local dependency was repaired, but no replacement jobs were submitted in this packet.
