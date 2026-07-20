# R2 Known-Bad Selftest Report

| fixture | expected_key | status |
| --- | --- | --- |
| `fake_sha` | `bad_weight_sha` | `PASS_EXPECTED_FAILURE` |
| `missing_license` | `missing_license` | `PASS_EXPECTED_FAILURE` |
| `binary_frame0_source` | `binary_frame0_source` | `PASS_EXPECTED_FAILURE` |
| `matched_control_mismatch` | `matched_control_mismatch` | `PASS_EXPECTED_FAILURE` |
| `direct_velocity_displacement` | `direct_velocity_displacement` | `PASS_EXPECTED_FAILURE` |
| `missing_seven_step_integration` | `missing_seven_step_integration` | `PASS_EXPECTED_FAILURE` |
| `proxy_jacobian_inverse_syn` | `proxy_jacobian_inverse_syn` | `PASS_EXPECTED_FAILURE` |
| `pair_as_case` | `pair_as_case` | `PASS_EXPECTED_FAILURE` |
| `temporal_z` | `temporal_z` | `PASS_EXPECTED_FAILURE` |
| `unconsumed_inputs` | `unconsumed_inputs` | `PASS_EXPECTED_FAILURE` |
| `r2_self_freeze` | `r2_self_freeze` | `PASS_EXPECTED_FAILURE` |

R3 final packet known-bad fixtures: PASS_EXPECTED_FAILURE for pending monitor, missing finalizer coverage, stale C0, R2 self-freeze, forbidden authority tokens.
