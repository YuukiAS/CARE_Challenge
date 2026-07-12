# M10 Wave 2 Retry4 Terminal D1 Failure

Checkpoint time: `2026-07-12T16:24:12Z`

State: `NEEDS_EVIDENCE`

## Slurm Accounting

| Phase | Job ID | State | Exit | Elapsed | Credit |
| --- | ---: | --- | --- | --- | --- |
| `d0_control` | `58706293` | `COMPLETED` | `0:0` | `02:09:10` | valid D0 runtime evidence |
| `d1_spatial_br2` | `58706294` | `FAILED` | `1:0` | `00:00:58` | zero effective D1 credit |
| `d2_hierarchical_psip` | `58706295` | `CANCELLED` | `0:0` | `00:00:00` | zero credit |
| `d3_full_propref` | `58706296` | `CANCELLED` | `0:0` | `00:00:00` | zero credit |
| `hard_negative_refresh` | `58706297` | `CANCELLED` | `0:0` | `00:00:00` | zero credit |
| `no_context_control` | `58706298` | `CANCELLED` | `0:0` | `00:00:00` | zero credit |
| `alignment_control` | `58706299` | `CANCELLED` | `0:0` | `00:00:00` | zero credit |
| finalizer | `58706300` | `FAILED` | `1:0` | `00:00:05` | fail-closed accounting |

Local retry4 finalization replay wrote `wave2_partition_race_retry4_finalization.json` and exited `2`. It records `status: NEEDS_EVIDENCE`, `winner_reason: no_completed_chain`, D0 `COMPLETED(0:0)`, D1 `FAILED(1:0)`, and D2-through-alignment `CANCELLED(0:0)`.

## Evidence

D0 completed and produced formal runtime evidence under:

`results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry4/htzhulab/variants/m10_d0_static_matched_formal/`

Key D0 files include:

- `summary.json`
- `training_log.csv`
- `validation_events.csv`
- `checkpoint_best.pt`
- `checkpoint_final.pt`
- `retrieval_usage.csv`
- `loss_component_gradient_sanity.csv`
- `prediction_sanity_checkpoint_best.csv`
- `prediction_sanity_checkpoint_final.csv`

D0 `summary.json` records `actual_optimizer_steps=36746`, `elapsed_seconds=7200.021336678998`, and `eval_cases=44`.

D1 failed after one-batch sanity passed. The D1 log is:

`logs/M10D1MyoPS_58706294_20260712_121728.log`

Failure:

```text
TypeError: float() argument must be a string or a real number, not 'list'
```

## Repair

The controller changed only:

`scripts/training/run_srr_v3_m10_complete_repair.py`

The repair monkeypatches the imported legacy `record_gate_usage` function in the M10 wrapper so nested/list gate usage from M10 spatial routers is flattened into scalar CSV rows. This preserves training semantics and only changes logging compatibility.

Repair fingerprints:

| Artifact | SHA256 |
| --- | --- |
| `scripts/training/run_srr_v3_m10_complete_repair.py` | `bf132c6f6c1649c2a98bbe16af3ffe7cd67f436f035431a6b3376e4917203ad3` |
| `configs/srr_v3_m10_complete_repair.yaml` | `df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b` |
| `data/benchmarks/protocol/splits_MyoPS.json` | `6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b` |

Wave 2 remains incomplete. Wave 3 remains blocked. No `review.md` was written and no push was performed.
