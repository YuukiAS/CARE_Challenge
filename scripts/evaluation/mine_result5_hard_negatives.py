#!/usr/bin/env python
"""Mine hard-negative components from completed Result5 proposal predictions."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training import run_srr_myops_fold0 as runner


DEFAULT_VARIANT_DIR = REPO_ROOT / "results/20260628_myops_proposal/variants/proposal_pos_neg_basic"
DEFAULT_OUT_DIR = REPO_ROOT / "results/20260629_proposal_memory_hardneg"
PATHOLOGY_CLASSES = {4: "myops_edema", 5: "myops_scar"}


def read_prediction(path: Path) -> np.ndarray:
    return sitk.GetArrayFromImage(sitk.ReadImage(str(path))).astype(np.int16)


def finite_min_distance(mask: np.ndarray, target: np.ndarray) -> float:
    if not bool(mask.any()):
        return math.nan
    if not bool(target.any()):
        return math.inf
    distance = ndimage.distance_transform_edt(~target.astype(bool))
    return float(distance[mask].min())


def component_bbox(mask: np.ndarray) -> tuple[str, str]:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return "", ""
    lo = coords.min(axis=0)
    hi = coords.max(axis=0)
    return "x".join(str(int(v)) for v in lo), "x".join(str(int(v)) for v in hi)


def component_center(mask: np.ndarray) -> str:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return ""
    center = coords.mean(axis=0)
    return "x".join(f"{float(v):.2f}" for v in center)


def edema_safety_type(t2_present: bool, dist_gt: float, dist_anatomy: float) -> tuple[str, bool]:
    if t2_present:
        if dist_gt >= 3.0 and dist_anatomy <= 2.0:
            return "edema_t2_far_from_gt_anatomy_negative", True
        if dist_gt >= 3.0 and dist_anatomy > 2.0:
            return "edema_t2_remote_fp_safe", True
        return "edema_t2_near_gt_unsafe", False
    if dist_anatomy > 2.0:
        return "edema_no_t2_true_background_safe", True
    return "edema_no_t2_unsafe_anatomy_or_scar", False


def scar_safety_type(overlap_labels: set[int], dist_gt: float, dist_anatomy: float) -> tuple[str, bool]:
    if dist_gt < 3.0:
        return "scar_near_gt_unsafe", False
    if 2 in overlap_labels or 3 in overlap_labels:
        return "scar_blood_pool_negative", True
    if 1 in overlap_labels or 4 in overlap_labels:
        return "scar_myocardium_or_edema_negative", True
    if dist_anatomy > 2.0:
        return "scar_remote_fp_safe", True
    return "scar_anatomy_adjacent_negative", True


def mine_components(variant_dir: Path) -> list[dict[str, Any]]:
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
        anatomy_union = labels > 0

        for class_id, metric_name in PATHOLOGY_CLASSES.items():
            pred_mask = pred == class_id
            gt_mask = labels == class_id
            fp_mask = pred_mask & ~gt_mask
            labeled, count = ndimage.label(fp_mask)
            if count == 0:
                continue
            gt_distance = ndimage.distance_transform_edt(~gt_mask.astype(bool)) if bool(gt_mask.any()) else None
            anatomy_distance = ndimage.distance_transform_edt(~anatomy_union.astype(bool)) if bool(anatomy_union.any()) else None
            for component_id in range(1, count + 1):
                comp = labeled == component_id
                size = int(comp.sum())
                if size == 0:
                    continue
                overlap_labels = {int(v) for v in np.unique(labels[comp]) if int(v) != 0}
                dist_gt = math.inf if gt_distance is None else float(gt_distance[comp].min())
                dist_anatomy = math.inf if anatomy_distance is None else float(anatomy_distance[comp].min())
                if class_id == 4:
                    safety_type, replay_safe = edema_safety_type(bool(case.metadata.t2_present), dist_gt, dist_anatomy)
                else:
                    safety_type, replay_safe = scar_safety_type(overlap_labels, dist_gt, dist_anatomy)
                bbox_min, bbox_max = component_bbox(comp)
                rows.append(
                    {
                        "variant": variant_dir.name,
                        "checkpoint": "checkpoint_best",
                        "case_id": case_id,
                        "center": case.metadata.center,
                        "modality_group": case.metadata.modality_group,
                        "t2_present": bool(case.metadata.t2_present),
                        "class_id": class_id,
                        "metric_name": metric_name,
                        "component_id": component_id,
                        "component_size_voxels": size,
                        "distance_to_gt_voxels": dist_gt,
                        "distance_to_anatomy_union_voxels": dist_anatomy,
                        "overlap_label_values": "|".join(str(v) for v in sorted(overlap_labels)),
                        "component_center_zyx": component_center(comp),
                        "bbox_min_zyx": bbox_min,
                        "bbox_max_zyx": bbox_max,
                        "safety_type": safety_type,
                        "replay_safe": replay_safe,
                    }
                )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_memory_usage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str, bool], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["class_id"]), str(row["safety_type"]), bool(row["replay_safe"]))].append(row)
    out: list[dict[str, Any]] = []
    for (class_id, safety_type, replay_safe), items in sorted(grouped.items()):
        sizes = [int(r["component_size_voxels"]) for r in items]
        out.append(
            {
                "class_id": class_id,
                "metric_name": PATHOLOGY_CLASSES[class_id],
                "safety_type": safety_type,
                "replay_safe": replay_safe,
                "component_count": len(items),
                "total_voxels": int(sum(sizes)),
                "median_component_size": float(np.median(sizes)) if sizes else math.nan,
                "max_component_size": int(max(sizes)) if sizes else 0,
                "memory_role": "hard_negative_replay" if replay_safe else "audit_only_excluded",
            }
        )
    return out


def write_docs(out_dir: Path, rows: list[dict[str, Any]], memory_rows: list[dict[str, Any]]) -> None:
    safe_counts = Counter((int(r["class_id"]), bool(r["replay_safe"])) for r in rows)
    safety_counts = Counter(str(r["safety_type"]) for r in rows)
    selection = "HARDNEG_PREFLIGHT_ONLY" if rows else "HARDNEG_BLOCKED_WAITING_FOR_PROPOSAL_JOBS"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "selection.md").write_text(
        "\n".join(
            [
                "# Proposal Memory Hard-Negative Selection",
                "",
                f"status: `{selection}`",
                "",
                "## Summary",
                f"- mined components: `{len(rows)}`",
                f"- scar replay-safe components: `{safe_counts[(5, True)]}`",
                f"- edema replay-safe components: `{safe_counts[(4, True)]}`",
                "- no formal hard-negative replay training was launched; current proposal formal jobs are still running.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    top_safety = "\n".join(f"- `{k}`: `{v}`" for k, v in safety_counts.most_common(12))
    (out_dir / "result.md").write_text(
        "\n".join(
            [
                "# Result 20260629 Proposal Memory HardNeg",
                "",
                "- selection: `HARDNEG_PREFLIGHT_ONLY`",
                "- source variant: `proposal_pos_neg_basic/checkpoint_best`",
                "- action: mined false-positive connected components from completed local predictions.",
                "- formal replay training: not launched, because `proposal_anatomy_distance` and `proposal_uncertainty_gate` are still running.",
                "",
                "## Safety Counts",
                "",
                top_safety or "- none",
                "",
                "## Edema Safety Rule",
                "",
                "No-T2 myocardium or scar components are excluded from edema replay. Only no-T2 true-background components and T2-present far-from-GT components are marked replay-safe.",
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
                "- Task: `prompts/tasks/20260629_proposal_memory_hardneg.md`",
                "- Result: `results/20260629_proposal_memory_hardneg/result.md`",
                "- Selection: `results/20260629_proposal_memory_hardneg/selection.md`",
                "- Mined components: `results/20260629_proposal_memory_hardneg/mined_components.csv`",
                "- Memory usage draft: `results/20260629_proposal_memory_hardneg/memory_usage.csv`",
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
    rows = mine_components(args.variant_dir)
    memory_rows = build_memory_usage(rows)
    write_csv(args.out_dir / "mined_components.csv", rows)
    write_csv(args.out_dir / "memory_usage.csv", memory_rows)
    write_docs(args.out_dir, rows, memory_rows)
    print({"mined_components": len(rows), "memory_rows": len(memory_rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
