from src.care_myocardium.training.care_myopath_pilot.contracts import known_bad_matrix, validate_contract_payload

def test_known_bad_matrix_rejects_all_fixtures():
    rows = known_bad_matrix()
    assert len(rows) == 20
    assert all(row['rejected'] for row in rows)

def test_valid_minimal_blocked_payload_has_no_contract_errors():
    payload = {'a0_fp32_max_abs_error': 0.0, 'a0_changed_argmax_voxels': 0, 'no_t2_edema_loss': 0.0, 'no_t2_edema_gradient': 0.0, 'proposal_enters_final_logits': True, 'has_model_hashes': True, 'has_config_hashes': True, 'has_split_hashes': True}
    assert validate_contract_payload(payload) == []
