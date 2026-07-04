#!/usr/bin/env python3
"""Bounded Cine temporal motion diagnostics for 20260704 resume task."""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage


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


def extract_frame(image_4d: sitk.Image, frame_index: int) -> sitk.Image:
    size = list(image_4d.GetSize())
    index = [0, 0, 0, int(frame_index)]
    size[3] = 0
    return sitk.Extract(image_4d, size, index)


def normalize_image(image: sitk.Image) -> sitk.Image:
    image = sitk.Cast(image, sitk.sitkFloat32)
    return sitk.RescaleIntensity(image, 0.0, 1.0)


def compact_pred_from_cinema(image: sitk.Image) -> sitk.Image:
    arr = sitk.GetArrayFromImage(image)
    out = np.zeros(arr.shape, dtype=np.uint8)
    out[arr == 2] = 1
    out[arr == 3] = 2
    compact = sitk.GetImageFromArray(out)
    compact.CopyInformation(image)
    return compact


def compact_gt(image: sitk.Image) -> sitk.Image:
    arr = sitk.GetArrayFromImage(image)
    out = np.zeros(arr.shape, dtype=np.uint8)
    out[arr == 200] = 1
    out[arr == 500] = 2
    out[arr == 2221] = 3
    compact = sitk.GetImageFromArray(out)
    compact.CopyInformation(image)
    return compact


def dice(a: np.ndarray, b: np.ndarray) -> float | None:
    a_sum = int(a.sum())
    b_sum = int(b.sum())
    if a_sum == 0 and b_sum == 0:
        return None
    denom = a_sum + b_sum
    return float(2.0 * np.logical_and(a, b).sum() / denom) if denom else 0.0


def ncc(a: np.ndarray, b: np.ndarray) -> float | None:
    a = a.astype(np.float32).ravel()
    b = b.astype(np.float32).ravel()
    if a.size == 0 or b.size == 0:
        return None
    a0 = a - float(a.mean())
    b0 = b - float(b.mean())
    denom = float(np.sqrt(np.sum(a0 * a0) * np.sum(b0 * b0)))
    return float(np.sum(a0 * b0) / denom) if denom > 1e-8 else None


def component_count(mask: np.ndarray) -> int:
    if not np.any(mask):
        return 0
    _, count = ndimage.label(mask)
    return int(count)


