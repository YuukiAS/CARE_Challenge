import numpy as np
import pytest

from scripts.inference import run_care_owned_pathology_validation_probe as probe


def test_pathology_fallback_must_be_empty():
    payload = {"pathology_label_fallback": {"cases": ["Case1001"]}}

    with pytest.raises(RuntimeError, match="pathology fallback must be empty"):
        probe.validate_pathology_fallback_empty(payload)


def test_compact_validator_accepts_historical_myops_compact_classes():
    valid = np.array([[[0, 1, 2, 3, 4, 5]]], dtype=np.uint8)

    probe.validate_compact_array(valid, "Case1001")
    assert probe.RAW_MAP == {0: 0, 1: 200, 2: 500, 3: 600, 4: 1220, 5: 2221}


def test_checkpoint_contract_constants_pin_frozen_models():
    assert probe.CARE_DG_CKPT.name == "checkpoint_step05000.pt"
    assert "checkpoint_step04000.pt" not in str(probe.CARE_DG_CKPT)
    assert probe.SCR_CKPT.name == "checkpoint_final.pt"
    assert probe.SCAR_SHA == "b59c7e1ade5cb987332de2a94f702b4aa60d1fcb042d9939736ba0f50854b0e7"
    assert probe.SCR_SHA == "fd1bab769737d7e85102d27b562cc7229bb8f3ade53e1d82ccd39c4a863e7a90"
