#!/usr/bin/env python3
"""M7 continued Cine registration repair evidence.

This is a bounded diagnostic repair attempt. It reads existing CineMyoPS train
safe cases and CineMA frame predictions, runs a small SimpleITK Demons
non-reference registration probe, and writes reviewer-visible evidence. It does
not train VoxelMorph, package validation data, upload, or promote a route.
"""

from __future__ import annotations

import argparse
import csv
import os
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TASK_KEY = "20260705_srr_v3_m7_training_and_cine_utilization"
OUT_ROOT = REPO_ROOT / "results" / TASK_KEY
SAFE_CASES = REPO_ROOT / "results/20260703_cine_motion/safe_cases_used.csv"
CINEMA_ROOT = REPO_ROOT / "results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr"
PRED_ROOT = CINEMA_ROOT / "predictions/train"
RUNTIME_ROOT = OUT_ROOT / "runtime/cine_registration_repair"
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp/matplotlib"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def frame_path(case_id: str, center: str, frame: int) -> Path:
    return PRED_ROOT / center / f"{case_id}_t{frame:02d}_cinema_acdc_s0.nii.gz"


def extract_frame(cine_path: Path, frame: int) -> sitk.Image:
    cine = sitk.ReadImage(str(cine_path))
    if cine.GetDimension() != 4:
        raise ValueError(f"Expected 4D cine image, got dimension={cine.GetDimension()} for {cine_path}")
    size = list(cine.GetSize())
    index = [0, 0, 0, frame]
    extract_size = [size[0], size[1], size[2], 0]
    extractor = sitk.ExtractImageFilter()
    extractor.SetSize(extract_size)
    extractor.SetIndex(index)
    extractor.SetDirectionCollapseToStrategy(extractor.DIRECTIONCOLLAPSETOSUBMATRIX)
    return extractor.Execute(cine)


def normalized_float(image: sitk.Image) -> sitk.Image:
    image = sitk.Cast(image, sitk.sitkFloat32)
    return sitk.RescaleIntensity(image, 0.0, 1.0)


def mask_array(seg: sitk.Image, label: int) -> np.ndarray:
    return (sitk.GetArrayFromImage(seg) == label)


def dice(seg_a: sitk.Image, seg_b: sitk.Image, label: int) -> float:
    a = mask_array(seg_a, label)
    b = mask_array(seg_b, label)
    denom = int(a.sum()) + int(b.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(a, b).sum() / denom)


def hd95(seg_a: sitk.Image, seg_b: sitk.Image, label: int) -> float:
    a = sitk.Cast(seg_a == label, sitk.sitkUInt8)
    b = sitk.Cast(seg_b == label, sitk.sitkUInt8)
    a_count = int(sitk.GetArrayViewFromImage(a).sum())
    b_count = int(sitk.GetArrayViewFromImage(b).sum())
    if a_count == 0 and b_count == 0:
        return 0.0
    if a_count == 0 or b_count == 0:
        return float("inf")
    a_surface = sitk.LabelContour(a)
    b_surface = sitk.LabelContour(b)
    a_to_b = sitk.Abs(sitk.SignedMaurerDistanceMap(b, insideIsPositive=False, squaredDistance=False, useImageSpacing=True))
    b_to_a = sitk.Abs(sitk.SignedMaurerDistanceMap(a, insideIsPositive=False, squaredDistance=False, useImageSpacing=True))
    dists = np.concatenate(
        [
            sitk.GetArrayFromImage(a_to_b)[sitk.GetArrayFromImage(a_surface) > 0],
            sitk.GetArrayFromImage(b_to_a)[sitk.GetArrayFromImage(b_surface) > 0],
        ]
    )
    if dists.size == 0:
        return float("inf")
    return float(np.percentile(dists, 95))


def image_ncc(fixed: sitk.Image, moving: sitk.Image) -> float:
    a = sitk.GetArrayFromImage(normalized_float(fixed)).astype(np.float64, copy=False).ravel()
    b = sitk.GetArrayFromImage(normalized_float(moving)).astype(np.float64, copy=False).ravel()
    a = a - a.mean()
    b = b - b.mean()
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def warp_segmentation(moving_seg: sitk.Image, fixed: sitk.Image, displacement: sitk.Image) -> sitk.Image:
    transform = sitk.DisplacementFieldTransform(displacement)
    return sitk.Resample(moving_seg, fixed, transform, sitk.sitkNearestNeighbor, 0, moving_seg.GetPixelID())


