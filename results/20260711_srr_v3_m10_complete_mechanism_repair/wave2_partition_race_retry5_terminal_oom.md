# M10 Wave 2 Retry5 Terminal OOM

Checkpoint time: `2026-07-12T16:47:36Z`

Retry5 is terminal and unsuccessful. This is not a completion packet and not a normal review request.

| Phase | Job ID | Terminal state | Credit |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` | valid D0 runtime evidence |
| D1 spatial BR2 | `58714023` | `OUT_OF_MEMORY 0:125` after `00:07:50` | zero effective D1 credit |
| D2 hierarchical PSIP | `58714024` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| D3 full memory PropRef | `58714025` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Hard-negative refresh | `58714026` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| No-nnU-Net-context control | `58714027` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Alignment control | `58714028` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Finalizer | `58714029` | `FAILED 1:0` | fail-closed accounting |

Slurm memory accounting for D1 records `ReqMem=64G` and batch `MaxRSS=67107264K`. The failure is an operational resource request failure. It does not count toward the M10 minimum-effective-training budget for D1-through-alignment.

The retry5 finalization replay wrote `wave2_partition_race_retry5_finalization.json`:

```text
status: NEEDS_EVIDENCE
winner_reason: no_completed_chain
d1_spatial_br2: OUT_OF_MEMORY(0:125)
```

Wave 3 remains blocked.
