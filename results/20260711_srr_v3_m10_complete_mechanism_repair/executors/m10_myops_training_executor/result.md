# M10 Wave 2 MyoPS Training Executor Result

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Executor: `m10_myops_training_executor`

Status: `NEEDS_MONITOR`

## Current Retry11 State

As of `2026-07-13T08:42:03Z`, retry11 D1 `58775065` is `COMPLETED 0:0` on `htzhulab` after `02:35:16`; retry11 D2 `58775066` is `RUNNING` on `htzhulab`; retry11 D3-through-alignment jobs `58775067`-`58775070` are dependency-pending via `afterok`; retry11 finalizer `58775071` is dependency-pending via `afterany`.

Retry11 follows a same-scope owned-wrapper repair for the retry10 D1 memory-growth failure. The repair only changes gate-usage evidence logging in `scripts/training/run_srr_v3_m10_complete_repair.py`, summarizing spatial gate tensors to per-slot means before writing `retrieval_usage.csv`. It does not change variants, formulas, budgets, split, case set, evaluation rules, checkpoint-selection rules, result paths, executor count, or wave graph.

Preflight accounting: htzhulab `58775059 COMPLETED 0:0`; a100 `58775057 CANCELLED` while pending and unused; volta `58775058 FAILED 1:0` because the current PyTorch CUDA build cannot execute kernels on V100. No formal a100 or volta training job was submitted.

D1 completion evidence: `actual_optimizer_steps=31778`, `train_loop_seconds=9000.150148481014`, `validation_event_count=19`, `eval_cases=44`, `stop_reason=max_steps_min_train_loop_seconds_satisfied`, and one-batch overfit `PASS`. The repaired `retrieval_usage.csv` is `10820647` bytes and `86497` lines including header, not the retry10-scale `156G` expansion. D2 has only early sanity files at this checkpoint and has not yet produced final runtime outputs.

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

Formal controller monitor later found all seven jobs terminal `FAILED` with exit code `1:0`.

| Phase | Job ID | Terminal state | Exit code | Log |
| --- | ---: | --- | --- | --- |
| D0 static matched control | 58644072 | `FAILED` | `1:0` | `logs/M10D0MyoPS_58644072_20260711_110852.log` |
| D1 spatial BR2 | 58644073 | `FAILED` | `1:0` | `logs/M10D1MyoPS_58644073_20260711_112003.log` |
| D2 hierarchical PSIP | 58644074 | `FAILED` | `1:0` | `logs/M10D2MyoPS_58644074_20260711_112103.log` |
| D3 full memory PropRef | 58644106 | `FAILED` | `1:0` | `logs/M10D3MyoPS_58644106_20260711_112204.log` |
| Hard-negative refresh | 58644107 | `FAILED` | `1:0` | `logs/M10HardNeg_58644107_20260711_112305.log` |
| No-nnU-Net-context control | 58644108 | `FAILED` | `1:0` | `logs/M10NoCtx_58644108_20260711_112406.log` |
| Alignment control | 58644109 | `FAILED` | `1:0` | `logs/M10Align_58644109_20260711_112450.log` |

All logs share the same startup dependency failure: `sympy` requires `mpmath`, but `mpmath` was absent from `env_CARE` during the jobs. This packet is not ready for controller merge.

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

These files now record submitted job IDs, terminal Slurm failure states, exit codes, log paths, and missing runtime artifacts. They are fail-closed evidence-gap packets, not completion evidence.

## External Compatibility Observation

The carried-forward compatibility issue in `scripts/training/run_srr_propref_myops_fold0.py` remains outside this executor's write scope per the user boundary. This wave 2 implementation did not edit that file. If an M10-owned job later fails specifically because the imported legacy function cannot run M10 variants, the controller should treat that as `NEEDS_REVISION` or `NEEDS_REVISION_RETURN_TO_WAVE1` depending on whether the blocker is wrapper-side or frozen shared architecture/loss wiring.
