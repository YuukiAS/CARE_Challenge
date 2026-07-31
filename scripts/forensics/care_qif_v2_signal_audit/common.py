#!/usr/bin/env python3
"""Shared utilities for the CARE-QIF v2 signal audit."""

from __future__ import annotations

import csv
import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import blosc2
import numpy as np
from scipy import ndimage

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_KEY = "20260731_care_qif_v2_signal_audit"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
RUNTIME_ROOT = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK_KEY
FEATURE_ROOT = RUNTIME_ROOT / "features"

PREPROCESSED_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
FULLRES_ROOT = PREPROCESSED_ROOT / "nnUNetPlans_3d_fullres"
SPLITS_PATH = PREPROCESSED_ROOT / "splits_final.json"
DATASET_JSON = PREPROCESSED_ROOT / "dataset.json"
PLANS_JSON = PREPROCESSED_ROOT / "nnUNetPlans.json"
STOCK_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)

SCAR_LABEL = 5
PURE_EDEMA_LABEL = 4
HEALTHY_MYO_LABEL = 1
LV_LABEL = 2
RV_LABEL = 3
MYO_UNION_LABELS = {1, 4, 5}
INJURY_LABELS = {4, 5}
SEED = 20260731


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(REPO_ROOT))
    except Exception:
        return str(p)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_image(case_id: str) -> np.ndarray:
    arr = np.asarray(blosc2.open(str(FULLRES_ROOT / f"{case_id}.b2nd"), mode="r")[:])
    if arr.ndim != 4 or arr.shape[0] != 3:
        raise ValueError(f"{case_id} image must be [3,Z,Y,X], got {arr.shape}")
    return arr.astype(np.float32, copy=False)


def load_seg(case_id: str) -> np.ndarray:
    arr = np.asarray(blosc2.open(str(FULLRES_ROOT / f"{case_id}_seg.b2nd"), mode="r")[:]).squeeze()
    if arr.ndim == 2:
        arr = arr[None]
    if arr.ndim != 3:
        raise ValueError(f"{case_id} segmentation must be 3D after squeeze, got {arr.shape}")
    return arr.astype(np.int16, copy=False)


def load_case_properties(case_id: str) -> dict[str, Any]:
    with (FULLRES_ROOT / f"{case_id}.pkl").open("rb") as f:
        return pickle.load(f)


def spacing_zyx(case_id: str) -> tuple[float, float, float]:
    props = load_case_properties(case_id)
    vals = tuple(float(v) for v in props.get("spacing", (1.0, 1.0, 1.0)))
    return vals if len(vals) == 3 else (1.0, 1.0, 1.0)


def voxel_volume_mm3(spacing: Iterable[float]) -> float:
    out = 1.0
    for value in spacing:
        out *= float(value)
    return float(out)


def load_case_metadata() -> dict[str, dict[str, Any]]:
    from src.care_myocardium.data.case_metadata import load_myops_case_metadata

    meta = load_myops_case_metadata(REPO_ROOT)
    return {
        case_id: {
            "case_id": row.case_id,
            "center": row.center,
            "modality_group": row.modality_group,
            "lge_present": row.lge_present,
            "t2_present": row.t2_present,
            "c0_present": row.c0_present,
        }
        for case_id, row in meta.items()
    }


def complete_bc_cases() -> list[dict[str, Any]]:
    meta = load_case_metadata()
    rows = [
        row
        for row in meta.values()
        if row["center"] in {"CenterB", "CenterC"}
        and bool(row["lge_present"])
        and bool(row["t2_present"])
        and bool(row["c0_present"])
    ]
    return sorted(rows, key=lambda r: r["case_id"])


def all_dataset_cases() -> list[str]:
    return sorted(p.name.replace("_seg.b2nd", "") for p in FULLRES_ROOT.glob("*_seg.b2nd"))


def load_splits() -> list[dict[str, list[str]]]:
    return read_json(SPLITS_PATH)


def oof_fold_for_case(case_id: str) -> int:
    hits = [idx for idx, split in enumerate(load_splits()) if case_id in set(split["val"])]
    if len(hits) != 1:
        raise ValueError(f"{case_id} has {len(hits)} OOF validation folds: {hits}")
    return int(hits[0])


