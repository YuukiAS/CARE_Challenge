from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
if str(MOSAIC_CODE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_CODE))

from mosaic_fair_protocol import (  # noqa: E402
    CARE_INPUT_ORDER,
    COMPACT_TO_OFFICIAL,
    MOSAIC_INPUT_ORDER,
    classify_spatial_layout,
    geometry_matches,
    pathology_mask,
    remap_labels,
    reorder_channels,
)


def test_channel_order_reorders_care_lge_t2_c0_to_mosaic_lge_c0_t2():
    image = np.stack(
        [
            np.full((2, 2, 2), 1),
            np.full((2, 2, 2), 2),
            np.full((2, 2, 2), 3),
        ]
    )
    reordered = reorder_channels(image, CARE_INPUT_ORDER, MOSAIC_INPUT_ORDER)
    assert [int(reordered[i, 0, 0, 0]) for i in range(3)] == [1, 3, 2]


def test_compact_to_official_label_mapping_preserves_pathology_ids():
    compact = np.array([0, 4, 5, 4], dtype=np.int32)
    official = remap_labels(compact, COMPACT_TO_OFFICIAL)
    assert official.tolist() == [0, 1220, 2221, 1220]


def test_edema_zone_and_pure_edema_are_distinct_masks():
    labels = np.array([0, 4, 5, 4], dtype=np.int32)
    pure = pathology_mask(labels, "pure_edema")
    zone = pathology_mask(labels, "edema_zone")
    assert pure.tolist() == [False, True, False, True]
    assert zone.tolist() == [False, True, True, True]


def test_spatial_layout_detects_zhw_and_hwz_transpose():
    reference = (3, 5, 7)
    assert classify_spatial_layout((3, 5, 7), reference) == "ZHW"
    assert classify_spatial_layout((5, 7, 3), reference) == "HWZ"


def test_geometry_roundtrip_requires_size_spacing_origin_direction():
    left = {
        "size_xyz": [7, 5, 3],
        "spacing_xyz": [1.0, 1.0, 5.0],
        "origin_xyz": [0.0, 0.0, 0.0],
        "direction": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
    }
    assert geometry_matches(left, dict(left))
    changed = dict(left)
    changed["spacing_xyz"] = [1.0, 1.0, 6.0]
    assert not geometry_matches(left, changed)
