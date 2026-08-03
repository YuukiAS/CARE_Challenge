from src.care_myocardium.training.care_ase_runtime import validate_logical_chunk_invocation


def test_initial_chunk_keeps_2000_step_boundary_contract():
    receipt = validate_logical_chunk_invocation(start_step=4000, end_step=6000, allow_short_smoke=False, resume_checkpoint_present=False)
    assert receipt["logical_chunk_end"] == 6000
