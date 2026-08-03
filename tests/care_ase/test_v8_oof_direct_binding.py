import numpy as np
import pytest

from scripts.evaluation.care_ase.build_care_ase_r2_hard_negative_manifest import bind_prediction_to_preprocessed_grid


DIRECT_META = {
    "case_id": "Case0001",
    "source_kind": "direct_preprocessed_grid_argmax_npy",
    "source_stock_fold": 0,
    "source_checkpoint_path": "stock/fold_0/checkpoint_final.pth",
    "source_checkpoint_sha256": "a" * 64,
    "source_preprocessed_image_path": "preprocessed/Case0001.b2nd",
    "source_preprocessed_image_sha256": "b" * 64,
    "plans_path": "preprocessed/nnUNetPlans.json",
    "plans_sha256": "c" * 64,
    "producer_source_commit_sha": "d" * 40,
    "producer_command": "scripts/evaluation/care_ase/build_stock_oof_preprocessed_grid_predictions.py",
    "producer_stage": "direct_preprocessed_grid_inference",
    "producer_binding_method": "direct_stock_inference_on_preprocessed_grid",
    "preprocessed_grid_binding": True,
    "preprocessed_shape": [4, 8, 8],
    "probability_shape_CZYX": [6, 4, 8, 8],
    "probability_sha256": "e" * 64,
    "argmax_shape_ZYX": [4, 8, 8],
    "argmax_sha256": "f" * 64,
    "proof_case_not_in_source_fold_train": True,
}


def test_v8_direct_preprocessed_grid_binding_accepts_complete_producer_receipt():
    gt = np.zeros((4, 8, 8), dtype=np.uint8)
    pred = np.zeros_like(gt)
    pred[1, 2, 3] = 5
    geometry = {"shape_zyx": [4, 8, 8], "spacing_zyx": [2.0, 1.0, 1.0]}
    meta = {**DIRECT_META, "preprocessed_geometry": geometry}

    bound, receipt = bind_prediction_to_preprocessed_grid(gt, pred, source_meta=meta, preprocessed_geometry=geometry)

    assert np.array_equal(bound, pred)
    assert receipt["binding"] == "direct_stock_inference_on_preprocessed_grid"
    assert receipt["nnunet_plan_probability_resample"] is False


def test_v8_probability_or_self_declared_binding_without_producer_receipt_rejected():
    gt = np.zeros((4, 8, 8), dtype=np.uint8)
    probs = np.zeros((6, 4, 8, 8), dtype=np.float32)
    meta = {
        "case_id": "Case0001",
        "source_kind": "canonical_stock_nnunet_oof_probability_npz",
        "preprocessed_grid_binding": True,
        "producer_binding_method": "direct_stock_inference_on_preprocessed_grid",
        "preprocessed_shape": [4, 8, 8],
    }
    geometry = {"shape_zyx": [4, 8, 8], "spacing_zyx": [2.0, 1.0, 1.0]}

    with pytest.raises(RuntimeError, match="producer receipt"):
        bind_prediction_to_preprocessed_grid(gt, probs, source_meta=meta, preprocessed_geometry=geometry)
