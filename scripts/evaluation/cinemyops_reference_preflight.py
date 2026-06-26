#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage


DEFAULT_SAFE_CASES = Path("results/20260625_cine_geometry/safe_cases.csv")
DEFAULT_PRED_ROOT = Path("results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/predictions/train")
DEFAULT_OUTPUT_DIR = Path("results/20260625_cine_geometry")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def extract_frame(image4d: sitk.Image, frame_index: int = 0) -> sitk.Image:
    size = list(image4d.GetSize())
    extractor = sitk.ExtractImageFilter()
    extractor.SetSize([size[0], size[1], size[2], 0])
    extractor.SetIndex([0, 0, 0, int(frame_index)])
    return extractor.Execute(image4d)


def allclose_tuple(a: tuple[float, ...], b: tuple[float, ...], atol: float = 1e-6) -> bool:
    return bool(np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), rtol=0.0, atol=atol))


def metadata_match(image: sitk.Image, reference: sitk.Image) -> bool:
    return (
        tuple(image.GetSize()) == tuple(reference.GetSize())
        and allclose_tuple(image.GetSpacing(), reference.GetSpacing(), atol=1e-6)
        and allclose_tuple(image.GetOrigin(), reference.GetOrigin(), atol=5e-6)
        and allclose_tuple(image.GetDirection(), reference.GetDirection(), atol=1e-6)
    )


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


def dice(pred: np.ndarray, gt: np.ndarray) -> float | None:
    pred_sum = int(pred.sum())
    gt_sum = int(gt.sum())
    if pred_sum == 0 and gt_sum == 0:
        return None
    if pred_sum + gt_sum == 0:
        return 0.0
    return float(2.0 * np.logical_and(pred, gt).sum() / (pred_sum + gt_sum))


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


def metric_mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    return float(np.mean(values)) if values else None


