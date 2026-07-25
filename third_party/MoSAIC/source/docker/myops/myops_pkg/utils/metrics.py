from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt


def dice_score(pred: np.ndarray, target: np.ndarray) -> float:
    pred = pred.astype(bool)
    target = target.astype(bool)
    intersection = float(np.logical_and(pred, target).sum())
    denominator = float(pred.sum() + target.sum())
    if denominator == 0.0:
        return 1.0
    return 2.0 * intersection / denominator


def _surface(mask: np.ndarray) -> np.ndarray:
    if mask.sum() == 0:
        return mask.astype(bool)
    eroded = binary_erosion(mask, iterations=1, border_value=0)
    return np.logical_xor(mask.astype(bool), eroded.astype(bool))


def hd95(pred: np.ndarray, target: np.ndarray, spacing: Sequence[float]) -> float:
    pred = pred.astype(bool)
    target = target.astype(bool)
    if pred.sum() == 0 and target.sum() == 0:
        return 0.0
    if pred.sum() == 0 or target.sum() == 0:
        return float("inf")
    pred_surface = _surface(pred)
    target_surface = _surface(target)
    dt_pred = distance_transform_edt(~pred_surface, sampling=spacing)
    dt_target = distance_transform_edt(~target_surface, sampling=spacing)
    distances = np.concatenate([dt_target[pred_surface], dt_pred[target_surface]])
    if distances.size == 0:
        return 0.0
    return float(np.percentile(distances, 95))
