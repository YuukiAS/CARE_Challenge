import numpy as np
import pytest

from scripts.inference import run_care_owned_pathology_validation_probe as probe


def test_anchor_probability_sum_is_checked_before_any_renormalization():
    probs = np.full((6, 2, 2, 2), 1.0 / 6.0, dtype=np.float32)
    probs[0, 0, 0, 0] += 0.01

    with pytest.raises(RuntimeError, match="channel sum error"):
        probe.validate_anchor_probabilities(probs, "Case1001")


def test_validation_gt_access_marker_is_rejected():
    with pytest.raises(RuntimeError, match="VALIDATION_GT_PATH_ACCESSED"):
        probe.assert_no_gt_access([probe.REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr/Case1001.nii.gz"])


def test_compact_myops_output_allows_anatomy_but_rejects_unknown_labels():
    valid_with_anatomy = np.array([[[0, 1, 2, 3, 4, 5]]], dtype=np.uint8)
    invalid = np.array([[[0, 4, 5, 9]]], dtype=np.uint8)

    probe.validate_compact_array(valid_with_anatomy, "Case1001")
    with pytest.raises(RuntimeError, match="compact labels invalid"):
        probe.validate_compact_array(invalid, "Case1001")


def test_custom_pathology_must_differ_from_nnunet_for_both_targets():
    rows = [{"scar_changed_voxels_vs_nnunet": 0, "edema_changed_voxels_vs_nnunet": 3}]

    with pytest.raises(RuntimeError, match="CUSTOM_PATHOLOGY_CHANGED_VOXELS_ZERO"):
        probe.validate_custom_change_counts(rows)


def test_composition_contract_rejects_scar_or_edema_source_mismatch():
    rows = [{
        "case_id": "Case1001",
        "scar_equals_care_dg_scar": True,
        "edema_equals_scr_class4_minus_scar_overlap": False,
        "anatomy_label_voxels": 0,
    }]

    with pytest.raises(RuntimeError, match="PATHOLOGY_COMPOSITION_CONTRACT_FAILED"):
        probe.validate_overlap_contract(rows)
