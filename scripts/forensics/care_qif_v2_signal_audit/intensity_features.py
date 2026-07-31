#!/usr/bin/env python3
"""Deterministic intensity features for CARE-QIF v2 Fact A."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_qif_v2_signal_audit.common import (  # noqa: E402
    HEALTHY_MYO_LABEL,
    INJURY_LABELS,
    LV_LABEL,
    MYO_UNION_LABELS,
    PURE_EDEMA_LABEL,
    SCAR_LABEL,
    feature_cache_path,
    load_image,
    load_seg,
    spacing_zyx,
)


_FEATURE_VOLUME_CACHE: dict[tuple[str, str, str, str], tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]] = {}


def _radius_to_size(radius_mm: float, spacing: tuple[float, float, float]) -> tuple[int, int, int]:
    sizes = []
    for sp in spacing:
        vox = max(1, int(round(radius_mm / max(float(sp), 1.0e-6))))
        sizes.append(2 * vox + 1)
    return tuple(sizes)  # type: ignore[return-value]


def _safe_support(mask: np.ndarray) -> np.ndarray:
    mask = mask.astype(bool)
    if mask.sum() < 16:
        return np.ones_like(mask, dtype=bool)
    return mask


def percentile_rank(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    support = _safe_support(support)
    ref = values[support].astype(np.float32)
    order = np.sort(ref)
    flat = values.reshape(-1)
    ranks = np.searchsorted(order, flat, side="right").astype(np.float32) / max(len(order), 1)
    return ranks.reshape(values.shape).astype(np.float32)


def robust_z(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    support = _safe_support(support)
    ref = values[support].astype(np.float32)
    med = float(np.median(ref))
    mad = float(np.median(np.abs(ref - med)))
    return ((values.astype(np.float32) - med) / (1.4826 * mad + 1.0e-6)).astype(np.float32)


def local_contrast(values: np.ndarray, spacing: tuple[float, float, float], radius_mm: float) -> np.ndarray:
    size = _radius_to_size(radius_mm, spacing)
    med = ndimage.median_filter(values.astype(np.float32), size=size, mode="nearest")
    return (values.astype(np.float32) - med).astype(np.float32)


def gradient_magnitude(values: np.ndarray, spacing: tuple[float, float, float]) -> np.ndarray:
    arr = values.astype(np.float32)
    out = np.zeros_like(values, dtype=np.float32)
    for axis, sp in enumerate(spacing):
        if arr.shape[axis] < 2:
            continue
        grad = np.gradient(arr, float(sp), axis=axis)
        out += grad.astype(np.float32) ** 2
    return np.sqrt(out).astype(np.float32)


def distance_features(myo_support: np.ndarray, lv_support: np.ndarray, spacing: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray]:
    myo = _safe_support(myo_support)
    lv = lv_support.astype(bool)
    if lv.sum() < 8:
        lv = np.zeros_like(myo, dtype=bool)
    dist_endo = ndimage.distance_transform_edt(~lv, sampling=spacing).astype(np.float32) if lv.any() else np.full(myo.shape, 999.0, dtype=np.float32)
    dist_epi = ndimage.distance_transform_edt(myo, sampling=spacing).astype(np.float32)
    return dist_endo, dist_epi


def load_deployable_context(case_id: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    path = feature_cache_path(case_id)
    if not path.exists():
        raise FileNotFoundError(f"deployable feature cache missing for {case_id}: {path}")
    data = np.load(path)
    return data["p_myo"].astype(np.float32), data["p_lv"].astype(np.float32), data["stock_scar_prob"].astype(np.float32)


def feature_volume(case_id: str, *, target: str, context: str, model: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    key = (case_id, target, context, model)
    if key in _FEATURE_VOLUME_CACHE:
        return _FEATURE_VOLUME_CACHE[key]
    image = load_image(case_id)
    seg = load_seg(case_id)
    spacing = spacing_zyx(case_id)
    channel_idx = 0 if target == "scar" else 1
    values = image[channel_idx].astype(np.float32)
    if context == "GT_CONTEXT":
        myo_support = np.isin(seg, list(MYO_UNION_LABELS))
        lv_support = seg == LV_LABEL
    elif context == "DEPLOYABLE_CONTEXT":
        p_myo, p_lv, _stock = load_deployable_context(case_id)
        myo_support = p_myo >= 0.50
        lv_support = p_lv >= 0.50
    else:
        raise ValueError(f"unknown context {context}")

    if target == "scar":
        positive = seg == SCAR_LABEL
        negative = seg == HEALTHY_MYO_LABEL
        raw_name = "lge_raw_nnunet_normalized"
        extra = []
        blood = values[seg == LV_LABEL]
        blood_med = float(np.median(blood)) if blood.size else 0.0
        blood_mad = float(np.median(np.abs(blood - blood_med))) if blood.size else 0.0
        extra.append(((values - blood_med) / (1.4826 * blood_mad + 1.0e-6)).astype(np.float32))
    elif target == "injury":
        positive = np.isin(seg, list(INJURY_LABELS))
        negative = seg == HEALTHY_MYO_LABEL
        raw_name = "t2_raw_nnunet_normalized"
        extra = []
    else:
        raise ValueError(f"unknown target {target}")

    valid = positive | negative
    base_meta = {
        "case_id": case_id,
        "target": target,
        "context": context,
        "model": model,
        "valid_voxels": int(valid.sum()),
        "positive_voxels": int(positive.sum()),
        "negative_voxels": int(negative.sum()),
        "t2_present": bool(np.abs(image[1]).max() > 1.0e-6),
        "pure_edema_positive_voxels": int((seg == PURE_EDEMA_LABEL).sum()),
    }
    if model == "raw":
        out = (
            values[..., None].astype(np.float32),
            positive.astype(np.uint8),
            valid,
            {**base_meta, "feature_names": [raw_name]},
        )
        _FEATURE_VOLUME_CACHE[key] = out
        return out

    rank = percentile_rank(values, myo_support)
    rz = robust_z(values, myo_support)
    contrast3 = local_contrast(values, spacing, 3.0)
    contrast6 = local_contrast(values, spacing, 6.0)
    grad = gradient_magnitude(values, spacing)
    d_endo, d_epi = distance_features(myo_support, lv_support, spacing)
    if model == "rank_composite":
        features = [rank, rz, contrast3, contrast6, grad, *extra, d_endo, d_epi]
        names = ["rank", "robust_z", "contrast3", "contrast6", "gradient"]
        if extra:
            names.append("blood_pool_relative_z")
        names.extend(["soft_distance_to_endocardium", "soft_distance_to_epicardium"])
    else:
        raise ValueError(f"unknown model {model}")
    x = np.stack(features, axis=-1).astype(np.float32)
    y = positive.astype(np.uint8)
    meta = {
        **base_meta,
        "feature_names": names,
    }
    out = (x, y, valid, meta)
    _FEATURE_VOLUME_CACHE[key] = out
    return out
