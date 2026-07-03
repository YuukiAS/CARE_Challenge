# Provenance Reconciliation

self_assessed_status: EXECUTED_UNAUDITED
route_decision: STOP_NO_PROPREF_SIGNAL

## Scope

This supplement addresses the first audit's `NEEDS_EVIDENCE` findings for run provenance and schedule wording only. It does not train, upload, package validation, expand folds, change label mappings, change fold splits, change the evaluator, commit, push, or audit the result.

## Authoritative Variant Mapping

The canonical Slurm evidence is the array accounting record for job array `57617442`. The variant mapping comes from `jobs/src/run_srr_propref_myops_fold0.sh`, where `SLURM_ARRAY_TASK_ID` indexes:

| array task id | variant | canonical Slurm job id | sacct state | exit code | elapsed | node |
| ---: | --- | --- | --- | --- | ---: | --- |
| 0 | `srr_propref_shared_dual_dict` | `57617442_0` | `COMPLETED` | `0:0` | `01:01:49` | `g1807htzh01` |
| 1 | `srr_propref_scar_precision` | `57617442_1` | `COMPLETED` | `0:0` | `00:39:37` | `g1807htzh01` |
| 2 | `srr_propref_no_proto_cascade` | `57617442_2` | `COMPLETED` | `0:0` | `00:32:28` | `g180702` |

Current accounting command used for this supplement:

```bash
sacct -j 57617442 --format=JobID,JobName%30,Partition,State,ExitCode,Elapsed,Start,End,NodeList --parsable2
```

Relevant output:

```text
57617442_0|SRRPropRefF0|htzhulab|COMPLETED|0:0|01:01:49|2026-07-03T04:03:42|2026-07-03T05:05:31|g1807htzh01
57617442_1|SRRPropRefF0|htzhulab|COMPLETED|0:0|00:39:37|2026-07-03T04:03:43|2026-07-03T04:43:20|g1807htzh01
57617442_2|SRRPropRefF0|htzhulab|COMPLETED|0:0|00:32:28|2026-07-03T04:03:43|2026-07-03T04:36:11|g180702
```

## `run_config.env` Job ID Mismatch

The per-variant `run_config.env` files record `job_id=${SLURM_JOB_ID}` and `array_task_id=${SLURM_ARRAY_TASK_ID}`. For this Slurm array, those shell-side `SLURM_JOB_ID` values are:

| variant | array task id | `run_config.env` job_id | authoritative Slurm array id |
| --- | ---: | --- | --- |
| `srr_propref_shared_dual_dict` | 0 | `57617443` | `57617442_0` |
| `srr_propref_scar_precision` | 1 | `57617444` | `57617442_1` |
| `srr_propref_no_proto_cascade` | 2 | `57617442` | `57617442_2` |

This is a provenance-recording mismatch, not evidence of different variants or failed jobs. The script did not record `SLURM_ARRAY_JOB_ID`, so `run_config.env` preserved the shell-side per-task numeric job ID while `slurm_status.csv` and current `sacct` preserve the canonical array-element IDs. For auditing this package, use `canonical_slurm_job_id` in `variant_provenance.csv` as authoritative, with `array_task_id` and variant name as the join keys back to `run_config.env`.

## Zero-Byte Log Files

The configured log files exist but are empty:

| variant | configured log file | size | stdout/stderr status |
| --- | --- | ---: | --- |
| `srr_propref_shared_dual_dict` | `/users/a/e/aereinh/CARE/logs/SRRPropRefF0_0_57617443_20260703_040343.log` | 0 bytes | evidence not found |
| `srr_propref_scar_precision` | `/users/a/e/aereinh/CARE/logs/SRRPropRefF0_1_57617444_20260703_040343.log` | 0 bytes | evidence not found |
| `srr_propref_no_proto_cascade` | `/users/a/e/aereinh/CARE/logs/SRRPropRefF0_2_57617442_20260703_040343.log` | 0 bytes | evidence not found |

Per-variant stdout/stderr cannot be recovered from these files. The final provenance transcript therefore relies on independent surviving evidence: `sacct` completion, `run_config.env`, nonempty checkpoints, prediction counts, metric CSVs, and `summary.json`.

## Per-Variant Evidence Pointers

| variant | config | checkpoint | predictions | metric evidence | exit status |
| --- | --- | --- | --- | --- | --- |
| `srr_propref_shared_dual_dict` | `variants/srr_propref_shared_dual_dict/configs/run_config.env` | `variants/srr_propref_shared_dual_dict/checkpoints/fold_0/propref_config/checkpoint_best.pt` (3234511 bytes) | 44 files in `variants/srr_propref_shared_dual_dict/predictions/fold_0/checkpoint_best` | `proposal_metrics.csv`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `roi_coverage.csv`, `hardneg_memory.csv` | `COMPLETED`, `0:0` |
| `srr_propref_scar_precision` | `variants/srr_propref_scar_precision/configs/run_config.env` | `variants/srr_propref_scar_precision/checkpoints/fold_0/propref_config/checkpoint_best.pt` (3234511 bytes) | 44 files in `variants/srr_propref_scar_precision/predictions/fold_0/checkpoint_best` | `proposal_metrics.csv`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `roi_coverage.csv`, `hardneg_memory.csv` | `COMPLETED`, `0:0` |
| `srr_propref_no_proto_cascade` | `variants/srr_propref_no_proto_cascade/configs/run_config.env` | `variants/srr_propref_no_proto_cascade/checkpoints/fold_0/propref_config/checkpoint_best.pt` (3227247 bytes) | 44 files in `variants/srr_propref_no_proto_cascade/predictions/fold_0/checkpoint_best` | `proposal_metrics.csv`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `roi_coverage.csv`, `hardneg_memory.csv` | `COMPLETED`, `0:0` |

## Low-LR Schedule Reconciliation

`scripts/training/run_srr_propref_myops_fold0.py` implements `low_lr_calibration` in `stage_for_step()` for the final 10% of steps and lowers the optimizer LR inside that stage. The formal runs used `max_steps=120`. With this setting, the low-LR stage would occur only in the last 11 steps, but `training_log.csv` is emitted only at step 1 and every 50 steps, with validation every 300 steps. Therefore each formal `training_log.csv` records only:

- `evidence_warmup`
- `proposal_dictionary`
- `soft_roi_refinement`

No formal variant has a logged `low_lr_calibration` row. Reports for this task should say the low-LR calibration path is implemented in code but not observed as a logged training row for the formal runs. They should not claim logged low-LR calibration evidence.

## Current Status

The missing stdout/stderr evidence remains unrecoverable, but the required final provenance transcript is now represented by:

- `variant_provenance.csv`
- this `provenance_reconciliation.md`
- updated `command_transcript.md`
- updated `training_schedule.md`
- updated `result.md`
- updated `MANIFEST.md`

The route decision remains `STOP_NO_PROPREF_SIGNAL` because this supplement adds provenance and schedule evidence only; it does not contradict the metric evidence that all PropRef variants remain far below the same-split nnU-Net reference.
