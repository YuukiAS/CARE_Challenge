import numpy as np

from scripts.training.care_ase.run_care_ase_r2_chunk import _recompute_augmented_physical_targets


def test_augmented_context_and_distance_are_recomputed_from_final_segmentation():
    cache = {
        "signed_endo_distance": np.full((5, 8, 8), 99.0, dtype=np.float32),
        "scar_context_target": np.full((5, 8, 8), 3, dtype=np.int64),
    }
    seg = np.zeros((5, 8, 8), dtype=np.int16)
    seg[:, 2:6, 2:6] = 1
    seg[:, 3:5, 3:5] = 2
    seg[2, 4, 4] = 5

    _recompute_augmented_physical_targets(cache, seg, (1.0, 1.0, 1.0))

    assert cache["signed_endo_distance"].shape == seg.shape
    assert not np.all(cache["signed_endo_distance"] == 99.0)
    assert cache["scar_context_target"].shape == seg.shape
    assert not np.all(cache["scar_context_target"] == 3)
