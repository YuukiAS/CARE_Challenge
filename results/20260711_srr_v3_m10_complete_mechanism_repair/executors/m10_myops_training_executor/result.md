# M10 Wave 2 MyoPS Training Executor Result

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Executor: `m10_myops_training_executor`

Status: `READY_FOR_CONTROLLER_MERGE`

## Scope Boundary

This is the same active M10 goal and the same `m10_myops_training_executor`. No new milestone, executor, scientific design, variant definition, model formula, split, case set, budget, evaluation rule, checkpoint-selection rule, result path, executor count, or wave graph was introduced.

No `review.md` was written. No push, validation packaging, validation upload, hosted metric claim, route promotion, route-negative conclusion, scientific stop, Wave 3 execution, or M11 action is claimed here.

## Terminal Accounting

The original Wave 2 jobs remain permanently recorded as `STARTUP_FAILED` with zero training credit, zero optimizer-step credit, and zero train-loop-second credit:

```text
58644072
58644073
58644074
58644106
58644107
58644108
58644109
```

The effective Wave 2 formal evidence consists of retained D0 job `58706293` plus retry11 jobs `58775065` through `58775070`.

| Phase | Job ID | State | Optimizer steps | Train-loop seconds | Status |
| --- | ---: | --- | ---: | ---: | --- |
| D0 static matched control | `58706293` | `COMPLETED 0:0` | `36746` | `7200.021336678998` | `TERMINAL_RUNTIME_EVIDENCE` |
| D1 spatial BR2 | `58775065` | `COMPLETED 0:0` | `31778` | `9000.150148481014` | `TERMINAL_RUNTIME_EVIDENCE` |
| D2 hierarchical PSIP | `58775066` | `COMPLETED 0:0` | `31810` | `9000.034213767038` | `TERMINAL_RUNTIME_EVIDENCE` |
| D3 full memory PropRef | `58775067` | `COMPLETED 0:0` | `50820` | `14400.138177286019` | `TERMINAL_RUNTIME_EVIDENCE` |
| Hard-negative refresh | `58775068` | `COMPLETED 0:0` | `20000` | `5684.537394266925` | `TERMINAL_RUNTIME_EVIDENCE` |
| No-nnU-Net-context control | `58775069` | `COMPLETED 0:0` | `20000` | `5488.0439176289365` | `TERMINAL_RUNTIME_EVIDENCE` |
| Pair-valid alignment control | `58775070` | `COMPLETED 0:0` | `12501` | `3600.2238130120095` | `TERMINAL_RUNTIME_EVIDENCE` |

## Aggregation Evidence

Wave 2 finalizer job `58775071` correctly ran after all old and replacement jobs, but the generic finalizer initially marked `RUNTIME_FAILURE` because it treated superseded historical `OUT_OF_MEMORY`/`CANCELLED` attempts as current formal failures. The controller corrected terminal accounting in the same finalizer scope by rerunning accounting over the current effective formal chain while recording the superseded job IDs in `finalizer_state.json`.

The successful aggregation evidence is:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/finalizer_state.json
results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_partition_race_retry11_finalization.json
results/20260711_srr_v3_m10_myops_d0_control/runtime_manifest.json
results/20260711_srr_v3_m10_myops_d1_spatial_br2/runtime_manifest.json
results/20260711_srr_v3_m10_myops_d2_hierarchical_psip/runtime_manifest.json
results/20260711_srr_v3_m10_myops_d3_full_propref/runtime_manifest.json
results/20260711_srr_v3_m10_hard_negative_refresh/runtime_manifest.json
results/20260711_srr_v3_m10_no_nnunet_context_control/runtime_manifest.json
results/20260711_srr_v3_m10_alignment_control/runtime_manifest.json
results/20260711_srr_v3_m10_component_causal_audit/runtime_manifest.json
```

`finalizer_state.json` records `final_state: READY_FOR_MAPPER_FINAL` and `aggregation_exit_code: 0`. `wave2_partition_race_retry11_finalization.json` records `status: TERMINAL_RUNTIME_EVIDENCE`.

## Result Directories

The phase result directories have been regenerated from runtime outputs:

```text
results/20260711_srr_v3_m10_myops_d0_control/
results/20260711_srr_v3_m10_myops_d1_spatial_br2/
results/20260711_srr_v3_m10_myops_d2_hierarchical_psip/
results/20260711_srr_v3_m10_myops_d3_full_propref/
results/20260711_srr_v3_m10_hard_negative_refresh/
results/20260711_srr_v3_m10_no_nnunet_context_control/
results/20260711_srr_v3_m10_alignment_control/
results/20260711_srr_v3_m10_component_causal_audit/
```

Each formal phase reports `TERMINAL_RUNTIME_EVIDENCE`; component causal audit also reports `TERMINAL_RUNTIME_EVIDENCE`.

## Next State

Wave 2 is ready for controller merge. Wave 3 may begin only after the controller records the Wave 2 merge receipt and re-grounds the original `m10_cine_temporal_executor` contract.