def sitk_to_ants(image: sitk.Image, pixel_type: np.dtype = np.float32) -> Any:
    import ants

    return ants.from_numpy(sitk.GetArrayFromImage(image).astype(pixel_type, copy=False))


def ants_to_sitk_seg(image: Any, reference: sitk.Image) -> sitk.Image:
    out = sitk.GetImageFromArray(image.numpy().astype(np.uint8, copy=False))
    out.CopyInformation(reference)
    return out


def displacement_stats(displacement: sitk.Image) -> dict[str, object]:
    arr = sitk.GetArrayFromImage(displacement).astype(np.float32, copy=False)
    mag = np.sqrt(np.sum(arr * arr, axis=-1))
    stats: dict[str, object] = {
        "displacement_mean": float(np.mean(mag)),
        "displacement_p95": float(np.percentile(mag, 95)),
        "displacement_max": float(np.max(mag)),
        "jacobian_fold_voxels": "EVIDENCE_NOT_FOUND",
    }
    try:
        jac = sitk.DisplacementFieldJacobianDeterminant(displacement)
        jac_arr = sitk.GetArrayFromImage(jac)
        stats["jacobian_fold_voxels"] = int((jac_arr <= 0).sum())
    except Exception as exc:
        stats["jacobian_fold_voxels"] = f"EVIDENCE_NOT_FOUND:{type(exc).__name__}"
    return stats


def run_demons(fixed: sitk.Image, moving: sitk.Image, iterations: int) -> tuple[sitk.Image, dict[str, object]]:
    demons = sitk.DemonsRegistrationFilter()
    demons.SetNumberOfIterations(iterations)
    demons.SetStandardDeviations(1.0)
    displacement = demons.Execute(normalized_float(fixed), normalized_float(moving))
    stats = displacement_stats(displacement)
    stats["metric_value"] = float(demons.GetMetric())
    stats["iterations"] = int(demons.GetElapsedIterations())
    return displacement, stats


def run_antspy_syn(fixed: sitk.Image, moving: sitk.Image, moving_seg: sitk.Image, fixed_seg: sitk.Image, iterations: int, outprefix: Path) -> tuple[sitk.Image, dict[str, object]]:
    import ants

    fixed_ants = sitk_to_ants(normalized_float(fixed), np.float32)
    moving_ants = sitk_to_ants(normalized_float(moving), np.float32)
    moving_seg_ants = sitk_to_ants(moving_seg, np.float32)
    outprefix.parent.mkdir(parents=True, exist_ok=True)
    reg = ants.registration(
        fixed=fixed_ants,
        moving=moving_ants,
        type_of_transform="SyNOnly",
        reg_iterations=(iterations, 0, 0),
        outprefix=str(outprefix),
        verbose=False,
        singleprecision=True,
    )
    warped = ants.apply_transforms(
        fixed=fixed_ants,
        moving=moving_seg_ants,
        transformlist=reg["fwdtransforms"],
        interpolator="nearestNeighbor",
        singleprecision=True,
    )
    stats = {
        "iterations": iterations,
        "registration_metric": "ANTsPy_SyNOnly_metric_not_exposed",
        "fwdtransforms": ";".join(reg.get("fwdtransforms", [])),
    }
    return ants_to_sitk_seg(warped, fixed_seg), stats


def selected_pairs(max_cases: int, pairs_per_case: int) -> list[dict[str, object]]:
    rows = read_csv(SAFE_CASES)
    pairs: list[dict[str, object]] = []
    for row in rows:
        frames = [int(x) for x in row.get("descriptor_frame_indices", "").split(",") if x.strip()]
        moving_frames = [f for f in frames if f != 0]
        if len(moving_frames) < pairs_per_case:
            continue
        center = row["center"]
        case_id = row["case_id"]
        cine_path = REPO_ROOT / row["cine_path"]
        if not cine_path.is_file():
            continue
        needed = [frame_path(case_id, center, 0)] + [frame_path(case_id, center, f) for f in moving_frames[:pairs_per_case]]
        if not all(path.is_file() for path in needed):
            continue
        for frame in moving_frames[:pairs_per_case]:
            pairs.append({"case_id": case_id, "center": center, "cine_path": cine_path, "fixed_frame": 0, "moving_frame": frame})
        if len({p["case_id"] for p in pairs}) >= max_cases:
            break
    return pairs


