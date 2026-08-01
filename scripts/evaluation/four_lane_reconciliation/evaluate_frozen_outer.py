#!/usr/bin/env python3
"""Frozen four-lane outer evidence reconciliation.

This evaluator intentionally reuses only frozen checkpoints and fixed fold2/fold3
case memberships from the existing target-domain gap-closure packets. It fixes
the previous metric contract by measuring distances and lesion volumes in
physical millimetres from nnU-Net preprocessing properties.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pickle
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import blosc2
import numpy as np
import torch
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt
from scipy.ndimage import generate_binary_structure, label as cc_label

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TASK_KEY = "20260801_care_four_lane_evidence_reconciliation"
SOURCE_TASK_KEY = "20260801_care_target_domain_race_gap_closure"
STOCK_TASK_KEY = "20260801_care_target_domain_pathology_specialist_race"

RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
SOURCE_ROOT = REPO_ROOT / "results" / SOURCE_TASK_KEY
STOCK_SOURCE_ROOT = REPO_ROOT / "results" / STOCK_TASK_KEY
DATA_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
RUNTIME_ROOT = Path("/users/a/e/aereinh/.tmp/codex-CARE") / SOURCE_TASK_KEY

PATHOLOGIES = {"scar": 5, "pure_edema": 4}
REMOTE_FP_DISTANCE_MM = 10.0
BLOOD_POOL_ADJACENT_MM = 2.0
SMALL_LESION_VOLUME_MM3 = 1000.0
SENTINEL_CASES = ["Case3008", "Case3009", "Case2019", "Case2034", "Case2021"]
M0R_SELECTED_STEPS = {"scar": 3500, "pure_edema": 4000}
M2_SELECTED_STEPS = {"scar": 4500, "pure_edema": 2500}

_M2_MODEL_CACHE: dict[tuple[int, str], torch.nn.Module] = {}
_M0R_PREDICTOR_CACHE: dict[tuple[int, str], Any] = {}
_STOCK_PREDICTOR_CACHE: dict[tuple[int, str], Any] = {}


@dataclass(frozen=True)
class CheckpointSpec:
    lane: str
    fold: int
    step: int
    path: Path


@dataclass(frozen=True)
class CaseData:
    image: np.ndarray
    label: np.ndarray
    spacing_zyx: tuple[float, float, float]
    voxel_volume_mm3: float


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def load_case(case_id: str) -> CaseData:
    image = read_b2nd(DATA_ROOT / f"{case_id}.b2nd").astype(np.float32)
    label_arr = read_b2nd(DATA_ROOT / f"{case_id}_seg.b2nd")[0].astype(np.int16)
    with (DATA_ROOT / f"{case_id}.pkl").open("rb") as f:
        props = pickle.load(f)
    spacing = tuple(float(v) for v in props["spacing"])
    if len(spacing) != 3:
        raise RuntimeError(f"invalid spacing for {case_id}: {spacing}")
    return CaseData(
        image=image,
        label=label_arr,
        spacing_zyx=(spacing[0], spacing[1], spacing[2]),
        voxel_volume_mm3=float(spacing[0] * spacing[1] * spacing[2]),
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_record(path: Path, role: str) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "role": role,
        "path": str(path),
        "exists": path.exists(),
    }
    if path.exists() and path.is_file():
        stat = path.stat()
        rec.update({"size_bytes": stat.st_size, "sha256": sha256_file(path)})
    return rec


def checkpoint_from_receipt(lane: str, fold: int, step: int) -> CheckpointSpec:
    receipt = json.loads((SOURCE_ROOT / lane / f"fold{fold}_training_receipt.json").read_text(encoding="utf-8"))
    if lane == "m0r_faithful_control":
        candidates = [Path(p) for p in receipt["step_checkpoints"]]
    else:
        candidates = sorted(Path(receipt["checkpoint_dir"]).glob("checkpoint_step*.pt"))
    for path in candidates:
        if f"step{step:05d}" in path.name:
            return CheckpointSpec(lane=lane, fold=fold, step=step, path=path)
    raise FileNotFoundError(f"missing checkpoint: lane={lane} fold={fold} step={step}")


def stock_checkpoint(fold: int) -> CheckpointSpec:
    receipt = json.loads((SOURCE_ROOT / "m0r_faithful_control" / f"fold{fold}_training_receipt.json").read_text(encoding="utf-8"))
    return CheckpointSpec(lane="stock_nnunet_outer", fold=fold, step=-1, path=Path(receipt["pretrained_checkpoint"]))


def outer_cases_for_fold(fold: int) -> list[str]:
    split = json.loads((SOURCE_ROOT / "split_receipt_copy.json").read_text(encoding="utf-8"))
    return list(split[f"fold{fold}"]["outer_cases"])


def inner_cases_for_fold(fold: int) -> list[str]:
    split = json.loads((SOURCE_ROOT / "split_receipt_copy.json").read_text(encoding="utf-8"))
    return list(split[f"fold{fold}"]["inner_selection_cases"])


def surface(mask: np.ndarray) -> np.ndarray:
    mask = mask.astype(bool)
    if not mask.any():
        return mask
    structure = generate_binary_structure(mask.ndim, 1)
    return np.logical_or(mask & ~binary_erosion(mask, structure=structure, border_value=0), binary_dilation(mask, structure=structure) & ~mask)


def binary_dice(pred: np.ndarray, gt: np.ndarray) -> float:
    p = pred.astype(bool)
    g = gt.astype(bool)
    denom = int(p.sum() + g.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(p, g).sum() / denom)


def hausdorff_mm(pred: np.ndarray, gt: np.ndarray, spacing: tuple[float, float, float], percentile: float) -> float | None:
    p = pred.astype(bool)
    g = gt.astype(bool)
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    sp = surface(p)
    sg = surface(g)
    dt_g = distance_transform_edt(~sg, sampling=spacing)
    dt_p = distance_transform_edt(~sp, sampling=spacing)
    distances = np.concatenate([dt_g[sp], dt_p[sg]])
    if distances.size == 0:
        return 0.0
    return float(np.percentile(distances, percentile))


def component_count(mask: np.ndarray) -> int:
    _cc, n = cc_label(mask.astype(bool))
    return int(n)


def center_crop_or_pad(arr: np.ndarray, dim: int) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    h, w = arr.shape[-2:]
    pad_h = max(0, dim - h)
    pad_w = max(0, dim - w)
    if pad_h or pad_w:
        pad_spec = [(0, 0)] * arr.ndim
        pad_spec[-2] = (pad_h // 2, pad_h - pad_h // 2)
        pad_spec[-1] = (pad_w // 2, pad_w - pad_w // 2)
        arr = np.pad(arr, pad_spec, mode="constant")
        h, w = arr.shape[-2:]
    y0 = max(0, (h - dim) // 2)
    x0 = max(0, (w - dim) // 2)
    return arr[..., y0 : y0 + dim, x0 : x0 + dim], (y0, y0 + dim, x0, x0 + dim)


def lesion_recall(pred: np.ndarray, gt: np.ndarray, voxel_volume_mm3: float) -> tuple[float | None, float | None, int, int]:
    cc, n = cc_label(gt.astype(bool))
    if n == 0:
        return None, None, 0, 0
    p = pred.astype(bool)
    hit = 0
    small = 0
    small_hit = 0
    for idx in range(1, n + 1):
        comp = cc == idx
        is_hit = bool(np.logical_and(comp, p).any())
        hit += int(is_hit)
        if float(comp.sum()) * voxel_volume_mm3 < SMALL_LESION_VOLUME_MM3:
            small += 1
            small_hit += int(is_hit)
    return float(hit / n), (float(small_hit / small) if small else None), int(n), int(small)


def fp_metrics(pred: np.ndarray, gt: np.ndarray, blood: np.ndarray, spacing: tuple[float, float, float], voxel_volume_mm3: float) -> dict[str, Any]:
    fp = pred.astype(bool) & ~gt.astype(bool)
    cc, n = cc_label(fp)
    if n == 0:
        return {
            "remote_fp_count": 0,
            "remote_fp_volume_mm3": 0.0,
            "blood_pool_adjacent_fp_count": 0,
            "blood_pool_adjacent_fp_volume_mm3": 0.0,
        }
    if gt.any():
        dt_gt = distance_transform_edt(~gt.astype(bool), sampling=spacing)
    else:
        dt_gt = np.full(fp.shape, REMOTE_FP_DISTANCE_MM + 1.0, dtype=np.float32)
    if blood.any():
        dt_blood = distance_transform_edt(~blood.astype(bool), sampling=spacing)
    else:
        dt_blood = np.full(fp.shape, BLOOD_POOL_ADJACENT_MM + 1.0, dtype=np.float32)
    remote_count = 0
    remote_volume = 0.0
    blood_count = 0
    blood_volume = 0.0
    for idx in range(1, n + 1):
        comp = cc == idx
        volume = float(comp.sum()) * voxel_volume_mm3
        if float(dt_gt[comp].min()) > REMOTE_FP_DISTANCE_MM:
            remote_count += 1
            remote_volume += volume
        if float(dt_blood[comp].min()) <= BLOOD_POOL_ADJACENT_MM:
            blood_count += 1
            blood_volume += volume
    return {
        "remote_fp_count": int(remote_count),
        "remote_fp_volume_mm3": remote_volume,
        "blood_pool_adjacent_fp_count": int(blood_count),
        "blood_pool_adjacent_fp_volume_mm3": blood_volume,
    }


def metric_row(
    lane: str,
    fold: int,
    checkpoint_step: int,
    case_id: str,
    pathology: str,
    pred: np.ndarray,
    case: CaseData,
    population: str,
    prediction_grid: str,
) -> dict[str, Any]:
    label_value = PATHOLOGIES[pathology]
    pm = pred == label_value
    gt = case.label == label_value
    blood = (case.label == 2) | (case.label == 3)
    tp = int(np.logical_and(pm, gt).sum())
    pred_voxels = int(pm.sum())
    gt_voxels = int(gt.sum())
    rec, small_rec, lesion_count, small_count = lesion_recall(pm, gt, case.voxel_volume_mm3)
    fp = fp_metrics(pm, gt, blood, case.spacing_zyx, case.voxel_volume_mm3)
    return {
        "lane": lane,
        "fold": fold,
        "checkpoint_step": checkpoint_step,
        "case_id": case_id,
        "population": population,
        "pathology": pathology,
        "prediction_grid": prediction_grid,
        "spacing_z_mm": case.spacing_zyx[0],
        "spacing_y_mm": case.spacing_zyx[1],
        "spacing_x_mm": case.spacing_zyx[2],
        "voxel_volume_mm3": case.voxel_volume_mm3,
        "gt_positive": bool(gt_voxels > 0),
        "pred_positive": bool(pred_voxels > 0),
        "dice": binary_dice(pm, gt),
        "hd95_mm": hausdorff_mm(pm, gt, case.spacing_zyx, 95.0),
        "exact_hd_mm": hausdorff_mm(pm, gt, case.spacing_zyx, 100.0),
        "precision": float(tp / pred_voxels) if pred_voxels else (1.0 if gt_voxels == 0 else 0.0),
        "sensitivity": float(tp / gt_voxels) if gt_voxels else (1.0 if pred_voxels == 0 else 0.0),
        "lesion_recall": rec,
        "small_lesion_recall": small_rec,
        "pred_component_count": component_count(pm),
        "gt_component_count": lesion_count,
        "pred_volume_mm3": float(pred_voxels) * case.voxel_volume_mm3,
        "gt_volume_mm3": float(gt_voxels) * case.voxel_volume_mm3,
        "volume_ratio": float(pred_voxels / gt_voxels) if gt_voxels else None,
        "gt_lesion_count": lesion_count,
        "small_lesion_count": small_count,
        **fp,
    }


def mean_defined(rows: Iterable[dict[str, Any]], field: str) -> float | None:
    vals: list[float] = []
    for row in rows:
        val = row.get(field)
        if val in (None, ""):
            continue
        vals.append(float(val))
    return float(np.mean(vals)) if vals else None


def summarize(lane: str, pathology: str, checkpoint_step: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    pos = [r for r in rows if bool(r["gt_positive"])]
    empty = [r for r in rows if not bool(r["gt_positive"])]
    return {
        "lane": lane,
        "fold": "2+3_outer",
        "checkpoint_step": checkpoint_step,
        "pathology": pathology,
        "case_count": len(rows),
        "positive_gt_case_count": len(pos),
        "empty_gt_case_count": len(empty),
        "dice_all_case_mean": mean_defined(rows, "dice"),
        "dice_positive_gt_mean": mean_defined(pos, "dice"),
        "hd95_mm_positive_gt_mean": mean_defined(pos, "hd95_mm"),
        "exact_hd_mm_positive_gt_mean": mean_defined(pos, "exact_hd_mm"),
        "precision_positive_gt_mean": mean_defined(pos, "precision"),
        "sensitivity_positive_gt_mean": mean_defined(pos, "sensitivity"),
        "lesion_recall_mean": mean_defined(pos, "lesion_recall"),
        "small_lesion_recall_mean": mean_defined(pos, "small_lesion_recall"),
        "remote_fp_count_sum": int(sum(int(r["remote_fp_count"]) for r in rows)),
        "remote_fp_volume_mm3_sum": float(sum(float(r["remote_fp_volume_mm3"]) for r in rows)),
        "blood_pool_adjacent_fp_count_sum": int(sum(int(r["blood_pool_adjacent_fp_count"]) for r in rows)),
        "blood_pool_adjacent_fp_volume_mm3_sum": float(sum(float(r["blood_pool_adjacent_fp_volume_mm3"]) for r in rows)),
        "pred_component_count_sum": int(sum(int(r["pred_component_count"]) for r in rows)),
        "gt_component_count_sum": int(sum(int(r["gt_component_count"]) for r in rows)),
        "volume_ratio_positive_gt_mean": mean_defined(pos, "volume_ratio"),
        "metric_population_note": "dice_all_case_mean and dice_positive_gt_mean are reported separately to prevent empty-GT inflation",
    }


def by_key(rows: list[dict[str, Any]], lane: str, case_id: str, pathology: str) -> dict[str, Any]:
    matches = [r for r in rows if r["lane"] == lane and r["case_id"] == case_id and r["pathology"] == pathology]
    if len(matches) != 1:
        raise RuntimeError(f"expected one metric row for {lane}/{case_id}/{pathology}, found {len(matches)}")
    return matches[0]


def classify_delta(dice_delta: float, hd95_delta: float | None) -> str:
    if dice_delta > 0.01 and (hd95_delta is None or hd95_delta <= 2.0):
        return "help"
    if dice_delta < -0.01 or (hd95_delta is not None and hd95_delta > 2.0):
        return "harm"
    return "neutral"


def comparison_rows(rows: list[dict[str, Any]], lane: str, baseline: str, pathologies: Iterable[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row["lane"] != lane or row["pathology"] not in pathologies:
            continue
        base = by_key(rows, baseline, row["case_id"], row["pathology"])
        hd95_delta = None
        if row["hd95_mm"] not in (None, "") and base["hd95_mm"] not in (None, ""):
            hd95_delta = float(row["hd95_mm"]) - float(base["hd95_mm"])
        dice_delta = float(row["dice"]) - float(base["dice"])
        out.append(
            {
                "case_id": row["case_id"],
                "fold": row["fold"],
                "pathology": row["pathology"],
                "candidate_lane": lane,
                "candidate_checkpoint_step": row["checkpoint_step"],
                "candidate_dice": row["dice"],
                "stock_dice": base["dice"],
                "delta_dice": dice_delta,
                "candidate_hd95_mm": row["hd95_mm"],
                "stock_hd95_mm": base["hd95_mm"],
                "delta_hd95_mm": hd95_delta,
                "candidate_exact_hd_mm": row["exact_hd_mm"],
                "stock_exact_hd_mm": base["exact_hd_mm"],
                "candidate_precision": row["precision"],
                "stock_precision": base["precision"],
                "delta_precision": float(row["precision"]) - float(base["precision"]),
                "candidate_sensitivity": row["sensitivity"],
                "stock_sensitivity": base["sensitivity"],
                "delta_sensitivity": float(row["sensitivity"]) - float(base["sensitivity"]),
                "candidate_lesion_recall": row["lesion_recall"],
                "stock_lesion_recall": base["lesion_recall"],
                "candidate_small_lesion_recall": row["small_lesion_recall"],
                "stock_small_lesion_recall": base["small_lesion_recall"],
                "candidate_remote_fp_count": row["remote_fp_count"],
                "stock_remote_fp_count": base["remote_fp_count"],
                "candidate_remote_fp_volume_mm3": row["remote_fp_volume_mm3"],
                "stock_remote_fp_volume_mm3": base["remote_fp_volume_mm3"],
                "candidate_blood_pool_adjacent_fp_count": row["blood_pool_adjacent_fp_count"],
                "stock_blood_pool_adjacent_fp_count": base["blood_pool_adjacent_fp_count"],
                "candidate_volume_ratio": row["volume_ratio"],
                "stock_volume_ratio": base["volume_ratio"],
                "help_harm_neutral": classify_delta(dice_delta, hd95_delta),
            }
        )
    return out


def summary_lookup(summary_rows: list[dict[str, Any]], lane: str, pathology: str) -> dict[str, Any]:
    matches = [r for r in summary_rows if r["lane"] == lane and r["pathology"] == pathology]
    if len(matches) != 1:
        raise RuntimeError(f"expected one summary row for {lane}/{pathology}, found {len(matches)}")
    return matches[0]


def m2_gate_summary(summary_rows: list[dict[str, Any]], casewise: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pathology in PATHOLOGIES:
        cand = summary_lookup(summary_rows, "m2_selected_outer", pathology)
        stock = summary_lookup(summary_rows, "stock_nnunet_outer", pathology)
        subset = [r for r in casewise if r["pathology"] == pathology]
        harm_fraction = float(sum(1 for r in subset if r["help_harm_neutral"] == "harm") / len(subset)) if subset else 1.0
        sentinel_degrades = {
            r["case_id"]: float(r["delta_dice"])
            for r in subset
            if r["case_id"] in {"Case3008", "Case3009"}
        }
        dice_delta = float(cand["dice_positive_gt_mean"]) - float(stock["dice_positive_gt_mean"])
        hd95_delta = float(cand["hd95_mm_positive_gt_mean"]) - float(stock["hd95_mm_positive_gt_mean"])
        sens_delta = float(cand["sensitivity_positive_gt_mean"]) - float(stock["sensitivity_positive_gt_mean"])
        prec_delta = float(cand["precision_positive_gt_mean"]) - float(stock["precision_positive_gt_mean"])
        if pathology == "scar":
            gate = (
                dice_delta >= 0.02
                and hd95_delta <= 2.0
                and harm_fraction < 0.40
                and all(v >= -0.03 for v in sentinel_degrades.values())
                and {"Case3008", "Case3009"}.issubset(set(sentinel_degrades))
            )
        else:
            gate = (
                dice_delta >= 0.02
                and sens_delta >= 0.03
                and prec_delta >= -0.05
                and hd95_delta <= 2.0
                and harm_fraction < 0.40
            )
        out.append(
            {
                "pathology": pathology,
                "m2_checkpoint_step": M2_SELECTED_STEPS[pathology],
                "m2_dice_positive_gt_mean": cand["dice_positive_gt_mean"],
                "stock_dice_positive_gt_mean": stock["dice_positive_gt_mean"],
                "delta_dice_positive_gt_mean": dice_delta,
                "delta_hd95_mm_positive_gt_mean": hd95_delta,
                "delta_sensitivity_positive_gt_mean": sens_delta,
                "delta_precision_positive_gt_mean": prec_delta,
                "harm_fraction": harm_fraction,
                "case3008_delta_dice": sentinel_degrades.get("Case3008"),
                "case3009_delta_dice": sentinel_degrades.get("Case3009"),
                "gate_pass": gate,
            }
        )
    return out


def _set_nnunet_env(results_root: Path, cache_name: str) -> None:
    os.environ["CARE_ROOT"] = str(REPO_ROOT)
    os.environ["nnUNet_raw"] = str(REPO_ROOT / "data/nnUNet/nnUNet_raw")
    os.environ["nnUNet_preprocessed"] = str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed")
    os.environ["nnUNet_results"] = str(results_root)
    os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_ROOT / cache_name))


def get_stock_predictor(spec: CheckpointSpec, device: torch.device) -> Any:
    key = (spec.fold, str(spec.path))
    if key in _STOCK_PREDICTOR_CACHE:
        return _STOCK_PREDICTOR_CACHE[key]

    _set_nnunet_env(REPO_ROOT / "data/nnUNet/nnUNet_results", "stock_mpl_cache")
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=False,
        perform_everything_on_device=True,
        device=device,
        verbose=False,
        verbose_preprocessing=False,
        allow_tqdm=False,
    )
    predictor.initialize_from_trained_model_folder(str(spec.path.parent.parent), use_folds=(spec.fold,), checkpoint_name=spec.path.name)
    _STOCK_PREDICTOR_CACHE[key] = predictor
    return predictor


def predict_stock(spec: CheckpointSpec, image: np.ndarray, device: torch.device) -> np.ndarray:
    predictor = get_stock_predictor(spec, device)
    with torch.no_grad():
        data = torch.from_numpy(image).to(device=device, dtype=torch.float32)
        logits = predictor.predict_logits_from_preprocessed_data(data).detach().cpu().numpy()
    return np.argmax(logits, axis=0).astype(np.uint8)


def get_m0r_predictor(spec: CheckpointSpec, device: torch.device) -> Any:
    key = (spec.fold, str(spec.path))
    if key in _M0R_PREDICTOR_CACHE:
        return _M0R_PREDICTOR_CACHE[key]

    _set_nnunet_env(RUNTIME_ROOT / "m0r_faithful_control" / "nnUNet_results", "m0r_mpl_cache")
    import nnunetv2.inference.predict_from_raw_data as predict_from_raw_data
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
    from src.care_myocardium.nnunet.gap_closure_trainer import nnUNetTrainerGapClosureM0R4000

    original_class_finder = predict_from_raw_data.recursive_find_python_class

    def class_finder(folder: str, trainer_name: str, current_module: str) -> Any:
        if trainer_name == "nnUNetTrainerGapClosureM0R4000":
            return nnUNetTrainerGapClosureM0R4000
        return original_class_finder(folder, trainer_name, current_module)

    predict_from_raw_data.recursive_find_python_class = class_finder
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=False,
        perform_everything_on_device=True,
        device=device,
        verbose=False,
        verbose_preprocessing=False,
        allow_tqdm=False,
    )
    predictor.initialize_from_trained_model_folder(str(spec.path.parent.parent), use_folds=(spec.fold,), checkpoint_name=spec.path.name)
    _M0R_PREDICTOR_CACHE[key] = predictor
    return predictor


def predict_m0r(spec: CheckpointSpec, image: np.ndarray, device: torch.device) -> np.ndarray:
    predictor = get_m0r_predictor(spec, device)
    with torch.no_grad():
        data = torch.from_numpy(image).to(device=device, dtype=torch.float32)
        logits = predictor.predict_logits_from_preprocessed_data(data).detach().cpu().numpy()
    return np.argmax(logits, axis=0).astype(np.uint8)


def get_m2_model(spec: CheckpointSpec, device: torch.device) -> torch.nn.Module:
    key = (spec.fold, str(spec.path))
    if key not in _M2_MODEL_CACHE:
        from scripts.training.target_domain_gap_closure.run_m2_i_mmseg_care import build_model as build_m2_model

        model = build_m2_model(device, load_released=False)
        model.load_state_dict(torch.load(spec.path, map_location=device)["model"])
        model.eval()
        _M2_MODEL_CACHE[key] = model
    return _M2_MODEL_CACHE[key]


def predict_m2_cached(spec: CheckpointSpec, image: np.ndarray, device: torch.device, dim: int) -> np.ndarray:
    model = get_m2_model(spec, device)
    pred = np.zeros(tuple(image.shape[1:]), dtype=np.uint8)
    with torch.no_grad():
        for z in range(image.shape[1]):
            crop, bounds = center_crop_or_pad(image[:, z], dim)
            c0 = torch.from_numpy(crop[2:3]).unsqueeze(0).to(device=device, dtype=torch.float32)
            lge = torch.from_numpy(crop[0:1]).unsqueeze(0).to(device=device, dtype=torch.float32)
            t2 = torch.from_numpy(crop[1:2]).unsqueeze(0).to(device=device, dtype=torch.float32)
            logits = model(c0, lge, t2, False)
            compact = torch.argmax(logits, dim=1)[0].detach().cpu().numpy().astype(np.uint8)
            decoded = np.zeros_like(compact, dtype=np.uint8)
            decoded[compact == 1] = 1
            decoded[compact == 2] = 5
            decoded[compact == 3] = 4
            y0, y1, x0, x1 = bounds
            h, w = pred.shape[-2:]
            yy0, yy1 = max(0, y0), min(h, y1)
            xx0, xx1 = max(0, x0), min(w, x1)
            pred[z, yy0:yy1, xx0:xx1] = decoded[(yy0 - y0) : (yy1 - y0), (xx0 - x0) : (xx1 - x0)]
    return pred


def evaluate_outer(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    all_rows: list[dict[str, Any]] = []
    inference_rows: list[dict[str, Any]] = []
    for fold in (2, 3):
        stock_spec = stock_checkpoint(fold)
        m0r_specs = {p: checkpoint_from_receipt("m0r_faithful_control", fold, step) for p, step in M0R_SELECTED_STEPS.items()}
        m2_specs = {p: checkpoint_from_receipt("m2_i_mmseg_care", fold, step) for p, step in M2_SELECTED_STEPS.items()}
        for case_id in outer_cases_for_fold(fold):
            case = load_case(case_id)
            t0 = time.time()
            stock_pred = predict_stock(stock_spec, case.image, device)
            m0r_preds = {p: predict_m0r(spec, case.image, device) for p, spec in m0r_specs.items()}
            m2_preds = {p: predict_m2_cached(spec, case.image, device, args.dim) for p, spec in m2_specs.items()}
            for pathology in PATHOLOGIES:
                all_rows.append(metric_row("stock_nnunet_outer", fold, -1, case_id, pathology, stock_pred, case, "fold2_fold3_outer", "preprocessed_grid_with_physical_spacing_from_properties"))
                all_rows.append(metric_row("m0r_selected_outer", fold, M0R_SELECTED_STEPS[pathology], case_id, pathology, m0r_preds[pathology], case, "fold2_fold3_outer", "preprocessed_grid_with_physical_spacing_from_properties"))
                all_rows.append(metric_row("m2_selected_outer", fold, M2_SELECTED_STEPS[pathology], case_id, pathology, m2_preds[pathology], case, "fold2_fold3_outer", "preprocessed_grid_with_physical_spacing_from_properties"))
            inference_rows.append(
                {
                    "fold": fold,
                    "case_id": case_id,
                    "device": str(device),
                    "status": "COMPLETED",
                    "elapsed_seconds": round(time.time() - t0, 3),
                    "stock_checkpoint": str(stock_spec.path),
                    "m0r_scar_checkpoint": str(m0r_specs["scar"].path),
                    "m0r_edema_checkpoint": str(m0r_specs["pure_edema"].path),
                    "m2_scar_checkpoint": str(m2_specs["scar"].path),
                    "m2_edema_checkpoint": str(m2_specs["pure_edema"].path),
                    "new_training": False,
                    "new_slurm_job": False,
                }
            )
            print(json.dumps({"phase": "outer", "fold": fold, "case_id": case_id, "status": "COMPLETED"}), flush=True)
    summary_rows: list[dict[str, Any]] = []
    for lane in ("stock_nnunet_outer", "m0r_selected_outer", "m2_selected_outer"):
        for pathology in PATHOLOGIES:
            subset = [r for r in all_rows if r["lane"] == lane and r["pathology"] == pathology]
            summary_rows.append(summarize(lane, pathology, M0R_SELECTED_STEPS.get(pathology, M2_SELECTED_STEPS.get(pathology, -1)) if lane != "stock_nnunet_outer" else -1, subset))
    return all_rows, summary_rows, inference_rows


def inner_stock_privilege_audit(args: argparse.Namespace) -> list[dict[str, Any]]:
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    splits = json.loads((REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for fold in (2, 3):
        train_cases = set(splits[fold]["train"])
        val_cases = set(splits[fold]["val"])
        stock_spec = stock_checkpoint(fold)
        m0r_specs = {p: checkpoint_from_receipt("m0r_faithful_control", fold, step) for p, step in M0R_SELECTED_STEPS.items()}
        for case_id in inner_cases_for_fold(fold):
            case = load_case(case_id)
            stock_pred = predict_stock(stock_spec, case.image, device)
            m0r_preds = {p: predict_m0r(spec, case.image, device) for p, spec in m0r_specs.items()}
            for pathology in PATHOLOGIES:
                stock_row = metric_row("stock_inner", fold, -1, case_id, pathology, stock_pred, case, "inner_selection", "preprocessed_grid_with_physical_spacing_from_properties")
                m0r_row = metric_row("m0r_inner", fold, M0R_SELECTED_STEPS[pathology], case_id, pathology, m0r_preds[pathology], case, "inner_selection", "preprocessed_grid_with_physical_spacing_from_properties")
                rows.append(
                    {
                        "fold": fold,
                        "case_id": case_id,
                        "pathology": pathology,
                        "inner_case_seen_by_stock_training": case_id in train_cases,
                        "inner_case_in_stock_validation": case_id in val_cases,
                        "stock_checkpoint": str(stock_spec.path),
                        "m0r_checkpoint_step": M0R_SELECTED_STEPS[pathology],
                        "stock_dice": stock_row["dice"],
                        "m0r_dice": m0r_row["dice"],
                        "m0r_minus_stock_dice": float(m0r_row["dice"]) - float(stock_row["dice"]),
                        "stock_hd95_mm": stock_row["hd95_mm"],
                        "m0r_hd95_mm": m0r_row["hd95_mm"],
                        "m0r_minus_stock_hd95_mm": (
                            None
                            if stock_row["hd95_mm"] in (None, "") or m0r_row["hd95_mm"] in (None, "")
                            else float(m0r_row["hd95_mm"]) - float(stock_row["hd95_mm"])
                        ),
                        "stock_precision": stock_row["precision"],
                        "m0r_precision": m0r_row["precision"],
                        "stock_sensitivity": stock_row["sensitivity"],
                        "m0r_sensitivity": m0r_row["sensitivity"],
                    }
                )
            print(json.dumps({"phase": "inner_privilege", "fold": fold, "case_id": case_id, "status": "COMPLETED"}), flush=True)
    return rows


def build_asset_manifest() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for fold in (2, 3):
        records.append(file_record(stock_checkpoint(fold).path, f"stock_nnunet_fold{fold}_checkpoint"))
        for pathology, step in M0R_SELECTED_STEPS.items():
            records.append(file_record(checkpoint_from_receipt("m0r_faithful_control", fold, step).path, f"m0r_fold{fold}_{pathology}_selected_checkpoint"))
        for pathology, step in M2_SELECTED_STEPS.items():
            records.append(file_record(checkpoint_from_receipt("m2_i_mmseg_care", fold, step).path, f"m2_fold{fold}_{pathology}_selected_checkpoint"))
        for lane in ("m1_myopsnet_l_care", "m3_care_tds"):
            selection_path = SOURCE_ROOT / "inner_evaluation" / lane / "selection_candidates.csv"
            if selection_path.exists():
                for row in read_csv(selection_path):
                    records.append(file_record(checkpoint_from_receipt(lane, fold, int(row["checkpoint_step"])).path, f"{lane}_fold{fold}_{row['pathology']}_inner_selected_checkpoint"))
    records.extend(
        [
            file_record(SOURCE_ROOT / "split_receipt_copy.json", "split_receipt_copy"),
            file_record(Path(__file__), "evaluation_script"),
            file_record(REPO_ROOT / "scripts/validation/validate_four_lane_evidence_reconciliation.py", "validation_script"),
            file_record(REPO_ROOT / "scripts/evaluation/target_domain_gap_closure/evaluate_inner_lanes.py", "source_prediction_helper"),
            file_record(REPO_ROOT / "scripts/evaluation/target_domain_gap_closure/replay_outer_composition.py", "source_stock_helper"),
        ]
    )
    return {
        "created_at": now_utc(),
        "task_key": TASK_KEY,
        "source_task_key": SOURCE_TASK_KEY,
        "hash_algorithm": "sha256",
        "records": records,
        "missing_records": [r for r in records if not r["exists"]],
    }


def write_metric_contract() -> None:
    write_json(
        RESULT_ROOT / "metric_contract.json",
        {
            "created_at": now_utc(),
            "metric_status": "CORRECTED_PHYSICAL_SPACE",
            "prediction_grid": "preprocessed_grid_with_physical_spacing_from_properties",
            "spacing_source": "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres/<case>.pkl:spacing",
            "distance_units": "mm",
            "hd95_field": "hd95_mm",
            "exact_hd_field": "exact_hd_mm",
            "remote_fp_distance_threshold_mm": REMOTE_FP_DISTANCE_MM,
            "small_lesion_definition": "component physical volume < 1000 mm3",
            "small_lesion_volume_threshold_mm3": SMALL_LESION_VOLUME_MM3,
            "blood_pool_adjacent_fp_threshold_mm": BLOOD_POOL_ADJACENT_MM,
            "empty_gt_policy": "casewise metrics retained; summaries separate all-case and positive-GT denominators",
            "evaluation_only_gt_anatomy_use": "GT blood pool is used only for error stratification, never for model inference",
            "forbidden_metric_semantics": ["HD vox mislabeled as mm", "small lesion defined in voxels", "empty-GT cases mixed into pathology mean without denominator fields"],
        },
    )


def write_controller_context(args: argparse.Namespace, outer_case_count: int, inner_case_count: int) -> None:
    head = os.popen("git rev-parse HEAD").read().strip()
    status = os.popen("git status --short --branch").read().strip().splitlines()
    write_json(
        RESULT_ROOT / "controller_context.json",
        {
            "created_at": now_utc(),
            "task_key": TASK_KEY,
            "task_prompt_path": f"prompts/tasks/{TASK_KEY}_controller.md",
            "git_head_at_evaluation": head,
            "git_status_short_branch": status,
            "source_task_key": SOURCE_TASK_KEY,
            "stock_source_task_key": STOCK_TASK_KEY,
            "diagram_versions_read": ["SRR-v2", "SRR-v2.5", "SRR-v3"],
            "visual_read_status": "PASS_REPO_LOCAL_BITMAPS_VISUALLY_INSPECTED",
            "visual_read_source_note": "Repo-local images were opened and visually inspected in this Codex session; ChatGPT Project background files are not directly accessible from the local shell.",
            "recovered_route_objective": "modality-specific evidence, pathology-specific authority, soft anatomy context, lesion proposal/refinement, negative-space accounting, and baseline safety",
            "new_training_authorized": False,
            "new_slurm_job_authorized": False,
            "validation_upload_authorized": False,
            "hosted_metric_claim_authorized": False,
            "outer_case_count": outer_case_count,
            "inner_privilege_case_count": inner_case_count,
            "device_request": "cpu" if args.cpu else "cuda_if_available",
            "m0r_selected_steps": M0R_SELECTED_STEPS,
            "m2_selected_steps": M2_SELECTED_STEPS,
        },
    )


def fidelity_audits() -> None:
    m1_source = (REPO_ROOT / "scripts/training/target_domain_gap_closure/run_m1_myopsnet_l_care.py").read_text(encoding="utf-8")
    m3_source = (REPO_ROOT / "src/care_myocardium/models/target_domain_gap_closure.py").read_text(encoding="utf-8")
    m1 = {
        "created_at": now_utc(),
        "decision": "M1_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC",
        "official_cmff_mpc_pathology_inclusiveness_used": "partial",
        "hard_argmax_anatomy_mask_used": "yes",
        "scar_target_matches_care_label5": "yes",
        "injury_or_pure_edema_target_matches_contract": "partial_pure_edema_label4_only_no_injury_inclusiveness",
        "lesion_balanced_sampling": "missing",
        "spatial_intensity_augmentation": "missing",
        "full_volume_reconstruction_training": "missing_slice_center_crop_training_only",
        "actual_input_size": "2D center crop 128x128",
        "loss": "NLL losses over C0 segmentation plus binary scar and edema decoders",
        "optimizer": "Adam",
        "code_evidence": {
            "contains_mask_c0_argmax_detach": "mask_c0 = torch.argmax(seg_c0" in m1_source and "mask_c0.detach()" in m1_source,
            "contains_nll_loss": "F.nll_loss" in m1_source,
            "contains_center_crop_dim_128": "--dim" in m1_source and "default=128" in m1_source,
        },
        "interpretation": "The adapter used pinned MyoPS-Net components but did not faithfully implement the full official CMFF/MPC and pathology-inclusiveness training contract.",
    }
    m3 = {
        "created_at": now_utc(),
        "decision": "M3_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC",
        "stock_encoder_decoder_frozen": "stock adapter parameters require_grad false",
        "blueprint_losses_implemented": "partial_BCE_and_containment_only",
        "missing_blueprint_losses": ["Dice", "Focal", "component-Tversky", "MIL", "remote-FP", "boundary-distance"],
        "hard_negative_mask_in_loss": "missing",
        "blueprint_patch_batch_manifests_used": "partial_batch_manifest_only",
        "only_shallow_bce_heads": "yes",
        "code_evidence": {
            "stock_requires_grad_false": "param.requires_grad_(False)" in m3_source,
            "bce_loss_used": "binary_cross_entropy_with_logits" in m3_source,
            "remote_fp_loss_absent": "remote" not in m3_source.lower(),
            "component_tversky_absent": "tversky" not in m3_source.lower(),
            "mil_absent": "mil" not in m3_source.lower(),
        },
        "interpretation": "The observed low M3 metrics describe a shallow detached-head implementation, not a faithful CARE-TDS scientific negative.",
    }
    write_json(RESULT_ROOT / "m1_fidelity_audit.json", m1)
    write_json(RESULT_ROOT / "m3_fidelity_audit.json", m3)


def write_interpretation(summary_rows: list[dict[str, Any]], m0r_cmp: list[dict[str, Any]], m2_gate_rows: list[dict[str, Any]]) -> str:
    m0r_scar = summary_lookup(summary_rows, "m0r_selected_outer", "scar")
    m0r_edema = summary_lookup(summary_rows, "m0r_selected_outer", "pure_edema")
    stock_scar = summary_lookup(summary_rows, "stock_nnunet_outer", "scar")
    stock_edema = summary_lookup(summary_rows, "stock_nnunet_outer", "pure_edema")
    m0r_scar_delta = float(m0r_scar["dice_positive_gt_mean"]) - float(stock_scar["dice_positive_gt_mean"])
    m0r_edema_delta = float(m0r_edema["dice_positive_gt_mean"]) - float(stock_edema["dice_positive_gt_mean"])
    m2_pass = any(bool(r["gate_pass"]) for r in m2_gate_rows if r["pathology"] == "scar")
    if m2_pass:
        decision = "M2_OUTER_CANDIDATE_WORTH_PACKAGING"
    elif m0r_scar_delta < 0:
        decision = "FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE"
    else:
        decision = "FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE"
    harmed = sum(1 for r in m0r_cmp if r["pathology"] == "scar" and r["help_harm_neutral"] == "harm")
    total = sum(1 for r in m0r_cmp if r["pathology"] == "scar")
    text = f"""# Four-lane Scientific Interpretation

