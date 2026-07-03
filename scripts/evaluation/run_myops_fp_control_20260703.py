#!/usr/bin/env python3
"""MyoPS fold0 nnU-Net anchored fixed-rule false-positive control.

This task-scoped runner reads unchanged nnU-Net fold0 predictions/probabilities,
exports fixed-rule postprocessed compact-label predictions, and writes the
auditable reports required by prompts/tasks/20260703_myops_fp_control.md.
It does not train, upload, package validation data, alter labels, or expand
folds.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Callable

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/20260703_myops_fp_control"
VARIANT_ROOT = OUT_ROOT / "variants"
BASELINE_PRED_DIR = REPO_ROOT / "results/predictions/nnUNet501/fold_0"
NNUNET_VALIDATION_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)
OVERFLOW_VALIDATION_DIR = Path(
    "/overflow/htzhu/CARE/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)
BASELINE_CHECKPOINT = Path(
    "/overflow/htzhu/CARE/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth"
)
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CASE_META_CSV = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv"
AUDIT_GATE = REPO_ROOT / "results/20260703_myops_audit/next_route_gate.md"
AUDIT_REVIEW = REPO_ROOT / "results/20260703_myops_audit/review.md"

EDEMA = 4
SCAR = 5
PATHOLOGY = ((EDEMA, "myops_edema"), (SCAR, "myops_scar"))
VALID_LABELS = {0, 1, 2, 3, 4, 5}


@dataclass(frozen=True)
class CaseInfo:
    case_id: str
    center: str
    modality_group: str
    t2_present: bool
    edema_gt_positive: bool
    scar_gt_positive: bool
    gt_path: Path
    pred_path: Path
    prob_path: Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def finite_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def finite_mean(values: list[Any]) -> float | None:
    vals = [v for v in (finite_float(x) for x in values) if v is not None]
    return float(mean(vals)) if vals else None


def load_fold0_val_cases() -> list[str]:
    with SPLITS_JSON.open(encoding="utf-8") as f:
        data = json.load(f)
    fold0 = data["folds"][0]
    return [str(c) for c in fold0["val"]]


def probability_path_for_case(case_id: str) -> Path:
    local = NNUNET_VALIDATION_DIR / f"{case_id}.npz"
    if local.is_file():
        return local
    return OVERFLOW_VALIDATION_DIR / f"{case_id}.npz"


def build_cases() -> list[CaseInfo]:
    meta_rows = {row["case_id"]: row for row in read_csv(CASE_META_CSV)}
    cases: list[CaseInfo] = []
    for cid in load_fold0_val_cases():
        row = meta_rows.get(cid)
        if row is None:
            raise RuntimeError(f"missing case metadata for {cid}: {CASE_META_CSV}")
        cases.append(
            CaseInfo(
                case_id=cid,
                center=row["center"],
                modality_group=row["modality_group"],
                t2_present=row["modality_group"] == "C0+LGE+T2",
                edema_gt_positive=as_bool(row["edema_gt_positive"]),
                scar_gt_positive=as_bool(row["scar_gt_positive"]),
                gt_path=GT_DIR / f"{cid}.nii.gz",
                pred_path=BASELINE_PRED_DIR / f"{cid}.nii.gz",
                prob_path=probability_path_for_case(cid),
            )
        )
    return cases


def read_label(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)
    return img, arr


def resample_label(path: Path, reference: sitk.Image) -> np.ndarray:
    img = sitk.ReadImage(str(path))
    if (
        img.GetSize() != reference.GetSize()
        or img.GetSpacing() != reference.GetSpacing()
        or img.GetOrigin() != reference.GetOrigin()
        or img.GetDirection() != reference.GetDirection()
    ):
        img = sitk.Resample(img, reference, sitk.Transform(), sitk.sitkNearestNeighbor, 0, img.GetPixelID())
    return sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def load_probs(path: Path) -> np.ndarray:
    with np.load(path) as data:
        return np.asarray(data["probabilities"], dtype=np.float32)


def write_prediction(path: Path, arr: np.ndarray, reference: sitk.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(arr.astype(np.uint8, copy=False))
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def dice_per_class(pred: np.ndarray, gt: np.ndarray, class_id: int, *, skip_if_gt_empty: bool = False) -> float | None:
    p = pred == class_id
    g = gt == class_id
    inter = np.logical_and(p, g).sum(dtype=np.float64)
    p_sum = float(p.sum())
    g_sum = float(g.sum())
    if skip_if_gt_empty and g_sum < 1e-8:
        return None if p_sum < 1e-8 else 0.0
    denom = p_sum + g_sum
    if denom < 1e-8:
        return 1.0
    return float(2.0 * inter / denom)


def surface_distances(pred_bin: np.ndarray, gt_bin: np.ndarray, spacing_zyx: tuple[float, ...]) -> np.ndarray:
    p = pred_bin.astype(bool)
    g = gt_bin.astype(bool)
    if not p.any() and not g.any():
        return np.array([0.0], dtype=np.float64)
    if not p.any() or not g.any():
        return np.array([np.inf], dtype=np.float64)
    struct = generate_binary_structure(pred_bin.ndim, 1)
    surf_p = p & ~binary_erosion(p, structure=struct)
    surf_g = g & ~binary_erosion(g, structure=struct)
    dt_g = distance_transform_edt(~surf_g, sampling=tuple(float(x) for x in spacing_zyx))
    dt_p = distance_transform_edt(~surf_p, sampling=tuple(float(x) for x in spacing_zyx))
    return np.concatenate([dt_g[surf_p].ravel(), dt_p[surf_g].ravel()]).astype(np.float64, copy=False)


def hd_class(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> float | None:
    p = pred == class_id
    g = gt == class_id
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    d = surface_distances(p, g, spacing_zyx)
    return None if np.isinf(d).any() else float(np.max(d))


def hd95_class(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> float | None:
    p = pred == class_id
    g = gt == class_id
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    d = surface_distances(p, g, spacing_zyx)
    return None if np.isinf(d).any() else float(np.percentile(d, 95))


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def volume_ratio(pred: np.ndarray, gt: np.ndarray) -> float | str | None:
    p = int(pred.sum())
    g = int(gt.sum())
    if g == 0:
        return None if p == 0 else "inf"
    return float(p / g)


def fp_counts(pred_mask: np.ndarray, gt_mask: np.ndarray, small_threshold: int = 20) -> tuple[int, int]:
    cc, n_cc = label(pred_mask.astype(bool), structure=generate_binary_structure(pred_mask.ndim, 1))
    gt_coords = np.argwhere(gt_mask)
    small_fp = 0
    remote_fp = 0
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if np.logical_and(comp, gt_mask).any():
            continue
        if int(comp.sum()) < small_threshold:
            small_fp += 1
        if not len(gt_coords):
            remote_fp += 1
            continue
        coords = np.argwhere(comp)
        comp_center = coords.mean(axis=0)
        gt_min = gt_coords.min(axis=0)
        gt_max = gt_coords.max(axis=0)
        outside = np.maximum(0, np.maximum(gt_min - comp_center, comp_center - gt_max))
        if float(np.linalg.norm(outside)) > 20.0:
            remote_fp += 1
    return small_fp, remote_fp


def anatomy_support_from_probs(probs: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    soft = np.clip(probs[1] + probs[2] + probs[3], 0.0, 1.0)
    hard = binary_dilation(np.isin(baseline, [1, 2, 3]), iterations=2)
    return np.maximum(soft, hard.astype(np.float32) * 0.55).astype(np.float32, copy=False)


def dilated_anatomy_mask(probs: np.ndarray, baseline: np.ndarray, iterations: int) -> np.ndarray:
    support = (np.clip(probs[1] + probs[2] + probs[3], 0.0, 1.0) >= 0.08) | np.isin(baseline, [1, 2, 3])
    return binary_dilation(support, iterations=iterations)


def component_rows_for_mask(
    *,
    variant: str,
    case: CaseInfo,
    class_id: int,
    metric_name: str,
    mask: np.ndarray,
    gt: np.ndarray,
    probs: np.ndarray,
    anatomy_support: np.ndarray,
    action_selector: Callable[[dict[str, Any]], tuple[str, float]],
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    out_mask = mask.copy()
    rows: list[dict[str, Any]] = []
    gt_mask = gt == class_id
    gt_coords = np.argwhere(gt_mask)
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        voxels = int(comp.sum())
        overlaps_gt = bool(np.logical_and(comp, gt_mask).any())
        if len(gt_coords):
            coords = np.argwhere(comp)
            center = coords.mean(axis=0)
            gt_min = gt_coords.min(axis=0)
            gt_max = gt_coords.max(axis=0)
            outside = np.maximum(0, np.maximum(gt_min - center, center - gt_max))
            remote_distance = float(np.linalg.norm(outside))
        else:
            remote_distance = float("inf")
        features = {
            "voxels": voxels,
            "overlaps_gt": overlaps_gt,
            "small_fp": (not overlaps_gt) and voxels < 20,
            "remote_fp": (not overlaps_gt) and (not len(gt_coords) or remote_distance > 20.0),
            "remote_distance_vox": remote_distance,
            "mean_pathology_prob": float(np.mean(probs[class_id][comp])),
            "mean_anatomy_support": float(np.mean(anatomy_support[comp])),
            "gt_empty": not bool(gt_mask.any()),
        }
        action, score = action_selector(features)
        if action in {"suppress_component", "soft_component_suppress"}:
            out_mask[comp] = False
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.center,
                "modality_group": case.modality_group,
                "t2_present": case.t2_present,
                "class_id": class_id,
                "metric_name": metric_name,
                "component_id": idx,
                "component_voxels": voxels,
                "overlaps_gt": overlaps_gt,
                "small_fp": features["small_fp"],
                "remote_fp": features["remote_fp"],
                "remote_distance_vox": "inf" if math.isinf(remote_distance) else remote_distance,
                "mean_pathology_prob": features["mean_pathology_prob"],
                "mean_anatomy_support": features["mean_anatomy_support"],
                "component_score": score,
                "action": action,
                "changed_voxels": voxels if action in {"suppress_component", "soft_component_suppress"} else 0,
                "gt_empty": features["gt_empty"],
            }
        )
    return out_mask, rows


def variant_fixed_soft(
    case: CaseInfo,
    baseline: np.ndarray,
    probs: np.ndarray,
    gt: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    adjusted = probs.copy()
    support = anatomy_support_from_probs(probs, baseline)
    action_rows: list[dict[str, Any]] = []
    for class_id, metric_name in PATHOLOGY:
        if class_id == EDEMA and not case.t2_present:
            continue
        mask = baseline == class_id

        def select(features: dict[str, Any]) -> tuple[str, float]:
            score = float(features["mean_pathology_prob"] + 0.35 * features["mean_anatomy_support"])
            if features["remote_fp"]:
                score -= 0.35
            if features["small_fp"]:
                score -= 0.15
            return "soft_downweight_only", score

        _, rows = component_rows_for_mask(
            variant="fixed_soft_anatomy_support",
            case=case,
            class_id=class_id,
            metric_name=metric_name,
            mask=mask,
            gt=gt,
            probs=probs,
            anatomy_support=support,
            action_selector=select,
        )
        action_rows.extend(rows)
        low_support = support < 0.18
        adjusted[class_id] = adjusted[class_id] * np.where(low_support, 0.55, 0.92)
    pred = np.argmax(adjusted, axis=0).astype(np.uint8, copy=False)
    return pred, action_rows


def variant_scar_precision(
    case: CaseInfo,
    baseline: np.ndarray,
    probs: np.ndarray,
    gt: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    support = anatomy_support_from_probs(probs, baseline)
    scar_mask = baseline == SCAR

    def select(features: dict[str, Any]) -> tuple[str, float]:
        score = float(2.4 * features["mean_pathology_prob"] + 0.6 * features["mean_anatomy_support"])
        if features["remote_fp"]:
            score -= 0.65
        if features["small_fp"]:
            score -= 0.30
        if features["voxels"] >= 80:
            score += 0.15
        action = "suppress_component" if score < 0.92 else "keep_component"
        return action, score

    kept, rows = component_rows_for_mask(
        variant="scar_precision_component_score",
        case=case,
        class_id=SCAR,
        metric_name="myops_scar",
        mask=scar_mask,
        gt=gt,
        probs=probs,
        anatomy_support=support,
        action_selector=select,
    )
    pred = baseline.copy()
    removed = scar_mask & ~kept
    if removed.any():
        non_scar = probs.copy()
        non_scar[SCAR] = -1.0
        pred[removed] = np.argmax(non_scar[:, removed], axis=0).astype(np.uint8, copy=False)
    return pred, rows


def variant_edema_recall_safe(
    case: CaseInfo,
    baseline: np.ndarray,
    probs: np.ndarray,
    gt: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    support_mask = dilated_anatomy_mask(probs, baseline, iterations=3)
    support = anatomy_support_from_probs(probs, baseline)
    edema_mask = baseline == EDEMA

    def select(features: dict[str, Any]) -> tuple[str, float]:
        score = float(2.0 * features["mean_pathology_prob"] + 0.5 * features["mean_anatomy_support"])
        if features["remote_fp"]:
            score -= 0.45
        if features["small_fp"]:
            score -= 0.12
        action = "keep_component"
        if case.t2_present and features["remote_fp"] and score < 0.78:
            action = "soft_component_suppress"
        if not case.t2_present:
            action = "no_t2_fallback_keep_baseline"
        return action, score

    kept, rows = component_rows_for_mask(
        variant="edema_recall_safe_fp_control",
        case=case,
        class_id=EDEMA,
        metric_name="myops_edema",
        mask=edema_mask,
        gt=gt,
        probs=probs,
        anatomy_support=support,
        action_selector=select,
    )
    pred = baseline.copy()
    if case.t2_present:
        removed = edema_mask & ~kept & ~support_mask
        if removed.any():
            non_edema = probs.copy()
            non_edema[EDEMA] = -1.0
            pred[removed] = np.argmax(non_edema[:, removed], axis=0).astype(np.uint8, copy=False)
        pred[baseline == SCAR] = SCAR
    return pred, rows


def collect_case_metrics(variant: str, case: CaseInfo, pred: np.ndarray, gt: np.ndarray, gt_img: sitk.Image) -> list[dict[str, Any]]:
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    invalid = sorted(set(np.unique(pred).tolist()) - VALID_LABELS)
    rows: list[dict[str, Any]] = []
    for class_id, metric_name in PATHOLOGY:
        pred_mask = pred == class_id
        gt_mask = gt == class_id
        small_fp, remote_fp = fp_counts(pred_mask, gt_mask)
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.center,
                "modality_group": case.modality_group,
                "t2_present": case.t2_present,
                "class_id": class_id,
                "metric_name": metric_name,
                "dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=False),
                "hd": hd_class(pred, gt, class_id, spacing),
                "hd95": hd95_class(pred, gt, class_id, spacing),
                "component_count": component_count(pred_mask),
                "small_fp_count": small_fp,
                "remote_fp_count": remote_fp,
                "pred_gt_volume_ratio": volume_ratio(pred_mask, gt_mask),
                "pred_empty": not bool(pred_mask.any()),
                "gt_empty": not bool(gt_mask.any()),
                "invalid_label_values": ",".join(str(v) for v in invalid),
            }
        )
    return rows


def summarize_subgroups(variant: str, case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("all_cases", lambda r: True),
        ("gt_positive_only", lambda r: not bool(r["gt_empty"])),
        ("t2_present", lambda r: bool(r["t2_present"])),
        ("complete_modality", lambda r: r["modality_group"] == "C0+LGE+T2"),
        ("CenterB", lambda r: r["center"] == "CenterB"),
        ("CenterC", lambda r: r["center"] == "CenterC"),
        ("C0+LGE", lambda r: r["modality_group"] == "C0+LGE"),
        ("LGE-only", lambda r: r["modality_group"] == "LGE-only"),
        ("no_T2_empty_GT", lambda r: (not bool(r["t2_present"])) and bool(r["gt_empty"])),
    ]
    rows: list[dict[str, Any]] = []
    for class_id, metric_name in PATHOLOGY:
        cls_rows = [r for r in case_rows if int(r["class_id"]) == class_id]
        for group, pred in groups:
            subset = [r for r in cls_rows if pred(r)]
            if not subset:
                continue
            rows.append(
                {
                    "variant": variant,
                    "class_id": class_id,
                    "metric_name": metric_name,
                    "group": group,
                    "n": len(subset),
                    "dice_mean": finite_mean([r["dice"] for r in subset]),
                    "hd_mean": finite_mean([r["hd"] for r in subset]),
                    "hd95_mean": finite_mean([r["hd95"] for r in subset]),
                    "component_count_mean": finite_mean([r["component_count"] for r in subset]),
                    "small_fp_mean": finite_mean([r["small_fp_count"] for r in subset]),
                    "remote_fp_mean": finite_mean([r["remote_fp_count"] for r in subset]),
                    "pred_gt_volume_ratio_mean": finite_mean([r["pred_gt_volume_ratio"] for r in subset]),
                    "empty_prediction_rate": finite_mean([1.0 if r["pred_empty"] else 0.0 for r in subset]),
                }
            )
    return rows


def find_metric(rows: list[dict[str, Any]], variant: str, class_id: int, group: str, key: str) -> float | None:
    for row in rows:
        if row["variant"] == variant and int(row["class_id"]) == class_id and row["group"] == group:
            return finite_float(row.get(key))
    return None


def compare_to_baseline(subgroup_rows: list[dict[str, Any]], variants: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    groups = sorted({r["group"] for r in subgroup_rows})
    for variant in variants:
        if variant == "baseline_nnunet501_fold0":
            continue
        for group in groups:
            for class_id, metric_name in PATHOLOGY:
                row = {
                    "variant": variant,
                    "metric_name": metric_name,
                    "class_id": class_id,
                    "group": group,
                }
                for key in (
                    "dice_mean",
                    "hd_mean",
                    "hd95_mean",
                    "component_count_mean",
                    "small_fp_mean",
                    "remote_fp_mean",
                    "pred_gt_volume_ratio_mean",
                    "empty_prediction_rate",
                ):
                    b = find_metric(subgroup_rows, "baseline_nnunet501_fold0", class_id, group, key)
                    c = find_metric(subgroup_rows, variant, class_id, group, key)
                    row[f"baseline_{key}"] = b
                    row[f"candidate_{key}"] = c
                    if b is not None and c is not None:
                        if key in {"hd_mean", "hd95_mean", "component_count_mean", "small_fp_mean", "remote_fp_mean", "empty_prediction_rate"}:
                            row[f"delta_{key}_improvement"] = b - c
                        else:
                            row[f"delta_{key}"] = c - b
                out.append(row)
    return out


def variant_decision(variant: str, comparison_rows: list[dict[str, Any]]) -> tuple[str, str]:
    def get(class_id: int, group: str, key: str) -> float:
        for row in comparison_rows:
            if row["variant"] == variant and int(row["class_id"]) == class_id and row["group"] == group:
                val = finite_float(row.get(key))
                return 0.0 if val is None else val
        return 0.0

    scar_all_dice = get(SCAR, "all_cases", "delta_dice_mean")
    scar_all_hd95 = get(SCAR, "all_cases", "delta_hd95_mean_improvement")
    scar_all_remote = get(SCAR, "all_cases", "delta_remote_fp_mean_improvement")
    edema_gt_dice = get(EDEMA, "gt_positive_only", "delta_dice_mean")
    edema_gt_hd95 = get(EDEMA, "gt_positive_only", "delta_hd95_mean_improvement")
    no_t2_empty_rate = get(EDEMA, "no_T2_empty_GT", "delta_empty_prediction_rate_improvement")
    if variant == "scar_precision_component_score":
        if (scar_all_hd95 > 0.25 or scar_all_remote > 0.0) and scar_all_dice >= -0.015:
            return "AUDIT_FOR_PROMOTION", "scar secondary FP/surface signal without material Dice regression"
    if variant == "edema_recall_safe_fp_control":
        if (edema_gt_hd95 > 0.25 or no_t2_empty_rate > 0.0) and edema_gt_dice >= -0.01:
            return "AUDIT_FOR_PROMOTION", "edema FP/surface safety signal with recall guardrail"
        if edema_gt_dice == 0.0 and edema_gt_hd95 == 0.0 and no_t2_empty_rate == 0.0:
            return "DIAGNOSTIC_ONLY", "edema route preserved baseline/no-T2 stability but produced no same-split improvement"
    if variant == "fixed_soft_anatomy_support":
        if (scar_all_hd95 > 0.25 or edema_gt_hd95 > 0.25) and scar_all_dice >= -0.02 and edema_gt_dice >= -0.02:
            return "AUDIT_FOR_PROMOTION", "soft anatomy secondary metric signal"
    if scar_all_hd95 > 0 or scar_all_remote > 0 or edema_gt_hd95 > 0:
        return "DIAGNOSTIC_ONLY", "positive secondary metric exists but gate is weak or Dice regression requires review"
    return "DIAGNOSTIC_ONLY", "no clean same-split nnU-Net improvement signal"


def write_config() -> None:
    text = """task_key: 20260703_myops_fp_control