def finite_mean(values: list[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return float(np.mean(vals)) if vals else None


def prediction_path(adapter_root: Path, center: str, case_id: str, frame_index: int) -> Path:
    return adapter_root / "predictions" / "train" / center / f"{case_id}_t{frame_index:02d}_cinema_acdc_s0.nii.gz"


def run_demons_probe(
    fixed: sitk.Image,
    moving: sitk.Image,
    moving_label: sitk.Image,
    iterations: int,
    smoothing: float,
) -> tuple[sitk.Image, sitk.Image, dict[str, float | int | None]]:
    fixed_n = normalize_image(fixed)
    moving_n = normalize_image(moving)
    start = time.perf_counter()
    registration = sitk.FastSymmetricForcesDemonsRegistrationFilter()
    registration.SetNumberOfIterations(int(iterations))
    registration.SetStandardDeviations(float(smoothing))
    field = registration.Execute(fixed_n, moving_n)
    jac = sitk.DisplacementFieldJacobianDeterminant(field)
    jac_arr = sitk.GetArrayFromImage(jac)
    field_arr = sitk.GetArrayFromImage(field)
    disp_mag = np.linalg.norm(field_arr, axis=-1)
    transform = sitk.DisplacementFieldTransform(field)

    warped_image = sitk.Resample(moving_n, fixed_n, transform, sitk.sitkLinear, 0.0, sitk.sitkFloat32)
    warped_label = sitk.Resample(moving_label, fixed, transform, sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8)
    elapsed = time.perf_counter() - start

    fixed_arr = sitk.GetArrayFromImage(fixed_n)
    moving_arr = sitk.GetArrayFromImage(moving_n)
    warped_arr = sitk.GetArrayFromImage(warped_image)
    return (
        warped_image,
        warped_label,
        {
            "runtime_seconds": float(elapsed),
            "metric_value": float(registration.GetMetric()),
            "image_ncc_before": ncc(fixed_arr, moving_arr),
            "image_ncc_after": ncc(fixed_arr, warped_arr),
            "folding_voxels": int(np.sum(jac_arr <= 0.0)),
            "jacobian_min": float(np.min(jac_arr)),
            "jacobian_mean": float(np.mean(jac_arr)),
            "displacement_mean": float(np.mean(disp_mag)),
            "displacement_max": float(np.max(disp_mag)),
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Run a bounded SimpleITK Cine motion fallback probe.")
    ap.add_argument("--safe-cases", type=Path, default=Path("results/20260703_cine_motion/safe_cases_used.csv"))
    ap.add_argument(
        "--adapter-root",
        type=Path,
        default=Path("results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr"),
    )
    ap.add_argument("--output-dir", type=Path, default=Path("results/20260704_cine_temporal_motion_resume"))
    ap.add_argument("--max-cases", type=int, default=8)
    ap.add_argument("--iterations", type=int, default=12)
    ap.add_argument("--smoothing", type=float, default=1.0)
    args = ap.parse_args()

    rows = read_rows(args.safe_cases)
    case_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    command = {
        "safe_cases": str(args.safe_cases),
        "adapter_root": str(args.adapter_root),
        "output_dir": str(args.output_dir),
        "max_cases": args.max_cases,
        "iterations": args.iterations,
        "smoothing": args.smoothing,
        "simpleitk_version": sitk.Version_VersionString(),
    }

    used = 0
    for row in rows:
        if used >= args.max_cases:
            break
        frame_tokens = [tok for tok in str(row.get("flow_frame_indices", "")).split(",") if tok.strip()]
        if not frame_tokens:
            continue
        moving_frame_index = int(frame_tokens[0])
        center = row["center"]
        case_id = row["case_id"]
        ref_pred_path = Path(row["reference_prediction_path"])
        moving_pred_path = prediction_path(args.adapter_root, center, case_id, moving_frame_index)
        cine_path = Path(row["cine_path"])
        label_path = Path(row["label_path"])
        if not (cine_path.is_file() and label_path.is_file() and ref_pred_path.is_file() and moving_pred_path.is_file()):
            continue

        cine = sitk.ReadImage(str(cine_path))
        fixed = extract_frame(cine, 0)
        moving = extract_frame(cine, moving_frame_index)
        ref_pred = compact_pred_from_cinema(sitk.ReadImage(str(ref_pred_path)))
        moving_pred = compact_pred_from_cinema(sitk.ReadImage(str(moving_pred_path)))
        gt = compact_gt(sitk.ReadImage(str(label_path)))
        warped_image, warped_pred, stats = run_demons_probe(
            fixed=fixed,
            moving=moving,
            moving_label=moving_pred,
            iterations=args.iterations,
            smoothing=args.smoothing,
        )
        del warped_image
        ref_arr = sitk.GetArrayFromImage(ref_pred)
        moving_arr = sitk.GetArrayFromImage(moving_pred)
        warped_arr = sitk.GetArrayFromImage(warped_pred)
        gt_arr = sitk.GetArrayFromImage(gt)
        used += 1
        for cls, name in CLASS_NAMES.items():
            case_rows.append(
                {
                    "variant": "simpleitk_demons_displacement_fallback",
                    "case_id": case_id,
                    "center": center,
                    "moving_frame_index": moving_frame_index,
                    "class_id": cls,
                    "metric_name": name,
                    "reference_dice_to_gt": dice(ref_arr == cls, gt_arr == cls),
                    "moving_dice_to_gt": dice(moving_arr == cls, gt_arr == cls),
                    "warped_dice_to_gt": dice(warped_arr == cls, gt_arr == cls),
                    "moving_consistency_to_reference": dice(moving_arr == cls, ref_arr == cls),
                    "warped_consistency_to_reference": dice(warped_arr == cls, ref_arr == cls),
                    "warped_component_count": component_count(warped_arr == cls),
                    "warped_voxels": int((warped_arr == cls).sum()),
                    **stats,
                }
            )

    for cls, name in CLASS_NAMES.items():
        subset = [r for r in case_rows if int(r["class_id"]) == cls]
        summary_rows.append(
            {
                "variant": "simpleitk_demons_displacement_fallback",
                "class_id": cls,
                "metric_name": name,
                "n": len(subset),
                "reference_dice_to_gt_mean": finite_mean([r["reference_dice_to_gt"] for r in subset]),
                "moving_dice_to_gt_mean": finite_mean([r["moving_dice_to_gt"] for r in subset]),
                "warped_dice_to_gt_mean": finite_mean([r["warped_dice_to_gt"] for r in subset]),
                "moving_consistency_to_reference_mean": finite_mean(
                    [r["moving_consistency_to_reference"] for r in subset]
                ),
                "warped_consistency_to_reference_mean": finite_mean(
                    [r["warped_consistency_to_reference"] for r in subset]
                ),
                "image_ncc_before_mean": finite_mean([r["image_ncc_before"] for r in subset]),
                "image_ncc_after_mean": finite_mean([r["image_ncc_after"] for r in subset]),
                "folding_voxels_mean": finite_mean([r["folding_voxels"] for r in subset]),
                "jacobian_min_min": min(
                    [float(r["jacobian_min"]) for r in subset if r["jacobian_min"] is not None],
                    default=None,
                ),
                "displacement_mean": finite_mean([r["displacement_mean"] for r in subset]),
                "runtime_seconds_mean": finite_mean([r["runtime_seconds"] for r in subset]),
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(case_rows, args.output_dir / "simpleitk_demons_case_metrics.csv")
    write_csv(summary_rows, args.output_dir / "simpleitk_demons_summary.csv")
    command["cases_used"] = used
    (args.output_dir / "simpleitk_demons_command.json").write_text(
        json.dumps(command, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({"cases_used": used, "summary": summary_rows}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
