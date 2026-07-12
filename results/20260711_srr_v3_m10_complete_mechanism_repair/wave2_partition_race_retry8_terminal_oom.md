# M10 Wave 2 Retry8 Terminal OOM

Checkpoint time: `2026-07-12T18:21:31Z`

Retry8 is terminal and unsuccessful. This is not a completion packet and not a normal review request.

| Phase | Job ID | Terminal state | Credit |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` | valid D0 runtime evidence |
| D1 spatial BR2 | `58720458` | `OUT_OF_MEMORY 0:125` after `00:23:41` | zero effective D1 credit |
| D2 hierarchical PSIP | `58720459` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| D3 full memory PropRef | `58720460` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Hard-negative refresh | `58720461` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| No-nnU-Net-context control | `58720462` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Alignment control | `58720463` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Finalizer | `58720464` | `FAILED 1:0` | fail-closed accounting |

Slurm memory accounting for D1 records `ReqMem=160G`, `QOS=gpu_access_patron`, and batch `MaxRSS=167770540K`. D1 wrote early runtime artifacts, including `checkpoint_validation_step_1666.pt`, but did not write `training_log.csv`, `validation_events.csv`, `summary.json`, or full completion evidence. It therefore has zero effective D1 credit for the M10 minimum-effective-training budget.

The retry8 finalization replay wrote `wave2_partition_race_retry8_finalization.json`:

```text
status: NEEDS_EVIDENCE
winner_reason: no_completed_chain
d1_spatial_br2: OUT_OF_MEMORY(0:125)
```

The observed OOM series is now D1 `64G -> 96G -> 128G -> 160G`, with increasing runtime before OOM (`00:07:50`, `00:12:46`, `00:18:06`, `00:23:41`). This points to a memory-growth defect in the D1 runtime path rather than a scheduler or startup failure. The controller must continue in the same M10 Wave 2 scope only if the repair stays within the owned Wave 2 wrapper/evaluation/job/result write scope and does not alter variants, model formulas, training budgets, split, case set, evaluation rules, checkpoint-selection rules, result paths, executor count, or wave graph.

Wave 3 remains blocked.
