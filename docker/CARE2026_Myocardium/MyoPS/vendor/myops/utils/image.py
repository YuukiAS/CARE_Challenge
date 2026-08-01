from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.ndimage import zoom


def robust_zscore(volume: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    values = volume[mask > 0] if mask is not None and mask.any() else volume
    values = values[np.isfinite(values)]
    if values.size == 0:
        return volume.astype(np.float32)
    lower = np.percentile(values, 1.0)
    upper = np.percentile(values, 99.0)
    clipped = np.clip(volume, lower, upper).astype(np.float32)
    mean = clipped.mean()
    std = clipped.std()
    if std < 1e-6:
        return clipped - mean
    return (clipped - mean) / std


def compute_zoom_factors(source_spacing: Sequence[float], target_spacing: Sequence[float]) -> list[float]:
    return [float(src / tgt) for src, tgt in zip(source_spacing, target_spacing)]


def resample_nd(
    array: np.ndarray, source_spacing: Sequence[float], target_spacing: Sequence[float], order: int,
) -> np.ndarray:
    if any(dim <= 0 for dim in array.shape):
        raise ValueError(f"Cannot resample array with shape: {array.shape}")
    zoom_factors = compute_zoom_factors(source_spacing, target_spacing)
    target_shape = [max(1, int(round(dim * factor))) for dim, factor in zip(array.shape, zoom_factors)]
    adjusted_zoom = [target / dim for target, dim in zip(target_shape, array.shape)]
    return zoom(array, zoom=adjusted_zoom, order=order).astype(array.dtype, copy=False)


def compute_bbox(mask: np.ndarray, margin: Sequence[int] | int = 0) -> list[list[int]]:
    if isinstance(margin, int):
        margin = [margin] * mask.ndim
    coords = np.argwhere(mask > 0)
    if coords.size == 0:
        return [[0, size] for size in mask.shape]
    min_corner = coords.min(axis=0)
    max_corner = coords.max(axis=0) + 1
    bbox = []
    for axis, (start, stop) in enumerate(zip(min_corner, max_corner)):
        lower = max(0, int(start) - int(margin[axis]))
        upper = min(mask.shape[axis], int(stop) + int(margin[axis]))
        bbox.append([lower, upper])
    return bbox


def crop_to_bbox(array: np.ndarray, bbox: Sequence[Sequence[int]]) -> np.ndarray:
    slices = tuple(slice(start, stop) for start, stop in bbox)
    return array[slices]


def center_crop_or_pad(
    array: np.ndarray, output_shape: Sequence[int], pad_value: float = 0.0,
) -> np.ndarray:
    output_shape = tuple(int(v) for v in output_shape)
    result = np.full(output_shape, pad_value, dtype=array.dtype)
    in_slices = []
    out_slices = []
    for dim, out_dim in enumerate(output_shape):
        in_dim = array.shape[dim]
        if in_dim >= out_dim:
            start_in = (in_dim - out_dim) // 2
            in_slices.append(slice(start_in, start_in + out_dim))
            out_slices.append(slice(0, out_dim))
        else:
            start_out = (out_dim - in_dim) // 2
            in_slices.append(slice(0, in_dim))
            out_slices.append(slice(start_out, start_out + in_dim))
    result[tuple(out_slices)] = array[tuple(in_slices)]
    return result
