# RC1 Unit Test Report

Decision: PASS_READY_FOR_CONTROLLER_VERIFICATION

Scope: RC1 runtime foundation/model repair only. No Slurm submission, no formal training credit, no upload/push.

## Commands

| Command | Exit | Result |
|---|---:|---|
| `./envs/env_CARE/bin/python -m pytest tests/care_mm/test_care_srr_cascade_rescue.py tests/care_mm/test_care_srr_cascade_runtime_rc1.py -q` | 0 | 14 passed, 1 warning |
| `./envs/env_CARE/bin/python -m py_compile <RC1 python files>` | 0 | PASS |
| `bash -n jobs/care_mm/precompute_care_srr_cascade_source_cache.sh` | 0 | PASS |
| `bash -n jobs/care_mm/run_care_srr_cascade_formal_training.sh` | 0 | PASS |
| `./envs/env_CARE/bin/python scripts/training/run_care_srr_cascade_formal.py --print-contract` | 0 | PASS |
| `./envs/env_CARE/bin/python scripts/inference/run_care_srr_cascade_inference.py --print-contract` | 0 | PASS |
| `./envs/env_CARE/bin/python scripts/evaluation/evaluate_care_srr_cascade.py --print-contract` | 0 | PASS |
| `./envs/env_CARE/bin/python scripts/evaluation/select_care_srr_cascade.py --print-contract` | 0 | PASS |
| `./envs/env_CARE/bin/python scripts/evaluation/validate_care_srr_cascade_packet.py --print-contract` | 0 | PASS |
| `./envs/env_CARE/bin/python scripts/evaluation/orchestrate_care_srr_cascade_w3.py --print-contract` | 0 | PASS |
| `./envs/env_CARE/bin/python scripts/training/run_care_srr_cascade_formal.py --dry-run ...` | 0 | PASS_DRY_RUN; formal_training_credit=0; preformal assets intentionally fail closed |

## Evidence

- Model branch independence: `model_branch_independence_checks.csv` records active branch perturbation changes and inactive branch gradient sum zero.
- Prototype categories: `prototype_category_contract.json` records category-specific negatives, own-shard exclusion, cap semantics, no-T2 edema negative exclusion, and fail-closed bank behavior.
- Future entrypoints: `future_wave_entrypoint_audit.json` records print-contract/dry-run exit codes and confirms the formal shell points at `run_care_srr_cascade_formal.py`, not the old guarded rescue entrypoint.

## RC2 Pending Gates

- Real all-220 OOF anchor/source/prototype cache receipts are not created by RC1.
- `formal_authorization_gate.json` is absent/not PASS, so orchestrator/formal jobs must not be submitted.
- RC2 must produce real source cache v2 parity, anchor cache v2 manifest, prototype cache v2 manifest, matched schedule hashes, and authorization gate before W3/formal work.
