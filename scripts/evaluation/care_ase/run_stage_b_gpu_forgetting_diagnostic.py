#!/usr/bin/env python3
"""GPU read-only CARE-ASE Stage-B no-T2 scar forgetting diagnostics.

This diagnostic performs full-volume inference from existing verified
checkpoints and writes lightweight CSV/JSON evidence only. It never mutates
training checkpoints, sampler state, optimizer state, or formal-training logs.
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
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
from scipy import ndimage
import torch
import torch.nn.functional as F


TASK_NAME = "care-ase-faithful-formal-training-20260812"
TASK_RESULTS_REL = Path("results/agent_flow_v3") / TASK_NAME


def add_runtime_repo(runtime_repo: Path) -> None:
    for item in (runtime_repo, runtime_repo / "src"):
        if str(item) not in sys.path:
            sys.path.insert(0, str(item))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.10g}"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def bool_csv(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def mean(values: list[float]) -> float | None:
    return float(statistics.fmean(values)) if values else None


def median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def percentile(values: list[float], q: float) -> float | None:
    return float(np.percentile(np.asarray(values, dtype=np.float64), q)) if values else None


def fraction_positive(values: list[float]) -> float | None:
    return float(sum(1 for v in values if v > 0.0) / len(values)) if values else None


def tensor_stats(tensor: torch.Tensor | None, mask: torch.Tensor) -> dict[str, Any]:
    if tensor is None:
        return {"count": 0}
    vals = tensor.detach().float()[mask].cpu().numpy().astype(np.float64, copy=False)
    if vals.size == 0:
        return {"count": 0}
    as_list = vals.tolist()
    return {
        "count": int(vals.size),
        "mean": mean(as_list),
        "median": median(as_list),
        "p10": percentile(as_list, 10),
        "p25": percentile(as_list, 25),
        "frac_gt0": fraction_positive(as_list),
    }


def class_dice(pred: np.ndarray, gt: np.ndarray, cls: int) -> float:
    p = pred == cls
    g = gt == cls
    denom = int(p.sum() + g.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(p, g).sum() / denom)


def class_sensitivity(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    g = gt == cls
    total = int(g.sum())
    if total == 0:
        return None
    return float(np.logical_and(pred == cls, g).sum() / total)


def class_precision(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    p = pred == cls
    total = int(p.sum())
    if total == 0:
        return None
    return float(np.logical_and(p, gt == cls).sum() / total)


def volume_ratio(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    gt_count = int((gt == cls).sum())
    if gt_count == 0:
        return None
    return float((pred == cls).sum() / gt_count)


def class_hd95(pred: np.ndarray, gt: np.ndarray, cls: int, spacing: tuple[float, float, float]) -> float:
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


def component_count(pred: np.ndarray, cls: int) -> int:
    return int(ndimage.label(pred == cls, structure=np.ones((3, 3, 3), dtype=np.uint8))[1])


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def load_spacing(preprocessed_dir: Path, case_id: str) -> tuple[float, float, float]:
    pkl = preprocessed_dir / f"{case_id}.pkl"
    if not pkl.exists():
        return (1.0, 1.0, 1.0)
    with pkl.open("rb") as f:
        return tuple(float(v) for v in pickle.load(f).get("spacing", (1.0, 1.0, 1.0)))


def require_checkpoint(checkpoint: Path, step: int) -> dict[str, Any]:
    verified = checkpoint.with_suffix(checkpoint.suffix + ".verified.json")
    if not checkpoint.exists():
        raise FileNotFoundError(checkpoint)
    if not verified.exists():
        raise FileNotFoundError(verified)
    payload = json.loads(verified.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise RuntimeError(f"checkpoint verified receipt is not PASS: {verified}")
    if int(payload.get("global_step", step)) != int(step):
        raise RuntimeError(f"checkpoint verified step mismatch for {checkpoint}")
    return payload


def checkpoint_path(runtime_repo: Path, fold: int, step: int) -> Path:
    runtime_name = "fold_3_parallel" if int(fold) == 3 else "fold_2"
    return runtime_repo / TASK_RESULTS_REL / "runtime" / runtime_name / f"checkpoint_step{int(step):05d}.pt"


def select_cases(
    runtime_repo: Path,
    folds: list[int],
    *,
    inner_partial_limit: int,
    actual_partial_limit: int,
    complete_control_limit: int,
) -> dict[int, list[dict[str, str]]]:
    split_rows = read_csv(runtime_repo / TASK_RESULTS_REL / "split_case_lists.csv")
    selected: dict[int, list[dict[str, str]]] = defaultdict(list)
    for fold in folds:
        rows = [r for r in split_rows if int(r["fold"]) == int(fold)]
        inner_partial = [r for r in rows if r["role"] == "inner" and not bool_csv(r["t2_present"])]
        actual_partial = [r for r in rows if r["role"] == "actual-train" and not bool_csv(r["t2_present"])]
        actual_complete = [r for r in rows if r["role"] == "actual-train" and bool_csv(r["t2_present"])]
        trend = runtime_repo / TASK_RESULTS_REL / "inner_checkpoint_monitor" / f"fold_{fold}" / "step06000" / "casewise_metrics.csv"
        if trend.exists():
            score = {r["case_id"]: float(r.get("care_scar_dice") or 1.0) for r in read_csv(trend)}
            inner_partial.sort(key=lambda row: (score.get(row["case_id"], 1.0), row["case_id"]))
        else:
            inner_partial.sort(key=lambda row: row["case_id"])
        actual_partial.sort(key=lambda row: row["case_id"])
        actual_complete.sort(key=lambda row: row["case_id"])
        selected[fold].extend(inner_partial[:inner_partial_limit])
        selected[fold].extend(actual_partial[:actual_partial_limit])
        selected[fold].extend(actual_complete[:complete_control_limit])
    return selected


@dataclass
class FullVolumeDiagnostic:
    logits: torch.Tensor
    base_logits: torch.Tensor
    tensors: dict[str, torch.Tensor | None]
    metadata: dict[str, Any]


def aggregate_full_volume_diagnostic(
    model: torch.nn.Module,
    image: torch.Tensor,
    availability: torch.Tensor,
    *,
    global_step: int,
    settings: Any,
    disable_global_extent_wall: bool = False,
    disabled_named_evidence_sources: set[str] | None = None,
) -> FullVolumeDiagnostic:
    from acvl_utils.cropping_and_padding.padding import pad_nd_image
    from nnunetv2.inference.sliding_window_prediction import compute_steps_for_sliding_window
    from src.care_myocardium.inference.care_ase_r2_full_volume import (
        _aggregate_patch_tensor,
        _pad_patch_to_size,
        apply_global_extent_bias_after_aggregation,
        gaussian_importance_map,
    )

    patch_size = tuple(int(v) for v in settings.patch_size)
    overlap = float(settings.tile_step_size)
    original_spatial = tuple(int(v) for v in image.shape[-3:])
    was_training = model.training
    model.eval()
    with torch.no_grad(), torch.autocast(device_type=image.device.type, enabled=False):
        fp32_image = image.float()
        padded_image, crop_slicer = pad_nd_image(
            fp32_image,
            new_shape=patch_size,
            mode="constant",
            kwargs={"value": 0},
            return_slicer=True,
        )
        valid_original = image.new_ones((image.shape[0], 1, *original_spatial), dtype=torch.float32)
        valid_padded = pad_nd_image(
            valid_original,
            new_shape=patch_size,
            mode="constant",
            kwargs={"value": 0},
            return_slicer=False,
        )
        spatial = tuple(int(v) for v in padded_image.shape[-3:])
        starts = compute_steps_for_sliding_window(spatial, patch_size, overlap)
        base = image.new_zeros((image.shape[0], 6, *spatial), dtype=torch.float32)
        denom = image.new_zeros((image.shape[0], 1, *spatial), dtype=torch.float32)
        p_wall = image.new_zeros((image.shape[0], 1, *spatial), dtype=torch.float32)
        valid_support = image.new_zeros((image.shape[0], 1, *spatial), dtype=torch.float32)
        component_accums = {
            "scar_extent_presence": image.new_zeros((image.shape[0], 1, *spatial), dtype=torch.float32),
            "scar_extent_area": image.new_zeros((image.shape[0], 1, *spatial), dtype=torch.float32),
            "edema_extent_presence": image.new_zeros((image.shape[0], 1, *spatial), dtype=torch.float32),
            "edema_extent_area": image.new_zeros((image.shape[0], 1, *spatial), dtype=torch.float32),
        }
        diagnostic_accums = {
            key: image.new_zeros((image.shape[0], 1, *spatial), dtype=torch.float32)
            for key in (
                "anatomy_class1_logit",
                "z_scar",
                "scar_half_logit",
                "scar_full_logit",
                "scar_final_logit",
            )
        }
        metadata = {
            "input_shape": list(image.shape),
            "padded_spatial": list(spatial),
            "patch_size": list(patch_size),
            "tile_count": int(len(starts[0]) * len(starts[1]) * len(starts[2])),
            "disabled_named_evidence_sources": sorted(disabled_named_evidence_sources or []),
            "disable_global_extent_wall": bool(disable_global_extent_wall),
        }
        weight = gaussian_importance_map(
            patch_size,
            sigma_scale=float(settings.gaussian_sigma_scale),
            device=image.device,
            dtype=torch.float32,
        )
        for z in starts[0]:
            for y in starts[1]:
                for x in starts[2]:
                    patch = padded_image[..., z : z + patch_size[0], y : y + patch_size[1], x : x + patch_size[2]]
                    model_patch, _actual = _pad_patch_to_size(patch, patch_size)
                    output_size = tuple(int(v) for v in model_patch.shape[-3:])
                    outputs = model(
                        model_patch,
                        availability,
                        global_step=int(global_step),
                        disable_extent_wall=True,
                        disabled_named_evidence_sources=set(disabled_named_evidence_sources or set()),
                    )
                    local = (slice(None), slice(None), slice(0, patch_size[0]), slice(0, patch_size[1]), slice(0, patch_size[2]))
                    _aggregate_patch_tensor(base, outputs["final_logits"].float()[local] * weight, z, y, x, patch_size)
                    _aggregate_patch_tensor(p_wall, outputs["p_wall_union"].float()[local] * weight, z, y, x, patch_size)
                    valid_patch = valid_padded[..., z : z + patch_size[0], y : y + patch_size[1], x : x + patch_size[2]]
                    _aggregate_patch_tensor(valid_support, valid_patch, z, y, x, patch_size)
                    components = outputs["components"]
                    for key, target in component_accums.items():
                        up = F.interpolate(components[key].float(), size=output_size, mode="trilinear", align_corners=False)
                        _aggregate_patch_tensor(target, up[local] * weight, z, y, x, patch_size)
                    scar = outputs.get("scar", {})
                    tensor_map = {
                        "anatomy_class1_logit": outputs["final_logits"][:, 1:2],
                        "z_scar": outputs.get("z_scar"),
                        "scar_half_logit": scar.get("half_logit"),
                        "scar_full_logit": scar.get("full_logit"),
                        "scar_final_logit": scar.get("final_logit"),
                    }
                    for key, value in tensor_map.items():
                        if value is None:
                            continue
                        up = F.interpolate(value.float(), size=output_size, mode="trilinear", align_corners=False)
                        _aggregate_patch_tensor(diagnostic_accums[key], up[local] * weight, z, y, x, patch_size)
                    _aggregate_patch_tensor(denom, weight, z, y, x, patch_size)
        eps = torch.finfo(base.dtype).eps
        averaged_base = base / denom.clamp_min(eps)
        averaged_p_wall = p_wall / denom.clamp_min(eps)
        averaged_components = {key: value / denom.clamp_min(eps) for key, value in component_accums.items()}
        averaged_diag = {key: value / denom.clamp_min(eps) for key, value in diagnostic_accums.items()}
        valid_support = valid_support.clamp(0.0, 1.0)
        final_logits = averaged_base.clone()
        if not disable_global_extent_wall:
            final_logits = apply_global_extent_bias_after_aggregation(
                model,
                final_logits,
                averaged_components,
                averaged_p_wall,
                availability,
                global_step=int(global_step),
                valid_spatial_mask=valid_support,
                metadata=metadata,
            )
        spatial_crop = tuple(crop_slicer[-3:])
        final_logits = final_logits[(slice(None), slice(None), *spatial_crop)]
        averaged_base = averaged_base[(slice(None), slice(None), *spatial_crop)]
        averaged_diag = {key: value[(slice(None), slice(None), *spatial_crop)] for key, value in averaged_diag.items()}
    if was_training:
        model.train()
    return FullVolumeDiagnostic(final_logits, averaged_base, averaged_diag, metadata)


def prediction_metrics(pred: np.ndarray, seg: np.ndarray, spacing: tuple[float, float, float]) -> dict[str, Any]:
    return {
        "scar_dice": class_dice(pred, seg, 5),
        "scar_sensitivity": class_sensitivity(pred, seg, 5),
        "scar_precision": class_precision(pred, seg, 5),
        "scar_hd95_mm": class_hd95(pred, seg, 5, spacing),
        "scar_empty_prediction": int((pred == 5).sum()) == 0,
        "scar_volume_ratio": volume_ratio(pred, seg, 5),
        "scar_component_count": component_count(pred, 5),
    }


def margin_rows(
    *,
    fold: int,
    step: int,
    case_row: dict[str, str],
    diag: FullVolumeDiagnostic,
    pred: np.ndarray,
    seg: np.ndarray,
) -> list[dict[str, Any]]:
    gt_scar_mask_np = seg == 5
    normal_myo_mask_np = seg == 1
    pred_scar_mask_np = pred == 5
    device = diag.logits.device
    masks = {
        "gt_scar_voxels": torch.from_numpy(gt_scar_mask_np[None, None]).to(device=device),
        "non_scar_myocardium_voxels": torch.from_numpy(normal_myo_mask_np[None, None]).to(device=device),
        "predicted_scar_voxels": torch.from_numpy(pred_scar_mask_np[None, None]).to(device=device),
    }
    margin = diag.logits[:, 5:6].float() - diag.logits[:, 1:2].float()
    out: list[dict[str, Any]] = []
    for region, mask in masks.items():
        s = tensor_stats(margin, mask)
        branch = {
            f"{name}_{stat}": value
            for name, tensor in (
                ("scar_half_logit", diag.tensors.get("scar_half_logit")),
                ("scar_full_logit", diag.tensors.get("scar_full_logit")),
                ("scar_final_logit", diag.tensors.get("scar_final_logit")),
                ("z_scar", diag.tensors.get("z_scar")),
                ("anatomy_class1_logit", diag.tensors.get("anatomy_class1_logit")),
            )
            for stat, value in tensor_stats(tensor, mask).items()
        }
        out.append(
            {
                "fold": fold,
                "checkpoint_step": step,
                "case_id": case_row["case_id"],
                "role": case_row["role"],
                "center": case_row["center"],
                "t2_present": bool_csv(case_row["t2_present"]),
                "region": region,
                "margin_count": s.get("count"),
                "margin_mean": s.get("mean"),
                "margin_median": s.get("median"),
                "margin_p10": s.get("p10"),
                "margin_p25": s.get("p25"),
                "margin_frac_gt0": s.get("frac_gt0"),
                **branch,
            }
        )
    return out


def evidence_groups() -> dict[str, set[str]]:
    return {
        "scar_lge_adapter": {"scar_lge_to_half", "scar_lge_to_full"},
        "scar_c0_adapter": {"scar_c0_to_half", "scar_c0_to_full"},
        "scar_occupancy_proposal": {"scar_quarter_occupancy_to_half", "scar_half_occupancy_to_full"},
        "scar_center": {"scar_quarter_center_to_half", "scar_half_center_to_full"},
        "scar_context": {"scar_context_to_half", "scar_context_to_full"},
        "soft_wall_geometry": {
            "scar_p_wall_to_half",
            "scar_p_lv_to_half",
            "scar_p_rv_to_half",
            "scar_signed_endo_to_half",
            "scar_signed_epi_to_half",
            "scar_rho_to_half",
            "scar_p_wall_to_full",
            "scar_p_lv_to_full",
            "scar_p_rv_to_full",
            "scar_signed_endo_to_full",
            "scar_signed_epi_to_full",
            "scar_rho_to_full",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--folds", nargs="+", type=int, default=[2, 3])
    parser.add_argument("--steps", nargs="+", type=int, default=[2000, 6000])
    parser.add_argument("--inner-partial-limit", type=int, default=3)
    parser.add_argument("--actual-partial-limit", type=int, default=3)
    parser.add_argument("--complete-control-limit", type=int, default=1)
    parser.add_argument("--evidence-case-limit-per-fold", type=int, default=1)
    parser.add_argument("--patch-size", default="20,256,256")
    args = parser.parse_args()

    runtime_repo = args.runtime_repo.resolve()
    add_runtime_repo(runtime_repo)
    from src.care_myocardium.data.case_metadata import load_myops_case_metadata
    from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
    from src.care_myocardium.inference.care_ase_r2_full_volume import default_care_ase_full_volume_inference_settings
    from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint_for_inference

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    lock = output_dir / "gpu_readonly_diagnostic.lock"
    if lock.exists():
        raise RuntimeError(f"diagnostic lock exists: {lock}")
    lock.write_text(f"pid={os.getpid()}\n", encoding="utf-8")
    try:
        preprocessed_dir = runtime_repo / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
        metadata = load_myops_case_metadata(runtime_repo)
        patch_size = tuple(int(v.strip()) for v in args.patch_size.split(","))
        settings = default_care_ase_full_volume_inference_settings(patch_size=patch_size)
        selected = select_cases(
            runtime_repo,
            args.folds,
            inner_partial_limit=args.inner_partial_limit,
            actual_partial_limit=args.actual_partial_limit,
            complete_control_limit=args.complete_control_limit,
        )
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if device.type != "cuda":
            raise RuntimeError("GPU diagnostic requires CUDA")
        logit_rows: list[dict[str, Any]] = []
        extent_rows: list[dict[str, Any]] = []
        evidence_rows: list[dict[str, Any]] = []
        actual_rows: list[dict[str, Any]] = []
        for fold in args.folds:
            evidence_case_ids = {
                row["case_id"]
                for row in selected[fold]
                if row["role"] == "inner" and not bool_csv(row["t2_present"])
            }
            evidence_case_ids = set(sorted(evidence_case_ids)[: args.evidence_case_limit_per_fold])
            for step in args.steps:
                ckpt = checkpoint_path(runtime_repo, fold, step)
                verified = require_checkpoint(ckpt, step)
                model, payload = load_care_ase_checkpoint_for_inference(ckpt, map_location=device)
                if int(payload.get("global_optimizer_step", -1)) != int(step):
                    raise RuntimeError(f"checkpoint payload step mismatch: {ckpt}")
                model.to(device).eval()
                for case_row in selected[fold]:
                    case_id = case_row["case_id"]
                    image_np = read_b2nd(preprocessed_dir / f"{case_id}.b2nd").astype(np.float32, copy=False)
                    seg = read_b2nd(preprocessed_dir / f"{case_id}_seg.b2nd")[0].astype(np.int64, copy=False)
                    image = torch.from_numpy(image_np[None]).to(device=device, dtype=torch.float32)
                    availability = torch.tensor([metadata[case_id].availability], device=device, dtype=torch.float32)
                    spacing = load_spacing(preprocessed_dir, case_id)
                    normal = aggregate_full_volume_diagnostic(
                        model,
                        image,
                        availability,
                        global_step=step,
                        settings=settings,
                        disable_global_extent_wall=False,
                    )
                    no_extent = aggregate_full_volume_diagnostic(
                        model,
                        image,
                        availability,
                        global_step=step,
                        settings=settings,
                        disable_global_extent_wall=True,
                    )
                    pred_normal = decode_care_ase_r2_logits(normal.logits, availability).cpu().numpy().astype(np.uint8)[0]
                    pred_no_extent = decode_care_ase_r2_logits(no_extent.logits, availability).cpu().numpy().astype(np.uint8)[0]
                    normal_metrics = prediction_metrics(pred_normal, seg, spacing)
                    no_extent_metrics = prediction_metrics(pred_no_extent, seg, spacing)
                    actual_rows.append(
                        {
                            "fold": fold,
                            "checkpoint_step": step,
                            "case_id": case_id,
                            "role": case_row["role"],
                            "population": "partial_no_t2" if not bool_csv(case_row["t2_present"]) else "complete_control",
                            "center": case_row["center"],
                            "t2_present": bool_csv(case_row["t2_present"]),
                            **normal_metrics,
                        }
                    )
                    logit_rows.extend(margin_rows(fold=fold, step=step, case_row=case_row, diag=normal, pred=pred_normal, seg=seg))
                    gt_mask = torch.from_numpy((seg == 5)[None, None]).to(device=device)
                    normal_margin = normal.logits[:, 5:6] - normal.logits[:, 1:2]
                    no_extent_margin = no_extent.logits[:, 5:6] - no_extent.logits[:, 1:2]
                    extent_rows.append(
                        {
                            "fold": fold,
                            "checkpoint_step": step,
                            "case_id": case_id,
                            "role": case_row["role"],
                            "center": case_row["center"],
                            "t2_present": bool_csv(case_row["t2_present"]),
                            "changed_voxels": int((pred_normal != pred_no_extent).sum()),
                            "scar_dice_normal": normal_metrics["scar_dice"],
                            "scar_dice_no_extent_wall": no_extent_metrics["scar_dice"],
                            "scar_dice_delta_no_extent_minus_normal": no_extent_metrics["scar_dice"] - normal_metrics["scar_dice"],
                            "scar_sensitivity_delta": (no_extent_metrics["scar_sensitivity"] or 0.0) - (normal_metrics["scar_sensitivity"] or 0.0),
                            "scar_precision_delta": (no_extent_metrics["scar_precision"] or 0.0) - (normal_metrics["scar_precision"] or 0.0),
                            "scar_volume_ratio_delta": (no_extent_metrics["scar_volume_ratio"] or 0.0) - (normal_metrics["scar_volume_ratio"] or 0.0),
                            "empty_prediction_rescued": bool(normal_metrics["scar_empty_prediction"] and not no_extent_metrics["scar_empty_prediction"]),
                            "gt_scar_z_scar_delta_no_extent_minus_normal": tensor_stats(no_extent.logits[:, 5:6] - normal.logits[:, 5:6], gt_mask).get("mean"),
                            "gt_scar_margin_delta_no_extent_minus_normal": tensor_stats(no_extent_margin - normal_margin, gt_mask).get("mean"),
                        }
                    )
                    if case_id in evidence_case_ids:
                        for group_name, disabled in evidence_groups().items():
                            intervention = aggregate_full_volume_diagnostic(
                                model,
                                image,
                                availability,
                                global_step=step,
                                settings=settings,
                                disabled_named_evidence_sources=disabled,
                            )
                            pred_int = decode_care_ase_r2_logits(intervention.logits, availability).cpu().numpy().astype(np.uint8)[0]
                            int_metrics = prediction_metrics(pred_int, seg, spacing)
                            evidence_rows.append(
                                {
                                    "fold": fold,
                                    "checkpoint_step": step,
                                    "case_id": case_id,
                                    "evidence_group": group_name,
                                    "disabled_sources": "|".join(sorted(disabled)),
                                    "changed_voxels": int((pred_normal != pred_int).sum()),
                                    "scar_dice_normal": normal_metrics["scar_dice"],
                                    "scar_dice_disabled": int_metrics["scar_dice"],
                                    "scar_dice_delta_disabled_minus_normal": int_metrics["scar_dice"] - normal_metrics["scar_dice"],
                                    "scar_sensitivity_delta": (int_metrics["scar_sensitivity"] or 0.0) - (normal_metrics["scar_sensitivity"] or 0.0),
                                    "gt_scar_z_scar_delta_disabled_minus_normal": tensor_stats(intervention.logits[:, 5:6] - normal.logits[:, 5:6], gt_mask).get("mean"),
                                }
                            )
                del model
                torch.cuda.empty_cache()
        write_csv(output_dir / "actual_train_vs_inner_partial_gpu_casewise.csv", actual_rows, list(actual_rows[0]) if actual_rows else ["fold"])
        write_csv(output_dir / "logit_margin_trend.csv", logit_rows, list(logit_rows[0]) if logit_rows else ["fold"])
        write_csv(output_dir / "extent_wall_intervention.csv", extent_rows, list(extent_rows[0]) if extent_rows else ["fold"])
        write_csv(output_dir / "evidence_intervention.csv", evidence_rows, list(evidence_rows[0]) if evidence_rows else ["fold"])
        write_json(
            output_dir / "gpu_readonly_diagnostic_summary.json",
            {
                "status": "PASS",
                "task_name": TASK_NAME,
                "outer_accessed": False,
                "training_mutated": False,
                "device": torch.cuda.get_device_name(0),
                "folds": args.folds,
                "steps": args.steps,
                "selected_case_counts_by_fold": {str(k): len(v) for k, v in selected.items()},
                "checkpoints_verified_before_read": True,
            },
        )
    finally:
        lock.unlink(missing_ok=True)
    print(json.dumps({"status": "PASS", "output_dir": str(output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    import os

    raise SystemExit(main())
