# Strict Validator Report

validator_entrypoint: `python scripts/evaluation/run_srr_v3_m6_concrete_architecture_repair.py --validate-packet <packet_dir>`

good_packet_validation: PASS

good_packet_failure_reasons: `none`

| known_bad_packet | expected_failure | actual_exit_code | status | failure_reason |
| --- | --- | --- | --- | --- |
| claim_only_architecture_trace | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/claim_only_architecture_trace", |   "reasons": [ |     "claim_only_architecture_trace" |   ] | } |
| missing_fidelity_contract | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/missing_fidelity_contract", |   "reasons": [ |     "missing_fidelity_contract" |   ] | } |
| dictionary_slot_usage_all_empty | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/dictionary_slot_usage_all_empty", |   "reasons": [ |     "dictionary_slot_usage_all_empty" |   ] | } |
| prototype_bank_empty_or_no_t2_negative | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/prototype_bank_empty_or_no_t2_negative", |   "reasons": [ |     "prototype_bank_empty" |   ] | } |
| segmentation_bypass_without_fallback_reason | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/segmentation_bypass_without_fallback_reason", |   "reasons": [ |     "low_quality_srr_did_not_choose_segmentation_branch" |   ] | } |
| hidden_decode_delta | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/hidden_decode_delta", |   "reasons": [ |     "closed_fallback_hidden_decode_delta" |   ] | } |
| full_volume_refiner | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/full_volume_refiner", |   "reasons": [ |     "full_volume_refiner" |   ] | } |
| loss_components_no_backward | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/loss_components_no_backward", |   "reasons": [ |     "loss_components_missing_backward_evidence" |   ] | } |
| zero_srr_contribution | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/zero_srr_contribution", |   "reasons": [ |     "zero_srr_contribution_correction_positive" |   ] | } |
| no_t2_edema_nonzero | nonzero_exit | 1 | PASS_FAIL_CLOSED | { |   "ok": false, |   "packet": "/users/a/e/aereinh/.tmp/codex-care/m6_known_bad_rqgnoydh/no_t2_edema_nonzero", |   "reasons": [ |     "no_t2_edema_nonzero" |   ] | } |

strict_validator_status: PASS
