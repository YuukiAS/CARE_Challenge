# M10 Mapper Draft Report

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Mapper phase: `draft_after_wave1_merge`

## Scope

This draft mapper pass inspected first-party source, config, tests, and lightweight wave 1 evidence after `m10_shared_architecture_executor` returned `READY_FOR_CONTROLLER_MERGE`.

The mapper did not inspect raw data, checkpoints, NIfTI outputs, large logs, upload packages, secrets, or environment dumps. It did not write `review.md`, submit Slurm jobs, train, package validation, upload, claim hosted metrics, or decide route promotion.

## Inputs Checked

- `src/care_myocardium/models/srr_spatial_dictionary.py`
- `src/care_myocardium/models/srr_blocks.py`
- `src/care_myocardium/models/srr_dictionary_memory.py`
- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/losses/srr_losses.py`
- `configs/srr_v3_m10_complete_repair.yaml`
- `src/care_myocardium/tests/test_srr_v3_m10_fidelity.py`
- `results/20260711_srr_v3_m10_architecture_fidelity/m10_slot_contract.csv`
- `results/20260711_srr_v3_m10_architecture_fidelity/m10_loss_component_contract.csv`
- `results/20260711_srr_v3_m10_mechanism_smoke/m10_smoke_summary.json`
- `results/20260711_srr_v3_m10_mechanism_smoke/m10_known_bad_checks.csv`
- `results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/completion_check.md`

## Component Draft Status

| Component | Draft status | Evidence status | Evidence |
| --- | --- | --- | --- |
| Canonical modality order `[LGE,T2,C0]` | implemented | verified_for_wave1 | `configs/srr_v3_m10_complete_repair.yaml`; `m10_slot_contract.csv` |
| Exact 16-slot dictionary per scale | implemented | verified_for_wave1 | `src/care_myocardium/models/srr_spatial_dictionary.py:M10_SLOT_SPECS`; `m10_slot_contract.csv` |
| Invalid-slot zero gate/value/gradient | implemented | verified_for_wave1 | `test_srr_v3_m10_fidelity.py`; `m10_slot_contract.csv` |
| Two-pass lesion-conditioned spatial dictionary | implemented | verified_for_wave1_smoke | `M10TwoPassSpatialDictionary`; M10 fidelity tests |
| Pattern-SIP independent loss | implemented | verified_for_wave1 | `pattern_sip_integrativeness_loss`; `m10_loss_component_contract.csv` |
| Prototype memory safe no-T2 policy | implemented | verified_for_wave1 | `M10CrossFittedPrototypeMemory`; known-bad checks |
| M10 D0-D3 variant declarations | implemented | verified_for_wave1 | `src/care_myocardium/models/srr_propref.py`; config |
| SRR proposal/refinement final-output relation | partial | verified_for_wave1_smoke | `final_output_base: SRR_PROPOSAL_REFINEMENT`; no-T2 edema probability zero test |
| Formal runtime training/evidence | not_started | missing | wave 2 not launched yet |
| Cine registration/temporal path | not_started | missing | wave 3 not launched yet |

## Verification Receipts

Controller re-ran:

```text
pytest src/care_myocardium/tests/test_srr_v3_m10_fidelity.py -> 5 passed
pytest test_srr_v3_m10_fidelity.py test_srr_dictionary_bank.py test_srr_losses.py test_srr_runtime_prototype_bank.py -> 15 passed, 3 warnings
py_compile touched wave1 files -> pass
validate_executor_plan.py -> pass
git diff --check -> pass
```

## Carry-Forward To Wave 2

The broader compatibility test `src/care_myocardium/tests/test_srr_proposal_prototypes.py` currently fails two tests because `scripts/training/run_srr_propref_myops_fold0.py::propref_loss` expects `args.variant` while older tests use an args fixture without that field. The script is outside wave 1 write scope and inside wave 2 write scope, so this must be addressed by `m10_myops_training_executor` before formal MyoPS jobs or evidence claims.

## Mapper Draft Decision

`MAPPER_DRAFT_READY_FOR_WAVE2_WITH_CARRY_FORWARD`

Wave 1 shared architecture can be treated as frozen for wave 2. If wave 2 finds a shared architecture or loss wiring defect, the controller must return to wave 1 rather than hot-patching shared files inside wave 2.
