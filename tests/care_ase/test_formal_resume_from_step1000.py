import pytest

from src.care_myocardium.training.care_ase_runtime import validate_logical_chunk_invocation


def test_formal_resume_from_step1000_continues_to_2000():
    receipt = validate_logical_chunk_invocation(start_step=1000, end_step=2000, allow_short_smoke=False, resume_checkpoint_present=True)
    assert receipt == {"logical_chunk_start": 0, "logical_chunk_end": 2000}


def test_formal_resume_from_step1000_rejects_new_1000_to_3000_chunk():
    with pytest.raises(ValueError, match="logical 2000-step chunk remainder"):
        validate_logical_chunk_invocation(start_step=1000, end_step=3000, allow_short_smoke=False, resume_checkpoint_present=True)
