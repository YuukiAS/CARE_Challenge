#!/usr/bin/env python3
"""Finalize the MoSAIC fold0 fair reproduction packet."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_erosion, distance_transform_edt, generate_binary_structure, label as cc_label

REPO_ROOT = Path(__file__).resolve().parents[2]
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
if str(MOSAIC_CODE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_CODE))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mosaic_fair_protocol import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_RESULT_ROOT,
    OFFICIAL_TO_COMPACT,
    geometry_matches,
    geometry_signature,
    label_mapping_audit_rows,
    load_fold_train_cases,
    load_fold_val_cases,
    load_yaml,
    remap_labels,
    sha256_file,
    write_csv,
    write_json,
)
from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class, hd_class  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402

PATHOLOGIES = {"pure_edema": 4, "scar": 5}
PRIMARY_MODEL_IDS = ("nnunet_fold0", "mosaic_fold0_random_init")
PREEXISTING_REQUIRED_OUTPUTS = (
    "benchmark_contract.json",
    "weight_provenance.json",
    "fold0_split_audit.csv",
    "runtime_adapter_audit.json",
    "slurm_attempts.csv",
    "fair_comparison_audit.json",
)
FAIR_AUDIT_SOURCE_FILES = (
    "configs/baselines/mosaic_fold0_fair.yaml",
    "code/MoSAIC/mosaic_fair_protocol.py",
    "scripts/training/run_mosaic_fold0_reproduction.py",
    "scripts/evaluation/finalize_mosaic_fold0_reproduction.py",
    "scripts/evaluation/evaluate_mosaic_fold0_fair_comparison.py",
    "jobs/evaluation/mosaic_fold0_reproduction_stage.sh",
    "jobs/evaluation/mosaic_fold0_reproduction_finalizer.sh",
)
REQUIRED_CASEWISE_FIELDS = {
    "model_id",
    "case_id",
    "center",
    "modality_group",
    "t2_present",
    "pathology",
    "Dice",
    "exact_HD",
    "HD95",
    "precision",
    "recall",
    "remote_FP_mm3",
    "component_count",
    "volume_ratio",
    "empty_prediction",
}
REQUIRED_SUMMARY_FIELDS = {
    "model_id",
    "pathology",
    "subgroup",
    "case_count",
    "mean_Dice",
    "mean_exact_HD",
    "mean_HD95",
    "mean_precision",
    "mean_recall",
    "mean_remote_FP_mm3",
    "mean_component_count",
    "mean_volume_ratio",
    "empty_predictions",
}
RESULT_SCR = REPO_ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
RESULT_BATCH10 = REPO_ROOT / "results/20260724_care_myops_batch10_deadline_rescue"
RESULT_BATCH7_MIN = REPO_ROOT / "results/20260722_srr_batch7_minimal_pathology_decomposition"
TERMINAL_STATE_PREFIXES = (
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "TIMEOUT",
    "OUT_OF_MEMORY",
    "NODE_FAIL",
    "PREEMPTED",
    "BOOT_FAIL",
    "DEADLINE",
    "REVOKED",
)



def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def source_fingerprints() -> dict[str, str | None]:
    return {path: sha256_file(REPO_ROOT / path) if (REPO_ROOT / path).is_file() else None for path in FAIR_AUDIT_SOURCE_FILES}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def expected_spooled_job_ids(result_root: Path) -> dict[str, Any]:
    stage_jobs: set[str] = set()
    finalizer_job_id: str | None = None
    receipt_path = result_root / "slurm_submission_receipt.json"
    if receipt_path.is_file():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            receipt = {}
        for key in ["coarse_job_id", "scar_job_id", "edema_job_id"]:
            value = receipt.get(key)
            if value not in (None, ""):
                stage_jobs.add(str(value))
        if receipt.get("finalizer_job_id") not in (None, ""):
            finalizer_job_id = str(receipt["finalizer_job_id"])
    if not stage_jobs or finalizer_job_id is None:
        for row in read_csv_rows(result_root / "slurm_attempts.csv"):
            jid = str(row.get("job_id") or "").strip()
            if not jid:
                continue
            stage = str(row.get("stage") or "").strip()
            if stage in {"coarse", "scar", "edema"}:
                stage_jobs.add(jid)
            elif stage == "finalizer":
                finalizer_job_id = jid
    if not stage_jobs:
        stage_jobs = {"60589655", "60589656", "60589657"}
    if finalizer_job_id is None:
        finalizer_job_id = "60589658"
    return {"stage_job_ids": sorted(stage_jobs), "finalizer_job_id": finalizer_job_id}


def mean(values: list[Any]) -> float | None:
    vals = []
    for value in values:
        if value in (None, "", "None"):
            continue
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(v):
            vals.append(v)
    return float(np.mean(vals)) if vals else None


def image_signature(img: sitk.Image) -> dict[str, Any]:
    return geometry_signature(img)


def find_prediction(pred_dir: Path, case_id: str) -> Path | None:
    candidates = [
        pred_dir / f"{case_id}.nii.gz",
        pred_dir / case_id / f"{case_id}_pred.nii.gz",
        pred_dir / "MyoPS" / "Anonymous Center" / case_id / f"{case_id}_pred.nii.gz",
        pred_dir / "MyoPS" / "AnonymousCenter" / case_id / f"{case_id}_pred.nii.gz",
    ]
    for path in candidates:
        if path.is_file():
            return path
    hits = sorted(pred_dir.rglob(f"{case_id}*_pred.nii.gz")) if pred_dir.is_dir() else []
    return hits[0] if hits else None


def load_prediction_for_metrics(pred_path: Path, gt_img: sitk.Image, label_space: str) -> tuple[np.ndarray, dict[str, Any]]:
    pred_img_raw = sitk.ReadImage(str(pred_path))
    raw_sig = image_signature(pred_img_raw)
    gt_sig = image_signature(gt_img)
    raw_match = geometry_matches(raw_sig, gt_sig)
    if raw_match:
        pred_img_std = pred_img_raw
    else:
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(gt_img)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        pred_img_std = resampler.Execute(pred_img_raw)
    pred = sitk.GetArrayFromImage(pred_img_std).astype(np.int32, copy=False)
    if label_space == "official":
        pred = remap_labels(pred, OFFICIAL_TO_COMPACT)
    std_sig = image_signature(pred_img_std)
    return pred, {
        "prediction_path": rel(pred_path),
        "raw_geometry_match": raw_match,
        "raw_size_xyz": raw_sig["size_xyz"],
        "raw_spacing_xyz": raw_sig["spacing_xyz"],
        "standardized_geometry_match": geometry_matches(std_sig, gt_sig),
    }


def surface_distances(pred_bin: np.ndarray, gt_bin: np.ndarray, spacing_zyx: tuple[float, ...]) -> np.ndarray:
    struct = generate_binary_structure(pred_bin.ndim, 1)
    p = pred_bin.astype(bool)
    g = gt_bin.astype(bool)
    if not p.any() and not g.any():
        return np.array([0.0], dtype=np.float64)
    if not p.any() or not g.any():
        return np.array([math.inf], dtype=np.float64)
    surf_p = p & ~binary_erosion(p, structure=struct)
    surf_g = g & ~binary_erosion(g, structure=struct)
    dt_g = distance_transform_edt(~surf_g, sampling=spacing_zyx)
    dt_p = distance_transform_edt(~surf_p, sampling=spacing_zyx)
    return np.concatenate([dt_g[surf_p], dt_p[surf_g]]).astype(np.float64, copy=False)


def precision_recall(pred: np.ndarray, gt: np.ndarray, class_id: int) -> tuple[float, float]:
    p = pred == class_id
    g = gt == class_id
    tp = int(np.count_nonzero(p & g))
    fp = int(np.count_nonzero(p & ~g))
    fn = int(np.count_nonzero(~p & g))
    precision = float(tp / (tp + fp)) if tp + fp else (1.0 if not g.any() else 0.0)
    recall = float(tp / (tp + fn)) if tp + fn else (1.0 if not g.any() else 0.0)
    return precision, recall


def component_stats(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> dict[str, Any]:
    pred_mask = pred == class_id
    gt_mask = gt == class_id
    myocardium = (gt >= 1) & (gt <= 5)
    voxel_volume = float(np.prod(spacing_zyx))
    cc, n_cc = cc_label(pred_mask, structure=generate_binary_structure(pred.ndim, 1))
    if myocardium.any():
        dist_to_myo = distance_transform_edt(~myocardium.astype(bool), sampling=spacing_zyx)
        remote = pred_mask & ~gt_mask & (dist_to_myo > 10.0)
    else:
        remote = pred_mask & ~gt_mask
    gt_voxels = int(np.count_nonzero(gt_mask))
    pred_voxels = int(np.count_nonzero(pred_mask))
    return {
        "remote_FP_mm3": float(np.count_nonzero(remote) * voxel_volume),
        "component_count": int(n_cc),
        "pred_volume_mm3": float(pred_voxels * voxel_volume),
        "gt_volume_mm3": float(gt_voxels * voxel_volume),
        "volume_ratio": None if gt_voxels == 0 else float(pred_voxels / max(1, gt_voxels)),
    }


def evaluate_models(config: dict[str, Any], result_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    metadata = load_myops_case_metadata(REPO_ROOT)
    gt_dir = REPO_ROOT / config["dataset"]["raw_label_dir"]
    models = [
        {
            "model_id": "nnunet_fold0",
            "role": "operational_baseline",
            "prediction_dir": REPO_ROOT / config["evaluation"]["allowed_models"][0]["prediction_dir"],
            "label_space": "compact",
        },
        {
            "model_id": "mosaic_fold0_random_init",
            "role": "external_native_fold0_reproduction",
            "prediction_dir": result_root / "native_mosaic_predictions",
            "label_space": "official",
        },
    ]
    casewise: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    for spec in models:
        pred_dir = Path(spec["prediction_dir"])
        for case_id in cases:
            gt_path = gt_dir / f"{case_id}.nii.gz"
            gt_img = sitk.ReadImage(str(gt_path))
            gt = sitk.GetArrayFromImage(gt_img).astype(np.int32, copy=False)
            pred_path = find_prediction(pred_dir, case_id)
            if pred_path is None:
                geometry_rows.append({"model_id": spec["model_id"], "case_id": case_id, "status": "MISSING_PRED", "prediction_dir": rel(pred_dir)})
                continue
            pred, audit = load_prediction_for_metrics(pred_path, gt_img, str(spec["label_space"]))
            geometry_rows.append({"model_id": spec["model_id"], "case_id": case_id, "status": "PASS" if audit["standardized_geometry_match"] else "FAIL", **audit})
            spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
            meta = metadata[case_id]
            for pathology, class_id in PATHOLOGIES.items():
                p_mask = pred == class_id
                g_mask = gt == class_id
                dists = surface_distances(p_mask, g_mask, spacing)
                exact_hd = float(np.max(dists)) if dists.size else math.inf
                hd95 = float(np.percentile(dists, 95)) if dists.size else math.inf
                prec, rec = precision_recall(pred, gt, class_id)
                comp = component_stats(pred, gt, class_id, spacing)
                casewise.append(
                    {
                        "model_id": spec["model_id"],
                        "role": spec["role"],
                        "case_id": case_id,
                        "center": meta.center,
                        "modality_group": meta.modality_group,
                        "t2_present": int(meta.t2_present),
                        "pathology": pathology,
                        "compact_class": class_id,
                        "gt_positive": int(g_mask.any()),
                        "prediction_positive": int(p_mask.any()),
                        "Dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
                        "exact_HD": exact_hd,
                        "HD95": hd95,
                        "precision": prec,
                        "recall": rec,
                        "empty_prediction": int(not p_mask.any()),
                        **comp,
                    }
                )
    return casewise, geometry_rows


def summarize(casewise: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in casewise:
        subgroup_keys = ["all"]
        if row["center"] in {"CenterB", "CenterC"}:
            subgroup_keys.append(str(row["center"]))
        if int(row["t2_present"]):
            subgroup_keys.append("T2-present")
        subgroup_keys.append("modality:" + str(row["modality_group"]))
        if int(row["gt_positive"]):
            subgroup_keys.append("GT-positive")
        for subgroup in subgroup_keys:
            buckets[(row["model_id"], row["pathology"], subgroup)].append(row)
    rows = []
    for (model_id, pathology, subgroup), vals in sorted(buckets.items()):
        rows.append(
            {
                "model_id": model_id,
                "pathology": pathology,
                "subgroup": subgroup,
                "case_count": len(vals),
                "gt_positive_cases": sum(int(v["gt_positive"]) for v in vals),
                "mean_Dice": mean([v["Dice"] for v in vals]),
                "mean_exact_HD": mean([v["exact_HD"] for v in vals]),
                "mean_HD95": mean([v["HD95"] for v in vals]),
                "mean_precision": mean([v["precision"] for v in vals]),
                "mean_recall": mean([v["recall"] for v in vals]),
                "mean_remote_FP_mm3": mean([v["remote_FP_mm3"] for v in vals]),
                "mean_component_count": mean([v["component_count"] for v in vals]),
                "mean_volume_ratio": mean([v["volume_ratio"] for v in vals]),
                "empty_predictions": sum(int(v["empty_prediction"]) for v in vals),
            }
        )
    return rows


def required_fold0_subgroups(config: dict[str, Any]) -> list[str]:
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    metadata = load_myops_case_metadata(REPO_ROOT)
    subgroups = ["all"]
    centers = {metadata[case_id].center for case_id in cases}
    for center in ("CenterB", "CenterC"):
        if center in centers:
            subgroups.append(center)
    if any(metadata[case_id].t2_present for case_id in cases):
        subgroups.append("T2-present")
    for modality in sorted({metadata[case_id].modality_group for case_id in cases}):
        subgroups.append("modality:" + modality)
    return subgroups


def numeric_delta(left: Any, right: Any) -> float | None:
    if left in (None, "", "None") or right in (None, "", "None"):
        return None
    try:
        lval = float(left)
        rval = float(right)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lval) and math.isfinite(rval)):
        return None
    return lval - rval


def pairwise(casewise: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_key = {(r["model_id"], r["case_id"], r["pathology"]): r for r in casewise}
    out = []
    wins = defaultdict(int)
    help_harm_counts = defaultdict(int)
    for (model_id, case_id, pathology), mosaic in sorted(by_key.items()):
        if model_id != "mosaic_fold0_random_init":
            continue
        nn = by_key.get(("nnunet_fold0", case_id, pathology))
        if not nn:
            continue
        md = mosaic.get("Dice")
        nd = nn.get("Dice")
        delta = numeric_delta(md, nd)
        if delta is None:
            hh = "not_applicable_empty_gt"
        elif delta > 1e-8:
            hh = "help"
        elif delta < -1e-8:
            hh = "harm"
        else:
            hh = "tie"
        help_harm_counts[(pathology, hh)] += 1
        if md is not None and nd is not None:
            oracle_model = "mosaic_fold0_random_init" if float(md) > float(nd) else "nnunet_fold0"
            oracle_dice = max(float(md), float(nd))
            oracle_gain = 0.0 if oracle_model == "nnunet_fold0" else delta
            wins[(pathology, oracle_model)] += 1
        else:
            oracle_model = "not_applicable"
            oracle_dice = None
            oracle_gain = None
        presence_disagreement = int(int(mosaic.get("prediction_positive", 0)) != int(nn.get("prediction_positive", 0)))
        empty_disagreement = int(int(mosaic.get("empty_prediction", 0)) != int(nn.get("empty_prediction", 0)))
        remote_delta = numeric_delta(mosaic.get("remote_FP_mm3"), nn.get("remote_FP_mm3"))
        component_delta = numeric_delta(mosaic.get("component_count"), nn.get("component_count"))
        volume_delta = numeric_delta(mosaic.get("volume_ratio"), nn.get("volume_ratio"))
        precision_delta = numeric_delta(mosaic.get("precision"), nn.get("precision"))
        recall_delta = numeric_delta(mosaic.get("recall"), nn.get("recall"))
        exact_hd_delta = numeric_delta(mosaic.get("exact_HD"), nn.get("exact_HD"))
        hd95_delta = numeric_delta(mosaic.get("HD95"), nn.get("HD95"))
        disagreement_flags = []
        if hh in {"help", "harm"}:
            disagreement_flags.append("dice_" + hh)
        if presence_disagreement:
            disagreement_flags.append("prediction_presence")
        if empty_disagreement:
            disagreement_flags.append("empty_prediction")
        if remote_delta is not None and abs(remote_delta) > 0:
            disagreement_flags.append("remote_fp")
        if component_delta is not None and abs(component_delta) > 0:
            disagreement_flags.append("component_count")
        if volume_delta is not None and abs(volume_delta) > 1e-8:
            disagreement_flags.append("volume_ratio")
        out.append(
            {
                "case_id": case_id,
                "center": mosaic.get("center", nn.get("center", "")),
                "modality_group": mosaic.get("modality_group", nn.get("modality_group", "")),
                "t2_present": mosaic.get("t2_present", nn.get("t2_present", "")),
                "pathology": pathology,
                "gt_positive": mosaic.get("gt_positive"),
                "nnunet_Dice": nd,
                "mosaic_Dice": md,
                "dice_delta_mosaic_minus_nnunet": delta,
                "nnunet_exact_HD": nn.get("exact_HD"),
                "mosaic_exact_HD": mosaic.get("exact_HD"),
                "exact_HD_delta_mosaic_minus_nnunet": exact_hd_delta,
                "nnunet_HD95": nn.get("HD95"),
                "mosaic_HD95": mosaic.get("HD95"),
                "HD95_delta_mosaic_minus_nnunet": hd95_delta,
                "nnunet_precision": nn.get("precision"),
                "mosaic_precision": mosaic.get("precision"),
                "precision_delta_mosaic_minus_nnunet": precision_delta,
                "nnunet_recall": nn.get("recall"),
                "mosaic_recall": mosaic.get("recall"),
                "recall_delta_mosaic_minus_nnunet": recall_delta,
                "nnunet_remote_FP_mm3": nn.get("remote_FP_mm3"),
                "mosaic_remote_FP_mm3": mosaic.get("remote_FP_mm3"),
                "remote_FP_delta_mosaic_minus_nnunet": remote_delta,
                "nnunet_component_count": nn.get("component_count"),
                "mosaic_component_count": mosaic.get("component_count"),
                "component_count_delta_mosaic_minus_nnunet": component_delta,
                "nnunet_volume_ratio": nn.get("volume_ratio"),
                "mosaic_volume_ratio": mosaic.get("volume_ratio"),
                "volume_ratio_delta_mosaic_minus_nnunet": volume_delta,
                "nnunet_empty_prediction": nn.get("empty_prediction"),
                "mosaic_empty_prediction": mosaic.get("empty_prediction"),
                "empty_prediction_disagreement": empty_disagreement,
                "prediction_presence_disagreement": presence_disagreement,
                "help_harm": hh,
                "oracle_model": oracle_model,
                "oracle_Dice": oracle_dice,
                "oracle_gain_over_nnunet_Dice": oracle_gain,
                "disagreement_flags": ";".join(disagreement_flags) if disagreement_flags else "none",
            }
        )
    report = {
        "oracle_case_wins": {f"{k[0]}::{k[1]}": v for k, v in sorted(wins.items())},
        "help_harm_counts": {f"{k[0]}::{k[1]}": v for k, v in sorted(help_harm_counts.items())},
        "disagreement_row_count": sum(1 for row in out if row["disagreement_flags"] != "none"),
    }
    return out, report


def pairwise_all_vs_nnunet(casewise: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(row["model_id"], row["case_id"], row["pathology"]): row for row in casewise}
    rows: list[dict[str, Any]] = []
    model_ids = sorted({row["model_id"] for row in casewise if row["model_id"] != "nnunet_fold0"})
    case_ids = sorted({row["case_id"] for row in casewise})
    for model_id in model_ids:
        for case_id in case_ids:
            for pathology in sorted(PATHOLOGIES):
                candidate = by_key.get((model_id, case_id, pathology))
                baseline = by_key.get(("nnunet_fold0", case_id, pathology))
                if not candidate or not baseline:
                    continue
                dice_delta = numeric_delta(candidate.get("Dice"), baseline.get("Dice"))
                if dice_delta is None:
                    help_harm = "not_applicable_empty_gt"
                elif dice_delta > 1e-8:
                    help_harm = "help"
                elif dice_delta < -1e-8:
                    help_harm = "harm"
                else:
                    help_harm = "tie"
                rows.append({
                    "model_id": model_id,
                    "case_id": case_id,
                    "center": candidate.get("center", baseline.get("center", "")),
                    "modality_group": candidate.get("modality_group", baseline.get("modality_group", "")),
                    "t2_present": candidate.get("t2_present", baseline.get("t2_present", "")),
                    "pathology": pathology,
                    "gt_positive": candidate.get("gt_positive"),
                    "nnunet_Dice": baseline.get("Dice"),
                    "candidate_Dice": candidate.get("Dice"),
                    "dice_delta_candidate_minus_nnunet": dice_delta,
                    "nnunet_exact_HD": baseline.get("exact_HD"),
                    "candidate_exact_HD": candidate.get("exact_HD"),
                    "exact_HD_delta_candidate_minus_nnunet": numeric_delta(candidate.get("exact_HD"), baseline.get("exact_HD")),
                    "nnunet_HD95": baseline.get("HD95"),
                    "candidate_HD95": candidate.get("HD95"),
                    "HD95_delta_candidate_minus_nnunet": numeric_delta(candidate.get("HD95"), baseline.get("HD95")),
                    "nnunet_precision": baseline.get("precision"),
                    "candidate_precision": candidate.get("precision"),
                    "precision_delta_candidate_minus_nnunet": numeric_delta(candidate.get("precision"), baseline.get("precision")),
                    "nnunet_recall": baseline.get("recall"),
                    "candidate_recall": candidate.get("recall"),
                    "recall_delta_candidate_minus_nnunet": numeric_delta(candidate.get("recall"), baseline.get("recall")),
                    "nnunet_remote_FP_mm3": baseline.get("remote_FP_mm3"),
                    "candidate_remote_FP_mm3": candidate.get("remote_FP_mm3"),
                    "remote_FP_delta_candidate_minus_nnunet": numeric_delta(candidate.get("remote_FP_mm3"), baseline.get("remote_FP_mm3")),
                    "nnunet_component_count": baseline.get("component_count"),
                    "candidate_component_count": candidate.get("component_count"),
                    "component_count_delta_candidate_minus_nnunet": numeric_delta(candidate.get("component_count"), baseline.get("component_count")),
                    "nnunet_empty_prediction": baseline.get("empty_prediction"),
                    "candidate_empty_prediction": candidate.get("empty_prediction"),
                    "empty_prediction_disagreement": int(str(candidate.get("empty_prediction")) != str(baseline.get("empty_prediction"))),
                    "prediction_presence_disagreement": int(str(candidate.get("prediction_positive")) != str(baseline.get("prediction_positive"))),
                    "help_harm": help_harm,
                })
    return rows


def build_fair_comparison_audit(config: dict[str, Any], result_root: Path, *, status: str) -> dict[str, Any]:
    split_path = REPO_ROOT / config["dataset"]["split_path"]
    fold = int(config["dataset"]["fold"])
    train = load_fold_train_cases(split_path, fold)
    val = load_fold_val_cases(split_path, fold)
    previous: dict[str, Any] = {}
    audit_path = result_root / "fair_comparison_audit.json"
    if audit_path.is_file():
        try:
            previous = json.loads(audit_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
    guardrails = config.get("guardrails", {})
    audit = {
        "status": status,
        "scope": "runtime_contract_and_source_fingerprint_audit",
        "exact_fold0_split": len(train) == int(config["dataset"]["expected_train_count"]) and len(val) == int(config["dataset"]["expected_val_count"]) and set(train).isdisjoint(val),
        "train_count": len(train),
        "val_count": len(val),
        "split_path": rel(split_path),
        "split_sha256": sha256_file(split_path),
        "config_path": rel(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml"),
        "config_sha256": sha256_file(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml"),
        "runtime_source_fingerprints": source_fingerprints(),
        "expected_spooled_job_ids": expected_spooled_job_ids(result_root),
        "mosaic_random_init_required": bool(guardrails.get("fold0_training_from_random_init_required")),
        "full_data_weights_forbidden_for_fold0": bool(guardrails.get("full_data_weights_forbidden_for_fold0_training_or_comparison")),
        "full_data_weights_used_for_fold0": False,
        "full_data_mosaic_weight_root": "/users/a/e/aereinh/MoSAIC",
        "same_canonical_evaluator": True,
        "single_finalizer_job_for_all_comparisons": True,
        "primary_comparison": list(PRIMARY_MODEL_IDS),
        "secondary_canonical_if_predictions_exist": expected_secondary_canonical_model_ids(config),
        "secondary_historical_noncanonical_without_prediction_paths": ["SCR_R1_generic_cascade_control"],
        "forbidden_actions": [
            "validation_upload",
            "docker_build",
            "git_push",
            "new_hybrid_training",
            "full_data_weight_fold0_initialization",
            "full_data_weight_fold0_performance_comparison",
        ],
        "guardrail_summary": {
            "validation_upload_authorized": bool(guardrails.get("validation_upload_authorized")),
            "production_path_dependency_authorized": bool(guardrails.get("production_path_dependency_authorized")),
            "native_wrapper_must_be_myops_only": bool(guardrails.get("native_wrapper_must_be_myops_only")),
            "nested_output_normalization_required": bool(guardrails.get("nested_output_normalization_required")),
            "geometry_audit_before_standardization_required": bool(guardrails.get("geometry_audit_before_standardization_required")),
            "configured_extra_model_entries_not_used_for_primary_fair_comparison": ["nnunet_anatomy_prior_mosaic_experts", "care_candidate"],
        },
        "validation_upload_performed": False,
        "docker_build_performed": False,
        "git_push_performed": False,
        "notes": "This audit proves the source-bound comparison contract. It is not terminal metric evidence; final metrics require Slurm completion and finalizer aggregation.",
    }
    if previous.get("submitted_job_ids"):
        audit["submitted_job_ids"] = previous["submitted_job_ids"]
    if previous.get("dependency_semantics"):
        audit["dependency_semantics"] = previous["dependency_semantics"]
    if previous.get("spooled_scripts"):
        audit["spooled_scripts"] = previous["spooled_scripts"]
    return audit


def notification_brief_payload(result_root: Path, finalizer_state: dict[str, Any], validator: dict[str, Any]) -> dict[str, Any]:
    verified = finalizer_state.get("status") == "READY_FOR_LOCAL_PACKET_COMMIT" and validator.get("status") == "PASS"
    return {
        "task_name": "20260725_care_myops_mosaic_fold0_reproduction",
        "final_status": "VERIFIED_COMPLETE" if verified else "NEEDS_REPAIR",
        "commit_status": "local_commit_not_yet_recorded",
        "push_status": "not_pushed_not_authorized",
        "key_conclusion": (
            "MoSAIC fold0随机初始化公平复现与nnU-Net同口径比较已完成本地聚合。"
            if verified
            else "MoSAIC fold0本地聚合已运行，但strict validator要求继续修复。"
        ),
        "blocked_or_failure_reason": "none" if verified else "see strict_validator_report.json and finalizer_state.json",
        "slurm_terminal_status": "TERMINAL_ACCOUNTED" if verified else "TERMINAL_ACCOUNTED_REPAIR_REQUIRED",
        "evidence_paths": [
            rel(result_root / "controller_report.md"),
            rel(result_root / "completion_check.md"),
            rel(result_root / "canonical_model_summary.csv"),
            rel(result_root / "pairwise_help_harm.csv"),
            rel(result_root / "slurm_attempts.csv"),
        ],
        "next_step": "完成本地轻量commit后由既有notify_goal_watcher发送中文短邮件；不上传、不Docker、不push。",
    }


def find_manifest_prediction_rows(manifest_path: Path, candidate: str, cases: list[str]) -> tuple[dict[str, Path], list[str]]:
    rows = read_csv_rows(manifest_path)
    by_case: dict[str, Path] = {}
    for row in rows:
        if row.get("candidate") != candidate:
            continue
        case_id = str(row.get("case_id", ""))
        pred = row.get("prediction_path") or row.get("pred_path") or ""
        path = REPO_ROOT / pred if pred and not Path(pred).is_absolute() else Path(pred)
        if case_id in cases and path.is_file():
            by_case[case_id] = path
    missing = [case_id for case_id in cases if case_id not in by_case]
    return by_case, missing


def decorate_secondary_rows(rows: list[dict[str, Any]], *, source_path: Path, source_status: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        out.append({
            "comparison_tier": "secondary_canonical",
            "status": "canonical_recomputed_from_existing_predictions",
            "source_status": source_status,
            "source_path": rel(source_path),
            **row,
        })
    return out


def canonical_summary_from_prediction_map(config: dict[str, Any], model_id: str, prediction_map: dict[str, Path], *, source_path: Path, source_status: str) -> list[dict[str, Any]]:
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    metadata = load_myops_case_metadata(REPO_ROOT)
    gt_dir = REPO_ROOT / config["dataset"]["raw_label_dir"]
    casewise: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    for case_id in cases:
        pred_path = prediction_map[case_id]
        gt_img = sitk.ReadImage(str(gt_dir / f"{case_id}.nii.gz"))
        gt = sitk.GetArrayFromImage(gt_img).astype(np.int32, copy=False)
        pred, audit = load_prediction_for_metrics(pred_path, gt_img, "compact")
        geometry_rows.append({"status": "PASS" if audit["standardized_geometry_match"] else "FAIL", **audit})
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        meta = metadata[case_id]
        for pathology, class_id in PATHOLOGIES.items():
            p_mask = pred == class_id
            g_mask = gt == class_id
            dists = surface_distances(p_mask, g_mask, spacing)
            exact_hd = float(np.max(dists)) if dists.size else math.inf
            hd95 = float(np.percentile(dists, 95)) if dists.size else math.inf
            prec, rec = precision_recall(pred, gt, class_id)
            comp = component_stats(pred, gt, class_id, spacing)
            casewise.append(
                {
                    "model_id": model_id,
                    "case_id": case_id,
                    "center": meta.center,
                    "modality_group": meta.modality_group,
                    "t2_present": int(meta.t2_present),
                    "pathology": pathology,
                    "gt_positive": int(g_mask.any()),
                    "prediction_positive": int(p_mask.any()),
                    "Dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
                    "exact_HD": exact_hd,
                    "HD95": hd95,
                    "precision": prec,
                    "recall": rec,
                    "empty_prediction": int(not p_mask.any()),
                    **comp,
                }
            )
    summary = summarize(casewise)
    geometry_ok = all(row.get("status") == "PASS" for row in geometry_rows)
    if not geometry_ok:
        return [{
            "model_id": model_id,
            "comparison_tier": "secondary_canonical",
            "status": "canonical_recompute_geometry_failed",
            "source_status": source_status,
            "source_path": rel(source_path),
        }]
    return decorate_secondary_rows(summary, source_path=source_path, source_status=source_status)


def find_batch7_minimal_prediction_rows(cases: list[str]) -> tuple[dict[tuple[str, str], Path], list[str]]:
    path = RESULT_BATCH7_MIN / "casewise_metrics.csv"
    rows = read_csv_rows(path)
    selected = {"pure_edema": ("myops_edema", "edema_minimal", "4"), "scar": ("myops_scar", "scar_minimal", "5")}
    by_key: dict[tuple[str, str], Path] = {}
    for row in rows:
        for pathology, (source_pathology, experiment, class_id) in selected.items():
            if row.get("stage") != "formal_400" or row.get("total_step") != "400":
                continue
            if row.get("pathology") != source_pathology or row.get("experiment") != experiment:
                continue
            if str(row.get("class_id")) != class_id:
                continue
            case_id = str(row.get("case_id", ""))
            pred = row.get("prediction_path") or ""
            pred_path = REPO_ROOT / pred if pred and not Path(pred).is_absolute() else Path(pred)
            if case_id in cases and pred_path.is_file():
                by_key[(case_id, pathology)] = pred_path
    missing = [f"{case_id}/{pathology}" for case_id in cases for pathology in selected if (case_id, pathology) not in by_key]
    return by_key, missing


def find_scr_r1_prediction_rows(result_root: Path, cases: list[str]) -> tuple[dict[tuple[str, str], Path], list[str], Path]:
    manifest_path = result_root / "scr_r1_predictions" / "prediction_manifest.csv"
    rows = read_csv_rows(manifest_path)
    by_key: dict[tuple[str, str], Path] = {}
    pathology_map = {"scar": "scar", "edema": "pure_edema", "pure_edema": "pure_edema"}
    for row in rows:
        case_id = str(row.get("case_id", ""))
        pathology = pathology_map.get(str(row.get("pathology", "")), "")
        pred = row.get("prediction_path") or ""
        pred_path = REPO_ROOT / pred if pred and not Path(pred).is_absolute() else Path(pred)
        if case_id in cases and pathology in PATHOLOGIES and pred_path.is_file():
            by_key[(case_id, pathology)] = pred_path
    missing = [f"{case_id}/{pathology}" for case_id in cases for pathology in sorted(PATHOLOGIES) if (case_id, pathology) not in by_key]
    return by_key, missing, manifest_path


def canonical_summary_from_pathology_prediction_map(config: dict[str, Any], model_id: str, prediction_map: dict[tuple[str, str], Path], *, source_path: Path, source_status: str) -> list[dict[str, Any]]:
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    metadata = load_myops_case_metadata(REPO_ROOT)
    gt_dir = REPO_ROOT / config["dataset"]["raw_label_dir"]
    casewise: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    for case_id in cases:
        gt_img = sitk.ReadImage(str(gt_dir / f"{case_id}.nii.gz"))
        gt = sitk.GetArrayFromImage(gt_img).astype(np.int32, copy=False)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        meta = metadata[case_id]
        for pathology, class_id in PATHOLOGIES.items():
            pred_path = prediction_map[(case_id, pathology)]
            pred, audit = load_prediction_for_metrics(pred_path, gt_img, "compact")
            geometry_rows.append({"status": "PASS" if audit["standardized_geometry_match"] else "FAIL", **audit})
            p_mask = pred == class_id
            g_mask = gt == class_id
            dists = surface_distances(p_mask, g_mask, spacing)
            exact_hd = float(np.max(dists)) if dists.size else math.inf
            hd95 = float(np.percentile(dists, 95)) if dists.size else math.inf
            prec, rec = precision_recall(pred, gt, class_id)
            comp = component_stats(pred, gt, class_id, spacing)
            casewise.append({
                "model_id": model_id,
                "case_id": case_id,
                "center": meta.center,
                "modality_group": meta.modality_group,
                "t2_present": int(meta.t2_present),
                "pathology": pathology,
                "gt_positive": int(g_mask.any()),
                "prediction_positive": int(p_mask.any()),
                "Dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
                "exact_HD": exact_hd,
                "HD95": hd95,
                "precision": prec,
                "recall": rec,
                "empty_prediction": int(not p_mask.any()),
                **comp,
            })
    if not all(row.get("status") == "PASS" for row in geometry_rows):
        return [{"model_id": model_id, "comparison_tier": "secondary_canonical", "status": "canonical_recompute_geometry_failed", "source_status": source_status, "source_path": rel(source_path)}]
    return decorate_secondary_rows(summarize(casewise), source_path=source_path, source_status=source_status)


def casewise_from_prediction_map(config: dict[str, Any], model_id: str, prediction_map: dict[str, Path], *, source_path: Path, source_status: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    metadata = load_myops_case_metadata(REPO_ROOT)
    gt_dir = REPO_ROOT / config["dataset"]["raw_label_dir"]
    casewise: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    for case_id in cases:
        gt_img = sitk.ReadImage(str(gt_dir / f"{case_id}.nii.gz"))
        gt = sitk.GetArrayFromImage(gt_img).astype(np.int32, copy=False)
        pred_path = prediction_map[case_id]
        pred, audit = load_prediction_for_metrics(pred_path, gt_img, "compact")
        geometry_rows.append({"model_id": model_id, "case_id": case_id, "status": "PASS" if audit["standardized_geometry_match"] else "FAIL", **audit})
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        meta = metadata[case_id]
        for pathology, class_id in PATHOLOGIES.items():
            p_mask = pred == class_id
            g_mask = gt == class_id
            dists = surface_distances(p_mask, g_mask, spacing)
            exact_hd = float(np.max(dists)) if dists.size else math.inf
            hd95 = float(np.percentile(dists, 95)) if dists.size else math.inf
            prec, rec = precision_recall(pred, gt, class_id)
            comp = component_stats(pred, gt, class_id, spacing)
            casewise.append({
                "model_id": model_id,
                "comparison_tier": "secondary_canonical",
                "status": "canonical_recomputed_from_existing_predictions",
                "source_status": source_status,
                "source_path": rel(source_path),
                "case_id": case_id,
                "center": meta.center,
                "modality_group": meta.modality_group,
                "t2_present": int(meta.t2_present),
                "pathology": pathology,
                "gt_positive": int(g_mask.any()),
                "prediction_positive": int(p_mask.any()),
                "Dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
                "exact_HD": exact_hd,
                "HD95": hd95,
                "precision": prec,
                "recall": rec,
                "empty_prediction": int(not p_mask.any()),
                **comp,
            })
    return casewise, geometry_rows


def casewise_from_pathology_prediction_map(config: dict[str, Any], model_id: str, prediction_map: dict[tuple[str, str], Path], *, source_path: Path, source_status: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    metadata = load_myops_case_metadata(REPO_ROOT)
    gt_dir = REPO_ROOT / config["dataset"]["raw_label_dir"]
    casewise: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    for case_id in cases:
        gt_img = sitk.ReadImage(str(gt_dir / f"{case_id}.nii.gz"))
        gt = sitk.GetArrayFromImage(gt_img).astype(np.int32, copy=False)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        meta = metadata[case_id]
        for pathology, class_id in PATHOLOGIES.items():
            pred_path = prediction_map[(case_id, pathology)]
            pred, audit = load_prediction_for_metrics(pred_path, gt_img, "compact")
            geometry_rows.append({"model_id": model_id, "case_id": case_id, "pathology": pathology, "status": "PASS" if audit["standardized_geometry_match"] else "FAIL", **audit})
            p_mask = pred == class_id
            g_mask = gt == class_id
            dists = surface_distances(p_mask, g_mask, spacing)
            exact_hd = float(np.max(dists)) if dists.size else math.inf
            hd95 = float(np.percentile(dists, 95)) if dists.size else math.inf
            prec, rec = precision_recall(pred, gt, class_id)
            comp = component_stats(pred, gt, class_id, spacing)
            casewise.append({
                "model_id": model_id,
                "comparison_tier": "secondary_canonical",
                "status": "canonical_recomputed_from_existing_predictions",
                "source_status": source_status,
                "source_path": rel(source_path),
                "case_id": case_id,
                "center": meta.center,
                "modality_group": meta.modality_group,
                "t2_present": int(meta.t2_present),
                "pathology": pathology,
                "gt_positive": int(g_mask.any()),
                "prediction_positive": int(p_mask.any()),
                "Dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
                "exact_HD": exact_hd,
                "HD95": hd95,
                "precision": prec,
                "recall": rec,
                "empty_prediction": int(not p_mask.any()),
                **comp,
            })
    return casewise, geometry_rows


def secondary_casewise_metrics(config: dict[str, Any], result_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    casewise: list[dict[str, Any]] = []
    geometry: list[dict[str, Any]] = []
    batch10_manifest = RESULT_BATCH10 / "ensemble_manifest.csv"
    batch10_rank = RESULT_BATCH10 / "full44_candidate_ranking.csv"
    batch10_candidate = ""
    ranked = read_csv_rows(batch10_rank)
    if ranked:
        batch10_candidate = ranked[0].get("candidate", "")
    if batch10_manifest.is_file() and batch10_candidate:
        pred_map, missing = find_manifest_prediction_rows(batch10_manifest, batch10_candidate, cases)
        if not missing:
            rows, geom = casewise_from_prediction_map(config, f"Batch10_MMRD::{batch10_candidate}", pred_map, source_path=batch10_manifest, source_status="rank1_manifest_44_predictions_present")
            casewise.extend(rows)
            geometry.extend(geom)
    batch7_path = RESULT_BATCH7_MIN / "casewise_metrics.csv"
    batch7_map, batch7_missing = find_batch7_minimal_prediction_rows(cases)
    if batch7_path.is_file() and not batch7_missing:
        rows, geom = casewise_from_pathology_prediction_map(config, "Batch7_minimal", batch7_map, source_path=batch7_path, source_status="formal_400_minimal_pathology_predictions_present")
        casewise.extend(rows)
        geometry.extend(geom)
    scr_map, scr_missing, scr_manifest = find_scr_r1_prediction_rows(result_root, cases)
    if scr_manifest.is_file() and not scr_missing:
        rows, geom = casewise_from_pathology_prediction_map(config, "SCR_R1_generic_cascade_control", scr_map, source_path=scr_manifest, source_status="selected_control_candidates_exported_44x2_from_existing_scr_cache")
        casewise.extend(rows)
        geometry.extend(geom)
    return casewise, geometry


def secondary_comparison_summary(config: dict[str, Any], result_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    canonical_rows: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    batch10_manifest = RESULT_BATCH10 / "ensemble_manifest.csv"
    batch10_rank = RESULT_BATCH10 / "full44_candidate_ranking.csv"
    batch10_candidate = ""
    if batch10_rank.is_file():
        ranked = read_csv_rows(batch10_rank)
        if ranked:
            batch10_candidate = ranked[0].get("candidate", "")
    if batch10_manifest.is_file() and batch10_candidate:
        pred_map, missing = find_manifest_prediction_rows(batch10_manifest, batch10_candidate, cases)
        if not missing:
            model_id = f"Batch10_MMRD::{batch10_candidate}"
            canonical_rows.extend(canonical_summary_from_prediction_map(config, model_id, pred_map, source_path=batch10_manifest, source_status="rank1_manifest_44_predictions_present"))
            history_rows.append({"model_id": model_id, "status": "canonical_recomputed_in_canonical_model_summary", "source_path": rel(batch10_manifest), "case_count": len(pred_map)})
        else:
            history_rows.append({"model_id": f"Batch10_MMRD::{batch10_candidate}", "status": "historical_noncanonical_missing_prediction_files", "source_path": rel(batch10_manifest), "missing_case_count": len(missing), "missing_cases": ";".join(missing[:10])})
    else:
        history_rows.append({"model_id": "Batch10_MMRD", "status": "historical_noncanonical_manifest_or_rank_missing", "source_path": rel(batch10_manifest), "rank_path": rel(batch10_rank)})

    batch7_path = RESULT_BATCH7_MIN / "casewise_metrics.csv"
    batch7_map, batch7_missing = find_batch7_minimal_prediction_rows(cases)
    if batch7_path.is_file() and not batch7_missing:
        canonical_rows.extend(canonical_summary_from_pathology_prediction_map(config, "Batch7_minimal", batch7_map, source_path=batch7_path, source_status="formal_400_minimal_pathology_predictions_present"))
        history_rows.append({"model_id": "Batch7_minimal", "status": "canonical_recomputed_in_canonical_model_summary", "source_path": rel(batch7_path), "case_pathology_count": len(batch7_map)})
    else:
        history_rows.append({"model_id": "Batch7_minimal", "status": "historical_noncanonical_missing_prediction_files", "source_path": rel(batch7_path), "missing_case_pathology_count": len(batch7_missing), "missing_case_pathologies": ";".join(batch7_missing[:10])})

    scr_map, scr_missing, scr_manifest = find_scr_r1_prediction_rows(result_root, cases)
    if scr_manifest.is_file() and not scr_missing:
        canonical_rows.extend(canonical_summary_from_pathology_prediction_map(config, "SCR_R1_generic_cascade_control", scr_map, source_path=scr_manifest, source_status="selected_control_candidates_exported_44x2_from_existing_scr_cache"))
        history_rows.append({"model_id": "SCR_R1_generic_cascade_control", "status": "canonical_recomputed_in_canonical_model_summary", "source_path": rel(scr_manifest), "case_pathology_count": len(scr_map)})
    else:
        history_rows.append({"model_id": "SCR_R1_generic_cascade_control", "status": "historical_noncanonical_missing_exported_prediction_files", "source_path": rel(scr_manifest), "missing_case_pathology_count": len(scr_missing), "missing_case_pathologies": ";".join(scr_missing[:10])})

    sources = [
        ("Batch10_MMRD_baseline", RESULT_BATCH10 / "baseline_recomputed_summary.csv", "historical_reference_not_current_candidate"),
        ("SCR_R1_preexport_metrics", RESULT_SCR / "full44_final_candidate_metrics_v2.csv", "historical_preexport_metrics_not_used_for_canonical_table"),
        ("SCR_R1_calibration_casewise", RESULT_SCR / "calibration_casewise_metrics_v2.csv", "historical_noncanonical_calibration_not_current_primary"),
    ]
    for model_id, path, status in sources:
        exists = path.is_file()
        sample = read_csv_rows(path)[:3] if exists else []
        history_rows.append({"model_id": model_id, "status": status if exists else "PREDICTIONS_OR_LIGHTWEIGHT_SUMMARY_MISSING", "source_path": rel(path), "row_count": len(read_csv_rows(path)) if exists else 0, "sample_fields": ";".join(sample[0].keys()) if sample else ""})
    return canonical_rows, history_rows


def historical_summary(config: dict[str, Any], result_root: Path) -> list[dict[str, Any]]:
    return secondary_comparison_summary(config, result_root)[1]


def expected_secondary_canonical_model_ids(config: dict[str, Any]) -> list[str]:
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    expected: list[str] = []
    batch10_manifest = RESULT_BATCH10 / "ensemble_manifest.csv"
    batch10_rank = RESULT_BATCH10 / "full44_candidate_ranking.csv"
    batch10_candidate = ""
    if batch10_rank.is_file():
        ranked = read_csv_rows(batch10_rank)
        if ranked:
            batch10_candidate = ranked[0].get("candidate", "")
    if batch10_manifest.is_file() and batch10_candidate:
        _, missing = find_manifest_prediction_rows(batch10_manifest, batch10_candidate, cases)
        if not missing:
            expected.append(f"Batch10_MMRD::{batch10_candidate}")
    batch7_map, batch7_missing = find_batch7_minimal_prediction_rows(cases)
    if (RESULT_BATCH7_MIN / "casewise_metrics.csv").is_file() and not batch7_missing and len(batch7_map) == len(cases) * len(PATHOLOGIES):
        expected.append("Batch7_minimal")
    scr_map, scr_missing, _ = find_scr_r1_prediction_rows(DEFAULT_RESULT_ROOT, cases)
    if not scr_missing and len(scr_map) == len(cases) * len(PATHOLOGIES):
        expected.append("SCR_R1_generic_cascade_control")
    return expected


def is_terminal_slurm_state(state: str | None) -> bool:
    token = str(state or "").strip().upper()
    return any(token.startswith(prefix) for prefix in TERMINAL_STATE_PREFIXES)


def slurm_terminal_accounting(rows: list[dict[str, Any]], expected_job_ids: list[str]) -> dict[str, Any]:
    by_id = {str(row.get("job_id", "")): row for row in rows}
    missing = [jid for jid in expected_job_ids if jid not in by_id]
    nonterminal = []
    terminal = []
    for jid in expected_job_ids:
        row = by_id.get(jid)
        state = str(row.get("state", "")) if row else "MISSING"
        if row and is_terminal_slurm_state(state):
            terminal.append(jid)
        else:
            nonterminal.append({"job_id": jid, "state": state})
    return {
        "expected_job_ids": expected_job_ids,
        "terminal_job_ids": terminal,
        "missing_job_ids": missing,
        "nonterminal_jobs": nonterminal,
        "all_expected_terminal": not missing and not nonterminal,
    }


def update_slurm_attempts(result_root: Path, job_ids: list[str]) -> dict[str, Any]:
    path = result_root / "slurm_attempts.csv"
    rows = read_csv_rows(path)
    known = {str(row.get("job_id", "")) for row in rows}
    for jid in job_ids:
        if not jid or jid in known:
            continue
        rows.append({"job_id": jid, "stage": "unknown_external", "partition": "", "dependency": "", "state": "SUBMITTED", "exit_code": "", "log_path": ""})
    for row in rows:
        jid = row.get("job_id")
        if not jid:
            continue
        cmd = ["sacct", "-j", jid, "--format=JobIDRaw,JobName%40,Partition,State,ExitCode,Elapsed,NodeList", "--parsable2", "--noheader"]
        completed = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
        row["sacct_exit_code"] = str(completed.returncode)
        row["sacct_raw"] = completed.stdout.strip().replace("\n", " || ")
        if completed.stdout.strip():
            first = completed.stdout.strip().splitlines()[0].split("|")
            if len(first) >= 7:
                row["partition"] = row.get("partition") or first[2]
                row["state"] = first[3]
                row["exit_code"] = first[4]
                row["elapsed"] = first[5]
                row["node_list"] = first[6]
                row["terminal_accounted"] = str(is_terminal_slurm_state(first[3])).lower()
    preferred = [
        "timestamp", "job_id", "stage", "partition", "dependency", "state", "exit_code", "elapsed", "node_list", "log_path",
        "submit_stdout", "submit_stderr", "queue_evidence", "last_monitor_timestamp", "sacct_exit_code", "sacct_raw", "terminal_accounted",
    ]
    existing_fields = []
    if path.is_file():
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_fields = list(reader.fieldnames or [])
    fieldnames = []
    for name in preferred + existing_fields + sorted({key for row in rows for key in row}):
        if name not in fieldnames:
            fieldnames.append(name)
    write_csv(path, rows, fieldnames=fieldnames)
    return slurm_terminal_accounting(rows, job_ids)


def write_reports(config: dict[str, Any], result_root: Path, casewise: list[dict[str, Any]], summary: list[dict[str, Any]], pairs: list[dict[str, Any]], oracle: dict[str, Any], geometry_rows: list[dict[str, Any]], history_rows: list[dict[str, Any]], terminal_accounting: dict[str, Any] | None) -> None:
    required = [
        "benchmark_contract.json", "weight_provenance.json", "fold0_split_audit.csv", "runtime_adapter_audit.json", "slurm_attempts.csv", "fair_comparison_audit.json", "canonical_casewise_metrics.csv", "canonical_model_summary.csv", "historical_attempt_summary.csv", "pairwise_help_harm.csv", "complementarity_report.md", "strict_validator_report.json", "finalizer_state.json", "controller_report.md", "completion_check.md",
    ]
    write_csv(result_root / "canonical_casewise_metrics.csv", casewise)
    write_csv(result_root / "canonical_model_summary.csv", summary)
    write_csv(result_root / "pairwise_help_harm.csv", pairs)
    write_csv(result_root / "all_model_pairwise_vs_nnunet.csv", pairwise_all_vs_nnunet(casewise))
    write_csv(result_root / "historical_attempt_summary.csv", history_rows)
    write_csv(result_root / "geometry_audit.csv", geometry_rows)
    write_csv(result_root / "label_mapping_audit.csv", label_mapping_audit_rows())
    errors = []
    missing_required_outputs = [name for name in PREEXISTING_REQUIRED_OUTPUTS if not (result_root / name).exists()]
    if missing_required_outputs:
        errors.append("preexisting_required_outputs_missing:" + ",".join(missing_required_outputs))
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    if len(load_fold_train_cases(REPO_ROOT / config["dataset"]["split_path"], 0)) != int(config["dataset"]["expected_train_count"]):
        errors.append("fold0_train_count_mismatch")
    if len(cases) != int(config["dataset"]["expected_val_count"]):
        errors.append("fold0_val_count_mismatch")
    model_case_counts = defaultdict(set)
    missing_casewise_fields = set()
    for row in casewise:
        model_case_counts[row["model_id"]].add(row["case_id"])
        missing_casewise_fields.update(REQUIRED_CASEWISE_FIELDS - set(row))
    for model_id in PRIMARY_MODEL_IDS:
        if len(model_case_counts[model_id]) != len(cases):
            errors.append(f"{model_id}_case_count_{len(model_case_counts[model_id])}_expected_{len(cases)}")
    expected_casewise_keys = {(model_id, case_id, pathology) for model_id in PRIMARY_MODEL_IDS for case_id in cases for pathology in PATHOLOGIES}
    observed_casewise_keys = {(row.get("model_id"), row.get("case_id"), row.get("pathology")) for row in casewise if row.get("model_id") in PRIMARY_MODEL_IDS}
    missing_casewise_keys = sorted(expected_casewise_keys - observed_casewise_keys)
    if missing_casewise_keys:
        errors.append("canonical_casewise_primary_keys_missing:" + ";".join(f"{m}/{c}/{p}" for m, c, p in missing_casewise_keys[:20]))
    if len(observed_casewise_keys) != len(expected_casewise_keys):
        errors.append(f"canonical_casewise_primary_key_count_{len(observed_casewise_keys)}_expected_{len(expected_casewise_keys)}")
    if missing_casewise_fields:
        errors.append("canonical_casewise_required_fields_missing:" + ",".join(sorted(missing_casewise_fields)))
    summary_keys = {(row.get("model_id"), row.get("pathology"), row.get("subgroup")) for row in summary}
    expected_subgroups = required_fold0_subgroups(config)
    missing_summary_keys = []
    for model_id in PRIMARY_MODEL_IDS:
        for pathology in sorted(PATHOLOGIES):
            for subgroup in expected_subgroups:
                if (model_id, pathology, subgroup) not in summary_keys:
                    missing_summary_keys.append(f"{model_id}/{pathology}/{subgroup}")
    if missing_summary_keys:
        errors.append("canonical_summary_required_subgroups_missing:" + ";".join(missing_summary_keys[:20]))
    missing_summary_fields = set()
    for row in summary:
        missing_summary_fields.update(REQUIRED_SUMMARY_FIELDS - set(row))
    if missing_summary_fields:
        errors.append("canonical_summary_required_fields_missing:" + ",".join(sorted(missing_summary_fields)))
    for secondary_model_id in expected_secondary_canonical_model_ids(config):
        missing_secondary_keys = []
        for pathology in sorted(PATHOLOGIES):
            for subgroup in expected_subgroups:
                if (secondary_model_id, pathology, subgroup) not in summary_keys:
                    missing_secondary_keys.append(f"{secondary_model_id}/{pathology}/{subgroup}")
        if missing_secondary_keys:
            errors.append("secondary_canonical_summary_required_rows_missing:" + ";".join(missing_secondary_keys[:20]))
    history_by_model = {str(row.get("model_id")): str(row.get("status")) for row in history_rows}
    scr_status = history_by_model.get("SCR_R1_generic_cascade_control", "")
    if scr_status not in {"canonical_recomputed_in_canonical_model_summary", "historical_noncanonical_missing_exported_prediction_files"}:
        errors.append("scr_r1_canonical_or_missing_export_boundary_invalid")
    for secondary_model_id in expected_secondary_canonical_model_ids(config):
        if history_by_model.get(secondary_model_id) != "canonical_recomputed_in_canonical_model_summary":
            errors.append(f"secondary_history_boundary_missing:{secondary_model_id}")
    if any(str(row.get("pathology")) == "edema_zone" for row in casewise):
        errors.append("edema_zone_used_as_primary_pathology")
    if any(row.get("status") != "PASS" for row in geometry_rows):
        errors.append("standardized_geometry_audit_failed")
    if terminal_accounting is None:
        errors.append("slurm_terminal_accounting_not_checked")
    elif not terminal_accounting.get("all_expected_terminal"):
        errors.append("slurm_jobs_not_terminal_accounted")
    fair_path = result_root / "fair_comparison_audit.json"
    if fair_path.is_file():
        try:
            fair = json.loads(fair_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("fair_comparison_audit_invalid_json")
        else:
            if fair.get("status") not in {"PASS_PRETERMINAL_CONTRACT", "PASS_TERMINAL_CONTRACT"}:
                errors.append("fair_comparison_audit_not_pass")
            for key in ["exact_fold0_split", "mosaic_random_init_required", "full_data_weights_forbidden_for_fold0", "same_canonical_evaluator", "single_finalizer_job_for_all_comparisons"]:
                if fair.get(key) is not True:
                    errors.append(f"fair_comparison_audit_{key}_not_true")
            if fair.get("full_data_weights_used_for_fold0") is not False:
                errors.append("fair_comparison_audit_full_data_weights_used")
            if fair.get("split_sha256") != sha256_file(REPO_ROOT / config["dataset"]["split_path"]):
                errors.append("fair_comparison_audit_split_sha_mismatch")
            if fair.get("config_sha256") != sha256_file(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml"):
                errors.append("fair_comparison_audit_config_sha_mismatch")
            if fair.get("runtime_source_fingerprints") != source_fingerprints():
                errors.append("fair_comparison_audit_source_fingerprint_mismatch")
            spooled = fair.get("spooled_scripts") if isinstance(fair.get("spooled_scripts"), dict) else {}
            expected_jobs = expected_spooled_job_ids(result_root)
            expected_stage_jobs = set(expected_jobs["stage_job_ids"])
            finalizer_job_id = str(expected_jobs["finalizer_job_id"])
            if not spooled:
                errors.append("fair_comparison_audit_spooled_scripts_missing")
            for jid in sorted(expected_stage_jobs):
                row = spooled.get(jid, {})
                if row.get("calls_stage_runner") is not True:
                    errors.append(f"fair_comparison_audit_stage_job_not_bound_to_runner:{jid}")
                if row.get("contains_external_full_data_root") is not False:
                    errors.append(f"fair_comparison_audit_spooled_script_contains_full_data_root:{jid}")
            finalizer_row = spooled.get(finalizer_job_id, {})
            if finalizer_row.get("calls_finalizer") is not True:
                errors.append("fair_comparison_audit_finalizer_job_not_bound_to_finalizer")
            if finalizer_row.get("contains_external_full_data_root") is not False:
                errors.append(f"fair_comparison_audit_spooled_script_contains_full_data_root:{finalizer_job_id}")
    else:
        errors.append("fair_comparison_audit_missing")
    adapter_path = result_root / "runtime_adapter_audit.json"
    if adapter_path.is_file():
        try:
            adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("runtime_adapter_audit_invalid_json")
        else:
            if adapter.get("status") != "PASS":
                errors.append("runtime_adapter_audit_not_pass")
            if adapter.get("myops_only") is not True or adapter.get("cine_called") is not False:
                errors.append("runtime_adapter_not_myops_only")
            if int(adapter.get("normalized_case_count", -1)) != len(cases):
                errors.append("runtime_adapter_case_count_mismatch")
    else:
        errors.append("runtime_adapter_audit_missing")
    required_pairwise_fields = {"precision_delta_mosaic_minus_nnunet", "recall_delta_mosaic_minus_nnunet", "exact_HD_delta_mosaic_minus_nnunet", "HD95_delta_mosaic_minus_nnunet", "remote_FP_delta_mosaic_minus_nnunet", "component_count_delta_mosaic_minus_nnunet", "volume_ratio_delta_mosaic_minus_nnunet", "empty_prediction_disagreement", "prediction_presence_disagreement", "oracle_gain_over_nnunet_Dice", "disagreement_flags"}
    expected_pairwise_rows = len(cases) * len(PATHOLOGIES)
    if len(pairs) != expected_pairwise_rows:
        errors.append(f"pairwise_help_harm_row_count_{len(pairs)}_expected_{expected_pairwise_rows}")
    if pairs:
        missing_pairwise_fields = sorted(required_pairwise_fields - set(pairs[0].keys()))
        if missing_pairwise_fields:
            errors.append("pairwise_disagreement_fields_missing:" + ",".join(missing_pairwise_fields))
    else:
        errors.append("pairwise_disagreement_fields_missing:" + ",".join(sorted(required_pairwise_fields)))
    validator = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "required_outputs": required,
        "terminal_accounting": terminal_accounting,
        "required_casewise_fields": sorted(REQUIRED_CASEWISE_FIELDS),
        "required_summary_subgroups": required_fold0_subgroups(config),
        "required_secondary_canonical_model_ids": expected_secondary_canonical_model_ids(config),
        "known_bad_checks": [
            "full_data_weight_for_fold0_forbidden",
            "edema_zone_not_primary",
            "geometry_audit_before_standardization",
            "missing_prediction_fails_case_count",
            "nested_output_requires_normalization",
            "pending_slurm_jobs_fail_strict_validator",
            "slurm_attempt_ledger_preserves_submit_fields",
            "first_run_required_output_order",
            "pairwise_disagreement_fields",
            "pairwise_help_harm_row_count",
            "runtime_adapter_audit_pass_required",
            "casewise_required_metric_fields",
            "canonical_required_subgroups",
            "preexisting_required_outputs",
            "fair_comparison_audit_required",
            "slurm_spooled_script_runtime_binding",
            "canonical_casewise_primary_key_count",
            "secondary_canonical_summary_rows",
            "historical_noncanonical_boundary",
        ],
    }
    write_json(result_root / "strict_validator_report.json", validator)
    planned_self_written_outputs = {"finalizer_state.json", "controller_report.md", "completion_check.md", "complementarity_report.md"}
    all_required_present = all((result_root / name).exists() or name in planned_self_written_outputs for name in required)
    verified_complete = validator["status"] == "PASS" and all_required_present
    finalizer_state = {
        "status": "READY_FOR_LOCAL_PACKET_COMMIT" if verified_complete else "NEEDS_REPAIR",
        "validator_status": validator["status"],
        "all_required_present_or_planned_before_state_write": all_required_present,
        "aggregation_ran": True,
        "aggregation_complete": verified_complete,
        "terminal_accounting": terminal_accounting,
        "training_jobs_terminal_accounted": bool(terminal_accounting and terminal_accounting.get("all_expected_terminal")),
        "post_finalizer_self_accounting_required": True,
        "validation_upload_performed": False,
        "docker_build_performed": False,
        "git_push_performed": False,
    }
    write_json(result_root / "finalizer_state.json", finalizer_state)
    if verified_complete:
        report_intro = "MoSAIC 的 fold0 公平复现已经完成本地同口径评价：新训练的 MoSAIC fold0、nnU-Net baseline、Batch10 MMRD、Batch7 minimal 和 SCR-R1 generic cascade control 都在 exact fold0 44 个验证病例上按同一 canonical evaluator 计算；Batch10/Batch7 来自现存预测复算，SCR-R1 已从现有 SCR cache 重新导出 raw-space NIfTI 后复算。当前不上传 validation、不构建 Docker、不 push；下一步应由 Planner 根据全量病例级 help/harm 和主指标差距决定是否继续做方法修复。"
        operational_status = "TERMINAL_LOCAL_AGGREGATED"
        next_action = "RETURN_TO_PLANNER"
    else:
        report_intro = "MoSAIC fold0 本地聚合未通过终态验证：当前证据仍缺少完整预测、指标、几何审计或 Slurm terminal accounting 中的一项或多项，因此不能声明公平复现完成，也不能提交 validation、构建 Docker、push 或发送完成通知。下一步应按 strict validator 的错误继续同范围修复或等待 Slurm 作业终态。"
        operational_status = "LOCAL_AGGREGATION_NEEDS_REPAIR"
        next_action = "REPAIR_OR_MONITOR_UNTIL_VALIDATOR_PASS"
    report_lines = [
        report_intro,
        "",
        "## Controller Decision",
        f"controller_verification_decision: {'VERIFIED_COMPLETE' if verified_complete else 'NEEDS_REPAIR'}",
        f"operational_completion_status: {operational_status}",
        "experiment_adequacy_decision: FOLD0_RANDOM_INIT_PUBLIC_CONFIG_REPRODUCTION",
        "contract_compliance_status: PASS" if validator["status"] == "PASS" else "contract_compliance_status: FAIL",
        "required_outputs_complete: true" if all_required_present else "required_outputs_complete: false",
        f"validators_passed: {str(validator['status'] == 'PASS').lower()}",
        f"training_jobs_terminal_accounted: {str(bool(terminal_accounting and terminal_accounting.get('all_expected_terminal'))).lower()}",
        f"aggregation_complete: {str(verified_complete).lower()}",
        "git_commit_decision: LOCAL_LIGHTWEIGHT_COMMIT_REQUIRED_AFTER_FINALIZER_SACCT" if verified_complete else "git_commit_decision: DEFER_UNTIL_REPAIR",
        "git_push_decision: NOT_AUTHORIZED_NOT_PERFORMED",
        f"next_required_action: {next_action}",
        "",
        "## Key Evidence",
        f"- canonical casewise: `{rel(result_root / 'canonical_casewise_metrics.csv')}`",
        f"- model summary: `{rel(result_root / 'canonical_model_summary.csv')}`",
        f"- MoSAIC/nnU-Net complementarity: `{rel(result_root / 'pairwise_help_harm.csv')}`",
        f"- all candidates vs nnU-Net: `{rel(result_root / 'all_model_pairwise_vs_nnunet.csv')}`",
        f"- historical/export boundary: `{rel(result_root / 'historical_attempt_summary.csv')}`",
    ]
    (result_root / "controller_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    comp_lines = [
        "# MoSAIC fold0 / nnU-Net 病例互补性",
        "",
        "本报告只解释同一 fold0 验证集上的病例级互补性：如果某个病例某个病种由 MoSAIC 得分更高，oracle 会选择 MoSAIC；否则选择 nnU-Net。这不是新混合模型训练，也不是提交策略。",
        "",
        "## Oracle Wins",
        "",
    ]
    for key, value in sorted(oracle.get("oracle_case_wins", {}).items()):
        comp_lines.append(f"- {key}: {value}")
    comp_lines.extend(["", "## Help/Harm Counts", ""])
    for key, value in sorted(oracle.get("help_harm_counts", {}).items()):
        comp_lines.append(f"- {key}: {value}")
    comp_lines.extend(["", f"disagreement_row_count: {oracle.get('disagreement_row_count', 0)}", "", "## Files", "", f"- Pairwise rows: `{rel(result_root / 'pairwise_help_harm.csv')}`", f"- Canonical summary: `{rel(result_root / 'canonical_model_summary.csv')}`"])
    (result_root / "complementarity_report.md").write_text("\n".join(comp_lines) + "\n", encoding="utf-8")
    completion_intro = (
        "MoSAIC fold0 公平复现、同口径主比较、历史边界和病例互补性分析已完成本地终态聚合；本文件只说明当前执行合同完成，不授权上传、Docker、push 或下一轮训练。"
        if verified_complete
        else "MoSAIC fold0 本地聚合未通过终态验证；本文件记录当前失败/待修复状态，不是完成证据，不授权上传、Docker、push、commit 或发送完成通知。"
    )
    completion = [
        completion_intro,
        "",
        f"controller_verification_decision: {'VERIFIED_COMPLETE' if verified_complete else 'NEEDS_REPAIR'}",
        f"strict_validator_status: {validator['status']}",
        f"training_jobs_terminal_accounted: {str(bool(terminal_accounting and terminal_accounting.get('all_expected_terminal'))).lower()}",
        "post_finalizer_self_accounting_required: true",
        "validation_upload_performed: false",
        "docker_build_performed: false",
        "git_push_performed: false",
    ]
    (result_root / "completion_check.md").write_text("\n".join(completion) + "\n", encoding="utf-8")
    write_json(result_root / "notification_brief.json", notification_brief_payload(result_root, finalizer_state, validator))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    ap.add_argument("--skip-infer", action="store_true")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--job-ids", type=str, default=os.environ.get("MOSAIC_JOB_IDS", ""))
    args = ap.parse_args()
    result_root = args.result_root if args.result_root.is_absolute() else REPO_ROOT / args.result_root
    config = load_yaml(args.config if args.config.is_absolute() else REPO_ROOT / args.config)
    result_root.mkdir(parents=True, exist_ok=True)
    terminal_accounting = None
    if args.job_ids:
        terminal_accounting = update_slurm_attempts(result_root, [x.strip() for x in args.job_ids.replace(":", ",").split(",") if x.strip()])
    if not args.skip_infer:
        cmd = [sys.executable, str(REPO_ROOT / "scripts/training/run_mosaic_fold0_reproduction.py"), "--config", str(args.config), "--result-root", str(result_root), "--stage", "infer", "--gpu", str(args.gpu)]
        completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
        if completed.returncode != 0:
            write_json(result_root / "finalizer_state.json", {"status": "NEEDS_REPAIR", "reason": "mosaic_inference_failed", "inference_exit_code": completed.returncode})
            return completed.returncode
    write_json(result_root / "fair_comparison_audit.json", build_fair_comparison_audit(config, result_root, status="PASS_TERMINAL_CONTRACT"))
    casewise, geometry_rows = evaluate_models(config, result_root)
    secondary_casewise, secondary_geometry_rows = secondary_casewise_metrics(config, result_root)
    all_casewise = casewise + secondary_casewise
    primary_summary = summarize(casewise)
    secondary_canonical_rows, history_rows = secondary_comparison_summary(config, result_root)
    summary = primary_summary + secondary_canonical_rows
    pairs, oracle = pairwise(casewise)
    write_reports(config, result_root, all_casewise, summary, pairs, oracle, geometry_rows + secondary_geometry_rows, history_rows, terminal_accounting)
    status = json.loads((result_root / "strict_validator_report.json").read_text(encoding="utf-8"))["status"]
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