def metrics_row(
    *,
    method: str,
    transform_family: str,
    pair: dict[str, object],
    fixed_img: sitk.Image,
    moving_img: sitk.Image,
    fixed_seg: sitk.Image,
    moving_seg: sitk.Image,
    warped_seg: sitk.Image | None,
    runtime_seconds: float,
    stats: dict[str, object] | None = None,
    failure_reason: str = "",
    decision: str = "NOT_USABLE_DIAGNOSTIC_ROW",
) -> dict[str, object]:
    seg = warped_seg if warped_seg is not None else moving_seg
    stats = stats or {}
    return {
        "method": method,
        "transform_family": transform_family,
        "case_id": pair["case_id"],
        "center": pair["center"],
        "fixed_frame": pair["fixed_frame"],
        "moving_frame": pair["moving_frame"],
        "before_myocardium_dice": dice(fixed_seg, moving_seg, 2),
        "after_myocardium_dice": dice(fixed_seg, seg, 2),
        "before_lv_dice": dice(fixed_seg, moving_seg, 3),
        "after_lv_dice": dice(fixed_seg, seg, 3),
        "before_myocardium_hd95": hd95(fixed_seg, moving_seg, 2),
        "after_myocardium_hd95": hd95(fixed_seg, seg, 2),
        "before_lv_hd95": hd95(fixed_seg, moving_seg, 3),
        "after_lv_hd95": hd95(fixed_seg, seg, 3),
        "image_ncc_before": image_ncc(fixed_img, moving_img),
        "image_ncc_after": "EVIDENCE_NOT_FOUND",
        "displacement_mean": stats.get("displacement_mean", ""),
        "displacement_p95": stats.get("displacement_p95", ""),
        "displacement_max": stats.get("displacement_max", ""),
        "jacobian_fold_voxels": stats.get("jacobian_fold_voxels", ""),
        "registration_metric": stats.get("metric_value", ""),
        "iterations": stats.get("iterations", ""),
        "runtime_seconds": runtime_seconds,
        "failure_reason": failure_reason,
        "m7_continued_decision": decision,
    }


def usability_decision(rows: list[dict[str, object]]) -> tuple[bool, str]:
    repair_rows = [r for r in rows if r["method"] in {"SimpleITK_Demons", "ANTsPy_SyNOnly"}]
    cases = {r["case_id"] for r in repair_rows}
    improved = [
        r
        for r in repair_rows
        if float(r["after_myocardium_dice"]) >= float(r["before_myocardium_dice"])
        and float(r["after_lv_dice"]) >= float(r["before_lv_dice"])
    ]
    if len(cases) >= 3 and len(improved) == len(repair_rows) and repair_rows:
        return True, "USABLE_NONREFERENCE_REGISTRATION_ROW"
    return False, "NOT_USABLE_FOR_TEMPORAL_DICTIONARY"


