#!/usr/bin/env python3
"""Postprocess cascade revision predictions and evaluate component pruning modes."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy import ndimage


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round4_fold0_short_train_eval as base_eval


PATHOLOGY_LABELS = (4, 5)
MODES = (
    "pathology_overlap_dilate1",
    "pathology_overlap_dilate2",
    "edema_overlap_dilate2_keep_scar",
    "top2_pathology_overlap_dilate2",
)


def rel(path: Path) -> str:
    full = path if path.is_absolute() else REPO_ROOT / path
    try:
        return str(full.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_pred(path: Path, reference: sitk.Image) -> np.ndarray:
    img = sitk.ReadImage(str(path))
    if (
        img.GetSize() != reference.GetSize()
        or img.GetSpacing() != reference.GetSpacing()
        or img.GetOrigin() != reference.GetOrigin()
        or img.GetDirection() != reference.GetDirection()
    ):
        img = sitk.Resample(img, reference, sitk.Transform(), sitk.sitkNearestNeighbor, 0, img.GetPixelID())
    return sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def component_slices(mask: np.ndarray) -> tuple[np.ndarray, int]:
    structure = ndimage.generate_binary_structure(mask.ndim, 1)
    return ndimage.label(mask.astype(bool), structure=structure)


def dilate(mask: np.ndarray, iterations: int) -> np.ndarray:
    if iterations <= 0:
        return mask.astype(bool, copy=False)
    structure = ndimage.generate_binary_structure(mask.ndim, 1)
    return ndimage.binary_dilation(mask.astype(bool, copy=False), structure=structure, iterations=iterations)


def parse_mode(mode: str) -> tuple[int, bool, int | None]:
    if mode == "pathology_overlap_dilate1":
        return 1, False, None
    if mode == "pathology_overlap_dilate2":
        return 2, False, None
    if mode == "edema_overlap_dilate2_keep_scar":
        return 2, True, None
    if mode == "top2_pathology_overlap_dilate2":
        return 2, False, 2
    raise ValueError(mode)


def prune_candidate(candidate: np.ndarray, baseline: np.ndarray, mode: str) -> tuple[np.ndarray, list[dict[str, object]]]:
    iterations, keep_candidate_scar, top_k = parse_mode(mode)
    out = candidate.copy() if keep_candidate_scar else baseline.copy()
    rows: list[dict[str, object]] = []
    labels = (4,) if keep_candidate_scar else PATHOLOGY_LABELS
    for label_id in labels:
        support = dilate(baseline == label_id, iterations)
        cc, n_cc = component_slices(candidate == label_id)
        components: list[tuple[int, int, bool]] = []
        for idx in range(1, n_cc + 1):
            comp = cc == idx
            size = int(comp.sum())
            overlaps = bool(np.logical_and(comp, support).any())
            components.append((idx, size, overlaps))
        kept = 0
        ranked = sorted((item for item in components if item[2]), key=lambda x: x[1], reverse=True)
        allowed = {idx for idx, _, _ in ranked[:top_k]} if top_k else {idx for idx, _, _ in ranked}
        for idx, size, overlaps in components:
            comp = cc == idx
            keep = overlaps and idx in allowed
            if keep:
                out[comp] = label_id
                kept += 1
            else:
                out[comp] = baseline[comp]
            rows.append(
                {
                    "label": label_id,
                    "component_index": idx,
                    "component_voxels": size,
                    "overlaps_baseline_support": overlaps,
                    "kept": keep,
                }
            )
        if n_cc == 0:
            rows.append(
                {
                    "label": label_id,
                    "component_index": 0,
                    "component_voxels": 0,
                    "overlaps_baseline_support": False,
                    "kept": False,
                }
            )
    return out.astype(np.uint8, copy=False), rows


def write_like(path: Path, arr: np.ndarray, reference: sitk.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(arr.astype(np.uint8, copy=False))
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def run_eval(pred_dir: Path, out_dir: Path, cascade_variant: str) -> None:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/diagnostics/laneA_round10_refiner_eval.py"),
        "--candidate-pred-dir",
        str(pred_dir),
        "--out-root",
        str(out_dir),
        "--cascade-variant",
        cascade_variant,
    ]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def first_subset_delta(path: Path, subset: str = "t2_present_gt_positive") -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("subset") == subset:
                return row
    return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pred-dir", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument(
        "--cascade-variant",
        required=True,
        choices=["nnunet_pathology_teacher_srr_refiner", "coarse_to_fine_srr_roi"],
    )
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--modes", nargs="+", default=list(MODES))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_root = args.out_root
    out_root.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, object]] = []
    case_ids = base_eval.fold0_cases()
    for mode in args.modes:
        mode_root = out_root / "variants" / f"{args.source_label}__{mode}"
        pred_dir = mode_root / "predictions" / f"{args.source_label}__{mode}" / "validation"
        component_rows: list[dict[str, object]] = []
        for case_id in case_ids:
            gt_img, _ = base_eval.read_label(base_eval.GT_DIR / f"{case_id}.nii.gz")
            baseline = read_pred(base_eval.BASELINE_PRED_DIR / f"{case_id}.nii.gz", gt_img)
            candidate = read_pred(args.source_pred_dir / f"{case_id}.nii.gz", gt_img)
            post, rows = prune_candidate(candidate, baseline, mode)
            for row in rows:
                row.update({"case_id": case_id, "mode": mode, "source_label": args.source_label})
            component_rows.extend(rows)
            write_like(pred_dir / f"{case_id}.nii.gz", post, gt_img)
        write_csv(mode_root / "postprocess_components.csv", component_rows)
        run_eval(pred_dir, mode_root, args.cascade_variant)
        subset = first_subset_delta(mode_root / "baseline_vs_refiner_by_subset.csv")
        summary_rows.append(
            {
                "source_label": args.source_label,
                "mode": mode,
                "variant_dir": rel(mode_root),
                "prediction_dir": rel(pred_dir),
                "delta_t2pos_edema_dice": subset.get("delta_edema_dice", ""),
                "delta_t2pos_edema_hd95_improvement": subset.get("delta_edema_hd95_improvement", ""),
                "delta_t2pos_component_count_improvement": subset.get("delta_edema_component_count_improvement", ""),
                "delta_t2pos_remote_fp_improvement": subset.get("delta_edema_remote_fp_improvement", ""),
                "delta_t2pos_scar_dice": subset.get("delta_scar_dice", ""),
                "decision_table": rel(mode_root / "round10_decision_table.md"),
            }
        )
    write_csv(out_root / f"{args.source_label}_postprocess_summary.csv", summary_rows)
    (out_root / f"{args.source_label}_summary.json").write_text(
        json.dumps({"source_label": args.source_label, "modes": args.modes, "rows": summary_rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    print({"source_label": args.source_label, "modes": len(args.modes), "out_root": str(out_root)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
