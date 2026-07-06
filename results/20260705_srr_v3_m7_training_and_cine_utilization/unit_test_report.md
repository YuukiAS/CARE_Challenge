# Unit Test Report

status: `PASS_LIGHTWEIGHT_EXECUTOR_VALIDATION`

## Commands

| command | status | scope |
| --- | --- | --- |
| `python -m py_compile src/care_myocardium/losses/srr_losses.py scripts/training/run_srr_propref_myops_fold0.py scripts/evaluation/run_srr_v3_m7_continued_repair.py scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py` | `exit 0` | Syntax check for loss graph repair, training gradient sanity path, MyoPS continued helper, and Cine repair helper. |
| `bash -n jobs/src/run_srr_v3_m7_continued_repair.sh` | `exit 0` | Syntax check for GPU Slurm continued helper entrypoint. |
| `bash -n jobs/src/run_srr_v3_m7_continued_repair_cpu.sh` | `exit 0` | Syntax check for high-memory CPU fallback entrypoint. |
| `python -m py_compile scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py` | `exit 0` | Syntax check for continued fail-closed aggregator guard. |
| `python scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py --job-state-snapshot ...` | `exit 0` | Exercised continued fail-closed aggregator path without overwriting metric CSVs. |

## Runtime Validation

- `loss_component_gradient_sanity.csv`: `93 PASS`, `14 PASS_ZERO_JUSTIFIED`, no `BACKWARD_FAILED`, no `EVIDENCE_NOT_FOUND`, no unexplained `ZERO_GRAD_OR_DETACHED`.
- `strict_validator_report.md`: `PASS_FAIL_CLOSED`.
- `completion_check.md`: `M7_CONTINUED_READY_FOR_REVIEW`.
- No validation packaging, upload, hosted metric claim, route promotion, `review.md` write, or M8 start was performed.
