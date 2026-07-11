# MANIFEST

task_key: `20260711_srr_v3_m10_complete_mechanism_repair`
executor_id: `m10_shared_architecture_executor`
completion_token: `READY_FOR_CONTROLLER_MERGE`

## Executor Packet

- `result.md`: executor summary, changed files, verification, boundaries.
- `completion_check.md`: wave 1 completion token.
- `commands_run.md`: commands and results.
- `MANIFEST.md`: this manifest.

## Architecture Fidelity Evidence

- `results/20260711_srr_v3_m10_architecture_fidelity/m10_wave1_architecture_fidelity.md`
- `results/20260711_srr_v3_m10_architecture_fidelity/m10_slot_contract.csv`
- `results/20260711_srr_v3_m10_architecture_fidelity/m10_loss_component_contract.csv`
- `results/20260711_srr_v3_m10_architecture_fidelity/m10_source_fingerprints.json`

## Mechanism Smoke Evidence

- `results/20260711_srr_v3_m10_mechanism_smoke/m10_wave1_smoke_report.md`
- `results/20260711_srr_v3_m10_mechanism_smoke/m10_known_bad_checks.csv`
- `results/20260711_srr_v3_m10_mechanism_smoke/m10_smoke_summary.json`

## Source/Test/Config Files

- `src/care_myocardium/models/srr_blocks.py`
- `src/care_myocardium/models/srr_spatial_dictionary.py`
- `src/care_myocardium/models/srr_dictionary_memory.py`
- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/losses/srr_losses.py`
- `src/care_myocardium/tests/test_srr_v3_m10_fidelity.py`
- `configs/srr_v3_m10_complete_repair.yaml`

## Explicit Non-Outputs

- No `results/20260711_srr_v3_m10_complete_mechanism_repair/review.md`.
- No validation zip/package/upload.
- No checkpoint, NIfTI, prediction output, raw data, large log, secret, commit,
  push, hosted metric claim, route promotion, scientific stop, M11, wave 2, or
  wave 3 artifact.
