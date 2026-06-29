"""Geometry utilities for proposal-conditioned soft ROI refinement."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage


@dataclass(frozen=True)
class ROIBox:
    starts: tuple[int, int, int]
    ends: tuple[int, int, int]
    original_shape: tuple[int, int, int]

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(e - s for s, e in zip(self.starts, self.ends))

    @property
    def volume(self) -> int:
        z, y, x = self.shape
        return int(z * y * x)

    def slices(self) -> tuple[slice, slice, slice]:
        return tuple(slice(s, e) for s, e in zip(self.starts, self.ends))  # type: ignore[return-value]


def _normalize_margin(margin: int | tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(margin, int):
        return (margin, margin, margin)
    if len(margin) != 3:
        raise ValueError("margin must be an int or a 3-tuple")
    return tuple(int(v) for v in margin)


def dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    mask = np.asarray(mask).astype(bool)
    if radius <= 0 or not bool(mask.any()):
        return mask
    structure = ndimage.generate_binary_structure(rank=3, connectivity=1)
    return ndimage.binary_dilation(mask, structure=structure, iterations=int(radius))


def box_from_mask(mask: np.ndarray, margin: int | tuple[int, int, int] = 0) -> ROIBox:
    mask = np.asarray(mask).astype(bool)
    if mask.ndim != 3:
        raise ValueError(f"mask must be 3D, got shape {mask.shape}")
    original_shape = tuple(int(v) for v in mask.shape)
    if not bool(mask.any()):
        return ROIBox((0, 0, 0), original_shape, original_shape)
    margin_zyx = _normalize_margin(margin)
    coords = np.argwhere(mask)
    starts = np.maximum(coords.min(axis=0) - np.asarray(margin_zyx), 0)
    ends = np.minimum(coords.max(axis=0) + np.asarray(margin_zyx) + 1, np.asarray(original_shape))
    return ROIBox(tuple(int(v) for v in starts), tuple(int(v) for v in ends), original_shape)


def build_candidate_mask(
    proposal_mask: np.ndarray,
    anatomy_mask: np.ndarray | None = None,
    proposal_dilation: int = 4,
    anatomy_dilation: int = 2,
) -> tuple[np.ndarray, str]:
    """Build a context-preserving ROI mask without hard-deleting distant evidence."""

    proposal = dilate_mask(proposal_mask, proposal_dilation)
    if bool(proposal.any()):
        if anatomy_mask is not None and bool(np.asarray(anatomy_mask).any()):
            anatomy = dilate_mask(anatomy_mask, anatomy_dilation)
            return proposal | anatomy, "proposal_plus_anatomy"
        return proposal, "proposal_only"
    if anatomy_mask is not None and bool(np.asarray(anatomy_mask).any()):
        return dilate_mask(anatomy_mask, anatomy_dilation), "anatomy_fallback"
    return np.ones_like(np.asarray(proposal_mask), dtype=bool), "full_volume_fallback"


def extract_roi(array: np.ndarray, box: ROIBox) -> np.ndarray:
    arr = np.asarray(array)
    if arr.shape[-3:] != box.original_shape:
        raise ValueError(f"array trailing shape {arr.shape[-3:]} does not match ROI original shape {box.original_shape}")
    return arr[(..., *box.slices())]


def restore_roi(crop: np.ndarray, box: ROIBox, fill_value: float | int = 0) -> np.ndarray:
    crop_arr = np.asarray(crop)
    prefix = crop_arr.shape[:-3]
    if crop_arr.shape[-3:] != box.shape:
        raise ValueError(f"crop trailing shape {crop_arr.shape[-3:]} does not match ROI shape {box.shape}")
    restored = np.full((*prefix, *box.original_shape), fill_value, dtype=crop_arr.dtype)
    restored[(..., *box.slices())] = crop_arr
    return restored
