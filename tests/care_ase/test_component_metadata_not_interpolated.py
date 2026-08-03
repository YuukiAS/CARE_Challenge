import numpy as np

from src.care_myocardium.training.care_ase_runtime import _apply_component_metadata_lookup


def test_component_volume_and_center_are_lookup_not_interpolated():
    cache = {
        "scar_component_id": np.array(
            [
                [[1, 1], [0, 2]],
                [[2, 0], [0, 0]],
            ],
            dtype=np.int64,
        )
    }
    metadata = {
        1: {"full_case_volume_mm3": 100.0, "full_case_center_zyx": [1.0, 2.0, 3.0]},
        2: {"full_case_volume_mm3": 400.0, "full_case_center_zyx": [4.0, 5.0, 6.0]},
    }
    _apply_component_metadata_lookup(cache, metadata)

    assert set(np.unique(cache["scar_component_volume_mm3"]).tolist()) == {0.0, 100.0, 400.0}
    assert float(cache["scar_component_volume_mm3"][0, 1, 1]) == 400.0
    assert float(cache["scar_component_center_z"][0, 1, 1]) == 4.0