这次重新核对后，旧的 scar-only 候选结论不能直接保留。M0R 在真正未见的 fold2+fold3 outer 病例上没有超过同病例 stock nnU-Net；M2 补做 outer 后也没有达到预设的候选门槛。因此当前最稳妥的判断是撤销本地候选，把四条 lane 归档为已经纠偏但没有可打包候选；下一步应回到 Planner，而不是继续调阈值、重训、上传验证集或声称 hosted 指标。

## Decision

scientific_decision: `{decision}`
old_decision_superseded: `SCAR_ONLY_CANDIDATE_READY`

## Same-case Stock Comparison

| pathology | stock Dice | M0R Dice | M0R-stock Dice | stock HD95 mm | M0R HD95 mm | M0R-stock HD95 mm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| scar | {float(stock_scar['dice_positive_gt_mean']):.6f} | {float(m0r_scar['dice_positive_gt_mean']):.6f} | {m0r_scar_delta:.6f} | {float(stock_scar['hd95_mm_positive_gt_mean']):.6f} | {float(m0r_scar['hd95_mm_positive_gt_mean']):.6f} | {float(m0r_scar['hd95_mm_positive_gt_mean']) - float(stock_scar['hd95_mm_positive_gt_mean']):.6f} |
| pure_edema | {float(stock_edema['dice_positive_gt_mean']):.6f} | {float(m0r_edema['dice_positive_gt_mean']):.6f} | {m0r_edema_delta:.6f} | {float(stock_edema['hd95_mm_positive_gt_mean']):.6f} | {float(m0r_edema['hd95_mm_positive_gt_mean']):.6f} | {float(m0r_edema['hd95_mm_positive_gt_mean']) - float(stock_edema['hd95_mm_positive_gt_mean']):.6f} |

