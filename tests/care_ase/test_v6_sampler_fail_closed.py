import pytest

from src.care_myocardium.training.care_ase_sampler import _hard_negative_category


def test_manifest_claim_with_empty_oof_coordinates_rejected():
    manifest = {
        "cases": {
            "CaseX": {
                "scar_fn_voxels": 12,
                "scar_fp_voxels": 0,
                "edema_fn_voxels": 0,
                "edema_fp_voxels": 0,
                "targets": {"scar_oof_fn": []},
            }
        }
    }

    with pytest.raises(RuntimeError, match="provides no scar_oof_fn coordinates"):
        _hard_negative_category(manifest, "CaseX", "scar", "oof_fn")