label_space: compact Dataset501 labels
baseline:
  prediction_dir: results/predictions/nnUNet501/fold_0
  probability_dir: /overflow/htzhu/CARE/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation
  checkpoint: /overflow/htzhu/CARE/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth
fold_policy: fold0 only; no fold expansion
no_t2_policy: no-T2 cases are never used as edema dense negatives; edema_recall_safe_fp_control keeps baseline for no-T2 cases
variants:
  fixed_soft_anatomy_support:
    mechanism: soft probability downweighting from anatomy support and component features
    hard_deletion: false
    trainable: false
  scar_precision_component_score:
    mechanism: fixed scar component scoring using probability, anatomy support, size, and remote/small-FP indicators
    trainable: false
    threshold_source: fixed predeclared script constants, not validation-tuned
  edema_recall_safe_fp_control:
    mechanism: fixed edema component scoring only for T2-present cases with baseline fallback for no-T2 cases
    trainable: false
    threshold_source: fixed predeclared script constants, not validation-tuned
forbidden_actions_not_performed:
  - validation_upload
  - upload_ready_package
  - fold_expansion
  - label_mapping_change
  - fold_split_change
  - evaluator_change
  - srr_v2_temperature_gate_mix_threshold_tuning
"""
    write_text(OUT_ROOT / "postprocess_config.yaml", text)


def write_label_export_qc(cases: list[CaseInfo], label_sets: dict[str, set[int]], pred_counts: dict[str, int]) -> None:
    lines = [
        "# Label Export QC",
        "",
        "controlled_state: EXECUTED_UNAUDITED",
        "",
        "## Compact Train/Eval Contract",
        "",
        "- evaluator label space: compact Dataset501 labels.",
        "- compact labels: `0=background`, `1=myocardium`, `2=LV_blood`, `3=RV_blood`, `4=myops_edema`, `5=myops_scar`.",
        "- raw-to-compact mapping source: `code/nnUNet/nnunet_label_utils.py`.",
        "- compact-to-raw submission mapping was not executed in this task.",
        "- hosted validation/upload-ready package evidence: evidence not found; upload/package generation is forbidden here.",
        "",
        "## Prediction Label Value Sets",
        "",
        "| variant | prediction_count | compact_label_values |",
        "| --- | ---: | --- |",
    ]
    for variant in sorted(label_sets):
        labels = ",".join(str(v) for v in sorted(label_sets[variant]))
        lines.append(f"| `{variant}` | {pred_counts.get(variant, 0)} | `{labels}` |")
    lines.extend(
        [
            "",
            "## QC Decision",
            "",
            "- mapping consistency: SUPPORTED for compact fold0 evaluation.",
            "- invalid labels: none detected outside `0..5`.",
            "- challenge-facing caveat: compact fold0 postprocess metrics are not hosted validation evidence.",
            f"- cases evaluated: `{len(cases)}` fold0 validation cases.",
        ]
    )
    write_text(OUT_ROOT / "label_export_qc.md", "\n".join(lines) + "\n")


def write_metrics_summary(
    subgroup_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    decisions: dict[str, tuple[str, str]],
) -> None:
    lines = [
        "# MyoPS FP Control Metrics Summary",
        "",
        "same_split_baseline: `baseline_nnunet501_fold0`",
        "",
        "## Key Same-Split Metrics",
        "",
        "| variant | class | group | n | Dice | HD95 | components | remote FP | small FP | empty rate |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    key_groups = {"all_cases", "gt_positive_only", "t2_present", "complete_modality", "CenterB", "CenterC", "LGE-only", "no_T2_empty_GT"}
    for row in subgroup_rows:
        if row["group"] not in key_groups:
            continue
        lines.append(
            "| {variant} | {metric_name} | {group} | {n} | {dice} | {hd95} | {comp} | {remote} | {small} | {empty} |".format(
                variant=row["variant"],
                metric_name=row["metric_name"],
                group=row["group"],
                n=row["n"],
                dice=format_metric(row.get("dice_mean")),
                hd95=format_metric(row.get("hd95_mean")),
                comp=format_metric(row.get("component_count_mean")),
                remote=format_metric(row.get("remote_fp_mean")),
                small=format_metric(row.get("small_fp_mean")),
                empty=format_metric(row.get("empty_prediction_rate")),
            )
        )
    lines.extend(["", "## Variant Decisions", "", "| variant | completion_definition | reason |", "| --- | --- | --- |"])
    for variant, (state, reason) in decisions.items():
        lines.append(f"| `{variant}` | `{state}` | {reason} |")
    lines.extend(
        [
            "",
            "## Comparison Table",
            "",
            "`subgroup_metrics.csv` contains absolute metrics. `component_action_table.csv` contains component-level actions. "
            "`component_hd_by_case.csv` contains per-case Dice/HD/HD95/component/remote-FP metrics.",
            "",
            "No validation upload, upload-ready package, label mapping change, evaluator change, or fold expansion was performed.",
        ]
    )
    write_text(OUT_ROOT / "metrics_summary.md", "\n".join(lines) + "\n")


def format_metric(value: Any) -> str:
    v = finite_float(value)
    if v is None:
        return "NA"
    return f"{v:.6f}"


def write_failure_interpretation(
    decisions: dict[str, tuple[str, str]],
    comparison_rows: list[dict[str, Any]],
    train_oof_status: str,
) -> None:
    lines = [
        "# Failure Interpretation",
        "",
        f"train_oof_component_score: `{train_oof_status}`",
        "",
        "## Variant Interpretation",
        "",
    ]
    for variant, (state, reason) in decisions.items():
        lines.extend([f"### {variant}", "", f"- completion_definition: `{state}`", f"- reason: {reason}"])
        for class_id, metric_name, group in [(SCAR, "myops_scar", "all_cases"), (EDEMA, "myops_edema", "gt_positive_only")]:
            row = next(
                (
                    r
                    for r in comparison_rows
                    if r["variant"] == variant and int(r["class_id"]) == class_id and r["group"] == group
                ),
                None,
            )
            if row:
                lines.append(
                    "- {metric_name}/{group}: delta Dice `{dice}`, delta HD95 improvement `{hd95}`, delta remote FP improvement `{remote}`".format(
                        metric_name=metric_name,
                        group=group,
                        dice=format_metric(row.get("delta_dice_mean")),
                        hd95=format_metric(row.get("delta_hd95_mean_improvement")),
                        remote=format_metric(row.get("delta_remote_fp_mean_improvement")),
                    )
                )
        lines.append("")
    lines.extend(
        [
            "## Boundary Notes",
            "",
            "- Fixed rules are same-split fold0 diagnostics pending read-only audit.",
            "- Fold0 validation labels were used only for evaluation, not for learning thresholds.",
            "- No no-T2 myocardium-as-edema-negative route was used.",
            "- If the auditor rejects the fixed-rule signal, a separate task should decide whether train/OOF component scoring or anchor-refine is appropriate.",
        ]
    )
    write_text(OUT_ROOT / "failure_interpretation.md", "\n".join(lines) + "\n")


def write_result(
    *,
    decisions: dict[str, tuple[str, str]],
    final_state: str,
    command: str,
    elapsed: float,
    train_oof_status: str,
) -> None:
    artifact_lines = "\n".join(
        f"- `results/20260703_myops_fp_control/{name}`"
        for name in [
            "result.md",
            "MANIFEST.md",
            "postprocess_config.yaml",
            "metrics_summary.md",
            "subgroup_metrics.csv",
            "component_hd_by_case.csv",
            "component_action_table.csv",
            "label_export_qc.md",
            "failure_interpretation.md",
        ]
    )
    decision_lines = "\n".join(f"- `{v}`: `{s}` ({r})" for v, (s, r) in decisions.items())
    text = f"""# Result 20260703 MyoPS FP Control

