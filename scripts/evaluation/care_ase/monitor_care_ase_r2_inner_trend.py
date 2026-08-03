#!/usr/bin/env python
"""Asynchronous CARE-ASE R2 inner checkpoint trend monitor.

This monitor is descriptive only. It refuses outer cases, uses the fixed R2
argmax decode, joins same-case nnU-Net/MoSAIC OOF reference metrics, and writes
an immutable packet for a single fold/checkpoint.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pickle
import statistics
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
from scipy import ndimage
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.inference.care_ase_r2_full_volume import (
    default_care_ase_full_volume_inference_settings,
    predict_care_ase_r2_full_volume_logits,
)
from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint_for_inference


TASK_KEY = "20260804_care_ase_r2_emergency_9h_training_docker"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
OLD_RESULT_ROOT_MARKER = "20260803_care_ase_r2_" + "full_fidelity_execution"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
SPLIT_CASE_LISTS = RESULT_ROOT / "split_case_lists.csv"
BASELINE_CASEWISE = REPO_ROOT / "results/20260801_care_nnunet_mosaic_complementarity_closure/oof_complementarity_casewise.csv"
MONITOR_STEPS = (4000, 6000, 8000, 10000, 12000, 14000)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"immutable monitor packet already exists: {path}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def load_inner_rows(fold: int) -> list[dict[str, str]]:
    if not SPLIT_CASE_LISTS.is_file():
        raise FileNotFoundError(f"missing frozen split case list: {SPLIT_CASE_LISTS}")
    with SPLIT_CASE_LISTS.open(newline="", encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(f) if int(row["fold"]) == int(fold)]
    outer = [row["case_id"] for row in rows if row["role"] == "outer"]
    inner = [row for row in rows if row["role"] == "inner"]
    if not inner:
        raise RuntimeError(f"fold{fold} has no frozen inner monitor cases")
    if set(row["case_id"] for row in inner) & set(outer):
        raise RuntimeError(f"fold{fold} inner/outer overlap in split case list")
    return sorted(inner, key=lambda row: row["case_id"])


def load_baseline_rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        out[(row["case_id"], row["pathology"])] = row
    return out


def dice_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float:
    p = pred == cls
    g = gt == cls
    denom = int(p.sum() + g.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(p, g).sum() / denom)


def sensitivity_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    g = gt == cls
    total = int(g.sum())
    if total == 0:
        return None
    return float(np.logical_and(pred == cls, g).sum() / total)


def pred_gt_volume_ratio(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    gt_voxels = int((gt == cls).sum())
    if gt_voxels == 0:
        return None
    return float((pred == cls).sum() / gt_voxels)


def precision_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    p = pred == cls
    total = int(p.sum())
    if total == 0:
        return None
    return float(np.logical_and(p, gt == cls).sum() / total)


def hd95_for_class(pred: np.ndarray, gt: np.ndarray, cls: int, spacing: tuple[float, float, float]) -> float:
    p = pred == cls
    g = gt == cls
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return 1.0e6
    p_border = p ^ ndimage.binary_erosion(p)
    g_border = g ^ ndimage.binary_erosion(g)
    p_to_g = ndimage.distance_transform_edt(~g_border, sampling=spacing)[p_border]
    g_to_p = ndimage.distance_transform_edt(~p_border, sampling=spacing)[g_border]
    values = np.concatenate([p_to_g, g_to_p]).astype(np.float64, copy=False)
    return float(np.percentile(values, 95)) if values.size else 0.0


def numeric_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def mean_or_none(values: list[float]) -> float | None:
    return float(statistics.fmean(values)) if values else None


def mean_or_default(values: list[float | None], default: float = 0.0) -> float:
    observed = [float(v) for v in values if v is not None]
    return float(statistics.fmean(observed)) if observed else float(default)


def median_or_none(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def bool_from_csv(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def parse_patch_size(text: str) -> tuple[int, int, int]:
    values = tuple(int(part.strip()) for part in str(text).split(",") if part.strip())
    if len(values) != 3:
        raise ValueError("--patch-size must contain three comma-separated integers")
    return values


def require_verified_checkpoint(checkpoint: Path) -> dict[str, Any]:
    sidecar = checkpoint.with_suffix(checkpoint.suffix + ".sha256")
    verified = checkpoint.with_name(checkpoint.stem + ".verified.json")
    if not sidecar.is_file():
        raise FileNotFoundError(f"missing checkpoint sidecar: {sidecar}")
    if not verified.is_file():
        raise FileNotFoundError(f"missing checkpoint verified receipt: {verified}")
    payload = json.loads(verified.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise RuntimeError(f"checkpoint verified receipt is not PASS: {verified}")
    observed = sha256_file(checkpoint)
    if str(payload.get("checkpoint_sha256", observed)) != observed:
        raise RuntimeError("checkpoint verified receipt SHA does not match checkpoint")
    return payload


def subgroup_summary(rows: list[dict[str, Any]], predicate: Any) -> dict[str, Any]:
    selected = [row for row in rows if predicate(row)]
    scar = [float(row["care_scar_dice"]) for row in selected if row.get("care_scar_dice") is not None]
    edema = [float(row["care_pure_edema_dice"]) for row in selected if row.get("care_pure_edema_dice") is not None]
    return {
        "case_count": len(selected),
        "scar_dice_mean": mean_or_none(scar),
        "scar_dice_median": median_or_none(scar),
        "pure_edema_dice_mean": mean_or_none(edema),
        "pure_edema_dice_median": median_or_none(edema),
    }


def help_harm_neutral(rows: list[dict[str, Any]], pathology: str, baseline_key: str, eps: float) -> dict[str, int]:
    care_key = "care_scar_dice" if pathology == "scar" else "care_pure_edema_dice"
    counts = {"help": 0, "harm": 0, "neutral": 0}
    for row in rows:
        care = row.get(care_key)
        base = row.get(baseline_key)
        if care is None or base is None:
            continue
        delta = float(care) - float(base)
        if delta > eps:
            counts["help"] += 1
        elif delta < -eps:
            counts["harm"] += 1
        else:
            counts["neutral"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-step", type=int, required=True, choices=MONITOR_STEPS)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--patch-size", default="20,256,256")
    parser.add_argument("--baseline-casewise", type=Path, default=BASELINE_CASEWISE)
    parser.add_argument("--max-cases", type=int, default=0, help="debug only; 0 means all frozen inner cases")
    args = parser.parse_args()

    if "outer" in str(args.output_dir or "").lower():
        raise RuntimeError("inner monitor output path must not contain 'outer'")
    if OLD_RESULT_ROOT_MARKER in str(args.output_dir or ""):
        raise RuntimeError("inner monitor rejects old CARE-ASE v5-v8 result roots")
    checkpoint = args.checkpoint.resolve()
    out_dir = (args.output_dir or RESULT_ROOT / "inner_checkpoint_monitor" / f"fold_{args.fold}" / f"step{args.checkpoint_step:05d}").resolve()
    packet_path = out_dir / "monitor_packet.json"
    casewise_path = out_dir / "casewise_metrics.csv"
    if packet_path.exists() or casewise_path.exists():
        raise FileExistsError(f"immutable monitor output already exists: {out_dir}")

    inner_rows = load_inner_rows(args.fold)
    if args.max_cases > 0:
        inner_rows = inner_rows[: args.max_cases]
    inner_cases = [row["case_id"] for row in inner_rows]
    metadata = load_myops_case_metadata(REPO_ROOT)
    baseline = load_baseline_rows(args.baseline_casewise)
    patch_size = parse_patch_size(args.patch_size)
    inference_settings = default_care_ase_full_volume_inference_settings(patch_size=patch_size)
    verified_receipt = require_verified_checkpoint(checkpoint)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, payload = load_care_ase_checkpoint_for_inference(checkpoint, map_location=device)
    model.to(device).eval()
    if int(payload.get("global_optimizer_step", -1)) != int(args.checkpoint_step):
        raise RuntimeError(
            f"checkpoint step mismatch: payload={payload.get('global_optimizer_step')} requested={args.checkpoint_step}"
        )

    case_rows: list[dict[str, Any]] = []
    with torch.no_grad():
        for split_row in inner_rows:
            case_id = split_row["case_id"]
            image_np = read_b2nd(PREPROCESSED / f"{case_id}.b2nd").astype(np.float32, copy=False)
            seg = read_b2nd(PREPROCESSED / f"{case_id}_seg.b2nd")[0].astype(np.int64, copy=False)
            image = torch.from_numpy(image_np[None]).to(device=device, dtype=torch.float32)
            availability = torch.tensor([metadata[case_id].availability], device=device, dtype=torch.float32)
            logits = predict_care_ase_r2_full_volume_logits(model, image, availability, settings=inference_settings)
            pred = decode_care_ase_r2_logits(logits, availability).cpu().numpy().astype(np.uint8)[0]
            scar_ref = baseline.get((case_id, "scar"))
            edema_ref = baseline.get((case_id, "pure_edema"))
            if scar_ref is None:
                raise RuntimeError(f"missing nnunet/mosaic scar baseline for inner case {case_id}")
            t2_present = bool(metadata[case_id].t2_present)
            if t2_present and edema_ref is None:
                raise RuntimeError(f"missing nnunet/mosaic pure_edema baseline for T2-present inner case {case_id}")
            spacing = (1.0, 1.0, 1.0)
            pkl = PREPROCESSED / f"{case_id}.pkl"
            if pkl.is_file():
                with pkl.open("rb") as f:
                    spacing = tuple(float(v) for v in pickle.load(f).get("spacing", spacing))
            voxel_volume = float(math.prod(spacing))
            scar_dice = dice_for_class(pred, seg, 5)
            edema_dice = dice_for_class(pred, seg, 4) if t2_present else None
            scar_hd95 = hd95_for_class(pred, seg, 5, spacing)
            edema_hd95 = hd95_for_class(pred, seg, 4, spacing) if t2_present else None
            wall = (seg == 1) | (seg == 4) | (seg == 5)
            dist_to_wall = ndimage.distance_transform_edt(~wall, sampling=spacing)
            scar_remote_fp_volume = float(((pred == 5) & (seg != 5) & (dist_to_wall > 10.0)).sum() * voxel_volume)
            scar_components = int(ndimage.label(pred == 5, structure=np.ones((3, 3, 3), dtype=np.uint8))[1])
            edema_components = int(ndimage.label(pred == 4, structure=np.ones((3, 3, 3), dtype=np.uint8))[1]) if t2_present else None
            nn_scar = float(scar_ref["nnunet_dice"])
            nn_edema = float(edema_ref["nnunet_dice"]) if edema_ref and t2_present else None
            stock_scar_hd95 = numeric_or_none(scar_ref.get("nnunet_hd95_mm"))
            stock_edema_hd95 = numeric_or_none(edema_ref.get("nnunet_hd95_mm")) if edema_ref and t2_present else None
            row = {
                "case_id": case_id,
                "fold": int(args.fold),
                "checkpoint_step": int(args.checkpoint_step),
                "role": split_row["role"],
                "center": split_row["center"],
                "t2_present": t2_present,
                "modality_group": split_row.get("modality_group", ""),
                "scar_volume_bin": split_row.get("scar_volume_bin", ""),
                "care_scar_dice": scar_dice,
                "care_pure_edema_dice": edema_dice,
                "care_scar_hd95_mm": scar_hd95,
                "care_pure_edema_hd95_mm": edema_hd95,
                "nnunet_scar_dice": nn_scar,
                "mosaic_scar_dice": float(scar_ref["mosaic_dice"]),
                "nnunet_scar_hd95_mm": stock_scar_hd95,
                "nnunet_pure_edema_dice": nn_edema,
                "nnunet_pure_edema_hd95_mm": stock_edema_hd95,
                "mosaic_pure_edema_dice": float(edema_ref["mosaic_dice"]) if edema_ref and t2_present else None,
                "scar_sensitivity": sensitivity_for_class(pred, seg, 5),
                "pure_edema_sensitivity": sensitivity_for_class(pred, seg, 4) if t2_present else None,
                "scar_precision": precision_for_class(pred, seg, 5),
                "pure_edema_precision": precision_for_class(pred, seg, 4) if t2_present else None,
                "scar_empty_prediction": int((pred == 5).sum()) == 0,
                "pure_edema_empty_prediction": (int((pred == 4).sum()) == 0) if t2_present else None,
                "scar_volume_ratio": pred_gt_volume_ratio(pred, seg, 5),
                "pure_edema_volume_ratio": pred_gt_volume_ratio(pred, seg, 4) if t2_present else None,
                "care_scar_pred_volume_mm3": float((pred == 5).sum() * voxel_volume),
                "care_pure_edema_pred_volume_mm3": float((pred == 4).sum() * voxel_volume) if t2_present else None,
                "scar_remote_fp_volume_mm3": scar_remote_fp_volume,
                "scar_component_count": scar_components,
                "pure_edema_component_count": edema_components,
                "small_lesion_recall": sensitivity_for_class(pred, seg, 5) if split_row.get("scar_volume_bin") == "scar_small_lt1000mm3" else None,
                "outer_accessed": False,
            }
            case_rows.append(row)

    out_dir.mkdir(parents=True, exist_ok=False)
    with casewise_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(case_rows[0]) if case_rows else ["case_id"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(case_rows)

    scar_values = [float(row["care_scar_dice"]) for row in case_rows]
    edema_values = [float(row["care_pure_edema_dice"]) for row in case_rows if row["care_pure_edema_dice"] is not None]
    scar_hd95_values = [float(row["care_scar_hd95_mm"]) for row in case_rows]
    edema_hd95_values = [float(row["care_pure_edema_hd95_mm"]) for row in case_rows if row["care_pure_edema_hd95_mm"] is not None]
    stock_scar_hd95_values = [row["nnunet_scar_hd95_mm"] for row in case_rows]
    stock_edema_hd95_values = [row["nnunet_pure_edema_hd95_mm"] for row in case_rows if row["nnunet_pure_edema_hd95_mm"] is not None]
    scar_harm = help_harm_neutral(case_rows, "scar", "nnunet_scar_dice", 1e-6)
    edema_harm = help_harm_neutral(case_rows, "pure_edema", "nnunet_pure_edema_dice", 1e-6)
    scar_harm_denom = max(1, sum(int(v) for v in scar_harm.values()))
    edema_harm_denom = max(1, sum(int(v) for v in edema_harm.values()))
    packet = {
        "status": "PASS",
        "monitor_type": "ASYNC_INNER_TREND_ONLY",
        "allowed_uses": ["learning_trend", "implementation_or_numeric_anomaly_detection", "user_progress_report"],
        "forbidden_uses": ["early_stop", "formal_checkpoint_selection", "model_loss_sampler_scheduler_change", "threshold_tuning", "training_budget_change", "final_baseline_claim"],
        "fold": int(args.fold),
        "checkpoint_step": int(args.checkpoint_step),
        "checkpoint_path": str(checkpoint.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(checkpoint),
        "checkpoint_verified_receipt": str((checkpoint.with_name(checkpoint.stem + ".verified.json")).relative_to(REPO_ROOT)) if checkpoint.with_name(checkpoint.stem + ".verified.json").is_relative_to(REPO_ROOT) else str(checkpoint.with_name(checkpoint.stem + ".verified.json")),
        "checkpoint_verified_receipt_status": verified_receipt.get("status"),
        "checkpoint_payload_global_optimizer_step": int(payload["global_optimizer_step"]),
        "decode": "fixed_argmax_t2_present_0_1_2_3_4_5_no_t2_0_1_2_3_5",
        "full_volume_inference_settings": inference_settings.to_json_dict(),
        "split_case_lists_path": str(SPLIT_CASE_LISTS.relative_to(REPO_ROOT)),
        "split_case_lists_sha256": sha256_file(SPLIT_CASE_LISTS),
        "inner_case_count": len(inner_cases),
        "inner_cases_sha256": hashlib.sha256(json.dumps(inner_cases, sort_keys=True).encode("utf-8")).hexdigest(),
        "outer_access_count_delta": 0,
        "baseline_casewise_path": str(args.baseline_casewise.resolve().relative_to(REPO_ROOT)),
        "baseline_casewise_sha256": sha256_file(args.baseline_casewise.resolve()),
        "baseline_join": "same_case_id_nnunet_oof_mosaic_clean_oof",
        "pure_edema_population": "T2_present_inner_cases_only",
        "summary": {
            "scar_dice_mean": mean_or_none(scar_values),
            "scar_dice_median": median_or_none(scar_values),
            "scar_hd95_mean": mean_or_none(scar_hd95_values),
            "stock_scar_hd95_mean": mean_or_default(stock_scar_hd95_values, default=mean_or_none(scar_hd95_values) or 0.0),
            "scar_remote_fp_volume_mm3_mean": mean_or_none([float(row["scar_remote_fp_volume_mm3"]) for row in case_rows]),
            "scar_harm_fraction_vs_nnunet": float(scar_harm["harm"] / scar_harm_denom),
            "pure_edema_dice_mean": mean_or_none(edema_values),
            "pure_edema_dice_median": median_or_none(edema_values),
            "pure_edema_hd95_mean": mean_or_none(edema_hd95_values),
            "stock_pure_edema_hd95_mean": mean_or_default(stock_edema_hd95_values, default=mean_or_none(edema_hd95_values) or 0.0),
            "pure_edema_harm_fraction_vs_nnunet": float(edema_harm["harm"] / edema_harm_denom),
            "scar_help_harm_neutral_vs_nnunet": scar_harm,
            "scar_help_harm_neutral_vs_mosaic": help_harm_neutral(case_rows, "scar", "mosaic_scar_dice", 1e-6),
            "pure_edema_help_harm_neutral_vs_nnunet": edema_harm,
            "pure_edema_help_harm_neutral_vs_mosaic": help_harm_neutral(case_rows, "pure_edema", "mosaic_pure_edema_dice", 1e-6),
            "scar_sensitivity_mean": mean_or_none([float(row["scar_sensitivity"]) for row in case_rows if row["scar_sensitivity"] is not None]),
            "pure_edema_sensitivity_mean": mean_or_none([float(row["pure_edema_sensitivity"]) for row in case_rows if row["pure_edema_sensitivity"] is not None]),
            "scar_precision_mean": mean_or_none([float(row["scar_precision"]) for row in case_rows if row["scar_precision"] is not None]),
            "pure_edema_precision_mean": mean_or_none([float(row["pure_edema_precision"]) for row in case_rows if row["pure_edema_precision"] is not None]),
            "scar_empty_prediction_count": sum(1 for row in case_rows if row["scar_empty_prediction"]),
            "pure_edema_empty_prediction_count": sum(1 for row in case_rows if row["pure_edema_empty_prediction"] is True),
            "scar_component_count_mean": mean_or_none([float(row["scar_component_count"]) for row in case_rows]),
            "pure_edema_component_count_mean": mean_or_none([float(row["pure_edema_component_count"]) for row in case_rows if row["pure_edema_component_count"] is not None]),
            "small_lesion_recall_mean": mean_or_none([float(row["small_lesion_recall"]) for row in case_rows if row["small_lesion_recall"] is not None]),
            "scar_volume_ratio_mean": mean_or_none([float(row["scar_volume_ratio"]) for row in case_rows if row["scar_volume_ratio"] is not None]),
            "pure_edema_volume_ratio_mean": mean_or_none([float(row["pure_edema_volume_ratio"]) for row in case_rows if row["pure_edema_volume_ratio"] is not None]),
        },
        "subgroups": {
            "CenterB": subgroup_summary(case_rows, lambda row: row["center"] == "CenterB"),
            "CenterC": subgroup_summary(case_rows, lambda row: row["center"] == "CenterC"),
            "small_scar": subgroup_summary(case_rows, lambda row: row["scar_volume_bin"] == "scar_small_lt1000mm3"),
            "no_T2_scar": subgroup_summary(case_rows, lambda row: not bool_from_csv(str(row["t2_present"]))),
        },
        "casewise_metrics_path": str(casewise_path.relative_to(REPO_ROOT)),
        "reviewer_required_checks": ["case_population", "checkpoint_sha", "fixed_decode", "baseline_join"],
    }
    write_json_atomic(packet_path, packet)
    print(json.dumps(packet, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
