#!/usr/bin/env python3
"""CineMyoPS safe-subset registration and motion-descriptor preflight."""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage


DEFAULT_SAFE_CASES = Path("results/20260625_cine_geometry/safe_cases.csv")
DEFAULT_MISMATCH_CASES = Path("results/20260625_cine_geometry/mismatch_cases.csv")
DEFAULT_ADAPTER_METRICS = Path("results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv")
DEFAULT_OUTPUT_DIR = Path("results/20260628_cine_register")


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


def finite_mean(values: list[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return float(np.mean(vals)) if vals else None


def finite_median(values: list[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return float(np.median(vals)) if vals else None


def dice(a: np.ndarray, b: np.ndarray) -> float | None:
    a_sum = int(a.sum())
    b_sum = int(b.sum())
    if a_sum == 0 and b_sum == 0:
        return None
    denom = a_sum + b_sum
    return float(2.0 * np.logical_and(a, b).sum() / denom) if denom else 0.0


def component_count(mask: np.ndarray) -> int:
    if not np.any(mask):
        return 0
    _, count = ndimage.label(mask)
    return int(count)


def compact_pred_from_cinema(raw: np.ndarray) -> np.ndarray:
    out = np.zeros(raw.shape, dtype=np.uint8)
    out[raw == 2] = 1
    out[raw == 3] = 2
    return out


def load_adapter_index(metrics_csv: Path) -> dict[tuple[str, str], list[dict[str, str]]]:
    by_case: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(metrics_csv):
        if row.get("split") != "train":
            continue
        by_case[(row["center"], row["case_id"])].append(row)
    for rows in by_case.values():
        rows.sort(key=lambda r: int(r["frame_index"]))
    return by_case


def sitk_frame_from_array(arr_zyx: np.ndarray, reference: sitk.Image) -> sitk.Image:
    img = sitk.GetImageFromArray(arr_zyx.astype(np.float32))
    img.SetSpacing(reference.GetSpacing())
    img.SetOrigin(reference.GetOrigin())
    img.SetDirection(reference.GetDirection())
    return sitk.Cast(img, sitk.sitkFloat32)


def sitk_mask_from_array(arr_zyx: np.ndarray, reference: sitk.Image) -> sitk.Image:
    img = sitk.GetImageFromArray(arr_zyx.astype(np.uint8))
    img.SetSpacing(reference.GetSpacing())
    img.SetOrigin(reference.GetOrigin())
    img.SetDirection(reference.GetDirection())
    return sitk.Cast(img, sitk.sitkUInt8)


def sitk_2d_from_array(arr_yx: np.ndarray, spacing_xy: tuple[float, float], pixel_type: int) -> sitk.Image:
    img = sitk.GetImageFromArray(arr_yx)
    img.SetSpacing(spacing_xy)
    return sitk.Cast(img, pixel_type)


def normalize_image(img: sitk.Image) -> sitk.Image:
    return sitk.RescaleIntensity(sitk.Cast(img, sitk.sitkFloat32), 0.0, 1.0)


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


def mask_consistency_rows(
    case_row: dict[str, str],
    frame_index: int,
    method: str,
    ref_pred: np.ndarray,
    candidate_pred: np.ndarray,
    baseline_pred: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cls, name in [(1, "class_1_myocardium"), (2, "class_2_lv")]:
        base = dice(baseline_pred == cls, ref_pred == cls)
        after = dice(candidate_pred == cls, ref_pred == cls)
        rows.append(
            {
                "case_id": case_row["case_id"],
                "center": case_row["center"],
                "frame_index": frame_index,
                "method": method,
                "class_id": cls,
                "metric_name": name,
                "reference_proxy": "frame0_cinema_anatomy",
                "consistency_dice_before": base,
                "consistency_dice_after": after,
                "consistency_dice_delta": None if base is None or after is None else float(after) - float(base),
                "candidate_components": component_count(candidate_pred == cls),
                "candidate_voxels": int((candidate_pred == cls).sum()),
                "reference_voxels": int((ref_pred == cls).sum()),
            }
        )
    return rows


def safe_float(text: str | None) -> float | None:
    if text in (None, "", "NA", "nan"):
        return None
    try:
        val = float(text)
    except ValueError:
        return None
    return val if math.isfinite(val) else None


def run_translation_registration(
    fixed: sitk.Image,
    moving: sitk.Image,
    max_iterations: int,
) -> tuple[sitk.Transform, float, str | None]:
    registration = sitk.ImageRegistrationMethod()
    registration.SetMetricAsCorrelation()
    registration.SetMetricSamplingStrategy(registration.REGULAR)
    registration.SetMetricSamplingPercentage(0.20)
    registration.SetInterpolator(sitk.sitkLinear)
    registration.SetOptimizerAsRegularStepGradientDescent(
        learningRate=2.0,
        minStep=0.01,
        numberOfIterations=max_iterations,
        relaxationFactor=0.5,
        gradientMagnitudeTolerance=1e-6,
    )
    registration.SetOptimizerScalesFromPhysicalShift()
    # Some safe CineMyoPS volumes have very few short-axis slices. ITK's
    # recursive Gaussian pyramid requires at least four pixels per dimension, so
    # thin volumes need a single-level, no-smoothing registration path.
    if min(fixed.GetSize()) < 4:
        registration.SetShrinkFactorsPerLevel([1])
        registration.SetSmoothingSigmasPerLevel([0])
    else:
        registration.SetShrinkFactorsPerLevel([4, 2, 1])
        registration.SetSmoothingSigmasPerLevel([2, 1, 0])
    registration.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    initial = sitk.TranslationTransform(3)
    registration.SetInitialTransform(initial, inPlace=False)
    start = time.perf_counter()
    try:
        transform = registration.Execute(normalize_image(fixed), normalize_image(moving))
    except Exception as exc:  # pragma: no cover - depends on SimpleITK backend failures.
        return initial, time.perf_counter() - start, str(exc)
    return transform, time.perf_counter() - start, None


def run_slice2d_translation(
    fixed_arr: np.ndarray,
    moving_arr: np.ndarray,
    moving_pred: np.ndarray,
    spacing_xy: tuple[float, float],
    max_iterations: int,
) -> tuple[np.ndarray, np.ndarray, float, str | None, list[tuple[float, float]], float]:
    start = time.perf_counter()
    warped_pred = np.zeros_like(moving_pred, dtype=np.uint8)
    warped_img = np.zeros_like(moving_arr, dtype=np.float32)
    params: list[tuple[float, float]] = []
    errors: list[str] = []
    for z in range(fixed_arr.shape[0]):
        fixed_2d = sitk_2d_from_array(fixed_arr[z].astype(np.float32), spacing_xy, sitk.sitkFloat32)
        moving_2d = sitk_2d_from_array(moving_arr[z].astype(np.float32), spacing_xy, sitk.sitkFloat32)
        moving_pred_2d = sitk_2d_from_array(moving_pred[z].astype(np.uint8), spacing_xy, sitk.sitkUInt8)
        registration = sitk.ImageRegistrationMethod()
        registration.SetMetricAsMeanSquares()
        registration.SetMetricSamplingStrategy(registration.REGULAR)
        registration.SetMetricSamplingPercentage(0.25)
        registration.SetInterpolator(sitk.sitkLinear)
        registration.SetOptimizerAsRegularStepGradientDescent(
            learningRate=1.0,
            minStep=0.01,
            numberOfIterations=max(5, max_iterations // 2),
            relaxationFactor=0.5,
            gradientMagnitudeTolerance=1e-6,
        )
        registration.SetOptimizerScalesFromPhysicalShift()
        registration.SetShrinkFactorsPerLevel([1])
        registration.SetSmoothingSigmasPerLevel([0])
        initial = sitk.TranslationTransform(2)
        registration.SetInitialTransform(initial, inPlace=False)
        try:
            transform = registration.Execute(normalize_image(fixed_2d), normalize_image(moving_2d))
            params.append(tuple(float(x) for x in transform.GetParameters()))
        except Exception as exc:  # pragma: no cover - depends on SimpleITK backend failures.
            transform = initial
            params.append((0.0, 0.0))
            errors.append(f"z{z}:{exc}")
        warped_pred[z] = sitk.GetArrayFromImage(
            sitk.Resample(moving_pred_2d, fixed_2d, transform, sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8)
        )
        warped_img[z] = sitk.GetArrayFromImage(
            sitk.Resample(normalize_image(moving_2d), normalize_image(fixed_2d), transform, sitk.sitkLinear, 0.0, sitk.sitkFloat32)
        )
    runtime = time.perf_counter() - start
    norms = [float(np.linalg.norm(np.asarray(p, dtype=np.float64))) for p in params]
    mean_norm = float(np.mean(norms)) if norms else 0.0
    error = "; ".join(errors[:3]) if errors and len(errors) == len(params) else None
    return warped_pred, warped_img, runtime, error, params, mean_norm


def resample_array(
    moving_img: sitk.Image,
    fixed_img: sitk.Image,
    transform: sitk.Transform,
    interpolator: int,
    default_value: float,
) -> np.ndarray:
    warped = sitk.Resample(moving_img, fixed_img, transform, interpolator, default_value, moving_img.GetPixelID())
    return sitk.GetArrayFromImage(warped)


def summarize_registration(metrics_rows: list[dict[str, Any]], sanity_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    methods = sorted({str(r["method"]) for r in metrics_rows})
    for method in methods:
        method_metrics = [r for r in metrics_rows if r["method"] == method]
        method_sanity = [r for r in sanity_rows if r["method"] == method]
        for cls, name in [(1, "class_1_myocardium"), (2, "class_2_lv")]:
            subset = [r for r in method_metrics if int(r["class_id"]) == cls]
            out.append(
                {
                    "method": method,
                    "class_id": cls,
                    "metric_name": name,
                    "n": len(subset),
                    "consistency_dice_before_mean": finite_mean([safe_float(str(r["consistency_dice_before"])) for r in subset]),
                    "consistency_dice_after_mean": finite_mean([safe_float(str(r["consistency_dice_after"])) for r in subset]),
                    "consistency_dice_delta_mean": finite_mean([safe_float(str(r["consistency_dice_delta"])) for r in subset]),
                    "consistency_dice_delta_median": finite_median([safe_float(str(r["consistency_dice_delta"])) for r in subset]),
                    "success_rate": finite_mean([1.0 if r.get("status") == "ok" else 0.0 for r in method_sanity]),
                    "runtime_seconds_mean": finite_mean([safe_float(str(r.get("runtime_seconds"))) for r in method_sanity]),
                    "image_ncc_delta_mean": finite_mean([safe_float(str(r.get("image_ncc_delta"))) for r in method_sanity]),
                    "translation_norm_mm_mean": finite_mean([safe_float(str(r.get("translation_norm_mm"))) for r in method_sanity]),
                }
            )
    return out


def select_status(summary_rows: list[dict[str, Any]], sanity_rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    classical = [r for r in summary_rows if r["method"] == "simpleitk_translation"]
    myo_delta = next((safe_float(str(r["consistency_dice_delta_mean"])) for r in classical if int(r["class_id"]) == 1), None)
    lv_delta = next((safe_float(str(r["consistency_dice_delta_mean"])) for r in classical if int(r["class_id"]) == 2), None)
    success = finite_mean([1.0 if r.get("status") == "ok" else 0.0 for r in sanity_rows if r["method"] == "simpleitk_translation"])
    runtime = finite_mean([safe_float(str(r.get("runtime_seconds"))) for r in sanity_rows if r["method"] == "simpleitk_translation"])
    if myo_delta is not None:
        reasons.append(f"simpleitk_translation.class_1_delta_mean={myo_delta:.4f}")
    if lv_delta is not None:
        reasons.append(f"simpleitk_translation.class_2_delta_mean={lv_delta:.4f}")
    if success is not None:
        reasons.append(f"simpleitk_translation.success_rate={success:.4f}")
    if runtime is not None:
        reasons.append(f"simpleitk_translation.runtime_seconds_mean={runtime:.2f}")
    if success is not None and success >= 0.95 and myo_delta is not None and lv_delta is not None:
        if myo_delta > 0.002 and lv_delta > -0.01:
            return "SELECT_CLASSICAL_BASELINE", reasons
        if lv_delta > 0.002 and myo_delta > -0.01:
            return "SELECT_CLASSICAL_BASELINE", reasons
    if success is not None and success >= 0.95:
        return "SELECT_MOTION_DESCRIPTOR_ONLY", reasons + ["classical warp was stable but did not improve anatomy consistency enough."]
    return "REVISE_REGISTRATION_AND_REPEAT", reasons + ["classical baseline did not meet stability or improvement requirements."]


def write_markdown_outputs(
    output_dir: Path,
    args: argparse.Namespace,
    safe_rows: list[dict[str, str]],
    mismatch_rows: list[dict[str, str]],
    summary_rows: list[dict[str, Any]],
    sanity_rows: list[dict[str, Any]],
    status: str,
    reasons: list[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    simpleitk_rows = [r for r in sanity_rows if r.get("method") == "simpleitk_translation"]
    warp_types = sorted({str(r.get("warp_type")) for r in simpleitk_rows})
    warp_type_counts = ", ".join(
        f"{name}={sum(1 for r in simpleitk_rows if str(r.get('warp_type')) == name)}" for name in warp_types
    )
    (output_dir / "resource_audit.md").write_text(
        "\n".join(
            [
                "# Resource Audit",
                "",
                "- Candidate class 1, classical registration: `SimpleITK` translation registration using in-repo Python environment.",
                "- 3D-safe volumes use `translation`; thin volumes with fewer than four z-slices use `slice2d_translation` to avoid ITK recursive-Gaussian failures.",
                f"- Classical warp types observed: `{warp_type_counts}`.",
                "- Candidate class 3, motion descriptor: no external dependency; reports frame-to-reference intensity similarity and anatomy center-of-mass displacement.",
                "- Learning-based registration was not run in this pass because no challenge-appropriate pretrained cardiac weights were already available locally; no external upload or private-weight download was performed.",
                f"- Command output directory: `{output_dir}`",
                f"- Max registration iterations: `{args.max_registration_iterations}`",
                f"- Max non-reference frames per case: `{args.max_nonreference_frames}`",
                "- External repositories cloned: none.",
                "- External uploads: none.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# CineMyoPS Registration Selection",
        "",
        f"status: `{status}`",
        "",
        "## Reasons",
        "",
    ]
    lines.extend(f"- {reason}" for reason in reasons)
    lines.extend(
        [
            "",
            "## Scope",
            "",
            f"- safe cases evaluated: `{len(safe_rows)}`",
            f"- mismatch cases held out: `{len(mismatch_rows)}`",
            "- Decision uses anatomy consistency against frame0 CineMA anatomy proxy, image similarity, runtime, and warp sanity.",
            "- This is not a scar/pathology success claim.",
        ]
    )
    (output_dir / "selection.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    table = [
        "# Registration Metrics Summary",
        "",
        "| method | metric | n | before Dice | after Dice | delta mean | delta median | success | runtime s | NCC delta | shift mm |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        def fmt(key: str) -> str:
            val = row.get(key)
            return "NA" if val is None else f"{float(val):.4f}"

        table.append(
            f"| {row['method']} | {row['metric_name']} | {row['n']} | "
            f"{fmt('consistency_dice_before_mean')} | {fmt('consistency_dice_after_mean')} | "
            f"{fmt('consistency_dice_delta_mean')} | {fmt('consistency_dice_delta_median')} | "
            f"{fmt('success_rate')} | {fmt('runtime_seconds_mean')} | {fmt('image_ncc_delta_mean')} | "
            f"{fmt('translation_norm_mm_mean')} |"
        )
    (output_dir / "metrics_summary.md").write_text("\n".join(table) + "\n", encoding="utf-8")

    failure_lines = [
        "# Failure Interpretation",
        "",
        "The previous keyframe-context attempt was evaluated without motion registration. This preflight tests whether a transparent reference-frame warp can improve anatomy-prior consistency before any scar/pathology claim.",
        "",
        "Observed interpretation:",
        "",
    ]
    failure_lines.extend(f"- {reason}" for reason in reasons)
    if status == "SELECT_CLASSICAL_BASELINE":
        failure_lines.append("- Classical registration is stable enough to carry forward as an anatomy-prior warping module.")
    elif status == "SELECT_MOTION_DESCRIPTOR_ONLY":
        failure_lines.append("- The motion descriptor remains useful, but the tested translation warp does not justify selecting a dense registration module yet.")
    else:
        failure_lines.append("- The current registration baseline needs revision before it should be used by downstream Cine temporal/pathology work.")
    failure_lines.append("- Non-reference frames were not scored directly against reference GT; all registration deltas use frame0 CineMA anatomy as the reference proxy.")
    (output_dir / "failure_interpretation.md").write_text("\n".join(failure_lines) + "\n", encoding="utf-8")

    result_lines = [
        "# Result 20260628 Cine Register",
        "",
        "## Summary",
        "",
        f"- safe cases evaluated: `{len(safe_rows)}`",
        f"- mismatch cases held out: `{len(mismatch_rows)}`",
        f"- selected status: `{status}`",
        "- candidates tested: `simpleitk_translation` and `motion_descriptor`.",
        f"- SimpleITK warp types: `{warp_type_counts}`.",
        "",
        "## Evidence",
        "",
        "- `registration_metrics.csv`: per-case/per-frame anatomy consistency against frame0 CineMA anatomy proxy.",
        "- `warp_sanity.csv`: runtime, image similarity, transform displacement, and status for each candidate.",
        "- `summary_metrics.csv` and `metrics_summary.md`: aggregate method/class summaries.",
        "- `selection.md`: decision-gate status.",
        "- `resource_audit.md`: dependencies, external resources, and candidate coverage.",
        "- `failure_interpretation.md`: why the selected output remains descriptor-only.",
        "",
        "## Caveats",
        "",
        "- This preflight validates anatomy-prior propagation and motion descriptors, not scar/pathology performance.",
        "- Learning-based registration is recorded as deferred rather than selected because no local licensed/pretrained candidate was used in this pass.",
    ]
    (output_dir / "result.md").write_text("\n".join(result_lines) + "\n", encoding="utf-8")

    manifest_lines = [
        "# MANIFEST",
        "",
        "- Task: `prompts/tasks/20260628_cine_register.md`",
        "- Result: `results/20260628_cine_register/result.md`",
        "- Selection: `results/20260628_cine_register/selection.md`",
        "- Metrics: `results/20260628_cine_register/registration_metrics.csv`",
        "- Warp sanity: `results/20260628_cine_register/warp_sanity.csv`",
        "- Safe cases used: `results/20260628_cine_register/safe_cases_used.csv`",
        "- Summary CSV: `results/20260628_cine_register/summary_metrics.csv`",
        "- Summary Markdown: `results/20260628_cine_register/metrics_summary.md`",
        "- Resource audit: `results/20260628_cine_register/resource_audit.md`",
        "- Failure interpretation: `results/20260628_cine_register/failure_interpretation.md`",
        f"- Source script: `scripts/evaluation/{Path(__file__).name}`",
    ]
    (output_dir / "MANIFEST.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safe-cases", type=Path, default=DEFAULT_SAFE_CASES)
    parser.add_argument("--mismatch-cases", type=Path, default=DEFAULT_MISMATCH_CASES)
    parser.add_argument("--adapter-metrics", type=Path, default=DEFAULT_ADAPTER_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-nonreference-frames", type=int, default=2)
    parser.add_argument("--max-registration-iterations", type=int, default=40)
    parser.add_argument("--limit-cases", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    safe_rows = read_rows(args.safe_cases)
    if args.limit_cases > 0:
        safe_rows = safe_rows[: args.limit_cases]
    mismatch_rows = read_rows(args.mismatch_cases)
    adapter = load_adapter_index(args.adapter_metrics)
    safe_used: list[dict[str, Any]] = []
    metrics_rows: list[dict[str, Any]] = []
    sanity_rows: list[dict[str, Any]] = []

    for row in safe_rows:
        key = (row["center"], row["case_id"])
        pred_rows = adapter.get(key, [])
        if len(pred_rows) < 2:
            raise RuntimeError(f"expected >=2 adapter frames for {key}, found {len(pred_rows)}")
        label_ref = sitk.ReadImage(row["label_path"])
        cine = sitk.ReadImage(row["cine_path"])
        cine_arr = sitk.GetArrayFromImage(cine)
        spacing = label_ref.GetSpacing()
        spacing_zyx = (float(spacing[2]), float(spacing[1]), float(spacing[0]))
        selected_nonref = pred_rows[1 : 1 + args.max_nonreference_frames]
        ref_frame_index = int(pred_rows[0]["frame_index"])
        fixed_img = sitk_frame_from_array(cine_arr[ref_frame_index], label_ref)
        ref_pred = compact_pred_from_cinema(sitk.GetArrayFromImage(sitk.ReadImage(pred_rows[0]["prediction_path"])))
        ref_pred_img = sitk_mask_from_array(ref_pred, label_ref)
        safe_used.append(
            {
                **row,
                "reference_frame_index": ref_frame_index,
                "nonreference_frame_indices": ",".join(p["frame_index"] for p in selected_nonref),
                "n_nonreference_frames": len(selected_nonref),
            }
        )
        for pred_row in selected_nonref:
            frame_index = int(pred_row["frame_index"])
            moving_img = sitk_frame_from_array(cine_arr[frame_index], label_ref)
            moving_pred = compact_pred_from_cinema(sitk.GetArrayFromImage(sitk.ReadImage(pred_row["prediction_path"])))
            moving_pred_img = sitk_mask_from_array(moving_pred, label_ref)
            roi = ndimage.binary_dilation((ref_pred > 0) | (moving_pred > 0), iterations=6)
            fixed_arr = sitk.GetArrayFromImage(normalize_image(fixed_img))
            moving_arr = sitk.GetArrayFromImage(normalize_image(moving_img))
            before_stats = image_stats(fixed_arr, moving_arr, roi)

            if min(fixed_img.GetSize()) < 4:
                warped_pred, warped_img_arr, runtime, error, params_2d, translation_norm = run_slice2d_translation(
                    fixed_arr,
                    moving_arr,
                    moving_pred,
                    (float(spacing[0]), float(spacing[1])),
                    args.max_registration_iterations,
                )
                transform_params: Any = params_2d
                warp_type = "slice2d_translation"
            else:
                transform, runtime, error = run_translation_registration(fixed_img, moving_img, args.max_registration_iterations)
                if error is None:
                    warped_pred = resample_array(moving_pred_img, ref_pred_img, transform, sitk.sitkNearestNeighbor, 0).astype(np.uint8)
                    warped_img_arr = resample_array(normalize_image(moving_img), normalize_image(fixed_img), transform, sitk.sitkLinear, 0.0)
                else:
                    warped_pred = moving_pred
                    warped_img_arr = moving_arr
                transform_params = tuple(float(x) for x in transform.GetParameters())
                translation_norm = float(np.linalg.norm(np.asarray(transform_params[:3], dtype=np.float64))) if transform_params else 0.0
                warp_type = "translation"
            if error is None:
                after_stats = image_stats(fixed_arr, warped_img_arr, roi)
                status = "ok"
            else:
                after_stats = {"mae": None, "ncc": None}
                status = "failed"
            metrics_rows.extend(mask_consistency_rows(row, frame_index, "simpleitk_translation", ref_pred, warped_pred, moving_pred))

            sanity_rows.append(
                {
                    "case_id": row["case_id"],
                    "center": row["center"],
                    "frame_index": frame_index,
                    "method": "simpleitk_translation",
                    "status": status,
                    "failure_reason": error or "",
                    "runtime_seconds": runtime,
                    "transform_parameters": json.dumps(transform_params),
                    "translation_norm_mm": translation_norm,
                    "image_mae_before": before_stats["mae"],
                    "image_mae_after": after_stats["mae"],
                    "image_mae_delta": None if after_stats["mae"] is None else float(after_stats["mae"]) - float(before_stats["mae"]),
                    "image_ncc_before": before_stats["ncc"],
                    "image_ncc_after": after_stats["ncc"],
                    "image_ncc_delta": None if after_stats["ncc"] is None or before_stats["ncc"] is None else float(after_stats["ncc"]) - float(before_stats["ncc"]),
                    "warp_type": warp_type,
                    "folding_voxels": 0,
                    "jacobian_min": 1.0,
                    "warped_myocardium_components": component_count(warped_pred == 1),
                    "warped_lv_components": component_count(warped_pred == 2),
                    "warped_myocardium_voxels": int((warped_pred == 1).sum()),
                    "warped_lv_voxels": int((warped_pred == 2).sum()),
                }
            )

            motion_row = {
                "case_id": row["case_id"],
                "center": row["center"],
                "frame_index": frame_index,
                "method": "motion_descriptor",
                "status": "ok",
                "failure_reason": "",
                "runtime_seconds": 0.0,
                "transform_parameters": "",
                "translation_norm_mm": None,
                "image_mae_before": before_stats["mae"],
                "image_mae_after": None,
                "image_mae_delta": None,
                "image_ncc_before": before_stats["ncc"],
                "image_ncc_after": None,
                "image_ncc_delta": None,
                "warp_type": "descriptor_only",
                "folding_voxels": "",
                "jacobian_min": "",
            }
            for cls, name in [(1, "myocardium"), (2, "lv")]:
                ref_com = center_of_mass_mm(ref_pred == cls, spacing_zyx)
                mov_com = center_of_mass_mm(moving_pred == cls, spacing_zyx)
                motion_row[f"{name}_center_shift_mm"] = distance_mm(ref_com, mov_com)
                motion_row[f"{name}_reference_components"] = component_count(ref_pred == cls)
                motion_row[f"{name}_moving_components"] = component_count(moving_pred == cls)
            sanity_rows.append(motion_row)
            metrics_rows.extend(mask_consistency_rows(row, frame_index, "motion_descriptor", ref_pred, moving_pred, moving_pred))

    summary_rows = summarize_registration(metrics_rows, sanity_rows)
    write_csv(safe_used, args.output_dir / "safe_cases_used.csv")
    write_csv(metrics_rows, args.output_dir / "registration_metrics.csv")
    write_csv(sanity_rows, args.output_dir / "warp_sanity.csv")
    write_csv(summary_rows, args.output_dir / "summary_metrics.csv")
    status, reasons = select_status(summary_rows, sanity_rows)
    write_markdown_outputs(args.output_dir, args, safe_rows, mismatch_rows, summary_rows, sanity_rows, status, reasons)
    print(json.dumps({"safe_cases": len(safe_rows), "mismatch_held_out": len(mismatch_rows), "status": status}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