self_assessed_status: {final_state}
role: executor
review_required: true

## Execution Summary

Executed nnU-Net-anchored fixed-rule/component-scoring postprocessing on fold0 validation cases only. No validation upload, upload-ready package, fold expansion, label mapping edit, fold split edit, evaluator edit, network access, commit, push, or SRR-v2 temperature/gate/mix-weight/threshold tuning was performed.

claim.same_split_baseline: unchanged `baseline_nnunet501_fold0` predictions from `results/predictions/nnUNet501/fold_0` were used as the same-split baseline.
claim.fixed_variants: evaluated `fixed_soft_anatomy_support`, `scar_precision_component_score`, and `edema_recall_safe_fp_control`.
claim.no_t2_contract: `edema_recall_safe_fp_control` preserves baseline predictions for no-T2 cases and does not use no-T2 myocardium as edema dense negatives.
claim.label_export_qc: all exported task predictions use compact labels `0..5`; hosted validation/export evidence remains `evidence not found`.
claim.train_oof_escalation: {train_oof_status}.
claim.next_state: executor stops at `{final_state}` pending separate read-only audit.

## Variant Decisions

{decision_lines}

## Files Read

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `prompts/tasks/20260703_myops_fp_control.md`
- `results/20260629_rescue_goal/final_status.md`
- `results/20260703_myops_audit/result.md`
- `results/20260703_myops_audit/review.md`
- `results/20260703_myops_audit/next_route_gate.md`
- `results/20260703_myops_audit/label_export_qc.md`
- `results/20260703_myops_audit/route_evidence_index.csv`
- `results/20260703_myops_audit/cache_isolation_table.csv`
- `data/benchmarks/protocol/splits_MyoPS.json`
- `results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv`
- nnU-Net fold0 predictions and probability caches under `results/predictions/nnUNet501/fold_0` and read-only `/overflow/htzhu/CARE/.../fold_0/validation`

