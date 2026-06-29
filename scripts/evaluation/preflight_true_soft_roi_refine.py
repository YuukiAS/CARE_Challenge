#!/usr/bin/env python
"""Geometry-only preflight for Result5 true soft-ROI refinement."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training import run_srr_myops_fold0 as runner
from src.care_myocardium.refiner.soft_roi import build_candidate_mask, box_from_mask, extract_roi, restore_roi


DEFAULT_VARIANT_DIR = REPO_ROOT / "results/20260628_myops_proposal/variants/proposal_pos_neg_basic"
DEFAULT_OUT_DIR = REPO_ROOT / "results/20260629_true_soft_roi_refine"
CLASS_CONFIG = {
    4: {"metric_name": "myops_edema", "proposal_dilation": 10, "margin": (2, 16, 16)},
    5: {"metric_name": "myops_scar", "proposal_dilation": 6, "margin": (1, 10, 10)},
}


def read_prediction(path: Path) -> np.ndarray:
    return sitk.GetArrayFromImage(sitk.ReadImage(str(path))).astype(np.int16)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fraction_covered(target: np.ndarray, roi_mask: np.ndarray) -> float | None:
    denom = int(target.sum())
    if denom == 0:
        return None
    return float((target & roi_mask).sum() / denom)


def preflight(variant_dir: Path) -> list[dict[str, Any]]:
    pred_dir = variant_dir / "predictions/fold_0/checkpoint_best"
    if not pred_dir.is_dir():
        raise FileNotFoundError(f"Missing prediction directory: {pred_dir}")
    _, val_ids = runner.load_split(0)
    metadata = runner.load_myops_case_metadata()
    rows: list[dict[str, Any]] = []
    for case_id in val_ids:
        pred_path = pred_dir / f"{case_id}.nii.gz"
        if not pred_path.is_file():
            continue
        case = runner.read_case(case_id, metadata)
        pred = read_prediction(pred_path)
        labels = case.label_arr.astype(np.int16)
        anatomy = labels > 0
        full_volume = int(np.prod(labels.shape))
        for class_id, cfg in CLASS_CONFIG.items():
            proposal = pred == class_id
            gt = labels == class_id
            candidate, source = build_candidate_mask(
                proposal,
                anatomy,
                proposal_dilation=int(cfg["proposal_dilation"]),
                anatomy_dilation=2,
            )
            box = box_from_mask(candidate, margin=cfg["margin"])
            roi_mask = np.zeros_like(candidate, dtype=bool)
            roi_mask[box.slices()] = True
            crop = extract_roi(pred == class_id, box)
            restored = restore_roi(crop, box, fill_value=False)
            restoration_valid = bool(np.array_equal(restored[box.slices()], proposal[box.slices()]) and not bool(restored[~roi_mask].any()))
            rows.append(
                {
                    "variant": variant_dir.name,
                    "checkpoint": "checkpoint_best",
                    "case_id": case_id,
                    "center": case.metadata.center,
                    "modality_group": case.metadata.modality_group,
                    "t2_present": bool(case.metadata.t2_present),
                    "class_id": class_id,
                    "metric_name": cfg["metric_name"],
                    "roi_source": source,
                    "proposal_voxels": int(proposal.sum()),
                    "gt_voxels": int(gt.sum()),
                    "roi_voxels": box.volume,
                    "roi_volume_ratio": float(box.volume / full_volume),
                    "gt_coverage": fraction_covered(gt, roi_mask),
                    "proposal_coverage": fraction_covered(proposal, roi_mask),
                    "box_starts_zyx": "x".join(str(v) for v in box.starts),
                    "box_ends_zyx": "x".join(str(v) for v in box.ends),
                    "box_shape_zyx": "x".join(str(v) for v in box.shape),
                    "empty_proposal": not bool(proposal.any()),
                    "restoration_valid": restoration_valid,
                }
            )
    return rows


def write_docs(out_dir: Path, rows: list[dict[str, Any]]) -> None:
    invalid = [r for r in rows if not bool(r["restoration_valid"])]
    covered = [r for r in rows if r["gt_coverage"] is not None]
    low_coverage = [r for r in covered if float(r["gt_coverage"]) < 0.95]
    selection = "REFINE_RESTORE_BUG" if invalid else "REFINE_WAITING_FOR_PROPOSAL_SELECTION"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "selection.md").write_text(
        "\n".join(
            [
                "# True Soft-ROI Refinement Selection",
                "",
                f"status: `{selection}`",
                "",
                "## Summary",
                f"- ROI rows: `{len(rows)}`",
                f"- restoration invalid rows: `{len(invalid)}`",
                f"- GT-positive rows with ROI coverage < 0.95: `{len(low_coverage)}`",
                "- formal refinement was not launched because proposal selection is not `SELECT_PROPOSAL_ROUTE`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "result.md").write_text(
        "\n".join(
            [
                "# Result 20260629 True Soft-ROI Refine",
                "",
                f"- selection: `{selection}`",
                "- source variant: `proposal_pos_neg_basic/checkpoint_best`",
                "- action: geometry-only ROI extract/restore preflight.",
                "- formal refinement: not launched; waiting for `results/20260628_myops_proposal/selection.md` to reach `SELECT_PROPOSAL_ROUTE`.",
                "",
                "## Findings",
                "",
                f"- restoration invalid rows: `{len(invalid)}`",
                f"- GT-positive low-coverage rows (<0.95): `{len(low_coverage)}`",
                "- ROI construction uses proposal dilation plus anatomy context and never hard-deletes evidence for training selection.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "MANIFEST.md").write_text(
        "\n".join(
            [
                "# MANIFEST",
                "",
                "- Task: `prompts/tasks/20260629_true_soft_roi_refine.md`",
                "- Result: `results/20260629_true_soft_roi_refine/result.md`",
                "- Selection: `results/20260629_true_soft_roi_refine/selection.md`",
                "- ROI sanity: `results/20260629_true_soft_roi_refine/roi_sanity.csv`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant-dir", type=Path, default=DEFAULT_VARIANT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = preflight(args.variant_dir)
    write_csv(args.out_dir / "roi_sanity.csv", rows)
    write_docs(args.out_dir, rows)
    invalid = sum(1 for row in rows if not bool(row["restoration_valid"]))
    print({"roi_rows": len(rows), "restoration_invalid": invalid})
    return 0 if invalid == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
