from __future__ import annotations

from typing import Iterable

import numpy as np
from scipy.ndimage import label as cc_label


def largest_component(mask: np.ndarray) -> np.ndarray:
    if mask.sum() == 0:
        return mask.astype(bool)
    labeled, num = cc_label(mask.astype(bool))
    if num == 0:
        return mask.astype(bool)
    best_component = None
    best_size = -1
    for component_idx in range(1, num + 1):
        component = labeled == component_idx
        component_size = int(component.sum())
        if component_size > best_size:
            best_component = component
            best_size = component_size
    return best_component.astype(bool)


def keep_components_with_mask(
    mask: np.ndarray, min_size: int, required_overlap_mask: np.ndarray | None = None,
) -> np.ndarray:
    if mask.sum() == 0:
        return mask.astype(bool)
    labeled, num = cc_label(mask.astype(bool))
    if num == 0:
        return mask.astype(bool)
    keep = np.zeros_like(mask, dtype=bool)
    for component_idx in range(1, num + 1):
        component = labeled == component_idx
        if int(component.sum()) < int(min_size):
            continue
        if required_overlap_mask is not None and not bool((component & required_overlap_mask.astype(bool)).any()):
            continue
        keep |= component
    return keep


def enforce_pathology_inside_myo(
    prediction: np.ndarray, myo_label: int, pathology_labels: Iterable[int],
    external_myo_mask: np.ndarray | None = None,
) -> np.ndarray:
    constrained = prediction.copy()
    myo_mask = constrained == myo_label
    if external_myo_mask is not None:
        myo_mask = myo_mask | external_myo_mask.astype(bool)
    for pathology_label in pathology_labels:
        pathology_mask = constrained == pathology_label
        constrained[pathology_mask & (~myo_mask)] = 0
    return constrained


def clean_prediction_by_class(
    prediction: np.ndarray, min_component_sizes: dict[int, int],
    required_overlap_masks: dict[int, np.ndarray | None] | None = None,
) -> np.ndarray:
    cleaned = prediction.copy()
    for class_id, min_size in min_component_sizes.items():
        class_mask = cleaned == class_id
        overlap_mask = None if required_overlap_masks is None else required_overlap_masks.get(class_id)
        filtered = keep_components_with_mask(class_mask, min_size=min_size, required_overlap_mask=overlap_mask)
        cleaned[class_mask & (~filtered)] = 0
    return cleaned