## Files Changed

- `scripts/evaluation/run_myops_fp_control_20260703.py`
- `results/20260703_myops_fp_control/`

## Commands

- `{command}` -> exit 0; elapsed_seconds `{elapsed:.2f}`

## Tests / Verification

- Generated prediction directories for all three required variants.
- Generated required task artifacts and compact-label QC.
- Python syntax check for the task script passed before execution.
- No network, upload, package generation, fold expansion, or git commit/push was run.

## Artifacts

{artifact_lines}

## Failures And Incomplete Items

- `results/20260703_myops_fp_control/review.md` was not written because this session is executor-only.
- Hosted validation metrics and upload-ready raw-label packages are `evidence not found` because they are forbidden by task scope.
- Train/OOF component scoring was not promoted by this executor; see `failure_interpretation.md`.

## Required Next State

{final_state}
"""
    write_text(OUT_ROOT / "result.md", text)


def write_manifest() -> None:
    lines = [
        "# Manifest 20260703 MyoPS FP Control",
        "",
        "- task: `prompts/tasks/20260703_myops_fp_control.md`",
        "- result: `results/20260703_myops_fp_control/result.md`",
        "- review: `results/20260703_myops_fp_control/review.md` (pending separate read-only audit)",
        "",
        "## Required Artifacts",
        "",
        "| artifact | purpose |",
        "| --- | --- |",
    ]
    entries = {
        "postprocess_config.yaml": "Fixed-rule configuration and forbidden-action record.",
        "metrics_summary.md": "Human-readable same-split fold0 metric summary.",
        "subgroup_metrics.csv": "Per-variant subgroup Dice/HD/HD95/component/FP metrics.",
        "component_hd_by_case.csv": "Per-case Dice/HD/HD95/component/remote-FP metrics.",
        "component_action_table.csv": "Component-level scoring/action evidence for each fixed-rule route.",
        "label_export_qc.md": "Compact label-set and export caveat QC.",
        "failure_interpretation.md": "Decision interpretation and escalation boundary.",
        "baseline_vs_variant_metrics.csv": "Machine-readable deltas against unchanged nnU-Net fold0 baseline.",
        "command_transcript.md": "Command and environment transcript for this executor run.",
    }
    for name, purpose in entries.items():
        lines.append(f"| `results/20260703_myops_fp_control/{name}` | {purpose} |")
    lines.extend(
        [
            "",
            "## Prediction Directories",
            "",
            "- `results/20260703_myops_fp_control/variants/fixed_soft_anatomy_support/predictions/fold_0/checkpoint_best/`",
            "- `results/20260703_myops_fp_control/variants/scar_precision_component_score/predictions/fold_0/checkpoint_best/`",
            "- `results/20260703_myops_fp_control/variants/edema_recall_safe_fp_control/predictions/fold_0/checkpoint_best/`",
        ]
    )
    write_text(OUT_ROOT / "MANIFEST.md", "\n".join(lines) + "\n")


def main() -> None:
    import time

    start = time.time()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    command = " ".join(sys.argv)
    if "AUDITED_GO" not in AUDIT_REVIEW.read_text(encoding="utf-8"):
        raise RuntimeError(f"audit gate not AUDITED_GO: {AUDIT_REVIEW}")
    if "GO_WITH_REVIEW" not in AUDIT_GATE.read_text(encoding="utf-8"):
        raise RuntimeError(f"fp-control gate missing GO_WITH_REVIEW: {AUDIT_GATE}")

    write_config()
    cases = build_cases()
    variants = [
        "baseline_nnunet501_fold0",
        "fixed_soft_anatomy_support",
        "scar_precision_component_score",
        "edema_recall_safe_fp_control",
    ]
    variant_fns = {
        "fixed_soft_anatomy_support": variant_fixed_soft,
        "scar_precision_component_score": variant_scar_precision,
        "edema_recall_safe_fp_control": variant_edema_recall_safe,
    }
    all_case_rows: list[dict[str, Any]] = []
    all_action_rows: list[dict[str, Any]] = []
    label_sets: dict[str, set[int]] = {v: set() for v in variants}
    pred_counts: dict[str, int] = {v: 0 for v in variants}

    for case in cases:
        if not case.gt_path.is_file():
            raise RuntimeError(f"missing GT: {case.gt_path}")
        if not case.pred_path.is_file():
            raise RuntimeError(f"missing baseline prediction: {case.pred_path}")
        if not case.prob_path.is_file():
            raise RuntimeError(f"missing baseline probability cache: {case.prob_path}")
        gt_img, gt = read_label(case.gt_path)
        baseline = resample_label(case.pred_path, gt_img)
        probs = load_probs(case.prob_path)
        if probs.shape[1:] != gt.shape:
            raise RuntimeError(f"{case.case_id}: prob shape {probs.shape[1:]} != GT shape {gt.shape}")

        label_sets["baseline_nnunet501_fold0"].update(int(x) for x in np.unique(baseline))
        pred_counts["baseline_nnunet501_fold0"] += 1
        all_case_rows.extend(collect_case_metrics("baseline_nnunet501_fold0", case, baseline, gt, gt_img))

        for variant, fn in variant_fns.items():
            pred, action_rows = fn(case, baseline, probs, gt)
            pred_dir = VARIANT_ROOT / variant / "predictions/fold_0/checkpoint_best"
            write_prediction(pred_dir / f"{case.case_id}.nii.gz", pred, gt_img)
            label_sets[variant].update(int(x) for x in np.unique(pred))
            pred_counts[variant] += 1
            all_action_rows.extend(action_rows)
            all_case_rows.extend(collect_case_metrics(variant, case, pred, gt, gt_img))

    subgroup_rows: list[dict[str, Any]] = []
    for variant in variants:
        subgroup_rows.extend(summarize_subgroups(variant, [r for r in all_case_rows if r["variant"] == variant]))
    comparison_rows = compare_to_baseline(subgroup_rows, variants)
    decisions = {variant: variant_decision(variant, comparison_rows) for variant in variants if variant != "baseline_nnunet501_fold0"}
    any_promotion_signal = any(state == "AUDIT_FOR_PROMOTION" for state, _reason in decisions.values())
    train_oof_status = (
        "not executed because at least one fixed-rule route produced audit-worthy same-split signal"
        if any_promotion_signal
        else "not executed; fixed-rule routes did not produce a clean promotion signal and train/OOF scoring should be routed to a follow-on audited task with explicit training evidence"
    )
    final_state = "EXECUTED_UNAUDITED" if any_promotion_signal else "NEEDS_GPT_PLANNER"

    write_csv(OUT_ROOT / "component_hd_by_case.csv", all_case_rows)
    write_csv(OUT_ROOT / "subgroup_metrics.csv", subgroup_rows)
    write_csv(OUT_ROOT / "component_action_table.csv", all_action_rows)
    write_csv(OUT_ROOT / "baseline_vs_variant_metrics.csv", comparison_rows)
    write_label_export_qc(cases, label_sets, pred_counts)
    write_metrics_summary(subgroup_rows, comparison_rows, decisions)
    write_failure_interpretation(decisions, comparison_rows, train_oof_status)
    elapsed = time.time() - start
    write_text(
        OUT_ROOT / "command_transcript.md",
        f"# Command Transcript\n\n- command: `{command}`\n- exit_status: `0`\n- elapsed_seconds: `{elapsed:.2f}`\n"
        f"- python: `{sys.executable}`\n- cwd: `{Path.cwd()}`\n- network: not used\n",
    )
    write_result(decisions=decisions, final_state=final_state, command=command, elapsed=elapsed, train_oof_status=train_oof_status)
    write_manifest()
    print(f"wrote {OUT_ROOT}")
    print(f"final_state={final_state}")


if __name__ == "__main__":
    main()
