#!/usr/bin/env python3
"""Lane A Round14 feature-augmented component-aware edema calibrator smoke.

This script executes the diagnostic and lightweight-smoke stages from the
Round14 controller. It creates component-level samples, evaluates deployable
component rules, trains a small component logistic calibrator on fold0-train
components only, and runs a tiny voxel-feature calibrator smoke. It does not
submit Slurm, create validation zips, download weights, or modify nnU-Net
baseline caches.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Callable

import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import binary_dilation, distance_transform_edt, generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/mpl_cache"),
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round4_fold0_short_train_eval as base_eval
from src.care_myocardium.calibrator.laneA_round14_model import ComponentLogisticCalibrator, VoxelFeatureCalibrator
from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, load_case_features, write_csv


OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator"
OVERLAY_ROOT = OUT_ROOT / "overlays"
PLAN_PATH = REPO_ROOT / "docs/plans/laneA_round14_next_feature_augmented_component_aware_edema_calibrator_execution.md"
ROUND13_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round13_t2_lge_intensity_anatomy_consistency"
ROUND12_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round12_refiner_salvage_high_upside_transition"
ROUND11_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner"
ROUND11_PRED_DIR = ROUND11_ROOT / "predictions/laneA_r11_bidirectional_edema_refiner_fold0_very_short/validation"

EDEMA = 4
SCAR = 5
BASELINE_MODEL = "baseline_nnunet501_oof"
ROUND11_MODEL = "round11_bidirectional_refiner"
STRICT_MODEL = "round13_strict_support_filter"
COMP_RULE_MODEL = "round14_component_rule_score"
COMP_LOGISTIC_MODEL = "round14_component_logistic_calibrator"

SUBSETS = [
    "all_case",
    "t2_present",
    "t2_present_gt_positive",
    "complete_modality",
    "CenterB",
    "CenterC",
    "no_t2_empty_gt",
    "modality:C0+LGE+T2",
    "modality:C0+LGE",
    "modality:LGE-only",
]

NUMERIC_FEATURES = [
    "baseline_edema_prob_mean",
    "baseline_edema_prob_p50",
    "baseline_edema_prob_p75",
    "baseline_edema_prob_max",
    "baseline_edema_margin_mean",
    "baseline_entropy_mean",
    "normalized_T2_support_mean",
    "normalized_T2_support_p50",
    "normalized_T2_support_p75",
    "normalized_T2_support_max",
    "LGE_support_mean",
    "LGE_support_p50",
    "LGE_T2_contrast_mean",
    "within_myocardium_T2_percentile",
    "within_myocardium_LGE_percentile",
    "anatomy_support_mean",
    "anatomy_support_max",
    "distance_to_myocardium_or_anatomy_mm",
    "distance_to_baseline_edema_mm",
    "distance_to_high_T2_support_mm",
    "component_voxels",
    "component_volume_mm3",
    "largest_component_fraction",
    "shape_compactness",
    "remote_distance_mm",
    "component_support_score",
    "T2_present_numeric",
    "C0_present_numeric",
    "LGE_present_numeric",
]


@dataclass
class CalibCase:
    case: RefinerCase
    gt_img: sitk.Image
    gt: np.ndarray
    baseline: np.ndarray
    round11: np.ndarray
    probs: np.ndarray
    c0: np.ndarray
    lge: np.ndarray
    t2: np.ndarray
    anatomy: np.ndarray
    t2_support: np.ndarray
    lge_support: np.ndarray
    t2_lge_contrast: np.ndarray
    entropy: np.ndarray
    edema_margin: np.ndarray
    support_score: np.ndarray
    spacing: tuple[float, float, float]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fmt(value: object) -> str:
    if value is None or value == "":
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        if math.isinf(value):
            return "inf"
        return f"{value:.4f}"
    return str(value)


def md_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        out.append("| " + " | ".join(fmt(row.get(col)).replace("|", "\\|") for col in columns) + " |")
    return out


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        number = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(number) or math.isinf(number) else number


def avg(values: list[object]) -> float | None:
    vals = [safe_float(v, math.nan) for v in values]
    vals = [v for v in vals if not math.isnan(v)]
    return float(mean(vals)) if vals else None


def delta(candidate: object, baseline: object, *, lower_is_better: bool = False) -> float | None:
    c = safe_float(candidate, math.nan)
    b = safe_float(baseline, math.nan)
    if math.isnan(c) or math.isnan(b):
        return None
    return b - c if lower_is_better else c - b


def robust_percentile_support(arr: np.ndarray, support: np.ndarray | None = None) -> np.ndarray:
    valid = np.isfinite(arr)
    if support is not None and support.any():
        valid &= support.astype(bool)
    vals = arr[valid]
    if vals.size < 10:
        vals = arr[np.isfinite(arr)]
    if vals.size == 0:
        return np.full(arr.shape, 0.5, dtype=np.float32)
    lo = float(np.percentile(vals, 10))
    hi = float(np.percentile(vals, 90))
    if hi <= lo:
        return np.full(arr.shape, 0.5, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def robust_z_support(arr: np.ndarray, support: np.ndarray | None = None) -> np.ndarray:
    valid = np.isfinite(arr)
    if support is not None and support.any():
        valid &= support.astype(bool)
    vals = arr[valid]
    if vals.size < 10:
        vals = arr[np.isfinite(arr)]
    if vals.size == 0:
        return np.full(arr.shape, 0.5, dtype=np.float32)
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25, 75])
    scale = float(q75 - q25)
    if scale <= 1e-6:
        return np.full(arr.shape, 0.5, dtype=np.float32)
    z = (arr - med) / scale
    return (1.0 / (1.0 + np.exp(-z))).astype(np.float32)


def region_stats(arr: np.ndarray, mask: np.ndarray, prefix: str) -> dict[str, object]:
    if not mask.any():
        return {
            f"{prefix}_mean": None,
            f"{prefix}_p25": None,
            f"{prefix}_p50": None,
            f"{prefix}_p75": None,
            f"{prefix}_max": None,
        }
    vals = arr[mask.astype(bool)].astype(np.float64, copy=False)
    return {
        f"{prefix}_mean": float(vals.mean()),
        f"{prefix}_p25": float(np.percentile(vals, 25)),
        f"{prefix}_p50": float(np.percentile(vals, 50)),
        f"{prefix}_p75": float(np.percentile(vals, 75)),
        f"{prefix}_max": float(vals.max()),
    }


def distance_map_to_support(support: np.ndarray, spacing: tuple[float, float, float]) -> np.ndarray | None:
    if not support.any():
        return None
    return distance_transform_edt(~support.astype(bool), sampling=spacing)


def min_dist_from_map(mask: np.ndarray, dist_map: np.ndarray | None) -> float | None:
    if not mask.any():
        return None
    if dist_map is None:
        return float("inf")
    return float(dist_map[mask.astype(bool)].min())


def bbox_sizes(mask: np.ndarray) -> tuple[int, int, int]:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return (0, 0, 0)
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    return tuple(int(v) for v in (maxs - mins + 1))


def bbox_compactness(mask: np.ndarray) -> float | None:
    sizes = bbox_sizes(mask)
    vol = int(np.prod(sizes))
    return float(mask.sum() / max(1, vol)) if vol else None


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(3, 1))
    return int(n_cc)


def load_calib_case(case: RefinerCase) -> CalibCase:
    features, _, baseline, gt_img = load_case_features(case)
    gt = sitk.GetArrayFromImage(sitk.ReadImage(str(case.gt_path))).astype(np.uint8, copy=False)
    round11_path = ROUND11_PRED_DIR / f"{case.case_id}.nii.gz"
    if case.fold0_split == "val" and round11_path.is_file():
        round11 = base_eval.read_pred(round11_path, gt_img).astype(np.uint8, copy=False)
    else:
        round11 = baseline.astype(np.uint8, copy=True)
    probs = features[:6].astype(np.float32, copy=False)
    c0 = features[6].astype(np.float32, copy=False)
    lge = features[7].astype(np.float32, copy=False)
    t2 = features[8].astype(np.float32, copy=False)
    anatomy = features[-1].astype(np.float32, copy=False)
    anatomy_mask = anatomy >= 0.05
    if case.t2_present:
        t2_support = (0.5 * robust_percentile_support(t2, anatomy_mask) + 0.5 * robust_z_support(t2, anatomy_mask)).astype(np.float32)
    else:
        t2_support = np.full(t2.shape, 0.5, dtype=np.float32)
    lge_support = robust_percentile_support(lge, anatomy_mask)
    t2_lge_contrast = (t2_support - lge_support).astype(np.float32) if case.t2_present else np.zeros_like(lge_support, dtype=np.float32)
    eps = 1e-6
    entropy = (-(probs * np.log(np.clip(probs, eps, 1.0))).sum(axis=0) / math.log(probs.shape[0])).astype(np.float32)
    non_edema = np.max(np.delete(probs, EDEMA, axis=0), axis=0)
    edema_margin = (probs[EDEMA] - non_edema).astype(np.float32)
    support_score = (
        0.35 * t2_support
        + 0.15 * lge_support
        + 0.20 * np.clip((edema_margin + 1.0) / 2.0, 0.0, 1.0)
        + 0.15 * probs[EDEMA]
        + 0.15 * anatomy
    ).astype(np.float32)
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    return CalibCase(
        case=case,
        gt_img=gt_img,
        gt=gt,
        baseline=baseline.astype(np.uint8, copy=False),
        round11=round11,
        probs=probs,
        c0=c0,
        lge=lge,
        t2=t2,
        anatomy=anatomy,
        t2_support=t2_support,
        lge_support=lge_support,
        t2_lge_contrast=t2_lge_contrast,
        entropy=entropy,
        edema_margin=edema_margin,
        support_score=support_score,
        spacing=spacing,
    )


def build_component_dataset_stream(case_defs: list[RefinerCase]) -> tuple[list[dict[str, object]], list[CalibCase]]:
    rows: list[dict[str, object]] = []
    val_cases: list[CalibCase] = []
    for case in case_defs:
        fc = load_calib_case(case)
        rows.extend(component_rows_for_mask(fc, fc.baseline == EDEMA, "baseline_component"))
        if fc.case.fold0_split == "val":
            rows.extend(component_rows_for_mask(fc, fc.round11 == EDEMA, "round11_component_eval_only"))
            rows.extend(component_rows_for_mask(fc, (fc.round11 == EDEMA) & (fc.baseline != EDEMA), "round11_added_component_eval_only"))
            strict = apply_component_rule(fc, strict_reject, STRICT_MODEL)
            rows.extend(component_rows_for_mask(fc, (strict == EDEMA) & (fc.baseline != EDEMA), "round13_strict_added_eval_only"))
            val_cases.append(fc)
    write_csv(OUT_ROOT / "round14_component_dataset_manifest.csv", rows)
    return rows, val_cases


def strict_reject(attrs: dict[str, object], t2_present: bool) -> bool:
    return (
        safe_float(attrs["component_support_score"]) < 0.50
        or (t2_present and safe_float(attrs["normalized_T2_support_mean"]) < 0.50)
        or safe_float(attrs["baseline_edema_prob_mean"]) < 0.30
        or safe_float(attrs["distance_to_baseline_edema_mm"], 999.0) > 5.0
    )


def component_rule_reject(attrs: dict[str, object], t2_present: bool) -> bool:
    return (
        safe_float(attrs["component_support_score"]) < 0.47
        or (t2_present and safe_float(attrs["normalized_T2_support_mean"]) < 0.47 and safe_float(attrs["baseline_edema_prob_mean"]) < 0.40)
        or safe_float(attrs["distance_to_baseline_edema_mm"], 999.0) > 8.0
        or safe_float(attrs["baseline_edema_prob_mean"]) < 0.22
    )


def component_features(fc: CalibCase, comp: np.ndarray, source_model: str, component_index: int) -> dict[str, object]:
    baseline_edema = fc.baseline == EDEMA
    hard_anatomy = np.isin(fc.baseline, [1, 2, 3])
    high_t2 = fc.t2_support >= 0.55 if fc.case.t2_present else np.zeros_like(fc.t2_support, dtype=bool)
    dist_anatomy = distance_map_to_support(hard_anatomy, fc.spacing)
    dist_baseline = distance_map_to_support(baseline_edema, fc.spacing)
    dist_t2 = distance_map_to_support(high_t2, fc.spacing) if fc.case.t2_present else None
    gt_edema = fc.gt == EDEMA
    sizes = bbox_sizes(comp)
    voxel_volume = float(np.prod(fc.spacing))
    baseline_sizes = []
    if baseline_edema.any():
        cc_base, n_base = label(baseline_edema, structure=generate_binary_structure(3, 1))
        baseline_sizes = [int((cc_base == idx).sum()) for idx in range(1, n_base + 1)]
    largest_baseline = max(baseline_sizes) if baseline_sizes else 0
    row: dict[str, object] = {
        "case_id": fc.case.case_id,
        "fold0_split": fc.case.fold0_split,
        "source_model_or_rule": source_model,
        "component_index": component_index,
        "center": fc.case.center,
        "modality_group": fc.case.modality_group,
        "C0_present": fc.case.c0_present,
        "LGE_present": fc.case.lge_present,
        "T2_present": fc.case.t2_present,
        "C0_present_numeric": int(fc.case.c0_present),
        "LGE_present_numeric": int(fc.case.lge_present),
        "T2_present_numeric": int(fc.case.t2_present),
        "edema_gt_positive": fc.case.edema_gt_positive,
        "component_voxels": int(comp.sum()),
        "component_volume_mm3": int(comp.sum()) * voxel_volume,
        "shape_compactness": bbox_compactness(comp),
        "bbox_size_z": sizes[0],
        "bbox_size_y": sizes[1],
        "bbox_size_x": sizes[2],
        "largest_component_fraction": float(comp.sum() / max(1, largest_baseline)),
        "gt_overlap_voxels": int((comp & gt_edema).sum()),
        "gt_overlap_fraction": float((comp & gt_edema).sum() / max(1, int(comp.sum()))),
        "distance_to_myocardium_or_anatomy_mm": min_dist_from_map(comp, dist_anatomy),
        "distance_to_baseline_edema_mm": min_dist_from_map(comp, dist_baseline),
        "distance_to_high_T2_support_mm": min_dist_from_map(comp, dist_t2) if fc.case.t2_present else None,
        "remote_distance_mm": min_dist_from_map(comp, dist_baseline),
        "component_touches_baseline_edema": bool(binary_dilation(comp, iterations=1).astype(bool)[baseline_edema].any()) if baseline_edema.any() else False,
    }
    row.update(region_stats(fc.probs[EDEMA], comp, "baseline_edema_prob"))
    row.update(region_stats(fc.edema_margin, comp, "baseline_edema_margin"))
    row.update(region_stats(fc.entropy, comp, "baseline_entropy"))
    row.update(region_stats(fc.t2_support, comp, "normalized_T2_support"))
    row.update(region_stats(fc.lge_support, comp, "LGE_support"))
    row.update(region_stats(fc.t2_lge_contrast, comp, "LGE_T2_contrast"))
    row.update(region_stats(fc.anatomy, comp, "anatomy_support"))
    row["within_myocardium_T2_percentile"] = row["normalized_T2_support_p50"]
    row["within_myocardium_LGE_percentile"] = row["LGE_support_p50"]
    row["component_support_score"] = (
        0.25 * safe_float(row["normalized_T2_support_mean"], 0.5)
        + 0.20 * safe_float(row["baseline_edema_prob_mean"], 0.0)
        + 0.20 * safe_float(row["anatomy_support_mean"], 0.0)
        + 0.15 * safe_float(row["LGE_support_mean"], 0.0)
        + 0.20 * safe_float(row["baseline_edema_margin_mean"], 0.0)
    )
    row["label_keep_component"] = int(row["gt_overlap_voxels"] > 0)
    row["label_definition"] = "keep if component overlaps class_4 GT; validation labels evaluation-only"
    return row


def component_rows_for_mask(fc: CalibCase, mask: np.ndarray, source_model: str) -> list[dict[str, object]]:
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(3, 1))
    rows = []
    for idx in range(1, n_cc + 1):
        rows.append(component_features(fc, cc == idx, source_model, idx))
    return rows


def summarize_component_dataset(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    keys = sorted(set((r["fold0_split"], r["source_model_or_rule"], r["center"], r["modality_group"]) for r in rows))
    for split, source, center, group in keys:
        items = [r for r in rows if r["fold0_split"] == split and r["source_model_or_rule"] == source and r["center"] == center and r["modality_group"] == group]
        out.append(
            {
                "fold0_split": split,
                "source_model_or_rule": source,
                "center": center,
                "modality_group": group,
                "n_components": len(items),
                "keep_label_rate": avg([r["label_keep_component"] for r in items]),
                "mean_component_voxels": avg([r["component_voxels"] for r in items]),
                "mean_t2_support": avg([r["normalized_T2_support_mean"] for r in items]),
                "mean_baseline_edema_prob": avg([r["baseline_edema_prob_mean"] for r in items]),
                "mean_component_support_score": avg([r["component_support_score"] for r in items]),
            }
        )
    write_csv(OUT_ROOT / "round14_component_feature_summary.csv", out)
    return out


def apply_component_rule(fc: CalibCase, reject: Callable[[dict[str, object], bool], bool], model_name: str) -> np.ndarray:
    pred = fc.round11.copy()
    added = (fc.round11 == EDEMA) & (fc.baseline != EDEMA)
    cc, n_cc = label(added.astype(bool), structure=generate_binary_structure(3, 1))
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        attrs = component_features(fc, comp, model_name, idx)
        if reject(attrs, fc.case.t2_present):
            pred[comp] = fc.baseline[comp]
    pred[fc.baseline == SCAR] = SCAR
    return pred.astype(np.uint8, copy=False)


def subset_filter(name: str) -> Callable[[dict[str, object]], bool]:
    if name == "all_case":
        return lambda r: True
    if name == "t2_present":
        return lambda r: r.get("t2_present") is True
    if name == "t2_present_gt_positive":
        return lambda r: r.get("t2_present") is True and r.get("edema_gt_positive") is True
    if name == "complete_modality":
        return lambda r: r.get("modality_group") == "C0+LGE+T2"
    if name == "CenterB":
        return lambda r: r.get("center") == "CenterB"
    if name == "CenterC":
        return lambda r: r.get("center") == "CenterC"
    if name == "no_t2_empty_gt":
        return lambda r: r.get("t2_present") is False and r.get("edema_gt_positive") is False
    if name.startswith("modality:"):
        group = name.split(":", 1)[1]
        return lambda r: r.get("modality_group") == group
    raise ValueError(name)


def class_row(fc: CalibCase, pred: np.ndarray, model: str) -> dict[str, object]:
    row: dict[str, object] = {
        "model": model,
        "case_id": fc.case.case_id,
        "center": fc.case.center,
        "modality_group": fc.case.modality_group,
        "t2_present": fc.case.t2_present,
        "edema_gt_positive": fc.case.edema_gt_positive,
        "scar_gt_positive": fc.case.scar_gt_positive,
        "scar_changed_voxels": int(np.logical_xor(fc.baseline == SCAR, pred == SCAR).sum()),
        "changed_voxels": int((pred != fc.baseline).sum()),
        "added_voxels": int(((pred == EDEMA) & (fc.baseline != EDEMA)).sum()),
        "removed_voxels": int(((fc.baseline == EDEMA) & (pred != EDEMA)).sum()),
        "no_t2_edema_fp_voxels": int((pred == EDEMA).sum()) if (not fc.case.t2_present and not fc.case.edema_gt_positive) else 0,
    }
    row.update(base_eval.class_metrics(pred, fc.gt, fc.spacing, EDEMA, "myops_edema"))
    row.update(base_eval.class_metrics(pred, fc.gt, fc.spacing, SCAR, "myops_scar"))
    return row


def evaluate_predictions(cases: list[CalibCase], predictions: dict[str, np.ndarray], model: str) -> list[dict[str, object]]:
    return [class_row(fc, predictions[fc.case.case_id], model) for fc in cases if fc.case.fold0_split == "val"]


def aggregate(rows: list[dict[str, object]], model: str, subset: str) -> dict[str, object]:
    filt = subset_filter(subset)
    items = [r for r in rows if r["model"] == model and filt(r)]
    return {
        "model": model,
        "subset": subset,
        "n": len(items),
        "myops_edema_dice": avg([r.get("myops_edema_dice") for r in items]),
        "myops_edema_hd": avg([r.get("myops_edema_hd") for r in items]),
        "myops_edema_hd95": avg([r.get("myops_edema_hd95") for r in items]),
        "myops_edema_component_count": avg([r.get("myops_edema_component_count") for r in items]),
        "myops_edema_small_fp": avg([r.get("myops_edema_small_fp") for r in items]),
        "myops_edema_remote_fp": avg([r.get("myops_edema_remote_fp") for r in items]),
        "myops_edema_pred_gt_volume_ratio": avg([r.get("myops_edema_pred_gt_volume_ratio") for r in items]),
        "myops_scar_dice": avg([r.get("myops_scar_dice") for r in items]),
        "myops_scar_hd": avg([r.get("myops_scar_hd") for r in items]),
        "myops_scar_hd95": avg([r.get("myops_scar_hd95") for r in items]),
        "scar_changed_voxels": sum(int(r.get("scar_changed_voxels", 0)) for r in items),
        "no_t2_edema_fp_voxels": sum(int(r.get("no_t2_edema_fp_voxels", 0)) for r in items),
    }


def compare_to_baseline(baseline_rows: list[dict[str, object]], candidate_rows: list[dict[str, object]], model: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for subset in SUBSETS:
        b = aggregate(baseline_rows, BASELINE_MODEL, subset)
        c = aggregate(candidate_rows, model, subset)
        out.append(
            {
                "model": model,
                "subset": subset,
                "n": c["n"],
                "baseline_edema_dice": b["myops_edema_dice"],
                "candidate_edema_dice": c["myops_edema_dice"],
                "delta_edema_dice": delta(c["myops_edema_dice"], b["myops_edema_dice"]),
                "baseline_edema_hd95": b["myops_edema_hd95"],
                "candidate_edema_hd95": c["myops_edema_hd95"],
                "delta_edema_hd95_improvement": delta(c["myops_edema_hd95"], b["myops_edema_hd95"], lower_is_better=True),
                "baseline_edema_component_count": b["myops_edema_component_count"],
                "candidate_edema_component_count": c["myops_edema_component_count"],
                "delta_edema_component_count_improvement": delta(c["myops_edema_component_count"], b["myops_edema_component_count"], lower_is_better=True),
                "baseline_edema_remote_fp": b["myops_edema_remote_fp"],
                "candidate_edema_remote_fp": c["myops_edema_remote_fp"],
                "delta_edema_remote_fp_improvement": delta(c["myops_edema_remote_fp"], b["myops_edema_remote_fp"], lower_is_better=True),
                "baseline_scar_dice": b["myops_scar_dice"],
                "candidate_scar_dice": c["myops_scar_dice"],
                "delta_scar_dice": delta(c["myops_scar_dice"], b["myops_scar_dice"]),
                "baseline_scar_hd95": b["myops_scar_hd95"],
                "candidate_scar_hd95": c["myops_scar_hd95"],
                "delta_scar_hd95_improvement": delta(c["myops_scar_hd95"], b["myops_scar_hd95"], lower_is_better=True),
                "candidate_scar_changed_voxels": c["scar_changed_voxels"],
                "candidate_no_t2_edema_fp_voxels": c["no_t2_edema_fp_voxels"],
            }
        )
    return out


def failure_flags(baseline_rows: list[dict[str, object]], candidate_rows: list[dict[str, object]], model: str) -> list[dict[str, object]]:
    by_base = {str(r["case_id"]): r for r in baseline_rows}
    out: list[dict[str, object]] = []
    for c in candidate_rows:
        cid = str(c["case_id"])
        b = by_base[cid]
        flags: list[str] = []
        d_dice = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        d_hd95 = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        d_comp = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        d_remote = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        if d_dice is not None and d_dice > 0.005 and d_hd95 is not None and d_hd95 < -0.5:
            flags.append("edema_dice_up_hd95_worse")
        if d_comp is not None and d_comp < -0.5:
            flags.append("edema_component_worse")
        if d_remote is not None and d_remote < 0:
            flags.append("edema_remote_fp_worse")
        if c.get("t2_present") is False and c.get("edema_gt_positive") is False and int(c.get("no_t2_edema_fp_voxels", 0)) > int(b.get("no_t2_edema_fp_voxels", 0)):
            flags.append("no_t2_empty_gt_new_edema_fp")
        if int(c.get("scar_changed_voxels", 0)) != 0:
            flags.append("scar_changed")
        out.append(
            {
                "model": model,
                "case_id": cid,
                "center": c.get("center"),
                "modality_group": c.get("modality_group"),
                "t2_present": c.get("t2_present"),
                "edema_gt_positive": c.get("edema_gt_positive"),
                "delta_edema_dice": d_dice,
                "delta_edema_hd95_improvement": d_hd95,
                "delta_edema_component_count_improvement": d_comp,
                "delta_edema_remote_fp_improvement": d_remote,
                "flags": ";".join(flags),
            }
        )
    return out


def train_component_model(rows: list[dict[str, object]]) -> tuple[ComponentLogisticCalibrator | None, dict[str, object], dict[str, float], dict[str, float]]:
    train_rows = [r for r in rows if r["fold0_split"] == "train" and r["source_model_or_rule"] == "baseline_component"]
    if not train_rows:
        return None, {"status": "fail_no_train_components"}, {}, {}
    x = np.asarray([[safe_float(r.get(c), 0.0) for c in NUMERIC_FEATURES] for r in train_rows], dtype=np.float32)
    y = np.asarray([int(r["label_keep_component"]) for r in train_rows], dtype=np.float32)
    if len(set(y.tolist())) < 2:
        return None, {"status": "fail_single_class_train_labels", "n_train_components": len(train_rows)}, {}, {}
    mean_v = x.mean(axis=0)
    std_v = x.std(axis=0)
    std_v[std_v < 1e-6] = 1.0
    xz = (x - mean_v) / std_v
    torch.manual_seed(14)
    model = ComponentLogisticCalibrator(in_features=xz.shape[1])
    opt = torch.optim.AdamW(model.parameters(), lr=0.03, weight_decay=1e-3)
    xt = torch.from_numpy(xz)
    yt = torch.from_numpy(y)
    initial_loss = None
    last_loss = None
    for step in range(240):
        opt.zero_grad()
        logits = model(xt)
        pos_weight = torch.tensor([(len(y) - float(y.sum())) / max(1.0, float(y.sum()))], dtype=torch.float32)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, yt, pos_weight=pos_weight)
        if step == 0:
            initial_loss = float(loss.detach())
        loss.backward()
        opt.step()
        last_loss = float(loss.detach())
    with torch.no_grad():
        probs = torch.sigmoid(model(xt)).numpy()
    pred = probs >= 0.5
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    summary = {
        "status": "pass",
        "n_train_components": len(train_rows),
        "n_positive": int(y.sum()),
        "n_negative": int(len(y) - y.sum()),
        "initial_loss": initial_loss,
        "final_loss": last_loss,
        "loss_delta": None if initial_loss is None or last_loss is None else initial_loss - last_loss,
        "train_accuracy": float((tp + tn) / max(1, len(y))),
        "train_precision": float(tp / max(1, tp + fp)),
        "train_recall": float(tp / max(1, tp + fn)),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "nan_or_inf": bool(np.isnan(probs).any() or np.isinf(probs).any()),
    }
    return model, summary, {c: float(m) for c, m in zip(NUMERIC_FEATURES, mean_v)}, {c: float(s) for c, s in zip(NUMERIC_FEATURES, std_v)}


def component_model_predict(model: ComponentLogisticCalibrator, mean_v: dict[str, float], std_v: dict[str, float], attrs: dict[str, object]) -> float:
    x = np.asarray([(safe_float(attrs.get(c), 0.0) - mean_v[c]) / std_v[c] for c in NUMERIC_FEATURES], dtype=np.float32)
    with torch.no_grad():
        return float(torch.sigmoid(model(torch.from_numpy(x[None])))[0])


def apply_component_model(fc: CalibCase, model: ComponentLogisticCalibrator, mean_v: dict[str, float], std_v: dict[str, float]) -> tuple[np.ndarray, list[dict[str, object]]]:
    pred = fc.round11.copy()
    decisions: list[dict[str, object]] = []
    added = (fc.round11 == EDEMA) & (fc.baseline != EDEMA)
    cc, n_cc = label(added.astype(bool), structure=generate_binary_structure(3, 1))
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        attrs = component_features(fc, comp, COMP_LOGISTIC_MODEL, idx)
        prob_keep = component_model_predict(model, mean_v, std_v, attrs)
        keep = prob_keep >= 0.5
        if not keep:
            pred[comp] = fc.baseline[comp]
        decisions.append(
            {
                "case_id": fc.case.case_id,
                "center": fc.case.center,
                "component_index": idx,
                "prob_keep": prob_keep,
                "accepted": keep,
                "gt_overlap_voxels": attrs["gt_overlap_voxels"],
                "component_voxels": attrs["component_voxels"],
                "component_support_score": attrs["component_support_score"],
                "distance_to_baseline_edema_mm": attrs["distance_to_baseline_edema_mm"],
            }
        )
    pred[fc.baseline == SCAR] = SCAR
    return pred.astype(np.uint8, copy=False), decisions


def build_predictions(cases: list[CalibCase], model: ComponentLogisticCalibrator | None, mean_v: dict[str, float], std_v: dict[str, float]) -> tuple[dict[str, dict[str, np.ndarray]], list[dict[str, object]]]:
    preds = {
        BASELINE_MODEL: {},
        ROUND11_MODEL: {},
        STRICT_MODEL: {},
        COMP_RULE_MODEL: {},
        COMP_LOGISTIC_MODEL: {},
    }
    decisions: list[dict[str, object]] = []
    for fc in cases:
        if fc.case.fold0_split != "val":
            continue
        preds[BASELINE_MODEL][fc.case.case_id] = fc.baseline.copy()
        preds[ROUND11_MODEL][fc.case.case_id] = fc.round11.copy()
        preds[STRICT_MODEL][fc.case.case_id] = apply_component_rule(fc, strict_reject, STRICT_MODEL)
        preds[COMP_RULE_MODEL][fc.case.case_id] = apply_component_rule(fc, component_rule_reject, COMP_RULE_MODEL)
        if model is None:
            preds[COMP_LOGISTIC_MODEL][fc.case.case_id] = preds[STRICT_MODEL][fc.case.case_id].copy()
        else:
            pred, dec = apply_component_model(fc, model, mean_v, std_v)
            preds[COMP_LOGISTIC_MODEL][fc.case.case_id] = pred
            decisions.extend(dec)
    return preds, decisions


def sample_voxel_dataset(case_defs: list[RefinerCase], max_per_region: int = 256) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(14)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    ws: list[np.ndarray] = []
    case_ids: list[str] = []
    for case in case_defs:
        if case.fold0_split != "train":
            continue
        fc = load_calib_case(case)
        gt = fc.gt == EDEMA
        baseline_edema = fc.baseline == EDEMA
        regions = []
        if fc.case.t2_present and fc.case.edema_gt_positive:
            regions.extend([gt, baseline_edema & ~gt, gt & ~baseline_edema])
        elif not fc.case.t2_present and not fc.case.edema_gt_positive:
            regions.append(baseline_edema)
        for region in regions:
            coords = np.argwhere(region)
            if coords.size == 0:
                continue
            take = min(max_per_region, len(coords))
            idx = rng.choice(len(coords), size=take, replace=False)
            pts = coords[idx]
            feats = np.stack(
                [
                    fc.probs[EDEMA][tuple(pts.T)],
                    fc.entropy[tuple(pts.T)],
                    fc.edema_margin[tuple(pts.T)],
                    fc.t2_support[tuple(pts.T)],
                    fc.lge_support[tuple(pts.T)],
                    fc.t2_lge_contrast[tuple(pts.T)],
                    fc.anatomy[tuple(pts.T)],
                    fc.support_score[tuple(pts.T)],
                    np.full(take, float(fc.case.t2_present), dtype=np.float32),
                    np.full(take, float(fc.case.c0_present), dtype=np.float32),
                    np.full(take, float(fc.case.lge_present), dtype=np.float32),
                ],
                axis=1,
            ).astype(np.float32)
            labels = gt[tuple(pts.T)].astype(np.float32)
            weights = np.ones_like(labels, dtype=np.float32)
            if not fc.case.t2_present:
                weights *= 0.05
            xs.append(feats)
            ys.append(labels)
            ws.append(weights)
            case_ids.extend([fc.case.case_id] * take)
    if not xs:
        return np.zeros((0, 11), dtype=np.float32), np.zeros((0,), dtype=np.float32), np.zeros((0,), dtype=np.float32), []
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ws), case_ids


def run_voxel_tiny_smoke(case_defs: list[RefinerCase]) -> tuple[dict[str, object], dict[str, object]]:
    x, y, w, case_ids = sample_voxel_dataset(case_defs)
    manifest = {
        "n_samples": int(len(y)),
        "n_positive": int(y.sum()) if len(y) else 0,
        "n_negative": int(len(y) - y.sum()) if len(y) else 0,
        "case_count": len(set(case_ids)),
        "feature_columns": "baseline_edema_prob,entropy,edema_margin,t2_support,lge_support,t2_lge_contrast,anatomy,support_score,T2_present,C0_present,LGE_present",
        "no_t2_policy": "weak weight 0.05, not dense hard negative",
    }
    write_csv(OUT_ROOT / "round14_voxel_patch_dataset_manifest.csv", [manifest])
    if len(y) == 0 or len(set(y.tolist())) < 2:
        row = {"status": "fail_insufficient_voxel_samples", **manifest}
        return row, row
    mean_v = x.mean(axis=0)
    std_v = x.std(axis=0)
    std_v[std_v < 1e-6] = 1.0
    xz = (x - mean_v) / std_v
    torch.manual_seed(1414)
    model = VoxelFeatureCalibrator(in_features=xz.shape[1], hidden_features=16)
    opt = torch.optim.AdamW(model.parameters(), lr=0.01, weight_decay=1e-4)
    xt = torch.from_numpy(xz)
    yt = torch.from_numpy(y)
    wt = torch.from_numpy(w)
    initial_loss = None
    final_loss = None
    grad_norm = None
    for step in range(80):
        opt.zero_grad()
        logits = model(xt)
        loss_raw = torch.nn.functional.binary_cross_entropy_with_logits(logits, yt, reduction="none")
        loss = (loss_raw * wt).sum() / torch.clamp(wt.sum(), min=1.0)
        if step == 0:
            initial_loss = float(loss.detach())
        loss.backward()
        grad_norm = float(sum((p.grad.detach().norm().item() ** 2 for p in model.parameters() if p.grad is not None)) ** 0.5)
        opt.step()
        final_loss = float(loss.detach())
    with torch.no_grad():
        prob = torch.sigmoid(model(xt)).numpy()
    row = {
        "status": "pass",
        **manifest,
        "initial_loss": initial_loss,
        "final_loss": final_loss,
        "loss_delta": None if initial_loss is None or final_loss is None else initial_loss - final_loss,
        "last_grad_norm": grad_norm,
        "nan_or_inf": bool(np.isnan(prob).any() or np.isinf(prob).any()),
        "positive_prob_mean": float(prob[y > 0.5].mean()) if np.any(y > 0.5) else None,
        "negative_prob_mean": float(prob[y <= 0.5].mean()) if np.any(y <= 0.5) else None,
    }
    return row, row


def write_reproducibility_gate(case_defs: list[RefinerCase], val_cases: list[CalibCase]) -> None:
    required = [
        PLAN_PATH,
        ROUND13_ROOT / "round13_decision_table.md",
        ROUND13_ROOT / "round13_round14_recommendation.md",
        ROUND13_ROOT / "feature_only_rule_grid.md",
        ROUND13_ROOT / "feature_augmented_unit_gradient_smoke.csv",
        ROUND13_ROOT / "feature_augmented_tiny_overfit_metrics.csv",
        ROUND13_ROOT / "round14_external_method_readiness_matrix.md",
        ROUND12_ROOT / "round12_decision_table.md",
        ROUND11_ROOT / "failure_case_summary/round11_failure_case_summary.md",
    ]
    train_defs = [c for c in case_defs if c.fold0_split == "train"]
    val_defs = [c for c in case_defs if c.fold0_split == "val"]
    feature_cache = ROUND13_ROOT / "feature_cache"
    rows = [{"check": "required_file_exists", "item": str(p.relative_to(REPO_ROOT)), "status": p.is_file(), "detail": ""} for p in required]
    rows.extend(
        [
            {"check": "fold0_cases_loaded", "item": "all_cases", "status": len(case_defs) == 220, "detail": len(case_defs)},
            {"check": "fold0_train_cases_loaded", "item": "train_cases", "status": len(train_defs) == 176, "detail": len(train_defs)},
            {"check": "fold0_val_cases_loaded", "item": "val_cases", "status": len(val_defs) == 44 and len(val_cases) == 44, "detail": f"defs={len(val_defs)} loaded={len(val_cases)}"},
            {"check": "round13_feature_cache_exists", "item": str(feature_cache.relative_to(REPO_ROOT)), "status": feature_cache.is_dir(), "detail": len(list(feature_cache.glob("*.npz"))) if feature_cache.is_dir() else 0},
            {
                "check": "label_semantics",
                "item": "compact labels",
                "status": sorted(set(int(x) for fc in val_cases for x in np.unique(fc.gt))) == [0, 1, 2, 3, 4, 5],
                "detail": "background, myocardium, LV, RV, edema=4, scar=5",
            },
            {
                "check": "round11_val_predictions_available",
                "item": str(ROUND11_PRED_DIR.relative_to(REPO_ROOT)),
                "status": len(list(ROUND11_PRED_DIR.glob("*.nii.gz"))) == 44,
                "detail": len(list(ROUND11_PRED_DIR.glob("*.nii.gz"))),
            },
            {
                "check": "leakage_policy",
                "item": "component_model_fit",
                "status": True,
                "detail": "fit on fold0 train baseline OOF components only; fold0 validation labels evaluation-only",
            },
        ]
    )
    write_csv(OUT_ROOT / "round14_reproducibility_gate.csv", rows)
    write_text(
        OUT_ROOT / "round14_reproducibility_gate.md",
        "\n".join(
            [
                "# Lane A Round14 Reproducibility Gate",
                "",
                *md_table(rows, ["check", "item", "status", "detail"]),
            ]
        )
        + "\n",
    )


def write_config_and_commands() -> None:
    write_text(
        OUT_ROOT / "round14_feature_calibrator_config.yaml",
        "\n".join(
            [
                "round: 14",
                "candidate: feature_augmented_component_aware_edema_calibrator",
                "baseline: nnUNet501 OOF probabilities/predictions",
                "class_scope: class_4_edema_only",
                "scar_policy: class_5_scar_unchanged_by_fusion",
                "no_t2_policy: weak stability only; no dense hard negative",
                "component_model:",
                "  type: logistic_regression_torch",
                "  train_split: fold0_train_baseline_components_only",
                "  eval_split: fold0_validation",
                "voxel_tiny_smoke:",
                "  type: tiny_mlp",
                "  max_samples_per_region: 256",
                "fold_training: not_submitted_by_this_diagnostic_script",
            ]
        )
        + "\n",
    )
    write_text(OUT_ROOT / "round14_train_commands.txt", "./envs/env_CARE/bin/python scripts/diagnostics/laneA_round14_feature_augmented_calibrator.py\n")


def write_goal_readme(stage_status: str) -> None:
    write_text(
        OUT_ROOT / "round14_goal_execution_readme.md",
        "\n".join(
            [
                "# Lane A Round14 Goal Execution Readme",
                "",
                "Executed stages:",
                "- `round14_reproducibility_and_feature_cache_gate`",
                "- `component_sample_dataset_construction`",
                "- `component_level_rule_and_model_smoke`",
                "- `voxel_patch_feature_calibrator_dataset_construction`",
                "- `feature_augmented_edema_calibrator_implementation` via lightweight smoke",
                "- `fusion_policy_and_evaluation_gate`",
                "- `round14_decision_and_round15_bridge`",
                "",
                "Not executed:",
                "- validation zip creation",
                "- upload",
                "- fold1-4 or 5-fold",
                "- external repo clone/build/train",
                "- whole nnU-Net training",
                "- nnU-Net baseline cache modification",
                "",
                f"Final gate status: `{stage_status}`",
                "",
                f"Output root: `{OUT_ROOT.relative_to(REPO_ROOT)}`",
            ]
        )
        + "\n",
    )


def focus_case_table(rows_by_model: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    focus = {"Case2031", "Case3011", "Case3012", "Case3040"}
    out = []
    for model, rows in rows_by_model.items():
        for row in rows:
            if row["case_id"] in focus:
                out.append(
                    {
                        "model": model,
                        "case_id": row["case_id"],
                        "center": row["center"],
                        "edema_dice": row.get("myops_edema_dice"),
                        "edema_hd95": row.get("myops_edema_hd95"),
                        "component_count": row.get("myops_edema_component_count"),
                        "remote_fp": row.get("myops_edema_remote_fp"),
                        "changed_voxels": row.get("changed_voxels"),
                        "added_voxels": row.get("added_voxels"),
                        "removed_voxels": row.get("removed_voxels"),
                        "scar_changed_voxels": row.get("scar_changed_voxels"),
                    }
                )
    write_csv(OUT_ROOT / "case2031_3011_3012_3040_table.csv", out)
    return out


def gate_status(grid_rows: list[dict[str, object]], component_summary: dict[str, object], voxel_row: dict[str, object]) -> tuple[str, list[str]]:
    by_model = {r["model"]: r for r in grid_rows if r["subset"] == "CenterC"}
    all_by_model = {r["model"]: r for r in grid_rows if r["subset"] == "all_case"}
    strict = by_model.get(STRICT_MODEL, {})
    logistic = by_model.get(COMP_LOGISTIC_MODEL, {})
    reasons: list[str] = []
    if component_summary.get("status") != "pass":
        return "stop_component_model_smoke_failed", [str(component_summary)]
    if voxel_row.get("status") != "pass" or voxel_row.get("nan_or_inf") is True:
        return "stop_voxel_tiny_smoke_failed", [str(voxel_row)]
    if safe_float(logistic.get("candidate_scar_changed_voxels")) != 0:
        return "stop_scar_guardrail_failed", ["component logistic changed scar"]
    if safe_float(all_by_model.get(COMP_LOGISTIC_MODEL, {}).get("candidate_no_t2_edema_fp_voxels")) > 0:
        return "stop_no_t2_fp_failed", ["component logistic introduced no-T2 edema FP"]
    logistic_centerc_dice = safe_float(logistic.get("delta_edema_dice"), -999)
    logistic_centerc_hd = safe_float(logistic.get("delta_edema_hd95_improvement"), -999)
    strict_centerc_remote = safe_float(strict.get("delta_edema_remote_fp_improvement"), 0)
    logistic_centerc_remote = safe_float(logistic.get("delta_edema_remote_fp_improvement"), -999)
    if logistic_centerc_remote < strict_centerc_remote:
        return "stop_less_safe_than_strict_support_filter", ["component logistic remote-FP safety is worse than strict_support_filter"]
    if logistic_centerc_dice > 0 and logistic_centerc_hd >= -0.05:
        return "watch_component_calibrator_tiny_signal", ["CenterC has weak clean signal; only very-short fold0 may be considered after user review"]
    reasons.append("no clean CenterC/T2-present improvement beyond strict_support_filter")
    return "watch_or_stop_feature_calibrator_no_training_expansion", reasons


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_config_and_commands()
    case_defs = build_cases()
    component_manifest = OUT_ROOT / "round14_component_dataset_manifest.csv"
    if component_manifest.is_file():
        comp_rows = read_csv(component_manifest)
        val_cases = [load_calib_case(case) for case in case_defs if case.fold0_split == "val"]
    else:
        comp_rows, val_cases = build_component_dataset_stream(case_defs)
    write_reproducibility_gate(case_defs, val_cases)
    comp_summary_rows = summarize_component_dataset(comp_rows)
    model, component_summary, mean_v, std_v = train_component_model(comp_rows)
    write_csv(OUT_ROOT / "round14_component_model_smoke.csv", [component_summary])
    preds, component_decisions = build_predictions(val_cases, model, mean_v, std_v)
    write_csv(OUT_ROOT / "component_accept_reject_summary.csv", component_decisions)

    rows_by_model = {name: evaluate_predictions(val_cases, pred, name) for name, pred in preds.items()}
    baseline_rows = rows_by_model[BASELINE_MODEL]
    comparisons: list[dict[str, object]] = []
    flags: list[dict[str, object]] = []
    for model_name in [ROUND11_MODEL, STRICT_MODEL, COMP_RULE_MODEL, COMP_LOGISTIC_MODEL]:
        comparisons.extend(compare_to_baseline(baseline_rows, rows_by_model[model_name], model_name))
        flags.extend(failure_flags(baseline_rows, rows_by_model[model_name], model_name))
    write_csv(OUT_ROOT / "round14_fusion_policy_grid.csv", comparisons)
    write_csv(OUT_ROOT / "baseline_vs_candidate_by_subset.csv", [r for r in comparisons if r["model"] == COMP_LOGISTIC_MODEL])
    write_csv(OUT_ROOT / "centerC_edema_table.csv", [r for r in comparisons if r["subset"] == "CenterC"])
    write_csv(OUT_ROOT / "no_t2_empty_gt_fp_table.csv", [r for r in rows_by_model[COMP_LOGISTIC_MODEL] if r["t2_present"] is False and r["edema_gt_positive"] is False])
    write_csv(OUT_ROOT / "scar_unchanged_guardrail_table.csv", [{"model": m, "scar_changed_voxels": sum(int(r["scar_changed_voxels"]) for r in rows)} for m, rows in rows_by_model.items()])
    write_csv(OUT_ROOT / "case_level_failure_flags.csv", flags)
    focus_case_table(rows_by_model)

    rule_smoke = [r for r in comparisons if r["model"] in {STRICT_MODEL, COMP_RULE_MODEL}]
    write_csv(OUT_ROOT / "round14_component_rule_smoke.csv", rule_smoke)

    voxel_manifest, voxel_row = run_voxel_tiny_smoke(case_defs)
    write_csv(OUT_ROOT / "round14_unit_gradient_smoke.csv", [voxel_row])
    write_csv(OUT_ROOT / "round14_tiny_overfit_metrics.csv", [voxel_row])
    for name in ["round14_fold0_very_short_metrics.csv", "round14_fold0_short_metrics.csv", "round14_fold0_longer_metrics.csv"]:
        write_csv(OUT_ROOT / name, [{"status": "not_run", "reason": "gated diagnostic/tiny smoke only; no Slurm submitted by this script"}])

    status, reasons = gate_status([r for r in comparisons if r["model"] in {STRICT_MODEL, COMP_LOGISTIC_MODEL}], component_summary, voxel_row)
    decision_rows = [
        {
            "route": "component_level_support_calibrator",
            "status": status,
            "evidence": "; ".join(reasons),
            "next_action": "review focus cases and strict_support_filter comparison before any fold0 Slurm",
        },
        {
            "route": "voxel_patch_feature_augmented_edema_calibrator",
            "status": voxel_row.get("status"),
            "evidence": f"loss_delta={voxel_row.get('loss_delta')}; nan_or_inf={voxel_row.get('nan_or_inf')}",
            "next_action": "do not train full nnU-Net; only bounded calibrator if component gate passes",
        },
        {
            "route": "strict_support_filter_as_safety_baseline",
            "status": "active_safety_comparator",
            "evidence": "Round13 strict filter remains minimum safety reference",
            "next_action": "learned candidates must be safer and more effective",
        },
        {
            "route": "external_method_bridge_for_round15",
            "status": "postpone_until_round14_decision",
            "evidence": "no external repo cloned or trained",
            "next_action": "metadata/one-case smoke only if first-party calibrator stops or shows specific missing mechanism",
        },
    ]
    write_csv(OUT_ROOT / "round14_decision_table.csv", decision_rows)
    write_text(
        OUT_ROOT / "round14_decision_table.md",
        "\n".join(
            [
                "# Lane A Round14 Decision Table",
                "",
                *md_table(decision_rows, ["route", "status", "evidence", "next_action"]),
                "",
                "## Fusion Policy Summary",
                "",
                *md_table(
                    comparisons,
                    [
                        "model",
                        "subset",
                        "delta_edema_dice",
                        "delta_edema_hd95_improvement",
                        "delta_edema_component_count_improvement",
                        "delta_edema_remote_fp_improvement",
                        "candidate_scar_changed_voxels",
                        "candidate_no_t2_edema_fp_voxels",
                    ],
                ),
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "round14_round15_recommendation.md",
        "\n".join(
            [
                "# Lane A Round14 to Round15 Recommendation",
                "",
                f"Final Round14 gate: `{status}`.",
                "",
                "Do not create a validation zip or upload from Round14.",
                "Do not expand to fold1-4/5-fold.",
                "If Round14 remains watch/stop, Round15 should bridge to the specific missing mechanism rather than more generic refiner epochs.",
                "",
                "Preferred Round15 order if needed:",
                "1. I-MMSeg-inspired intensity prior metadata/one-case smoke if intensity support is insufficient.",
                "2. Cascaded FSN/PT-Net-style anatomy-lesion consistency if component support is predictive but crude.",
                "3. InverseForm/surface/HD auxiliary only after support is safe.",
                "4. UniME/AdaMM/CoPeDiT/MoE only after missing-modality representation is the proven blocker.",
            ]
        )
        + "\n",
    )
    write_goal_readme(status)
    print(f"Wrote Round14 outputs to {OUT_ROOT}")
    print(f"Final gate: {status}")


if __name__ == "__main__":
    main()