def checkpoint_path_for_fold(fold: int) -> Path:
    return STOCK_ROOT / f"fold_{int(fold)}" / "checkpoint_final.pth"


def case_membership_proof(case_id: str, fold: int) -> dict[str, Any]:
    splits = load_splits()
    split = splits[int(fold)]
    in_val = case_id in set(split["val"])
    in_train = case_id in set(split["train"])
    return {
        "case_id": case_id,
        "oof_fold": int(fold),
        "in_oof_validation": bool(in_val),
        "in_oof_training": bool(in_train),
        "status": "PASS" if in_val and not in_train else "FAIL",
        "proof_sha256": sha256_text(json.dumps({"fold": fold, "train": split["train"], "val": split["val"]}, sort_keys=True)),
    }


def connected_components_26(mask: np.ndarray) -> tuple[np.ndarray, int]:
    labeled, count = ndimage.label(mask.astype(bool), structure=ndimage.generate_binary_structure(3, 3))
    return labeled.astype(np.int32, copy=False), int(count)


def component_rows(case_id: str) -> list[dict[str, Any]]:
    seg = load_seg(case_id)
    spacing = spacing_zyx(case_id)
    voxel_vol = voxel_volume_mm3(spacing)
    scar = seg == SCAR_LABEL
    lv = seg == LV_LABEL
    myo = np.isin(seg, list(MYO_UNION_LABELS))
    lab, count = connected_components_26(scar)
    if lv.any():
        dist_lv = ndimage.distance_transform_edt(~lv, sampling=spacing)
    else:
        dist_lv = np.full(seg.shape, np.inf, dtype=np.float32)
    if myo.any():
        dist_myo = ndimage.distance_transform_edt(~myo, sampling=spacing)
    else:
        dist_myo = np.full(seg.shape, np.inf, dtype=np.float32)
    rows: list[dict[str, Any]] = []
    if count == 0:
        rows.append(
            {
                "case_id": case_id,
                "component_id": 0,
                "component_count": 0,
                "voxels": 0,
                "volume_mm3": 0.0,
                "small_lesion": False,
                "centroid_z": "",
                "centroid_y": "",
                "centroid_x": "",
                "min_blood_pool_distance_mm": "",
                "min_myocardium_boundary_distance_mm": "",
            }
        )
        return rows
    for idx in range(1, count + 1):
        comp = lab == idx
        coords = np.argwhere(comp)
        volume = float(comp.sum()) * voxel_vol
        rows.append(
            {
                "case_id": case_id,
                "component_id": idx,
                "component_count": count,
                "voxels": int(comp.sum()),
                "volume_mm3": volume,
                "small_lesion": bool(volume < 1000.0),
                "centroid_z": float(coords[:, 0].mean()),
                "centroid_y": float(coords[:, 1].mean()),
                "centroid_x": float(coords[:, 2].mean()),
                "min_blood_pool_distance_mm": float(dist_lv[comp].min()) if comp.any() else "",
                "min_myocardium_boundary_distance_mm": float(dist_myo[comp].min()) if comp.any() else "",
            }
        )
    return rows


def deterministic_center_selection(cases: list[str], case_stats: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    keyed = []
    for case_id in cases:
        stat = case_stats[case_id]
        burden_bin = int(min(4, float(stat.get("scar_voxels", 0)) // 1500))
        comp_bin = int(min(4, float(stat.get("scar_component_count", 0))))
        key = sha256_text(f"qif-select:{SEED}:{burden_bin}:{comp_bin}:{case_id}")
        keyed.append((burden_bin, comp_bin, key, case_id))
    keyed.sort()
    n_sel = max(1, int(round(len(cases) * 0.20)))
    selection = sorted(case_id for *_rest, case_id in keyed[:n_sel])
    train = sorted(case_id for case_id in cases if case_id not in set(selection))
    return train, selection


def feature_cache_path(case_id: str) -> Path:
    return FEATURE_ROOT / f"{case_id}.npz"


def finite_mean(vals: Iterable[Any]) -> float | None:
    clean = []
    for val in vals:
        try:
            f = float(val)
        except Exception:
            continue
        if np.isfinite(f):
            clean.append(f)
    if not clean:
        return None
    return float(np.mean(clean))
