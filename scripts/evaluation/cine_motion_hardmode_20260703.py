#!/usr/bin/env python3
"""CineMyoPS hardmode temporal/motion proxy evaluation for 20260703."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage
from skimage.registration import optical_flow_ilk
from skimage.transform import warp


DEFAULT_SAFE_CASES = Path("results/20260625_cine_geometry/safe_cases.csv")
DEFAULT_MISMATCH_CASES = Path("results/20260625_cine_geometry/mismatch_cases.csv")
DEFAULT_ADAPTER_METRICS = Path("results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv")
DEFAULT_OUTPUT_DIR = Path("results/20260703_cine_motion")
DEFAULT_CINEMA_REPO = Path("results/cinema_adapter/external/CineMA")
DEFAULT_CINEMA_RUN_INFO = Path("results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/run_info.json")
DEFAULT_TASK_KEY = "20260703_cine_motion"
DEFAULT_CONTROLLER_TASK_KEY = "20260703_hardmode_goal"

CLASS_NAMES = {
    1: "class_1_myocardium",
    2: "class_2_lv",
    3: "class_3_scar_sanity",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def finite_values(values: list[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        if value in (None, "", "NA"):
            continue
        try:
            val = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(val):
            out.append(val)
    return out


def finite_mean(values: list[Any]) -> float | None:
    vals = finite_values(values)
    return float(np.mean(vals)) if vals else None


def finite_median(values: list[Any]) -> float | None:
    vals = finite_values(values)
    return float(np.median(vals)) if vals else None


def compact_gt(raw: np.ndarray) -> np.ndarray:
    out = np.zeros(raw.shape, dtype=np.uint8)
    out[raw == 200] = 1
    out[raw == 500] = 2
    out[raw == 2221] = 3
    return out


def compact_pred_from_cinema(raw: np.ndarray) -> np.ndarray:
    out = np.zeros(raw.shape, dtype=np.uint8)
    out[raw == 2] = 1
    out[raw == 3] = 2
    return out


def dice(a: np.ndarray, b: np.ndarray) -> float | None:
    a_sum = int(a.sum())
    b_sum = int(b.sum())
    if a_sum == 0 and b_sum == 0:
        return None
    denom = a_sum + b_sum
    return float(2.0 * np.logical_and(a, b).sum() / denom) if denom else 0.0


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


def load_adapter_index(metrics_csv: Path) -> dict[tuple[str, str], list[dict[str, str]]]:
    by_case: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(metrics_csv):
        if row.get("split") == "train":
            by_case[(row["center"], row["case_id"])].append(row)
    for rows in by_case.values():
        rows.sort(key=lambda r: int(r["frame_index"]))
    return by_case


def normalize(arr: np.ndarray) -> np.ndarray:
    arr_f = arr.astype(np.float32)
    lo = float(np.percentile(arr_f, 1.0))
    hi = float(np.percentile(arr_f, 99.0))
    if hi <= lo:
        return np.zeros_like(arr_f, dtype=np.float32)
    return np.clip((arr_f - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def image_stats(a: np.ndarray, b: np.ndarray, roi: np.ndarray | None = None) -> dict[str, float | None]:
    a_f = a.astype(np.float32)
    b_f = b.astype(np.float32)
    if roi is not None and np.any(roi):
        a_f = a_f[roi]
        b_f = b_f[roi]
    if a_f.size == 0:
        return {"mae": None, "ncc": None}
    mae = float(np.mean(np.abs(a_f - b_f)))
    a0 = a_f - float(np.mean(a_f))
    b0 = b_f - float(np.mean(b_f))
    denom = float(np.sqrt(np.sum(a0 * a0) * np.sum(b0 * b0)))
    ncc = float(np.sum(a0 * b0) / denom) if denom > 1e-8 else None
    return {"mae": mae, "ncc": ncc}


def center_of_mass_mm(mask: np.ndarray, spacing_zyx: tuple[float, float, float]) -> tuple[float, float, float] | None:
    if not np.any(mask):
        return None
    coords = ndimage.center_of_mass(mask.astype(np.uint8))
    return tuple(float(c) * float(s) for c, s in zip(coords, spacing_zyx))


def distance_mm(a: tuple[float, float, float] | None, b: tuple[float, float, float] | None) -> float | None:
    if a is None or b is None:
        return None
    return float(np.linalg.norm(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)))


def agreement(a: np.ndarray, b: np.ndarray) -> float:
    scores = []
    for cls in (1, 2):
        score = dice(a == cls, b == cls)
        if score is not None:
            scores.append(score)
    return float(np.mean(scores)) if scores else 0.0


def softmax(values: list[float], temperature: float = 0.20) -> list[float]:
    arr = np.asarray(values, dtype=np.float64) / max(temperature, 1e-6)
    arr = arr - np.max(arr)
    exp = np.exp(arr)
    probs = exp / np.sum(exp)
    return [float(x) for x in probs]


def fuse_predictions(preds: list[np.ndarray], weights: list[float], threshold: float) -> np.ndarray:
    out = np.zeros_like(preds[0], dtype=np.uint8)
    for cls in (1, 2):
        score = np.zeros(preds[0].shape, dtype=np.float32)
        for pred, weight in zip(preds, weights):
            score += float(weight) * (pred == cls)
        out[score >= threshold] = cls
    return out


def warp_label_slice(label: np.ndarray, flow_v: np.ndarray, flow_u: np.ndarray) -> np.ndarray:
    nr, nc = label.shape
    row_coords, col_coords = np.meshgrid(np.arange(nr), np.arange(nc), indexing="ij")
    warped = warp(
        label.astype(np.float32),
        np.array([row_coords + flow_v, col_coords + flow_u]),
        order=0,
        mode="constant",
        cval=0.0,
        preserve_range=True,
    )
    return np.rint(warped).astype(np.uint8)


def warp_image_slice(image: np.ndarray, flow_v: np.ndarray, flow_u: np.ndarray) -> np.ndarray:
    nr, nc = image.shape
    row_coords, col_coords = np.meshgrid(np.arange(nr), np.arange(nc), indexing="ij")
    warped = warp(
        image.astype(np.float32),
        np.array([row_coords + flow_v, col_coords + flow_u]),
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


def run_optical_flow_warp(
    fixed_arr: np.ndarray,
    moving_arr: np.ndarray,
    moving_pred: np.ndarray,
    radius: int,
    max_side: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int]]:
    start = time.perf_counter()
    warped_pred = np.zeros_like(moving_pred, dtype=np.uint8)
    warped_img = np.zeros_like(moving_arr, dtype=np.float32)
    folding_pixels = 0
    jac_min = 1.0
    smoothness_values: list[float] = []
    mean_flow_values: list[float] = []
    max_flow_values: list[float] = []
    for z in range(fixed_arr.shape[0]):
        fixed_2d = fixed_arr[z].astype(np.float32)
        moving_2d = moving_arr[z].astype(np.float32)
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
            zoom_x = fixed_2d.shape[1] / float(flow_v.shape[1])
            flow_v = ndimage.zoom(flow_v, zoom=(zoom_y, zoom_x), order=1) / scale
            flow_u = ndimage.zoom(flow_u, zoom=(zoom_y, zoom_x), order=1) / scale
            flow_v = flow_v[: fixed_2d.shape[0], : fixed_2d.shape[1]]
            flow_u = flow_u[: fixed_2d.shape[0], : fixed_2d.shape[1]]
        fold, jmin, smooth = flow_folding_proxy(flow_v, flow_u)
        folding_pixels += int(fold)
        jac_min = min(jac_min, float(jmin))
        flow_mag = np.sqrt(flow_v * flow_v + flow_u * flow_u)
        smoothness_values.append(smooth)
        mean_flow_values.append(float(np.mean(flow_mag)))
        max_flow_values.append(float(np.max(flow_mag)))
        warped_pred[z] = warp_label_slice(moving_pred[z], flow_v, flow_u)
        warped_img[z] = warp_image_slice(moving_2d, flow_v, flow_u)
    return (
        warped_pred,
        warped_img,
        {
            "runtime_seconds": time.perf_counter() - start,
            "folding_pixels": folding_pixels,
            "folding_voxels": folding_pixels,
            "jacobian_min_proxy": jac_min,
            "flow_smoothness_mean": float(np.mean(smoothness_values)) if smoothness_values else 0.0,
            "flow_magnitude_mean_px": float(np.mean(mean_flow_values)) if mean_flow_values else 0.0,
            "flow_magnitude_max_px": float(np.max(max_flow_values)) if max_flow_values else 0.0,
        },
    )


def case_metric_rows(variant: str, row: dict[str, str], pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, float, float]) -> list[dict[str, Any]]:
    out = []
    for cls, name in CLASS_NAMES.items():
        pred_mask = pred == cls
        gt_mask = gt == cls
        pred_voxels = int(pred_mask.sum())
        gt_voxels = int(gt_mask.sum())
        out.append(
            {
                "variant": variant,
                "case_id": row["case_id"],
                "center": row["center"],
                "class_id": cls,
                "metric_name": name,
                "dice": dice(pred_mask, gt_mask),
                "hd95": hd95(pred_mask, gt_mask, spacing_zyx),
                "component_count": component_count(pred_mask),
                "pred_voxels": pred_voxels,
                "gt_voxels": gt_voxels,
                "volume_ratio": None if gt_voxels == 0 else float(pred_voxels) / float(gt_voxels),
                "empty_prediction": not bool(pred_mask.any()),
            }
        )
    return out


def anatomy_consistency_rows(
    variant: str,
    row: dict[str, str],
    ref_pred: np.ndarray,
    pred: np.ndarray,
    frame_index: int,
) -> list[dict[str, Any]]:
    out = []
    for cls, name in [(1, "class_1_myocardium"), (2, "class_2_lv")]:
        out.append(
            {
                "variant": variant,
                "case_id": row["case_id"],
                "center": row["center"],
                "frame_index": frame_index,
                "class_id": cls,
                "metric_name": name,
                "anatomy_consistency_dice": dice(pred == cls, ref_pred == cls),
                "candidate_components": component_count(pred == cls),
                "candidate_voxels": int((pred == cls).sum()),
                "reference_components": component_count(ref_pred == cls),
                "reference_voxels": int((ref_pred == cls).sum()),
            }
        )
    return out


def summarize_case_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    variants = sorted({str(r["variant"]) for r in rows})
    for variant in variants:
        for cls, name in CLASS_NAMES.items():
            subset = [r for r in rows if r["variant"] == variant and int(r["class_id"]) == cls]
            out.append(
                {
                    "variant": variant,
                    "class_id": cls,
                    "metric_name": name,
                    "n": len(subset),
                    "dice_mean": finite_mean([r["dice"] for r in subset]),
                    "hd95_mean": finite_mean([r["hd95"] for r in subset]),
                    "hd95_median": finite_median([r["hd95"] for r in subset]),
                    "component_count_mean": finite_mean([r["component_count"] for r in subset]),
                    "volume_ratio_mean": finite_mean([r["volume_ratio"] for r in subset]),
                    "empty_prediction_rate": finite_mean([1.0 if r["empty_prediction"] else 0.0 for r in subset]),
                }
            )
    return out


def summarize_case_metrics_by_center(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    variants = sorted({str(r["variant"]) for r in rows})
    centers = sorted({str(r["center"]) for r in rows})
    for variant in variants:
        for center in centers:
            for cls, name in CLASS_NAMES.items():
                subset = [
                    r
                    for r in rows
                    if r["variant"] == variant and str(r["center"]) == center and int(r["class_id"]) == cls
                ]
                out.append(
                    {
                        "variant": variant,
                        "center": center,
                        "class_id": cls,
                        "metric_name": name,
                        "n": len(subset),
                        "dice_mean": finite_mean([r["dice"] for r in subset]),
                        "hd95_mean": finite_mean([r["hd95"] for r in subset]),
                        "component_count_mean": finite_mean([r["component_count"] for r in subset]),
                        "volume_ratio_mean": finite_mean([r["volume_ratio"] for r in subset]),
                        "empty_prediction_rate": finite_mean([1.0 if r["empty_prediction"] else 0.0 for r in subset]),
                    }
                )
    return out


def summarize_motion(metrics_rows: list[dict[str, Any]], warp_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    variants = sorted({str(r["variant"]) for r in metrics_rows})
    for variant in variants:
        warp_subset = [r for r in warp_rows if r["variant"] == variant]
        for cls, name in [(1, "class_1_myocardium"), (2, "class_2_lv")]:
            subset = [r for r in metrics_rows if r["variant"] == variant and int(r["class_id"]) == cls]
            out.append(
                {
                    "variant": variant,
                    "class_id": cls,
                    "metric_name": name,
                    "n": len(subset),
                    "anatomy_consistency_mean": finite_mean([r["anatomy_consistency_dice"] for r in subset]),
                    "candidate_component_mean": finite_mean([r["candidate_components"] for r in subset]),
                    "runtime_seconds_mean": finite_mean([r["runtime_seconds"] for r in warp_subset]),
                    "image_ncc_before_mean": finite_mean([r["image_ncc_before"] for r in warp_subset]),
                    "image_ncc_after_mean": finite_mean([r["image_ncc_after"] for r in warp_subset]),
                    "image_ncc_delta_mean": finite_mean([r["image_ncc_delta"] for r in warp_subset]),
                    "folding_voxels_mean": finite_mean([r["folding_voxels"] for r in warp_subset]),
                    "jacobian_min_proxy_min": min(finite_values([r["jacobian_min_proxy"] for r in warp_subset]), default=None),
                    "flow_smoothness_mean": finite_mean([r["flow_smoothness_mean"] for r in warp_subset]),
                }
            )
    return out


def fmt(value: Any, digits: int = 4) -> str:
    vals = finite_values([value])
    return "NA" if not vals else f"{vals[0]:.{digits}f}"


def metric_lookup(summary_rows: list[dict[str, Any]], variant: str, cls: int, key: str) -> float | None:
    for row in summary_rows:
        if row["variant"] == variant and int(row["class_id"]) == cls:
            vals = finite_values([row.get(key)])
            return vals[0] if vals else None
    return None


def safe_rel_path(path: str | Path) -> str:
    return str(path).replace("/overflow/htzhu/CARE/", "").replace("/users/a/e/aereinh/CARE/", "")


def sanitize_case_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {key: safe_rel_path(value) if key.endswith("_path") else value for key, value in row.items()}
        for row in rows
    ]


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "evidence not found"


def command_text() -> str:
    return " ".join([sys.executable, *sys.argv])


def write_reports(
    args: argparse.Namespace,
    elapsed: float,
    safe_rows: list[dict[str, str]],
    mismatch_rows: list[dict[str, str]],
    safe_used: list[dict[str, Any]],
    case_rows: list[dict[str, Any]],
    motion_rows: list[dict[str, Any]],
    warp_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    motion_summary_rows: list[dict[str, Any]],
    descriptor_rows: list[dict[str, Any]],
) -> str:
    ref_myo = metric_lookup(summary_rows, "cine_reference_control_recheck", 1, "dice_mean")
    flow_myo = metric_lookup(summary_rows, "cine_deformable_or_feature_warp", 1, "dice_mean")
    desc_myo = metric_lookup(summary_rows, "cine_motion_descriptor_temporal_refiner", 1, "dice_mean")
    ref_lv = metric_lookup(summary_rows, "cine_reference_control_recheck", 2, "dice_mean")
    flow_lv = metric_lookup(summary_rows, "cine_deformable_or_feature_warp", 2, "dice_mean")
    desc_lv = metric_lookup(summary_rows, "cine_motion_descriptor_temporal_refiner", 2, "dice_mean")
    flow_delta = None if ref_myo is None or flow_myo is None else flow_myo - ref_myo
    desc_delta = None if ref_myo is None or desc_myo is None else desc_myo - ref_myo
    flow_lv_delta = None if ref_lv is None or flow_lv is None else flow_lv - ref_lv
    desc_lv_delta = None if ref_lv is None or desc_lv is None else desc_lv - ref_lv
    positive = (
        flow_delta is not None
        and flow_lv_delta is not None
        and flow_delta > 0.002
        and flow_lv_delta > -0.02
    ) or (
        desc_delta is not None
        and desc_lv_delta is not None
        and desc_delta > 0.002
        and desc_lv_delta > -0.02
    )
    route_decision = "TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC" if positive else "STOP_CINE_NO_TEMPORAL_SIGNAL"
    next_state = "EXECUTED_UNAUDITED"
    experiment_adequacy_decision = (
        "PARTIAL"
        if len(safe_rows) == 59
        and len(mismatch_rows) == 5
        and ref_myo is not None
        and (flow_delta is not None or desc_delta is not None)
        else "EVIDENCE_NOT_FOUND"
    )
    route_promotion_decision = "NO_PROMOTION"
    route_negative_decision = "STOP_NOT_SUPPORTED"
    scientific_resolution_status = "SCIENTIFIC_UNRESOLVED"
    result_title = " ".join(part.capitalize() for part in args.task_key.split("_")[1:])

    ref_weight = finite_mean([r["reference_weight"] for r in descriptor_rows])
    ref_dom_rate = finite_mean([1.0 if r["reference_dominance"] else 0.0 for r in descriptor_rows])
    flow_folding = finite_mean([r["folding_voxels"] for r in warp_rows if r["variant"] == "cine_deformable_or_feature_warp"])
    flow_smoothness = finite_mean([r["flow_smoothness_mean"] for r in warp_rows if r["variant"] == "cine_deformable_or_feature_warp"])
    flow_runtime = finite_mean([r["runtime_seconds"] for r in warp_rows if r["variant"] == "cine_deformable_or_feature_warp"])

    write_text(
        args.output_dir / "reference_frame_contract.md",
        "\n".join(
            [
                "# Reference Frame Contract",
                "",
                "reference_frame_selection: `frame0 / ED-like adapter t00`",
                "",
                "Frame 0 is used as the reference because prior geometry preflight established that safe-case labels match raw Cine frame0 metadata and the frozen CineMA adapter produced frame0 anatomy predictions on that geometry. This run treats frame0/reference-only as a control only.",
                "",
                "Non-reference frame usage:",
                "",
                "- `cine_deformable_or_feature_warp`: uses the first adapter-selected non-reference frame per case, estimates a dense 2D slice-wise optical-flow displacement into frame0 space, warps the non-reference anatomy prediction, and fuses it with the frame0 anatomy prediction before local proxy scoring.",
                "- `cine_motion_descriptor_temporal_refiner`: uses frame0 plus adapter-selected non-reference keyframes, computes frame agreement and center-of-mass/motion descriptors, and fuses frame predictions by descriptor-derived temporal weights. This is descriptor/aggregation evidence, not completed registration.",
                "",
                "Target-head availability:",
                "",
                "- Local source anatomy prior has myocardium/LV outputs only after remapping CineMA labels `2 -> compact 1` and `3 -> compact 2`.",
                "- Pathology/scar class `compact 3` remains a sanity negative control; hosted `myocardium_cinemyops` evidence is `evidence not found` because validation upload/package generation was forbidden.",
            ]
        ),
    )

    write_text(
        args.output_dir / "resource_audit.md",
        "\n".join(
            [
                "# Resource Audit",
                "",
                f"- safe cases source: `{args.safe_cases}`",
                f"- mismatch cases source: `{args.mismatch_cases}`",
                f"- adapter metrics source: `{args.adapter_metrics}`",
                f"- output directory: `{args.output_dir}`",
                f"- Python executable: `{sys.executable}`",
                f"- SimpleITK version: `{sitk.Version_VersionString()}`",
                "- optical-flow implementation: `skimage.registration.optical_flow_ilk`, CPU only.",
                f"- optical-flow max side before displacement estimation: `{args.flow_max_side}` pixels; displacement is rescaled before full-resolution warp/sanity.",
                "- GPU jobs: none.",
                "- Network/downloads/uploads: none.",
                "- External weights downloaded in this run: none.",
                f"- Total runtime seconds: `{elapsed:.2f}`",
                "",
                "Variant coverage:",
                "",
                "- `cine_reference_control_recheck`: completed.",
                "- `cine_deformable_or_feature_warp`: completed as first-party dense optical-flow/feature-warp proxy with folding/smoothness sanity; not claimed as validated registration.",
                "- `cine_motion_descriptor_temporal_refiner`: completed as descriptor/temporal aggregation proxy; not claimed as registration.",
                "- `cine_anatomy_prior_temporal_adapter`: local CineMA artifacts exist and are audited in `anatomy_prior_adapter_audit.md`; no new adapter run or external download was performed.",
            ]
        ),
    )

    observed_pred_labels = sorted(
        {
            int(r["class_id"])
            for r in case_rows
            if int(r["pred_voxels"]) > 0
        }
    )
    observed_gt_labels = sorted(
        {
            int(r["class_id"])
            for r in case_rows
            if int(r["gt_voxels"]) > 0
        }
    )
    write_text(
        args.output_dir / "label_export_qc.md",
        "\n".join(
            [
                "# Label Export QC",
                "",
                "scope: local diagnostic only",
                "",
                "- evaluator: local safe-case proxy from `scripts/evaluation/cine_motion_hardmode_20260703.py`.",
                "- raw ground-truth labels: `200 -> compact 1 myocardium`, `500 -> compact 2 LV`, `2221 -> compact 3 scar_sanity`.",
                "- CineMA anatomy-prior prediction remap: `2 -> compact 1 myocardium`, `3 -> compact 2 LV`; no scar/pathology prediction head exists.",
                f"- observed compact GT labels in scored case metrics: `{observed_gt_labels}`.",
                f"- observed compact predicted labels with nonzero volume: `{observed_pred_labels}`.",
                "- validation export: `not performed`.",
                "- upload-ready package: `not performed`.",
                "- raw-label submission decode path: `evidence not found` because validation packaging/upload were forbidden.",
                "- hosted `myocardium_cinemyops`: `evidence not found`.",
                "",
                "Conclusion: compact-label local proxy scoring is internally consistent for the safe subset, but this is not challenge-facing raw-label export QC.",
            ]
        ),
    )

    license_path = args.cinema_repo / "LICENSE"
    readme_path = args.cinema_repo / "README.md"
    run_info_text = "evidence not found"
    if args.cinema_run_info.is_file():
        run_info = json.loads(args.cinema_run_info.read_text(encoding="utf-8"))
        run_info_text = json.dumps(
            {
                "cinema_repo": run_info.get("args", {}).get("cinema_repo", "evidence not found"),
                "trained_dataset": run_info.get("args", {}).get("trained_dataset", "evidence not found"),
                "frame_strategy": run_info.get("args", {}).get("frame_strategy", "evidence not found"),
                "device": run_info.get("args", {}).get("device", "evidence not found"),
                "selected_cases": run_info.get("selected_cases", {}),
                "cinema_label_semantics": run_info.get("cinema_label_semantics", {}),
            },
            indent=2,
            sort_keys=True,
        )
    write_text(
        args.output_dir / "anatomy_prior_adapter_audit.md",
        "\n".join(
            [
                "# Anatomy Prior Adapter Audit",
                "",
                f"- local CineMA repo path: `{args.cinema_repo}`",
                f"- repo exists: `{args.cinema_repo.is_dir()}`",
                f"- LICENSE exists: `{license_path.is_file()}`",
                f"- README exists: `{readme_path.is_file()}`",
                "- license observed: `MIT License`" if license_path.is_file() and "MIT License" in license_path.read_text(encoding="utf-8", errors="ignore")[:200] else "- license observed: `evidence not found`",
                "- provenance caveat: adapter run info was generated in an earlier run and records an `/overflow/htzhu/CARE/...` path; this task did not refresh or download external weights.",
                "- adapter role in this task: frozen local anatomy prior for myocardium/LV proxy only; no scar/pathology head.",
                "",
                "## Prior Adapter Run Info",
                "",
                "```json",
                run_info_text,
                "```",
            ]
        ),
    )

    lines = [
        "# Cine Motion Hardmode Temporal Metrics",
        "",
        "## Setup",
        "",
        f"- safe cases evaluated: `{len(safe_rows)}`",
        f"- mismatch cases held out: `{len(mismatch_rows)}`",
        f"- runtime seconds: `{elapsed:.2f}`",
        "- hosted `myocardium_cinemyops`: `evidence not found`; no validation upload/package was authorized.",
        "- class_3 scar sanity remains a negative control because the source anatomy prior has no scar head.",
        "",
        "## Local Proxy Metrics",
        "",
        "| variant | metric | n | Dice | HD95 mean | HD95 median | components | volume ratio | empty rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['variant']} | {row['metric_name']} | {row['n']} | "
            f"{fmt(row['dice_mean'])} | {fmt(row['hd95_mean'])} | {fmt(row['hd95_median'])} | "
            f"{fmt(row['component_count_mean'])} | {fmt(row['volume_ratio_mean'])} | {fmt(row['empty_prediction_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Temporal Diagnostics",
            "",
            f"- mean descriptor reference weight: `{fmt(ref_weight)}`",
            f"- descriptor reference dominance rate: `{fmt(ref_dom_rate)}`",
            f"- optical-flow warp runtime mean seconds: `{fmt(flow_runtime)}`",
            f"- optical-flow folding proxy mean pixels: `{fmt(flow_folding)}`",
            f"- optical-flow smoothness proxy mean: `{fmt(flow_smoothness)}`",
            "",
            "## Delta Versus Reference Control",
            "",
            f"- optical-flow/feature-warp myocardium Dice delta: `{fmt(flow_delta)}`",
            f"- optical-flow/feature-warp LV Dice delta: `{fmt(flow_lv_delta)}`",
            f"- descriptor temporal refiner myocardium Dice delta: `{fmt(desc_delta)}`",
            f"- descriptor temporal refiner LV Dice delta: `{fmt(desc_lv_delta)}`",
            "",
            f"route_decision: `{route_decision}`",
            f"self_assessed_status: `{next_state}`",
            f"experiment_adequacy_decision: `{experiment_adequacy_decision}`",
            f"route_promotion_decision: `{route_promotion_decision}`",
            f"route_negative_decision: `{route_negative_decision}`",
            f"scientific_resolution_status: `{scientific_resolution_status}`",
        ]
    )
    write_text(args.output_dir / "temporal_metrics_summary.md", "\n".join(lines))

    write_text(
        args.output_dir / "failure_interpretation.md",
        "\n".join(
            [
                "# Failure Interpretation",
                "",
                f"route_decision: `{route_decision}`",
                f"experiment_adequacy_decision: `{experiment_adequacy_decision}`",
                f"route_promotion_decision: `{route_promotion_decision}`",
                f"route_negative_decision: `{route_negative_decision}`",
                f"scientific_resolution_status: `{scientific_resolution_status}`",
                "",
                "Interpretation:",
                "",
                f"- Reference-control myocardium Dice: `{fmt(ref_myo)}`; LV Dice: `{fmt(ref_lv)}`.",
                f"- Optical-flow/feature-warp delta: myocardium `{fmt(flow_delta)}`, LV `{fmt(flow_lv_delta)}`.",
                f"- Motion-descriptor temporal-refiner delta: myocardium `{fmt(desc_delta)}`, LV `{fmt(desc_lv_delta)}`.",
                "- Translation-only evidence from prior Cine registration was not used as a final hardmode conclusion; this run attempted a harder dense optical-flow/feature-warp proxy plus a descriptor temporal refiner.",
                "- Dense optical flow is reported as a proxy with warp sanity, not a validated diffeomorphic registration method.",
                "- Descriptor aggregation is reported as descriptor evidence, not completed registration.",
                "- Hosted challenge metric, raw-label validation export, and upload-package evidence are `evidence not found` by task constraint.",
                "- If audited, any continuation should be treated as a new planner/controller decision because this package is local proxy evidence only.",
            ]
        ),
    )

    write_text(
        args.output_dir / "command_transcript.md",
        "\n".join(
            [
                "# Command Transcript",
                "",
                f"- command: `{command_text()}`",
                f"- cwd: `{Path.cwd()}`",
                f"- python: `{sys.executable}`",
                f"- exit_status: `0`",
                f"- elapsed_seconds: `{elapsed:.2f}`",
                f"- git_head: `{git_head()}`",
                f"- network_used: `false`",
                f"- gpu_used: `false`",
                f"- pid: `{os.getpid()}`",
            ]
        ),
    )

    result_lines = [
        f"# Result {result_title}",
        "",
        "self_assessed_status: EXECUTED_UNAUDITED",
        f"route_decision: {route_decision}",
        f"experiment_adequacy_decision: {experiment_adequacy_decision}",
        f"route_promotion_decision: {route_promotion_decision}",
        f"route_negative_decision: {route_negative_decision}",
        f"scientific_resolution_status: {scientific_resolution_status}",
        "domain_evidence_label: PARTIAL_MECHANISM_INCOMPLETE",
        "",
        "## Execution Summary",
        "",
        f"- Evaluated `{len(safe_rows)}` safe CineMyoPS cases and held out `{len(mismatch_rows)}` mismatch cases.",
        "- Completed baseline `cine_reference_control_recheck`.",
        "- Completed `cine_deformable_or_feature_warp` as dense slice-wise optical-flow/feature-warp proxy with warp sanity.",
        "- Completed `cine_motion_descriptor_temporal_refiner` as descriptor/temporal aggregation proxy.",
        "- No GPU job, network, upload, validation package, fold expansion, evaluator change, or label mapping change was performed.",
        "",
        "## Key Metrics",
        "",
        f"- reference myocardium Dice / LV Dice: `{fmt(ref_myo)}` / `{fmt(ref_lv)}`",
        f"- optical-flow myocardium Dice delta / LV Dice delta: `{fmt(flow_delta)}` / `{fmt(flow_lv_delta)}`",
        f"- descriptor myocardium Dice delta / LV Dice delta: `{fmt(desc_delta)}` / `{fmt(desc_lv_delta)}`",
        f"- descriptor mean reference weight / dominance rate: `{fmt(ref_weight)}` / `{fmt(ref_dom_rate)}`",
        f"- optical-flow folding proxy mean pixels / smoothness mean: `{fmt(flow_folding)}` / `{fmt(flow_smoothness)}`",
        "",
        "## Claims",
        "",
        "claim.reference_frame_contract: frame0 is the reference-control frame, selected from prior safe geometry evidence and used only as a baseline.",
        "claim.nonreference_route: non-reference frames enter both the optical-flow feature-warp route and the descriptor temporal-refiner route.",
        "claim.local_proxy_only: all reported metrics are local safe-subset proxies; hosted `myocardium_cinemyops` evidence is not present.",
        "claim.no_forbidden_actions: no validation upload/package, fold expansion, evaluator/label mapping change, network download, commit, or push was performed.",
        "",
        "## Files Read",
        "",
        "- `AGENTS.md`",
        "- handoff protocol files under `prompts/`",
        "- `.agents/skills/agent-task-executor/SKILL.md`",
        "- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md` and `references/reference.md`",
        f"- `prompts/tasks/{args.task_key}.md`",
        "- `prompts/CONTROLLER_TASK_PROTOCOL.md`",
        "- `prompts/EXPERIMENT_ADEQUACY_GATE.md`",
        "- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`",
        "- `prompts/CARE_OVERLAY_GATES.md`",
        "- `results/20260703_srr_formal_training/review.md`",
        "- `results/20260703_cine_motion/result.md` and `review.md`",
        "- prior Cine result files under `results/20260625_cine_geometry/`, `results/20260629_cine_motion_alignment/`, `results/20260629_cine_motion_pathology/`, and `results/cinema_adapter/`",
        "- current controller report and selected MyoPS reviews under `results/20260703_hardmode_goal/` and `results/20260703_myops_*`",
        "",
        "## Files Changed",
        "",
        "- `scripts/evaluation/cine_motion_hardmode_20260703.py`",
        f"- `{args.output_dir}/*`",
        "",
        "## Commands",
        "",
        f"- `{command_text()}` -> exit `0`, elapsed `{elapsed:.2f}s`",
        "",
        "## Incomplete Evidence",
        "",
        "- independent audit: `evidence not found` in this executor session; review is required separately.",
        "- hosted `myocardium_cinemyops`: `evidence not found` because upload/package generation was forbidden.",
        "- learned target pathology head: `evidence not found`; source CineMA prior has no scar head.",
        "- validated registration: `evidence not found`; optical flow is a proxy with warp sanity, and descriptor route is not registration.",
        "",
        "## Blocked Actions",
        "",
        "- validation packaging/upload remains blocked.",
        "- fold expansion remains blocked.",
        "- hosted metric claims remain blocked.",
        "- label/evaluator/fold split changes remain blocked.",
        "- next-stage training remains blocked unless a later GPT-authored task explicitly authorizes it.",
    ]
    write_text(args.output_dir / "result.md", "\n".join(result_lines))

    manifest_lines = [
        "# MANIFEST",
        "",
        f"- Task: `prompts/tasks/{args.task_key}.md`",
        f"- Controller task: `prompts/tasks/{args.controller_task_key}.md`",
        f"- Result: `{args.output_dir / 'result.md'}`",
        f"- Review placeholder: `{args.output_dir / 'review.md'}` (not written by executor)",
        "",
        "## Artifacts",
        "",
        "- `resource_audit.md`: dependencies, resource use, and variant coverage.",
        "- `safe_cases_used.csv`: safe case list with reference/non-reference frame usage.",
        "- `mismatch_cases_heldout.csv`: held-out mismatch cases requiring header/resample repair before supervised scoring.",
        "- `reference_frame_contract.md`: reference frame and non-reference frame route statement.",
        "- `motion_or_warp_metrics.csv`: per-case/per-class anatomy consistency and frame-to-reference similarity summary.",
        "- `warp_sanity.csv`: dense optical-flow/descriptor runtime, smoothness, folding, and similarity diagnostics.",
        "- `temporal_metrics_summary.md`: aggregate proxy metrics and temporal diagnostics.",
        "- `case_metrics.csv`: per-case local proxy Dice, HD95, components, and volume ratio.",
        "- `summary_metrics.csv`: aggregate case metric table.",
        "- `center_summary_metrics.csv`: per-center subgroup metrics for available safe-case centers.",
        "- `anatomy_prior_adapter_audit.md`: local CineMA license/provenance/adapter sanity.",
        "- `label_export_qc.md`: compact-label local proxy and non-export caveat.",
        "- `failure_interpretation.md`: route decision, caveats, and missing evidence.",
        "- `command_transcript.md`: command, exit status, environment, and elapsed time.",
        "- `motion_or_warp_summary.csv`: aggregate motion/warp diagnostic table.",
        f"- Source script: `scripts/evaluation/{Path(__file__).name}`",
    ]
    write_text(args.output_dir / "MANIFEST.md", "\n".join(manifest_lines))
    return next_state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safe-cases", type=Path, default=DEFAULT_SAFE_CASES)
    parser.add_argument("--mismatch-cases", type=Path, default=DEFAULT_MISMATCH_CASES)
    parser.add_argument("--adapter-metrics", type=Path, default=DEFAULT_ADAPTER_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--task-key", default=DEFAULT_TASK_KEY)
    parser.add_argument("--controller-task-key", default=DEFAULT_CONTROLLER_TASK_KEY)
    parser.add_argument("--cinema-repo", type=Path, default=DEFAULT_CINEMA_REPO)
    parser.add_argument("--cinema-run-info", type=Path, default=DEFAULT_CINEMA_RUN_INFO)
    parser.add_argument("--max-nonreference-frames", type=int, default=2)
    parser.add_argument("--flow-nonreference-frames", type=int, default=1)
    parser.add_argument("--flow-radius", type=int, default=7)
    parser.add_argument("--flow-max-side", type=int, default=96)
    parser.add_argument("--limit-cases", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    start = time.perf_counter()
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    safe_rows = read_rows(args.safe_cases)
    if args.limit_cases:
        safe_rows = safe_rows[: args.limit_cases]
    mismatch_rows = read_rows(args.mismatch_cases)
    adapter = load_adapter_index(args.adapter_metrics)
    case_rows: list[dict[str, Any]] = []
    motion_rows: list[dict[str, Any]] = []
    warp_rows: list[dict[str, Any]] = []
    descriptor_rows: list[dict[str, Any]] = []
    safe_used: list[dict[str, Any]] = []

    for row in safe_rows:
        key = (row["center"], row["case_id"])
        pred_rows = adapter.get(key, [])
        if len(pred_rows) < 2:
            raise RuntimeError(f"expected >=2 adapter frames for {key}, found {len(pred_rows)}")
        selected = pred_rows[: max(2, 1 + args.max_nonreference_frames)]
        ref_info = selected[0]
        nonref_infos = selected[1:]
        flow_infos = nonref_infos[: max(1, args.flow_nonreference_frames)]

        label = sitk.ReadImage(row["label_path"])
        gt = compact_gt(sitk.GetArrayFromImage(label))
        spacing = label.GetSpacing()
        spacing_zyx = (float(spacing[2]), float(spacing[1]), float(spacing[0]))
        cine_arr = sitk.GetArrayFromImage(sitk.ReadImage(row["cine_path"]))
        ref_frame_index = int(ref_info["frame_index"])
        ref_img = normalize(cine_arr[ref_frame_index])
        ref_pred = compact_pred_from_cinema(sitk.GetArrayFromImage(sitk.ReadImage(ref_info["prediction_path"])))

        safe_used.append(
            {
                **{k: safe_rel_path(v) if k.endswith("_path") else v for k, v in row.items()},
                "reference_frame_index": ref_frame_index,
                "reference_prediction_path": safe_rel_path(ref_info["prediction_path"]),
                "descriptor_frame_indices": ",".join(p["frame_index"] for p in selected),
                "flow_frame_indices": ",".join(p["frame_index"] for p in flow_infos),
                "n_descriptor_frames": len(selected),
                "n_flow_frames": len(flow_infos),
            }
        )

        case_rows.extend(case_metric_rows("cine_reference_control_recheck", row, ref_pred, gt, spacing_zyx))

        flow_preds = [ref_pred]
        flow_weights = [0.50]
        for info in flow_infos:
            frame_index = int(info["frame_index"])
            moving_img = normalize(cine_arr[frame_index])
            moving_pred = compact_pred_from_cinema(sitk.GetArrayFromImage(sitk.ReadImage(info["prediction_path"])))
            roi = ndimage.binary_dilation((ref_pred > 0) | (moving_pred > 0), iterations=6)
            before = image_stats(ref_img, moving_img, roi)
            warped_pred, warped_img, flow_stats = run_optical_flow_warp(
                ref_img,
                moving_img,
                moving_pred,
                radius=args.flow_radius,
                max_side=args.flow_max_side,
            )
            after = image_stats(ref_img, warped_img, roi)
            image_ncc_delta = None if before["ncc"] is None or after["ncc"] is None else float(after["ncc"]) - float(before["ncc"])
            warp_row = {
                "variant": "cine_deformable_or_feature_warp",
                "case_id": row["case_id"],
                "center": row["center"],
                "frame_index": frame_index,
                "status": "ok",
                "failure_reason": "",
                "warp_type": "slice2d_dense_optical_flow_ilk",
                "runtime_seconds": flow_stats["runtime_seconds"],
                "image_mae_before": before["mae"],
                "image_mae_after": after["mae"],
                "image_mae_delta": None if before["mae"] is None or after["mae"] is None else float(after["mae"]) - float(before["mae"]),
                "image_ncc_before": before["ncc"],
                "image_ncc_after": after["ncc"],
                "image_ncc_delta": image_ncc_delta,
                "folding_voxels": flow_stats["folding_voxels"],
                "jacobian_min_proxy": flow_stats["jacobian_min_proxy"],
                "flow_smoothness_mean": flow_stats["flow_smoothness_mean"],
                "flow_magnitude_mean_px": flow_stats["flow_magnitude_mean_px"],
                "flow_magnitude_max_px": flow_stats["flow_magnitude_max_px"],
            }
            warp_rows.append(warp_row)
            motion_rows.extend(
                {
                    **m,
                    "runtime_seconds": flow_stats["runtime_seconds"],
                    "image_ncc_before": before["ncc"],
                    "image_ncc_after": after["ncc"],
                    "image_ncc_delta": image_ncc_delta,
                    "folding_voxels": flow_stats["folding_voxels"],
                    "jacobian_min_proxy": flow_stats["jacobian_min_proxy"],
                    "flow_smoothness_mean": flow_stats["flow_smoothness_mean"],
                }
                for m in anatomy_consistency_rows("cine_deformable_or_feature_warp", row, ref_pred, warped_pred, frame_index)
            )
            flow_preds.append(warped_pred)
            flow_weights.append(0.50 / len(flow_infos))
        flow_pred = fuse_predictions(flow_preds, flow_weights, threshold=0.50)
        case_rows.extend(case_metric_rows("cine_deformable_or_feature_warp", row, flow_pred, gt, spacing_zyx))

        descriptor_preds = []
        agreements = []
        center_shifts = []
        for info in selected:
            frame_index = int(info["frame_index"])
            pred = compact_pred_from_cinema(sitk.GetArrayFromImage(sitk.ReadImage(info["prediction_path"])))
            descriptor_preds.append(pred)
            agreements.append(1.0 if frame_index == ref_frame_index else agreement(ref_pred, pred))
            myo_shift = distance_mm(center_of_mass_mm(ref_pred == 1, spacing_zyx), center_of_mass_mm(pred == 1, spacing_zyx))
            lv_shift = distance_mm(center_of_mass_mm(ref_pred == 2, spacing_zyx), center_of_mass_mm(pred == 2, spacing_zyx))
            center_shifts.append(finite_mean([myo_shift, lv_shift]) or 0.0)
        motion_penalty = [1.0 / (1.0 + x / 10.0) for x in center_shifts]
        descriptor_scores = [a * p for a, p in zip(agreements, motion_penalty)]
        weights = softmax(descriptor_scores, temperature=0.25)
        descriptor_pred = fuse_predictions(descriptor_preds, weights, threshold=0.50)
        case_rows.extend(case_metric_rows("cine_motion_descriptor_temporal_refiner", row, descriptor_pred, gt, spacing_zyx))
        entropy = -sum(w * math.log(max(w, 1e-8)) for w in weights)
        descriptor_rows.append(
            {
                "variant": "cine_motion_descriptor_temporal_refiner",
                "case_id": row["case_id"],
                "center": row["center"],
                "frame_indices": ",".join(p["frame_index"] for p in selected),
                "frame_agreements": ",".join(f"{x:.6f}" for x in agreements),
                "center_shift_mm": ",".join(f"{x:.6f}" for x in center_shifts),
                "descriptor_scores": ",".join(f"{x:.6f}" for x in descriptor_scores),
                "frame_weights": ",".join(f"{x:.6f}" for x in weights),
                "reference_weight": weights[0],
                "reference_dominance": weights[0] >= 0.80,
                "temporal_entropy": entropy,
                "runtime_seconds": 0.0,
                "image_ncc_before": "",
                "image_ncc_after": "",
                "image_ncc_delta": "",
                "folding_voxels": "",
                "jacobian_min_proxy": "",
                "flow_smoothness_mean": "",
                "warp_type": "descriptor_only",
                "status": "ok",
            }
        )
        for info, pred in zip(selected, descriptor_preds):
            motion_rows.extend(
                {
                    **m,
                    "runtime_seconds": 0.0,
                    "image_ncc_before": "",
                    "image_ncc_after": "",
                    "image_ncc_delta": "",
                    "folding_voxels": "",
                    "jacobian_min_proxy": "",
                    "flow_smoothness_mean": "",
                }
                for m in anatomy_consistency_rows(
                    "cine_motion_descriptor_temporal_refiner",
                    row,
                    ref_pred,
                    pred,
                    int(info["frame_index"]),
                )
            )

    summary_rows = summarize_case_metrics(case_rows)
    center_summary_rows = summarize_case_metrics_by_center(case_rows)
    motion_summary_rows = summarize_motion(motion_rows, warp_rows + descriptor_rows)
    write_csv(safe_used, args.output_dir / "safe_cases_used.csv")
    write_csv(sanitize_case_rows(mismatch_rows), args.output_dir / "mismatch_cases_heldout.csv")
    write_csv(case_rows, args.output_dir / "case_metrics.csv")
    write_csv(summary_rows, args.output_dir / "summary_metrics.csv")
    write_csv(center_summary_rows, args.output_dir / "center_summary_metrics.csv")
    write_csv(motion_rows + descriptor_rows, args.output_dir / "motion_or_warp_metrics.csv")
    write_csv(warp_rows + descriptor_rows, args.output_dir / "warp_sanity.csv")
    write_csv(motion_summary_rows, args.output_dir / "motion_or_warp_summary.csv")
    elapsed = time.perf_counter() - start
    write_reports(
        args,
        elapsed,
        safe_rows,
        mismatch_rows,
        safe_used,
        case_rows,
        motion_rows,
        warp_rows,
        summary_rows,
        motion_summary_rows,
        descriptor_rows,
    )
    print(
        json.dumps(
            {
                "safe_cases": len(safe_rows),
                "mismatch_held_out": len(mismatch_rows),
                "output_dir": str(args.output_dir),
                "elapsed_seconds": elapsed,
                "status": "EXECUTED_UNAUDITED",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
