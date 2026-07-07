# M8 Validator Unit Test Report

status: `PASS_FAIL_CLOSED`

Temporary known-bad fixtures were generated outside the repo and are not committed. Summary rows are in `m8_validator_unit_test_report.csv`.

| fixture | expected | actual | failure_reason |
| --- | --- | --- | --- |
| good_ready_fixture | PASS | PASS |  |
| total_training_budget_under_8h | FAIL_CLOSED | FAIL_CLOSED | ready packet has included train_loop_seconds 1000.0 < 28800 |
| missing_training_budget_ledger | FAIL_CLOSED | FAIL_CLOSED | ready packet missing required file m8_training_budget_ledger.csv; ready packet has included train_loop_seconds 0.0 < 28800 |
| pending_monitor_packet_marked_ready | FAIL_CLOSED | FAIL_CLOSED | ready packet contains monitor token RUNNING; ready packet contains monitor token AWAITING_RUNTIME_AGGREGATION |
| completed_job_not_reaggregated | FAIL_CLOSED | FAIL_CLOSED | ready packet contains monitor token PENDING_PRIORITY |
| config_contract_not_read_by_code | FAIL_CLOSED | FAIL_CLOSED | variant config contract is not tied to the training code reader |
| variants_only_renamed | FAIL_CLOSED | FAIL_CLOSED | variant config variants only differ by name |
| missing_per_case_anchor_delta | FAIL_CLOSED | FAIL_CLOSED | m8_srr_contribution_by_case.csv lacks real per-case anchor_delta_rate |
| easy_only_formal_evaluation | FAIL_CLOSED | FAIL_CLOSED | ready packet lacks broad formal evidence with T2-present cases |
| no_t2_safety_violation | FAIL_CLOSED | FAIL_CLOSED | ready packet contains no-T2 edema voxel safety violation |
| missing_local_candidate_assembly | FAIL_CLOSED | FAIL_CLOSED | ready packet missing required file m8_candidate_assembly_matrix.csv; ready packet lacks complete local candidate assembly |
| cine_three_case_smoke | FAIL_CLOSED | FAIL_CLOSED | ready packet Cine registration covers fewer than 12 cases; ready packet lacks at least two mature non-reference Cine registration families |
| no_best_registration_selection | FAIL_CLOSED | FAIL_CLOSED | ready packet lacks quantitative best-registration selection text |
| usable_registration_without_temporal_dictionary | FAIL_CLOSED | FAIL_CLOSED | usable Cine registration exists but temporal dictionary was not executed |
| missing_label_export_qc | FAIL_CLOSED | FAIL_CLOSED | ready packet missing required file m8_official_label_mapping_qc.csv |
| placeholder_final_proof | FAIL_CLOSED | FAIL_CLOSED | ready packet contains monitor token AWAITING COMPLETED M8 RUNTIME AGGREGATION; ready packet contains monitor token AWAITING COMPLETED |
| unauthorized_upload_claim | FAIL_CLOSED | FAIL_CLOSED | packet references upload package path or zip |
