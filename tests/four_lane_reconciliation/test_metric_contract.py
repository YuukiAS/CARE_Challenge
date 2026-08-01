from __future__ import annotations

import numpy as np

from scripts.evaluation.four_lane_reconciliation.evaluate_frozen_outer import (
    SMALL_LESION_VOLUME_MM3,
    hausdorff_mm,
    lesion_recall,
)


def test_hausdorff_uses_physical_spacing_not_voxels() -> None:
    pred = np.zeros((3, 3, 3), dtype=bool)
    gt = np.zeros((3, 3, 3), dtype=bool)
    pred[0, 1, 1] = True
    gt[1, 1, 1] = True

    assert hausdorff_mm(pred, gt, (5.0, 1.0, 1.0), 100.0) == 5.0


def test_small_lesion_uses_physical_volume_threshold() -> None:
    pred = np.ones((1, 10, 10), dtype=bool)
    gt = np.ones((1, 10, 10), dtype=bool)

    _recall, small_recall, lesion_count, small_count = lesion_recall(pred, gt, voxel_volume_mm3=20.0)

    assert lesion_count == 1
    assert small_count == 0
    assert small_recall is None
    assert gt.sum() * 20.0 > SMALL_LESION_VOLUME_MM3
