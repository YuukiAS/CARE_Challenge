# M10 Wave 2 Retry4 Monitor

Checkpoint time: `2026-07-12T14:11:10Z`

State: `NEEDS_MONITOR`

Retry4 is the same `m10_myops_training_executor` Wave 2 replacement attempt after the owned-wrapper metric-compatibility repair in `scripts/training/run_srr_v3_m10_complete_repair.py`. It does not change variants, formulas, budgets, split, case set, evaluation rules, checkpoint-selection rules, result paths, executor count, or wave graph.

## Preflight

| Job ID | Partition | State | Exit | Elapsed | Notes |
| ---: | --- | --- | --- | --- | --- |
| `58706079` | `htzhulab` | `COMPLETED` | `0:0` | `00:00:22` | successful repaired-code compute-node preflight |
| `58706080` | `a100-gpu` | `CANCELLED by 397557` | `0:0` | `00:00:00` | pending mirror cancelled after htz preflight succeeded |

## Formal Chain

| Phase | Job ID | Partition | State | Runtime root |
| --- | ---: | --- | --- | --- |
| `d0_control` | `58706293` | `htzhulab` | `RUNNING` | `results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry4/htzhulab` |
| `d1_spatial_br2` | `58706294` | `htzhulab` | `PENDING (Dependency)` | same |
| `d2_hierarchical_psip` | `58706295` | `htzhulab` | `PENDING (Dependency)` | same |
| `d3_full_propref` | `58706296` | `htzhulab` | `PENDING (Dependency)` | same |
| `hard_negative_refresh` | `58706297` | `htzhulab` | `PENDING (Dependency)` | same |
| `no_context_control` | `58706298` | `htzhulab` | `PENDING (Dependency)` | same |
| `alignment_control` | `58706299` | `htzhulab` | `PENDING (Dependency)` | same |

Finalizer job `58706300` is `PENDING (Dependency)` with `afterany` over old failed jobs, superseded/cancelled attempts, preflights, and the retry4 formal chain.

## Runtime Evidence

Early D0 runtime files exist under the retry4 htz runtime root:

- `contracts/d0_control_m10_phase_contract.json`
- `variants/m10_d0_static_matched_formal/one_batch_overfit.csv`
- `variants/m10_d0_static_matched_formal/one_batch_overfit.json`
- `variants/m10_d0_static_matched_formal/prototype_update_sanity.csv`
- `variants/m10_d0_static_matched_formal/prototype_bank_summary.json`

This is not completion evidence. Wave 2 remains in monitor state until terminal Slurm accounting and post-job aggregation complete.
