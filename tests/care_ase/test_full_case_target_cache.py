import numpy as np
import torch

from src.care_myocardium.training.care_ase_trainer import (
    build_care_ase_targets,
    build_full_case_target_cache,
    slice_full_case_target_cache,
)


def _fake_outputs() -> dict:
    return {
        "components": {
            "scar_quarter_center": torch.zeros(1, 1, 2, 4, 4),
            "scar_half_center": torch.zeros(1, 1, 4, 8, 8),
        }
    }


def test_full_case_target_cache_preserves_extent_profile_not_patch_local():
    seg = np.zeros((8, 16, 16), dtype=np.int16)
    seg[:, 4:12, 4:12] = 1
    seg[1, 6:8, 6:8] = 5
    seg[6, 8:10, 8:10] = 5
    cache = build_full_case_target_cache(seg, (2.0, 1.0, 1.0))
    sliced = slice_full_case_target_cache(cache, center=(1, 8, 8), patch_size=(4, 8, 8))

    assert sliced["scar_slice_presence"].shape == (8,)
    assert sliced["scar_slice_presence"][1] == 1.0
    assert sliced["scar_slice_presence"][6] == 1.0
    assert float(sliced["scar_slice_pathology_voxels"][6]) > 0.0


def test_full_case_cache_padding_keeps_ignore_and_valid_zero():
    seg = np.zeros((4, 8, 8), dtype=np.int16)
    seg[:, 2:6, 2:6] = 1
    cache = build_full_case_target_cache(seg, (1.0, 1.0, 1.0))
    sliced = slice_full_case_target_cache(cache, center=(-2, 2, 2), patch_size=(6, 10, 10))

    assert int((sliced["scar_context_target"] == -1).sum()) > 0
    assert float(sliced["valid_label_mask"][0].sum()) == 0.0
    assert float(sliced["geometry_valid"][0].sum()) == 0.0


def test_build_targets_prefers_full_case_cache_over_patch_recompute():
    full_seg = np.zeros((8, 16, 16), dtype=np.int16)
    full_seg[:, 4:12, 4:12] = 1
    full_seg[7, 6:8, 6:8] = 5
    cache = build_full_case_target_cache(full_seg, (1.0, 1.0, 1.0))
    sliced = slice_full_case_target_cache(cache, center=(1, 8, 8), patch_size=(4, 8, 8))
    patch_seg = torch.zeros(1, 4, 8, 8, dtype=torch.long)
    availability = torch.ones(1, 3)

    targets = build_care_ase_targets(
        patch_seg,
        availability,
        _fake_outputs(),
        {"spacing": torch.ones(1, 3), "full_case_target_cache": sliced},
    )

    assert targets["target_builder_provenance"] == "full_case_target_cache"
    assert targets["scar_slice_presence"].shape[-1] == 8
    assert float(targets["scar_slice_presence"][0, 0, 7]) == 1.0
