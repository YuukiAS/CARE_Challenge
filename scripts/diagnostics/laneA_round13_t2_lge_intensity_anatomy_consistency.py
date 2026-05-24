#!/usr/bin/env python3
"""Lane A Round13 T2/LGE intensity prior and anatomy consistency diagnostics.

This entrypoint is staged and diagnostic-first. It builds CARE-only intensity
and anatomy support features, evaluates deployable feature-only rules, and runs
a tiny feature-calibrator smoke only if the feature-only gate has signal. It
does not submit Slurm jobs, create validation zips, download weights, or modify
nnU-Net baseline caches.
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
    str(REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round13_t2_lge_intensity_anatomy_consistency/mpl_cache"),
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round04_fold0_short_train_eval as base_eval
from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, load_case_features, raw_modality_path, write_csv


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round13_t2_lge_intensity_anatomy_consistency"
FEATURE_ROOT = OUT_ROOT / "feature_cache"
OVERLAY_ROOT = OUT_ROOT / "overlays"
PLAN_PATH = REPO_ROOT / "docs/plans/laneA_round13_next_t2_lge_intensity_prior_anatomy_consistency_execution.md"
R12_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round12_refiner_salvage_high_upside_transition"
R11_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner"
R10_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round10_edema_refiner"
R11_PRED_DIR = R11_ROOT / "predictions/laneA_r11_bidirectional_edema_refiner_fold0_very_short/validation"

EDEMA = 4
SCAR = 5
BASELINE_MODEL = "baseline_nnunet501_fold0"
ROUND11_MODEL = "round11_bidirectional_refiner"

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


@dataclass(frozen=True)
class FeatureCase:
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
    feature_cache_path: Path


@dataclass(frozen=True)
class Rule:
    name: str
    description: str
    apply: Callable[[FeatureCase], np.ndarray]


ROUND11_ADDED_COMPONENT_CACHE: dict[str, list[tuple[np.ndarray, dict[str, object]]]] = {}


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


def finite(values: list[object]) -> list[float]:
    out: list[float] = []
    for value in values:
        number = safe_float(value, math.nan)
        if not math.isnan(number):
            out.append(number)
    return out


def avg(values: list[object]) -> float | None:
    vals = finite(values)
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


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def component_sizes(mask: np.ndarray) -> list[int]:
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return [int((cc == idx).sum()) for idx in range(1, n_cc + 1)]


def mean_dist_to_support(mask: np.ndarray, support: np.ndarray, spacing: tuple[float, float, float]) -> float | None:
    if not mask.any():
        return None
    if not support.any():
        return float("inf")
    dist = distance_transform_edt(~support.astype(bool), sampling=spacing)
    return float(dist[mask.astype(bool)].mean())


def min_dist_to_support(mask: np.ndarray, support: np.ndarray, spacing: tuple[float, float, float]) -> float | None:
    if not mask.any():
        return None
    if not support.any():
        return float("inf")
    dist = distance_transform_edt(~support.astype(bool), sampling=spacing)
    return float(dist[mask.astype(bool)].min())


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


def bbox_compactness(mask: np.ndarray) -> float | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    vol = int(np.prod(maxs - mins + 1))
    return float(mask.sum() / max(1, vol))


def region_stats(arr: np.ndarray, mask: np.ndarray, prefix: str) -> dict[str, object]:
    if not mask.any():
        return {
            f"{prefix}_n": 0,
            f"{prefix}_mean": None,
            f"{prefix}_p25": None,
            f"{prefix}_p50": None,
            f"{prefix}_p75": None,
        }
    vals = arr[mask.astype(bool)].astype(np.float64, copy=False)
    return {
        f"{prefix}_n": int(vals.size),
        f"{prefix}_mean": float(vals.mean()),
        f"{prefix}_p25": float(np.percentile(vals, 25)),
        f"{prefix}_p50": float(np.percentile(vals, 50)),
        f"{prefix}_p75": float(np.percentile(vals, 75)),
    }


def load_feature_case(case: RefinerCase) -> FeatureCase:
    features, _, baseline, gt_img = load_case_features(case)
    gt = sitk.GetArrayFromImage(sitk.ReadImage(str(case.gt_path))).astype(np.uint8, copy=False)
    round11 = base_eval.read_pred(R11_PRED_DIR / f"{case.case_id}.nii.gz", gt_img)
    probs = features[:6].astype(np.float32, copy=False)
    c0 = features[6].astype(np.float32, copy=False)
    lge = features[7].astype(np.float32, copy=False)
    t2 = features[8].astype(np.float32, copy=False)
    anatomy = features[-1].astype(np.float32, copy=False)
    anatomy_mask = anatomy >= 0.05
    if case.t2_present:
        t2_pct = robust_percentile_support(t2, anatomy_mask)
        t2_z = robust_z_support(t2, anatomy_mask)
        t2_support = (0.5 * t2_pct + 0.5 * t2_z).astype(np.float32)
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
    FEATURE_ROOT.mkdir(parents=True, exist_ok=True)
    cache_path = FEATURE_ROOT / f"{case.case_id}_round13_features.npz"
    np.savez_compressed(
        cache_path,
        t2_support=t2_support,
        lge_support=lge_support,
        t2_lge_contrast=t2_lge_contrast,
        entropy=entropy,
        edema_margin=edema_margin,
        support_score=support_score,
        anatomy_support=anatomy,
        baseline_edema_prob=probs[EDEMA],
    )
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    return FeatureCase(
        case=case,
        gt_img=gt_img,
        gt=gt,
        baseline=baseline.astype(np.uint8, copy=False),
        round11=round11.astype(np.uint8, copy=False),
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
        feature_cache_path=cache_path,
    )


def load_all_feature_cases() -> list[FeatureCase]:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    cases = [c for c in build_cases() if c.fold0_split == "val"]
    return [load_feature_case(case) for case in cases]


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


def class_row(fc: FeatureCase, pred: np.ndarray, model: str) -> dict[str, object]:
    row: dict[str, object] = {
        "model": model,
        "case_id": fc.case.case_id,
        "missing_prediction": False,
        "center": fc.case.center,
        "modality_group": fc.case.modality_group,
        "t2_present": fc.case.t2_present,
        "edema_gt_positive": fc.case.edema_gt_positive,
        "scar_gt_positive": fc.case.scar_gt_positive,
    }
    row.update(base_eval.class_metrics(pred, fc.gt, fc.spacing, EDEMA, "myops_edema"))
    row.update(base_eval.class_metrics(pred, fc.gt, fc.spacing, SCAR, "myops_scar"))
    return row


def evaluate_predictions(cases: list[FeatureCase], predictions: dict[str, np.ndarray], model: str) -> list[dict[str, object]]:
    return [class_row(fc, predictions[fc.case.case_id], model) for fc in cases]


def clone_metric_row(row: dict[str, object], model: str) -> dict[str, object]:
    out = dict(row)
    out["model"] = model
    return out


def evaluate_predictions_with_references(
    cases: list[FeatureCase],
    predictions: dict[str, np.ndarray],
    model: str,
    baseline_rows_by_case: dict[str, dict[str, object]],
    round11_rows_by_case: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for fc in cases:
        case_id = fc.case.case_id
        pred = predictions[case_id]
        if np.array_equal(pred, fc.baseline):
            rows.append(clone_metric_row(baseline_rows_by_case[case_id], model))
        elif np.array_equal(pred, fc.round11):
            rows.append(clone_metric_row(round11_rows_by_case[case_id], model))
        else:
            rows.append(class_row(fc, pred, model))
    return rows


def aggregate(rows: list[dict[str, object]], model: str, subset: str) -> dict[str, object]:
    filt = subset_filter(subset)
    items = [r for r in rows if r["model"] == model and not r.get("missing_prediction") and filt(r)]
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
                "delta_edema_component_count_improvement": delta(
                    c["myops_edema_component_count"], b["myops_edema_component_count"], lower_is_better=True
                ),
                "baseline_edema_remote_fp": b["myops_edema_remote_fp"],
                "candidate_edema_remote_fp": c["myops_edema_remote_fp"],
                "delta_edema_remote_fp_improvement": delta(c["myops_edema_remote_fp"], b["myops_edema_remote_fp"], lower_is_better=True),
                "baseline_scar_dice": b["myops_scar_dice"],
                "candidate_scar_dice": c["myops_scar_dice"],
                "delta_scar_dice": delta(c["myops_scar_dice"], b["myops_scar_dice"]),
                "baseline_scar_hd95": b["myops_scar_hd95"],
                "candidate_scar_hd95": c["myops_scar_hd95"],
                "delta_scar_hd95_improvement": delta(c["myops_scar_hd95"], b["myops_scar_hd95"], lower_is_better=True),
            }
        )
    return out


def failure_flags(baseline_rows: list[dict[str, object]], candidate_rows: list[dict[str, object]], model: str) -> list[dict[str, object]]:
    by_base = {str(r["case_id"]): r for r in baseline_rows}
    out: list[dict[str, object]] = []
    for c in sorted(candidate_rows, key=lambda r: str(r["case_id"])):
        cid = str(c["case_id"])
        b = by_base[cid]
        flags: list[str] = []
        d_dice = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        d_hd95 = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        d_comp = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        d_remote = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        d_scar_dice = delta(c.get("myops_scar_dice"), b.get("myops_scar_dice"))
        d_scar_hd95 = delta(c.get("myops_scar_hd95"), b.get("myops_scar_hd95"), lower_is_better=True)
        if d_dice is not None and d_dice > 0.005 and d_hd95 is not None and d_hd95 < -0.5:
            flags.append("edema_dice_up_hd95_worse")
        if d_comp is not None and d_comp < -0.5:
            flags.append("edema_component_worse")
        if d_remote is not None and d_remote < 0:
            flags.append("edema_remote_fp_worse")
        if c.get("t2_present") is False and c.get("edema_gt_positive") is False:
            if safe_float(c.get("myops_edema_component_count")) > safe_float(b.get("myops_edema_component_count")):
                flags.append("no_t2_empty_gt_new_edema_fp")
        if d_scar_dice is not None and d_scar_dice < -1e-8:
            flags.append("scar_dice_changed")
        if d_scar_hd95 is not None and abs(d_scar_hd95) > 1e-8:
            flags.append("scar_hd95_changed")
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
                "delta_scar_dice": d_scar_dice,
                "delta_scar_hd95_improvement": d_scar_hd95,
                "flags": ";".join(flags),
            }
        )
    return out


def write_reproducibility_gate(cases: list[FeatureCase]) -> None:
    required = [
        PLAN_PATH,
        R12_ROOT / "round12_decision_table.md",
        R12_ROOT / "round12_round13_recommendation.md",
        R12_ROOT / "round12_t2_lge_intensity_prior_audit.csv",
        R12_ROOT / "round12_anatomy_lesion_consistency_audit.csv",
        R12_ROOT / "round12_deployable_fallback_proxy_grid.csv",
        R10_ROOT / "round10_fold0_very_short_metrics.csv",
        R11_ROOT / "round11_fold0_very_short_metrics.csv",
    ]
    rows = [{"check": "required_file_exists", "item": str(p.relative_to(REPO_ROOT)), "status": p.is_file(), "detail": ""} for p in required]
    rows.extend(
        [
            {"check": "fold0_val_feature_cases", "item": "feature_cases", "status": len(cases) == 44, "detail": len(cases)},
            {
                "check": "label_semantics",
                "item": "compact labels",
                "status": sorted(set(int(x) for fc in cases for x in np.unique(fc.gt))) == [0, 1, 2, 3, 4, 5],
                "detail": "background, myocardium, LV, RV, edema=4, scar=5",
            },
            {
                "check": "round11_predictions_available",
                "item": str(R11_PRED_DIR.relative_to(REPO_ROOT)),
                "status": len(list(R11_PRED_DIR.glob("*.nii.gz"))) == 44,
                "detail": len(list(R11_PRED_DIR.glob("*.nii.gz"))),
            },
        ]
    )
    write_csv(OUT_ROOT / "round13_reproducibility_gate.csv", rows)
    manifest_rows = []
    for fc in cases:
        manifest_rows.append(
            {
                "case_id": fc.case.case_id,
                "center": fc.case.center,
                "modality_group": fc.case.modality_group,
                "C0_present": fc.case.c0_present,
                "LGE_present": fc.case.lge_present,
                "T2_present": fc.case.t2_present,
                "edema_gt_positive": fc.case.edema_gt_positive,
                "scar_gt_positive": fc.case.scar_gt_positive,
                "gt_path": str(fc.case.gt_path),
                "baseline_prediction_path": str(fc.case.prediction_path),
                "baseline_probability_path": str(fc.case.probability_path),
                "raw_c0_path": str(raw_modality_path(fc.case, "C0")),
                "raw_lge_path": str(raw_modality_path(fc.case, "LGE")),
                "raw_t2_path": str(raw_modality_path(fc.case, "T2")),
                "feature_cache_path": str(fc.feature_cache_path),
                "shape_zyx": "x".join(map(str, fc.gt.shape)),
                "spacing_zyx": "x".join(f"{v:.6g}" for v in fc.spacing),
            }
        )
    write_csv(OUT_ROOT / "round13_feature_source_manifest.csv", manifest_rows)


def write_feature_configs() -> None:
    write_text(
        OUT_ROOT / "t2_lge_intensity_feature_config.yaml",
        "\n".join(
            [
                "round: 13",
                "feature_scope: fold0_validation",
                "external_data: false",
                "normalized_T2_support:",
                "  present_cases: robust percentile plus robust sigmoid-z within baseline anatomy support",
                "  no_t2_cases: neutral 0.5 map plus explicit T2_present=false",
                "LGE_T2_contrast_feature: t2_support - lge_support when T2 present, otherwise zero with missing-state flag",
                "baseline_uncertainty_intensity_feature:",
                "  entropy: normalized all-class entropy from nnU-Net probabilities",
                "  edema_margin: class_4_probability - max_other_class_probability",
                "  support_score: weighted T2 support, LGE support, edema margin, edema probability, anatomy support",
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "anatomy_lesion_consistency_feature_config.yaml",
        "\n".join(
            [
                "round: 13",
                "feature_scope: fold0_validation",
                "hard_roi_deletion: false",
                "simple_distance_attenuation: false",
                "anatomy_source: nnU-Net baseline classes 1/2/3 probabilities and hard baseline support",
                "component_features:",
                "  - component size",
                "  - distance to hard anatomy",
                "  - distance to baseline edema",
                "  - distance to high T2 support",
                "  - component compactness",
                "  - T2/LGE/support-score means",
                "deployable_rule_selection: no GT, no case ID, no hosted feedback",
            ]
        )
        + "\n",
    )


def feature_summary_rows(cases: list[FeatureCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for fc in cases:
        gt_edema = fc.gt == EDEMA
        baseline_edema = fc.baseline == EDEMA
        round11_edema = fc.round11 == EDEMA
        masks = {
            "gt_edema": gt_edema,
            "baseline_tp": baseline_edema & gt_edema,
            "baseline_fp": baseline_edema & ~gt_edema,
            "baseline_fn": gt_edema & ~baseline_edema,
            "round11_added_all": round11_edema & ~baseline_edema,
            "round11_added_fp": round11_edema & ~baseline_edema & ~gt_edema,
            "round11_added_gt_overlap": round11_edema & ~baseline_edema & gt_edema,
        }
        for region, mask in masks.items():
            row: dict[str, object] = {
                "case_id": fc.case.case_id,
                "center": fc.case.center,
                "modality_group": fc.case.modality_group,
                "t2_present": fc.case.t2_present,
                "edema_gt_positive": fc.case.edema_gt_positive,
                "region": region,
                "voxels": int(mask.sum()),
            }
            for arr, prefix in [
                (fc.t2_support, "t2_support"),
                (fc.lge_support, "lge_support"),
                (fc.t2_lge_contrast, "t2_lge_contrast"),
                (fc.entropy, "entropy"),
                (fc.edema_margin, "edema_margin"),
                (fc.support_score, "support_score"),
                (fc.anatomy, "anatomy_support"),
                (fc.probs[EDEMA], "baseline_edema_prob"),
            ]:
                row.update(region_stats(arr, mask, prefix))
            rows.append(row)
    write_csv(OUT_ROOT / "t2_lge_intensity_feature_summary.csv", rows)
    return rows


def separability_rows(summary_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    features = ["t2_support", "lge_support", "t2_lge_contrast", "entropy", "edema_margin", "support_score", "anatomy_support", "baseline_edema_prob"]
    comparisons = [
        ("gt_edema", "round11_added_fp"),
        ("gt_edema", "baseline_fp"),
        ("baseline_tp", "baseline_fp"),
        ("round11_added_gt_overlap", "round11_added_fp"),
    ]
    groups = ["all", "CenterB", "CenterC", "t2_present"]
    out: list[dict[str, object]] = []
    for group in groups:
        if group == "all":
            rows = summary_rows
        elif group == "t2_present":
            rows = [r for r in summary_rows if str(r.get("t2_present")).lower() == "true"]
        else:
            rows = [r for r in summary_rows if r.get("center") == group]
        for pos, neg in comparisons:
            for feat in features:
                pos_vals = [r.get(f"{feat}_mean") for r in rows if r.get("region") == pos and safe_float(r.get("voxels")) > 0]
                neg_vals = [r.get(f"{feat}_mean") for r in rows if r.get("region") == neg and safe_float(r.get("voxels")) > 0]
                pos_mean = avg(pos_vals)
                neg_mean = avg(neg_vals)
                gap = None if pos_mean is None or neg_mean is None else pos_mean - neg_mean
                out.append(
                    {
                        "group": group,
                        "positive_region": pos,
                        "negative_region": neg,
                        "feature": feat,
                        "positive_n": len(finite(pos_vals)),
                        "negative_n": len(finite(neg_vals)),
                        "positive_mean": pos_mean,
                        "negative_mean": neg_mean,
                        "mean_gap_positive_minus_negative": gap,
                        "abs_gap": abs(gap) if gap is not None else None,
                    }
                )
    write_csv(OUT_ROOT / "t2_lge_intensity_separability.csv", out)
    return out


def center_comparison_rows(summary_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for center in ["CenterB", "CenterC"]:
        rows = [r for r in summary_rows if r.get("center") == center and str(r.get("t2_present")).lower() == "true"]
        for region in sorted(set(str(r.get("region")) for r in rows)):
            items = [r for r in rows if r.get("region") == region and safe_float(r.get("voxels")) > 0]
            out.append(
                {
                    "center": center,
                    "region": region,
                    "n_regions": len(items),
                    "mean_t2_support": avg([r.get("t2_support_mean") for r in items]),
                    "mean_lge_support": avg([r.get("lge_support_mean") for r in items]),
                    "mean_t2_lge_contrast": avg([r.get("t2_lge_contrast_mean") for r in items]),
                    "mean_support_score": avg([r.get("support_score_mean") for r in items]),
                    "mean_baseline_edema_prob": avg([r.get("baseline_edema_prob_mean") for r in items]),
                }
            )
    write_csv(OUT_ROOT / "centerB_centerC_intensity_comparison.csv", out)
    write_text(
        OUT_ROOT / "centerB_centerC_intensity_comparison.md",
        "\n".join(
            [
                "# Lane A Round13 CenterB/CenterC Intensity Comparison",
                "",
                "Scope: fold0 validation T2-present cases. no-T2 cases are tracked separately and do not receive fake T2 support.",
                "",
                *md_table(out, ["center", "region", "n_regions", "mean_t2_support", "mean_t2_lge_contrast", "mean_support_score", "mean_baseline_edema_prob"]),
            ]
        )
        + "\n",
    )
    return out


def round11_added_component_attrs(fc: FeatureCase) -> list[tuple[np.ndarray, dict[str, object]]]:
    cached = ROUND11_ADDED_COMPONENT_CACHE.get(fc.case.case_id)
    if cached is not None:
        return cached
    baseline_edema = fc.baseline == EDEMA
    round11_added = (fc.round11 == EDEMA) & ~baseline_edema
    hard_anatomy = np.isin(fc.baseline, [1, 2, 3])
    high_t2 = fc.t2_support >= 0.55 if fc.case.t2_present else np.zeros_like(fc.t2_support, dtype=bool)
    gt_edema = fc.gt == EDEMA
    dist_anatomy = distance_map_to_support(hard_anatomy, fc.spacing)
    dist_baseline_edema = distance_map_to_support(baseline_edema, fc.spacing)
    dist_high_t2 = distance_map_to_support(high_t2, fc.spacing) if fc.case.t2_present else None
    cc, n_cc = label(round11_added.astype(bool), structure=generate_binary_structure(3, 1))
    components: list[tuple[np.ndarray, dict[str, object]]] = []
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        attrs: dict[str, object] = {
            "component_index": idx,
            "component_voxels": int(comp.sum()),
            "component_compactness": bbox_compactness(comp),
            "gt_overlap_voxels": int((comp & gt_edema).sum()),
            "distance_to_hard_anatomy_mm": min_dist_from_map(comp, dist_anatomy),
            "distance_to_baseline_edema_mm": min_dist_from_map(comp, dist_baseline_edema),
            "distance_to_high_t2_support_mm": min_dist_from_map(comp, dist_high_t2) if fc.case.t2_present else None,
            "mean_t2_support": float(fc.t2_support[comp].mean()) if comp.any() else 0.0,
            "mean_lge_support": float(fc.lge_support[comp].mean()) if comp.any() else 0.0,
            "mean_t2_lge_contrast": float(fc.t2_lge_contrast[comp].mean()) if comp.any() else 0.0,
            "mean_support_score": float(fc.support_score[comp].mean()) if comp.any() else 0.0,
            "mean_anatomy_support": float(fc.anatomy[comp].mean()) if comp.any() else 0.0,
            "mean_baseline_edema_prob": float(fc.probs[EDEMA][comp].mean()) if comp.any() else 0.0,
            "mean_edema_margin": float(fc.edema_margin[comp].mean()) if comp.any() else 0.0,
        }
        components.append((comp, attrs))
    ROUND11_ADDED_COMPONENT_CACHE[fc.case.case_id] = components
    return components


def component_support_rows(cases: list[FeatureCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for fc in cases:
        for comp, attrs in round11_added_component_attrs(fc):
            row = {
                "case_id": fc.case.case_id,
                "center": fc.case.center,
                "modality_group": fc.case.modality_group,
                "t2_present": fc.case.t2_present,
                "edema_gt_positive": fc.case.edema_gt_positive,
            }
            row.update(attrs)
            plausibility = []
            if safe_float(row["distance_to_baseline_edema_mm"], 999.0) > 8.0:
                plausibility.append("remote_from_baseline_edema")
            if fc.case.t2_present and safe_float(row["mean_t2_support"]) < 0.45:
                plausibility.append("weak_t2_support")
            if safe_float(row["mean_support_score"]) < 0.45:
                plausibility.append("weak_combined_support")
            if safe_float(row["mean_baseline_edema_prob"]) < 0.28:
                plausibility.append("weak_baseline_edema_prob")
            row["plausibility_flags"] = ";".join(plausibility)
            rows.append(row)
    write_csv(OUT_ROOT / "component_support_consistency_table.csv", rows)
    write_csv(OUT_ROOT / "anatomy_lesion_consistency_feature_manifest.csv", rows)
    return rows


def clone_baseline(fc: FeatureCase) -> np.ndarray:
    return fc.baseline.copy()


def remove_round11_added_components(fc: FeatureCase, reject: Callable[[dict[str, object]], bool]) -> np.ndarray:
    pred = fc.round11.copy()
    for comp, attrs in round11_added_component_attrs(fc):
        if reject(attrs):
            pred[comp] = fc.baseline[comp]
    return pred


def round12_baseline_prob_weak_or_remote(fc: FeatureCase) -> np.ndarray:
    pred = remove_round11_added_components(
        fc,
        lambda a: safe_float(a["distance_to_baseline_edema_mm"], 999.0) > 8.0
        or safe_float(a["mean_baseline_edema_prob"]) < 0.28,
    )
    return pred


def build_rules() -> list[Rule]:
    return [
        Rule("baseline", "nnU-Net501 fold0 baseline; reference only.", lambda fc: fc.baseline.copy()),
        Rule("round11_refiner", "Round11 bidirectional refiner; reference only.", lambda fc: fc.round11.copy()),
        Rule("round12_baseline_prob_weak_or_remote_proxy", "Round12 deployable fallback proxy at component level.", round12_baseline_prob_weak_or_remote),
        Rule(
            "intensity_t2_support_filter",
            "Remove Round11 added components with weak T2 support or remote from high-T2 support.",
            lambda fc: remove_round11_added_components(
                fc,
                lambda a: (fc.case.t2_present and safe_float(a["mean_t2_support"]) < 0.45)
                or (fc.case.t2_present and safe_float(a["distance_to_high_t2_support_mm"], 999.0) > 6.0),
            ),
        ),
        Rule(
            "anatomy_component_consistency_filter",
            "Remove Round11 added components with weak anatomy support or far from anatomy/baseline edema.",
            lambda fc: remove_round11_added_components(
                fc,
                lambda a: safe_float(a["mean_anatomy_support"]) < 0.05
                or safe_float(a["distance_to_hard_anatomy_mm"], 999.0) > 5.0
                or safe_float(a["distance_to_baseline_edema_mm"], 999.0) > 8.0,
            ),
        ),
        Rule(
            "combined_support_score_filter",
            "Remove Round11 added components with weak combined intensity/anatomy/probability support.",
            lambda fc: remove_round11_added_components(
                fc,
                lambda a: safe_float(a["mean_support_score"]) < 0.45
                or safe_float(a["mean_baseline_edema_prob"]) < 0.28
                or safe_float(a["distance_to_baseline_edema_mm"], 999.0) > 8.0,
            ),
        ),
        Rule(
            "strict_support_filter",
            "Strict support filter for diagnostics; expected to be safer but may erase true additions.",
            lambda fc: remove_round11_added_components(
                fc,
                lambda a: safe_float(a["mean_support_score"]) < 0.50
                or (fc.case.t2_present and safe_float(a["mean_t2_support"]) < 0.50)
                or safe_float(a["mean_baseline_edema_prob"]) < 0.30
                or safe_float(a["distance_to_baseline_edema_mm"], 999.0) > 5.0,
            ),
        ),
    ]


def rule_predictions(cases: list[FeatureCase], rule: Rule) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for fc in cases:
        pred = rule.apply(fc).astype(np.uint8, copy=False)
        if int(np.logical_xor(fc.baseline == SCAR, pred == SCAR).sum()) != 0:
            raise RuntimeError(f"{rule.name} changed scar in {fc.case.case_id}")
        out[fc.case.case_id] = pred
    return out


def run_feature_only_grid(cases: list[FeatureCase]) -> tuple[list[dict[str, object]], list[dict[str, object]], str | None]:
    baseline_rows = evaluate_predictions(cases, {fc.case.case_id: fc.baseline.copy() for fc in cases}, BASELINE_MODEL)
    round11_rows = evaluate_predictions(cases, {fc.case.case_id: fc.round11.copy() for fc in cases}, ROUND11_MODEL)
    baseline_rows_by_case = {str(r["case_id"]): r for r in baseline_rows}
    round11_rows_by_case = {str(r["case_id"]): r for r in round11_rows}
    grid_rows: list[dict[str, object]] = []
    all_flags: list[dict[str, object]] = []
    best_rule: str | None = None
    best_score = -1e9
    best_comparison: list[dict[str, object]] = []
    best_candidate_rows: list[dict[str, object]] = []
    for rule in build_rules():
        model = f"rule:{rule.name}"
        preds = rule_predictions(cases, rule)
        candidate_rows = evaluate_predictions_with_references(cases, preds, model, baseline_rows_by_case, round11_rows_by_case)
        comparison = compare_to_baseline(baseline_rows, candidate_rows, model)
        flags = failure_flags(baseline_rows, candidate_rows, model)
        by_subset = {row["subset"]: row for row in comparison}
        hard_flags = [f for f in flags if f.get("flags")]
        changed_cases = sum(1 for fc in cases if np.any(preds[fc.case.case_id] != fc.baseline))
        row = {
            "rule": rule.name,
            "description": rule.description,
            "changed_cases": changed_cases,
            "hard_flag_count": len(hard_flags),
            "flagged_cases": ";".join(f"{f['case_id']}:{f['flags']}" for f in hard_flags[:20]),
            "all_case_delta_edema_dice": by_subset["all_case"]["delta_edema_dice"],
            "all_case_delta_edema_hd95_improvement": by_subset["all_case"]["delta_edema_hd95_improvement"],
            "t2_gtpos_delta_edema_dice": by_subset["t2_present_gt_positive"]["delta_edema_dice"],
            "t2_gtpos_delta_edema_hd95_improvement": by_subset["t2_present_gt_positive"]["delta_edema_hd95_improvement"],
            "t2_gtpos_delta_component_improvement": by_subset["t2_present_gt_positive"]["delta_edema_component_count_improvement"],
            "t2_gtpos_delta_remote_fp_improvement": by_subset["t2_present_gt_positive"]["delta_edema_remote_fp_improvement"],
            "centerB_delta_edema_dice": by_subset["CenterB"]["delta_edema_dice"],
            "centerB_delta_edema_hd95_improvement": by_subset["CenterB"]["delta_edema_hd95_improvement"],
            "centerC_delta_edema_dice": by_subset["CenterC"]["delta_edema_dice"],
            "centerC_delta_edema_hd95_improvement": by_subset["CenterC"]["delta_edema_hd95_improvement"],
            "centerC_delta_component_improvement": by_subset["CenterC"]["delta_edema_component_count_improvement"],
            "centerC_delta_remote_fp_improvement": by_subset["CenterC"]["delta_edema_remote_fp_improvement"],
            "no_t2_empty_delta_component_improvement": by_subset["no_t2_empty_gt"]["delta_edema_component_count_improvement"],
            "delta_scar_dice_all": by_subset["all_case"]["delta_scar_dice"],
            "delta_scar_hd95_improvement_all": by_subset["all_case"]["delta_scar_hd95_improvement"],
        }
        grid_rows.append(row)
        all_flags.extend(flags)
        eligible = (
            rule.name not in {"baseline", "round11_refiner"}
            and len(hard_flags) == 0
            and safe_float(row["no_t2_empty_delta_component_improvement"]) >= 0
            and safe_float(row["centerC_delta_remote_fp_improvement"]) >= 0
            and safe_float(row["centerC_delta_component_improvement"]) >= 0
            and safe_float(row["delta_scar_dice_all"]) >= -1e-8
            and abs(safe_float(row["delta_scar_hd95_improvement_all"])) <= 1e-8
            and max(safe_float(row["t2_gtpos_delta_edema_dice"]), safe_float(row["centerC_delta_edema_dice"])) >= 0
        )
        score = (
            safe_float(row["t2_gtpos_delta_edema_dice"])
            + safe_float(row["centerC_delta_edema_dice"])
            + 0.001 * safe_float(row["t2_gtpos_delta_edema_hd95_improvement"])
            + 0.001 * safe_float(row["centerC_delta_edema_hd95_improvement"])
        )
        if eligible and score > best_score:
            best_score = score
            best_rule = rule.name
            best_comparison = comparison
            best_candidate_rows = candidate_rows
    write_csv(OUT_ROOT / "feature_only_rule_grid.csv", grid_rows)
    write_csv(OUT_ROOT / "case_level_failure_flags.csv", all_flags)
    if best_rule:
        best_rule_obj = next(r for r in build_rules() if r.name == best_rule)
        best_preds = rule_predictions(cases, best_rule_obj)
        write_csv(OUT_ROOT / "baseline_vs_round13_by_subset.csv", best_comparison)
        write_csv(OUT_ROOT / "no_t2_empty_gt_fp_table.csv", [r for r in best_candidate_rows if r.get("t2_present") is False and r.get("edema_gt_positive") is False])
        write_csv(
            OUT_ROOT / "scar_guardrail_table.csv",
            [
                {
                    "case_id": fc.case.case_id,
                    "scar_changed_voxels": int(np.logical_xor(fc.baseline == SCAR, best_preds[fc.case.case_id] == SCAR).sum()),
                }
                for fc in cases
            ],
        )
    else:
        write_csv(OUT_ROOT / "baseline_vs_round13_by_subset.csv", [])
        write_csv(OUT_ROOT / "no_t2_empty_gt_fp_table.csv", [])
        write_csv(OUT_ROOT / "scar_guardrail_table.csv", [])
    write_text(
        OUT_ROOT / "feature_only_rule_grid.md",
        "\n".join(
            [
                "# Lane A Round13 Feature-Only Rule Grid",
                "",
                f"Best eligible deployable feature rule: `{best_rule or 'none'}`",
                "",
                "Rules only remove/refuse Round11 added edema components using intensity/anatomy/probability support; no GT/case IDs/hosted feedback are used for rule selection.",
                "",
                *md_table(
                    grid_rows,
                    [
                        "rule",
                        "hard_flag_count",
                        "t2_gtpos_delta_edema_dice",
                        "t2_gtpos_delta_edema_hd95_improvement",
                        "centerC_delta_edema_dice",
                        "centerC_delta_edema_hd95_improvement",
                        "centerC_delta_remote_fp_improvement",
                        "flagged_cases",
                    ],
                ),
            ]
        )
        + "\n",
    )
    return grid_rows, all_flags, best_rule


def feature_gate_status(grid_rows: list[dict[str, object]], best_rule: str | None) -> tuple[str, list[str]]:
    if not best_rule:
        return "stop_feature_only_no_clean_deployable_rule", ["no clean deployable feature-only rule passed"]
    row = next(r for r in grid_rows if r["rule"] == best_rule)
    strong = (
        safe_float(row["t2_gtpos_delta_edema_dice"]) > 0.002
        and safe_float(row["t2_gtpos_delta_edema_hd95_improvement"]) >= -0.05
        and safe_float(row["centerC_delta_remote_fp_improvement"]) >= 0
    )
    if strong:
        return "go_feature_augmented_calibrator_smoke", [f"`{best_rule}` has clean support-aware signal"]
    return "watch_feature_augmented_calibrator_smoke", [f"`{best_rule}` is clean but signal is weak; only tiny smoke allowed"]


def sample_voxel_rows(cases: list[FeatureCase], max_per_region: int = 256) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(13)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    case_ids: list[str] = []
    for fc in cases:
        if fc.case.t2_present and fc.case.edema_gt_positive:
            positive = np.argwhere(fc.gt == EDEMA)
            hard_neg = np.argwhere(((fc.round11 == EDEMA) | (fc.baseline == EDEMA)) & (fc.gt != EDEMA))
        elif (not fc.case.t2_present) and (not fc.case.edema_gt_positive):
            positive = np.empty((0, 3), dtype=int)
            hard_neg = np.argwhere((fc.round11 == EDEMA) | (fc.baseline == EDEMA))
        else:
            positive = np.empty((0, 3), dtype=int)
            hard_neg = np.argwhere((fc.round11 == EDEMA) & (fc.gt != EDEMA))
        for coords, target in [(positive, 1.0), (hard_neg, 0.0)]:
            if coords.size == 0:
                continue
            take = coords
            if len(coords) > max_per_region:
                take = coords[rng.choice(len(coords), max_per_region, replace=False)]
            z, y, x = take[:, 0], take[:, 1], take[:, 2]
            feat = np.stack(
                [
                    fc.t2_support[z, y, x],
                    fc.lge_support[z, y, x],
                    fc.t2_lge_contrast[z, y, x],
                    fc.entropy[z, y, x],
                    fc.edema_margin[z, y, x],
                    fc.support_score[z, y, x],
                    fc.anatomy[z, y, x],
                    fc.probs[EDEMA][z, y, x],
                    np.full(len(take), 1.0 if fc.case.t2_present else 0.0, dtype=np.float32),
                ],
                axis=1,
            )
            xs.append(feat.astype(np.float32))
            ys.append(np.full(len(take), target, dtype=np.float32))
            case_ids.extend([fc.case.case_id] * len(take))
    if not xs:
        return np.zeros((0, 9), dtype=np.float32), np.zeros((0,), dtype=np.float32), []
    return np.concatenate(xs, axis=0), np.concatenate(ys, axis=0), case_ids


def run_feature_augmented_smoke(cases: list[FeatureCase], gate_status: str) -> None:
    write_text(
        OUT_ROOT / "feature_augmented_refiner_config.yaml",
        "\n".join(
            [
                "round: 13",
                "candidate: feature_augmented_edema_only_calibrator_smoke",
                "model: one-layer voxel calibrator diagnostic, not production model",
                "features: [t2_support,lge_support,t2_lge_contrast,entropy,edema_margin,support_score,anatomy_support,baseline_edema_prob,T2_present]",
                "scar_immutable: true",
                "no_t2_policy: no fake T2 support; no-T2 cases included only as stability controls",
                f"feature_only_gate_status: {gate_status}",
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "feature_augmented_refiner_commands.txt",
        "./envs/env_CARE/bin/python scripts/diagnostics/laneA_round13_t2_lge_intensity_anatomy_consistency.py\n",
    )
    if not gate_status.endswith("calibrator_smoke"):
        rows = [{"status": "not_run", "reason": gate_status}]
        write_csv(OUT_ROOT / "feature_augmented_unit_gradient_smoke.csv", rows)
        write_csv(OUT_ROOT / "feature_augmented_tiny_overfit_metrics.csv", rows)
        write_csv(OUT_ROOT / "feature_augmented_fold0_very_short_metrics.csv", [{"status": "not_run", "reason": "no Slurm/full training in this diagnostic"}])
        write_csv(OUT_ROOT / "feature_augmented_fold0_short_metrics.csv", [{"status": "not_run", "reason": "no Slurm/full training in this diagnostic"}])
        return
    x_np, y_np, case_ids = sample_voxel_rows(cases)
    if x_np.shape[0] == 0 or len(np.unique(y_np)) < 2:
        rows = [{"status": "fail", "reason": "insufficient positive/negative samples", "n_samples": x_np.shape[0]}]
        write_csv(OUT_ROOT / "feature_augmented_unit_gradient_smoke.csv", rows)
        write_csv(OUT_ROOT / "feature_augmented_tiny_overfit_metrics.csv", rows)
        return
    torch.manual_seed(13)
    x = torch.from_numpy(x_np)
    y = torch.from_numpy(y_np[:, None])
    model = torch.nn.Sequential(torch.nn.Linear(x.shape[1], 1))
    opt = torch.optim.AdamW(model.parameters(), lr=0.05, weight_decay=1e-4)
    with torch.no_grad():
        initial_loss = float(torch.nn.functional.binary_cross_entropy_with_logits(model(x), y))
    losses: list[float] = []
    grad_norms: list[float] = []
    finite_ok = True
    for _ in range(80):
        opt.zero_grad(set_to_none=True)
        logits = model(x)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, y)
        if not torch.isfinite(loss):
            finite_ok = False
            break
        loss.backward()
        grad_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                grad_norm += float(p.grad.detach().norm())
        opt.step()
        losses.append(float(loss.detach()))
        grad_norms.append(grad_norm)
    with torch.no_grad():
        logits = model(x)
        probs = torch.sigmoid(logits).numpy().ravel()
        final_loss = float(torch.nn.functional.binary_cross_entropy_with_logits(logits, y))
    pos_mean = float(probs[y_np > 0.5].mean())
    neg_mean = float(probs[y_np < 0.5].mean())
    rows = [
        {
            "status": "pass" if finite_ok and final_loss < initial_loss else "fail",
            "n_samples": int(x_np.shape[0]),
            "n_positive": int((y_np > 0.5).sum()),
            "n_negative": int((y_np < 0.5).sum()),
            "initial_loss": initial_loss,
            "final_loss": final_loss,
            "loss_delta": initial_loss - final_loss,
            "last_grad_norm": grad_norms[-1] if grad_norms else None,
            "nan_or_inf": not finite_ok,
            "positive_prob_mean": pos_mean,
            "negative_prob_mean": neg_mean,
            "case_count": len(set(case_ids)),
        }
    ]
    write_csv(OUT_ROOT / "feature_augmented_unit_gradient_smoke.csv", rows)
    write_csv(OUT_ROOT / "feature_augmented_tiny_overfit_metrics.csv", rows)
    write_csv(OUT_ROOT / "feature_augmented_fold0_very_short_metrics.csv", [{"status": "not_run", "reason": "feature smoke only; no fold0 train submitted"}])
    write_csv(OUT_ROOT / "feature_augmented_fold0_short_metrics.csv", [{"status": "not_run", "reason": "feature smoke only; no fold0 train submitted"}])


def write_overlay(fc: FeatureCase) -> dict[str, object] | None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return None
    union = (fc.gt == EDEMA) | (fc.baseline == EDEMA) | (fc.round11 == EDEMA)
    coords = np.argwhere(union)
    if coords.size == 0:
        return None
    z = int(np.median(coords[:, 0]))
    OVERLAY_ROOT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 5, figsize=(17, 4), constrained_layout=True)
    panels = [
        ("T2 support", fc.t2_support[z], "gray", None),
        ("support score", fc.support_score[z], "viridis", None),
        ("GT edema", fc.gt[z] == EDEMA, "Greens", fc.t2_support[z]),
        ("Round11 added", (fc.round11[z] == EDEMA) & (fc.baseline[z] != EDEMA), "magma", fc.t2_support[z]),
        ("baseline edema", fc.baseline[z] == EDEMA, "Blues", fc.t2_support[z]),
    ]
    for ax, (title, img, cmap, underlay) in zip(axes, panels):
        if underlay is not None:
            ax.imshow(underlay, cmap="gray")
            ax.imshow(np.ma.masked_where(~img.astype(bool), img.astype(bool)), cmap=cmap, alpha=0.45)
        else:
            ax.imshow(img, cmap=cmap)
        ax.set_title(title)
        ax.axis("off")
    path = OVERLAY_ROOT / f"{fc.case.case_id}_round13_feature_overlay.png"
    fig.suptitle(f"{fc.case.case_id} z={z} center={fc.case.center}")
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return {"case_id": fc.case.case_id, "overlay_path": str(path.relative_to(REPO_ROOT)), "slice_z": z}


def write_boundary_watch(boundary_rows: list[dict[str, object]]) -> None:
    tag_counts: dict[str, int] = {}
    for row in boundary_rows:
        for tag in str(row.get("failure_tags", "")).split(";"):
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    rows = [{"failure_tag": k, "case_count": v} for k, v in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))]
    write_csv(OUT_ROOT / "boundary_hd_auxiliary_watch.csv", rows)
    write_text(
        OUT_ROOT / "boundary_hd_auxiliary_watch.md",
        "\n".join(
            [
                "# Lane A Round13 Boundary/HD Auxiliary Watch",
                "",
                "Boundary/HD remains a watch item. It should not replace intensity/anatomy support.",
                "",
                *md_table(rows, ["failure_tag", "case_count"]),
            ]
        )
        + "\n",
    )


def boundary_watch_rows(cases: list[FeatureCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for fc in cases:
        baseline_metrics = base_eval.class_metrics(fc.baseline, fc.gt, fc.spacing, EDEMA, "baseline")
        r11_metrics = base_eval.class_metrics(fc.round11, fc.gt, fc.spacing, EDEMA, "round11")
        d_hd95 = delta(r11_metrics["round11_hd95"], baseline_metrics["baseline_hd95"], lower_is_better=True)
        d_comp = delta(r11_metrics["round11_component_count"], baseline_metrics["baseline_component_count"], lower_is_better=True)
        d_remote = delta(r11_metrics["round11_remote_fp"], baseline_metrics["baseline_remote_fp"], lower_is_better=True)
        tags = []
        if d_remote is not None and d_remote < 0:
            tags.append("remote_fp_worse")
        if d_comp is not None and d_comp < 0:
            tags.append("component_worse")
        if d_hd95 is not None and d_hd95 < 0:
            tags.append("hd95_worse")
        if not tags:
            tags.append("no_round11_boundary_regression")
        rows.append(
            {
                "case_id": fc.case.case_id,
                "center": fc.case.center,
                "t2_present": fc.case.t2_present,
                "edema_gt_positive": fc.case.edema_gt_positive,
                "delta_hd95_improvement": d_hd95,
                "delta_component_improvement": d_comp,
                "delta_remote_fp_improvement": d_remote,
                "failure_tags": ";".join(tags),
            }
        )
    return rows


def external_readiness_rows(feature_gate: str) -> list[dict[str, object]]:
    return [
        {
            "mechanism_slot": "T2_LGE_intensity_prior",
            "candidate_methods": "I-MMSeg-inspired CARE-first intensity features",
            "round14_priority": "go" if "calibrator" in feature_gate else "watch",
            "status": "first_party_feature_smoke_done",
            "next_smoke": "feature-augmented calibrator/fold0 very-short if Round13 gate passes",
            "compliance_notes": "No external data or weights; I-MMSeg remains mechanism source only.",
        },
        {
            "mechanism_slot": "anatomy_lesion_consistency",
            "candidate_methods": "Cascaded FSN/PT-Net-inspired soft consistency",
            "round14_priority": "go" if "calibrator" in feature_gate else "watch",
            "status": "first_party_feature_smoke_done",
            "next_smoke": "soft support feature/penalty, no hard ROI",
            "compliance_notes": "CARE-only anatomy support from nnU-Net probabilities/labels.",
        },
        {
            "mechanism_slot": "boundary_HD",
            "candidate_methods": "InverseForm/surface/HD-aware auxiliary",
            "round14_priority": "watch",
            "status": "not_primary",
            "next_smoke": "small-weight auxiliary only after support features pass",
            "compliance_notes": "Do not replace Dice/CE or report foreground_mean.",
        },
        {
            "mechanism_slot": "missing_modality_representation",
            "candidate_methods": "UniME/AdaMM/CoPeDiT/MoE/MMPL-Seg",
            "round14_priority": "postpone",
            "status": "metadata_only",
            "next_smoke": "license/compliance/input-output/one-case smoke before training",
            "compliance_notes": "External data training disallowed; complete-case teacher reliability unresolved.",
        },
        {
            "mechanism_slot": "alignment",
            "candidate_methods": "CAA-Seg/SSA",
            "round14_priority": "watch",
            "status": "not_escalated",
            "next_smoke": "escalate only if overlays show sequence mismatch",
            "compliance_notes": "CARE-only alignment audit first.",
        },
    ]


def write_decisions(grid_rows: list[dict[str, object]], best_rule: str | None, feature_gate: str, gate_reasons: list[str]) -> None:
    best_row = next((r for r in grid_rows if r["rule"] == best_rule), None)
    decision_rows = [
        {
            "route": "T2_LGE_intensity_prior",
            "status": "go" if best_rule else "watch",
            "evidence": f"best_feature_rule={best_rule or 'none'}; {gate_reasons[0] if gate_reasons else ''}",
            "next_action": "feature-augmented calibrator smoke" if best_rule else "refine feature construction before training",
        },
        {
            "route": "anatomy_lesion_consistency",
            "status": "go" if best_rule else "watch",
            "evidence": "component support table generated; rules do not use hard ROI",
            "next_action": "combine with intensity support; no hard deletion",
        },
        {
            "route": "feature_augmented_refiner_or_calibrator",
            "status": feature_gate,
            "evidence": f"best_rule_metrics={best_row}" if best_row else "no best rule",
            "next_action": "bounded fold0 very-short only after user approval if smoke is clean",
        },
        {
            "route": "boundary_HD_auxiliary",
            "status": "watch",
            "evidence": "boundary watch written; not primary until support features pass",
            "next_action": "small-weight auxiliary only",
        },
        {
            "route": "external_method_integration",
            "status": "postpone",
            "evidence": "Round14 readiness matrix written; no repo cloned",
            "next_action": "metadata/one-case smoke only after first-party route decision",
        },
    ]
    write_csv(OUT_ROOT / "round13_decision_table.csv", decision_rows)
    write_text(
        OUT_ROOT / "round13_decision_table.md",
        "\n".join(["# Lane A Round13 Decision Table", "", *md_table(decision_rows, ["route", "status", "evidence", "next_action"])]) + "\n",
    )
    readiness = external_readiness_rows(feature_gate)
    write_csv(OUT_ROOT / "round14_external_method_readiness_matrix.csv", readiness)
    write_text(
        OUT_ROOT / "round14_external_method_readiness_matrix.md",
        "\n".join(
            [
                "# Lane A Round14 External Method Readiness Matrix",
                "",
                "No external repo was cloned, built, or trained in Round13.",
                "",
                *md_table(readiness, ["mechanism_slot", "candidate_methods", "round14_priority", "status", "next_smoke", "compliance_notes"]),
            ]
        )
        + "\n",
    )
    rec_lines = [
        "# Lane A Round13 to Round14 Recommendation",
        "",
        "## Verdict",
        "",
        f"- Feature-only gate: `{feature_gate}`.",
        f"- Best deployable feature rule: `{best_rule or 'none'}`.",
        "- Do not create a validation zip or upload from Round13.",
        "- Do not expand to fold1-4/5-fold.",
        "- Continue only staged, gated CARE-first support features before external repo integration.",
        "",
        "## Recommended Order",
        "",
    ]
    if "go" in feature_gate:
        rec_lines.extend(
            [
                "1. Run a bounded fold0 very-short feature-augmented calibrator/refiner only after explicit user authorization.",
                "2. If that remains clean on scar/no-T2/CenterC/HD95, consider fold0 short.",
            ]
        )
    elif "watch" in feature_gate:
        rec_lines.extend(
            [
                "1. Review feature overlays and component support table before any fold0 training.",
                "2. Prefer stronger intensity/anatomy support design over longer refiner training.",
            ]
        )
    else:
        rec_lines.append("1. Do not train this feature route; move to Round14 readiness review.")
    rec_lines.extend(
        [
            "3. Keep boundary/HD as auxiliary watch.",
            "4. External methods require license/compliance/pretrained-data/input-output/label-mapping/one-case smoke first.",
        ]
    )
    write_text(OUT_ROOT / "round13_round14_recommendation.md", "\n".join(rec_lines) + "\n")


def write_readme(best_rule: str | None, feature_gate: str) -> None:
    write_text(
        OUT_ROOT / "round13_goal_execution_readme.md",
        "\n".join(
            [
                "# Lane A Round13 Goal Execution Readme",
                "",
                "Executed stages:",
                "- `round13_reproducibility_and_feature_source_gate`",
                "- `t2_lge_intensity_prior_feature_construction`",
                "- `anatomy_lesion_consistency_feature_construction`",
                "- `feature_only_diagnostic_and_rule_smoke`",
                "- `feature_augmented_refiner_or_calibrator_smoke` when feature gate allowed smoke",
                "- `boundary_hd_auxiliary_watch`",
                "- `external_method_readiness_for_round14`",
                "",
                "Not executed:",
                "- Slurm submission",
                "- validation zip creation",
                "- upload",
                "- fold1-4 or 5-fold",
                "- external repo clone/build/train",
                "- nnU-Net baseline cache modification",
                "",
                f"Best feature rule: `{best_rule or 'none'}`",
                f"Feature gate status: `{feature_gate}`",
                "",
                f"Output root: `{OUT_ROOT.relative_to(REPO_ROOT)}`",
            ]
        )
        + "\n",
    )


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_feature_configs()
    cases = load_all_feature_cases()
    write_reproducibility_gate(cases)
    feature_rows = feature_summary_rows(cases)
    sep_rows = separability_rows(feature_rows)
    center_comparison_rows(feature_rows)
    write_csv(
        OUT_ROOT / "t2_lge_intensity_feature_cache_manifest.csv",
        [
            {
                "case_id": fc.case.case_id,
                "feature_cache_path": str(fc.feature_cache_path),
                "center": fc.case.center,
                "modality_group": fc.case.modality_group,
                "t2_present": fc.case.t2_present,
                "edema_gt_positive": fc.case.edema_gt_positive,
            }
            for fc in cases
        ],
    )
    component_support_rows(cases)
    grid_rows, _, best_rule = run_feature_only_grid(cases)
    feature_gate, gate_reasons = feature_gate_status(grid_rows, best_rule)
    run_feature_augmented_smoke(cases, feature_gate)
    boundary_rows = boundary_watch_rows(cases)
    write_csv(OUT_ROOT / "boundary_hd_case_watch.csv", boundary_rows)
    write_boundary_watch(boundary_rows)
    overlay_rows = []
    for fc in cases:
        if fc.case.case_id in {"Case2031", "Case3011", "Case3012", "Case3040"}:
            row = write_overlay(fc)
            if row:
                overlay_rows.append(row)
    write_csv(OUT_ROOT / "overlay_manifest.csv", overlay_rows)
    write_decisions(grid_rows, best_rule, feature_gate, gate_reasons)
    write_readme(best_rule, feature_gate)
    # Keep a small top-feature table for quick inspection.
    write_text(
        OUT_ROOT / "t2_lge_intensity_separability_top.md",
        "\n".join(
            [
                "# Lane A Round13 Top Intensity Separability Features",
                "",
                *md_table(sorted(sep_rows, key=lambda r: safe_float(r.get("abs_gap")), reverse=True)[:20], ["group", "positive_region", "negative_region", "feature", "positive_mean", "negative_mean", "mean_gap_positive_minus_negative", "abs_gap"]),
            ]
        )
        + "\n",
    )
    print(f"Wrote Round13 diagnostics to {OUT_ROOT}")
    print(f"Best feature rule: {best_rule or 'none'}")
    print(f"Feature gate: {feature_gate}")


if __name__ == "__main__":
    main()
