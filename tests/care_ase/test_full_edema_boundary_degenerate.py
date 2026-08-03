import numpy as np

from src.care_myocardium.training.care_ase_trainer import _edema_boundary_numpy


def test_empty_edema_boundary_has_no_valid_supervision():
    seg = np.zeros((3, 8, 8), dtype=np.int16)
    out = _edema_boundary_numpy(seg, (2.0, 1.0, 1.0))

    assert out["edema_boundary"].sum() == 0
    assert out["edema_boundary_raw_mm"].sum() == 0
    assert out["edema_boundary_valid"].sum() == 0


def test_full_patch_edema_without_observable_boundary_has_no_valid_supervision():
    seg = np.full((3, 8, 8), 4, dtype=np.int16)
    out = _edema_boundary_numpy(seg, (2.0, 1.0, 1.0))

    assert out["edema_boundary"].sum() == 0
    assert out["edema_boundary_raw_mm"].sum() == 0
    assert out["edema_boundary_valid"].sum() == 0


def test_observable_edema_boundary_uses_signed_physical_band():
    seg = np.zeros((5, 16, 16), dtype=np.int16)
    seg[:, 4:12, 4:12] = 4
    out = _edema_boundary_numpy(seg, (2.0, 1.0, 1.0))

    assert out["edema_boundary_valid"].sum() > 0
    assert out["edema_boundary"][2, 8, 8] > 0
    assert out["edema_boundary"][2, 0, 0] < 0
