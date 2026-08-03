import numpy as np
import pytest

from scripts.evaluation.care_ase.build_care_ase_r2_hard_negative_manifest import (
    bind_prediction_to_preprocessed_grid,
)


def test_exported_nifti_oof_without_preprocessed_grid_proof_rejected():
    gt = np.zeros((4, 8, 8), dtype=np.uint8)
    pred = np.zeros((8, 8, 4), dtype=np.uint8)
    source_meta = {
        "source_kind": "canonical_stock_nnunet_oof_anchor_manifest",
        "header_zooms": [1.0, 1.0, 2.0],
        "preprocessed_grid_binding": False,
    }
    geometry = {"shape_zyx": [4, 8, 8], "spacing_zyx": [2.0, 1.0, 1.0]}

    with pytest.raises(RuntimeError, match="direct preprocessed-grid artifact"):
        bind_prediction_to_preprocessed_grid(gt, pred, source_meta=source_meta, preprocessed_geometry=geometry)
