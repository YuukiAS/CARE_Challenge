#!/usr/bin/env python3
"""CineMyoPS component, volume, bbox, Dice, HD, and HD95 audit.

This is a read-only diagnostic entrypoint for existing compact-label prediction
directories. It does not train, infer, submit Slurm jobs, or create validation
packages.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_erosion, distance_transform_edt, generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
CLASS_MYOCARDIUM = 1
CLASS_SCAR = 3
DEFAULT_CLASSES = (CLASS_MYOCARDIUM, CLASS_SCAR)


@dataclass(frozen=True)
class VariantDir:
    name: str
    path: Path


def read_image(path: Path) -> sitk.Image:
    return sitk.ReadImage(str(path))


def read_array(path: Path) -> tuple[sitk.Image, np.ndarray]:
    image = read_image(path)
    return image, sitk.GetArrayFromImage(image)


def resample_to_reference(moving: sitk.Image, reference: sitk.Image) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(moving)


def parse_variant_dirs(items: list[str]) -> list[VariantDir]:
    variants = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"--pred-dirs entries must be name=path, got: {item}")
        name, raw_path = item.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"Empty variant name in --pred-dirs entry: {item}")
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = (REPO_ROOT / path).resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"Prediction directory for {name!r} not found: {path}")
        variants.append(VariantDir(name=name, path=path))
    if not variants:
        raise ValueError("At least one --pred-dirs name=path entry is required")
    return variants


def collect_case_ids(variants: list[VariantDir], explicit_cases: str | None, fold_json: Path | None, fold: int | None) -> list[str]:
    if explicit_cases:
        return sorted(x.strip() for x in explicit_cases.split(",") if x.strip())
    if fold_json is not None and fold is not None:
        data = json.loads(fold_json.read_text(encoding="utf-8"))
        return sorted(data["folds"][fold]["val"])
    common: set[str] | None = None
    for variant in variants:
        ids = {p.name.replace(".nii.gz", "") for p in variant.path.glob("*.nii.gz")}
        common = ids if common is None else common & ids
    return sorted(common or [])


def dice(pred: np.ndarray, gt: np.ndarray, class_id: int) -> float | None:
    p = pred == class_id
    g = gt == class_id
    denom = float(p.sum() + g.sum())
    if denom < 1e-8:
        return 1.0
    return float(2.0 * np.logical_and(p, g).sum(dtype=np.float64) / denom)


def surface_distances(pred_bin: np.ndarray, gt_bin: np.ndarray, spacing_zyx: tuple[float, ...]) -> np.ndarray:
    p = pred_bin.astype(bool)
    g = gt_bin.astype(bool)
    if not p.any() and not g.any():
        return np.array([0.0], dtype=np.float64)
    if not p.any() or not g.any():
        return np.array([np.inf], dtype=np.float64)
    struct = generate_binary_structure(p.ndim, 1)
    surf_p = p & ~binary_erosion(p, structure=struct)
    surf_g = g & ~binary_erosion(g, structure=struct)
    dt_g = distance_transform_edt(~surf_g, sampling=spacing_zyx)
    dt_p = distance_transform_edt(~surf_p, sampling=spacing_zyx)
    return np.concatenate([dt_g[surf_p].ravel(), dt_p[surf_g].ravel()]).astype(np.float64, copy=False)


def hd(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> float | None:
    distances = surface_distances(pred == class_id, gt == class_id, spacing_zyx)
    if np.isinf(distances).any():
        return None
    return float(np.max(distances))


def hd95(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> float | None:
    distances = surface_distances(pred == class_id, gt == class_id, spacing_zyx)
    if np.isinf(distances).any():
        return None
    return float(np.percentile(distances, 95))


def bbox(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    return coords.min(axis=0), coords.max(axis=0)


def bbox_distance_mm(a: tuple[np.ndarray, np.ndarray] | None, b: tuple[np.ndarray, np.ndarray] | None, spacing_zyx: tuple[float, ...]) -> float | None:
    if a is None or b is None:
        return None
    gap = np.zeros(len(spacing_zyx), dtype=np.float64)
    for axis in range(len(spacing_zyx)):
        if a[1][axis] < b[0][axis]:
            gap[axis] = b[0][axis] - a[1][axis]
        elif b[1][axis] < a[0][axis]:
            gap[axis] = a[0][axis] - b[1][axis]
    return float(np.linalg.norm(gap * np.asarray(spacing_zyx, dtype=np.float64)))


def center_distance_mm(a: tuple[np.ndarray, np.ndarray] | None, b: tuple[np.ndarray, np.ndarray] | None, spacing_zyx: tuple[float, ...]) -> float | None:
    if a is None or b is None:
        return None
    ca = (a[0].astype(np.float64) + a[1].astype(np.float64)) / 2.0
    cb = (b[0].astype(np.float64) + b[1].astype(np.float64)) / 2.0
    return float(np.linalg.norm((ca - cb) * np.asarray(spacing_zyx, dtype=np.float64)))


def component_summary(mask: np.ndarray) -> dict[str, int | float]:
    struct = generate_binary_structure(mask.ndim, 1)
    cc, n_cc = label(mask, structure=struct)
    if n_cc == 0:
        return {
            "scar_components": 0,
            "largest_component_voxels": 0,
            "largest_component_frac": 0.0,
        }
    sizes = [int((cc == idx).sum()) for idx in range(1, n_cc + 1)]
    total = int(mask.sum())
    largest = max(sizes)
    return {
        "scar_components": int(n_cc),
        "largest_component_voxels": int(largest),
        "largest_component_frac": float(largest / total) if total else 0.0,
    }


def maybe_gt(gt_dir: Path | None, cid: str, pred_img: sitk.Image) -> tuple[np.ndarray | None, tuple[float, ...]]:
    spacing = tuple(float(v) for v in pred_img.GetSpacing()[::-1])
    if gt_dir is None:
        return None, spacing
    gt_path = gt_dir / f"{cid}.nii.gz"
    if not gt_path.is_file():
        return None, spacing
    gt_img = read_image(gt_path)
    spacing = tuple(float(v) for v in gt_img.GetSpacing()[::-1])
    return sitk.GetArrayFromImage(gt_img).astype(np.uint8, copy=False), spacing


def label_counts(arr: np.ndarray) -> str:
    values, counts = np.unique(arr, return_counts=True)
    return json.dumps({int(v): int(c) for v, c in zip(values, counts)}, sort_keys=True)


def audit_case(
    variant: VariantDir,
    cid: str,
    gt_dir: Path | None,
    baseline_arr: np.ndarray | None,
    fallback_arr: np.ndarray | None,
) -> dict[str, object]:
    pred_path = variant.path / f"{cid}.nii.gz"
    if not pred_path.is_file():
        raise FileNotFoundError(f"Missing prediction for {variant.name}/{cid}: {pred_path}")
    pred_img, pred_arr_raw = read_array(pred_path)
    pred_arr = pred_arr_raw.astype(np.uint8, copy=False)
    gt_arr, spacing = maybe_gt(gt_dir, cid, pred_img)

    scar = pred_arr == CLASS_SCAR
    anatomy = np.isin(pred_arr, (CLASS_MYOCARDIUM, 2))
    scar_bbox = bbox(scar)
    anatomy_bbox = bbox(anatomy)
    comp = component_summary(scar)

    row: dict[str, object] = {
        "case": cid,
        "variant": variant.name,
        "shape_zyx": "x".join(str(v) for v in pred_arr.shape),
        "spacing_zyx": "x".join(f"{v:.6g}" for v in spacing),
        "labels": label_counts(pred_arr),
        "scar_voxels": int(scar.sum()),
        "anatomy_voxels": int(anatomy.sum()),
        "scar_to_anatomy_volume_ratio": float(scar.sum() / anatomy.sum()) if anatomy.any() else None,
        "scar_components": comp["scar_components"],
        "largest_component_voxels": comp["largest_component_voxels"],
        "largest_component_frac": comp["largest_component_frac"],
        "bbox_distance_mm": bbox_distance_mm(scar_bbox, anatomy_bbox, spacing),
        "center_distance_mm": center_distance_mm(scar_bbox, anatomy_bbox, spacing),
        "fallback_used": False,
        "action_reason": "",
        "removed_voxels": None,
        "removed_components": None,
    }

    if baseline_arr is not None:
        baseline_scar = baseline_arr == CLASS_SCAR
        removed = baseline_scar & ~scar
        row["removed_voxels"] = int(removed.sum())
        row["removed_components"] = component_summary(removed)["scar_components"]
    if fallback_arr is not None and np.array_equal(pred_arr, fallback_arr):
        row["fallback_used"] = True
        row["action_reason"] = "matches_fallback_prediction"
    elif int(row["scar_voxels"]) == 0:
        row["action_reason"] = "empty_scar"
    elif int(row["scar_components"]) > 1:
        row["action_reason"] = "multi_component_scar"
    else:
        row["action_reason"] = "ok"

    for class_id in DEFAULT_CLASSES:
        suffix = f"class_{class_id}"
        if gt_arr is None:
            row[f"dice_{suffix}"] = None
            row[f"hd_{suffix}"] = None
            row[f"hd95_{suffix}"] = None
        else:
            row[f"dice_{suffix}"] = dice(pred_arr, gt_arr, class_id)
            row[f"hd_{suffix}"] = hd(pred_arr, gt_arr, class_id, spacing)
            row[f"hd95_{suffix}"] = hd95(pred_arr, gt_arr, class_id, spacing)
    return row


def read_baseline_arrays(variant: VariantDir | None, case_ids: list[str]) -> dict[str, np.ndarray]:
    if variant is None:
        return {}
    arrays = {}
    for cid in case_ids:
        path = variant.path / f"{cid}.nii.gz"
        if path.is_file():
            _, arr = read_array(path)
            arrays[cid] = arr.astype(np.uint8, copy=False)
    return arrays


def numeric_values(rows: list[dict[str, object]], key: str) -> list[float]:
    vals = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)) and value is not None:
            vals.append(float(value))
    return vals


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    by_variant: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_variant.setdefault(str(row["variant"]), []).append(row)
    summary = {}
    for variant, variant_rows in by_variant.items():
        item: dict[str, object] = {"n_cases": len(variant_rows)}
        for key in (
            "dice_class_1",
            "dice_class_3",
            "hd_class_1",
            "hd_class_3",
            "hd95_class_1",
            "hd95_class_3",
            "scar_voxels",
            "scar_components",
            "removed_voxels",
        ):
            vals = numeric_values(variant_rows, key)
            if vals:
                item[f"mean_{key}"] = float(np.mean(vals))
                item[f"median_{key}"] = float(np.median(vals))
        hd3 = numeric_values(variant_rows, "hd_class_3")
        if hd3:
            item["worst_hd_class_3"] = float(np.max(hd3))
        item["cases_with_removed_components"] = sum(1 for r in variant_rows if isinstance(r.get("removed_components"), int) and int(r["removed_components"]) > 0)
        item["fallback_cases"] = [str(r["case"]) for r in variant_rows if r.get("fallback_used")]
        summary[variant] = item
    return summary


def write_outputs(rows: list[dict[str, object]], output_csv: Path, output_md: Path, output_json: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError("No audit rows were produced")
    fieldnames = list(rows[0].keys())
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows)
    output_json.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")

    lines = ["# CineMyoPS Component/HD Audit", ""]
    lines += [
        "| variant | cases | class_1 Dice | class_3 Dice | class_3 HD | class_3 HD95 | scar comps | removed voxels | worst class_3 HD |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant, item in summary.items():
        lines.append(
            "| {variant} | {n_cases} | {d1} | {d3} | {h3} | {h953} | {cc} | {rv} | {wh3} |".format(
                variant=variant,
                n_cases=item.get("n_cases", 0),
                d1=_fmt(item.get("mean_dice_class_1")),
                d3=_fmt(item.get("mean_dice_class_3")),
                h3=_fmt(item.get("mean_hd_class_3")),
                h953=_fmt(item.get("mean_hd95_class_3")),
                cc=_fmt(item.get("mean_scar_components")),
                rv=_fmt(item.get("mean_removed_voxels")),
                wh3=_fmt(item.get("worst_hd_class_3")),
            )
        )
    lines += ["", f"- CSV: `{output_csv}`", f"- JSON: `{output_json}`"]
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred-dirs", nargs="+", required=True, help="Prediction dirs as name=path.")
    parser.add_argument("--baseline-variant", default=None, help="Variant name used to compute removed voxels/components.")
    parser.add_argument("--fallback-dir", type=Path, default=None, help="Optional fallback prediction dir for equality checks.")
    parser.add_argument("--gt-dir", type=Path, default=REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/labelsTr")
    parser.add_argument("--fold-json", type=Path, default=REPO_ROOT / "data/benchmarks/protocol/splits_CineMyoPS.json")
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--cases", default=None, help="Comma-separated case ids; overrides fold-json.")
    parser.add_argument("--output-prefix", type=Path, default=REPO_ROOT / "results/diagnostics/CineMyoPS_phase0_component_hd")
    args = parser.parse_args()

    variants = parse_variant_dirs(args.pred_dirs)
    case_ids = collect_case_ids(variants, args.cases, args.fold_json, args.fold)
    if not case_ids:
        raise RuntimeError("No case ids found to audit")
    baseline_variant = next((v for v in variants if v.name == args.baseline_variant), None) if args.baseline_variant else None
    if args.baseline_variant and baseline_variant is None:
        raise ValueError(f"--baseline-variant {args.baseline_variant!r} is not among {[v.name for v in variants]}")
    baseline_arrays = read_baseline_arrays(baseline_variant, case_ids)
    fallback_variant = VariantDir("fallback", args.fallback_dir.resolve()) if args.fallback_dir else None
    fallback_arrays = read_baseline_arrays(fallback_variant, case_ids)

    rows = []
    for variant in variants:
        for cid in case_ids:
            rows.append(
                audit_case(
                    variant,
                    cid,
                    args.gt_dir,
                    baseline_arrays.get(cid),
                    fallback_arrays.get(cid),
                )
            )

    prefix = args.output_prefix
    write_outputs(rows, prefix.with_suffix(".csv"), prefix.with_suffix(".md"), prefix.with_suffix(".json"))
    print(json.dumps({"cases": len(case_ids), "variants": [v.name for v in variants], "output_prefix": str(prefix)}, indent=2))


if __name__ == "__main__":
    main()
