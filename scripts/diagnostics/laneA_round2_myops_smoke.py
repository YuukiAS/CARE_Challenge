#!/usr/bin/env python3
"""Lane A Round2 edema-focused smoke diagnostics.

This script is diagnostic-only. It reads existing nnUNet501 fold0 predictions
and Dataset501 GT, then writes Round2 edema topology/T2-routing reports. It
does not train, infer, submit jobs, package validation outputs, or modify model
artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import distance_transform_edt, generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class, hd_class


EDEMA = 4
SCAR = 5
ANATOMY_LABELS = {1, 2, 3, 5}


@dataclass(frozen=True)
class CaseMeta:
    case_id: str
    center: str
    modality_group: str
    t2_present: bool


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        if math.isinf(value):
            return "inf"
        return f"{value:.4f}"
    return str(value)


def finite(values: Iterable[object]) -> list[float]:
    out = []
    for value in values:
        if isinstance(value, (int, float)):
            value = float(value)
            if not math.isnan(value) and not math.isinf(value):
                out.append(value)
    return out


def avg(values: Iterable[object]) -> float | None:
    vals = finite(values)
    return float(mean(vals)) if vals else None


def sum_int(values: Iterable[object]) -> int:
    return int(sum(int(v) for v in values if v is not None))


def load_case_meta(cases_json: Path, raw_root: Path) -> dict[str, CaseMeta]:
    cases = read_json(cases_json)["cases"]
    meta: dict[str, CaseMeta] = {}
    for item in cases:
        cid = item["case_id"]
        center = item["center"]
        case_dir = raw_root / center / cid
        has_lge = (case_dir / f"{cid}_LGE.nii.gz").is_file()
        has_c0 = (case_dir / f"{cid}_C0.nii.gz").is_file()
        has_t2 = (case_dir / f"{cid}_T2.nii.gz").is_file()
        if has_c0 and has_lge and has_t2:
            group = "C0+LGE+T2"
        elif has_c0 and has_lge:
            group = "C0+LGE"
        elif has_lge:
            group = "LGE-only"
        else:
            group = "unknown"
        meta[cid] = CaseMeta(cid, center, group, has_t2)
    return meta


def load_split_cases(split_json: Path, fold: int) -> tuple[list[str], list[str]]:
    data = read_json(split_json)
    folds = data["folds"]
    if fold < 0 or fold >= len(folds):
        raise ValueError(f"fold {fold} out of range [0, {len(folds)})")
    return list(folds[fold]["train"]), list(folds[fold]["val"])


def read_label(path: Path) -> tuple[sitk.Image, np.ndarray]:
    image = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(image).astype(np.uint8, copy=False)
    return image, arr


def resample_pred_to_gt(pred_path: Path, gt_img: sitk.Image) -> np.ndarray:
    pred_img = sitk.ReadImage(str(pred_path))
    if (
        pred_img.GetSize() != gt_img.GetSize()
        or pred_img.GetSpacing() != gt_img.GetSpacing()
        or pred_img.GetOrigin() != gt_img.GetOrigin()
        or pred_img.GetDirection() != gt_img.GetDirection()
    ):
        pred_img = sitk.Resample(
            pred_img,
            gt_img,
            sitk.Transform(),
            sitk.sitkNearestNeighbor,
            0,
            pred_img.GetPixelID(),
        )
    return sitk.GetArrayFromImage(pred_img).astype(np.uint8, copy=False)


def connected_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    return label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))


def component_sizes(mask: np.ndarray) -> list[int]:
    cc, n_cc = connected_components(mask)
    return [int((cc == idx).sum()) for idx in range(1, n_cc + 1)]


def class_metrics(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> dict[str, float | None]:
    return {
        "dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
        "hd": hd_class(pred, gt, class_id, spacing_zyx),
        "hd95": hd95_class(pred, gt, class_id, spacing_zyx),
    }


def volume_ratio(pred_mask: np.ndarray, gt_mask: np.ndarray) -> float | None:
    pred_voxels = int(pred_mask.sum())
    gt_voxels = int(gt_mask.sum())
    if gt_voxels == 0:
        return None if pred_voxels == 0 else float("inf")
    return float(pred_voxels / gt_voxels)


def infer_train_thresholds(
    train_cases: list[str],
    gt_dir: Path,
    *,
    component_quantile: float,
    distance_quantile: float,
) -> dict[str, float | int | str]:
    edema_component_sizes: list[int] = []
    edema_to_anatomy_distances: list[float] = []

    for cid in train_cases:
        gt_path = gt_dir / f"{cid}.nii.gz"
        if not gt_path.is_file():
            continue
        gt_img, gt = read_label(gt_path)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        edema = gt == EDEMA
        if not edema.any():
            continue
        edema_component_sizes.extend(component_sizes(edema))

        anatomy = np.isin(gt, list(ANATOMY_LABELS))
        if anatomy.any():
            dt = distance_transform_edt(~anatomy, sampling=spacing)
            edema_to_anatomy_distances.extend([float(x) for x in dt[edema].ravel()])

    if edema_component_sizes:
        small_threshold = int(max(1, math.floor(np.percentile(edema_component_sizes, component_quantile))))
        component_source = f"fold_train_gt_edema_component_p{component_quantile:g}"
    else:
        small_threshold = 1
        component_source = "fallback_no_train_edema_components"

    if edema_to_anatomy_distances:
        roi_radius_mm = float(np.percentile(edema_to_anatomy_distances, distance_quantile))
        radius_source = f"fold_train_gt_edema_to_anatomy_distance_p{distance_quantile:g}"
    else:
        roi_radius_mm = 0.0
        radius_source = "fallback_no_train_edema_to_anatomy_distances"

    return {
        "small_component_threshold_voxels": small_threshold,
        "small_component_threshold_source": component_source,
        "roi_radius_mm": roi_radius_mm,
        "roi_radius_source": radius_source,
        "train_edema_component_count": len(edema_component_sizes),
        "train_edema_to_anatomy_distance_count": len(edema_to_anatomy_distances),
    }


def component_diagnostics(
    pred_edema: np.ndarray,
    gt_edema: np.ndarray,
    gt_anatomy: np.ndarray,
    spacing_zyx: tuple[float, ...],
    *,
    small_threshold: int,
    roi_radius_mm: float,
) -> dict[str, int | float | None]:
    cc, n_cc = connected_components(pred_edema)
    dt_gt_anatomy = distance_transform_edt(~gt_anatomy, sampling=spacing_zyx) if gt_anatomy.any() else None
    small_components = 0
    small_fp = 0
    remote_components = 0
    remote_fp = 0
    gt_overlap_components = 0
    largest = 0

    for idx in range(1, n_cc + 1):
        comp = cc == idx
        voxels = int(comp.sum())
        largest = max(largest, voxels)
        overlaps_gt = bool(np.logical_and(comp, gt_edema).any())
        if overlaps_gt:
            gt_overlap_components += 1
        if voxels <= small_threshold:
            small_components += 1
            if not overlaps_gt:
                small_fp += 1
        if dt_gt_anatomy is None:
            min_dist = float("inf")
        else:
            min_dist = float(dt_gt_anatomy[comp].min()) if comp.any() else float("inf")
        if min_dist > roi_radius_mm:
            remote_components += 1
            if not overlaps_gt:
                remote_fp += 1

    return {
        "edema_components": n_cc,
        "edema_small_components": small_components,
        "edema_small_fp": small_fp,
        "edema_remote_components": remote_components,
        "edema_remote_fp": remote_fp,
        "edema_gt_overlap_components": gt_overlap_components,
        "edema_largest_component_voxels": largest,
        "edema_pred_voxels": int(pred_edema.sum()),
        "edema_gt_voxels": int(gt_edema.sum()),
        "edema_pred_gt_volume_ratio": volume_ratio(pred_edema, gt_edema),
    }


def apply_edema_component_roi_guard(
    pred: np.ndarray,
    gt: np.ndarray,
    spacing_zyx: tuple[float, ...],
    *,
    case_id: str,
    small_threshold: int,
    roi_radius_mm: float,
) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = pred.copy()
    edema = pred == EDEMA
    if not edema.any():
        return out, []

    pred_anatomy = np.isin(pred, list(ANATOMY_LABELS))
    dt_pred_anatomy = distance_transform_edt(~pred_anatomy, sampling=spacing_zyx) if pred_anatomy.any() else None
    gt_edema = gt == EDEMA
    cc, n_cc = connected_components(edema)
    remove_mask = np.zeros_like(edema, dtype=bool)
    actions: list[dict[str, object]] = []

    for idx in range(1, n_cc + 1):
        comp = cc == idx
        voxels = int(comp.sum())
        gt_overlap = int(np.logical_and(comp, gt_edema).sum())
        if dt_pred_anatomy is None:
            min_dist = float("inf")
            overlaps_roi = False
        else:
            min_dist = float(dt_pred_anatomy[comp].min()) if comp.any() else float("inf")
            overlaps_roi = min_dist <= roi_radius_mm
        is_small = voxels <= small_threshold
        outside_roi = not overlaps_roi
        remove = is_small or outside_roi
        reasons = []
        if is_small:
            reasons.append("small_component")
        if outside_roi:
            reasons.append("outside_soft_anatomy_roi")
        if remove:
            remove_mask |= comp
        actions.append(
            {
                "case_id": case_id,
                "component_id": idx,
                "voxels": voxels,
                "gt_overlap_voxels": gt_overlap,
                "gt_positive_case": bool(gt_edema.any()),
                "small_threshold_voxels": small_threshold,
                "roi_radius_mm": roi_radius_mm,
                "min_distance_to_pred_anatomy_mm": min_dist,
                "overlaps_soft_roi": overlaps_roi,
                "small_by_threshold": is_small,
                "outside_soft_roi": outside_roi,
                "removed": remove,
                "action_reason": "+".join(reasons) if reasons else "kept",
            }
        )

    if remove_mask.any():
        proposed = edema & ~remove_mask
        if not proposed.any():
            for action in actions:
                if action["removed"]:
                    action["removed"] = False
                    action["action_reason"] = "fallback_keep_original_would_delete_all_edema"
            return out, actions
        out[remove_mask] = 0
    return out, actions


def summarize_group(rows: list[dict[str, object]], prefix: str) -> dict[str, object]:
    return {
        f"{prefix}_n_cases": len(rows),
        f"{prefix}_gt_positive_n": sum(1 for r in rows if r["edema_gt_positive"]),
        f"{prefix}_empty_gt_n": sum(1 for r in rows if not r["edema_gt_positive"]),
        f"{prefix}_dice": avg(r[f"{prefix}_dice"] for r in rows),
        f"{prefix}_hd": avg(r[f"{prefix}_hd"] for r in rows),
        f"{prefix}_hd95": avg(r[f"{prefix}_hd95"] for r in rows),
        f"{prefix}_components": avg(r[f"{prefix}_components"] for r in rows),
        f"{prefix}_small_fp": sum_int(r[f"{prefix}_small_fp"] for r in rows),
        f"{prefix}_remote_fp": sum_int(r[f"{prefix}_remote_fp"] for r in rows),
        f"{prefix}_volume_ratio": avg(r[f"{prefix}_volume_ratio"] for r in rows),
    }


def aggregate_before_after(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: list[tuple[str, str, list[dict[str, object]]]] = [
        ("all", "all", rows),
        ("gt_status", "gt_positive", [r for r in rows if r["edema_gt_positive"]]),
        ("gt_status", "empty_gt", [r for r in rows if not r["edema_gt_positive"]]),
        ("t2_status", "t2_present", [r for r in rows if r["t2_present"]]),
        ("t2_status", "no_t2", [r for r in rows if not r["t2_present"]]),
        ("modality_group", "C0+LGE+T2", [r for r in rows if r["modality_group"] == "C0+LGE+T2"]),
        ("modality_group", "C0+LGE", [r for r in rows if r["modality_group"] == "C0+LGE"]),
        ("modality_group", "LGE-only", [r for r in rows if r["modality_group"] == "LGE-only"]),
    ]
    for center in sorted({str(r["center"]) for r in rows}):
        groups.append(("center", center, [r for r in rows if r["center"] == center]))

    out = []
    for group_type, group_value, items in groups:
        if not items:
            continue
        before = summarize_group(items, "before")
        after = summarize_group(items, "after")
        out.append(
            {
                "group_type": group_type,
                "group_value": group_value,
                "n_cases": len(items),
                "gt_positive_n": before["before_gt_positive_n"],
                "empty_gt_n": before["before_empty_gt_n"],
                "before_dice": before["before_dice"],
                "after_dice": after["after_dice"],
                "delta_dice": None
                if before["before_dice"] is None or after["after_dice"] is None
                else float(after["after_dice"] - before["before_dice"]),
                "before_hd95": before["before_hd95"],
                "after_hd95": after["after_hd95"],
                "delta_hd95": None
                if before["before_hd95"] is None or after["after_hd95"] is None
                else float(after["after_hd95"] - before["before_hd95"]),
                "before_components": before["before_components"],
                "after_components": after["after_components"],
                "delta_components": None
                if before["before_components"] is None or after["after_components"] is None
                else float(after["after_components"] - before["before_components"]),
                "before_remote_fp": before["before_remote_fp"],
                "after_remote_fp": after["after_remote_fp"],
                "delta_remote_fp": int(after["after_remote_fp"] - before["before_remote_fp"]),
                "before_small_fp": before["before_small_fp"],
                "after_small_fp": after["after_small_fp"],
                "delta_small_fp": int(after["after_small_fp"] - before["before_small_fp"]),
                "before_volume_ratio": before["before_volume_ratio"],
                "after_volume_ratio": after["after_volume_ratio"],
            }
        )
    return out


def write_before_after_md(path: Path, aggregate_rows: list[dict[str, object]], params: dict[str, object]) -> None:
    all_row = next(r for r in aggregate_rows if r["group_type"] == "all")
    gt_row = next((r for r in aggregate_rows if r["group_type"] == "gt_status" and r["group_value"] == "gt_positive"), None)
    empty_row = next((r for r in aggregate_rows if r["group_type"] == "gt_status" and r["group_value"] == "empty_gt"), None)
    gate = "watch"
    reasons = []
    if gt_row is not None:
        if gt_row["delta_hd95"] is not None and gt_row["delta_hd95"] < 0:
            reasons.append("GT-positive edema HD95 improved")
        elif gt_row["delta_hd95"] is not None:
            reasons.append("GT-positive edema HD95 did not improve")
            gate = "fail"
        if gt_row["delta_dice"] is not None and gt_row["delta_dice"] < -0.01:
            reasons.append("GT-positive edema Dice dropped >1 point")
            gate = "fail"
        if gt_row["delta_components"] is not None and gt_row["delta_components"] < 0 and gate == "fail":
            reasons.append("component count decreased but not enough to pass HD95/Dice gate")
    if empty_row is not None and empty_row["delta_components"] not in (None, 0):
        reasons.append("empty-GT changes are diagnostic only")
    if not reasons:
        reasons.append("no clear actionable before/after signal")

    lines = [
        "# Lane A Round2 Edema Component/ROI Postprocess Smoke",
        "",
        f"- Output type: diagnostic in-memory before/after; no predictions were written.",
        f"- Small-component threshold: `{params['small_component_threshold_voxels']}` voxels from `{params['small_component_threshold_source']}`.",
        f"- Soft anatomy ROI radius: `{fmt(params['roi_radius_mm'])}` mm from `{params['roi_radius_source']}`.",
        f"- Gate: `{gate}`; reason: {'; '.join(reasons)}.",
        "",
        "| group_type | group | n | GT+ | empty GT | Dice before | Dice after | delta Dice | HD95 before | HD95 after | delta HD95 | comps before | comps after | remote FP before | remote FP after | small FP before | small FP after |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in aggregate_rows:
        lines.append(
            "| {group_type} | {group_value} | {n_cases} | {gt_positive_n} | {empty_gt_n} | {before_dice} | {after_dice} | {delta_dice} | {before_hd95} | {after_hd95} | {delta_hd95} | {before_components} | {after_components} | {before_remote_fp} | {after_remote_fp} | {before_small_fp} | {after_small_fp} |".format(
                **{k: fmt(v) for k, v in row.items()}
            )
        )
    lines.extend(
        [
            "",
            "Interpretation rules:",
            "- This smoke is not a deployable postprocess. It tests whether edema HD95/topology failures are component/ROI-sensitive.",
            "- Empty-GT improvements are diagnostic only and cannot justify a model change.",
            "- A candidate fails if GT-positive Dice drops materially, if HD95 improves only through volume collapse, or if scar metrics would be changed. This script leaves class_5 unchanged.",
            "",
            "Headline:",
            f"- All-case edema Dice `{fmt(all_row['before_dice'])}` -> `{fmt(all_row['after_dice'])}`; HD95 `{fmt(all_row['before_hd95'])}` -> `{fmt(all_row['after_hd95'])}`; components `{fmt(all_row['before_components'])}` -> `{fmt(all_row['after_components'])}`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_routing_audit_rows(case_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: list[tuple[str, str, list[dict[str, object]]]] = [
        ("all", "all", case_rows),
        ("t2_status", "t2_present", [r for r in case_rows if r["t2_present"]]),
        ("t2_status", "no_t2", [r for r in case_rows if not r["t2_present"]]),
        ("gt_status", "gt_positive", [r for r in case_rows if r["edema_gt_positive"]]),
        ("gt_status", "empty_gt", [r for r in case_rows if not r["edema_gt_positive"]]),
    ]
    for group in ("C0+LGE+T2", "C0+LGE", "LGE-only"):
        groups.append(("modality_group", group, [r for r in case_rows if r["modality_group"] == group]))
    for center in sorted({str(r["center"]) for r in case_rows}):
        groups.append(("center", center, [r for r in case_rows if r["center"] == center]))

    rows = []
    for group_type, group_value, items in groups:
        if not items:
            continue
        n = len(items)
        gt_pos = sum(1 for r in items if r["edema_gt_positive"])
        no_t2 = sum(1 for r in items if not r["t2_present"])
        if group_type == "t2_status" and group_value == "no_t2":
            recommendation = "future_loss_masking_or_downweighting_only; no hard negative assumption"
        elif group_type == "t2_status" and group_value == "t2_present":
            recommendation = "primary_edema_supervision_subset"
        elif gt_pos == 0:
            recommendation = "empty_gt_diagnostic_only"
        else:
            recommendation = "report_only_then_compare_loss_masking"
        rows.append(
            {
                "group_type": group_type,
                "group_value": group_value,
                "n_cases": n,
                "t2_present_n": sum(1 for r in items if r["t2_present"]),
                "no_t2_n": no_t2,
                "edema_gt_positive_n": gt_pos,
                "edema_empty_gt_n": n - gt_pos,
                "edema_dice": avg(r["before_dice"] for r in items),
                "edema_hd": avg(r["before_hd"] for r in items),
                "edema_hd95": avg(r["before_hd95"] for r in items),
                "edema_components": avg(r["before_components"] for r in items),
                "edema_small_fp": sum_int(r["before_small_fp"] for r in items),
                "edema_remote_fp": sum_int(r["before_remote_fp"] for r in items),
                "edema_pred_gt_volume_ratio": avg(r["before_volume_ratio"] for r in items),
                "strategy_report_only": "current_baseline",
                "strategy_loss_masking": "omit class_4 loss for no-T2 cases; preserve scar/anatomy",
                "strategy_loss_downweighting": "small class_4 no-T2 FP penalty only",
                "recommendation": recommendation,
            }
        )
    return rows


def write_routing_md(path: Path, rows: list[dict[str, object]]) -> None:
    t2 = next((r for r in rows if r["group_type"] == "t2_status" and r["group_value"] == "t2_present"), None)
    no_t2 = next((r for r in rows if r["group_type"] == "t2_status" and r["group_value"] == "no_t2"), None)
    actionable = "watch"
    if t2 and no_t2:
        actionable = "actionable" if int(no_t2["edema_remote_fp"]) > 0 or int(no_t2["edema_small_fp"]) > 0 else "report_only"
    lines = [
        "# Lane A Round2 T2-Aware Edema Routing Audit",
        "",
        f"- Gate: `{actionable}`.",
        "- This is an audit only. It does not train a routing model and does not suppress no-T2 predictions.",
        "- Future trainable strategies are limited to `loss_masking` or `loss_downweighting`; no-T2 cases are not reliable hard negatives by default.",
        "",
        "| group_type | group | n | T2 present | no T2 | edema GT+ | empty GT | Dice | HD | HD95 | comps | small FP | remote FP | volume ratio | recommendation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {group_type} | {group_value} | {n_cases} | {t2_present_n} | {no_t2_n} | {edema_gt_positive_n} | {edema_empty_gt_n} | {edema_dice} | {edema_hd} | {edema_hd95} | {edema_components} | {edema_small_fp} | {edema_remote_fp} | {edema_pred_gt_volume_ratio} | {recommendation} |".format(
                **{k: fmt(v) for k, v in row.items()}
            )
        )
    if t2 and no_t2:
        lines.extend(
            [
                "",
                "Headline:",
                f"- T2-present cases: n={t2['n_cases']}, edema Dice `{fmt(t2['edema_dice'])}`, HD95 `{fmt(t2['edema_hd95'])}`, components `{fmt(t2['edema_components'])}`.",
                f"- No-T2 cases: n={no_t2['n_cases']}, edema GT+ `{no_t2['edema_gt_positive_n']}`, small FP `{no_t2['edema_small_fp']}`, remote FP `{no_t2['edema_remote_fp']}`.",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Path]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    train_cases, val_cases = load_split_cases(args.fold_json, args.fold)
    meta = load_case_meta(args.cases_json, args.raw_root)
    thresholds = infer_train_thresholds(
        train_cases,
        args.gt_dir,
        component_quantile=args.component_quantile,
        distance_quantile=args.distance_quantile,
    )
    small_threshold = int(thresholds["small_component_threshold_voxels"])
    roi_radius_mm = float(thresholds["roi_radius_mm"])

    case_rows: list[dict[str, object]] = []
    action_rows: list[dict[str, object]] = []

    for cid in sorted(val_cases):
        gt_path = args.gt_dir / f"{cid}.nii.gz"
        pred_path = args.pred_dir / f"{cid}.nii.gz"
        if not gt_path.is_file():
            raise FileNotFoundError(f"Missing GT: {gt_path}")
        if not pred_path.is_file():
            raise FileNotFoundError(f"Missing prediction: {pred_path}")
        gt_img, gt = read_label(gt_path)
        pred = resample_pred_to_gt(pred_path, gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])

        after, actions = apply_edema_component_roi_guard(
            pred,
            gt,
            spacing,
            case_id=cid,
            small_threshold=small_threshold,
            roi_radius_mm=roi_radius_mm,
        )
        action_rows.extend(actions)

        gt_edema = gt == EDEMA
        gt_anatomy = np.isin(gt, list(ANATOMY_LABELS))
        before_metrics = class_metrics(pred, gt, EDEMA, spacing)
        after_metrics = class_metrics(after, gt, EDEMA, spacing)
        scar_metrics = class_metrics(pred, gt, SCAR, spacing)
        before_components = component_diagnostics(
            pred == EDEMA,
            gt_edema,
            gt_anatomy,
            spacing,
            small_threshold=small_threshold,
            roi_radius_mm=roi_radius_mm,
        )
        after_components = component_diagnostics(
            after == EDEMA,
            gt_edema,
            gt_anatomy,
            spacing,
            small_threshold=small_threshold,
            roi_radius_mm=roi_radius_mm,
        )
        cm = meta.get(cid, CaseMeta(cid, "unknown", "unknown", False))
        row = {
            "case_id": cid,
            "center": cm.center,
            "modality_group": cm.modality_group,
            "t2_present": cm.t2_present,
            "edema_gt_positive": bool(gt_edema.any()),
            "scar_dice_guardrail": scar_metrics["dice"],
            "scar_hd95_guardrail": scar_metrics["hd95"],
            "before_dice": before_metrics["dice"],
            "after_dice": after_metrics["dice"],
            "delta_dice": None
            if before_metrics["dice"] is None or after_metrics["dice"] is None
            else float(after_metrics["dice"] - before_metrics["dice"]),
            "before_hd": before_metrics["hd"],
            "after_hd": after_metrics["hd"],
            "delta_hd": None
            if before_metrics["hd"] is None or after_metrics["hd"] is None
            else float(after_metrics["hd"] - before_metrics["hd"]),
            "before_hd95": before_metrics["hd95"],
            "after_hd95": after_metrics["hd95"],
            "delta_hd95": None
            if before_metrics["hd95"] is None or after_metrics["hd95"] is None
            else float(after_metrics["hd95"] - before_metrics["hd95"]),
            "before_components": before_components["edema_components"],
            "after_components": after_components["edema_components"],
            "delta_components": int(after_components["edema_components"] - before_components["edema_components"]),
            "before_small_fp": before_components["edema_small_fp"],
            "after_small_fp": after_components["edema_small_fp"],
            "before_remote_fp": before_components["edema_remote_fp"],
            "after_remote_fp": after_components["edema_remote_fp"],
            "before_volume_ratio": before_components["edema_pred_gt_volume_ratio"],
            "after_volume_ratio": after_components["edema_pred_gt_volume_ratio"],
            "removed_components": sum(1 for a in actions if a["removed"]),
            "removed_voxels": sum(int(a["voxels"]) for a in actions if a["removed"]),
            "small_component_threshold_voxels": small_threshold,
            "roi_radius_mm": roi_radius_mm,
        }
        case_rows.append(row)

    aggregate_rows = aggregate_before_after(case_rows)
    routing_rows = build_routing_audit_rows(case_rows)

    before_after_csv = output_dir / "edema_component_roi_before_after.csv"
    before_after_md = output_dir / "edema_component_roi_before_after.md"
    routing_csv = output_dir / "t2_aware_edema_routing_audit.csv"
    routing_md = output_dir / "t2_aware_edema_routing_audit.md"
    flags_csv = output_dir / "edema_case_flags.csv"

    write_csv(before_after_csv, aggregate_rows)
    write_before_after_md(before_after_md, aggregate_rows, thresholds)
    write_csv(routing_csv, routing_rows)
    write_routing_md(routing_md, routing_rows)
    write_csv(flags_csv, action_rows)

    manifest = {
        "script": str(Path(__file__).relative_to(REPO_ROOT)),
        "fold": args.fold,
        "pred_dir": str(args.pred_dir),
        "gt_dir": str(args.gt_dir),
        "fold_json": str(args.fold_json),
        "cases_json": str(args.cases_json),
        "raw_root": str(args.raw_root),
        "thresholds": thresholds,
        "outputs": {
            "edema_component_roi_before_after_csv": str(before_after_csv),
            "edema_component_roi_before_after_md": str(before_after_md),
            "t2_aware_edema_routing_audit_csv": str(routing_csv),
            "t2_aware_edema_routing_audit_md": str(routing_md),
            "edema_case_flags_csv": str(flags_csv),
        },
        "prohibited_actions_confirmed": [
            "no_training",
            "no_slurm",
            "no_inference",
            "no_validation_zip",
            "no_upload",
            "no_label_semantics_change",
            "no_prediction_files_written",
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "before_after_csv": before_after_csv,
        "before_after_md": before_after_md,
        "routing_csv": routing_csv,
        "routing_md": routing_md,
        "flags_csv": flags_csv,
        "manifest": manifest_path,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--pred-dir",
        type=Path,
        default=REPO_ROOT / "results/predictions/nnUNet501/fold_0",
        help="Existing compact-label nnUNet501 fold prediction directory.",
    )
    ap.add_argument(
        "--gt-dir",
        type=Path,
        default=REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr",
    )
    ap.add_argument(
        "--fold-json",
        type=Path,
        default=REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json",
    )
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument(
        "--cases-json",
        type=Path,
        default=REPO_ROOT / "data/benchmarks/protocol/cases_MyoPS.json",
    )
    ap.add_argument(
        "--raw-root",
        type=Path,
        default=REPO_ROOT / "data/CARE_Challenge/MyoPS_train",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round02_edema_postprocess_smoke",
    )
    ap.add_argument(
        "--component-quantile",
        type=float,
        default=5.0,
        help="Train-fold GT edema component-size percentile used as the small-component threshold.",
    )
    ap.add_argument(
        "--distance-quantile",
        type=float,
        default=95.0,
        help="Train-fold GT edema-to-anatomy distance percentile used as soft ROI radius.",
    )
    return ap.parse_args()


def main() -> None:
    outputs = run(parse_args())
    print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
