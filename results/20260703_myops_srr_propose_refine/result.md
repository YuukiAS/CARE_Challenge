# Result 20260703 MyoPS SRR ProposeRefine

self_assessed_status: EXECUTED_UNAUDITED
route_decision: STOP_NO_PROPREF_SIGNAL
role: executor
review_required: true

## Execution Summary

Implemented a first-party SRR-ProposeRefine mechanism with shared evidence trunk, scar/edema proposal dictionaries, typed negative prototype memory, soft ROI refinement heads, and a staged training runner. No validation upload, upload-ready package, fold expansion, label mapping edit, fold split edit, evaluator edit, network access, commit, or push was performed.

claim.architecture_contract: `architecture_contract.md` documents the implemented mechanism and forbidden-substitute boundary.
claim.three_stage_schedule: `training_schedule.md` records the implemented staged schedule. Per-variant `training_log.csv` files record evidence warmup, proposal dictionary learning, and soft ROI refinement; `low_lr_calibration` is implemented in code but has no logged row in the formal `max_steps=120` runs.
claim.no_t2_contract: runner loss masks dense edema supervision to T2-present samples and hard-negative replay only consumes `replay_safe=True` mined components; no-T2 myocardium/scar unsafe edema entries remain excluded.
claim.variant_evidence: `variant_matrix.md`, `metrics_summary.md`, and aggregate CSVs index per-variant checkpoints, prediction dirs, metrics, ROI coverage, and hard-negative memory where present.
claim.provenance_reconciliation: `provenance_reconciliation.md` and `variant_provenance.csv` tie each variant to array task id, canonical Slurm array job id, config, checkpoint, predictions, metric paths, and exit status; per-variant stdout/stderr logs are explicitly marked `evidence not found` because configured tee logs are zero bytes.
claim.next_state: executor stops at `EXECUTED_UNAUDITED` pending separate read-only audit.

## Formal Variant Status

| variant | checkpoint | predictions | prediction files | Slurm state | Slurm elapsed | train_loop_seconds |
| --- | --- | --- | ---: | --- | ---: | ---: |
| `srr_propref_shared_dual_dict` | `/users/a/e/aereinh/CARE/results/20260703_myops_srr_propose_refine/variants/srr_propref_shared_dual_dict/checkpoints/fold_0/propref_config/checkpoint_best.pt` | `/users/a/e/aereinh/CARE/results/20260703_myops_srr_propose_refine/variants/srr_propref_shared_dual_dict/predictions/fold_0/checkpoint_best` | 44 | `COMPLETED:0:0` | `01:01:49` | `6.052591476996895` |
| `srr_propref_scar_precision` | `/users/a/e/aereinh/CARE/results/20260703_myops_srr_propose_refine/variants/srr_propref_scar_precision/checkpoints/fold_0/propref_config/checkpoint_best.pt` | `/users/a/e/aereinh/CARE/results/20260703_myops_srr_propose_refine/variants/srr_propref_scar_precision/predictions/fold_0/checkpoint_best` | 44 | `COMPLETED:0:0` | `00:39:37` | `6.022802207997302` |
| `srr_propref_no_proto_cascade` | `/users/a/e/aereinh/CARE/results/20260703_myops_srr_propose_refine/variants/srr_propref_no_proto_cascade/checkpoints/fold_0/propref_config/checkpoint_best.pt` | `/users/a/e/aereinh/CARE/results/20260703_myops_srr_propose_refine/variants/srr_propref_no_proto_cascade/predictions/fold_0/checkpoint_best` | 44 | `COMPLETED:0:0` | `00:32:28` | `29.664764647372067` |

## Files Changed

- `src/care_myocardium/models/srr_propref.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `scripts/evaluation/aggregate_srr_propref_20260703.py`
- `jobs/src/run_srr_propref_myops_fold0.sh`
- `results/20260703_myops_srr_propose_refine/`

## Failures And Incomplete Items

- Independent audit is still required before any promotion.
- Per-variant stdout/stderr content is `evidence not found`: the configured log files exist but are zero bytes. Final provenance is reconstructed from `sacct`, `run_config.env`, checkpoint, prediction, summary, and metric evidence.
- `run_config.env` job IDs for shared/scar are shell-side per-task `SLURM_JOB_ID` values; the authoritative Slurm mapping is `57617442_0`, `57617442_1`, and `57617442_2` in `variant_provenance.csv`.
- The low-LR calibration path is implemented in code, but no formal `training_log.csv` contains a `low_lr_calibration` row under the `max_steps=120` logged schedule.
- Hosted validation metrics and upload-ready raw-label packages are `evidence not found` because they are forbidden by task scope.
- `review.md` was not written because this session is executor-only.

## Evidence Supplement Files

- `provenance_reconciliation.md`
- `variant_provenance.csv`
- updated `command_transcript.md`
- updated `training_schedule.md`
- updated `MANIFEST.md`

## Required Next State

EXECUTED_UNAUDITED