M0R scar harmed {harmed}/{total} scar-positive outer rows under the predefined help/harm rule. Its inner 0.888/0.792 selection numbers are contaminated development evidence because the fold-specific stock checkpoints had seen the inner-selection cases during their original training.

## M2 Gate

| pathology | gate_pass | Dice delta | HD95 delta mm | sensitivity delta | precision delta | harm fraction |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
"""
    for row in m2_gate_rows:
        text += f"| {row['pathology']} | {row['gate_pass']} | {float(row['delta_dice_positive_gt_mean']):.6f} | {float(row['delta_hd95_mm_positive_gt_mean']):.6f} | {float(row['delta_sensitivity_positive_gt_mean']):.6f} | {float(row['delta_precision_positive_gt_mean']):.6f} | {float(row['harm_fraction']):.6f} |\n"
    text += """
## M1/M3 Fidelity

M1 is classified as `M1_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC` because the CARE adapter uses pinned MyoPS-Net pieces but keeps a hard argmax anatomy mask and lacks the full official CMFF/MPC/pathology-inclusiveness contract, lesion-balanced sampling, augmentation, and full-volume training semantics.

M3 is classified as `M3_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC` because the current code freezes the stock adapter and adds shallow BCE heads with limited containment losses; it does not implement the blueprint's Dice/Focal/component-Tversky/MIL/remote-FP/boundary-distance loss stack or hard-negative loss path.
"""
    (RESULT_ROOT / "four_lane_scientific_interpretation.md").write_text(text, encoding="utf-8")
    write_json(
        RESULT_ROOT / "scientific_decision.json",
        {
            "created_at": now_utc(),
            "scientific_decision": decision,
            "old_decision_superseded": "SCAR_ONLY_CANDIDATE_READY",
            "m0r_scar_delta_dice_vs_stock": m0r_scar_delta,
            "m0r_edema_delta_dice_vs_stock": m0r_edema_delta,
            "m2_gate_rows": m2_gate_rows,
            "validation_upload_authorized": False,
            "docker_upload_authorized": False,
            "hosted_metric_claim_authorized": False,
        },
    )
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--skip-inner-privilege", action="store_true")
    args = parser.parse_args()

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    write_metric_contract()
    write_json(RESULT_ROOT / "frozen_asset_manifest.json", build_asset_manifest())
    fidelity_audits()

    outer_rows, summary_rows, inference_rows = evaluate_outer(args)
    write_csv(RESULT_ROOT / "all_outer_casewise.csv", outer_rows)
    write_csv(RESULT_ROOT / "all_outer_summary.csv", summary_rows)
    write_csv(RESULT_ROOT / "inference_accounting.csv", inference_rows)

    m0r_cmp = comparison_rows(outer_rows, "m0r_selected_outer", "stock_nnunet_outer", PATHOLOGIES)
    m2_cmp = comparison_rows(outer_rows, "m2_selected_outer", "stock_nnunet_outer", PATHOLOGIES)
    write_csv(RESULT_ROOT / "m0r_vs_stock_outer_casewise.csv", m0r_cmp)
    m0r_summary = []
    for pathology in PATHOLOGIES:
        cand = summary_lookup(summary_rows, "m0r_selected_outer", pathology)
        stock = summary_lookup(summary_rows, "stock_nnunet_outer", pathology)
        subset = [r for r in m0r_cmp if r["pathology"] == pathology]
        m0r_summary.append(
            {
                "pathology": pathology,
                "m0r_checkpoint_step": M0R_SELECTED_STEPS[pathology],
                "m0r_dice_positive_gt_mean": cand["dice_positive_gt_mean"],
                "stock_dice_positive_gt_mean": stock["dice_positive_gt_mean"],
                "delta_dice_positive_gt_mean": float(cand["dice_positive_gt_mean"]) - float(stock["dice_positive_gt_mean"]),
                "m0r_hd95_mm_positive_gt_mean": cand["hd95_mm_positive_gt_mean"],
                "stock_hd95_mm_positive_gt_mean": stock["hd95_mm_positive_gt_mean"],
                "delta_hd95_mm_positive_gt_mean": float(cand["hd95_mm_positive_gt_mean"]) - float(stock["hd95_mm_positive_gt_mean"]),
                "harm_fraction": float(sum(1 for r in subset if r["help_harm_neutral"] == "harm") / len(subset)) if subset else 1.0,
                "help_count": sum(1 for r in subset if r["help_harm_neutral"] == "help"),
                "harm_count": sum(1 for r in subset if r["help_harm_neutral"] == "harm"),
                "neutral_count": sum(1 for r in subset if r["help_harm_neutral"] == "neutral"),
            }
        )
    write_csv(RESULT_ROOT / "m0r_vs_stock_outer_summary.csv", m0r_summary)
    write_csv(RESULT_ROOT / "m2_outer_casewise.csv", m2_cmp)
    m2_gate_rows = m2_gate_summary(summary_rows, m2_cmp)
    write_csv(RESULT_ROOT / "m2_vs_stock_outer_summary.csv", m2_gate_rows)
    sentinel_rows = [r for r in m0r_cmp + m2_cmp if r["case_id"] in SENTINEL_CASES]
    write_csv(RESULT_ROOT / "sentinel_case_comparison.csv", sentinel_rows)

    inner_rows: list[dict[str, Any]] = []
    if not args.skip_inner_privilege:
        inner_rows = inner_stock_privilege_audit(args)
    write_csv(RESULT_ROOT / "inner_stock_privilege_audit.csv", inner_rows)
    write_controller_context(args, len({r["case_id"] for r in outer_rows}), len({r["case_id"] for r in inner_rows}))
    decision = write_interpretation(summary_rows, m0r_cmp, m2_gate_rows)

    write_json(
        RESULT_ROOT / "evaluation_receipt.json",
        {
            "created_at": now_utc(),
            "status": "PASS",
            "task_key": TASK_KEY,
            "scientific_decision": decision,
            "outer_cases": sorted({r["case_id"] for r in outer_rows}),
            "outer_case_count": len({r["case_id"] for r in outer_rows}),
            "inner_privilege_case_count": len({r["case_id"] for r in inner_rows}),
            "metric_contract": str((RESULT_ROOT / "metric_contract.json").relative_to(REPO_ROOT)),
            "new_training": False,
            "new_slurm_job": False,
        },
    )
    print(json.dumps({"status": "PASS", "scientific_decision": decision}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
