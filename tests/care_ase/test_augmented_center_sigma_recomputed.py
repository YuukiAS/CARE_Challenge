import numpy as np

from scripts.training.care_ase.run_care_ase_r2_chunk import _recompute_augmented_physical_targets


def test_augmented_scar_center_heatmap_is_recomputed_from_final_segmentation():
    cache = {"scar_center_fullres": np.zeros((7, 9, 9), dtype=np.float32)}
    seg = np.zeros((7, 9, 9), dtype=np.int16)
    seg[3, 4, 4] = 5

    _recompute_augmented_physical_targets(cache, seg, (1.0, 1.0, 1.0))
    heatmap = cache["scar_center_fullres"]

    assert heatmap.shape == seg.shape
    assert float(heatmap.max()) > 0.9
    assert np.unravel_index(int(np.argmax(heatmap)), heatmap.shape) == (3, 4, 4)
