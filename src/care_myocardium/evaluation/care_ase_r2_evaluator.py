"""Small first-party CARE-ASE R2 evaluator used by zero-credit probes."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage


REQUIRED_CARE_ASE_R2_METRICS = (
    "blood_pool_adjacent_fp",
    "casewise_help_harm",
    "centerB_centerC_subgroup",
    "component_count",
    "dice",
    "exact_hd",
    "hd95",
    "lesion_recall",
    "precision",
    "remote_fp_count",
    "remote_fp_volume",
    "sensitivity",
    "sentinel_case",
    "small_lesion_recall",
    "volume_ratio",
)


def _surface_distances_mm(a: np.ndarray, b: np.ndarray, spacing_zyx: tuple[float, float, float]) -> np.ndarray:
    a = np.asarray(a, dtype=bool)
    b = np.asarray(b, dtype=bool)
    if not a.any() or not b.any():
        return np.asarray([], dtype=np.float64)
    structure = ndimage.generate_binary_structure(3, 1)
    a_surface = a ^ ndimage.binary_erosion(a, structure=structure, border_value=0)
    b_surface = b ^ ndimage.binary_erosion(b, structure=structure, border_value=0)
    dt_b = ndimage.distance_transform_edt(~b_surface, sampling=spacing_zyx)
    dt_a = ndimage.distance_transform_edt(~a_surface, sampling=spacing_zyx)
    return np.concatenate([dt_b[a_surface], dt_a[b_surface]]).astype(np.float64, copy=False)


def _class_metrics(pred: np.ndarray, gt: np.ndarray, label: int, spacing_zyx: tuple[float, float, float]) -> dict[str, Any]:
    pred_mask = np.asarray(pred == int(label), dtype=bool)
    gt_mask = np.asarray(gt == int(label), dtype=bool)
    tp = int(np.logical_and(pred_mask, gt_mask).sum())
    fp = int(np.logical_and(pred_mask, ~gt_mask).sum())
    fn = int(np.logical_and(~pred_mask, gt_mask).sum())
    pred_count = int(pred_mask.sum())
    gt_count = int(gt_mask.sum())
    denom = pred_count + gt_count
    dice = 1.0 if denom == 0 else (2.0 * tp) / float(denom)
    precision = 1.0 if pred_count == 0 else tp / float(pred_count)
    sensitivity = 1.0 if gt_count == 0 else tp / float(gt_count)
    distances = _surface_distances_mm(pred_mask, gt_mask, spacing_zyx)
    exact_hd = None if distances.size == 0 else float(distances.max())
    hd95 = None if distances.size == 0 else float(np.percentile(distances, 95.0))
    gt_components, gt_n = ndimage.label(gt_mask)
    pred_components, pred_n = ndimage.label(pred_mask)
    recalled = 0
    small_total = 0
    small_recalled = 0
    voxel_volume = float(np.prod(np.asarray(spacing_zyx, dtype=np.float64)))
    for comp_id in range(1, int(gt_n) + 1):
        comp = gt_components == comp_id
        hit = bool(np.logical_and(comp, pred_mask).any())
        recalled += int(hit)
        if float(comp.sum()) * voxel_volume < 1000.0:
            small_total += 1
            small_recalled += int(hit)
    remote_fp = 0
    if fp:
        gt_dilated = ndimage.binary_dilation(gt_mask, iterations=2)
        remote_fp = int(np.logical_and(pred_mask, ~gt_dilated).sum())
    blood_pool = np.asarray(gt == 2, dtype=bool)
    blood_adjacent = ndimage.binary_dilation(blood_pool, iterations=1) if blood_pool.any() else np.zeros_like(pred_mask)
    return {
        "dice": float(dice),
        "hd95": hd95,
        "exact_hd": exact_hd,
        "precision": float(precision),
        "sensitivity": float(sensitivity),
        "lesion_recall": 1.0 if gt_n == 0 else recalled / float(gt_n),
        "small_lesion_recall": 1.0 if small_total == 0 else small_recalled / float(small_total),
        "component_count": int(pred_n),
        "remote_fp_count": int(remote_fp > 0),
        "remote_fp_volume": float(remote_fp) * voxel_volume,
        "blood_pool_adjacent_fp": int(np.logical_and(pred_mask, blood_adjacent).sum()),
        "volume_ratio": 1.0 if gt_count == 0 else pred_count / float(gt_count),
    }


def evaluate_care_ase_r2_prediction_pair(
    *,
    case_id: str,
    care_prediction: np.ndarray,
    baseline_prediction: np.ndarray,
    ground_truth: np.ndarray,
    availability: tuple[float, float, float],
    spacing_zyx: tuple[float, float, float],
    tta: str,
    decode: str,
    center: str,
) -> dict[str, Any]:
    """Evaluate CARE and baseline arrays with identical population semantics."""

    care = np.asarray(care_prediction)
    baseline = np.asarray(baseline_prediction)
    gt = np.asarray(ground_truth)
    if care.shape != baseline.shape or care.shape != gt.shape:
        raise ValueError(f"prediction/ground-truth shape mismatch: care={care.shape} baseline={baseline.shape} gt={gt.shape}")
    labels = [5]
    if float(availability[1]) > 0.5:
        labels.append(4)
    care_by_label = {str(label): _class_metrics(care, gt, label, spacing_zyx) for label in labels}
    baseline_by_label = {str(label): _class_metrics(baseline, gt, label, spacing_zyx) for label in labels}
    care_dice = float(np.mean([row["dice"] for row in care_by_label.values()])) if care_by_label else 1.0
    baseline_dice = float(np.mean([row["dice"] for row in baseline_by_label.values()])) if baseline_by_label else 1.0
    return {
        "case_id": str(case_id),
        "same_case_population": True,
        "same_tta": str(tta),
        "same_decode": str(decode),
        "same_metric_population": labels,
        "care": care_by_label,
        "baseline": baseline_by_label,
        "metrics": list(REQUIRED_CARE_ASE_R2_METRICS),
        "casewise_help_harm": "HELP" if care_dice > baseline_dice else ("HARM" if care_dice < baseline_dice else "NO_CHANGE"),
        "centerB_centerC_subgroup": str(center) in {"CenterB", "CenterC"},
        "sentinel_case": str(case_id),
    }