def append_command(command: str, status: str, purpose: str) -> None:
    path = OUT_ROOT / "commands_run.md"
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Commands Run\n\n| command | status | purpose |\n| --- | --- | --- |\n"
    if "| command | status | purpose |" not in existing:
        existing += "\n| command | status | purpose |\n| --- | --- | --- |\n"
    existing += f"| `{command}` | {status} | {purpose} |\n"
    write_text(path, existing)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-cases", type=int, default=3)
    parser.add_argument("--pairs-per-case", type=int, default=2)
    parser.add_argument("--demons-iterations", type=int, default=20)
    parser.add_argument("--antspy-iterations", type=int, default=10)
    parser.add_argument("--skip-antspy", action="store_true")
    args = parser.parse_args()

    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    pairs = selected_pairs(args.max_cases, args.pairs_per_case)
    rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    if not pairs:
        rows.append(
            {
                "method": "SimpleITK_Demons",
                "transform_family": "dense_displacement",
                "case_id": "EVIDENCE_NOT_FOUND",
                "failure_reason": "No safe cases with frame0 and non-reference CineMA predictions were available.",
                "m7_continued_decision": "NOT_USABLE_FOR_TEMPORAL_DICTIONARY",
            }
        )
    for pair in pairs:
        cine_path = Path(pair["cine_path"])
        fixed_frame = int(pair["fixed_frame"])
        moving_frame = int(pair["moving_frame"])
        center = str(pair["center"])
        case_id = str(pair["case_id"])
        fixed_img = extract_frame(cine_path, fixed_frame)
        moving_img = extract_frame(cine_path, moving_frame)
        fixed_seg = sitk.ReadImage(str(frame_path(case_id, center, fixed_frame)))
        moving_seg = sitk.ReadImage(str(frame_path(case_id, center, moving_frame)))
        rows.append(
            metrics_row(
                method="frame0_identity_control",
                transform_family="identity_reference_control",
                pair=pair,
                fixed_img=fixed_img,
                moving_img=fixed_img,
                fixed_seg=fixed_seg,
                moving_seg=fixed_seg,
                warped_seg=fixed_seg,
                runtime_seconds=0.0,
                failure_reason="reference-frame control row; not a non-reference registration method",
                decision="NOT_USABLE_REFERENCE_CONTROL",
            )
        )
        start = time.monotonic()
        try:
            displacement, stats = run_demons(fixed_img, moving_img, args.demons_iterations)
            warped = warp_segmentation(moving_seg, fixed_img, displacement)
            row = metrics_row(
                method="SimpleITK_Demons",
                transform_family="dense_displacement",
                pair=pair,
                fixed_img=fixed_img,
                moving_img=moving_img,
                fixed_seg=fixed_seg,
                moving_seg=moving_seg,
                warped_seg=warped,
                runtime_seconds=time.monotonic() - start,
                stats=stats,
                decision="NOT_USABLE_PENDING_AGGREGATE_THRESHOLD",
            )
            rows.append(row)
        except Exception as exc:
            rows.append(
                metrics_row(
                    method="SimpleITK_Demons",
                    transform_family="dense_displacement",
                    pair=pair,
                    fixed_img=fixed_img,
                    moving_img=moving_img,
                    fixed_seg=fixed_seg,
                    moving_seg=moving_seg,
                    warped_seg=None,
                    runtime_seconds=time.monotonic() - start,
                    failure_reason=f"{type(exc).__name__}:{exc}",
                    decision="NOT_USABLE_REGISTRATION_FAILED",
                )
            )
        if (not args.skip_antspy) and importlib.util.find_spec("ants") is not None:
            start = time.monotonic()
            try:
                warped, stats = run_antspy_syn(
                    fixed_img,
                    moving_img,
                    moving_seg,
                    fixed_seg,
                    args.antspy_iterations,
                    RUNTIME_ROOT / f"ants_{case_id}_t{moving_frame:02d}_",
                )
                rows.append(
                    metrics_row(
                        method="ANTsPy_SyNOnly",
                        transform_family="SyNOnly_dense_displacement",
                        pair=pair,
                        fixed_img=fixed_img,
                        moving_img=moving_img,
                        fixed_seg=fixed_seg,
                        moving_seg=moving_seg,
                        warped_seg=warped,
                        runtime_seconds=time.monotonic() - start,
                        stats=stats,
                        decision="NOT_USABLE_PENDING_AGGREGATE_THRESHOLD",
                    )
                )
            except Exception as exc:
                rows.append(
                    metrics_row(
                        method="ANTsPy_SyNOnly",
                        transform_family="SyNOnly_dense_displacement",
                        pair=pair,
                        fixed_img=fixed_img,
                        moving_img=moving_img,
                        fixed_seg=fixed_seg,
                        moving_seg=moving_seg,
                        warped_seg=None,
                        runtime_seconds=time.monotonic() - start,
                        failure_reason=f"{type(exc).__name__}:{exc}",
                        decision="NOT_USABLE_REGISTRATION_FAILED",
                    )
                )

    usable, decision = usability_decision(rows)
    for row in rows:
        if row.get("method") in {"SimpleITK_Demons", "ANTsPy_SyNOnly"}:
            row["m7_continued_decision"] = decision

    antspy_available = importlib.util.find_spec("ants") is not None
    voxelmorph_available = importlib.util.find_spec("voxelmorph") is not None
    if (not antspy_available) or args.skip_antspy:
        rows.append(
            {
                "method": "ANTsPy_SyNOnly",
                "transform_family": "SyNOnly_dense_displacement",
                "case_id": "availability_probe",
                "failure_reason": "ANTsPy module not available." if not antspy_available else "ANTsPy run skipped by explicit CLI option.",
                "m7_continued_decision": "EVIDENCE_NOT_FOUND_NOT_EXECUTED",
            }
        )
    rows.append(
        {
            "method": "VoxelMorph",
            "transform_family": "learned_dense_displacement",
            "case_id": "availability_probe",
            "failure_reason": "No trained CARE CineMyoPS VoxelMorph weights were found or authorized for this M7 continued repair attempt.",
            "module_available": voxelmorph_available,
            "m7_continued_decision": "NOT_USABLE_UNTRAINED_OR_NO_WEIGHTS",
        }
    )

    write_csv(OUT_ROOT / "registration_same_subset_matrix.csv", rows)
    for method in sorted({str(r.get("method", "")) for r in rows if r.get("case_id") != "availability_probe"}):
        subset = [r for r in rows if r.get("method") == method and r.get("case_id") != "availability_probe"]
        if not subset:
            continue
        summary_rows.append(
            {
                "method": method,
                "n_rows": len(subset),
                "n_cases": len({r.get("case_id") for r in subset}),
                "mean_before_myocardium_dice": float(np.mean([float(r["before_myocardium_dice"]) for r in subset])),
                "mean_after_myocardium_dice": float(np.mean([float(r["after_myocardium_dice"]) for r in subset])),
                "mean_before_lv_dice": float(np.mean([float(r["before_lv_dice"]) for r in subset])),
                "mean_after_lv_dice": float(np.mean([float(r["after_lv_dice"]) for r in subset])),
                "decision": subset[0].get("m7_continued_decision", ""),
            }
        )
    write_csv(OUT_ROOT / "cine_metrics_summary.csv", summary_rows)

    temporal_status = "TEMPORAL_DICTIONARY_READY_FOR_LIGHTWEIGHT_ATTEMPT" if usable else "TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_REPAIR_ATTEMPT"
    write_csv(
        OUT_ROOT / "temporal_dictionary_evidence.csv",
        [
            {
                "status": temporal_status,
                "usable_nonreference_registration": usable,
                "registration_decision": decision,
                "cases_attempted": len({p["case_id"] for p in pairs}),
                "pairs_attempted": len(pairs),
                "temporal_dictionary_attempted": usable,
                "reason": "M7 continued requires a usable non-reference registration row before temporal dictionary integration.",
            }
        ],
    )

    report = [
        "# Cine Registration Repair Report",
        "",
        "status: `EXECUTED_UNAUDITED`",
        f"cine_decision: `{'CINE_REGISTRATION_REPAIRED_READY_FOR_TEMPORAL_DICTIONARY' if usable else 'CINE_REGISTRATION_BLOCKED_AFTER_REPAIR_ATTEMPT'}`",
        "",
        f"- safe cases selected: `{','.join(sorted({str(p['case_id']) for p in pairs}))}`",
        f"- non-reference pairs attempted: `{len(pairs)}`",
        f"- SimpleITK Demons iterations: `{args.demons_iterations}`",
        f"- ANTsPy available: `{antspy_available}`; SyNOnly attempted: `{antspy_available and not args.skip_antspy}`; iterations: `{args.antspy_iterations}`",
        f"- VoxelMorph module available: `{voxelmorph_available}`; trained usable weights: `false`",
        f"- temporal dictionary status: `{temporal_status}`",
        "",
        "Evidence files: `registration_same_subset_matrix.csv`, `cine_metrics_summary.csv`, and `temporal_dictionary_evidence.csv`.",
        "",
        "This report does not copy M5 as a conclusion. It records a bounded M7 continued repair attempt and keeps Cine blocked unless a usable non-reference registration row is actually present.",
    ]
    write_text(OUT_ROOT / "cine_registration_repair_report.md", "\n".join(report) + "\n")
    append_command(
        f"python scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py --max-cases {args.max_cases} --pairs-per-case {args.pairs_per_case} --demons-iterations {args.demons_iterations} --antspy-iterations {args.antspy_iterations}",
        "exit 0",
        "Run M7 continued Cine non-reference registration repair attempt.",
    )
    print(json.dumps({"status": "EXECUTED_UNAUDITED", "usable_registration": usable, "pairs": len(pairs)}, indent=2))


if __name__ == "__main__":
    main()
