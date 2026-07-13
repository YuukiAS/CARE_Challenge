# M10 Wave 3 Executor Prompt

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Executor: `m10_cine_temporal_executor`

This is Wave 3 of the original M10 controller-supervised task. It is not a new milestone and not a new executor graph.

## Preconditions

- Wave 1 merge receipt: `results/20260711_srr_v3_m10_complete_mechanism_repair/wave1_merge_receipt.md`
- Wave 2 merge receipt: `results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_merge_receipt.md`
- Wave 2 completion token: `READY_FOR_CONTROLLER_MERGE`

## Contract

Follow `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml`, executor id `m10_cine_temporal_executor`.

Allowed write scope is exactly the Wave 3 write scope:

```text
src/care_myocardium/cine/cinema_adapter.py
src/care_myocardium/cine/registration_model.py
src/care_myocardium/cine/temporal_dictionary.py
src/care_myocardium/cine/temporal_model.py
src/care_myocardium/cine/temporal_output.py
src/care_myocardium/tests/test_cine_m10_temporal_fidelity.py
scripts/training/run_cinema_adapter_m10.py
scripts/training/run_cine_registration_m10.py
scripts/training/run_cine_temporal_model_m10.py
scripts/evaluation/evaluate_cine_m10_temporal.py
scripts/evaluation/aggregate_cine_m10_packet.py
jobs/src/run_srr_v3_m10_cinema_adapter.sh
jobs/src/run_srr_v3_m10_cine_registration.sh
jobs/src/run_srr_v3_m10_cine_temporal.sh
results/20260711_srr_v3_m10_cinema_adapter/
results/20260711_srr_v3_m10_cine_registration/
results/20260711_srr_v3_m10_cine_learned_temporal/
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_cine_temporal_executor/
```

Do not edit shared MyoPS model/loss files, wiki files, prompts, `review.md`, validation packaging/upload paths, or M11 files.

## Required Phase Order

1. `cinema_provenance_and_geometry_QA`
2. `cinema_CARE_adapter_formal_training`
3. `learned_diffeomorphic_registration_formal_training`
4. `registration_completion_gate`
5. `learned_temporal_dictionary_formal_training`
6. `same_subset_controls_and_final_output_intervention`
7. `post_job_aggregation`

Training-to-training dependencies use `afterok`; Wave 3 finalizer/accounting uses `afterany`.

## Review Boundary

Wave 3 writes executor result files and completion receipts only. It does not write `review.md`, does not self-review, does not push, and does not claim hosted readiness.
