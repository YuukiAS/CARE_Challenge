# M10 Wave 2 Retry6 Terminal OOM

Checkpoint time: `2026-07-12T17:10:37Z`

Retry6 is terminal and unsuccessful. This is not a completion packet and not a normal review request.

| Phase | Job ID | Terminal state | Credit |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` | valid D0 runtime evidence |
| D1 spatial BR2 | `58714634` | `OUT_OF_MEMORY 0:125` after `00:12:46` | zero effective D1 credit |
| D2 hierarchical PSIP | `58714635` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| D3 full memory PropRef | `58714636` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Hard-negative refresh | `58714637` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| No-nnU-Net-context control | `58714638` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Alignment control | `58714639` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Finalizer | `58714640` | `FAILED 2:0` | finalizer argument-format failure; local replay performed |

Slurm memory accounting for D1 records `ReqMem=96G` and batch `MaxRSS=100661736K`. The failure is an operational resource request failure. It does not count toward the M10 minimum-effective-training budget for D1-through-alignment.

The retry6 finalizer failed because `--aggregation-command` was submitted as split argv. The controller replayed finalization locally and wrote `wave2_partition_race_retry6_finalization.json`:

```text
status: NEEDS_EVIDENCE
winner_reason: no_completed_chain
d1_spatial_br2: OUT_OF_MEMORY(0:125)
```

Wave 3 remains blocked.
