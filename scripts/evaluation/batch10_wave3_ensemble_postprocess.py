#!/usr/bin/env python3
"""Batch10 Wave3 bounded probability ensembles, calibration grid, and near-baseline gate."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import distance_transform_edt, generate_binary_structure, label

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class  # noqa: E402
from scripts.inference.run_care_mm_batch10_fair_inference import (  # noqa: E402
    LABELS,
    RAW_LABEL_DIR,
    component_stats,
    export_logits,
    load_case_preprocessed,
    precision_recall,
    read_label,
)
from src.care_myocardium.data.care_mm_batch9 import build_case_records, load_fold_cases, sha256_file  # noqa: E402

TASK_KEY = "20260724_care_myops_batch10_deadline_rescue"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
PHASE1_ROOT = RESULT_ROOT / "runtime/phase1"
ENSEMBLE_ROOT = RESULT_ROOT / "runtime/wave3_ensemble_common_space"
ANATOMY_THRESHOLDS = [0.20, 0.30, 0.40]
DISTANCES_MM = [5, 10]
SCAR_MIN_MM3 = [0, 5, 10]
EDEMA_MIN_MM3 = [0, 20, 50]
ENSEMBLE_CANDIDATES = [
    "direct_two_seed_mean",
    "teacher_two_seed_mean",
    "control_epoch25_two_seed_mean",
    "distill_epoch25_two_seed_mean",
    "best_two_individual_mean",
    "pathology_specific_compositor",
]
COMPOSITOR_TEMPERATURES = [0.75, 1.0, 1.25]
COMPOSITOR_MARGINS = [-0.25, 0.0, 0.25]
BASELINE_VARIANT = "nnunet_fold0_baseline"
_SPLIT_CACHE: dict[str, str] | None = None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float(value: Any) -> float | None:
    if value in (None, "", "nan", "None"):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(v) or np.isinf(v):
        return None
    return v


def mean(values: list[Any]) -> float | None:
    vals = [v for v in (to_float(x) for x in values) if v is not None]
    return float(np.mean(vals)) if vals else None


def val_cases() -> list[str]:
    return sorted(load_fold_cases(0)[1])


def records_by_case() -> dict[str, Any]:
    return {r.case_id: r for r in build_case_records(0)}


def split_by_case() -> dict[str, str]:
    global _SPLIT_CACHE
    if _SPLIT_CACHE is None:
        _SPLIT_CACHE = {r["case_id"]: r["rescue_split"] for r in read_csv(RESULT_ROOT / "rescue_split_manifest.csv")}
    return _SPLIT_CACHE


def single_sources() -> list[dict[str, str]]:
    manifest_by_prefix: dict[str, dict[str, str]] = {}
    for row in read_csv(RESULT_ROOT / "single_model_candidate_manifest.csv"):
        prefix = row.get("source_prefix", "")
        if prefix and prefix not in manifest_by_prefix:
            manifest_by_prefix[prefix] = row
    by_prefix: dict[str, dict[str, str]] = {}
    for row in read_csv(RESULT_ROOT / "single_model_casewise_metrics.csv"):
        prefix = row.get("source_prefix", "")
        if not prefix or prefix == "baseline_nnunet_fold0_existing_prediction":
            continue
        manifest_row = manifest_by_prefix.get(prefix, {})
        by_prefix.setdefault(prefix, {
            "source_prefix": prefix,
            "variant": row.get("variant", ""),
            "seed": row.get("seed", ""),
            "checkpoint_path": manifest_row.get("checkpoint_path", row.get("checkpoint_path", "")),
            "checkpoint_sha256": manifest_row.get("checkpoint_sha256", row.get("checkpoint_sha256", "")),
        })
    return sorted(by_prefix.values(), key=lambda r: (r["variant"], r["seed"], r["source_prefix"]))


def prob_path(source_prefix: str, case_id: str) -> Path:
    return PHASE1_ROOT / source_prefix / f"{case_id}.npz"


def pred_path(source_prefix: str, case_id: str) -> Path:
    return PHASE1_ROOT / source_prefix / f"{case_id}.nii.gz"


def load_prob(source_prefix: str, case_id: str) -> np.ndarray:
    path = prob_path(source_prefix, case_id)
    if not path.is_file():
        raise FileNotFoundError(f"missing probability file: {path}")
    probs = np.load(path)["probabilities"].astype(np.float32, copy=False)
    if probs.shape[0] != 6:
        raise ValueError(f"expected 6-class probabilities in {path}, got {probs.shape}")
    return probs


def preprocessed_logits_path(source_prefix: str, case_id: str) -> Path:
    return PHASE1_ROOT / source_prefix / f"{case_id}_preprocessed_logits.npz"


def load_preprocessed_logits(source_prefix: str, case_id: str) -> np.ndarray:
    path = preprocessed_logits_path(source_prefix, case_id)
    if not path.is_file():
        raise FileNotFoundError(f"missing preprocessed logits for common-space fusion: {path}")
    logits = np.load(path)["logits"].astype(np.float32, copy=False)
    return np.clip(logits, -100.0, 100.0).astype(np.float32, copy=False)


def compositor_params_id(params: dict[str, Any]) -> str:
    return "temp{temperature}_scar{scar_margin}_edema{edema_margin}".format(**params)


def compose_pathology_logits(
    anatomy: np.ndarray,
    edema: np.ndarray,
    scar: np.ndarray,
    params: dict[str, Any],
) -> np.ndarray:
    """Use anatomy logits as the base and add calibrated pathology residuals."""
    temperature = max(float(params["temperature"]), 1e-6)
    out = anatomy.copy()
    edema_residual = edema[4] - anatomy[4]
    scar_residual = scar[5] - anatomy[5]
    out[4] = anatomy[4] + (edema_residual + float(params["edema_margin"])) / temperature
    out[5] = anatomy[5] + (scar_residual + float(params["scar_margin"])) / temperature
    return out.astype(np.float32, copy=False)


def ensemble_probability_path(candidate: str, case_id: str) -> Path:
    return ENSEMBLE_ROOT / candidate / "raw_argmax" / f"{case_id}.npz"


def fuse_preprocessed_logits(name: str, case_id: str, selected: dict[str, Any]) -> tuple[np.ndarray, Any]:
    components = candidate_components(name, selected)
    if isinstance(components, list):
        logits = [load_preprocessed_logits(source["source_prefix"], case_id) for source in components]
        return np.mean(logits, axis=0).astype(np.float32, copy=False), components
    anatomy = load_preprocessed_logits(components["anatomy_0_to_3"]["source_prefix"], case_id)
    edema = load_preprocessed_logits(components["edema_class4"]["source_prefix"], case_id)
    scar = load_preprocessed_logits(components["scar_class5"]["source_prefix"], case_id)
    out = compose_pathology_logits(anatomy, edema, scar, components["calibration"])
    return out.astype(np.float32, copy=False), components


def export_common_space_ensemble(name: str, case_id: str, selected: dict[str, Any]) -> tuple[Path, np.ndarray, Any]:
    logits, components = fuse_preprocessed_logits(name, case_id, selected)
    _data, props = load_case_preprocessed(case_id)
    out_truncated = ENSEMBLE_ROOT / name / "raw_argmax" / case_id
    pred = export_logits(logits, props, out_truncated, save_probabilities=True)
    prob_npz = out_truncated.with_suffix(".npz")
    probs = np.load(prob_npz)["probabilities"].astype(np.float32, copy=False)
    return pred, probs, components


def calibration_rows_for(pathology: str) -> list[dict[str, str]]:
    splits = split_by_case()
    return [
        r for r in read_csv(RESULT_ROOT / "single_model_casewise_metrics.csv")
        if r["pathology"] == pathology and splits.get(r["case_id"]) == "calibration" and r["gt_positive"] == "1"
    ]


def source_score(rows: list[dict[str, str]], source_prefix: str) -> float:
    vals = [r["dice"] for r in rows if r.get("source_prefix") == source_prefix]
    return mean(vals) if vals else -1.0


def source_pathology_scores(source: dict[str, str]) -> dict[str, float]:
    scores = {}
    for pathology in LABELS:
        scores[pathology] = source_score(calibration_rows_for(pathology), source["source_prefix"])
    vals = [v for v in scores.values() if v >= 0]
    scores["min_pathology_dice"] = min(vals) if vals else -1.0
    scores["mean_pathology_dice"] = float(np.mean(vals)) if vals else -1.0
    return scores


def source_epoch(source: dict[str, str]) -> int:
    prefix = source.get("source_prefix", "")
    match = __import__("re").search(r"_epoch(\d+)_", prefix)
    return int(match.group(1)) if match else 25


def anatomy_score(source: dict[str, str]) -> dict[str, Any]:
    splits = split_by_case()
    per_class: dict[int, list[float]] = {1: [], 2: [], 3: []}
    myocardium_hd95: list[float] = []
    for case_id in val_cases():
        if splits.get(case_id) != "calibration":
            continue
        gt_img, gt = read_label(RAW_LABEL_DIR / f"{case_id}.nii.gz")
        pred_img, pred = read_label(pred_path(source["source_prefix"], case_id), reference=gt_img)
        del pred_img
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        for class_id in (1, 2, 3):
            dice = dice_per_class(pred, gt, class_id, skip_if_gt_empty=True)
            if dice is not None:
                per_class[class_id].append(float(dice))
        hd95 = hd95_class(pred, gt, 1, spacing)
        if hd95 is not None:
            myocardium_hd95.append(float(hd95))
    class_means = {f"class_{class_id}_calibration_dice": mean(vals) for class_id, vals in per_class.items()}
    dice_values = [v for v in class_means.values() if v is not None]
    return {
        **source,
        **class_means,
        "min_anatomy_class_dice": min(dice_values) if dice_values else -1.0,
        "mean_anatomy_class_dice": mean(dice_values),
        "myocardium_hd95": mean(myocardium_hd95),
    }


def best_source_per_variant_seed(sources: list[dict[str, str]], variant: str) -> list[dict[str, str]]:
    selected = []
    for seed in sorted({s["seed"] for s in sources if s["variant"] == variant}):
        candidates = [s for s in sources if s["variant"] == variant and s["seed"] == seed]
        if not candidates:
            continue
        candidates.sort(
            key=lambda s: (
                source_pathology_scores(s)["min_pathology_dice"],
                source_pathology_scores(s)["mean_pathology_dice"],
                -source_epoch(s),
            ),
            reverse=True,
        )
        selected.append(candidates[0])
    if len(selected) != 2:
        raise RuntimeError(f"expected two seed sources for {variant}, found {len(selected)}")
    return selected


def select_calibration_sources() -> dict[str, Any]:
    sources = single_sources()
    edema_rows = calibration_rows_for("edema")
    scar_rows = calibration_rows_for("scar")
    if not sources:
        raise RuntimeError("single_model_casewise_metrics.csv does not define any non-baseline source_prefix candidates")
    edema_best = max(sources, key=lambda s: source_score(edema_rows, s["source_prefix"]))
    scar_best = max(sources, key=lambda s: source_score(scar_rows, s["source_prefix"]))
    combined_scores = []
    for source in sources:
        scores = source_pathology_scores(source)
        combined_scores.append((source, scores["min_pathology_dice"], scores["mean_pathology_dice"]))
    combined_scores.sort(key=lambda x: (x[1], x[2], -source_epoch(x[0])), reverse=True)
    anatomy_scores = [anatomy_score(source) for source in sources]
    anatomy_scores.sort(
        key=lambda s: (
            to_float(s.get("min_anatomy_class_dice")) or -1.0,
            to_float(s.get("mean_anatomy_class_dice")) or -1.0,
            -(to_float(s.get("myocardium_hd95")) or 1e9),
            -source_epoch(s),
        ),
        reverse=True,
    )
    anatomy = anatomy_scores[0]
    return {
        "best_edema_source": {**edema_best, "calibration_positive_gt_dice": source_score(edema_rows, edema_best["source_prefix"])},
        "best_scar_source": {**scar_best, "calibration_positive_gt_dice": source_score(scar_rows, scar_best["source_prefix"])},
        "best_anatomy_source": anatomy,
        "best_two_individual_sources": [
            {**source, "calibration_min_pathology_dice": min_score, "calibration_mean_pathology_dice": mean_score}
            for source, min_score, mean_score in combined_scores[:2]
        ],
        "two_seed_variant_sources": {
            "student_direct_reliable": best_source_per_variant_seed(sources, "student_direct_reliable"),
            "teacher_full_view": best_source_per_variant_seed(sources, "teacher_full_view"),
            "student_moddrop_control": best_source_per_variant_seed(sources, "student_moddrop_control"),
            "student_reliable_distill": best_source_per_variant_seed(sources, "student_reliable_distill"),
        },
        "selection_uses_audit": False,
    }


def candidate_components(name: str, selected: dict[str, Any]) -> list[dict[str, str]] | dict[str, dict[str, str]]:
    if name == "direct_two_seed_mean":
        return selected["two_seed_variant_sources"]["student_direct_reliable"]
    if name == "teacher_two_seed_mean":
        return selected["two_seed_variant_sources"]["teacher_full_view"]
    if name == "control_epoch25_two_seed_mean":
        return selected["two_seed_variant_sources"]["student_moddrop_control"]
    if name == "distill_epoch25_two_seed_mean":
        return selected["two_seed_variant_sources"]["student_reliable_distill"]
    if name == "best_two_individual_mean":
        return selected["best_two_individual_sources"]
    if name == "pathology_specific_compositor":
        anatomy = selected["best_anatomy_source"]
        edema = selected["best_edema_source"]
        scar = selected["best_scar_source"]
        return {
            "anatomy_0_to_3": anatomy,
            "edema_class4": edema,
            "scar_class5": scar,
            "calibration": selected["pathology_compositor_calibration"]["selected"],
        }
    raise ValueError(name)


def select_pathology_compositor_calibration(
    selected_sources: dict[str, Any],
    baseline: dict[tuple[str, str], dict[str, str]],
) -> dict[str, Any]:
    records = records_by_case()
    splits = split_by_case()
    base_summary = baseline_split_summary()
    calibration_cases = [case_id for case_id in val_cases() if splits[case_id] == "calibration"]
    source_bundle = {
        "anatomy_0_to_3": selected_sources["best_anatomy_source"],
        "edema_class4": selected_sources["best_edema_source"],
        "scar_class5": selected_sources["best_scar_source"],
    }
    grid_rows: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for temperature, scar_margin, edema_margin in itertools.product(
        COMPOSITOR_TEMPERATURES,
        COMPOSITOR_MARGINS,
        COMPOSITOR_MARGINS,
    ):
        params = {
            "temperature": float(temperature),
            "scar_margin": float(scar_margin),
            "edema_margin": float(edema_margin),
        }
        pid = compositor_params_id(params)
        metric_rows: list[dict[str, Any]] = []
        for case_id in calibration_cases:
            rec = records[case_id]
            anatomy = load_preprocessed_logits(source_bundle["anatomy_0_to_3"]["source_prefix"], case_id)
            edema = load_preprocessed_logits(source_bundle["edema_class4"]["source_prefix"], case_id)
            scar = load_preprocessed_logits(source_bundle["scar_class5"]["source_prefix"], case_id)
            logits = compose_pathology_logits(anatomy, edema, scar, params)
            _data, props = load_case_preprocessed(case_id)
            out_truncated = ENSEMBLE_ROOT / "pathology_specific_compositor_calibration_grid" / pid / case_id
            pred_path_exported = export_logits(logits, props, out_truncated, save_probabilities=False)
            gt_img, gt = read_label(RAW_LABEL_DIR / f"{case_id}.nii.gz")
            _pred_img, pred = read_label(pred_path_exported, reference=gt_img)
            if not rec.t2_present:
                pred[pred == 4] = 0
            metric_rows.extend(
                metric_rows_for_pred(
                    pred,
                    gt,
                    gt_img,
                    case_id=case_id,
                    candidate="pathology_specific_compositor_calibration_grid",
                    postprocess_id=pid,
                    params=raw_params(),
                    baseline=baseline,
                    rec=rec,
                    compute_hd95=False,
                    compute_components=False,
                )
            )
        score = {
            "postprocess_id": pid,
            "temperature": params["temperature"],
            "scar_margin": params["scar_margin"],
            "edema_margin": params["edema_margin"],
            **score_grid_rows(metric_rows, base_summary),
        }
        grid_rows.append(score)
        key = (
            to_float(score.get("minimum_pathology_delta_vs_nnunet")) if to_float(score.get("minimum_pathology_delta_vs_nnunet")) is not None else -999.0,
            to_float(score.get("mean_pathology_delta_vs_nnunet")) if to_float(score.get("mean_pathology_delta_vs_nnunet")) is not None else -999.0,
            -int(score.get("harm_count_total") or 0),
            -int(score.get("empty_prediction_count_total") or 0),
            -abs(float(params["temperature"]) - 1.0),
            -abs(float(params["scar_margin"])),
            -abs(float(params["edema_margin"])),
        )
        if best is None or key > best["_key"]:
            best = {**score, "_key": key}
    assert best is not None
    selected = {k: v for k, v in best.items() if k != "_key"}
    payload = {
        "schema_version": 1,
        "status": "PASS",
        "selection_uses": "calibration_only",
        "audit_used_for_selection": False,
        "fixed_grid": {
            "temperature": COMPOSITOR_TEMPERATURES,
            "scar_margin": COMPOSITOR_MARGINS,
            "edema_margin": COMPOSITOR_MARGINS,
        },
        "source_bundle": source_bundle,
        "selected": selected,
    }
    write_csv(RESULT_ROOT / "pathology_compositor_calibration_grid.csv", grid_rows)
    write_json(RESULT_ROOT / "pathology_compositor_calibration.json", payload)
    return payload


def ensemble_prob(name: str, case_id: str, selected: dict[str, Any]) -> tuple[np.ndarray, Any]:
    components = candidate_components(name, selected)
    path = ensemble_probability_path(name, case_id)
    if not path.is_file():
        _pred, probs, components = export_common_space_ensemble(name, case_id, selected)
        return probs, components
    probs = np.load(path)["probabilities"].astype(np.float32, copy=False)
    return probs, components


def remove_small(mask: np.ndarray, spacing_zyx: tuple[float, float, float], min_mm3: float) -> np.ndarray:
    if min_mm3 <= 0 or not mask.any():
        return mask
    cc, n = label(mask, structure=generate_binary_structure(mask.ndim, 1))
    if n == 0:
        return mask
    voxel = float(np.prod(spacing_zyx))
    keep = np.zeros_like(mask, dtype=bool)
    for idx in range(1, n + 1):
        comp = cc == idx
        if np.count_nonzero(comp) * voxel >= min_mm3:
            keep |= comp
    return keep


def prediction_from_probs(
    probs: np.ndarray,
    params: dict[str, Any],
    *,
    spacing_zyx: tuple[float, float, float],
    t2_present: bool,
    support_distance: np.ndarray | None = None,
    base_pred: np.ndarray | None = None,
) -> np.ndarray:
    pred = base_pred.copy() if base_pred is not None else np.argmax(probs, axis=0).astype(np.uint8, copy=False)
    if not t2_present:
        pred[pred == 4] = 0
    if support_distance is None:
        support = probs[1] >= float(params["anatomy_probability_threshold"])
        dist = distance_transform_edt(~support.astype(bool), sampling=spacing_zyx) if support.any() else np.full(pred.shape, np.inf, dtype=np.float32)
    else:
        dist = support_distance
    allowed = dist <= float(params["allowed_distance_mm"])
    for class_id, min_key in [(4, "edema_min_component_mm3"), (5, "scar_min_component_mm3")]:
        mask = (pred == class_id) & allowed
        mask = remove_small(mask, spacing_zyx, float(params[min_key]))
        pred[pred == class_id] = 0
        pred[mask] = class_id
    return pred


def raw_params() -> dict[str, Any]:
    return {"anatomy_probability_threshold": 0.0, "allowed_distance_mm": 1e9, "scar_min_component_mm3": 0, "edema_min_component_mm3": 0}


def params_id(params: dict[str, Any]) -> str:
    return "anat{anatomy_probability_threshold}_dist{allowed_distance_mm}_scar{scar_min_component_mm3}_edema{edema_min_component_mm3}".format(**params)


def metric_rows_for_pred(
    pred: np.ndarray,
    gt: np.ndarray,
    gt_img: sitk.Image,
    *,
    case_id: str,
    candidate: str,
    postprocess_id: str,
    params: dict[str, Any],
    baseline: dict[tuple[str, str], dict[str, str]],
    rec: Any,
    compute_hd95: bool = True,
    compute_components: bool = True,
) -> list[dict[str, Any]]:
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    myocardium = (gt >= 1) & (gt <= 5)
    rows = []
    for pathology, class_id in LABELS.items():
        prec, rec_val = precision_recall(pred, gt, class_id)
        row = {
            "variant": candidate,
            "seed": "ensemble",
            "case_id": case_id,
            "pathology": pathology,
            "class_id": class_id,
            "dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
            "hd95": hd95_class(pred, gt, class_id, spacing) if compute_hd95 else None,
            "precision": prec,
            "recall": rec_val,
            "gt_positive": int(bool(np.any(gt == class_id))),
            "prediction_positive": int(bool(np.any(pred == class_id))),
            "center": rec.center,
            "modality_group": rec.modality_group,
            "complete_trimodal": int(rec.t2_present and rec.c0_present),
            "rescue_split": split_by_case()[case_id],
            "postprocess_id": postprocess_id,
            "anatomy_probability_threshold": params["anatomy_probability_threshold"],
            "allowed_distance_mm": params["allowed_distance_mm"],
            "scar_min_component_mm3": params["scar_min_component_mm3"],
            "edema_min_component_mm3": params["edema_min_component_mm3"],
            "no_t2_edema_predicted_voxels": int(np.count_nonzero(pred == 4)) if not rec.t2_present else 0,
            "source_prefix": f"wave3_{candidate}_{postprocess_id}",
        }
        b = baseline.get((case_id, pathology))
        if b:
            d = to_float(row["dice"])
            bd = to_float(b.get("dice"))
            h = to_float(row["hd95"])
            bh = to_float(b.get("hd95"))
            row["baseline_dice"] = bd
            row["baseline_hd95"] = bh
            row["delta_dice_vs_nnunet"] = None if d is None or bd is None else d - bd
            row["delta_hd95_vs_nnunet"] = None if h is None or bh is None else h - bh
            delta = to_float(row["delta_dice_vs_nnunet"])
            row["casewise_help_harm_vs_nnunet"] = "tie_or_empty" if delta is None or abs(delta) <= 1e-8 else ("help" if delta > 0 else "harm")
        if compute_components:
            row.update(component_stats(pred, gt, myocardium, class_id, spacing))
        else:
            pred_mask = pred == class_id
            gt_mask = gt == class_id
            spacing_volume = float(np.prod(spacing))
            row.update({
                "component_count": None,
                "remote_fp_volume_mm3": None,
                "pred_volume_mm3": float(np.count_nonzero(pred_mask) * spacing_volume),
                "gt_volume_mm3": float(np.count_nonzero(gt_mask) * spacing_volume),
                "volume_ratio": None if not gt_mask.any() else float(np.count_nonzero(pred_mask) / max(1, np.count_nonzero(gt_mask))),
                "empty_prediction": int(not pred_mask.any()),
            })
        rows.append(row)
    return rows


def summarize(rows: list[dict[str, Any]], output: Path, *, source: str) -> list[dict[str, Any]]:
    populations = ["full44", "calibration", "audit", "positive_gt", "audit_positive_gt", "complete_trimodal"]
    summary: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["variant"]), str(row["postprocess_id"]), str(row["pathology"]))].append(row)
    def filt(group: list[dict[str, Any]], pop: str) -> list[dict[str, Any]]:
        if pop == "full44":
            return group
        if pop == "calibration":
            return [r for r in group if r.get("rescue_split") == "calibration"]
        if pop == "audit":
            return [r for r in group if r.get("rescue_split") == "audit"]
        if pop == "positive_gt":
            return [r for r in group if str(r.get("gt_positive")) == "1"]
        if pop == "audit_positive_gt":
            return [r for r in group if r.get("rescue_split") == "audit" and str(r.get("gt_positive")) == "1"]
        if pop == "complete_trimodal":
            return [r for r in group if str(r.get("complete_trimodal")) == "1"]
        raise ValueError(pop)
    for (candidate, postprocess_id, pathology), group in sorted(grouped.items()):
        for pop in populations:
            subset = filt(group, pop)
            if not subset:
                continue
            summary.append({
                "source": source,
                "variant": candidate,
                "postprocess_id": postprocess_id,
                "pathology": pathology,
                "population": pop,
                "case_count": len(subset),
                "gt_positive_cases": sum(int(str(r.get("gt_positive")) == "1") for r in subset),
                "mean_dice": mean([r.get("dice") for r in subset]),
                "mean_hd95": mean([r.get("hd95") for r in subset]),
                "mean_remote_fp_volume_mm3": mean([r.get("remote_fp_volume_mm3") for r in subset]),
                "mean_component_count": mean([r.get("component_count") for r in subset]),
                "empty_prediction_count": sum(int(float(r.get("empty_prediction") or 0)) for r in subset),
                "empty_prediction_rate": sum(int(float(r.get("empty_prediction") or 0)) for r in subset) / max(1, len(subset)),
                "no_t2_edema_predicted_voxels_sum": sum(int(float(r.get("no_t2_edema_predicted_voxels") or 0)) for r in subset),
                "help_count_vs_nnunet": sum(int((to_float(r.get("delta_dice_vs_nnunet")) or 0.0) > 1e-8) for r in subset),
                "harm_count_vs_nnunet": sum(int((to_float(r.get("delta_dice_vs_nnunet")) or 0.0) < -1e-8) for r in subset),
            })
    write_csv(output, summary)
    return summary


def write_pred(path: Path, pred: np.ndarray, reference_path: Path) -> None:
    ref = sitk.ReadImage(str(reference_path))
    img = sitk.GetImageFromArray(pred.astype(np.uint8, copy=False))
    img.CopyInformation(ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(path))


def evaluate_raw_ensembles(selected_sources: dict[str, Any], baseline: dict[tuple[str, str], dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = records_by_case()
    rows: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for candidate in ENSEMBLE_CANDIDATES:
        for case_id in val_cases():
            rec = records[case_id]
            pred_path_exported, probs, components = export_common_space_ensemble(candidate, case_id, selected_sources)
            gt_img, gt = read_label(RAW_LABEL_DIR / f"{case_id}.nii.gz")
            spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
            pred = prediction_from_probs(probs, raw_params(), spacing_zyx=spacing, t2_present=rec.t2_present)
            out = ENSEMBLE_ROOT / candidate / "raw_argmax" / f"{case_id}.nii.gz"
            write_pred(out, pred, pred_path_exported)
            manifest.append({
                "candidate": candidate,
                "postprocess_id": "raw_argmax",
                "case_id": case_id,
                "prediction_path": str(out.relative_to(REPO_ROOT)),
                "prediction_sha256": sha256_file(out),
                "probability_ensemble_only": True,
                "nnunet_probability_source": False,
                "fusion_space": "common_preprocessed_logits",
                "inverse_export_count": 1,
                "components": json.dumps(components, sort_keys=True),
            })
            rows.extend(metric_rows_for_pred(pred, gt, gt_img, case_id=case_id, candidate=candidate, postprocess_id="raw_argmax", params=raw_params(), baseline=baseline, rec=rec))
    return rows, manifest


def grid_params() -> list[dict[str, Any]]:
    return [
        {"anatomy_probability_threshold": a, "allowed_distance_mm": d, "scar_min_component_mm3": s, "edema_min_component_mm3": e}
        for a, d, s, e in itertools.product(ANATOMY_THRESHOLDS, DISTANCES_MM, SCAR_MIN_MM3, EDEMA_MIN_MM3)
    ]


def score_grid_rows(rows: list[dict[str, Any]], baseline_summary: dict[tuple[str, str], float]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pathology in LABELS:
        subset = [r for r in rows if r["pathology"] == pathology and r["rescue_split"] == "calibration" and str(r["gt_positive"]) == "1"]
        dice = mean([r.get("dice") for r in subset])
        hd95 = mean([r.get("hd95") for r in subset])
        remote = mean([r.get("remote_fp_volume_mm3") for r in subset])
        harm = sum(int((to_float(r.get("delta_dice_vs_nnunet")) or 0.0) < -1e-8) for r in subset)
        out[f"{pathology}_calibration_positive_gt_dice"] = dice
        out[f"{pathology}_calibration_positive_gt_delta_vs_nnunet"] = None if dice is None else dice - baseline_summary.get((pathology, "calibration_positive_gt"), 0.0)
        out[f"{pathology}_calibration_positive_gt_hd95"] = hd95
        out[f"{pathology}_calibration_remote_fp_volume_mm3"] = remote
        out[f"{pathology}_calibration_harm_count"] = harm
        out[f"{pathology}_calibration_empty_prediction_count"] = sum(int(float(r.get("empty_prediction") or 0)) for r in subset)
    deltas = [to_float(out.get(f"{p}_calibration_positive_gt_delta_vs_nnunet")) for p in LABELS]
    out["minimum_pathology_delta_vs_nnunet"] = min(v for v in deltas if v is not None) if any(v is not None for v in deltas) else None
    out["mean_pathology_delta_vs_nnunet"] = mean(deltas)
    out["harm_count_total"] = sum(int(out.get(f"{p}_calibration_harm_count") or 0) for p in LABELS)
    out["empty_prediction_count_total"] = sum(int(out.get(f"{p}_calibration_empty_prediction_count") or 0) for p in LABELS)
    out["remote_fp_sum"] = sum(float(out.get(f"{p}_calibration_remote_fp_volume_mm3") or 0.0) for p in LABELS)
    out["hd95_sum"] = sum(float(out.get(f"{p}_calibration_positive_gt_hd95") or 0.0) for p in LABELS)
    return out


def baseline_split_summary() -> dict[tuple[str, str], float]:
    splits = split_by_case()
    rows = read_csv(RESULT_ROOT / "baseline_recomputed_casewise.csv")
    out = {}
    for pathology in LABELS:
        subset = [r for r in rows if r["pathology"] == pathology and splits.get(r["case_id"]) == "calibration" and r["gt_positive"] == "1"]
        out[(pathology, "calibration_positive_gt")] = mean([r.get("dice") for r in subset]) or 0.0
        audit = [r for r in rows if r["pathology"] == pathology and splits.get(r["case_id"]) == "audit" and r["gt_positive"] == "1"]
        out[(pathology, "audit_positive_gt_dice")] = mean([r.get("dice") for r in audit]) or 0.0
        out[(pathology, "audit_positive_gt_hd95")] = mean([r.get("hd95") for r in audit]) or 0.0
    return out


def run_grid(selected_sources: dict[str, Any], baseline: dict[tuple[str, str], dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = records_by_case()
    splits = split_by_case()
    base_summary = baseline_split_summary()
    grid_rows: list[dict[str, Any]] = []
    calibration_cases = [case_id for case_id in val_cases() if splits[case_id] == "calibration"]
    payloads_by_candidate: dict[str, list[dict[str, Any]]] = {}
    raw_scores: dict[str, dict[str, Any]] = {}
    for candidate in ENSEMBLE_CANDIDATES:
        payloads = []
        for case_id in calibration_cases:
            rec = records[case_id]
            probs, _components = ensemble_prob(candidate, case_id, selected_sources)
            gt_img, gt = read_label(RAW_LABEL_DIR / f"{case_id}.nii.gz")
            spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
            distance_by_threshold = {}
            for threshold in ANATOMY_THRESHOLDS:
                support = probs[1] >= float(threshold)
                distance_by_threshold[threshold] = distance_transform_edt(~support.astype(bool), sampling=spacing) if support.any() else np.full(probs.shape[1:], np.inf, dtype=np.float32)
            base_pred = np.argmax(probs, axis=0).astype(np.uint8, copy=False)
            payloads.append({"case_id": case_id, "rec": rec, "probs": probs, "base_pred": base_pred, "gt_img": gt_img, "gt": gt, "spacing": spacing, "distance_by_threshold": distance_by_threshold})
        payloads_by_candidate[candidate] = payloads
        raw_metric_rows: list[dict[str, Any]] = []
        for payload in payloads:
            raw_metric_rows.extend(metric_rows_for_pred(payload["base_pred"], payload["gt"], payload["gt_img"], case_id=payload["case_id"], candidate=candidate, postprocess_id="raw_argmax", params=raw_params(), baseline=baseline, rec=payload["rec"], compute_hd95=False, compute_components=False))
        raw_scores[candidate] = {"candidate": candidate, "postprocess_id": "raw_argmax", "stage": "raw_no_postprocess", **raw_params(), **score_grid_rows(raw_metric_rows, base_summary)}
    stage1_params = [
        {"anatomy_probability_threshold": a, "allowed_distance_mm": d, "scar_min_component_mm3": 0, "edema_min_component_mm3": 0}
        for a, d in itertools.product(ANATOMY_THRESHOLDS, DISTANCES_MM)
    ]
    stage1_best: dict[str, Any] | None = None
    for candidate, payloads in payloads_by_candidate.items():
        for params in stage1_params:
            pid = params_id(params)
            metric_rows: list[dict[str, Any]] = []
            for payload in payloads:
                pred = prediction_from_probs(
                    payload["probs"],
                    params,
                    spacing_zyx=payload["spacing"],
                    t2_present=payload["rec"].t2_present,
                    support_distance=payload["distance_by_threshold"][float(params["anatomy_probability_threshold"])],
                    base_pred=payload["base_pred"],
                )
                metric_rows.extend(
                    metric_rows_for_pred(
                        pred,
                        payload["gt"],
                        payload["gt_img"],
                        case_id=payload["case_id"],
                        candidate=candidate,
                        postprocess_id=pid,
                        params=params,
                        baseline=baseline,
                        rec=payload["rec"],
                        compute_hd95=False,
                        compute_components=False,
                    )
                )
            score = {"candidate": candidate, "postprocess_id": pid, "stage": "stage1_anatomy_support_distance", **params, **score_grid_rows(metric_rows, base_summary)}
            grid_rows.append(score)
            key = (
                to_float(score.get("minimum_pathology_delta_vs_nnunet")) if to_float(score.get("minimum_pathology_delta_vs_nnunet")) is not None else -999.0,
                to_float(score.get("mean_pathology_delta_vs_nnunet")) if to_float(score.get("mean_pathology_delta_vs_nnunet")) is not None else -999.0,
                -int(score.get("harm_count_total") or 0),
                -float(score.get("hd95_sum") or 0.0),
                -float(score.get("remote_fp_sum") or 0.0),
                -float(params["anatomy_probability_threshold"]),
                -float(params["allowed_distance_mm"]),
                -float(params["scar_min_component_mm3"]),
                -float(params["edema_min_component_mm3"]),
            )
            if stage1_best is None or key > stage1_best["_key"]:
                stage1_best = {**score, "_key": key}
    assert stage1_best is not None
    stage2_best: dict[str, Any] | None = None
    stage2_params = [
        {
            "anatomy_probability_threshold": float(stage1_best["anatomy_probability_threshold"]),
            "allowed_distance_mm": float(stage1_best["allowed_distance_mm"]),
            "scar_min_component_mm3": s,
            "edema_min_component_mm3": e,
        }
        for s, e in itertools.product(SCAR_MIN_MM3, EDEMA_MIN_MM3)
    ]
    candidate = str(stage1_best["candidate"])
    for params in stage2_params:
        pid = params_id(params)
        metric_rows = []
        for payload in payloads_by_candidate[candidate]:
            pred = prediction_from_probs(payload["probs"], params, spacing_zyx=payload["spacing"], t2_present=payload["rec"].t2_present, support_distance=payload["distance_by_threshold"][float(params["anatomy_probability_threshold"])], base_pred=payload["base_pred"])
            metric_rows.extend(metric_rows_for_pred(pred, payload["gt"], payload["gt_img"], case_id=payload["case_id"], candidate=candidate, postprocess_id=pid, params=params, baseline=baseline, rec=payload["rec"], compute_hd95=False, compute_components=False))
        score = {"candidate": candidate, "postprocess_id": pid, "stage": "stage2_pathology_component_filter", **params, **score_grid_rows(metric_rows, base_summary)}
        grid_rows.append(score)
        key = (
            to_float(score.get("minimum_pathology_delta_vs_nnunet")) if to_float(score.get("minimum_pathology_delta_vs_nnunet")) is not None else -999.0,
            to_float(score.get("mean_pathology_delta_vs_nnunet")) if to_float(score.get("mean_pathology_delta_vs_nnunet")) is not None else -999.0,
            -int(score.get("harm_count_total") or 0),
            -int(score.get("empty_prediction_count_total") or 0),
            -float(score.get("hd95_sum") or 0.0),
            -float(score.get("remote_fp_sum") or 0.0),
        )
        if stage2_best is None or key > stage2_best["_key"]:
            stage2_best = {**score, "_key": key}
    assert stage2_best is not None
    raw = raw_scores[candidate]
    selected = stage2_best
    gain = (to_float(selected.get("minimum_pathology_delta_vs_nnunet")) or -999.0) - (to_float(raw.get("minimum_pathology_delta_vs_nnunet")) or -999.0)
    fallback_reasons = []
    if gain < 0.005:
        fallback_reasons.append("minimum_pathology_delta_gain_below_0.005")
    if int(selected.get("harm_count_total") or 0) > int(raw.get("harm_count_total") or 0):
        fallback_reasons.append("harm_count_increased")
    if int(selected.get("empty_prediction_count_total") or 0) > int(raw.get("empty_prediction_count_total") or 0):
        fallback_reasons.append("empty_prediction_count_increased")
    if fallback_reasons:
        best_clean = {**raw, "postprocess_selected": "raw_argmax", "fallback_reasons": ";".join(fallback_reasons)}
    else:
        best_clean = {k: v for k, v in selected.items() if k != "_key"}
        best_clean["postprocess_selected"] = "two_stage_postprocess"
        best_clean["fallback_reasons"] = ""
    write_csv(RESULT_ROOT / "postprocess_calibration_grid.csv", grid_rows)
    write_json(RESULT_ROOT / "postprocess_selected.json", {
        "schema_version": 1,
        "status": "PASS",
        "selection_uses": "calibration_only_two_stage",
        "audit_used_for_selection": False,
        "selected": best_clean,
        "stage1_best": {k: v for k, v in stage1_best.items() if k != "_key"},
        "stage2_best": {k: v for k, v in stage2_best.items() if k != "_key"},
        "raw_comparator": raw,
        "fixed_grid": {
            "anatomy_probability_threshold": ANATOMY_THRESHOLDS,
            "allowed_distance_mm": DISTANCES_MM,
            "scar_min_component_mm3": SCAR_MIN_MM3,
            "edema_min_component_mm3": EDEMA_MIN_MM3,
        },
    })
    return grid_rows, best_clean

def evaluate_selected(best: dict[str, Any], selected_sources: dict[str, Any], baseline: dict[tuple[str, str], dict[str, str]], manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if str(best["postprocess_id"]) == "raw_argmax":
        return []
    records = records_by_case()
    params = {
        "anatomy_probability_threshold": float(best["anatomy_probability_threshold"]),
        "allowed_distance_mm": float(best["allowed_distance_mm"]),
        "scar_min_component_mm3": float(best["scar_min_component_mm3"]),
        "edema_min_component_mm3": float(best["edema_min_component_mm3"]),
    }
    candidate = str(best["candidate"])
    pid = str(best["postprocess_id"])
    rows: list[dict[str, Any]] = []
    for case_id in val_cases():
        rec = records[case_id]
        probs, components = ensemble_prob(candidate, case_id, selected_sources)
        gt_img, gt = read_label(RAW_LABEL_DIR / f"{case_id}.nii.gz")
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        pred = prediction_from_probs(probs, params, spacing_zyx=spacing, t2_present=rec.t2_present)
        out = ENSEMBLE_ROOT / candidate / pid / f"{case_id}.nii.gz"
        first_component = components[0] if isinstance(components, list) else components["anatomy_0_to_3"]
        write_pred(out, pred, pred_path(first_component["source_prefix"], case_id))
        manifest.append({
            "candidate": candidate,
            "postprocess_id": pid,
            "case_id": case_id,
            "prediction_path": str(out.relative_to(REPO_ROOT)),
            "prediction_sha256": sha256_file(out),
            "probability_ensemble_only": True,
            "nnunet_probability_source": False,
            "fusion_space": "common_preprocessed_logits",
            "inverse_export_count": 1,
            "components": json.dumps(components, sort_keys=True),
        })
        rows.extend(metric_rows_for_pred(pred, gt, gt_img, case_id=case_id, candidate=candidate, postprocess_id=pid, params=params, baseline=baseline, rec=rec))
    return rows


def record_wave3_selection_provenance(selected_sources: dict[str, Any], postprocess: dict[str, Any], ranking: list[dict[str, Any]]) -> None:
    path = RESULT_ROOT / "selection_provenance.json"
    data = json.loads(path.read_text()) if path.is_file() else {"schema_version": 1, "selection_events": []}
    calibration = sorted(case_id for case_id, split in split_by_case().items() if split == "calibration")
    audit = sorted(case_id for case_id, split in split_by_case().items() if split == "audit")
    data["selection_events"] = [
        event for event in data.get("selection_events", [])
        if event.get("event") != "wave3_calibration_only_source_and_postprocess_selection"
    ]
    data.setdefault("selection_events", []).append({
        "event": "wave3_calibration_only_source_and_postprocess_selection",
        "timestamp_unix": int(time.time()),
        "selection_uses": "calibration_only",
        "selection_rule": "anatomy_classes_1_3_fixed_order_pathology_sources_calibrated_logit_residual_compositor_two_stage_postprocess_with_raw_fallback",
        "selection_read_case_ids": calibration,
        "audit_case_ids": audit,
        "audit_case_ids_used_for_selection": [],
        "best_anatomy_source": selected_sources.get("best_anatomy_source"),
        "best_scar_source": selected_sources.get("best_scar_source"),
        "best_edema_source": selected_sources.get("best_edema_source"),
        "best_two_individual_sources": selected_sources.get("best_two_individual_sources"),
        "two_seed_variant_sources": selected_sources.get("two_seed_variant_sources"),
        "pathology_compositor_calibration": selected_sources.get("pathology_compositor_calibration"),
        "postprocess_selected": postprocess.get("selected"),
        "audit_ranking_rule": "audit_only_after_frozen_calibration_selection_min_delta_then_mean_delta_then_harm_hd95_remote_fp",
        "audit_top_candidate_after_freeze": ranking[0] if ranking else None,
    })
    data["status"] = "WAVE3_SELECTION_RECORDED"
    write_json(path, data)


def rank_rows(summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[tuple[str, str], dict[str, Any]] = defaultdict(dict)
    for r in summary:
        if r["population"] == "audit_positive_gt":
            by[(r["variant"], r["postprocess_id"])][f"{r['pathology']}_audit_dice"] = to_float(r.get("mean_dice"))
            by[(r["variant"], r["postprocess_id"])][f"{r['pathology']}_audit_hd95"] = to_float(r.get("mean_hd95"))
            by[(r["variant"], r["postprocess_id"])][f"{r['pathology']}_audit_harm"] = int(r.get("harm_count_vs_nnunet") or 0)
            by[(r["variant"], r["postprocess_id"])][f"{r['pathology']}_audit_remote_fp"] = to_float(r.get("mean_remote_fp_volume_mm3"))
        if r["population"] == "full44":
            by[(r["variant"], r["postprocess_id"])][f"{r['pathology']}_full44_dice"] = to_float(r.get("mean_dice"))
    base = baseline_split_summary()
    rows = []
    for (candidate, pid), vals in by.items():
        scar_delta = None if vals.get("scar_audit_dice") is None else vals["scar_audit_dice"] - base[("scar", "audit_positive_gt_dice")]
        edema_delta = None if vals.get("edema_audit_dice") is None else vals["edema_audit_dice"] - base[("edema", "audit_positive_gt_dice")]
        rows.append({
            "candidate": candidate,
            "postprocess_id": pid,
            **vals,
            "scar_audit_delta_vs_nnunet": scar_delta,
            "edema_audit_delta_vs_nnunet": edema_delta,
            "minimum_audit_delta_vs_nnunet": min(v for v in [scar_delta, edema_delta] if v is not None),
            "mean_audit_delta_vs_nnunet": mean([scar_delta, edema_delta]),
            "audit_harm_total": int(vals.get("scar_audit_harm") or 0) + int(vals.get("edema_audit_harm") or 0),
            "audit_hd95_sum": float(vals.get("scar_audit_hd95") or 0.0) + float(vals.get("edema_audit_hd95") or 0.0),
            "audit_remote_fp_sum": float(vals.get("scar_audit_remote_fp") or 0.0) + float(vals.get("edema_audit_remote_fp") or 0.0),
        })
    rows.sort(key=lambda r: (to_float(r["minimum_audit_delta_vs_nnunet"]) or -999, to_float(r["mean_audit_delta_vs_nnunet"]) or -999, -int(r["audit_harm_total"]), -float(r["audit_hd95_sum"]), -float(r["audit_remote_fp_sum"])), reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    write_csv(RESULT_ROOT / "full44_candidate_ranking.csv", rows)
    return rows


def near_baseline_gate(ranking: list[dict[str, Any]], casewise: list[dict[str, Any]]) -> dict[str, Any]:
    selected = ranking[0]
    base = baseline_split_summary()
    rows = [r for r in casewise if r["variant"] == selected["candidate"] and r["postprocess_id"] == selected["postprocess_id"] and r["rescue_split"] == "audit"]
    gate = {
        "schema_version": 1,
        "evaluated_on": "rescue_audit",
        "selected_candidate": selected["candidate"],
        "selected_postprocess_id": selected["postprocess_id"],
        "thresholds": {
            "scar_dice_gap_to_nnunet_max": 0.04,
            "edema_dice_gap_to_nnunet_max": 0.03,
            "gt_positive_empty_count_max": 0,
            "no_t2_edema_voxels_max": 0,
            "hd95_relative_worsening_max": 0.10,
        },
        "metrics": {},
        "checks": {},
    }
    passed = True
    for pathology in LABELS:
        subset = [r for r in rows if r["pathology"] == pathology and str(r["gt_positive"]) == "1"]
        dice = mean([r.get("dice") for r in subset])
        hd95 = mean([r.get("hd95") for r in subset])
        base_dice = base[(pathology, "audit_positive_gt_dice")]
        base_hd95 = base[(pathology, "audit_positive_gt_hd95")]
        gap = None if dice is None else base_dice - dice
        hd95_rel = None if hd95 is None or base_hd95 <= 0 else (hd95 - base_hd95) / base_hd95
        empty_count = sum(int(float(r.get("empty_prediction") or 0)) for r in subset)
        key = pathology
        gate["metrics"][key] = {"dice": dice, "baseline_dice": base_dice, "dice_gap_to_nnunet": gap, "hd95": hd95, "baseline_hd95": base_hd95, "hd95_relative_worsening": hd95_rel, "gt_positive_empty_count": empty_count}
        if pathology == "scar":
            ok = gap is not None and gap <= 0.04
        else:
            ok = gap is not None and gap <= 0.03
        ok = ok and empty_count <= 0 and (hd95_rel is not None and hd95_rel <= 0.10)
        gate["checks"][f"{pathology}_near_baseline"] = ok
        passed = passed and ok
    no_t2 = sum(int(float(r.get("no_t2_edema_predicted_voxels") or 0)) for r in rows)
    gate["metrics"]["no_t2_edema_predicted_voxels"] = no_t2
    gate["checks"]["no_t2_safety"] = no_t2 <= 0
    passed = passed and no_t2 <= 0
    gate["status"] = "PASS" if passed else "FAIL"
    gate["training_authorized"] = bool(passed)
    gate["if_fail"] = "skip_all_batch10_training_and_finalize_stop_or_docker_decision"
    write_json(RESULT_ROOT / "near_baseline_gate.json", gate)
    return gate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    started = int(time.time())
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    baseline_rows = read_csv(RESULT_ROOT / "baseline_recomputed_casewise.csv")
    baseline = {(r["case_id"], r["pathology"]): r for r in baseline_rows}
    selected_sources = select_calibration_sources()
    selected_sources["pathology_compositor_calibration"] = select_pathology_compositor_calibration(selected_sources, baseline)
    write_json(RESULT_ROOT / "ensemble_source_selection.json", selected_sources)
    raw_rows, manifest = evaluate_raw_ensembles(selected_sources, baseline)
    _grid, best = run_grid(selected_sources, baseline)
    selected_rows = evaluate_selected(best, selected_sources, baseline, manifest)
    all_rows = raw_rows + selected_rows
    write_csv(RESULT_ROOT / "ensemble_manifest.csv", manifest)
    write_csv(RESULT_ROOT / "ensemble_casewise_metrics.csv", all_rows)
    summary = summarize(all_rows, RESULT_ROOT / "ensemble_summary.csv", source="wave3_probability_ensemble")
    audit_rows = [r for r in summary if r["population"] in {"audit", "audit_positive_gt"}]
    write_csv(RESULT_ROOT / "audit_split_metrics.csv", audit_rows)
    ranking = rank_rows(summary)
    gate = near_baseline_gate(ranking, all_rows)
    postprocess_payload = json.loads((RESULT_ROOT / "postprocess_selected.json").read_text())
    record_wave3_selection_provenance(selected_sources, postprocess_payload, ranking)
    receipt = {
        "schema_version": 1,
        "status": "PASS",
        "started_unix": started,
        "finished_unix": int(time.time()),
        "exact_candidate_set": ENSEMBLE_CANDIDATES,
        "probability_ensemble_only": True,
        "no_nnunet_probability_in_ensemble": True,
        "calibration_only_selects_postprocess": True,
        "audit_split_never_selects_parameters": True,
        "selected_candidate": ranking[0] if ranking else None,
        "near_baseline_gate_status": gate["status"],
        "fusion_space": "common_preprocessed_logits",
        "single_inverse_export_per_ensemble_case": True,
        "postprocess_selection": postprocess_payload.get("selection_uses"),
        "postprocess_raw_fallback_reasons": postprocess_payload.get("selected", {}).get("fallback_reasons", ""),
        "pathology_compositor_mode": "calibration_only_logit_residual_margin_temperature_softmax",
        "pathology_compositor_calibration": selected_sources.get("pathology_compositor_calibration", {}).get("selected"),
    }
    write_json(RESULT_ROOT / "wave3_ensemble_postprocess_receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "near_baseline_gate": gate["status"], "selected": receipt["selected_candidate"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
