#!/usr/bin/env python3
"""Round8 Dice/HD and component profile for nnU-Net vs MyoPS-Net."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, generate_binary_structure
from skimage import measure


CLASSES = {
    4: "myops_edema",
    5: "myops_scar",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_fold_cases(fold_json: Path, fold: int) -> list[str]:
    data = load_json(fold_json)
    folds = data["folds"]
    if fold < 0 or fold >= len(folds):
        raise ValueError(f"fold {fold} out of range [0, {len(folds)})")
    return sorted(folds[fold]["val"])


def load_modalities(data_root: Path) -> dict[str, dict[str, bool]]:
    metadata = data_root / "modalities_present.json"
    if not metadata.is_file():
        return {}
    raw = load_json(metadata)
    return {
        case_id: {
            "c0": bool(info.get("c0", False)),
            "lge": bool(info.get("lge", False)),
            "t2": bool(info.get("t2", False)),
        }
        for case_id, info in raw.items()
    }


def group_name(info: dict[str, bool]) -> str:
    parts = []
    if info.get("c0"):
        parts.append("C0")
    if info.get("lge"):
        parts.append("LGE")
    if info.get("t2"):
        parts.append("T2")
    return "+".join(parts) or "none"


def read_sitk(path: Path) -> sitk.Image:
    return sitk.ReadImage(str(path))


def resample_to_reference(moving: sitk.Image, reference: sitk.Image) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(moving)


def dice(pred: np.ndarray, gt: np.ndarray) -> float | None:
    p_sum = float(pred.sum())
    g_sum = float(gt.sum())
    if g_sum < 1e-8:
        return None if p_sum < 1e-8 else 0.0
    denom = p_sum + g_sum
    if denom < 1e-8:
        return None
    return float(2.0 * np.logical_and(pred, gt).sum(dtype=np.float64) / denom)


def surface_distances(pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, ...]) -> np.ndarray | None:
    if not pred.any() or not gt.any():
        return None
    struct = generate_binary_structure(pred.ndim, 1)
    surf_p = pred & ~binary_erosion(pred, structure=struct)
    surf_g = gt & ~binary_erosion(gt, structure=struct)
    dt_g = distance_transform_edt(~surf_g, sampling=spacing_zyx)
    dt_p = distance_transform_edt(~surf_p, sampling=spacing_zyx)
    d1 = dt_g[surf_p] if surf_p.any() else np.array([0.0])
    d2 = dt_p[surf_g] if surf_g.any() else np.array([0.0])
    return np.concatenate([d1.ravel(), d2.ravel()]).astype(np.float64, copy=False)


def bbox(mask: np.ndarray) -> tuple[int, int, int, int, int, int] | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    lo = coords.min(axis=0)
    hi = coords.max(axis=0) + 1
    return (int(lo[0]), int(hi[0]), int(lo[1]), int(hi[1]), int(lo[2]), int(hi[2]))


def bbox_overlaps(a: tuple[int, int, int, int, int, int], b: tuple[int, int, int, int, int, int], margin: int) -> bool:
    az0, az1, ay0, ay1, ax0, ax1 = a
    bz0, bz1, by0, by1, bx0, bx1 = b
    return (
        az0 < bz1 + margin
        and az1 > bz0 - margin
        and ay0 < by1 + margin
        and ay1 > by0 - margin
        and ax0 < bx1 + margin
        and ax1 > bx0 - margin
    )


def component_profile(
    pred: np.ndarray,
    gt: np.ndarray,
    anatomy_support: np.ndarray,
    *,
    min_component_voxels: int,
    remote_dilation_iters: int,
    bbox_margin_voxels: int,
) -> dict[str, int | float | None]:
    labels = measure.label(pred, connectivity=1)
    components = measure.regionprops(labels)
    support_dilated = binary_dilation(anatomy_support, iterations=remote_dilation_iters)
    support_bbox = bbox(anatomy_support)
    n_small = 0
    n_remote = 0
    n_bbox_outlier = 0
    largest = 0
    for component in components:
        comp = labels == component.label
        area = int(component.area)
        largest = max(largest, area)
        if area < min_component_voxels:
            n_small += 1
        if not np.any(comp & support_dilated):
            n_remote += 1
        comp_bbox = (
            int(component.bbox[0]),
            int(component.bbox[3]),
            int(component.bbox[1]),
            int(component.bbox[4]),
            int(component.bbox[2]),
            int(component.bbox[5]),
        )
        if support_bbox is None or not bbox_overlaps(comp_bbox, support_bbox, bbox_margin_voxels):
            n_bbox_outlier += 1

    pred_vol = int(pred.sum())
    gt_vol = int(gt.sum())
    if gt_vol == 0:
        volume_ratio = None if pred_vol == 0 else float("inf")
    else:
        volume_ratio = float(pred_vol / gt_vol)
    return {
        "pred_components": len(components),
        "pred_small_components": n_small,
        "pred_remote_components": n_remote,
        "pred_bbox_outlier_components": n_bbox_outlier,
        "pred_largest_component_voxels": largest,
        "pred_voxels": pred_vol,
        "gt_voxels": gt_vol,
        "pathology_volume_ratio": volume_ratio,
    }


def fmt(value: float | int | None) -> str:
    if value is None:
        return "NA"
    if isinstance(value, int):
        return str(value)
    if np.isinf(value):
        return "inf"
    return f"{value:.4f}"


def mean_non_null(values: list[float | None]) -> float | None:
    kept = [float(v) for v in values if v is not None and not np.isinf(v)]
    return float(np.mean(kept)) if kept else None


def write_md(rows: list[dict[str, object]], output_md: Path, leaderboard_note: str) -> None:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["model"]), str(row["class_name"]))].append(row)

    lines = [
        "# MyoPS-Net round8 nnU-Net vs MyoPS-Net HD/component profile",
        "",
        leaderboard_note,
        "",
        "| model | class | n eval | mean Dice | mean HD | mean HD95 | mean components | small comps | remote comps | bbox outlier comps | mean pred/GT volume ratio |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for (model, class_name), group_rows in sorted(grouped.items()):
        n_eval = sum(1 for r in group_rows if r["dice"] is not None)
        ratios = [r["pathology_volume_ratio"] for r in group_rows if r["pathology_volume_ratio"] is not None]
        lines.append(
            f"| {model} | {class_name} | {n_eval} | "
            f"{fmt(mean_non_null([r['dice'] for r in group_rows]))} | "
            f"{fmt(mean_non_null([r['hd'] for r in group_rows]))} | "
            f"{fmt(mean_non_null([r['hd95'] for r in group_rows]))} | "
            f"{fmt(mean_non_null([float(r['pred_components']) for r in group_rows]))} | "
            f"{sum(int(r['pred_small_components']) for r in group_rows)} | "
            f"{sum(int(r['pred_remote_components']) for r in group_rows)} | "
            f"{sum(int(r['pred_bbox_outlier_components']) for r in group_rows)} | "
            f"{fmt(mean_non_null(ratios))} |"
        )

    lines.extend(
        [
            "",
            "Definitions:",
            "- HD/HD95 are computed only when both prediction and GT are positive for that class.",
            "- Dice follows CARE pathology handling: GT-empty cases are omitted if prediction is empty, and scored 0 if prediction has false positives.",
            "- Remote components are predicted pathology components with no overlap against dilated GT myocardium/pathology support; this is diagnostic only and is not used for postprocessing.",
            "- Bbox outlier components are predicted components whose bbox does not overlap the GT myocardium/pathology bbox with a fixed voxel margin.",
        ]
    )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nnunet-pred-dir", type=Path, required=True)
    ap.add_argument("--myopsnet-pred-dir", type=Path, required=True)
    ap.add_argument("--gt-dir", type=Path, required=True)
    ap.add_argument("--fold-json", type=Path, required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--output-csv", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    ap.add_argument("--min-component-voxels", type=int, default=20)
    ap.add_argument("--remote-dilation-iters", type=int, default=3)
    ap.add_argument("--bbox-margin-voxels", type=int, default=8)
    ap.add_argument(
        "--leaderboard-note",
        default="Leaderboard note: OrganAgent hosted nnU-Net branch currently scores scar Dice 0.5969/HD 16.2536 and edema Dice 0.6496/HD 22.0125.",
    )
    args = ap.parse_args()

    case_ids = load_fold_cases(args.fold_json, args.fold)
    modalities = load_modalities(args.data_root)
    models = {
        "nnU-Net_fold0": args.nnunet_pred_dir,
        "MyoPS-Net_round4_combined_safe": args.myopsnet_pred_dir,
    }
    rows: list[dict[str, object]] = []

    for case_id in case_ids:
        gt_path = args.gt_dir / f"{case_id}.nii.gz"
        if not gt_path.is_file():
            raise FileNotFoundError(f"Missing GT: {gt_path}")
        gt_img = read_sitk(gt_path)
        gt_arr = sitk.GetArrayFromImage(gt_img).astype(np.uint8, copy=False)
        spacing_zyx = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        anatomy_support = (gt_arr == 1) | (gt_arr == 4) | (gt_arr == 5)
        info = modalities.get(case_id, {"c0": False, "lge": True, "t2": False})

        for model_name, pred_dir in models.items():
            pred_path = pred_dir / f"{case_id}.nii.gz"
            if not pred_path.is_file():
                raise FileNotFoundError(f"Missing prediction for {model_name}: {pred_path}")
            pred_img = resample_to_reference(read_sitk(pred_path), gt_img)
            pred_arr = sitk.GetArrayFromImage(pred_img).astype(np.uint8, copy=False)
            for class_id, class_name in CLASSES.items():
                pred_mask = pred_arr == class_id
                gt_mask = gt_arr == class_id
                dists = surface_distances(pred_mask, gt_mask, spacing_zyx)
                profile = component_profile(
                    pred_mask,
                    gt_mask,
                    anatomy_support,
                    min_component_voxels=args.min_component_voxels,
                    remote_dilation_iters=args.remote_dilation_iters,
                    bbox_margin_voxels=args.bbox_margin_voxels,
                )
                row: dict[str, object] = {
                    "case_id": case_id,
                    "model": model_name,
                    "class_id": class_id,
                    "class_name": class_name,
                    "modality_group": group_name(info),
                    "t2_present": bool(info.get("t2", False)),
                    "dice": dice(pred_mask, gt_mask),
                    "hd": None if dists is None else float(np.max(dists)),
                    "hd95": None if dists is None else float(np.percentile(dists, 95)),
                }
                row.update(profile)
                rows.append(row)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "model",
        "class_id",
        "class_name",
        "modality_group",
        "t2_present",
        "dice",
        "hd",
        "hd95",
        "pred_components",
        "pred_small_components",
        "pred_remote_components",
        "pred_bbox_outlier_components",
        "pred_largest_component_voxels",
        "pred_voxels",
        "gt_voxels",
        "pathology_volume_ratio",
    ]
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
    write_md(rows, args.output_md, args.leaderboard_note)
    print(f"Wrote {args.output_csv} and {args.output_md}")


if __name__ == "__main__":
    main()
