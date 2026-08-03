import numpy as np
import torch

from src.care_myocardium.training.care_ase_trainer import (
    build_care_ase_targets,
    build_full_case_target_cache,
    per_gt_component_tversky,
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
    assert "scar_component_id" in targets


def test_full_case_component_volume_survives_patch_slice():
    seg = np.zeros((6, 16, 16), dtype=np.int16)
    seg[:, 4:12, 4:12] = 1
    seg[2, 6:8, 6:8] = 5
    seg[2, 12:14, 12:14] = 5
    cache = build_full_case_target_cache(seg, (2.0, 1.0, 1.0))
    sliced = slice_full_case_target_cache(cache, center=(2, 7, 7), patch_size=(3, 6, 6))

    visible_ids = sorted(int(v) for v in np.unique(sliced["scar_component_id"]) if int(v) > 0)
    assert visible_ids == [1]
    assert float(sliced["scar_component_volume_mm3"][sliced["scar_component_id"] == 1].mean()) == 8.0


def test_component_tversky_uses_full_case_component_volume_map():
    seg = np.zeros((6, 16, 16), dtype=np.int16)
    seg[:, 4:12, 4:12] = 1
    seg[2, 6:8, 6:8] = 5
    seg[2, 12:14, 12:14] = 5
    cache = build_full_case_target_cache(seg, (2.0, 1.0, 1.0))
    sliced = slice_full_case_target_cache(cache, center=(2, 7, 7), patch_size=(3, 6, 6))
    target = torch.from_numpy((sliced["scar_component_id"] > 0).astype(np.float32))[None, None]
    logit = torch.where(target > 0, torch.full_like(target, 10.0), torch.full_like(target, -10.0))
    valid = torch.ones_like(target)

    loss = per_gt_component_tversky(logit, target, valid, {"full_case_target_cache": sliced})

    assert torch.isfinite(loss)
    assert float(loss) < 0.05
