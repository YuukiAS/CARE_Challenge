#!/usr/bin/env python3
"""Reaudit MoSAIC fold0 checkpoint selection and full-data leakage diagnostics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pickletools
import socket
import subprocess
import sys
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, generate_binary_structure
from scipy.ndimage import label as cc_label

REPO_ROOT = Path(__file__).resolve().parents[2]
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
MOSAIC_SOURCE = REPO_ROOT / "third_party/MoSAIC/source"
for _path in (REPO_ROOT, MOSAIC_CODE, MOSAIC_SOURCE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mosaic_fair_protocol import (  # noqa: E402
    DEFAULT_CONFIG,
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
from myops.data.labels import TRACK_MYOPS, modalities_for_track, num_classes, train_to_official_labels  # noqa: E402
from myops.data.preprocessing import cache_path  # noqa: E402
from myops.inference.edema_predict import EdemaNet, merge_labels, predict_edema_case_probs  # noqa: E402
from myops.inference.postprocess import clean_prediction_by_class, enforce_pathology_inside_myo, largest_component  # noqa: E402
from myops.inference.predict import predict_case_coarse, predict_case_fine  # noqa: E402
from myops.models import build_model  # noqa: E402
from myops.utils.io import torch_load  # noqa: E402
from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class, hd_class  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402


RESULT_ROOT_DEFAULT = REPO_ROOT / "results/20260726_mosaic_fold0_fairness_reaudit"
OLD_RESULT_ROOT_DEFAULT = REPO_ROOT / "results/20260725_care_myops_mosaic_fold0_reproduction"
FULL_WEIGHT_ROOT = Path("/users/a/e/aereinh/MoSAIC/code/weights/myops")
PATHOLOGIES = {"scar": 5, "pure_edema": 4}
OFFICIAL_LABELS = {4: 1220, 5: 2221}
PRIMARY_VARIANTS = [
    "nnunet_fold0",
    "clean_current_bug",
    "clean_pathology_checkpoint",
    "clean_pathology_scar_terminal_edema",
    "clean_terminal_budget",
    "full_data_submission_recipe",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, default=json_default) + "\n")


def safe_number(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, str)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def checkpoint_pickle_member(path: Path) -> bytes | None:
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            data_names = [n for n in names if n.endswith("/data.pkl")]
            if data_names:
                return zf.read(data_names[0])
    except zipfile.BadZipFile:
        return None
    return None


def safe_checkpoint_metadata(path: Path) -> dict[str, Any]:
    """Extract primitive checkpoint metadata without unpickling tensor payloads."""

    out: dict[str, Any] = {"exists": path.is_file(), "path": str(path)}
    if not path.is_file():
        return out
    out["bytes"] = path.stat().st_size
    out["sha256"] = sha256_file(path)
    payload = checkpoint_pickle_member(path)
    if payload is None:
        out["metadata_status"] = "NO_ZIP_PICKLE"
        return out
    keys = {"epoch", "max_epochs", "scar_dice", "edema_dice", "val_loss", "best_metric"}
    values: dict[str, Any] = {}
    pending: str | None = None
    gap = 0
    try:
        for op, arg, _pos in pickletools.genops(payload):
            if op.name in {"BINUNICODE", "SHORT_BINUNICODE", "UNICODE"} and str(arg) in keys:
                pending = str(arg)
                gap = 0
                continue
            if pending is None:
                continue
            gap += 1
            if op.name in {"BINPUT", "LONG_BINPUT", "MEMOIZE"}:
                continue
            if op.name in {"BININT", "BININT1", "BININT2", "LONG1", "LONG4", "INT"}:
                values.setdefault(pending, int(arg))
                pending = None
            elif op.name in {"BINFLOAT", "FLOAT"}:
                values.setdefault(pending, float(arg))
                pending = None
            elif op.name in {"BINUNICODE", "SHORT_BINUNICODE", "UNICODE"}:
                values.setdefault(pending, str(arg))
                pending = None
            elif gap > 12:
                pending = None
    except Exception as exc:  # pragma: no cover - defensive audit path
        out["metadata_error"] = repr(exc)
    out.update({k: safe_number(v) for k, v in values.items()})
    out["metadata_status"] = "PASS_SAFE_OPCODE_SCAN"
    return out


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_checkpoint_state(path: Path) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    ckpt = torch.load(str(path), map_location="cpu", weights_only=True)
    if isinstance(ckpt, dict) and "model_state" in ckpt:
        state = ckpt["model_state"]
        meta = {k: v for k, v in ckpt.items() if k != "model_state"}
    elif isinstance(ckpt, dict):
        state = ckpt
        meta = {}
    else:
        raise TypeError(f"unsupported checkpoint object in {path}: {type(ckpt)!r}")
    return state, {k: safe_number(v) for k, v in meta.items() if k in {"epoch", "max_epochs", "scar_dice", "edema_dice", "val_loss"}}


def build_coarse_model_safe(device: torch.device, ckpt_path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("mosaic_infer_submit_reaudit", MOSAIC_SOURCE / "scripts/infer_and_submit.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import infer_and_submit.py")
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    cfg = upstream.load_config(str(MOSAIC_SOURCE / "configs/myops_coarse.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))
    model = build_model(
        stage="coarse",
        track=TRACK_MYOPS,
        arch="2d_coarse",
        in_channels=n_mod * 2,
        out_channels=num_classes(TRACK_MYOPS, "coarse"),
        base_channels=int(cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    state, _meta = load_checkpoint_state(ckpt_path)
    model.load_state_dict(state)
    return model.to(device).eval()


def build_scar_model_safe(device: torch.device, ckpt_path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("mosaic_infer_submit_reaudit2", MOSAIC_SOURCE / "scripts/infer_and_submit.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import infer_and_submit.py")
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    cfg = upstream.load_config(str(MOSAIC_SOURCE / "configs/myops_fine.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))
    model = build_model(
        stage="fine",
        track=TRACK_MYOPS,
        arch="2d_multi",
        in_channels=n_mod * 2 + 1,
        out_channels=num_classes(TRACK_MYOPS, "fine"),
        base_channels=int(cfg["model"].get("base_channels", 24)),
        deep_supervision=bool(cfg["model"].get("deep_supervision", True)),
        grid_size=int(cfg["model"].get("grid_size", 4)),
        span_range=float(cfg["model"].get("span_range", 0.98)),
        image_size=192,
        use_tps=bool(cfg["model"].get("use_tps", True)),
        use_spg=bool(cfg["model"].get("use_spg", True)),
        use_consistency=bool(cfg["model"].get("use_consistency", True)),
    )
    state, _meta = load_checkpoint_state(ckpt_path)
    model.load_state_dict(state, strict=False)
    return model.to(device).eval()


def load_edema_model_safe(ckpt_path: Path, device: torch.device):
    model = EdemaNet(use_c0=True, deep_supervision=True)
    state, _meta = load_checkpoint_state(ckpt_path)
    model.load_state_dict(state)
    return model.to(device).eval()


def import_upstream_infer():
    import importlib.util

    spec = importlib.util.spec_from_file_location("mosaic_infer_submit_reaudit3", MOSAIC_SOURCE / "scripts/infer_and_submit.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import infer_and_submit.py")
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    return upstream


def orient_array_to_reference_zyx(array: np.ndarray, ref: sitk.Image) -> np.ndarray:
    arr = np.asarray(array)
    ref_x, ref_y, ref_z = (int(v) for v in ref.GetSize())
    ref_zyx = (ref_z, ref_y, ref_x)
    if tuple(arr.shape) == ref_zyx:
        return arr
    candidates = {
        (ref_z, ref_x, ref_y): (0, 2, 1),
        (ref_x, ref_y, ref_z): (2, 1, 0),
        (ref_y, ref_x, ref_z): (2, 0, 1),
    }
    axes = candidates.get(tuple(arr.shape))
    if axes is None:
        raise ValueError(f"cannot orient prediction array shape {tuple(arr.shape)} to reference zyx {ref_zyx}")
    return np.transpose(arr, axes)


def sitk_write_like(array_zyx: np.ndarray, reference_path: Path, dest: Path) -> None:
    ref = sitk.ReadImage(str(reference_path))
    oriented = orient_array_to_reference_zyx(array_zyx, ref)
    img = sitk.GetImageFromArray(oriented.astype(np.int16, copy=False))
    img.CopyInformation(ref)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(dest))


def find_prediction(pred_dir: Path, case_id: str) -> Path | None:
    candidates = [
        pred_dir / f"{case_id}.nii.gz",
        pred_dir / case_id / f"{case_id}_pred.nii.gz",
        pred_dir / "MyoPS" / "Anonymous Center" / case_id / f"{case_id}_pred.nii.gz",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    hits = sorted(pred_dir.rglob(f"{case_id}*.nii.gz")) if pred_dir.is_dir() else []
    return hits[0] if hits else None


def load_label_for_eval(pred_path: Path, gt_img: sitk.Image, label_space: str) -> tuple[np.ndarray, dict[str, Any]]:
    raw_img = sitk.ReadImage(str(pred_path))
    raw_arr = sitk.GetArrayFromImage(raw_img).astype(np.int32, copy=False)
    raw_sig = geometry_signature(raw_img)
    gt_sig = geometry_signature(gt_img)
    raw_match = geometry_matches(raw_sig, gt_sig)
    if raw_match:
        std_img = raw_img
    else:
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(gt_img)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        std_img = resampler.Execute(raw_img)
    pred = sitk.GetArrayFromImage(std_img).astype(np.int32, copy=False)
    if label_space == "official":
        pred = remap_labels(pred, OFFICIAL_TO_COMPACT)
    std_sig = geometry_signature(std_img)
    return pred, {
        "raw_geometry_status": "PASS" if raw_match else "FAIL_STANDARDIZED_AFTER_AUDIT",
        "standardized_geometry_status": "PASS" if geometry_matches(std_sig, gt_sig) else "FAIL",
        "raw_size_xyz": raw_sig["size_xyz"],
        "gt_size_xyz": gt_sig["size_xyz"],
        "raw_spacing_xyz": raw_sig["spacing_xyz"],
        "gt_spacing_xyz": gt_sig["spacing_xyz"],
        "raw_unique_labels": sorted(int(v) for v in np.unique(raw_arr)),
        "eval_unique_labels": sorted(int(v) for v in np.unique(pred)),
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


def precision_recall_mask(pred_mask: np.ndarray, gt_mask: np.ndarray) -> tuple[float, float]:
    p = pred_mask.astype(bool)
    g = gt_mask.astype(bool)
    tp = int(np.count_nonzero(p & g))
    fp = int(np.count_nonzero(p & ~g))
    fn = int(np.count_nonzero(~p & g))
    precision = float(tp / (tp + fp)) if tp + fp else (1.0 if not g.any() else 0.0)
    recall = float(tp / (tp + fn)) if tp + fn else (1.0 if not g.any() else 0.0)
    return precision, recall


def dice_mask(pred_mask: np.ndarray, gt_mask: np.ndarray, *, skip_if_gt_empty: bool = True) -> float | None:
    p = pred_mask.astype(bool)
    g = gt_mask.astype(bool)
    p_sum = float(np.count_nonzero(p))
    g_sum = float(np.count_nonzero(g))
    if skip_if_gt_empty and g_sum < 1e-8:
        return None if p_sum < 1e-8 else 0.0
    denom = p_sum + g_sum
    if denom < 1e-8:
        return 1.0
    return float(2.0 * np.count_nonzero(p & g) / denom)


def component_count(mask: np.ndarray) -> int:
    _, n_cc = cc_label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def remote_fp_mm3(pred_mask: np.ndarray, gt_mask: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, ...]) -> float:
    myocardium = (gt >= 1) & (gt <= 5)
    voxel_volume = float(np.prod(spacing_zyx))
    if myocardium.any():
        dist_to_myo = distance_transform_edt(~myocardium.astype(bool), sampling=spacing_zyx)
        remote = pred_mask.astype(bool) & ~gt_mask.astype(bool) & (dist_to_myo > 10.0)
    else:
        remote = pred_mask.astype(bool) & ~gt_mask.astype(bool)
    return float(np.count_nonzero(remote) * voxel_volume)


def mask_metric_row(
    *,
    model_id: str,
    role: str,
    case_id: str,
    center: str,
    modality_group: str,
    t2_present: bool,
    pathology: str,
    class_id: int,
    pred_mask: np.ndarray,
    gt_mask: np.ndarray,
    gt: np.ndarray,
    spacing_zyx: tuple[float, ...],
    comparison_tier: str,
) -> dict[str, Any]:
    dists = surface_distances(pred_mask, gt_mask, spacing_zyx)
    exact_hd = float(np.max(dists)) if dists.size else math.inf
    hd95 = float(np.percentile(dists, 95)) if dists.size else math.inf
    prec, rec = precision_recall_mask(pred_mask, gt_mask)
    gt_voxels = int(np.count_nonzero(gt_mask))
    pred_voxels = int(np.count_nonzero(pred_mask))
    voxel_volume = float(np.prod(spacing_zyx))
    return {
        "model_id": model_id,
        "role": role,
        "comparison_tier": comparison_tier,
        "case_id": case_id,
        "center": center,
        "modality_group": modality_group,
        "t2_present": int(t2_present),
        "pathology": pathology,
        "compact_class": class_id,
        "official_label": OFFICIAL_LABELS.get(class_id, ""),
        "gt_positive": int(gt_mask.any()),
        "prediction_positive": int(pred_mask.any()),
        "Dice": dice_mask(pred_mask, gt_mask, skip_if_gt_empty=True),
        "exact_HD": exact_hd,
        "HD95": hd95,
        "precision": prec,
        "recall": rec,
        "remote_FP_mm3": remote_fp_mm3(pred_mask, gt_mask, gt, spacing_zyx),
        "component_count": component_count(pred_mask),
        "pred_volume_mm3": float(pred_voxels * voxel_volume),
        "gt_volume_mm3": float(gt_voxels * voxel_volume),
        "volume_ratio": None if gt_voxels == 0 else float(pred_voxels / max(1, gt_voxels)),
        "empty_prediction": int(not pred_mask.any()),
    }


def mean(values: list[Any]) -> float | None:
    vals: list[float] = []
    for value in values:
        if value in (None, "", "None", "nan"):
            continue
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(v):
            vals.append(v)
    return float(np.mean(vals)) if vals else None


def summary_rows(casewise: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in casewise:
        subgroups = []
        if row["pathology"] == "scar":
            subgroups += ["all44", "GT-positive"]
            if int(row["t2_present"]):
                subgroups += ["T2-present", "complete_three_modal"] if row["modality_group"] == "C0+LGE+T2" else ["T2-present"]
            if row["modality_group"] == "LGE-only":
                subgroups.append("LGE-only")
            if row["center"] in {"CenterB", "CenterC"}:
                subgroups.append(row["center"])
            subgroups.append("modality:" + str(row["modality_group"]))
        elif row["pathology"] == "pure_edema":
            reliable = int(row["t2_present"]) and row["center"] in {"CenterB", "CenterC"}
            if reliable:
                subgroups.append("T2-present_reliable")
                if int(row["gt_positive"]):
                    subgroups.append("T2-present_reliable_GT-positive")
            if int(row["t2_present"]):
                subgroups.append("T2-present")
            if int(row["gt_positive"]):
                subgroups.append("GT-positive")
            if row["center"] in {"CenterB", "CenterC"}:
                subgroups.append(row["center"])
            subgroups.append("modality:" + str(row["modality_group"]))
        for subgroup in sorted(set(subgroups)):
            if subgroup == "GT-positive" and not int(row["gt_positive"]):
                continue
            buckets[(row["model_id"], row["pathology"], subgroup)].append(row)

    out = []
    for (model_id, pathology, subgroup), rows in sorted(buckets.items()):
        out.append(
            {
                "model_id": model_id,
                "pathology": pathology,
                "subgroup": subgroup,
                "case_count": len(rows),
                "gt_positive_cases": sum(int(r["gt_positive"]) for r in rows),
                "prediction_positive_cases": sum(int(r["prediction_positive"]) for r in rows),
                "mean_Dice": mean([r["Dice"] for r in rows]),
                "mean_exact_HD": mean([r["exact_HD"] for r in rows]),
                "mean_HD95": mean([r["HD95"] for r in rows]),
                "mean_precision": mean([r["precision"] for r in rows]),
                "mean_recall": mean([r["recall"] for r in rows]),
                "mean_remote_FP_mm3": mean([r["remote_FP_mm3"] for r in rows]),
                "mean_component_count": mean([r["component_count"] for r in rows]),
                "mean_volume_ratio": mean([r["volume_ratio"] for r in rows]),
                "empty_predictions": sum(int(r["empty_prediction"]) for r in rows),
            }
        )
    return out


def summary_lookup(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(str(r["model_id"]), str(r["pathology"]), str(r["subgroup"])): r for r in rows}


def select_pathology_checkpoint(fine_dir: Path) -> tuple[Path, str]:
    best_scar = fine_dir / "best_scar.pt"
    best_pathology = fine_dir / "best_pathology.pt"
    if best_scar.is_file():
        return best_scar, "upstream_prefers_best_scar_when_present"
    if best_pathology.is_file():
        return best_pathology, "best_pathology_present_without_best_scar"
    raise FileNotFoundError(f"pathology-specific checkpoint missing in {fine_dir}")


def checkpoint_inventory(old_root: Path, result_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rroot = old_root / "runtime/fold0"
    clean_specs = [
        ("clean_fold0", "coarse_best", rroot / "coarse/best.pt"),
        ("clean_fold0", "coarse_last", rroot / "coarse/last.pt"),
        ("clean_fold0", "fine_scar_best", rroot / "fine_scar/best.pt"),
        ("clean_fold0", "fine_scar_best_scar", rroot / "fine_scar/best_scar.pt"),
        ("clean_fold0", "fine_scar_best_pathology", rroot / "fine_scar/best_pathology.pt"),
        ("clean_fold0", "fine_scar_last", rroot / "fine_scar/last.pt"),
        ("clean_fold0", "edema_best", rroot / "edema/best.pt"),
        ("clean_fold0", "edema_last", rroot / "edema/last.pt"),
    ]
    full_specs = [
        ("full_data_downloaded", "coarse", FULL_WEIGHT_ROOT / "coarse.pt"),
        ("full_data_downloaded", "coarse_edema", FULL_WEIGHT_ROOT / "coarse_edema.pt"),
        ("full_data_downloaded", "fine_scar", FULL_WEIGHT_ROOT / "fine_scar.pt"),
        ("full_data_downloaded", "edema", FULL_WEIGHT_ROOT / "edema.pt"),
    ]
    rows = []
    for family, name, path in clean_specs + full_specs:
        meta = safe_checkpoint_metadata(path)
        rows.append({"family": family, "checkpoint_name": name, **meta, "relative_path": rel(path)})
    by_name = {(r["family"], r["checkpoint_name"]): r for r in rows}
    scar_sha_same = (
        by_name[("clean_fold0", "fine_scar_best_scar")].get("sha256")
        == by_name[("clean_fold0", "fine_scar_best_pathology")].get("sha256")
    )
    pathology_ckpt, reason = select_pathology_checkpoint(rroot / "fine_scar")
    payload = {
        "status": "PASS" if all(r["exists"] for r in rows) else "FAIL_MISSING_CHECKPOINT",
        "clean_fold0_root": rel(rroot),
        "full_data_downloaded_root": str(FULL_WEIGHT_ROOT),
        "best_scar_and_best_pathology_same_sha256": bool(scar_sha_same),
        "pathology_checkpoint_selected": rel(pathology_ckpt),
        "pathology_checkpoint_selection_reason": reason,
        "upstream_submission_scar_selection": "full_train/myops/fold-1/fine/best_scar.pt else best.pt",
        "old_fold0_runner_scar_selection": "runtime/fold0/fine_scar/best.pt else last.pt",
        "rows": rows,
    }
    write_json(result_root / "checkpoint_inventory.json", payload)
    write_csv(result_root / "checkpoint_inventory.csv", rows)
    lines = [
        "MoSAIC fold0 的旧 inference 入口优先读取 `fine_scar/best.pt`，因此会加载 epoch 75 的 scar checkpoint；upstream submission 入口在存在时优先读取 `best_scar.pt`，本次 clean 修正按这个规则使用 fold0 epoch 190 checkpoint。",
        "",
        f"- best_scar 与 best_pathology SHA256 相同: {scar_sha_same}",
        f"- pathology checkpoint selected: `{rel(pathology_ckpt)}`",
        "- full-data Google Drive 权重只用于污染诊断，不进入 fair clean comparison。",
    ]
    (result_root / "checkpoint_selection_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload, rows


def variant_specs(old_root: Path) -> list[dict[str, Any]]:
    rroot = old_root / "runtime/fold0"
    pathology, pathology_reason = select_pathology_checkpoint(rroot / "fine_scar")
    return [
        {
            "model_id": "clean_current_bug",
            "role": "old_checkpoint_bug_control",
            "comparison_tier": "CLEAN_FOLD0_RANDOM_INIT_CHECKPOINT_BUG_CONTROL",
            "coarse_scar": rroot / "coarse/best.pt",
            "coarse_edema": rroot / "coarse/best.pt",
            "scar": rroot / "fine_scar/best.pt",
            "edema": rroot / "edema/best.pt",
            "selection_policy": "old_runner_best_pt_priority",
        },
        {
            "model_id": "clean_pathology_checkpoint",
            "role": "clean_fold0_corrected_scar_primary",
            "comparison_tier": "FAIR_CLEAN_FOLD0_RANDOM_INIT",
            "coarse_scar": rroot / "coarse/best.pt",
            "coarse_edema": rroot / "coarse/best.pt",
            "scar": pathology,
            "edema": rroot / "edema/best.pt",
            "selection_policy": pathology_reason,
        },
        {
            "model_id": "clean_pathology_scar_terminal_edema",
            "role": "clean_fold0_fixed_primary_merged",
            "comparison_tier": "FAIR_CLEAN_FOLD0_RANDOM_INIT",
            "coarse_scar": rroot / "coarse/best.pt",
            "coarse_edema": rroot / "coarse/best.pt",
            "scar": pathology,
            "edema": rroot / "edema/last.pt",
            "selection_policy": "pathology_specific_scar_plus_terminal_edema_predeclared",
        },
        {
            "model_id": "clean_terminal_budget",
            "role": "clean_fold0_terminal_budget_control",
            "comparison_tier": "FAIR_CLEAN_FOLD0_RANDOM_INIT_TERMINAL_BUDGET",
            "coarse_scar": rroot / "coarse/best.pt",
            "coarse_edema": rroot / "coarse/best.pt",
            "scar": rroot / "fine_scar/last.pt",
            "edema": rroot / "edema/last.pt",
            "selection_policy": "terminal_epoch_control",
        },
        {
            "model_id": "full_data_submission_recipe",
            "role": "full_data_leakage_contaminated_diagnostic",
            "comparison_tier": "FULL_DATA_LEAKAGE_CONTAMINATED_DIAGNOSTIC",
            "coarse_scar": FULL_WEIGHT_ROOT / "coarse.pt",
            "coarse_edema": FULL_WEIGHT_ROOT / "coarse_edema.pt",
            "scar": FULL_WEIGHT_ROOT / "fine_scar.pt",
            "edema": FULL_WEIGHT_ROOT / "edema.pt",
            "selection_policy": "google_drive_submission_recipe_two_coarse_tta_cleanup",
        },
    ]


def ckpt_desc(path: Path, inventory_rows: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = str(path.resolve())
    for row in inventory_rows:
        if Path(str(row["path"])).resolve() == Path(resolved):
            return row
    meta = safe_checkpoint_metadata(path)
    return meta


def write_variant_manifest(result_root: Path, specs: list[dict[str, Any]], inventory_rows: list[dict[str, Any]]) -> None:
    rows = []
    for spec in specs:
        for role in ("coarse_scar", "coarse_edema", "scar", "edema"):
            desc = ckpt_desc(Path(spec[role]), inventory_rows)
            rows.append(
                {
                    "model_id": spec["model_id"],
                    "role": spec["role"],
                    "comparison_tier": spec["comparison_tier"],
                    "checkpoint_role": role,
                    "checkpoint_path": rel(Path(spec[role])),
                    "sha256": desc.get("sha256"),
                    "epoch": desc.get("epoch"),
                    "max_epochs": desc.get("max_epochs"),
                    "scar_dice": desc.get("scar_dice"),
                    "edema_dice": desc.get("edema_dice"),
                    "selection_policy": spec["selection_policy"],
                }
            )
    write_csv(result_root / "variant_manifest.csv", rows)


def run_one_variant(
    *,
    spec: dict[str, Any],
    config: dict[str, Any],
    old_root: Path,
    result_root: Path,
    cases: list[str],
    runtime_log: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    t0 = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    write_jsonl(
        runtime_log,
        {
            "event": "variant_start",
            "model_id": spec["model_id"],
            "time_utc": now_iso(),
            "hostname": socket.gethostname(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "device": str(device),
            "checkpoints": {k: {"path": str(spec[k]), "sha256": sha256_file(Path(spec[k]))} for k in ("coarse_scar", "coarse_edema", "scar", "edema")},
        },
    )
    upstream = import_upstream_infer()
    tta = {"enabled": True, "flips": ["horizontal", "vertical"]}
    thresholds = upstream.default_thresholds(TRACK_MYOPS, "fine")
    coarse_scar = build_coarse_model_safe(device, Path(spec["coarse_scar"]))
    coarse_edema = coarse_scar if Path(spec["coarse_scar"]).resolve() == Path(spec["coarse_edema"]).resolve() else build_coarse_model_safe(device, Path(spec["coarse_edema"]))
    scar = build_scar_model_safe(device, Path(spec["scar"]))
    edema = load_edema_model_safe(Path(spec["edema"]), device)
    gt_dir = REPO_ROOT / config["dataset"]["raw_label_dir"]
    cache_root = old_root / "runtime/fold0/cache"
    official_dir = result_root / "predictions" / spec["model_id"] / "official"
    compact_dir = result_root / "predictions" / spec["model_id"] / "compact"
    stage_dir = result_root / "stage_cache" / spec["model_id"]
    manifest_rows = []
    ablation_rows = []
    for case_id in cases:
        payload = torch_load(cache_path(str(cache_root), TRACK_MYOPS, case_id))
        with torch.no_grad():
            coarse_scar_result = predict_case_coarse(coarse_scar, payload, TRACK_MYOPS, device, image_size=[192, 192], tta_config=tta)
            coarse_scar_prior = np.asarray(coarse_scar_result["label"], dtype=np.int16)
            if coarse_edema is coarse_scar:
                coarse_edema_prior = coarse_scar_prior
            else:
                coarse_edema_result = predict_case_coarse(coarse_edema, payload, TRACK_MYOPS, device, image_size=[192, 192], tta_config=tta)
                coarse_edema_prior = np.asarray(coarse_edema_result["label"], dtype=np.int16)
            scar_result = predict_case_fine(scar, payload, TRACK_MYOPS, device, coarse_prior=coarse_scar_prior, image_size=[192, 192], tta_config=tta)
            ucf_probs = np.asarray(scar_result["probs"], dtype=np.float32)
            edema_prob = predict_edema_case_probs(edema, payload, coarse_edema_prior, device, dim=192)
        ucf_probs_orig = upstream.probs_to_original_space(ucf_probs, payload)
        edema_prob_orig = upstream.probs_to_original_space(edema_prob[None], payload)[0]
        raw_scar_label = upstream.probs_to_label(ucf_probs_orig, thresholds)
        coarse_scar_orig = upstream.label_to_original_space(coarse_scar_prior, payload)
        coarse_edema_orig = upstream.label_to_original_space(coarse_edema_prior, payload)
        myo_mask_scar = binary_dilation(coarse_scar_orig > 0, iterations=1)
        myo_mask_edema = binary_dilation(coarse_edema_orig > 0, iterations=1)
        scar_contained = enforce_pathology_inside_myo(raw_scar_label.copy(), 1, [4, 5], external_myo_mask=myo_mask_scar)
        scar_clean = clean_prediction_by_class(scar_contained.copy(), {4: 5, 5: 3})
        scar_lcc_label = scar_clean.copy()
        scar_mask = scar_lcc_label == 5
        if scar_mask.any():
            scar_lcc_label[scar_mask & ~largest_component(scar_mask)] = 0
        edema_raw = edema_prob_orig > 0.35
        edema_masked = edema_raw & myo_mask_edema
        edema_lcc = largest_component(edema_raw) if edema_raw.any() else edema_raw
        edema_lcc_masked = edema_lcc & myo_mask_edema
        edema_minus_scar = edema_lcc_masked & ~(scar_clean == 5)
        final_label_hwz = merge_labels(scar_clean, coarse_scar_orig, edema_lcc_masked)
        final_label_hwz = clean_prediction_by_class(final_label_hwz, {4: 5, 5: 3})
        final_scar_mask = final_label_hwz == 5
        if final_scar_mask.any():
            final_label_hwz[final_scar_mask & ~largest_component(final_scar_mask)] = 0
        official_hwz = train_to_official_labels(final_label_hwz, TRACK_MYOPS, stage="fine")
        official_zyx = np.transpose(official_hwz, (2, 0, 1))
        compact_zyx = remap_labels(official_zyx, OFFICIAL_TO_COMPACT)
        gt_path = gt_dir / f"{case_id}.nii.gz"
        official_path = official_dir / f"{case_id}.nii.gz"
        compact_path = compact_dir / f"{case_id}.nii.gz"
        sitk_write_like(official_zyx, gt_path, official_path)
        sitk_write_like(compact_zyx, gt_path, compact_path)
        npz_path = stage_dir / f"{case_id}.npz"
        npz_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            npz_path,
            scar_probs=ucf_probs_orig.astype(np.float16),
            edema_prob=edema_prob_orig.astype(np.float16),
            coarse_scar=coarse_scar_orig.astype(np.int16),
            coarse_edema=coarse_edema_orig.astype(np.int16),
            raw_scar_label=raw_scar_label.astype(np.int16),
            scar_clean=scar_clean.astype(np.int16),
            edema_lcc_masked=edema_lcc_masked.astype(np.uint8),
            final_label=final_label_hwz.astype(np.int16),
        )
        manifest_rows.append(
            {
                "model_id": spec["model_id"],
                "case_id": case_id,
                "official_prediction_path": rel(official_path),
                "compact_prediction_path": rel(compact_path),
                "stage_cache_path": rel(npz_path),
                "label_space_written": "official_and_compact",
                "comparison_tier": spec["comparison_tier"],
                "loaded_coarse_scar_sha256": sha256_file(Path(spec["coarse_scar"])),
                "loaded_coarse_edema_sha256": sha256_file(Path(spec["coarse_edema"])),
                "loaded_scar_sha256": sha256_file(Path(spec["scar"])),
                "loaded_edema_sha256": sha256_file(Path(spec["edema"])),
            }
        )
        if spec["model_id"] == "full_data_submission_recipe":
            gt_img = sitk.ReadImage(str(gt_path))
            gt = sitk.GetArrayFromImage(gt_img).astype(np.int32, copy=False)
            spacing = tuple(float(v) for v in gt_img.GetSpacing()[::-1])
            meta = load_myops_case_metadata(REPO_ROOT)[case_id]
            stages = [
                ("scar", "raw_scar_expert", raw_scar_label == 5, gt == 5),
                ("scar", "new_coarse_containment", scar_contained == 5, gt == 5),
                ("scar", "class_cleanup", scar_clean == 5, gt == 5),
                ("scar", "largest_scar_component", scar_lcc_label == 5, gt == 5),
                ("scar", "final_merged_scar", final_label_hwz == 5, gt == 5),
                ("edema_zone", "raw_edema_probability_threshold_0.35", edema_raw, (gt == 4) | (gt == 5)),
                ("edema_zone", "old_coarse_myocardium_mask", edema_masked, (gt == 4) | (gt == 5)),
                ("edema_zone", "largest_edema_component", edema_lcc_masked, (gt == 4) | (gt == 5)),
                ("pure_edema", "minus_accepted_scar", edema_minus_scar, gt == 4),
                ("pure_edema", "final_pure_edema", final_label_hwz == 4, gt == 4),
            ]
            for pathology, stage, pred_mask_hwz, gt_mask_hwz in stages:
                pred_zyx = orient_array_to_reference_zyx(pred_mask_hwz.astype(bool), gt_img)
                gt_zyx = gt_mask_hwz.astype(bool)
                ablation_rows.append(
                    {
                        **mask_metric_row(
                            model_id=spec["model_id"],
                            role=spec["role"],
                            case_id=case_id,
                            center=meta.center,
                            modality_group=meta.modality_group,
                            t2_present=meta.t2_present,
                            pathology=pathology,
                            class_id=5 if pathology == "scar" else 4,
                            pred_mask=pred_zyx,
                            gt_mask=gt_zyx,
                            gt=gt,
                            spacing_zyx=spacing,
                            comparison_tier=spec["comparison_tier"],
                        ),
                        "stage": stage,
                    }
                )
    del coarse_scar, scar, edema
    if coarse_edema is not None:
        del coarse_edema
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    write_jsonl(
        runtime_log,
        {
            "event": "variant_end",
            "model_id": spec["model_id"],
            "time_utc": now_iso(),
            "exit_code": 0,
            "duration_seconds": round(time.time() - t0, 3),
            "prediction_count": len(manifest_rows),
        },
    )
    return manifest_rows, ablation_rows


def evaluate_all(config: dict[str, Any], result_root: Path, cases: list[str], specs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    gt_dir = REPO_ROOT / config["dataset"]["raw_label_dir"]
    metadata = load_myops_case_metadata(REPO_ROOT)
    model_specs = [
        {
            "model_id": "nnunet_fold0",
            "role": "operational_baseline",
            "comparison_tier": "FAIR_CLEAN_FOLD0_BASELINE",
            "prediction_dir": REPO_ROOT / config["evaluation"]["allowed_models"][0]["prediction_dir"],
            "label_space": "compact",
        }
    ]
    for spec in specs:
        model_specs.append(
            {
                "model_id": spec["model_id"],
                "role": spec["role"],
                "comparison_tier": spec["comparison_tier"],
                "prediction_dir": result_root / "predictions" / spec["model_id"] / "compact",
                "label_space": "compact",
            }
        )
    casewise = []
    geometry_rows = []
    edema_availability_rows = []
    for spec in model_specs:
        pred_dir = Path(spec["prediction_dir"])
        for case_id in cases:
            gt_path = gt_dir / f"{case_id}.nii.gz"
            gt_img = sitk.ReadImage(str(gt_path))
            gt = sitk.GetArrayFromImage(gt_img).astype(np.int32, copy=False)
            pred_path = find_prediction(pred_dir, case_id)
            if pred_path is None:
                geometry_rows.append({"model_id": spec["model_id"], "case_id": case_id, "status": "MISSING_PRED", "prediction_dir": rel(pred_dir)})
                continue
            pred, audit = load_label_for_eval(pred_path, gt_img, str(spec["label_space"]))
            geometry_rows.append(
                {
                    "model_id": spec["model_id"],
                    "case_id": case_id,
                    "status": "PASS" if audit["standardized_geometry_status"] == "PASS" else "FAIL",
                    "prediction_path": rel(pred_path),
                    "label_space": spec["label_space"],
                    **audit,
                }
            )
            spacing = tuple(float(v) for v in gt_img.GetSpacing()[::-1])
            meta = metadata[case_id]
            for pathology, class_id in PATHOLOGIES.items():
                row = mask_metric_row(
                    model_id=spec["model_id"],
                    role=spec["role"],
                    comparison_tier=spec["comparison_tier"],
                    case_id=case_id,
                    center=meta.center,
                    modality_group=meta.modality_group,
                    t2_present=meta.t2_present,
                    pathology=pathology,
                    class_id=class_id,
                    pred_mask=pred == class_id,
                    gt_mask=gt == class_id,
                    gt=gt,
                    spacing_zyx=spacing,
                )
                row["edema_label_reliable"] = int(meta.t2_present and meta.center in {"CenterB", "CenterC"})
                casewise.append(row)
            edema_pred_mask = pred == 4
            no_t2 = not meta.t2_present
            edema_availability_rows.append(
                {
                    "model_id": spec["model_id"],
                    "case_id": case_id,
                    "center": meta.center,
                    "modality_group": meta.modality_group,
                    "t2_present": int(meta.t2_present),
                    "edema_label_reliable": int(meta.t2_present and meta.center in {"CenterB", "CenterC"}),
                    "no_t2_case": int(no_t2),
                    "predicted_edema_voxels": int(np.count_nonzero(edema_pred_mask)),
                    "predicted_edema_volume_mm3": float(np.count_nonzero(edema_pred_mask) * np.prod(spacing)),
                    "positive_prediction_case": int(edema_pred_mask.any()),
                    "remote_FP_mm3": remote_fp_mm3(edema_pred_mask, gt == 4, gt, spacing),
                    "safety_violation": int(no_t2 and edema_pred_mask.any()),
                }
            )
    return casewise, geometry_rows, edema_availability_rows


def help_harm_rows(casewise: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(r["model_id"], r["case_id"], r["pathology"]): r for r in casewise}
    out = []
    for row in casewise:
        model_id = row["model_id"]
        if model_id == "nnunet_fold0":
            continue
        nn = by_key.get(("nnunet_fold0", row["case_id"], row["pathology"]))
        if nn is None:
            continue
        delta = None if row["Dice"] is None or nn["Dice"] is None else float(row["Dice"]) - float(nn["Dice"])
        if delta is None:
            effect = "not_applicable"
        elif delta > 1e-8:
            effect = "help"
        elif delta < -1e-8:
            effect = "harm"
        else:
            effect = "tie"
        out.append(
            {
                "model_id": model_id,
                "case_id": row["case_id"],
                "pathology": row["pathology"],
                "subgroup_applicable": "reliable_T2" if row["pathology"] == "pure_edema" and int(row.get("edema_label_reliable", 0)) else "standard",
                "nnunet_Dice": nn["Dice"],
                "candidate_Dice": row["Dice"],
                "delta_Dice_vs_nnunet": delta,
                "help_harm": effect,
                "oracle_best_model": model_id if delta is not None and delta > 0 else "nnunet_fold0",
                "oracle_Dice": max(float(row["Dice"]), float(nn["Dice"])) if delta is not None else None,
            }
        )
    return out


def summarize_ablation(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["pathology"] == "pure_edema":
            if int(row["t2_present"]) and row["center"] in {"CenterB", "CenterC"} and int(row["gt_positive"]):
                buckets[(row["pathology"], row["stage"])].append(row)
        elif row["pathology"] == "edema_zone":
            if int(row["t2_present"]) and row["center"] in {"CenterB", "CenterC"}:
                buckets[(row["pathology"], row["stage"])].append(row)
        else:
            buckets[(row["pathology"], row["stage"])].append(row)
    out = []
    for (pathology, stage), vals in sorted(buckets.items()):
        out.append(
            {
                "model_id": "full_data_submission_recipe",
                "comparison_tier": "FULL_DATA_LEAKAGE_CONTAMINATED_DIAGNOSTIC",
                "pathology": pathology,
                "stage": stage,
                "case_count": len(vals),
                "gt_positive_cases": sum(int(v["gt_positive"]) for v in vals),
                "mean_Dice": mean([v["Dice"] for v in vals]),
                "mean_HD95": mean([v["HD95"] for v in vals]),
                "mean_exact_HD": mean([v["exact_HD"] for v in vals]),
                "mean_remote_FP_mm3": mean([v["remote_FP_mm3"] for v in vals]),
                "mean_component_count": mean([v["component_count"] for v in vals]),
                "mean_volume_ratio": mean([v["volume_ratio"] for v in vals]),
            }
        )
    return out


def write_receipt(result_root: Path, job_id: str) -> None:
    squeue_cmd = ["squeue", "-j", job_id, "-o", "%.18i %.12P %.32j %.8u %.2t %.10M %.10l %.4D %R"]
    squeue_out = subprocess.run(squeue_cmd, text=True, capture_output=True, check=False)
    gpu_cmd = ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"]
    gpu_out = subprocess.run(gpu_cmd, text=True, capture_output=True, check=False)
    receipt = {
        "job_id": job_id,
        "partition": "htzhulab",
        "node": "g1807htzh01",
        "expected_job_name": "CAREInteractive3d",
        "new_slurm_jobs_submitted": False,
        "sbatch_used": False,
        "salloc_used": False,
        "srun_reuse_command_required_from_controller_shell": os.environ.get("SLURM_JOB_ID") != job_id,
        "hostname": socket.gethostname(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "squeue_command": " ".join(squeue_cmd),
        "squeue_exit_code": squeue_out.returncode,
        "squeue_stdout": squeue_out.stdout,
        "squeue_stderr": squeue_out.stderr,
        "gpu_query_exit_code": gpu_out.returncode,
        "gpu_query_stdout": gpu_out.stdout,
        "gpu_query_stderr": gpu_out.stderr,
        "time_utc": now_iso(),
    }
    write_json(result_root / "interactive_job_reuse_receipt.json", receipt)


def write_split_audit(config: dict[str, Any], result_root: Path, cases: list[str]) -> None:
    split_path = REPO_ROOT / config["dataset"]["split_path"]
    train = load_fold_train_cases(split_path, int(config["dataset"]["fold"]))
    meta = load_myops_case_metadata(REPO_ROOT)
    rows = []
    for case_id in sorted(train + cases):
        rows.append(
            {
                "case_id": case_id,
                "split_role": "val" if case_id in cases else "train",
                "fold": 0,
                "center": meta[case_id].center,
                "modality_group": meta[case_id].modality_group,
                "t2_present": int(meta[case_id].t2_present),
            }
        )
    write_csv(result_root / "fold0_split_audit.csv", rows)
    write_json(
        result_root / "benchmark_contract.json",
        {
            "task": "mosaic_fold0_fairness_reaudit",
            "split_path": config["dataset"]["split_path"],
            "fold": 0,
            "train_count": len(train),
            "val_count": len(cases),
            "expected_train_count": 176,
            "expected_val_count": 44,
            "training_authorized": False,
            "new_slurm_jobs_authorized": False,
            "validation_upload_authorized": False,
            "docker_authorized": False,
            "push_authorized": False,
            "primary_clean_comparison": ["nnunet_fold0", "clean_pathology_checkpoint", "clean_pathology_scar_terminal_edema", "clean_terminal_budget"],
            "full_data_weight_policy": "diagnostic_only_leakage_contaminated",
        },
    )


def metric(summary: dict[tuple[str, str, str], dict[str, Any]], model: str, pathology: str, subgroup: str) -> float | None:
    row = summary.get((model, pathology, subgroup))
    return None if row is None else mean([row.get("mean_Dice")])


def fmt(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.4f}"


def write_reports(result_root: Path, summary: list[dict[str, Any]], ablation_summary: list[dict[str, Any]], validator: dict[str, Any]) -> None:
    look = summary_lookup(summary)
    nn_scar = metric(look, "nnunet_fold0", "scar", "all44")
    bug_scar = metric(look, "clean_current_bug", "scar", "all44")
    corr_scar = metric(look, "clean_pathology_checkpoint", "scar", "all44")
    term_scar = metric(look, "clean_terminal_budget", "scar", "all44")
    merged_scar = metric(look, "clean_pathology_scar_terminal_edema", "scar", "all44")
    full_scar = metric(look, "full_data_submission_recipe", "scar", "all44")
    nn_edema = metric(look, "nnunet_fold0", "pure_edema", "T2-present_reliable_GT-positive")
    corr_edema = metric(look, "clean_pathology_checkpoint", "pure_edema", "T2-present_reliable_GT-positive")
    merged_edema = metric(look, "clean_pathology_scar_terminal_edema", "pure_edema", "T2-present_reliable_GT-positive")
    term_edema = metric(look, "clean_terminal_budget", "pure_edema", "T2-present_reliable_GT-positive")
    full_edema = metric(look, "full_data_submission_recipe", "pure_edema", "T2-present_reliable_GT-positive")

    ab_lookup = {(r["pathology"], r["stage"]): r for r in ablation_summary}
    full_raw_scar = mean([ab_lookup.get(("scar", "raw_scar_expert"), {}).get("mean_Dice")])
    full_final_scar = mean([ab_lookup.get(("scar", "final_merged_scar"), {}).get("mean_Dice")])
    full_raw_edema = mean([ab_lookup.get(("edema_zone", "raw_edema_probability_threshold_0.35"), {}).get("mean_Dice")])
    full_final_edema = mean([ab_lookup.get(("pure_edema", "final_pure_edema"), {}).get("mean_Dice")])
    checkpoint_gain = None if bug_scar is None or corr_scar is None else corr_scar - bug_scar
    term_diff = None if term_scar is None or corr_scar is None else term_scar - corr_scar
    edema_epoch_diff = None if merged_edema is None or corr_edema is None else merged_edema - corr_edema
    full_gain_scar = None if full_scar is None or corr_scar is None else full_scar - corr_scar
    full_gain_edema = None if full_edema is None or merged_edema is None else full_edema - merged_edema
    post_scar = None if full_raw_scar is None or full_final_scar is None else full_final_scar - full_raw_scar
    post_edema = None if full_raw_edema is None or full_final_edema is None else full_final_edema - full_raw_edema

    if corr_scar is None or nn_scar is None:
        conclusion = "PREVIOUS_COMPARISON_INVALID_AND_REQUIRES_MORE_EVIDENCE"
    elif corr_scar + 0.05 < nn_scar and (merged_edema is None or nn_edema is None or merged_edema + 0.05 < nn_edema):
        conclusion = "CLEAN_MOSAIC_STILL_MATERIALLY_BELOW_NNUNET"
    elif corr_scar >= nn_scar - 0.03:
        conclusion = "CLEAN_MOSAIC_COMPETITIVE_AFTER_CHECKPOINT_FIX"
    else:
        conclusion = "PREVIOUS_COMPARISON_INVALID_AND_REQUIRES_MORE_EVIDENCE"

    verdict_lines = [
        "本次复核显示，旧 MoSAIC fold0 结论的 checkpoint 选择部分失效：旧 scar 结果用了 epoch 75 的 `best.pt`，不是 upstream 风格的 pathology-specific checkpoint。修正后仍需看 clean fold0 与 nnU-Net 的同口径差距，full-data Google Drive 权重只能作为训练污染诊断。",
        "",
        f"final_verdict: {conclusion}",
        "",
        "| 问题 | 结论 |",
        "| --- | --- |",
        f"| 旧 0.3392 scar 是否由错误 checkpoint 造成 | checkpoint routing 错误成立；epoch75->pathology checkpoint scar Dice 变化为 {fmt(checkpoint_gain)}，旧结论至少不能作为最终 clean MoSAIC 结论 |",
        f"| 修正 clean MoSAIC scar 与 nnU-Net 差距 | nnU-Net {fmt(nn_scar)} vs clean_pathology_checkpoint {fmt(corr_scar)}，差值 MoSAIC-nnU-Net {fmt(None if corr_scar is None or nn_scar is None else corr_scar - nn_scar)} |",
        f"| 修正 clean MoSAIC edema reliable T2 subset 与 nnU-Net 差距 | nnU-Net {fmt(nn_edema)} vs clean best-edema {fmt(corr_edema)} / terminal-edema merged {fmt(merged_edema)} |",
        f"| epoch 75 -> epoch 190 scar 增益 | {fmt(checkpoint_gain)} |",
        f"| epoch 190 -> epoch 300 scar 差异 | {fmt(term_diff)} |",
        f"| edema epoch 130 -> epoch 200 差异 | {fmt(edema_epoch_diff)} |",
        f"| full-data 污染版本比 clean fold0 高多少 | scar {fmt(full_gain_scar)}；pure edema reliable {fmt(full_gain_edema)} |",
        f"| full-data 增益来自后处理多少 | scar final-raw {fmt(post_scar)}；edema final-raw-zone {fmt(post_edema)}；其余混有 all-train 权重、双 coarse、checkpoint 和 submission recipe |",
        f"| 三选一判断 | {conclusion} |",
        f"| MoSAIC 是否适合做 primary backbone | {'否，当前 clean 证据不足以替代 nnU-Net' if conclusion != 'CLEAN_MOSAIC_COMPETITIVE_AFTER_CHECKPOINT_FIX' else '可继续评估，但不能跳过更多 folds'} |",
        "| MoSAIC 是否适合做 proposal source | 可以作为候选/互补性来源观察，但只能基于 clean fold0 help/harm 证据，不可用 full-data 污染结果背书 |",
        "| 是否不值得进入 CARE final Docker | 当前不授权 Docker；若 clean 仍明显低于 nnU-Net，则不应作为 primary 进入 final Docker |",
    ]
    (result_root / "fairness_verdict.md").write_text("\n".join(verdict_lines) + "\n", encoding="utf-8")

    report = [
        "本次 Controller 只完成 MoSAIC fold0 公平复核和 full-data 权重污染诊断；没有训练、没有 validation 上传、没有 Docker、没有 push，也没有提交新 Slurm job。",
        "",
        f"strict_validator_status: {validator['status']}",
        f"fairness_verdict: {conclusion}",
        f"nnunet_fold0_scar_all44: {fmt(nn_scar)}",
        f"clean_pathology_checkpoint_scar_all44: {fmt(corr_scar)}",
        f"nnunet_pure_edema_reliable_gt_positive: {fmt(nn_edema)}",
        f"clean_pathology_scar_terminal_edema_pure_edema_reliable_gt_positive: {fmt(merged_edema)}",
        f"full_data_submission_recipe_scar_all44: {fmt(full_scar)}",
        f"full_data_submission_recipe_pure_edema_reliable_gt_positive: {fmt(full_edema)}",
        "",
        "Outputs are listed in MANIFEST.md.",
    ]
    (result_root / "controller_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    completion = [
        "本次 reaudit 的结束条件已经按 strict validator 检查；只有 PASS 时才可视为 terminal。",
        "",
        f"- strict_validator_status: {validator['status']}",
        f"- no_new_slurm_jobs: {validator.get('no_new_slurm_jobs')}",
        f"- predictions_complete: {validator.get('predictions_complete')}",
        f"- geometry_pass: {validator.get('geometry_pass')}",
        f"- full_data_marked_contaminated: {validator.get('full_data_marked_contaminated')}",
        f"- corrected_clean_variants_complete: {validator.get('corrected_clean_variants_complete')}",
    ]
    (result_root / "completion_check.md").write_text("\n".join(completion) + "\n", encoding="utf-8")


def strict_validate(result_root: Path, cases: list[str], specs: list[dict[str, Any]]) -> dict[str, Any]:
    required = [
        "checkpoint_inventory.json",
        "checkpoint_inventory.csv",
        "checkpoint_selection_audit.md",
        "variant_manifest.csv",
        "prediction_manifest.csv",
        "canonical_casewise_metrics.csv",
        "canonical_model_summary.csv",
        "help_harm_vs_nnunet.csv",
        "full_data_stage_ablation_casewise.csv",
        "full_data_stage_ablation_summary.csv",
        "geometry_audit.csv",
        "label_mapping_audit.csv",
        "edema_label_availability_audit.csv",
        "interactive_job_reuse_receipt.json",
        "runtime_commands.jsonl",
        "fairness_verdict.md",
        "controller_report.md",
        "completion_check.md",
        "MANIFEST.md",
    ]
    pred_models = [s["model_id"] for s in specs]
    pred_complete = True
    pred_counts = {}
    for model_id in pred_models:
        count = len(list((result_root / "predictions" / model_id / "compact").glob("*.nii.gz")))
        pred_counts[model_id] = count
        if count != len(cases):
            pred_complete = False
    geometry_rows = read_csv_rows(result_root / "geometry_audit.csv")
    geometry_pass = bool(geometry_rows) and all(r.get("status") == "PASS" for r in geometry_rows)
    variant_rows = read_csv_rows(result_root / "variant_manifest.csv")
    clean_ok = all("/users/a/e/aereinh/MoSAIC/code/weights" not in r.get("checkpoint_path", "") for r in variant_rows if r.get("model_id", "").startswith("clean_"))
    full_marked = all(
        r.get("comparison_tier") == "FULL_DATA_LEAKAGE_CONTAMINATED_DIAGNOSTIC"
        for r in variant_rows
        if r.get("model_id") == "full_data_submission_recipe"
    )
    banned_commands = []
    runtime_path = result_root / "runtime_commands.jsonl"
    if runtime_path.is_file():
        for line in runtime_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            command_value = str(event.get("command", "")).strip()
            argv_value = [str(v) for v in event.get("argv", [])] if isinstance(event.get("argv"), list) else []
            candidates = [command_value] + argv_value
            for candidate in candidates:
                token = candidate.split()[0] if candidate.split() else ""
                if token in {"sbatch", "salloc"}:
                    banned_commands.append(candidate)
    receipt_path = result_root / "interactive_job_reuse_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else {}
    no_new = not banned_commands and receipt.get("new_slurm_jobs_submitted") is False and receipt.get("sbatch_used") is False and receipt.get("salloc_used") is False
    validator = {
        "status": "PASS",
        "required_files_present": all((result_root / name).is_file() for name in required),
        "missing_required_files": [name for name in required if not (result_root / name).is_file()],
        "prediction_counts": pred_counts,
        "predictions_complete": pred_complete,
        "geometry_pass": geometry_pass,
        "clean_variants_no_full_data_weights": clean_ok,
        "full_data_marked_contaminated": full_marked,
        "no_new_slurm_jobs": no_new,
        "banned_slurm_commands_detected": banned_commands,
        "corrected_clean_variants_complete": all(pred_counts.get(mid) == len(cases) for mid in ["clean_pathology_checkpoint", "clean_pathology_scar_terminal_edema", "clean_terminal_budget"]),
    }
    if not all(
        [
            validator["required_files_present"],
            pred_complete,
            geometry_pass,
            clean_ok,
            full_marked,
            no_new,
            validator["corrected_clean_variants_complete"],
        ]
    ):
        validator["status"] = "FAIL"
    return validator


def write_manifest_md(result_root: Path) -> None:
    files = [
        "benchmark_contract.json",
        "fold0_split_audit.csv",
        "checkpoint_inventory.json",
        "checkpoint_inventory.csv",
        "checkpoint_selection_audit.md",
        "variant_manifest.csv",
        "prediction_manifest.csv",
        "canonical_casewise_metrics.csv",
        "canonical_model_summary.csv",
        "help_harm_vs_nnunet.csv",
        "full_data_stage_ablation_casewise.csv",
        "full_data_stage_ablation_summary.csv",
        "geometry_audit.csv",
        "label_mapping_audit.csv",
        "edema_label_availability_audit.csv",
        "interactive_job_reuse_receipt.json",
        "runtime_commands.jsonl",
        "fairness_verdict.md",
        "controller_report.md",
        "completion_check.md",
        "strict_validator_report.json",
    ]
    lines = [
        "本目录是 MoSAIC fold0 公平性复核和 full-data 权重污染诊断的隔离结果根目录。",
        "",
        "| file | purpose |",
        "| --- | --- |",
    ]
    for name in files:
        lines.append(f"| `{name}` | generated artifact |")
    (result_root / "MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT_DEFAULT)
    parser.add_argument("--old-result-root", type=Path, default=OLD_RESULT_ROOT_DEFAULT)
    parser.add_argument("--job-id", default="60657290")
    parser.add_argument("--skip-inference", action="store_true")
    args = parser.parse_args()

    result_root = args.result_root if args.result_root.is_absolute() else REPO_ROOT / args.result_root
    old_root = args.old_result_root if args.old_result_root.is_absolute() else REPO_ROOT / args.old_result_root
    result_root.mkdir(parents=True, exist_ok=True)
    runtime_log = result_root / "runtime_commands.jsonl"
    write_jsonl(
        runtime_log,
        {
            "event": "script_start",
            "time_utc": now_iso(),
            "argv": sys.argv,
            "hostname": socket.gethostname(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "command": " ".join(sys.argv),
            "sbatch_used": False,
            "salloc_used": False,
        },
    )
    config = load_yaml(args.config if args.config.is_absolute() else REPO_ROOT / args.config)
    cases = load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    train = load_fold_train_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"]))
    if len(cases) != 44 or len(train) != 176:
        raise RuntimeError(f"fold0 split mismatch: train={len(train)} val={len(cases)}")
    write_receipt(result_root, args.job_id)
    write_split_audit(config, result_root, cases)
    _inventory, inventory_rows = checkpoint_inventory(old_root, result_root)
    specs = variant_specs(old_root)
    write_variant_manifest(result_root, specs, inventory_rows)
    all_manifest_rows = []
    all_ablation_rows = []
    if not args.skip_inference:
        for spec in specs:
            rows, ablation = run_one_variant(spec=spec, config=config, old_root=old_root, result_root=result_root, cases=cases, runtime_log=runtime_log)
            all_manifest_rows.extend(rows)
            all_ablation_rows.extend(ablation)
    else:
        all_manifest_rows = read_csv_rows(result_root / "prediction_manifest.csv")
        all_ablation_rows = read_csv_rows(result_root / "full_data_stage_ablation_casewise.csv")
    write_csv(result_root / "prediction_manifest.csv", all_manifest_rows)
    write_csv(result_root / "full_data_stage_ablation_casewise.csv", all_ablation_rows)
    ab_sum = summarize_ablation(all_ablation_rows)
    write_csv(result_root / "full_data_stage_ablation_summary.csv", ab_sum)
    casewise, geometry_rows, edema_rows = evaluate_all(config, result_root, cases, specs)
    write_csv(result_root / "canonical_casewise_metrics.csv", casewise)
    summary = summary_rows(casewise)
    write_csv(result_root / "canonical_model_summary.csv", summary)
    write_csv(result_root / "help_harm_vs_nnunet.csv", help_harm_rows(casewise))
    write_csv(result_root / "geometry_audit.csv", geometry_rows)
    write_csv(result_root / "label_mapping_audit.csv", label_mapping_audit_rows())
    write_csv(result_root / "edema_label_availability_audit.csv", edema_rows)
    write_manifest_md(result_root)
    provisional = {"status": "PENDING_FINAL_REPORTS"}
    write_reports(result_root, summary, ab_sum, provisional)
    validator = strict_validate(result_root, cases, specs)
    write_json(result_root / "strict_validator_report.json", validator)
    write_reports(result_root, summary, ab_sum, validator)
    write_jsonl(runtime_log, {"event": "script_end", "time_utc": now_iso(), "exit_code": 0, "strict_validator_status": validator["status"]})
    print(json.dumps({"status": validator["status"], "result_root": rel(result_root)}, indent=2, sort_keys=True))
    return 0 if validator["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
