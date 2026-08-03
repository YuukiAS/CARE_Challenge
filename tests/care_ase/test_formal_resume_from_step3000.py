from src.care_myocardium.training.care_ase_runtime import validate_logical_chunk_invocation


def test_formal_resume_from_step3000_continues_to_4000():
    receipt = validate_logical_chunk_invocation(start_step=3000, end_step=4000, allow_short_smoke=False, resume_checkpoint_present=True)
    assert receipt == {"logical_chunk_start": 2000, "logical_chunk_end": 4000}
