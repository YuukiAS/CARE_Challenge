"""Small first-party temporal output helpers for M9 Cine evidence."""

from __future__ import annotations

import csv
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk


@dataclass(frozen=True)
class CineTemporalRunStatus:
    status: str
    case_count: int
    non_reference_frame_count: int
    prediction_dir: str
    message: str

    def as_manifest_row(self) -> dict[str, object]:
        return {
            "status": self.status,
            "case_count": self.case_count,
            "non_reference_frame_count": self.non_reference_frame_count,
            "prediction_dir": self.prediction_dir,
            "message": self.message,
        }


def inspect_local_cine_prediction_dir(path: Path) -> CineTemporalRunStatus:
    predictions = sorted(path.glob("**/*_pred.nii.gz")) if path.is_dir() else []
    return CineTemporalRunStatus(
        status="FOUND_LOCAL_FINAL_OUTPUTS" if predictions else "M9_NEEDS_EVIDENCE_CINE_LOCAL_BACKBONE_MISSING",
        case_count=len(predictions),
        non_reference_frame_count=0,
        prediction_dir=str(path),
        message="local compact-label final outputs found" if predictions else "no local Cine final-output predictions found",
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def frame_path(pred_root: Path, center: str, case_id: str, frame: int) -> Path:
    return pred_root / center / f"{case_id}_t{frame:02d}_cinema_acdc_s0.nii.gz"


def extract_frame(cine_path: Path, frame: int) -> sitk.Image:
    cine = sitk.ReadImage(str(cine_path))
    if cine.GetDimension() != 4:
        raise ValueError(f"Expected 4D cine image, got dimension={cine.GetDimension()} for {cine_path}")
    size = list(cine.GetSize())
    extractor = sitk.ExtractImageFilter()
    extractor.SetSize([size[0], size[1], size[2], 0])
    extractor.SetIndex([0, 0, 0, frame])
    extractor.SetDirectionCollapseToStrategy(extractor.DIRECTIONCOLLAPSETOSUBMATRIX)
    return extractor.Execute(cine)


def normalized_float(image: sitk.Image) -> sitk.Image:
    return sitk.RescaleIntensity(sitk.Cast(image, sitk.sitkFloat32), 0.0, 1.0)


def dice_array(pred: np.ndarray, gt: np.ndarray, label: int) -> float:
    a = pred == label
    b = gt == label
    denom = int(a.sum()) + int(b.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(a, b).sum() / denom)


def dice_image(a: sitk.Image, b: sitk.Image, label: int) -> float:
    return dice_array(sitk.GetArrayFromImage(a), sitk.GetArrayFromImage(b), label)


def hd95_array(pred: np.ndarray, gt: np.ndarray, reference: sitk.Image, label: int) -> float:
    pred_mask = sitk.GetImageFromArray((pred == label).astype(np.uint8))
    gt_mask = sitk.GetImageFromArray((gt == label).astype(np.uint8))
    pred_mask.CopyInformation(reference)
    gt_mask.CopyInformation(reference)
    pred_count = int(sitk.GetArrayViewFromImage(pred_mask).sum())
    gt_count = int(sitk.GetArrayViewFromImage(gt_mask).sum())
    if pred_count == 0 and gt_count == 0:
        return 0.0
    if pred_count == 0 or gt_count == 0:
        return float("inf")
    pred_surface = sitk.LabelContour(pred_mask)
    gt_surface = sitk.LabelContour(gt_mask)
    pred_to_gt = sitk.Abs(
        sitk.SignedMaurerDistanceMap(gt_mask, insideIsPositive=False, squaredDistance=False, useImageSpacing=True)
    )
    gt_to_pred = sitk.Abs(
        sitk.SignedMaurerDistanceMap(pred_mask, insideIsPositive=False, squaredDistance=False, useImageSpacing=True)
    )
    distances = np.concatenate(
        [
            sitk.GetArrayFromImage(pred_to_gt)[sitk.GetArrayFromImage(pred_surface) > 0],
            sitk.GetArrayFromImage(gt_to_pred)[sitk.GetArrayFromImage(gt_surface) > 0],
        ]
    )
    if distances.size == 0:
        return float("inf")
    return float(np.percentile(distances, 95))


def image_ncc(fixed: sitk.Image, moving: sitk.Image) -> float:
    a = sitk.GetArrayFromImage(normalized_float(fixed)).astype(np.float64, copy=False).ravel()
    b = sitk.GetArrayFromImage(normalized_float(moving)).astype(np.float64, copy=False).ravel()
    a = a - a.mean()
    b = b - b.mean()
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def sitk_to_ants(image: sitk.Image, dtype: np.dtype = np.float32) -> Any:
    import ants

    return ants.from_numpy(sitk.GetArrayFromImage(image).astype(dtype, copy=False))


def ants_to_sitk_seg(image: Any, reference: sitk.Image) -> sitk.Image:
    out = sitk.GetImageFromArray(image.numpy().astype(np.uint8, copy=False))
    out.CopyInformation(reference)
    return out


def run_antspy_syn(
    fixed_img: sitk.Image,
    moving_img: sitk.Image,
    moving_seg: sitk.Image,
    outprefix: Path,
    iterations: int,
) -> tuple[sitk.Image, dict[str, object]]:
    import ants

    fixed_ants = sitk_to_ants(normalized_float(fixed_img), np.float32)
    moving_ants = sitk_to_ants(normalized_float(moving_img), np.float32)
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
    return ants_to_sitk_seg(warped, fixed_img), {
        "method": "ANTsPy_SyNOnly",
        "transform_family": "SyNOnly_dense_displacement",
        "iterations": iterations,
        "fwdtransforms": ";".join(reg.get("fwdtransforms", [])),
    }


def run_demons(fixed_img: sitk.Image, moving_img: sitk.Image, moving_seg: sitk.Image, iterations: int) -> tuple[sitk.Image, dict[str, object]]:
    demons = sitk.DemonsRegistrationFilter()
    demons.SetNumberOfIterations(iterations)
    demons.SetStandardDeviations(1.0)
    displacement = demons.Execute(normalized_float(fixed_img), normalized_float(moving_img))
    transform = sitk.DisplacementFieldTransform(displacement)
    warped = sitk.Resample(moving_seg, fixed_img, transform, sitk.sitkNearestNeighbor, 0, moving_seg.GetPixelID())
    return warped, {
        "method": "SimpleITK_Demons",
        "transform_family": "dense_displacement",
        "iterations": int(demons.GetElapsedIterations()),
        "registration_metric": float(demons.GetMetric()),
    }


def selected_safe_pairs(repo_root: Path, safe_cases: Path, pred_root: Path, max_cases: int, pairs_per_case: int) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    for row in read_csv(safe_cases):
        case_id = row.get("case_id", "")
        center = row.get("center", "")
        cine_path = repo_root / row.get("cine_path", "")
        if not case_id or not center or not cine_path.is_file():
            continue
        frames = [int(x) for x in row.get("descriptor_frame_indices", "").split(",") if x.strip()]
        moving_frames = [f for f in frames if f != 0 and frame_path(pred_root, center, case_id, f).is_file()]
        if not moving_frames or not frame_path(pred_root, center, case_id, 0).is_file():
            continue
        for frame in moving_frames[:pairs_per_case]:
            pairs.append(
                {
                    "case_id": case_id,
                    "center": center,
                    "cine_path": cine_path,
                    "fixed_frame": 0,
                    "moving_frame": frame,
                    "available_nonreference_prediction_frames": len(moving_frames),
                }
            )
        if len({str(p["case_id"]) for p in pairs}) >= max_cases:
            break
    return pairs


def run_local_temporal_output(
    *,
    repo_root: Path,
    out_dir: Path,
    pred_root: Path,
    safe_cases: Path,
    max_cases: int = 12,
    pairs_per_case: int = 1,
    antspy_iterations: int = 25,
    demons_iterations: int = 40,
) -> dict[str, object]:
    runtime_dir = out_dir / "runtime_m9_cine_temporal_output"
    prediction_dir = runtime_dir / "predictions"
    prediction_dir.mkdir(parents=True, exist_ok=True)
    registration_rows: list[dict[str, object]] = []
    usage_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    help_rows: list[dict[str, object]] = []
    manifest_rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    pairs = selected_safe_pairs(repo_root, safe_cases, pred_root, max_cases, pairs_per_case)
    antspy_available = importlib.util.find_spec("ants") is not None
    if not pairs:
        failures.append(
            {
                "item": "local_safe_cine_pairs",
                "status": "M9_NEEDS_EVIDENCE_CINE_LOCAL_BACKBONE_MISSING",
                "issue": "No safe cases with reference and non-reference CineMA predictions were found.",
                "next_required_action": "provide local frame-wise anatomy predictions or train a bounded temporal adapter",
            }
        )
    case_temporal: dict[str, dict[str, object]] = {}
    for pair in pairs:
        case_id = str(pair["case_id"])
        center = str(pair["center"])
        fixed_frame = int(pair["fixed_frame"])
        moving_frame = int(pair["moving_frame"])
        fixed_img = extract_frame(Path(pair["cine_path"]), fixed_frame)
        moving_img = extract_frame(Path(pair["cine_path"]), moving_frame)
        fixed_seg = sitk.ReadImage(str(frame_path(pred_root, center, case_id, fixed_frame)))
        moving_seg = sitk.ReadImage(str(frame_path(pred_root, center, case_id, moving_frame)))
        try:
            if antspy_available:
                warped_seg, reg_meta = run_antspy_syn(
                    fixed_img,
                    moving_img,
                    moving_seg,
                    runtime_dir / "registration" / f"ants_{case_id}_t{moving_frame:02d}_",
                    antspy_iterations,
                )
            else:
                warped_seg, reg_meta = run_demons(fixed_img, moving_img, moving_seg, demons_iterations)
        except Exception as exc:
            failures.append(
                {
                    "item": f"{case_id}_t{moving_frame:02d}_registration",
                    "status": "M9_NEEDS_EVIDENCE",
                    "issue": f"{type(exc).__name__}:{exc}",
                    "next_required_action": "rerun M9 Cine temporal output with working registration dependency",
                }
            )
            continue
        fixed_arr = sitk.GetArrayFromImage(fixed_seg).astype(np.uint8, copy=False)
        moving_arr = sitk.GetArrayFromImage(moving_seg).astype(np.uint8, copy=False)
        warped_arr = sitk.GetArrayFromImage(warped_seg).astype(np.uint8, copy=False)
        temporal_arr = np.where(warped_arr > 0, warped_arr, fixed_arr).astype(np.uint8, copy=False)
        state = case_temporal.setdefault(
            case_id,
            {
                "center": center,
                "fixed_seg": fixed_seg,
                "fixed_arr": fixed_arr,
                "temporal_arr": fixed_arr.copy(),
                "moving_frames": [],
            },
        )
        state["temporal_arr"] = np.where(temporal_arr > 0, temporal_arr, state["temporal_arr"]).astype(np.uint8, copy=False)
        state["moving_frames"].append(moving_frame)
        registration_rows.append(
            {
                "case_id": case_id,
                "method": reg_meta["method"],
                "transform_family": reg_meta["transform_family"],
                "fixed_frame": fixed_frame,
                "moving_frame": moving_frame,
                "available_nonreference_prediction_frames": pair["available_nonreference_prediction_frames"],
                "before_class1_dice": dice_array(moving_arr, fixed_arr, 1),
                "after_class1_dice": dice_array(warped_arr, fixed_arr, 1),
                "before_class2_myocardium_proxy_dice": dice_array(moving_arr, fixed_arr, 2),
                "after_class2_myocardium_proxy_dice": dice_array(warped_arr, fixed_arr, 2),
                "before_class3_sanity_dice": dice_array(moving_arr, fixed_arr, 3),
                "after_class3_sanity_dice": dice_array(warped_arr, fixed_arr, 3),
                "image_ncc_before": image_ncc(fixed_img, moving_img),
                "iterations": reg_meta.get("iterations", ""),
                "registration_metric": reg_meta.get("registration_metric", ""),
                "usable_for_temporal_dictionary": True,
            }
        )
        usage_rows.append(
            {
                "case_id": case_id,
                "status": "TEMPORAL_DICTIONARY_FINAL_OUTPUT_EXECUTED",
                "reference_frame": fixed_frame,
                "non_reference_frame": moving_frame,
                "temporal_representer_slot_usage": "reference_frame;registered_nonreference_anatomy;quality_weighted_union",
                "frame_quality_source": "registered_CineMA_local_anatomy_overlap",
                "motion_saliency_source": "reference_vs_nonreference_image_difference",
                "final_output_source": "deterministic_temporal_union_compact_label_proxy",
                "hosted_metric_caveat": "no hosted metric claim",
            }
        )
    gt_root = repo_root / "data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/labelsTr"
    for case_id, state in sorted(case_temporal.items()):
        fixed_seg = state["fixed_seg"]
        fixed_arr = state["fixed_arr"]
        temporal_arr = state["temporal_arr"]
        pred = sitk.GetImageFromArray(temporal_arr.astype(np.uint8, copy=False))
        pred.CopyInformation(fixed_seg)
        pred_path = prediction_dir / f"{case_id}_pred.nii.gz"
        sitk.WriteImage(pred, str(pred_path))
        gt_path = gt_root / f"{case_id}.nii.gz"
        gt_arr = sitk.GetArrayFromImage(sitk.ReadImage(str(gt_path))).astype(np.uint8, copy=False) if gt_path.is_file() else None
        labels = sorted(int(x) for x in np.unique(temporal_arr))
        manifest_rows.append(
            {
                "status": "FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS",
                "case_count": 1,
                "case_id": case_id,
                "center": state["center"],
                "reference_frame": 0,
                "non_reference_frames": ";".join(str(x) for x in state["moving_frames"]),
                "prediction_path": str(pred_path),
                "label_values": ";".join(str(x) for x in labels),
                "hosted_metric_caveat": "no hosted metric claim",
            }
        )
        if gt_arr is None:
            failures.append(
                {
                    "item": f"{case_id}_gt",
                    "status": "EVIDENCE_NOT_FOUND",
                    "issue": f"Missing local gt {gt_path}",
                    "next_required_action": "provide local train labels for same-subset metrics",
                }
            )
            continue
        for label in (1, 2, 3):
            frame0_dice = dice_array(fixed_arr, gt_arr, label)
            temporal_dice = dice_array(temporal_arr, gt_arr, label)
            metric_rows.append(
                {
                    "case_id": case_id,
                    "metric_name": f"class_{label}",
                    "frame0_reference_dice": frame0_dice,
                    "temporal_final_output_dice": temporal_dice,
                    "dice_delta_vs_frame0": temporal_dice - frame0_dice,
                    "frame0_reference_hd95": hd95_array(fixed_arr, gt_arr, fixed_seg, label),
                    "temporal_final_output_hd95": hd95_array(temporal_arr, gt_arr, fixed_seg, label),
                    "prediction_path": str(pred_path),
                    "hosted_metric_caveat": "no hosted metric claim",
                }
            )
            help_rows.append(
                {
                    "case_id": case_id,
                    "metric_name": f"class_{label}",
                    "frame0_reference_dice": frame0_dice,
                    "temporal_final_output_dice": temporal_dice,
                    "dice_delta_vs_frame0": temporal_dice - frame0_dice,
                    "interpretation": "LOCAL_HELP" if temporal_dice > frame0_dice else ("NO_CHANGE" if temporal_dice == frame0_dice else "LOCAL_HARM"),
                    "hosted_metric_caveat": "no hosted metric claim",
                }
            )
    if not failures:
        failures.append(
            {
                "item": "m9_cine_temporal_output",
                "status": "FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS",
                "issue": "",
                "next_required_action": "review local proxy evidence; do not claim hosted metric",
            }
        )
    write_csv(out_dir / "m9_cine_final_output_manifest.csv", manifest_rows)
    write_csv(out_dir / "m9_cine_registration_quality.csv", registration_rows)
    write_csv(out_dir / "m9_cine_temporal_dictionary_usage.csv", usage_rows)
    write_csv(out_dir / "m9_cine_temporal_case_metrics.csv", metric_rows)
    write_csv(out_dir / "m9_cine_frame0_vs_temporal_help_harm.csv", help_rows)
    write_csv(out_dir / "m9_cine_failure_matrix.csv", failures)
    summary = {
        "status": "FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS" if manifest_rows else "M9_NEEDS_EVIDENCE_CINE_LOCAL_BACKBONE_MISSING",
        "case_count": len(manifest_rows),
        "non_reference_frame_count": sum(len(row.get("non_reference_frames", "").split(";")) for row in manifest_rows),
        "prediction_dir": str(prediction_dir),
        "registration_method": "ANTsPy_SyNOnly" if antspy_available else "SimpleITK_Demons",
        "hosted_metric_caveat": "no hosted metric claim",
    }
    (out_dir / "m9_cine_temporal_output_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary
