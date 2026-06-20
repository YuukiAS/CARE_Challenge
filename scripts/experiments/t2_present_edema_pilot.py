#!/usr/bin/env python3
"""T2-present MyoPS edema mechanism diagnostic and feature-routing pilot.

This is an isolated CARE pilot. It reads raw MyoPS NIfTI files and compact
Dataset501 labels, then evaluates a simple complete-case T2 intensity rule.
The baseline is diagnostic only: it uses GT myocardium/scar support as an
oracle spatial prior to test whether T2 contrast is locally useful for edema.
It does not train, upload, or modify existing nnU-Net outputs.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, median

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
NNUNET_CODE_DIR = REPO_ROOT / "code/nnUNet"
if str(NNUNET_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(NNUNET_CODE_DIR))

from nnunet_label_utils import remap_segmentation


MYO = 1
LV = 2
RV = 3
EDEMA = 4
SCAR = 5


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    center: str
    case_dir: Path
    lge_path: Path
    gd_path: Path
    t2_path: Path | None
    c0_path: Path | None
    modality_group: str


def discover_train_cases(root: Path) -> list[CaseRecord]:
    out: list[CaseRecord] = []
    for case_dir in sorted(root.glob("Center*/Case*")):
        if not case_dir.is_dir():
            continue
        cid = case_dir.name
        lge = case_dir / f"{cid}_LGE.nii.gz"
        gd = case_dir / f"{cid}_gd.nii.gz"
        t2 = case_dir / f"{cid}_T2.nii.gz"
        c0 = case_dir / f"{cid}_C0.nii.gz"
        if not lge.is_file() or not gd.is_file():
            continue
        has_t2 = t2.is_file()
        has_c0 = c0.is_file()
        if has_c0 and has_t2:
            group = "C0+LGE+T2"
        elif has_c0:
            group = "C0+LGE"
        elif has_t2:
            group = "LGE+T2"
        else:
            group = "LGE-only"
        out.append(
            CaseRecord(
                case_id=cid,
                center=case_dir.parent.name,
                case_dir=case_dir,
                lge_path=lge,
                gd_path=gd,
                t2_path=t2 if has_t2 else None,
                c0_path=c0 if has_c0 else None,
                modality_group=group,
            )
        )
    return out


def discover_val_modalities(root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case_dir in sorted(root.glob("*Center*/Case*")):
        if not case_dir.is_dir():
            continue
        cid = case_dir.name
        has_lge = (case_dir / f"{cid}_LGE.nii.gz").is_file()
        has_t2 = (case_dir / f"{cid}_T2.nii.gz").is_file()
        has_c0 = (case_dir / f"{cid}_C0.nii.gz").is_file()
        rows.append(
            {
                "case_id": cid,
                "center": case_dir.parent.name,
                "lge_present": has_lge,
                "t2_present": has_t2,
                "c0_present": has_c0,
                "modality_group": "C0+LGE+T2"
                if has_lge and has_t2 and has_c0
                else "incomplete_or_unexpected",
            }
        )
    return rows


def read_image(path: Path) -> sitk.Image:
    return sitk.ReadImage(str(path))


def resample_to_reference(moving: sitk.Image, reference: sitk.Image, *, is_label: bool) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(moving)


def array_from_image(path: Path, reference: sitk.Image | None = None, *, is_label: bool = False) -> np.ndarray:
    img = read_image(path)
    if reference is not None:
        same_grid = (
            img.GetSize() == reference.GetSize()
            and img.GetSpacing() == reference.GetSpacing()
            and img.GetOrigin() == reference.GetOrigin()
            and img.GetDirection() == reference.GetDirection()
        )
        if not same_grid:
            img = resample_to_reference(img, reference, is_label=is_label)
    arr = sitk.GetArrayFromImage(img)
    return arr.astype(np.int32 if is_label else np.float32, copy=False)


def compact_label(path: Path, reference: sitk.Image) -> np.ndarray:
    raw = array_from_image(path, reference, is_label=True)
    return remap_segmentation(raw)


def robust_z(arr: np.ndarray, support: np.ndarray | None = None) -> np.ndarray:
    valid = np.isfinite(arr)
    if support is not None and support.any():
        valid &= support.astype(bool)
    vals = arr[valid]
    if vals.size < 16:
        vals = arr[np.isfinite(arr)]
    if vals.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25, 75])
    scale = float(q75 - q25)
    if scale <= 1e-6:
        scale = float(np.std(vals))
    if scale <= 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - med) / scale).astype(np.float32, copy=False)


def surface_distances(pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, ...]) -> np.ndarray:
    struct = generate_binary_structure(pred.ndim, 1)
    p = pred.astype(bool)
    g = gt.astype(bool)
    if not p.any() and not g.any():
        return np.array([0.0], dtype=np.float64)
    if not p.any() or not g.any():
        return np.array([np.inf], dtype=np.float64)
    surf_p = p & ~binary_erosion(p, structure=struct)
    surf_g = g & ~binary_erosion(g, structure=struct)
    dt_g = distance_transform_edt(~surf_g, sampling=spacing_zyx)
    dt_p = distance_transform_edt(~surf_p, sampling=spacing_zyx)
    return np.concatenate([dt_g[surf_p].ravel(), dt_p[surf_g].ravel()]).astype(np.float64, copy=False)


def binary_metrics(pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, ...]) -> dict[str, object]:
    p = pred.astype(bool)
    g = gt.astype(bool)
    tp = int(np.logical_and(p, g).sum())
    fp = int(np.logical_and(p, ~g).sum())
    fn = int(np.logical_and(~p, g).sum())
    denom = int(p.sum()) + int(g.sum())
    dice = 1.0 if denom == 0 else float(2.0 * tp / denom)
    precision = None if tp + fp == 0 else float(tp / (tp + fp))
    recall = None if tp + fn == 0 else float(tp / (tp + fn))
    dists = surface_distances(p, g, spacing_zyx)
    hd = None if np.isinf(dists).any() else float(np.max(dists))
    hd95 = None if np.isinf(dists).any() else float(np.percentile(dists, 95))
    cc, n_cc = label(p, structure=generate_binary_structure(p.ndim, 1))
    sizes = [int((cc == i).sum()) for i in range(1, n_cc + 1)]
    return {
        "dice": dice,
        "precision": precision,
        "recall": recall,
        "hd": hd,
        "hd95": hd95,
        "tp_voxels": tp,
        "fp_voxels": fp,
        "fn_voxels": fn,
        "pred_voxels": int(p.sum()),
        "gt_voxels": int(g.sum()),
        "pred_components": int(n_cc),
        "pred_largest_component_voxels": max(sizes) if sizes else 0,
    }


def cheap_binary_metrics(pred: np.ndarray, gt: np.ndarray) -> dict[str, object]:
    p = pred.astype(bool)
    g = gt.astype(bool)
    tp = int(np.logical_and(p, g).sum())
    fp = int(np.logical_and(p, ~g).sum())
    fn = int(np.logical_and(~p, g).sum())
    denom = int(p.sum()) + int(g.sum())
    dice = 1.0 if denom == 0 else float(2.0 * tp / denom)
    precision = None if tp + fp == 0 else float(tp / (tp + fp))
    recall = None if tp + fn == 0 else float(tp / (tp + fn))
    _, n_cc = label(p, structure=generate_binary_structure(p.ndim, 1))
    return {
        "dice": dice,
        "precision": precision,
        "recall": recall,
        "pred_components": int(n_cc),
    }


def component_stats(mask: np.ndarray, voxel_mm3: float) -> dict[str, object]:
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    sizes = [int((cc == i).sum()) for i in range(1, n_cc + 1)]
    vols = [s * voxel_mm3 for s in sizes]
    if not sizes:
        return {
            "component_count": 0,
            "component_voxels_median": None,
            "component_voxels_p90": None,
            "component_mm3_median": None,
            "component_mm3_p90": None,
            "largest_component_mm3": 0.0,
        }
    return {
        "component_count": int(n_cc),
        "component_voxels_median": float(median(sizes)),
        "component_voxels_p90": float(np.percentile(sizes, 90)),
        "component_mm3_median": float(median(vols)),
        "component_mm3_p90": float(np.percentile(vols, 90)),
        "largest_component_mm3": float(max(vols)),
    }


def maybe_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) or math.isinf(number) else number


def avg(values: list[object]) -> float | None:
    vals = [v for v in (maybe_float(x) for x in values) if v is not None]
    return float(mean(vals)) if vals else None


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({k for row in rows for k in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def format_value(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(format_value(row.get(c)) for c in columns) + " |")
    return "\n".join(lines)


def load_split(path: Path) -> tuple[set[str], set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    fold0 = data["folds"][0]
    return set(fold0["train"]), set(fold0["val"])


def build_prediction(
    t2_z: np.ndarray,
    gt: np.ndarray,
    *,
    threshold: float,
    prior_iterations: int,
    min_component_mm3: float,
    voxel_mm3: float,
) -> np.ndarray:
    prior = np.logical_or(gt == MYO, gt == SCAR)
    if prior_iterations > 0:
        prior = binary_dilation(prior, structure=generate_binary_structure(gt.ndim, 1), iterations=prior_iterations)
    pred = np.logical_and(t2_z >= threshold, prior)
    if min_component_mm3 <= 0 or not pred.any():
        return pred
    cc, n_cc = label(pred, structure=generate_binary_structure(pred.ndim, 1))
    keep = np.zeros_like(pred, dtype=bool)
    min_voxels = max(1, int(math.ceil(min_component_mm3 / max(voxel_mm3, 1e-9))))
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if int(comp.sum()) >= min_voxels:
            keep |= comp
    return keep


def summarize_groups(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[("modality_group", str(row["modality_group"]))].append(row)
        groups[("center", str(row["center"]))].append(row)
    groups[("all", "all")].extend(rows)
    out: list[dict[str, object]] = []
    for (group_type, group), items in sorted(groups.items()):
        out.append(
            {
                "group_type": group_type,
                "group": group,
                "cases": len(items),
                "edema_positive_cases": sum(1 for r in items if r["edema_gt_positive"]),
                "scar_positive_cases": sum(1 for r in items if r["scar_gt_positive"]),
                "myocardium_positive_cases": sum(1 for r in items if r["myocardium_gt_positive"]),
                "edema_voxel_fraction_mean": avg([r["edema_voxel_fraction"] for r in items]),
                "scar_voxel_fraction_mean": avg([r["scar_voxel_fraction"] for r in items]),
                "t2_edema_vs_myo_contrast_median": avg([r["t2_edema_vs_myo_contrast"] for r in items]),
                "edema_components_mean": avg([r["edema_component_count"] for r in items]),
            }
        )
    return out


def run(args: argparse.Namespace) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = args.output_root or (REPO_ROOT / "results/experiments" / f"t2_present_edema_{timestamp}")
    pred_root = out_root / "feature_baseline_predictions"
    out_root.mkdir(parents=True, exist_ok=True)

    train_cases = discover_train_cases(args.myops_train)
    val_rows = discover_val_modalities(args.myops_val) if args.myops_val.is_dir() else []
    split_train, split_val = load_split(args.splits_json)

    metadata_rows: list[dict[str, object]] = []
    complete_cache: list[dict[str, object]] = []
    complete_by_id: dict[str, dict[str, object]] = {}

    for idx, case in enumerate(train_cases, start=1):
        print(f"[{idx:03d}/{len(train_cases):03d}] {case.case_id}", flush=True)
        lge_img = read_image(case.lge_path)
        gt = compact_label(case.gd_path, lge_img)
        shape = tuple(int(x) for x in gt.shape)
        spacing_xyz = tuple(float(x) for x in lge_img.GetSpacing())
        spacing_zyx = spacing_xyz[::-1]
        voxel_mm3 = float(np.prod(spacing_xyz))
        n_voxels = int(gt.size)
        edema = gt == EDEMA
        scar = gt == SCAR
        myo = gt == MYO
        myo_scar_prior = np.logical_or(myo, scar)
        prior_d2 = binary_dilation(myo_scar_prior, structure=generate_binary_structure(gt.ndim, 1), iterations=2)
        prior_d4 = binary_dilation(myo_scar_prior, structure=generate_binary_structure(gt.ndim, 1), iterations=4)

        row: dict[str, object] = {
            "case_id": case.case_id,
            "center": case.center,
            "modality_group": case.modality_group,
            "lge_present": True,
            "t2_present": case.t2_path is not None,
            "c0_present": case.c0_path is not None,
            "in_fold0_train": case.case_id in split_train,
            "in_fold0_val": case.case_id in split_val,
            "shape_zyx": "x".join(map(str, shape)),
            "spacing_xyz": ",".join(f"{x:.6g}" for x in spacing_xyz),
            "direction": ",".join(f"{x:.6g}" for x in lge_img.GetDirection()),
            "voxel_mm3": voxel_mm3,
            "myocardium_gt_positive": bool(myo.any()),
            "edema_gt_positive": bool(edema.any()),
            "scar_gt_positive": bool(scar.any()),
            "myocardium_voxels": int(myo.sum()),
            "edema_voxels": int(edema.sum()),
            "scar_voxels": int(scar.sum()),
            "myocardium_voxel_fraction": float(myo.sum() / n_voxels),
            "edema_voxel_fraction": float(edema.sum() / n_voxels),
            "scar_voxel_fraction": float(scar.sum() / n_voxels),
            "edema_prior_d2_coverage": None
            if not edema.any()
            else float(np.logical_and(edema, prior_d2).sum() / max(1, edema.sum())),
            "edema_prior_d4_coverage": None
            if not edema.any()
            else float(np.logical_and(edema, prior_d4).sum() / max(1, edema.sum())),
        }
        edema_stats = component_stats(edema, voxel_mm3)
        scar_stats = component_stats(scar, voxel_mm3)
        row.update({f"edema_{k}": v for k, v in edema_stats.items()})
        row.update({f"scar_{k}": v for k, v in scar_stats.items()})

        if case.t2_path is not None:
            t2 = array_from_image(case.t2_path, lge_img)
            t2_z = robust_z(t2, np.logical_or.reduce((myo, edema, scar)))
            row["t2_edema_median_z"] = float(np.median(t2_z[edema])) if edema.any() else None
            row["t2_myocardium_median_z"] = float(np.median(t2_z[myo])) if myo.any() else None
            row["t2_scar_median_z"] = float(np.median(t2_z[scar])) if scar.any() else None
            row["t2_edema_vs_myo_contrast"] = (
                float(row["t2_edema_median_z"] - row["t2_myocardium_median_z"])
                if row["t2_edema_median_z"] is not None and row["t2_myocardium_median_z"] is not None
                else None
            )
            complete_item = {
                "case": case,
                "gt": gt,
                "t2_z": t2_z,
                "spacing_zyx": spacing_zyx,
                "voxel_mm3": voxel_mm3,
                "metadata": row,
                "lge_img": lge_img,
            }
            complete_cache.append(complete_item)
            complete_by_id[case.case_id] = complete_item
        else:
            row["t2_edema_median_z"] = None
            row["t2_myocardium_median_z"] = None
            row["t2_scar_median_z"] = None
            row["t2_edema_vs_myo_contrast"] = None

        metadata_rows.append(row)

    complete_ids = {item["case"].case_id for item in complete_cache}
    complete_train = [item for item in complete_cache if item["case"].case_id in split_train]
    complete_val = [item for item in complete_cache if item["case"].case_id in split_val]

    thresholds = [round(x, 2) for x in np.arange(args.threshold_min, args.threshold_max + 1e-9, args.threshold_step)]
    prior_iterations_grid = [int(x) for x in args.prior_iterations.split(",") if x.strip()]
    min_component_grid = [float(x) for x in args.min_component_mm3.split(",") if x.strip()]
    grid_rows: list[dict[str, object]] = []
    for threshold in thresholds:
        for prior_iterations in prior_iterations_grid:
            for min_component_mm3 in min_component_grid:
                metrics = []
                for item in complete_train:
                    pred = build_prediction(
                        item["t2_z"],
                        item["gt"],
                        threshold=threshold,
                        prior_iterations=prior_iterations,
                        min_component_mm3=min_component_mm3,
                        voxel_mm3=item["voxel_mm3"],
                    )
                    metrics.append(cheap_binary_metrics(pred, item["gt"] == EDEMA))
                grid_rows.append(
                    {
                        "threshold": threshold,
                        "prior_iterations": prior_iterations,
                        "min_component_mm3": min_component_mm3,
                        "split": "fold0_complete_train",
                        "cases": len(metrics),
                        "mean_dice": avg([m["dice"] for m in metrics]),
                        "mean_precision": avg([m["precision"] for m in metrics]),
                        "mean_recall": avg([m["recall"] for m in metrics]),
                        "mean_hd95": None,
                        "mean_components": avg([m["pred_components"] for m in metrics]),
                    }
                )

    best = max(grid_rows, key=lambda r: (maybe_float(r["mean_dice"]) or -1.0, maybe_float(r["mean_recall"]) or -1.0))
    case_metric_rows: list[dict[str, object]] = []
    split_pred_dir = pred_root / "all_complete"
    split_pred_dir.mkdir(parents=True, exist_ok=True)
    for idx, item in enumerate(complete_cache, start=1):
        case = item["case"]
        print(f"[feature {idx:03d}/{len(complete_cache):03d}] {case.case_id}", flush=True)
        pred = build_prediction(
            item["t2_z"],
            item["gt"],
            threshold=float(best["threshold"]),
            prior_iterations=int(best["prior_iterations"]),
            min_component_mm3=float(best["min_component_mm3"]),
            voxel_mm3=item["voxel_mm3"],
        )
        metrics = binary_metrics(pred, item["gt"] == EDEMA, item["spacing_zyx"])
        out_pred = pred.astype(np.uint8) * EDEMA
        pred_img = sitk.GetImageFromArray(out_pred)
        pred_img.CopyInformation(item["lge_img"])
        sitk.WriteImage(pred_img, str(split_pred_dir / f"{case.case_id}.nii.gz"))
        case_metric_rows.append(
            {
                "split": "all_complete",
                "case_id": case.case_id,
                "center": case.center,
                "modality_group": case.modality_group,
                "in_fold0_train": case.case_id in split_train,
                "in_fold0_val": case.case_id in split_val,
                **metrics,
            }
        )

    baseline_summary: list[dict[str, object]] = []
    summary_splits = [
        ("fold0_complete_train", [r for r in case_metric_rows if r["in_fold0_train"]]),
        ("fold0_complete_val", [r for r in case_metric_rows if r["in_fold0_val"]]),
        ("all_complete", case_metric_rows),
    ]
    for split_name, items in summary_splits:
        baseline_summary.append(
            {
                "split": split_name,
                "cases": len(items),
                "mean_dice": avg([r["dice"] for r in items]),
                "mean_precision": avg([r["precision"] for r in items]),
                "mean_recall": avg([r["recall"] for r in items]),
                "mean_hd": avg([r["hd"] for r in items]),
                "mean_hd95": avg([r["hd95"] for r in items]),
                "mean_pred_components": avg([r["pred_components"] for r in items]),
                "mean_pred_voxels": avg([r["pred_voxels"] for r in items]),
                "mean_gt_voxels": avg([r["gt_voxels"] for r in items]),
            }
        )
    for center in sorted({r["center"] for r in case_metric_rows if r["split"] == "all_complete"}):
        items = [r for r in case_metric_rows if r["split"] == "all_complete" and r["center"] == center]
        baseline_summary.append(
            {
                "split": f"all_complete_center:{center}",
                "cases": len(items),
                "mean_dice": avg([r["dice"] for r in items]),
                "mean_precision": avg([r["precision"] for r in items]),
                "mean_recall": avg([r["recall"] for r in items]),
                "mean_hd": avg([r["hd"] for r in items]),
                "mean_hd95": avg([r["hd95"] for r in items]),
                "mean_pred_components": avg([r["pred_components"] for r in items]),
                "mean_pred_voxels": avg([r["pred_voxels"] for r in items]),
                "mean_gt_voxels": avg([r["gt_voxels"] for r in items]),
            }
        )

    group_summary = summarize_groups(metadata_rows)
    val_group_counts = Counter(str(r["modality_group"]) for r in val_rows)
    manifest = {
        "created_at": timestamp,
        "repo_root": str(REPO_ROOT),
        "task": "20260620_t2_present_edema_pilot",
        "train_cases": len(train_cases),
        "complete_cases": len(complete_cache),
        "complete_fold0_train_cases": len(complete_train),
        "complete_fold0_val_cases": len(complete_val),
        "train_modality_groups": dict(Counter(r["modality_group"] for r in metadata_rows)),
        "val_modality_groups": dict(val_group_counts),
        "label_mapping": {"myocardium": 1, "LV_blood": 2, "RV_blood": 3, "edema": 4, "scar": 5},
        "feature_baseline": {
            "diagnostic_only": True,
            "uses_gt_myo_scar_prior": True,
            "selected_on": "fold0_complete_train",
            "threshold": best["threshold"],
            "prior_iterations": best["prior_iterations"],
            "min_component_mm3": best["min_component_mm3"],
        },
        "outputs": {
            "metadata_csv": str(out_root / "myops_case_metadata.csv"),
            "group_summary_csv": str(out_root / "myops_group_summary.csv"),
            "validation_modality_csv": str(out_root / "myops_validation_modality_metadata.csv"),
            "threshold_grid_csv": str(out_root / "feature_baseline_threshold_grid.csv"),
            "case_metrics_csv": str(out_root / "feature_baseline_case_metrics.csv"),
            "summary_json": str(out_root / "feature_baseline_summary.json"),
            "summary_md": str(out_root / "summary.md"),
        },
    }

    write_csv(out_root / "myops_case_metadata.csv", metadata_rows)
    write_csv(out_root / "myops_group_summary.csv", group_summary)
    write_csv(out_root / "myops_validation_modality_metadata.csv", val_rows)
    write_csv(out_root / "feature_baseline_threshold_grid.csv", grid_rows)
    write_csv(out_root / "feature_baseline_case_metrics.csv", case_metric_rows)
    write_json(out_root / "feature_baseline_summary.json", {"selected_config": best, "summary": baseline_summary})
    write_json(out_root / "manifest.json", manifest)

    modality_table = [
        {"split": "train", "modality_group": k, "cases": v}
        for k, v in sorted(Counter(r["modality_group"] for r in metadata_rows).items())
    ] + [
        {"split": "validation_raw", "modality_group": k, "cases": v}
        for k, v in sorted(val_group_counts.items())
    ]
    mechanism_rows = [
        {
            "group": r["group"],
            "cases": r["cases"],
            "edema_positive_cases": r["edema_positive_cases"],
            "scar_positive_cases": r["scar_positive_cases"],
            "edema_voxel_fraction_mean": r["edema_voxel_fraction_mean"],
            "t2_edema_vs_myo_contrast_median": r["t2_edema_vs_myo_contrast_median"],
        }
        for r in group_summary
        if r["group_type"] == "modality_group"
    ]
    summary_md = f"""# T2-present edema pilot summary

Task: `20260620_t2_present_edema_pilot`

## Data coverage

{markdown_table(modality_table, ["split", "modality_group", "cases"])}

Complete train cases: `{len(complete_cache)}`. Fold0 complete train/val: `{len(complete_train)}` / `{len(complete_val)}`.

## Label mechanism by modality group

{markdown_table(mechanism_rows, ["group", "cases", "edema_positive_cases", "scar_positive_cases", "edema_voxel_fraction_mean", "t2_edema_vs_myo_contrast_median"])}

## Feature baseline

Diagnostic rule: robust-z T2 threshold inside a GT myocardium/scar support prior, followed by connected-component minimum-volume filtering. This is an oracle-prior feasibility baseline, not a submission candidate.

Selected config on fold0 complete train:

{markdown_table([best], ["threshold", "prior_iterations", "min_component_mm3", "cases", "mean_dice", "mean_precision", "mean_recall", "mean_hd95", "mean_components"])}

Metrics:

{markdown_table(baseline_summary, ["split", "cases", "mean_dice", "mean_precision", "mean_recall", "mean_hd", "mean_hd95", "mean_pred_components"])}

## Outputs

- `myops_case_metadata.csv`
- `myops_group_summary.csv`
- `myops_validation_modality_metadata.csv`
- `feature_baseline_threshold_grid.csv`
- `feature_baseline_case_metrics.csv`
- `feature_baseline_summary.json`
- `feature_baseline_predictions/`
- `manifest.json`
"""
    (out_root / "summary.md").write_text(summary_md, encoding="utf-8")

    print(f"OUT_ROOT={out_root}")
    print(f"COMPLETE_CASES={len(complete_cache)}")
    print(f"FOLD0_COMPLETE_TRAIN={len(complete_train)}")
    print(f"FOLD0_COMPLETE_VAL={len(complete_val)}")
    print(f"BEST_CONFIG={best}")
    return out_root


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--myops-train", type=Path, default=REPO_ROOT / "data/CARE_Challenge/MyoPS_train")
    ap.add_argument("--myops-val", type=Path, default=REPO_ROOT / "data/CARE_Challenge/MyoPS_val")
    ap.add_argument("--splits-json", type=Path, default=REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json")
    ap.add_argument("--output-root", type=Path, default=None)
    ap.add_argument("--threshold-min", type=float, default=-0.5)
    ap.add_argument("--threshold-max", type=float, default=2.5)
    ap.add_argument("--threshold-step", type=float, default=1.0)
    ap.add_argument("--prior-iterations", type=str, default="2")
    ap.add_argument("--min-component-mm3", type=str, default="50")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
