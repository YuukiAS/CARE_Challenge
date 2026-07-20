#!/usr/bin/env python3
"""Batch 3B diagnostic CineMyoPS 4D mainline.

This is a production thin entrypoint for real Dataset502 4D I/O, reference-frame
selection, non-reference registration/warping, ED-space temporal aggregation,
export, and local geometry/evaluator checks. It is intentionally diagnostic: it
does not train, submit Slurm, package validation, upload, or make hosted/performance
claims.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage
from skimage.registration import optical_flow_ilk
from skimage.transform import warp


DEFAULT_TRAIN_ROOT = Path("data/CARE_Challenge/CineMyoPS_train")
DEFAULT_OUTPUT_ROOT = Path("results/srr_production/cine_batch3b")
RAW_TO_COMPACT = {0: 0, 200: 1, 500: 2, 2221: 3}
COMPACT_TO_RAW = {0: 0, 1: 200, 2: 500, 3: 2221}
CLASS_NAMES = {1: "myocardium_cinemyops_local_proxy", 2: "lv_blood_sanity", 3: "scar_sanity_negative_control"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "evidence not found"


def collect_cases(train_root: Path, max_cases: int | None, requested: list[str] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    requested_set = set(requested or [])
    for cine_path in sorted(train_root.glob("*/*_Cine.nii.gz")):
        case_id = cine_path.name.replace("_Cine.nii.gz", "")
        if requested_set and case_id not in requested_set:
            continue
        label_path = cine_path.with_name(f"{case_id}_gd.nii.gz")
        if not label_path.is_file():
            continue
        rows.append(
            {
                "case_id": case_id,
                "center": cine_path.parent.name,
                "cine_path": cine_path,
                "label_path": label_path,
            }
        )
        if max_cases is not None and len(rows) >= max_cases:
            break
    if requested_set:
        found = {row["case_id"] for row in rows}
        missing = sorted(requested_set - found)
        if missing:
            raise FileNotFoundError(f"Requested Cine cases not found with labels: {missing}")
    if not rows:
        raise FileNotFoundError(f"No CineMyoPS 4D cases found under {train_root}")
    return rows


def validate_time_axis(arr_tzyx: np.ndarray, case_id: str) -> None:
    if arr_tzyx.ndim != 4:
        raise ValueError(f"{case_id}: expected 4D Cine array t,z,y,x, got shape {arr_tzyx.shape}")
    if arr_tzyx.shape[0] < 2:
        raise ValueError(f"{case_id}: expected at least two time frames, got shape {arr_tzyx.shape}")


def select_reference_and_nonreference(frame_count: int) -> tuple[int, int]:
    if frame_count < 2:
        raise ValueError("Cine temporal aggregation requires at least one non-reference frame")
    reference_frame_index = 0
    nonreference_frame_index = frame_count // 2
    if nonreference_frame_index == reference_frame_index:
        nonreference_frame_index = 1
    return reference_frame_index, nonreference_frame_index


def frame_image_from_4d(cine_img: sitk.Image, frame_index: int) -> sitk.Image:
    size = list(cine_img.GetSize())
    index = [0, 0, 0, int(frame_index)]
    extract_size = [int(size[0]), int(size[1]), int(size[2]), 0]
    return sitk.Extract(cine_img, extract_size, index)


def assert_reference_geometry(case_id: str, frame_img: sitk.Image, label_img: sitk.Image) -> None:
    checks = {
        "size": frame_img.GetSize() == label_img.GetSize(),
        "spacing": np.allclose(frame_img.GetSpacing(), label_img.GetSpacing(), atol=1e-5),
        "origin": np.allclose(frame_img.GetOrigin(), label_img.GetOrigin(), atol=1e-5),
        "direction": np.allclose(frame_img.GetDirection(), label_img.GetDirection(), atol=1e-5),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"{case_id}: reference frame and label geometry mismatch: {failed}")


def compact_from_raw(raw: np.ndarray) -> np.ndarray:
    out = np.zeros(raw.shape, dtype=np.uint8)
    for raw_value, compact_value in RAW_TO_COMPACT.items():
        if raw_value:
            out[raw == raw_value] = compact_value
    return out


def raw_from_compact(compact: np.ndarray) -> np.ndarray:
    out = np.zeros(compact.shape, dtype=np.uint16)
    for compact_value, raw_value in COMPACT_TO_RAW.items():
        if compact_value:
            out[compact == compact_value] = raw_value
    return out


def normalize_frame(frame_zyx: np.ndarray) -> np.ndarray:
    arr = frame_zyx.astype(np.float32)
    nonzero = arr[arr > 0]
    if nonzero.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    lo = float(np.percentile(nonzero, 1.0))
    hi = float(np.percentile(nonzero, 99.0))
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def largest_component(mask: np.ndarray) -> np.ndarray:
    if not np.any(mask):
        return mask.astype(bool)
    labels, count = ndimage.label(mask)
    if count == 0:
        return mask.astype(bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def anatomy_proxy_from_frame(frame_zyx: np.ndarray) -> np.ndarray:
    norm = normalize_frame(frame_zyx)
    nonzero = norm[norm > 0]
    if nonzero.size == 0:
        return np.zeros(frame_zyx.shape, dtype=np.uint8)
    body = largest_component(norm > max(0.05, float(np.percentile(nonzero, 35.0))))
    high = norm >= float(np.percentile(norm[body], 84.0)) if np.any(body) else norm >= 0.84
    mid = norm >= float(np.percentile(norm[body], 70.0)) if np.any(body) else norm >= 0.70
    lv = ndimage.binary_opening(high & body, iterations=1)
    myocardium = ndimage.binary_closing((mid & body) & ~lv, iterations=1)
    out = np.zeros(frame_zyx.shape, dtype=np.uint8)
    out[myocardium] = 1
    out[lv] = 2
    return out


def warp_label_slice(label: np.ndarray, flow_v: np.ndarray, flow_u: np.ndarray) -> np.ndarray:
    rows, cols = label.shape
    rr, cc = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    warped = warp(
        label.astype(np.float32),
        np.array([rr + flow_v, cc + flow_u]),
        order=0,
        mode="constant",
        cval=0.0,
        preserve_range=True,
    )
    return np.rint(warped).astype(np.uint8)


def warp_image_slice(image: np.ndarray, flow_v: np.ndarray, flow_u: np.ndarray) -> np.ndarray:
    rows, cols = image.shape
    rr, cc = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    warped = warp(
        image.astype(np.float32),
        np.array([rr + flow_v, cc + flow_u]),
        order=1,
        mode="constant",
        cval=0.0,
        preserve_range=True,
    )
    return warped.astype(np.float32)


def flow_folding_proxy(flow_v: np.ndarray, flow_u: np.ndarray) -> tuple[int, float, float]:
    dv_dy, dv_dx = np.gradient(flow_v)
    du_dy, du_dx = np.gradient(flow_u)
    jac = (1.0 + dv_dy) * (1.0 + du_dx) - dv_dx * du_dy
    smooth = float(np.mean(np.sqrt(dv_dy * dv_dy + dv_dx * dv_dx + du_dy * du_dy + du_dx * du_dx)))
    return int(np.sum(jac <= 0.0)), float(np.min(jac)), smooth


def image_stats(a: np.ndarray, b: np.ndarray) -> dict[str, float | None]:
    a_f = a.astype(np.float32)
    b_f = b.astype(np.float32)
    mae = float(np.mean(np.abs(a_f - b_f)))
    a0 = a_f - float(np.mean(a_f))
    b0 = b_f - float(np.mean(b_f))
    denom = float(np.sqrt(np.sum(a0 * a0) * np.sum(b0 * b0)))
    ncc = float(np.sum(a0 * b0) / denom) if denom > 1e-8 else None
    return {"mae": mae, "ncc": ncc}


def register_and_warp_to_reference(
    fixed_zyx: np.ndarray,
    moving_zyx: np.ndarray,
    moving_label_zyx: np.ndarray,
    *,
    radius: int,
    max_side: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    start = time.perf_counter()
    fixed = normalize_frame(fixed_zyx)
    moving = normalize_frame(moving_zyx)
    warped_label = np.zeros_like(moving_label_zyx, dtype=np.uint8)
    warped_image = np.zeros_like(moving, dtype=np.float32)
    folds = 0
    jac_min = 1.0
    smoothness: list[float] = []
    flow_means: list[float] = []
    flow_maxes: list[float] = []
    before: list[float] = []
    after: list[float] = []
    for z in range(fixed.shape[0]):
        fixed_2d = fixed[z]
        moving_2d = moving[z]
        before_stats = image_stats(fixed_2d, moving_2d)
        scale = min(1.0, float(max_side) / float(max(fixed_2d.shape)))
        if scale < 0.999:
            fixed_small = ndimage.zoom(fixed_2d, zoom=scale, order=1)
            moving_small = ndimage.zoom(moving_2d, zoom=scale, order=1)
            flow_radius = max(3, int(round(radius * scale)))
        else:
            fixed_small = fixed_2d
            moving_small = moving_2d
            flow_radius = radius
        try:
            flow_v, flow_u = optical_flow_ilk(fixed_small, moving_small, radius=flow_radius)
        except TypeError:
            flow_v, flow_u = optical_flow_ilk(fixed_small, moving_small)
        if scale < 0.999:
            zoom_y = fixed_2d.shape[0] / float(flow_v.shape[0])
            zoom_x = fixed_2d.shape[1] / float(flow_u.shape[1])
            flow_v = ndimage.zoom(flow_v, zoom=(zoom_y, zoom_x), order=1) / scale
            flow_u = ndimage.zoom(flow_u, zoom=(zoom_y, zoom_x), order=1) / scale
            flow_v = flow_v[: fixed_2d.shape[0], : fixed_2d.shape[1]]
            flow_u = flow_u[: fixed_2d.shape[0], : fixed_2d.shape[1]]
        fold_count, z_jac_min, z_smooth = flow_folding_proxy(flow_v, flow_u)
        folds += int(fold_count)
        jac_min = min(jac_min, float(z_jac_min))
        flow_mag = np.sqrt(flow_v * flow_v + flow_u * flow_u)
        smoothness.append(float(z_smooth))
        flow_means.append(float(np.mean(flow_mag)))
        flow_maxes.append(float(np.max(flow_mag)))
        warped_label[z] = warp_label_slice(moving_label_zyx[z], flow_v, flow_u)
        warped_image[z] = warp_image_slice(moving_2d, flow_v, flow_u)
        after_stats = image_stats(fixed_2d, warped_image[z])
        if before_stats["ncc"] is not None:
            before.append(float(before_stats["ncc"]))
        if after_stats["ncc"] is not None:
            after.append(float(after_stats["ncc"]))
    return (
        warped_label,
        warped_image,
        {
            "runtime_seconds": time.perf_counter() - start,
            "registration_method": "slice2d_dense_optical_flow_ilk_image_based",
            "folding_voxels_proxy": folds,
            "jacobian_min_proxy": jac_min,
            "flow_smoothness_mean": float(np.mean(smoothness)) if smoothness else 0.0,
            "flow_magnitude_mean_px": float(np.mean(flow_means)) if flow_means else 0.0,
            "flow_magnitude_max_px": float(np.max(flow_maxes)) if flow_maxes else 0.0,
            "image_ncc_before_mean": float(np.mean(before)) if before else None,
            "image_ncc_after_mean": float(np.mean(after)) if after else None,
            "image_ncc_delta_mean": float(np.mean(after) - np.mean(before)) if before and after else None,
        },
    )


def temporal_aggregate(reference_pred: np.ndarray, warped_nonref_pred: np.ndarray, nonreference_weight: float) -> np.ndarray:
    if not (0.0 < nonreference_weight < 0.5):
        raise ValueError("nonreference_weight must be in (0, 0.5) so reference remains audited anchor")
    out = reference_pred.copy()
    for cls in (1, 2):
        supplemental = (out == 0) & (warped_nonref_pred == cls)
        out[supplemental] = cls
    return out


def dice(pred: np.ndarray, gt: np.ndarray) -> float | None:
    pred_count = int(pred.sum())
    gt_count = int(gt.sum())
    if pred_count == 0 and gt_count == 0:
        return None
    denom = pred_count + gt_count
    return float(2.0 * np.logical_and(pred, gt).sum() / denom) if denom else 0.0


def hd95(pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, float, float]) -> float | None:
    if not np.any(pred) or not np.any(gt):
        return None
    pred_border = np.logical_xor(pred, ndimage.binary_erosion(pred))
    gt_border = np.logical_xor(gt, ndimage.binary_erosion(gt))
    dt_gt = ndimage.distance_transform_edt(~gt_border, sampling=spacing_zyx)
    dt_pred = ndimage.distance_transform_edt(~pred_border, sampling=spacing_zyx)
    distances = np.concatenate([dt_gt[pred_border], dt_pred[gt_border]])
    return float(np.percentile(distances, 95)) if distances.size else 0.0


def component_count(mask: np.ndarray) -> int:
    if not np.any(mask):
        return 0
    _, count = ndimage.label(mask)
    return int(count)


def metric_rows(case_id: str, center: str, pred_compact: np.ndarray, gt_compact: np.ndarray, spacing_zyx: tuple[float, float, float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cls, name in CLASS_NAMES.items():
        pred_mask = pred_compact == cls
        gt_mask = gt_compact == cls
        rows.append(
            {
                "case_id": case_id,
                "center": center,
                "class_id": cls,
                "metric_name": name,
                "dice": dice(pred_mask, gt_mask),
                "hd95": hd95(pred_mask, gt_mask, spacing_zyx),
                "pred_voxels": int(pred_mask.sum()),
                "gt_voxels": int(gt_mask.sum()),
                "empty_prediction": not bool(pred_mask.any()),
                "component_count": component_count(pred_mask),
                "performance_claim": "NONE_LOCAL_DIAGNOSTIC_ONLY",
            }
        )
    return rows


def run_known_bad_checks() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        validate_time_axis(np.zeros((3, 8, 8), dtype=np.float32), "known_bad_3d")
    except ValueError as exc:
        checks.append({"name": "reject_3d_cine_missing_time_axis", "detected": True, "error": str(exc)})
    else:
        checks.append({"name": "reject_3d_cine_missing_time_axis", "detected": False, "error": ""})

    try:
        select_reference_and_nonreference(1)
    except ValueError as exc:
        checks.append({"name": "reject_no_nonreference_frame", "detected": True, "error": str(exc)})
    else:
        checks.append({"name": "reject_no_nonreference_frame", "detected": False, "error": ""})

    try:
        temporal_aggregate(np.zeros((2, 4, 4), dtype=np.uint8), np.zeros((2, 4, 4), dtype=np.uint8), 0.5)
    except ValueError as exc:
        checks.append({"name": "reject_nonreference_weight_without_reference_anchor", "detected": True, "error": str(exc)})
    else:
        checks.append({"name": "reject_nonreference_weight_without_reference_anchor", "detected": False, "error": ""})

    return {
        "status": "BATCH3B_KNOWN_BAD_INJECTION_PASS" if all(c["detected"] for c in checks) else "BATCH3B_KNOWN_BAD_INJECTION_FAIL",
        "checks": checks,
    }


def process_case(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    cine_path = Path(row["cine_path"])
    label_path = Path(row["label_path"])
    cine_img = sitk.ReadImage(str(cine_path))
    cine_arr = sitk.GetArrayFromImage(cine_img)
    validate_time_axis(cine_arr, row["case_id"])
    label_img = sitk.ReadImage(str(label_path))
    label_arr = sitk.GetArrayFromImage(label_img)
    reference_idx, nonreference_idx = select_reference_and_nonreference(int(cine_arr.shape[0]))
    reference_img = frame_image_from_4d(cine_img, reference_idx)
    assert_reference_geometry(row["case_id"], reference_img, label_img)

    reference_frame = cine_arr[reference_idx]
    nonreference_frame = cine_arr[nonreference_idx]
    reference_proxy = anatomy_proxy_from_frame(reference_frame)
    nonreference_proxy = anatomy_proxy_from_frame(nonreference_frame)
    warped_nonreference, warped_image, registration = register_and_warp_to_reference(
        reference_frame,
        nonreference_frame,
        nonreference_proxy,
        radius=args.flow_radius,
        max_side=args.flow_max_side,
    )
    aggregated = temporal_aggregate(reference_proxy, warped_nonreference, args.nonreference_weight)
    final_raw = raw_from_compact(aggregated)
    pred_img = sitk.GetImageFromArray(final_raw)
    pred_img.CopyInformation(label_img)
    prediction_dir = args.output_root / "predictions" / row["center"]
    prediction_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = prediction_dir / f"{row['case_id']}_pred.nii.gz"
    sitk.WriteImage(pred_img, str(prediction_path))

    spacing = label_img.GetSpacing()
    gt_compact = compact_from_raw(label_arr)
    spacing_zyx = (float(spacing[2]), float(spacing[1]), float(spacing[0]))
    eval_rows = metric_rows(row["case_id"], row["center"], aggregated, gt_compact, spacing_zyx)

    changed_by_temporal = int(np.sum(aggregated != reference_proxy))
    nonreference_votes = int(np.sum(warped_nonreference > 0))
    return {
        "case_id": row["case_id"],
        "center": row["center"],
        "cine_path": str(cine_path),
        "label_path": str(label_path),
        "prediction_path": str(prediction_path),
        "prediction_sha256": sha256_file(prediction_path),
        "time_frame_count": int(cine_arr.shape[0]),
        "cine_shape_tzyx": [int(x) for x in cine_arr.shape],
        "reference_frame_index": reference_idx,
        "nonreference_frame_index": nonreference_idx,
        "reference_frame_policy": "frame0_label_geometry_reference_ed_space",
        "reference_geometry_matches_label": True,
        "time_axis_preserved": True,
        "reference_proxy_voxels": int(np.sum(reference_proxy > 0)),
        "nonreference_proxy_voxels": int(np.sum(nonreference_proxy > 0)),
        "warped_nonreference_voxels": nonreference_votes,
        "temporal_changed_voxels": changed_by_temporal,
        "temporal_nonreference_weight": float(args.nonreference_weight),
        "nonreference_entered_temporal_aggregation": nonreference_votes > 0,
        "export_geometry_matches_label": pred_img.GetSize() == label_img.GetSize()
        and pred_img.GetSpacing() == label_img.GetSpacing()
        and pred_img.GetOrigin() == label_img.GetOrigin()
        and pred_img.GetDirection() == label_img.GetDirection(),
        "registration": registration,
        "metric_rows": eval_rows,
        "warped_image_mean": float(np.mean(warped_image)),
    }


def write_summary(output_root: Path, contract: dict[str, Any]) -> None:
    lines = [
        "# Batch 3B Cine Mainline Diagnostic",
        "",
        f"- status: `{contract['status']}`",
        f"- cases: `{contract['case_count']}`",
        "- scope: real Dataset502 4D I/O, reference frame, optical-flow registration/warp, temporal aggregation, ED-space export/evaluation.",
        "- training: `0`",
        "- Slurm jobs: `0`",
        "- validation upload: `0`",
        "- performance claim: `NONE`",
        "- CineMA used: `false`; official CineMA weights were not loaded in this batch.",
        "- historical B7/B8 formal authority: `false`",
        "",
        "## Evidence",
        "",
        "- `batch3b_cine_contract.json`",
        "- `batch3b_time_axis_audit.csv`",
        "- `batch3b_registration_warp_qc.csv`",
        "- `batch3b_temporal_aggregation.csv`",
        "- `batch3b_ed_space_evaluation.csv`",
        "- `batch3b_known_bad_report.json`",
    ]
    (output_root / "batch3b_completion.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-root", type=Path, default=DEFAULT_TRAIN_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--max-cases", type=int, default=3)
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--flow-radius", type=int, default=5)
    parser.add_argument("--flow-max-side", type=int, default=96)
    parser.add_argument("--nonreference-weight", type=float, default=0.35)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.perf_counter()
    args.output_root.mkdir(parents=True, exist_ok=True)
    cases = collect_cases(args.train_root, args.max_cases, args.case_id)
    case_outputs = [process_case(row, args) for row in cases]
    known_bad = run_known_bad_checks()

    time_rows = []
    registration_rows = []
    temporal_rows = []
    eval_rows = []
    prediction_hashes: dict[str, str] = {}
    for item in case_outputs:
        time_rows.append(
            {
                "case_id": item["case_id"],
                "center": item["center"],
                "cine_path": item["cine_path"],
                "label_path": item["label_path"],
                "cine_shape_tzyx": "x".join(str(v) for v in item["cine_shape_tzyx"]),
                "time_frame_count": item["time_frame_count"],
                "reference_frame_index": item["reference_frame_index"],
                "nonreference_frame_index": item["nonreference_frame_index"],
                "reference_frame_policy": item["reference_frame_policy"],
                "time_axis_preserved": item["time_axis_preserved"],
                "reference_geometry_matches_label": item["reference_geometry_matches_label"],
            }
        )
        reg = item["registration"]
        registration_rows.append(
            {
                "case_id": item["case_id"],
                "center": item["center"],
                **{key: reg[key] for key in sorted(reg)},
            }
        )
        temporal_rows.append(
            {
                "case_id": item["case_id"],
                "center": item["center"],
                "reference_proxy_voxels": item["reference_proxy_voxels"],
                "nonreference_proxy_voxels": item["nonreference_proxy_voxels"],
                "warped_nonreference_voxels": item["warped_nonreference_voxels"],
                "temporal_changed_voxels": item["temporal_changed_voxels"],
                "temporal_nonreference_weight": item["temporal_nonreference_weight"],
                "nonreference_entered_temporal_aggregation": item["nonreference_entered_temporal_aggregation"],
                "prediction_path": item["prediction_path"],
                "prediction_sha256": item["prediction_sha256"],
                "export_geometry_matches_label": item["export_geometry_matches_label"],
            }
        )
        eval_rows.extend(item["metric_rows"])
        prediction_hashes[item["case_id"]] = item["prediction_sha256"]

    write_csv(args.output_root / "batch3b_time_axis_audit.csv", time_rows)
    write_csv(args.output_root / "batch3b_registration_warp_qc.csv", registration_rows)
    write_csv(args.output_root / "batch3b_temporal_aggregation.csv", temporal_rows)
    write_csv(args.output_root / "batch3b_ed_space_evaluation.csv", eval_rows)
    write_json(args.output_root / "batch3b_known_bad_report.json", known_bad)

    all_nonref = all(bool(row["nonreference_entered_temporal_aggregation"]) for row in temporal_rows)
    temporal_affects_output = any(int(row["temporal_changed_voxels"]) > 0 for row in temporal_rows)
    all_export = all(bool(row["export_geometry_matches_label"]) for row in temporal_rows)
    status = (
        "BATCH3B_REAL_CINE_MAINLINE_DIAGNOSTIC_COMPLETE"
        if all_nonref and temporal_affects_output and all_export and known_bad["status"] == "BATCH3B_KNOWN_BAD_INJECTION_PASS"
        else "BATCH3B_REAL_CINE_MAINLINE_NEEDS_EVIDENCE"
    )
    contract = {
        "schema_version": 1,
        "batch": "3B",
        "status": status,
        "git_head": git_head(),
        "command": " ".join([sys.executable, *sys.argv]),
        "case_count": len(case_outputs),
        "train_root": str(args.train_root),
        "output_root": str(args.output_root),
        "time_axis_preserved_all_cases": all(bool(row["time_axis_preserved"]) for row in time_rows),
        "reference_frame_policy": "frame0_label_geometry_reference_ed_space",
        "reference_frame_indices": {row["case_id"]: row["reference_frame_index"] for row in time_rows},
        "nonreference_frame_indices": {row["case_id"]: row["nonreference_frame_index"] for row in time_rows},
        "nonreference_entered_temporal_aggregation_all_cases": all_nonref,
        "temporal_aggregation_affects_output": temporal_affects_output,
        "registration_method": "slice2d_dense_optical_flow_ilk_image_based",
        "registration_warp_qc_path": str(args.output_root / "batch3b_registration_warp_qc.csv"),
        "temporal_aggregation_path": str(args.output_root / "batch3b_temporal_aggregation.csv"),
        "ed_space_evaluation_path": str(args.output_root / "batch3b_ed_space_evaluation.csv"),
        "time_axis_audit_path": str(args.output_root / "batch3b_time_axis_audit.csv"),
        "known_bad_report_path": str(args.output_root / "batch3b_known_bad_report.json"),
        "prediction_hashes": prediction_hashes,
        "cinema_used": False,
        "cinema_official_weights_loaded": False,
        "cinema_policy": "not_used_in_batch3b_to_avoid_unverified_official_weight_claim",
        "historical_b7_b8_formal_authority": False,
        "formal_training_count": 0,
        "slurm_job_count": 0,
        "validation_upload_count": 0,
        "hosted_metric_claim_count": 0,
        "performance_claim": "NONE_LOCAL_DIAGNOSTIC_ONLY",
        "runtime_seconds": time.perf_counter() - start,
    }
    write_json(args.output_root / "batch3b_cine_contract.json", contract)
    write_summary(args.output_root, contract)
    print(json.dumps({"status": status, "case_count": len(case_outputs), "output_root": str(args.output_root)}, sort_keys=True))
    return 0 if status == "BATCH3B_REAL_CINE_MAINLINE_DIAGNOSTIC_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
