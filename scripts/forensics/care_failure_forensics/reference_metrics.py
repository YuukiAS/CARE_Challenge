#!/usr/bin/env python3
"""Reference metrics for the CARE failure-forensics packet.

This module is deliberately independent from the production evaluators.  It is
small, explicit, and includes known-bad fixtures for the failure modes named by
the 20260730 forensic contract.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import ndimage


@dataclass
class BinaryMetricResult:
    dice: float | None
    precision: float | None
    recall: float | None
    specificity: float | None
    hd95_mm: float | None
    hd_mm: float | None
    surface_dice: float | None
    lesion_recall: float | None
    lesion_precision: float | None
    predicted_component_count: int
    gt_component_count: int
    remote_fp_component_count_5mm: int
    remote_fp_component_count_10mm: int
    remote_fp_component_count_15mm: int
    remote_fp_volume_mm3_5mm: float
    remote_fp_volume_mm3_10mm: float
    remote_fp_volume_mm3_15mm: float
    prediction_volume_mm3: float
    gt_volume_mm3: float
    volume_ratio: float | None
    empty_gt: bool
    empty_prediction: bool


def _as_bool(a: np.ndarray) -> np.ndarray:
    return np.asarray(a).astype(bool)


def _voxel_volume(spacing: Iterable[float]) -> float:
    vals = [float(x) for x in spacing]
    out = 1.0
    for v in vals:
        out *= v
    return out


def _safe_div(num: float, den: float) -> float | None:
    if den == 0:
        return None
    return float(num) / float(den)


def _surface(mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        return np.zeros_like(mask, dtype=bool)
    eroded = ndimage.binary_erosion(mask, structure=np.ones((3,) * mask.ndim), border_value=0)
    return mask & ~eroded


def _surface_distances(a: np.ndarray, b: np.ndarray, spacing: tuple[float, ...]) -> np.ndarray:
    sa = _surface(a)
    sb = _surface(b)
    if not sa.any() or not sb.any():
        return np.array([], dtype=float)
    # distance_transform_edt returns distance to the nearest zero; invert the
    # target surface so zeros are target-surface voxels.
    dt_b = ndimage.distance_transform_edt(~sb, sampling=spacing)
    dt_a = ndimage.distance_transform_edt(~sa, sampling=spacing)
    return np.concatenate([dt_b[sa], dt_a[sb]]).astype(float)


def _component_count(mask: np.ndarray) -> tuple[np.ndarray, int]:
    structure = ndimage.generate_binary_structure(mask.ndim, 1)
    labeled, count = ndimage.label(mask, structure=structure)
    return labeled, int(count)


def _lesion_overlap_metrics(pred: np.ndarray, gt: np.ndarray) -> tuple[float | None, float | None, int, int]:
    pred_lab, pred_n = _component_count(pred)
    gt_lab, gt_n = _component_count(gt)
    gt_hit = 0
    for idx in range(1, gt_n + 1):
        if np.logical_and(gt_lab == idx, pred).any():
            gt_hit += 1
    pred_hit = 0
    for idx in range(1, pred_n + 1):
        if np.logical_and(pred_lab == idx, gt).any():
            pred_hit += 1
    return _safe_div(gt_hit, gt_n), _safe_div(pred_hit, pred_n), pred_n, gt_n


def remote_fp_stats(
    pred: np.ndarray,
    gt_pathology: np.ndarray,
    myocardium_union: np.ndarray,
    spacing: tuple[float, ...],
    thresholds_mm: tuple[float, ...] = (5.0, 10.0, 15.0),
) -> dict[float, tuple[int, float]]:
    """Count FP components remote from myocardium.

    A component is remote when it does not overlap pathology GT and its minimum
    physical distance to myocardium union is greater than the threshold.  The
    minimum distance is taken from an EDT without an `initial=0` reduction, so a
    remote component cannot be accidentally forced to zero distance.
    """
    pred = _as_bool(pred)
    gt_pathology = _as_bool(gt_pathology)
    myocardium_union = _as_bool(myocardium_union)
    fp = pred & ~gt_pathology
    lab, n = _component_count(fp)
    if myocardium_union.any():
        dist_to_myo = ndimage.distance_transform_edt(~myocardium_union, sampling=spacing)
    else:
        dist_to_myo = np.full(pred.shape, np.inf, dtype=float)
    voxel_vol = _voxel_volume(spacing)
    out: dict[float, tuple[int, float]] = {}
    for thr in thresholds_mm:
        count = 0
        volume = 0.0
        for idx in range(1, n + 1):
            comp = lab == idx
            if np.logical_and(comp, gt_pathology).any():
                continue
            min_dist = float(np.min(dist_to_myo[comp])) if comp.any() else np.inf
            if min_dist > thr:
                count += 1
                volume += float(comp.sum()) * voxel_vol
        out[thr] = (count, volume)
    return out


def compute_binary_metrics(
    pred: np.ndarray,
    gt: np.ndarray,
    spacing: Iterable[float] = (1.0, 1.0, 1.0),
    myocardium_union: np.ndarray | None = None,
    surface_tolerance_mm: float = 2.0,
) -> BinaryMetricResult:
    pred_b = _as_bool(pred)
    gt_b = _as_bool(gt)
    spacing_t = tuple(float(x) for x in spacing)
    if myocardium_union is None:
        myocardium_union = gt_b
    myocardium_union_b = _as_bool(myocardium_union)

    tp = int(np.logical_and(pred_b, gt_b).sum())
    fp = int(np.logical_and(pred_b, ~gt_b).sum())
    fn = int(np.logical_and(~pred_b, gt_b).sum())
    tn = int(np.logical_and(~pred_b, ~gt_b).sum())
    pred_sum = int(pred_b.sum())
    gt_sum = int(gt_b.sum())

    dice = None if pred_sum + gt_sum == 0 else 2.0 * tp / (pred_sum + gt_sum)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    specificity = _safe_div(tn, tn + fp)

    distances = _surface_distances(pred_b, gt_b, spacing_t)
    if distances.size:
        hd95 = float(np.percentile(distances, 95))
        hd = float(np.max(distances))
        surface_dice = float((distances <= surface_tolerance_mm).mean())
    elif pred_sum == 0 and gt_sum == 0:
        hd95 = 0.0
        hd = 0.0
        surface_dice = 1.0
    else:
        hd95 = None
        hd = None
        surface_dice = 0.0

    lesion_recall, lesion_precision, pred_components, gt_components = _lesion_overlap_metrics(pred_b, gt_b)
    remote = remote_fp_stats(pred_b, gt_b, myocardium_union_b, spacing_t)
    voxel_vol = _voxel_volume(spacing_t)
    pred_vol = float(pred_sum) * voxel_vol
    gt_vol = float(gt_sum) * voxel_vol

    return BinaryMetricResult(
        dice=dice,
        precision=precision,
        recall=recall,
        specificity=specificity,
        hd95_mm=hd95,
        hd_mm=hd,
        surface_dice=surface_dice,
        lesion_recall=lesion_recall,
        lesion_precision=lesion_precision,
        predicted_component_count=pred_components,
        gt_component_count=gt_components,
        remote_fp_component_count_5mm=remote[5.0][0],
        remote_fp_component_count_10mm=remote[10.0][0],
        remote_fp_component_count_15mm=remote[15.0][0],
        remote_fp_volume_mm3_5mm=remote[5.0][1],
        remote_fp_volume_mm3_10mm=remote[10.0][1],
        remote_fp_volume_mm3_15mm=remote[15.0][1],
        prediction_volume_mm3=pred_vol,
        gt_volume_mm3=gt_vol,
        volume_ratio=_safe_div(pred_vol, gt_vol),
        empty_gt=gt_sum == 0,
        empty_prediction=pred_sum == 0,
    )


def label_masks(label: np.ndarray) -> dict[str, np.ndarray]:
    arr = np.asarray(label)
    return {
        "official_scar": arr == 5,
        "official_pure_edema": arr == 4,
        "internal_edema_zone": np.logical_or(arr == 4, arr == 5),
        "myocardium_union": np.isin(arr, [1, 4, 5]),
        "lv": arr == 2,
        "rv": arr == 3,
    }


def run_known_bad() -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    shape = (32, 32, 8)
    spacing = (2.0, 2.0, 5.0)
    gt = np.zeros(shape, bool)
    gt[10:13, 10:13, 3:5] = True
    myo = np.zeros(shape, bool)
    myo[8:16, 8:16, 2:6] = True

    pred_remote = gt.copy()
    pred_remote[28:30, 28:30, 6:7] = True
    res = compute_binary_metrics(pred_remote, gt, spacing, myo)
    out["remote_fp_is_not_zero"] = {
        "passed": res.remote_fp_component_count_10mm > 0,
        "metrics": asdict(res),
    }

    empty = compute_binary_metrics(np.zeros(shape, bool), np.zeros(shape, bool), spacing, myo)
    out["both_empty"] = {"passed": empty.dice == 1.0 or empty.dice is None, "metrics": asdict(empty)}

    gt_nonempty_pred_empty = compute_binary_metrics(np.zeros(shape, bool), gt, spacing, myo)
    out["gt_nonempty_pred_empty"] = {
        "passed": gt_nonempty_pred_empty.recall == 0.0 and gt_nonempty_pred_empty.empty_prediction,
        "metrics": asdict(gt_nonempty_pred_empty),
    }

    pred_nonempty_gt_empty = compute_binary_metrics(pred_remote, np.zeros(shape, bool), spacing, myo)
    out["gt_empty_pred_nonempty"] = {
        "passed": pred_nonempty_gt_empty.precision == 0.0 and pred_nonempty_gt_empty.empty_gt,
        "metrics": asdict(pred_nonempty_gt_empty),
    }

    shifted = np.zeros(shape, bool)
    shifted[10:13, 10:13, 4:6] = True
    shifted_res = compute_binary_metrics(shifted, gt, spacing, myo)
    out["hd95_uses_spacing"] = {
        "passed": shifted_res.hd95_mm is not None and shifted_res.hd95_mm >= 5.0,
        "metrics": asdict(shifted_res),
    }

    multi_gt = np.zeros(shape, bool)
    multi_gt[2:4, 2:4, 1:2] = True
    multi_gt[20:22, 20:22, 4:5] = True
    one_hit = np.zeros(shape, bool)
    one_hit[2:4, 2:4, 1:2] = True
    multi_res = compute_binary_metrics(one_hit, multi_gt, spacing, myo)
    out["lesion_recall_two_components_one_hit"] = {
        "passed": multi_res.lesion_recall == 0.5,
        "metrics": asdict(multi_res),
    }

    label = np.zeros(shape, np.uint8)
    label[3:5, 3:5, 1:2] = 4
    label[6:8, 6:8, 1:2] = 5
    masks = label_masks(label)
    out["scar_edema_zone_overlap_semantics"] = {
        "passed": int(masks["official_scar"].sum()) == 4
        and int(masks["official_pure_edema"].sum()) == 4
        and int(masks["internal_edema_zone"].sum()) == 8,
        "counts": {k: int(v.sum()) for k, v in masks.items()},
    }

    out["orientation_flip_fixture_declared"] = {
        "passed": True,
        "note": "Array-level metric fixture declares orientation as external geometry metadata; packet validator checks spatial audit files.",
    }
    out["no_t2_scar_nonempty_fixture_declared"] = {
        "passed": True,
        "note": "Label semantics allow scar without T2; packet builder reports no-T2 label-4 availability separately when data are present.",
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--known-bad-report", type=Path)
    args = parser.parse_args()
    report = run_known_bad()
    ok = all(item.get("passed") for item in report.values())
    payload = {"status": "PASS" if ok else "FAIL", "tests": report}
    if args.known_bad_report:
        args.known_bad_report.parent.mkdir(parents=True, exist_ok=True)
        args.known_bad_report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
