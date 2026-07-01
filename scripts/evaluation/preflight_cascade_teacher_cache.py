#!/usr/bin/env python3
"""Build a task-scoped cascade teacher cache preflight for Dataset501 fold0."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_dilation, generate_binary_structure


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata


RAW_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS"
SPLIT_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
NNUNET_VAL_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)
NNUNET_BASE_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
DEFAULT_OUT_DIR = REPO_ROOT / "results/20260629_cascade_teacher_route/teacher_cache"
CLASS_NAMES = {1: "myocardium", 2: "LV_blood", 3: "RV_blood", 4: "myops_edema", 5: "myops_scar"}
ROI_MARGIN_ZYX = (2, 16, 16)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_label(case_id: str) -> np.ndarray:
    path = RAW_ROOT / "labelsTr" / f"{case_id}.nii.gz"
    return sitk.GetArrayFromImage(sitk.ReadImage(str(path))).astype(np.int16, copy=False)


def read_mask(path: Path) -> np.ndarray:
    return sitk.GetArrayFromImage(sitk.ReadImage(str(path))).astype(np.int16, copy=False)


def load_split(fold: int) -> tuple[list[str], list[str]]:
    data = json.loads(SPLIT_JSON.read_text(encoding="utf-8"))
    split = data["folds"][fold]
    return list(split["train"]), list(split["val"])


def case_to_validation_fold() -> dict[str, int]:
    data = json.loads(SPLIT_JSON.read_text(encoding="utf-8"))
    out: dict[str, int] = {}
    for split in data["folds"]:
        fold = int(split["fold"])
        for case_id in split["val"]:
            out[str(case_id)] = fold
    return out


def teacher_dir_for_case(case_id: str, split_name: str, fold: int, val_fold_map: dict[str, int], mode: str) -> tuple[Path, int, str]:
    if mode == "fold0-validation-only":
        return NNUNET_BASE_ROOT / f"fold_{fold}" / "validation", fold, "nnunet_fold0_validation_teacher"
    if mode == "oof5":
        source_fold = val_fold_map[case_id]
        source = "nnunet_fold0_validation_teacher" if source_fold == fold else "nnunet_oof5_validation_teacher"
        return NNUNET_BASE_ROOT / f"fold_{source_fold}" / "validation", source_fold, source
    raise ValueError(f"unsupported teacher mode: {mode}")


def bbox_from_mask(mask: np.ndarray, margin_zyx: tuple[int, int, int]) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], int]:
    coords = np.argwhere(mask)
    if coords.size == 0:
        shape = tuple(int(x) for x in mask.shape)
        return (0, 0, 0), shape, shape, int(mask.size)
    starts = coords.min(axis=0)
    ends = coords.max(axis=0) + 1
    margin = np.asarray(margin_zyx, dtype=np.int64)
    starts = np.maximum(0, starts - margin)
    ends = np.minimum(np.asarray(mask.shape, dtype=np.int64), ends + margin)
    shape = ends - starts
    volume = int(np.prod(shape))
    return tuple(int(x) for x in starts), tuple(int(x) for x in ends), tuple(int(x) for x in shape), volume


def fraction_covered(target: np.ndarray, roi_mask: np.ndarray) -> float | None:
    denom = int(target.sum())
    if denom == 0:
        return None
    return float((target & roi_mask).sum() / denom)


def dice(pred: np.ndarray, target: np.ndarray) -> float | None:
    denom = int(pred.sum() + target.sum())
    if denom == 0:
        return None
    return float(2.0 * int((pred & target).sum()) / denom)


def make_roi_mask(base_mask: np.ndarray, shape: tuple[int, ...], dilation_iter: int = 4) -> np.ndarray:
    if not bool(base_mask.any()):
        return np.ones(shape, dtype=bool)
    structure = generate_binary_structure(rank=base_mask.ndim, connectivity=1)
    return binary_dilation(base_mask, structure=structure, iterations=dilation_iter)


def summarize_case(
    case_id: str,
    split_name: str,
    metadata: dict[str, Any],
    *,
    fold: int,
    val_fold_map: dict[str, int],
    teacher_mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    label = read_label(case_id)
    label_path = RAW_ROOT / "labelsTr" / f"{case_id}.nii.gz"
    teacher_dir, teacher_source_fold, teacher_source_name = teacher_dir_for_case(case_id, split_name, fold, val_fold_map, teacher_mode)
    teacher_mask_path = teacher_dir / f"{case_id}.nii.gz"
    teacher_softmax_path = teacher_dir / f"{case_id}.npz"
    has_teacher = teacher_mask_path.is_file()
    teacher = read_mask(teacher_mask_path) if has_teacher else None
    meta = metadata[case_id]
    anatomy_gt = label > 0
    pathology_gt = np.isin(label, [4, 5])
    if has_teacher:
        prior_source = teacher_source_name
        roi_base = teacher > 0
    else:
        prior_source = "missing_teacher_prediction"
        roi_base = anatomy_gt
    roi_mask = make_roi_mask(roi_base, label.shape)
    starts, ends, box_shape, roi_voxels = bbox_from_mask(roi_mask, ROI_MARGIN_ZYX)
    case_row = {
        "case_id": case_id,
        "split": split_name,
        "center": meta.center,
        "modality_group": meta.modality_group,
        "lge_present": bool(meta.lge_present),
        "t2_present": bool(meta.t2_present),
        "c0_present": bool(meta.c0_present),
        "label_path": str(label_path),
        "teacher_mask_path": str(teacher_mask_path) if has_teacher else "",
        "teacher_softmax_path": str(teacher_softmax_path) if teacher_softmax_path.is_file() else "",
        "has_teacher_prediction": has_teacher,
        "has_teacher_softmax": teacher_softmax_path.is_file(),
        "teacher_source_fold": teacher_source_fold if has_teacher else "",
        "prior_source": prior_source,
        "shape_zyx": "x".join(str(int(v)) for v in label.shape),
        "roi_starts_zyx": "x".join(str(v) for v in starts),
        "roi_ends_zyx": "x".join(str(v) for v in ends),
        "roi_shape_zyx": "x".join(str(v) for v in box_shape),
        "roi_voxels": roi_voxels,
        "roi_volume_ratio": float(roi_voxels / label.size),
        "anatomy_gt_voxels": int(anatomy_gt.sum()),
        "pathology_gt_voxels": int(pathology_gt.sum()),
        "anatomy_roi_coverage": fraction_covered(anatomy_gt, roi_mask),
        "pathology_roi_coverage": fraction_covered(pathology_gt, roi_mask),
    }
    class_rows: list[dict[str, Any]] = []
    for class_id, name in CLASS_NAMES.items():
        target = label == class_id
        pred = teacher == class_id if teacher is not None else None
        class_rows.append(
            {
                "case_id": case_id,
                "split": split_name,
                "class_id": class_id,
                "class_name": name,
                "prior_source": prior_source,
                "gt_voxels": int(target.sum()),
                "teacher_voxels": int(pred.sum()) if pred is not None else "",
                "roi_coverage": fraction_covered(target, roi_mask),
                "teacher_dice_vs_label": dice(pred, target) if pred is not None else "",
            }
        )
    return case_row, class_rows


def build_cache(out_dir: Path, fold: int, teacher_mode: str) -> dict[str, Any]:
    train_ids, val_ids = load_split(fold)
    val_fold_map = case_to_validation_fold()
    metadata = load_myops_case_metadata(REPO_ROOT)
    case_rows: list[dict[str, Any]] = []
    roi_rows: list[dict[str, Any]] = []
    for split_name, case_ids in [("train", train_ids), ("val", val_ids)]:
        for case_id in case_ids:
            case_row, class_rows = summarize_case(
                case_id,
                split_name,
                metadata,
                fold=fold,
                val_fold_map=val_fold_map,
                teacher_mode=teacher_mode,
            )
            case_rows.append(case_row)
            roi_rows.extend(class_rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "case_index.csv", case_rows)
    write_csv(out_dir / "roi_coverage.csv", roi_rows)
    train_teacher = sum(1 for row in case_rows if row["split"] == "train" and row["has_teacher_prediction"])
    val_teacher = sum(1 for row in case_rows if row["split"] == "val" and row["has_teacher_prediction"])
    low_roi = [
        row
        for row in roi_rows
        if row["roi_coverage"] not in ("", None) and float(row["roi_coverage"]) < 0.95 and int(row["gt_voxels"]) > 0
    ]
    summary = {
        "fold": fold,
        "train_cases": len(train_ids),
        "val_cases": len(val_ids),
        "train_teacher_predictions": train_teacher,
        "val_teacher_predictions": val_teacher,
        "teacher_mode": teacher_mode,
        "train_prior_source": "nnunet_oof5_validation_teacher" if teacher_mode == "oof5" else "missing_oracle_fallback",
        "val_prior_source": "nnunet_fold0_validation_teacher",
        "low_gt_roi_coverage_rows_lt_0_95": len(low_roi),
        "case_index": str(out_dir / "case_index.csv"),
        "roi_coverage": str(out_dir / "roi_coverage.csv"),
        "nnunet_validation_dir": str(NNUNET_VAL_DIR),
        "nnunet_base_root": str(NNUNET_BASE_ROOT),
        "raw_root": str(RAW_ROOT),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_contract(out_dir, summary)
    return summary


def write_contract(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Cascade Teacher Cache Preflight",
        "",
        "Task: `prompts/tasks/20260629_cascade_teacher_route.md`",
        "",
        "## Status",
        "",
        "- This is a task-scoped cache/index preflight, not a formal cascade training result.",
        f"- Fold0 train cases: `{summary['train_cases']}`.",
        f"- Fold0 validation cases: `{summary['val_cases']}`.",
        f"- Train-side nnU-Net teacher predictions available: `{summary['train_teacher_predictions']}/{summary['train_cases']}`.",
        f"- Validation nnU-Net teacher predictions available: `{summary['val_teacher_predictions']}/{summary['val_cases']}`.",
        f"- Teacher mode: `{summary['teacher_mode']}`.",
        "- Train split cache rows use out-of-fold nnU-Net validation predictions when teacher mode is `oof5`.",
        "- Validation split rows use existing `nnunet_fold0_validation_teacher` predictions.",
        "",
        "## Decision",
        "",
        "- Formal teacher/refiner training may use this cache only if train and validation teacher prediction coverage are both complete.",
        "- Cropping logic must retain anatomy fallback/margins because validation teacher-derived ROIs miss some GT-positive scar rows.",
        "",
        "## Artifacts",
        "",
        "- `teacher_cache/case_index.csv`",
        "- `teacher_cache/roi_coverage.csv`",
        "- `teacher_cache/summary.json`",
    ]
    (out_dir / "teacher_cache_contract.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--teacher-mode", choices=["oof5", "fold0-validation-only"], default="oof5")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_cache(args.out_dir, args.fold, args.teacher_mode)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
