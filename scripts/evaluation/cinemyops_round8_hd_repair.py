#!/usr/bin/env python3
"""Round8 CineMyoPS package QA and export-only HD repair variants.

This script intentionally does not train. It audits raw validation submission
predictions, builds compact-label postprocessed protocol predictions, and
records enough geometry/component evidence to interpret hosted HD failures.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_dilation, generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_SCAR = 2221
RAW_ANATOMY = (200, 500)
COMPACT_SCAR = 3
COMPACT_ANATOMY = (1, 2)


def read_image(path: Path) -> sitk.Image:
    return sitk.ReadImage(str(path))


def read_array(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = read_image(path)
    return img, sitk.GetArrayFromImage(img)


def write_like(arr: np.ndarray, ref: sitk.Image, out_path: Path) -> None:
    out = sitk.GetImageFromArray(arr.astype(np.uint8, copy=False))
    out.CopyInformation(ref)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(out, str(out_path))


def bbox(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    return coords.min(axis=0), coords.max(axis=0)


def bbox_distance_mm(
    a: tuple[np.ndarray, np.ndarray] | None,
    b: tuple[np.ndarray, np.ndarray] | None,
    spacing_zyx: tuple[float, ...],
) -> float | None:
    if a is None or b is None:
        return None
    gap = np.zeros(len(spacing_zyx), dtype=np.float64)
    for axis in range(len(spacing_zyx)):
        if a[1][axis] < b[0][axis]:
            gap[axis] = b[0][axis] - a[1][axis]
        elif b[1][axis] < a[0][axis]:
            gap[axis] = a[0][axis] - b[1][axis]
    return float(np.linalg.norm(gap * np.asarray(spacing_zyx, dtype=np.float64)))


def component_table(mask: np.ndarray, anatomy_mask: np.ndarray, spacing_zyx: tuple[float, ...]) -> list[dict]:
    struct = generate_binary_structure(mask.ndim, 1)
    cc, n_cc = label(mask, structure=struct)
    anatomy_bbox = bbox(anatomy_mask)
    rows = []
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        comp_bbox = bbox(comp)
        voxels = int(comp.sum())
        rows.append(
            {
                "component": idx,
                "voxels": voxels,
                "bbox_distance_to_anatomy_mm": bbox_distance_mm(comp_bbox, anatomy_bbox, spacing_zyx),
            }
        )
    rows.sort(key=lambda item: item["voxels"], reverse=True)
    return rows


def case_id_from_submission_path(path: Path) -> str:
    return path.name.replace("_pred.nii.gz", "")


def audit_validation_tree(cine_submission_tree: Path, out_csv: Path, out_md: Path) -> list[dict]:
    rows: list[dict] = []
    for pred_path in sorted(cine_submission_tree.glob("Anonymous Center/Case*/Case*_pred.nii.gz")):
        cid = case_id_from_submission_path(pred_path)
        img, arr = read_array(pred_path)
        spacing_zyx = tuple(float(v) for v in img.GetSpacing()[::-1])
        counts = Counter({int(v): int(c) for v, c in zip(*np.unique(arr, return_counts=True))})
        scar = arr == RAW_SCAR
        anatomy = np.isin(arr, RAW_ANATOMY)
        comps = component_table(scar, anatomy, spacing_zyx)
        largest = comps[0]["voxels"] if comps else 0
        total = int(scar.sum())
        far = [c for c in comps if c["bbox_distance_to_anatomy_mm"] not in (None, 0.0)]
        rows.append(
            {
                "case": cid,
                "shape_zyx": "x".join(str(v) for v in arr.shape),
                "spacing_zyx": "x".join(f"{v:.6g}" for v in spacing_zyx),
                "labels": json.dumps(dict(sorted(counts.items())), sort_keys=True),
                "scar_2221_voxels": total,
                "anatomy_200_500_voxels": int(anatomy.sum()),
                "scar_components": len(comps),
                "largest_scar_component_voxels": largest,
                "largest_scar_component_frac": float(largest / total) if total else 0.0,
                "small_scar_components": max(0, len(comps) - 1),
                "far_scar_components_from_anatomy_bbox": len(far),
                "max_component_bbox_distance_to_anatomy_mm": max(
                    [float(c["bbox_distance_to_anatomy_mm"] or 0.0) for c in comps],
                    default=0.0,
                ),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["case"])
        writer.writeheader()
        writer.writerows(rows)

    total_scar = sum(int(r["scar_2221_voxels"]) for r in rows)
    outlier_cases = [
        r
        for r in rows
        if int(r["small_scar_components"]) > 0 or int(r["far_scar_components_from_anatomy_bbox"]) > 0
    ]
    lines = [
        "# CineMyoPS round8 validation zip QC",
        "",
        f"- cases: {len(rows)}",
        f"- total raw 2221 voxels: {total_scar}",
        f"- cases with extra scar components or bbox-distance outliers: {len(outlier_cases)}",
        "",
        "| case | 2221 voxels | components | largest frac | far bbox comps | max bbox distance mm |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(
            "| {case} | {scar_2221_voxels} | {scar_components} | {largest_scar_component_frac:.4f} | "
            "{far_scar_components_from_anatomy_bbox} | {max_component_bbox_distance_to_anatomy_mm:.2f} |".format(**r)
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def load_fold_train_case_ids(splits_json: Path, fold: int) -> list[str]:
    with splits_json.open(encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data["folds"][fold]["train"])


def train_scar_volume_stats(labels_dir: Path, splits_json: Path, fold: int) -> dict:
    vols = []
    for cid in load_fold_train_case_ids(splits_json, fold):
        path = labels_dir / f"{cid}.nii.gz"
        if not path.is_file():
            continue
        _, arr = read_array(path)
        count = int((arr == COMPACT_SCAR).sum())
        if count > 0:
            vols.append(count)
    if not vols:
        raise RuntimeError("No positive class_3 volumes found in protocol train labels")
    a = np.asarray(vols, dtype=np.float64)
    return {
        "n_positive_train_cases": int(len(vols)),
        "min": int(np.min(a)),
        "p50": float(np.percentile(a, 50)),
        "p90": float(np.percentile(a, 90)),
        "p95": float(np.percentile(a, 95)),
        "max": int(np.max(a)),
    }


def keep_largest_components(mask: np.ndarray, k: int = 1, max_voxels: int | None = None) -> np.ndarray:
    struct = generate_binary_structure(mask.ndim, 1)
    cc, n_cc = label(mask, structure=struct)
    if n_cc == 0:
        return mask
    sizes = [(idx, int((cc == idx).sum())) for idx in range(1, n_cc + 1)]
    sizes.sort(key=lambda item: item[1], reverse=True)
    keep = np.zeros(mask.shape, dtype=bool)
    kept = 0
    for idx, size in sizes[:k if max_voxels is None else len(sizes)]:
        if max_voxels is not None and kept > 0 and kept + size > max_voxels:
            continue
        keep |= cc == idx
        kept += size
        if max_voxels is not None and kept >= max_voxels:
            break
        if max_voxels is None and int(keep.sum()) >= sum(s for _, s in sizes[:k]):
            break
    return keep


def repair_case(
    arr: np.ndarray,
    anatomy_arr: np.ndarray | None,
    mode: str,
    dilation_iters: int,
    max_scar_voxels: int,
) -> np.ndarray:
    out = arr.copy()
    scar = out == COMPACT_SCAR
    if mode == "pathology_largest_component":
        keep = keep_largest_components(scar, k=1)
    elif mode == "pathology_myocardium_roi":
        if anatomy_arr is None:
            raise ValueError("pathology_myocardium_roi requires anatomy predictions")
        roi = np.isin(anatomy_arr, COMPACT_ANATOMY)
        roi = binary_dilation(roi, structure=generate_binary_structure(roi.ndim, 1), iterations=dilation_iters)
        keep = scar & roi
    elif mode == "pathology_volume_guard":
        keep = keep_largest_components(scar, k=9999, max_voxels=max_scar_voxels)
    elif mode == "pathology_roi_lcc_volume_guard":
        if anatomy_arr is None:
            raise ValueError("pathology_roi_lcc_volume_guard requires anatomy predictions")
        roi = np.isin(anatomy_arr, COMPACT_ANATOMY)
        roi = binary_dilation(roi, structure=generate_binary_structure(roi.ndim, 1), iterations=dilation_iters)
        keep = keep_largest_components(scar & roi, k=1, max_voxels=max_scar_voxels)
    else:
        raise ValueError(f"Unknown mode: {mode}")
    out[np.logical_and(scar, ~keep)] = 0
    return out


def build_repair_variants(
    source_dir: Path,
    anatomy_dir: Path,
    output_root: Path,
    modes: list[str],
    dilation_iters: int,
    max_scar_voxels: int,
) -> dict[str, Path]:
    outputs = {}
    for mode in modes:
        out_dir = output_root / mode / "fold_0"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for pred_path in sorted(source_dir.glob("*.nii.gz")):
            cid = pred_path.name.replace(".nii.gz", "")
            img, arr = read_array(pred_path)
            anatomy_arr = None
            anatomy_path = anatomy_dir / pred_path.name
            if anatomy_path.is_file():
                _, anatomy_arr = read_array(anatomy_path)
            repaired = repair_case(arr.astype(np.uint8, copy=False), anatomy_arr, mode, dilation_iters, max_scar_voxels)
            write_like(repaired, img, out_dir / pred_path.name)
        outputs[mode] = out_dir
    return outputs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--validation-tree-cine",
        type=Path,
        default=REPO_ROOT
        / "results/submissions/care_myocardium_validation/upload_ready/"
        / "nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/submission_tree/CineMyoPS",
    )
    ap.add_argument("--diagnostic-csv", type=Path, default=REPO_ROOT / "results/diagnostics/baseline_paper_models/CineMyoPS/round08_hd_repair/CineMyoPS_round8_validation_zip_qc.csv")
    ap.add_argument("--diagnostic-md", type=Path, default=REPO_ROOT / "results/diagnostics/baseline_paper_models/CineMyoPS/round08_hd_repair/CineMyoPS_round8_validation_zip_qc.md")
    ap.add_argument("--source-dir", type=Path, default=REPO_ROOT / "results/predictions/CineMyoPS_R6_pathology_direct/fold_0")
    ap.add_argument("--anatomy-dir", type=Path, default=REPO_ROOT / "results/predictions/CineMyoPS_R6_cardiac_only/fold_0")
    ap.add_argument("--labels-dir", type=Path, default=REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/labelsTr")
    ap.add_argument("--splits-json", type=Path, default=REPO_ROOT / "data/benchmarks/protocol/splits_CineMyoPS.json")
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--repair-output-root", type=Path, default=REPO_ROOT / "results/predictions/CineMyoPS_R8_hd_repair")
    ap.add_argument("--summary-json", type=Path, default=REPO_ROOT / "results/diagnostics/baseline_paper_models/CineMyoPS/round08_hd_repair/CineMyoPS_round8_repair_summary.json")
    ap.add_argument("--dilation-iters", type=int, default=3)
    ap.add_argument(
        "--modes",
        nargs="+",
        default=[
            "pathology_largest_component",
            "pathology_myocardium_roi",
            "pathology_volume_guard",
            "pathology_roi_lcc_volume_guard",
        ],
    )
    args = ap.parse_args()

    qc_rows = audit_validation_tree(args.validation_tree_cine, args.diagnostic_csv, args.diagnostic_md)
    volume_stats = train_scar_volume_stats(args.labels_dir, args.splits_json, args.fold)
    max_scar_voxels = int(round(volume_stats["p95"]))
    outputs = build_repair_variants(
        args.source_dir,
        args.anatomy_dir,
        args.repair_output_root,
        args.modes,
        args.dilation_iters,
        max_scar_voxels,
    )
    summary = {
        "validation_qc_csv": str(args.diagnostic_csv),
        "validation_qc_md": str(args.diagnostic_md),
        "validation_cases": len(qc_rows),
        "train_class3_volume_stats": volume_stats,
        "volume_guard_max_scar_voxels": max_scar_voxels,
        "repair_outputs": {mode: str(path) for mode, path in outputs.items()},
        "dilation_iters": args.dilation_iters,
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
