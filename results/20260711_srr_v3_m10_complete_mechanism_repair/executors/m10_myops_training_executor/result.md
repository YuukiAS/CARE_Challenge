# M10 Wave 2 MyoPS Training Executor Result

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Executor: `m10_myops_training_executor`

Status: `NEEDS_MONITOR`

## Dependency Gate

Wave 1 dependency passed before wave 2 work:

- `results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/completion_check.md` contains `READY_FOR_CONTROLLER_MERGE`.
- `results/20260711_srr_v3_m10_complete_mechanism_repair/wave1_merge_receipt.md` accepts wave 1 with `WAVE1_READY_FOR_CONTROLLER_MERGE_ACCEPTED`.

Wave 1 shared architecture remains frozen. No shared model, loss, Cine, wiki, prompt, review, validation packaging, upload, hosted metric, route-promotion, scientific-stop, M11, commit, or push action was performed.

## Implemented Entry Points

Created M10-owned wave 2 entrypoints:

- `scripts/training/run_srr_v3_m10_complete_repair.py`
- `scripts/evaluation/evaluate_srr_v3_m10_full_case.py`
- `scripts/evaluation/aggregate_srr_v3_m10_myops.py`

Created seven `htzhulab` Slurm wrappers with `--time=08:00:00`, `--partition=htzhulab`, and `--qos=gpu_access`:

- `jobs/src/run_srr_v3_m10_myops_d0_control.sh`
- `jobs/src/run_srr_v3_m10_myops_d1_spatial_br2.sh`
- `jobs/src/run_srr_v3_m10_myops_d2_hierarchical_psip.sh`
- `jobs/src/run_srr_v3_m10_myops_d3_full_propref.sh`
- `jobs/src/run_srr_v3_m10_hard_negative_refresh.sh`
- `jobs/src/run_srr_v3_m10_no_context_control.sh`
- `jobs/src/run_srr_v3_m10_alignment_control.sh`

The training wrapper imports the legacy fold0 training function with a constructed M10 namespace because the legacy CLI does not accept M10 variant names. The legacy script was not edited.

## Submitted Jobs

Submitted as a serial `afterany` dependency chain to preserve `max_parallel: 1`:

| Phase | Job ID | Dependency | State at packet write |
| --- | ---: | --- | --- |
| D0 static matched control | 58644072 | none | `PENDING (Resources)` |
| D1 spatial BR2 | 58644073 | `afterany:58644072` | `PENDING (Dependency)` |
| D2 hierarchical PSIP | 58644074 | `afterany:58644073` | `PENDING (Dependency)` |
| D3 full memory PropRef | 58644106 | `afterany:58644074` | `PENDING (Dependency)` |
| Hard-negative refresh | 58644107 | `afterany:58644106` | `PENDING (Dependency)` |
| No-nnU-Net-context control | 58644108 | `afterany:58644107` | `PENDING (Dependency)` |
| Alignment control | 58644109 | `afterany:58644108` | `PENDING (Dependency)` |

Because all jobs are pending and no post-job aggregation has terminal runtime evidence, this packet is not ready for controller merge.

## Output State

Monitor-mode lightweight files were generated under:

- `results/20260711_srr_v3_m10_myops_d0_control/`
- `results/20260711_srr_v3_m10_myops_d1_spatial_br2/`
- `results/20260711_srr_v3_m10_myops_d2_hierarchical_psip/`
- `results/20260711_srr_v3_m10_myops_d3_full_propref/`
- `results/20260711_srr_v3_m10_hard_negative_refresh/`
- `results/20260711_srr_v3_m10_no_nnunet_context_control/`
- `results/20260711_srr_v3_m10_alignment_control/`
- `results/20260711_srr_v3_m10_component_causal_audit/`

These files record submitted job IDs and missing terminal runtime artifacts. They are monitor packets, not completion evidence.

## External Compatibility Observation

The carried-forward compatibility issue in `scripts/training/run_srr_propref_myops_fold0.py` remains outside this executor's write scope per the user boundary. This wave 2 implementation did not edit that file. If an M10-owned job later fails specifically because the imported legacy function cannot run M10 variants, the controller should treat that as `NEEDS_REVISION` or `NEEDS_REVISION_RETURN_TO_WAVE1` depending on whether the blocker is wrapper-side or frozen shared architecture/loss wiring.