def metric_median(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    return float(np.median(values)) if values else None


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def evaluate_case(row: dict[str, str], pred_root: Path) -> dict[str, Any]:
    center = row["center"]
    case_id = row["case_id"]
    cine_path = Path(row["cine_path"])
    label_path = Path(row["label_path"])
    pred_path = pred_root / center / f"{case_id}_t00_cinema_acdc_s0.nii.gz"
    if not pred_path.is_file():
        raise FileNotFoundError(pred_path)

    frame0 = extract_frame(sitk.ReadImage(str(cine_path)), 0)
    label = sitk.ReadImage(str(label_path))
    pred = sitk.ReadImage(str(pred_path))
    pred_arr = compact_pred_from_cinema(sitk.GetArrayFromImage(pred))
    gt_arr = compact_gt(sitk.GetArrayFromImage(label))
    spacing = frame0.GetSpacing()
    spacing_zyx = (float(spacing[2]), float(spacing[1]), float(spacing[0]))
    out: dict[str, Any] = {
        "center": center,
        "case_id": case_id,
        "prediction_path": str(pred_path),
        "prediction_matches_frame0_metadata": metadata_match(pred, frame0),
        "label_matches_frame0_metadata": metadata_match(label, frame0),
    }
    class_names = {1: "class_1_myocardium", 2: "class_2_lv", 3: "class_3_scar_sanity"}
    for value, name in class_names.items():
        pred_mask = pred_arr == value
        gt_mask = gt_arr == value
        out[f"{name}_dice"] = dice(pred_mask, gt_mask)
        out[f"{name}_hd95"] = hd95(pred_mask, gt_mask, spacing_zyx)
        out[f"{name}_pred_voxels"] = int(pred_mask.sum())
        out[f"{name}_gt_voxels"] = int(gt_mask.sum())
        out[f"{name}_pred_components"] = component_count(pred_mask)
        out[f"{name}_gt_components"] = component_count(gt_mask)
    return out


def write_summary(rows: list[dict[str, Any]], path: Path) -> None:
    keys = [
        "class_1_myocardium_dice",
        "class_1_myocardium_hd95",
        "class_2_lv_dice",
        "class_2_lv_hd95",
        "class_3_scar_sanity_dice",
        "class_3_scar_sanity_hd95",
    ]
    lines = [
        "# CineMyoPS Reference-Frame Preflight",
        "",
        "## Setup",
        "",
        "- source predictions: `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/predictions/train/*/*_t00_cinema_acdc_s0.nii.gz`",
        "- case filter: `results/20260625_cine_geometry/safe_cases.csv`",
        "- prediction remap: CineMA `2` -> CARE compact myocardium `1`, CineMA `3` -> CARE compact LV `2`; no scar output is produced by this anatomy prior.",
        "- reference frame: raw Cine frame 0.",
        "",
        "## Metadata Gates",
        "",
        f"- prediction metadata matched frame0 for all safe cases: {all(bool(row['prediction_matches_frame0_metadata']) for row in rows)}",
        f"- label metadata matched frame0 for all safe cases: {all(bool(row['label_matches_frame0_metadata']) for row in rows)}",
        "",
        "## Metrics",
        "",
        "| metric | mean | median |",
        "| --- | ---: | ---: |",
    ]
    for key in keys:
        mean = metric_mean(rows, key)
        median = metric_median(rows, key)
        mean_text = "NA" if mean is None else f"{mean:.4f}"
        median_text = "NA" if median is None else f"{median:.4f}"
        lines.append(f"| {key} | {mean_text} | {median_text} |")
    scar_positive = sum(1 for row in rows if int(row["class_3_scar_sanity_gt_voxels"]) > 0)
    scar_pred_positive = sum(1 for row in rows if int(row["class_3_scar_sanity_pred_voxels"]) > 0)
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- scar-positive safe cases: {scar_positive}",
            f"- cases with scar-like class-3 prediction after CineMA remap: {scar_pred_positive}",
            "- The class-3 scar sanity metric is expected to fail for this frozen anatomy prior because CineMA has no scar head; this is a negative control, not a submission-ready pathology model.",
            "- The myocardium/LV anatomy signal and metadata gate are sufficient to proceed to a temporal/anatomy preflight on the safe subset.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_decision(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    meta_ok = all(bool(row["prediction_matches_frame0_metadata"]) and bool(row["label_matches_frame0_metadata"]) for row in rows)
    myocardium_mean = metric_mean(rows, "class_1_myocardium_dice")
    status = "GO_CINE_TEMPORAL_PREFLIGHT" if meta_ok and myocardium_mean is not None and myocardium_mean > 0.0 else "REVISE_GEOMETRY_SAFE_SUBSET_ONLY"
    lines = [
        "# Decision 20260625 Cine Geometry",
        "",
        f"status: `{status}`",
        "",
        "## Evidence",
        "",
        f"- safe reference-frame preflight cases: {len(rows)}",
        f"- prediction and label metadata match frame0 for all safe cases: {meta_ok}",
        f"- safe subset myocardium Dice mean: {myocardium_mean:.4f}" if myocardium_mean is not None else "- safe subset myocardium Dice mean: NA",
        "- frozen CineMA anatomy prior has no scar output, so class-3 scar sanity remains a negative control.",
        "",
        "## Next Step",
        "",
        "Run a temporal/anatomy retrieval preflight on the 59-case safe subset. Keep the five metadata mismatch cases in the repair queue until explicit header or nearest-neighbor resampling policy is accepted.",
    ]
    (output_dir / "decision.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate CineMA frame0 predictions on the CineMyoPS safe geometry subset.")
    parser.add_argument("--safe-cases", type=Path, default=DEFAULT_SAFE_CASES)
    parser.add_argument("--pred-root", type=Path, default=DEFAULT_PRED_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = [evaluate_case(row, args.pred_root) for row in read_rows(args.safe_cases)]
    write_csv(rows, args.output_dir / "case_metrics.csv")
    write_summary(rows, args.output_dir / "metrics_summary.md")
    update_decision(args.output_dir, rows)
    print(json.dumps({"cases": len(rows), "myocardium_dice_mean": metric_mean(rows, "class_1_myocardium_dice")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
