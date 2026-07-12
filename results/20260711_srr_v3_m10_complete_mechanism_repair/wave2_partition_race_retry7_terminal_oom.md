# M10 Wave 2 Retry7 Terminal OOM

Checkpoint time: `2026-07-12T17:44:44Z`

Retry7 is terminal and unsuccessful. This is not a completion packet and not a normal review request.

| Phase | Job ID | Terminal state | Credit |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` | valid D0 runtime evidence |
| D1 spatial BR2 | `58719835` | `OUT_OF_MEMORY 0:125` after `00:18:06` | zero effective D1 credit |
| D2 hierarchical PSIP | `58719836` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| D3 full memory PropRef | `58719837` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Hard-negative refresh | `58719838` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| No-nnU-Net-context control | `58719839` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Alignment control | `58719840` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Finalizer | `58719841` | `FAILED 1:0` | fail-closed accounting |

Slurm memory accounting for D1 records `ReqMem=128G` and batch `MaxRSS=134216104K`. The failure is an operational resource request failure. It does not count toward the M10 minimum-effective-training budget for D1-through-alignment.

The retry7 finalization replay wrote `wave2_partition_race_retry7_finalization.json`:

```text
status: NEEDS_EVIDENCE
winner_reason: no_completed_chain
d1_spatial_br2: OUT_OF_MEMORY(0:125)
```

Wave 3 remains blocked.
