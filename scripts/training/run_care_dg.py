#!/usr/bin/env python3
"""CARE-DG training entrypoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import SimpleITK as sitk
import torch
from torch.amp import GradScaler, autocast

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.models.care_dg import build_care_dg
from src.care_myocardium.training.care_dg_trainer import care_dg_loss, load_care_dg_checkpoint, save_care_dg_checkpoint

TASK_KEY = "20260727_care_dg_dual_pathology_validation"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
RAW_TRAIN = REPO_ROOT / "data/CARE_Challenge/MyoPS_train"
LABEL_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
ANCHOR_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
SPLIT_PATH = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CONFIG_PATH = REPO_ROOT / "configs/care_dg/care_dg_v1.yaml"
SCAR = 5
EDEMA = 4
PATCH_SHAPE = (8, 128, 128)
ALLOWED_W0_CONTRACT_STATUSES = {
    "W1_IMPLEMENTATION_AND_REAL_CASE_GATES_PASS_FORMAL_TRAINING_NOT_STARTED",
    "GATE_A_REPAIRED_IMPLEMENTATION_PASS",
}
PROTECTED_RUNTIME_LABELS = {"formal", "repaired_formal"}
SAMPLER_PATTERN = ["error_fn", "error_fp", "error_fn", "error_fp", "pathology", "pathology", "random", "random"]
INNER_EVAL_MODES = ("scar_fn", "scar_fp", "edema_zone_fn", "edema_zone_fp", "pathology", "background")
REPRESENTATION_MODULES = ("lge_stem", "t2_stem", "c0_stem", "anchor_context", "encoder")
PATHOLOGY_MODULES = ("scar_decoder", "edema_decoder")
STAGE_A_REPRESENTATION_LR = 3e-4
STAGE_A_PATHOLOGY_LR = 3e-4
STAGE_B_REPRESENTATION_LR = 2e-5
STAGE_B_PATHOLOGY_LR = 1e-4
WEIGHT_DECAY = 1e-4
GRAD_CLIP_NORM = 1.0
AMP_DTYPE = "bfloat16"
DISTANCE_CLIP_MM = (-64.0, 128.0)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: set[str] = set(); fieldnames = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key); fieldnames.append(key)
        fieldnames = fieldnames or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def append_csv(path: Path, row: dict[str, Any], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def load_splits() -> list[dict[str, Any]]:
    return json.loads(SPLIT_PATH.read_text(encoding="utf-8"))["folds"]


def modality_path(case_id: str, suffix: str) -> Path | None:
    found = list(RAW_TRAIN.glob(f"*/{case_id}/{case_id}_{suffix}.nii.gz"))
    return found[0] if found else None


def read_resampled(path: Path | None, ref: sitk.Image) -> np.ndarray:
    if path is None:
        return np.zeros(tuple(reversed(ref.GetSize())), dtype=np.float32)
    img = sitk.ReadImage(str(path), sitk.sitkFloat32)
    if img.GetSize() != ref.GetSize() or img.GetSpacing() != ref.GetSpacing() or img.GetOrigin() != ref.GetOrigin() or img.GetDirection() != ref.GetDirection():
        img = sitk.Resample(img, ref, sitk.Transform(), sitk.sitkLinear, 0.0, sitk.sitkFloat32)
    arr = sitk.GetArrayFromImage(img).astype(np.float32)
    return (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)


def support_maps(anchor_mask: np.ndarray, ref: sitk.Image) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    tissue = np.isin(anchor_mask, [1, 4, 5]).astype(np.uint8)
    img = sitk.GetImageFromArray(tissue)
    img.CopyInformation(ref)
    dist_img = sitk.SignedMaurerDistanceMap(img, insideIsPositive=False, squaredDistance=False, useImageSpacing=True)
    dist = sitk.GetArrayFromImage(dist_img).astype(np.float32)
    dist = np.nan_to_num(dist, nan=DISTANCE_CLIP_MM[1], posinf=DISTANCE_CLIP_MM[1], neginf=DISTANCE_CLIP_MM[0])
    dist = np.clip(dist, DISTANCE_CLIP_MM[0], DISTANCE_CLIP_MM[1]).astype(np.float32)
    myocardium_support = (1.0 / (1.0 + np.exp(np.clip((dist - 6.0) / 2.0, -60.0, 60.0)))).astype(np.float32)
    edema_support = (1.0 / (1.0 + np.exp(np.clip((dist - 10.0) / 2.0, -60.0, 60.0)))).astype(np.float32)
    return myocardium_support[None], edema_support[None], dist[None]


class CaseCache:
    def __init__(self, max_cases: int = 48) -> None:
        self.max_cases = int(max_cases)
        self.cache: OrderedDict[str, dict[str, np.ndarray]] = OrderedDict()

    def get(self, case_id: str, fold: int, availability: tuple[float, float, float]) -> dict[str, np.ndarray]:
        if case_id in self.cache:
            self.cache.move_to_end(case_id)
            return self.cache[case_id]
        ref = sitk.ReadImage(str(LABEL_ROOT / f"{case_id}.nii.gz"))
        label = sitk.GetArrayFromImage(ref).astype(np.int64)
        images = np.stack([read_resampled(modality_path(case_id, suffix), ref) for suffix in ("LGE", "T2", "C0")], axis=0)
        anchor_npz = ANCHOR_ROOT / f"fold_{fold}/validation/{case_id}.npz"
        with np.load(anchor_npz) as data:
            probs = data["probabilities"].astype(np.float32)[:6]
        if probs.shape[-3:] != label.shape:
            raise ValueError(f"probability/label shape mismatch for {case_id}: {probs.shape[-3:]} vs {label.shape}")
        if float(probs.min()) < 0.0 or float(probs.max()) > 1.0:
            raise ValueError(f"anchor probability outside [0,1] for {case_id}")
        anchor = np.log(np.clip(probs, 1e-5, 1.0)).astype(np.float32)
        anchor_mask = probs.argmax(axis=0).astype(np.int64)
        uncertainty = (1.0 - probs.max(axis=0, keepdims=True)).astype(np.float32)
        myocardium_support, edema_support, distance_to_myocardium = support_maps(anchor_mask, ref)
        record = {
            "images": images,
            "labels": label,
            "anchor_logits": anchor,
            "anchor_mask": anchor_mask,
            "availability": np.asarray(availability, dtype=np.float32),
            "uncertainty": uncertainty,
            "myocardium_support": myocardium_support,
            "edema_support": edema_support,
            "distance_to_myocardium": distance_to_myocardium,
            "anchor_value_kind": "log_probabilities",
            "anchor_probability_path": str(anchor_npz),
        }
        self.cache[case_id] = record
        if len(self.cache) > self.max_cases:
            self.cache.popitem(last=False)
        return record


def crop_pad(arr: np.ndarray, center: tuple[int, int, int], shape: tuple[int, int, int], fill: float = 0.0) -> np.ndarray:
    spatial = arr.shape[-3:]
    starts = [int(c - s // 2) for c, s in zip(center, shape)]
    slices_src = []
    slices_dst = []
    for start, size, dim in zip(starts, shape, spatial):
        src0 = max(0, start); src1 = min(dim, start + size)
        dst0 = max(0, -start); dst1 = dst0 + max(0, src1 - src0)
        slices_src.append(slice(src0, src1)); slices_dst.append(slice(dst0, dst1))
    out_shape = arr.shape[:-3] + tuple(shape)
    out = np.full(out_shape, fill, dtype=arr.dtype)
    out[(..., *slices_dst)] = arr[(..., *slices_src)]
    return out


def choose_center(record: dict[str, np.ndarray], rng: random.Random, mode: str, t2_present: bool) -> tuple[int, int, int]:
    labels = record["labels"]
    anchor = record["anchor_mask"]
    scar_fn = (labels == SCAR) & (anchor != SCAR)
    scar_fp = (labels != SCAR) & (anchor == SCAR)
    zone_gt = (labels == SCAR) | (labels == EDEMA)
    zone_pred = (anchor == SCAR) | (anchor == EDEMA)
    edema_fn = (zone_gt & ~zone_pred) if t2_present else np.zeros_like(labels, dtype=bool)
    edema_fp = (~zone_gt & zone_pred) if t2_present else np.zeros_like(labels, dtype=bool)
    pathology = (labels == SCAR) | ((labels == EDEMA) if t2_present else False)
    if mode == "error_fn":
        mask = scar_fn | edema_fn
    elif mode == "error_fp":
        mask = scar_fp | edema_fp
    elif mode == "pathology":
        mask = pathology
    else:
        mask = np.zeros_like(labels, dtype=bool)
    coords = np.argwhere(mask)
    if coords.size:
        z, y, x = coords[rng.randrange(len(coords))]
    else:
        z = rng.randrange(labels.shape[0]); y = rng.randrange(labels.shape[1]); x = rng.randrange(labels.shape[2])
    jitter = [rng.randint(-16, 16), rng.randint(-32, 32), rng.randint(-32, 32)]
    return (
        max(0, min(labels.shape[0] - 1, int(z) + jitter[0])),
        max(0, min(labels.shape[1] - 1, int(y) + jitter[1])),
        max(0, min(labels.shape[2] - 1, int(x) + jitter[2])),
    )





def stable_json_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def case_target_masks(record: dict[str, np.ndarray], t2_present: bool) -> dict[str, np.ndarray]:
    labels = record["labels"]
    anchor = record["anchor_mask"]
    scar_fn = (labels == SCAR) & (anchor != SCAR)
    scar_fp = (labels != SCAR) & (anchor == SCAR)
    zone_gt = (labels == SCAR) | (labels == EDEMA)
    zone_pred = (anchor == SCAR) | (anchor == EDEMA)
    edema_fn = (zone_gt & ~zone_pred) if t2_present else np.zeros_like(labels, dtype=bool)
    edema_fp = (~zone_gt & zone_pred) if t2_present else np.zeros_like(labels, dtype=bool)
    pathology = (labels == SCAR) | ((labels == EDEMA) if t2_present else np.zeros_like(labels, dtype=bool))
    background = (labels < EDEMA) & (anchor < EDEMA)
    return {
        "scar_fn": scar_fn,
        "scar_fp": scar_fp,
        "edema_zone_fn": edema_fn,
        "edema_zone_fp": edema_fp,
        "error_fn": scar_fn | edema_fn,
        "error_fp": scar_fp | edema_fp,
        "pathology": pathology,
        "random": np.ones_like(labels, dtype=bool),
        "background": background,
    }


def actionable_target_mask(record: dict[str, np.ndarray], t2_present: bool, mode: str) -> np.ndarray:
    masks = case_target_masks(record, t2_present)
    labels = record["labels"]
    scar_support = record.get("myocardium_support", np.ones((1, *labels.shape), dtype=np.float32))[0] > 0.1
    edema_support = record.get("edema_support", np.ones((1, *labels.shape), dtype=np.float32))[0] > 0.1
    if mode == "error_fn":
        return ((masks["scar_fn"] & scar_support) | (masks["edema_zone_fn"] & edema_support)).astype(bool)
    if mode == "error_fp":
        return ((masks["scar_fp"] & scar_support) | (masks["edema_zone_fp"] & edema_support)).astype(bool)
    if mode == "pathology":
        scar_pathology = (labels == SCAR) & scar_support
        edema_pathology = (labels == EDEMA) & edema_support if t2_present else np.zeros_like(labels, dtype=bool)
        return (scar_pathology | edema_pathology).astype(bool)
    if mode == "random":
        return masks["random"]
    return masks.get(mode, np.zeros_like(labels, dtype=bool))


def support_actionability_summary(record: dict[str, np.ndarray], t2_present: bool) -> dict[str, Any]:
    raw = case_target_masks(record, t2_present)
    actionable = {mode: actionable_target_mask(record, t2_present, mode) for mode in ("error_fn", "error_fp", "pathology", "random")}
    labels = record["labels"]
    scar_support = record.get("myocardium_support", np.ones((1, *labels.shape), dtype=np.float32))[0]
    edema_support = record.get("edema_support", np.ones((1, *labels.shape), dtype=np.float32))[0]
    return {
        "anchor_tissue_voxels_1_4_5": int(np.count_nonzero(np.isin(record["anchor_mask"], [1, 4, 5]))),
        "max_distance_to_myocardium": float(np.max(record.get("distance_to_myocardium", np.zeros((1, *labels.shape), dtype=np.float32)))),
        "scar_support_gt_0_1_voxels": int(np.count_nonzero(scar_support > 0.1)),
        "edema_support_gt_0_1_voxels": int(np.count_nonzero(edema_support > 0.1)),
        "raw_target_counts": {mode: int(np.count_nonzero(raw[mode])) for mode in ("error_fn", "error_fp", "pathology", "random")},
        "actionable_target_counts": {mode: int(np.count_nonzero(actionable[mode])) for mode in actionable},
    }


def deterministic_center(mask: np.ndarray, case_id: str, mode: str, salt: str) -> tuple[int, int, int] | None:
    coords = np.argwhere(mask)
    if not coords.size:
        return None
    idx = int(hashlib.sha256(f"{case_id}:{mode}:{salt}:r2".encode("utf-8")).hexdigest()[:16], 16) % len(coords)
    return tuple(int(v) for v in coords[idx])


def target_voxels_in_patch(record: dict[str, np.ndarray], center: tuple[int, int, int], mode: str, t2_present: bool) -> int:
    mask = actionable_target_mask(record, t2_present, mode)
    if mask is None:
        raise ValueError(f"unknown sampler target mode: {mode}")
    return int(crop_pad(mask.astype(np.uint8)[None], center, PATCH_SHAPE, fill=0)[0].sum())


def choose_effective_center(
    record: dict[str, np.ndarray],
    rng: random.Random,
    *,
    case_id: str,
    mode: str,
    t2_present: bool,
) -> tuple[tuple[int, int, int], int, str]:
    labels = record["labels"]
    if mode == "random":
        center = (rng.randrange(labels.shape[0]), rng.randrange(labels.shape[1]), rng.randrange(labels.shape[2]))
        return center, 0, ""
    target = actionable_target_mask(record, t2_present, mode)
    if target is None or not np.any(target):
        raise ValueError(f"CARE_DG_EFFECTIVE_SAMPLER_EMPTY_TARGET:{case_id}:{mode}")
    coords = np.argwhere(target)
    z, y, x = coords[rng.randrange(len(coords))]
    original = (int(z), int(y), int(x))
    jitter = (rng.randint(-16, 16), rng.randint(-32, 32), rng.randint(-32, 32))
    jittered = (
        max(0, min(labels.shape[0] - 1, original[0] + jitter[0])),
        max(0, min(labels.shape[1] - 1, original[1] + jitter[1])),
        max(0, min(labels.shape[2] - 1, original[2] + jitter[2])),
    )
    count = target_voxels_in_patch(record, jittered, mode, t2_present)
    if count > 0:
        return jittered, count, ""
    count = target_voxels_in_patch(record, original, mode, t2_present)
    if count <= 0:
        raise ValueError(f"CARE_DG_EFFECTIVE_SAMPLER_TARGET_LEFT_PATCH:{case_id}:{mode}")
    return original, count, "jitter_recentered_to_original_target"


def sha256_case_ids(case_ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(case_ids)).encode("utf-8")).hexdigest()


def validate_inner_split_contract(split_payload: dict[str, Any]) -> None:
    actual_train = set(split_payload.get("actual_train_cases") or [])
    inner_select = set(split_payload.get("inner_select_cases") or [])
    complete_actual = set(split_payload.get("complete_actual_train_cases") or [])
    complete_inner = set(split_payload.get("complete_inner_select_cases") or [])
    if actual_train & inner_select:
        raise ValueError("CARE_DG_INNER_SELECT_LEAKS_INTO_STAGE_A_TRAINING")
    if complete_actual & inner_select:
        raise ValueError("CARE_DG_INNER_SELECT_LEAKS_INTO_STAGE_B_TRAINING")
    if complete_inner and complete_inner != inner_select:
        raise ValueError("CARE_DG_INNER_OBJECTIVE_NOT_FIXED_COMPLETE_TRIMODAL_SUBSET")
    if split_payload.get("outer_val_used") is not False:
        raise ValueError("CARE_DG_OUTER_VAL_USED_FOR_INNER_SELECTION")


def deterministic_inner_split(outer_train: list[str], fold: int, metadata: Any) -> dict[str, Any]:
    ranked = sorted(outer_train, key=lambda c: hashlib.sha256(f"{fold}:{c}:inner:r1".encode()).hexdigest())
    complete = [c for c in ranked if metadata[c].modality_group == "C0+LGE+T2"]
    target_complete = max(8, len(complete) // 5)
    if len(complete) >= target_complete:
        inner_select = sorted(complete[:target_complete])
        policy = "complete_trimodal_train_side_inner_split"
    else:
        by_group: dict[str, list[str]] = {}
        for case_id in ranked:
            by_group.setdefault(str(metadata[case_id].modality_group), []).append(case_id)
        target = max(8, len(ranked) // 5)
        selected: list[str] = []
        while len(selected) < target and any(by_group.values()):
            for group in sorted(by_group):
                if by_group[group] and len(selected) < target:
                    selected.append(by_group[group].pop(0))
        inner_select = sorted(selected)
        policy = "stratified_modality_group_train_side_inner_split_complete_insufficient"
    actual_train = sorted(c for c in outer_train if c not in set(inner_select))
    complete_actual_train = sorted(c for c in actual_train if metadata[c].modality_group == "C0+LGE+T2")
    complete_inner_select = sorted(c for c in inner_select if metadata[c].modality_group == "C0+LGE+T2")
    payload = {
        "fold": fold,
        "policy": policy,
        "outer_train_cases": sorted(outer_train),
        "actual_train_cases": actual_train,
        "inner_select_cases": inner_select,
        "complete_actual_train_cases": complete_actual_train,
        "complete_inner_select_cases": complete_inner_select,
        "counts": {
            "outer_train": len(outer_train),
            "actual_train": len(actual_train),
            "inner_select": len(inner_select),
            "complete_actual_train": len(complete_actual_train),
            "complete_inner_select": len(complete_inner_select),
        },
        "sha256": {
            "outer_train": sha256_case_ids(outer_train),
            "actual_train": sha256_case_ids(actual_train),
            "inner_select": sha256_case_ids(inner_select),
            "complete_actual_train": sha256_case_ids(complete_actual_train),
            "complete_inner_select": sha256_case_ids(complete_inner_select),
        },
        "fixed_inner_objective": "complete_inner_select_binary_care_dg_loss_stage_A_mode",
        "outer_val_used": False,
        "margin_cap_population": "actual_train_cases_only",
    }
    validate_inner_split_contract(payload)
    return payload


def inner_split(cases: list[str], fold: int) -> tuple[list[str], list[str]]:
    ranked = sorted(cases, key=lambda c: hashlib.sha256(f"{fold}:{c}:inner".encode()).hexdigest())
    n_val = max(8, len(ranked) // 5)
    select = sorted(ranked[:n_val])
    train = sorted(ranked[n_val:])
    return train, select


def sampler_modes(batch_size: int) -> list[str]:
    return [SAMPLER_PATTERN[i % len(SAMPLER_PATTERN)] for i in range(batch_size)]


def build_sampler_index(case_ids: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, *, stage: str) -> dict[str, Any]:
    active_cases: list[str] = []
    weights: dict[str, float] = {}
    eligible: dict[str, list[str]] = {"error_fn": [], "error_fp": [], "pathology": [], "random": []}
    target_counts: dict[str, dict[str, int]] = {}
    support_actionability: dict[str, dict[str, Any]] = {}
    excluded_unactionable: dict[str, list[str]] = {"error_fn": [], "error_fp": [], "pathology": []}
    for case_id in sorted(case_ids):
        meta = metadata[case_id]
        if stage == "B" and meta.modality_group != "C0+LGE+T2":
            continue
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        summary = support_actionability_summary(rec, bool(meta.t2_present))
        support_actionability[case_id] = summary
        active_cases.append(case_id)
        weights[case_id] = 4.0 if meta.modality_group == "C0+LGE+T2" else 1.0
        target_counts[case_id] = dict(summary["actionable_target_counts"])
        for mode in eligible:
            if mode == "random" or target_counts[case_id][mode] > 0:
                eligible[mode].append(case_id)
            elif int(summary["raw_target_counts"].get(mode, 0)) > 0 and mode in excluded_unactionable:
                excluded_unactionable[mode].append(case_id)
    if not active_cases:
        raise ValueError(f"no active cases for stage {stage}")
    empty = [mode for mode, pool in eligible.items() if not pool]
    if empty:
        raise ValueError(f"CARE_DG_EFFECTIVE_SAMPLER_EMPTY_ELIGIBLE_POOL:{stage}:{','.join(empty)}")
    payload = {
        "stage": stage,
        "case_ids": active_cases,
        "case_ids_sha256": sha256_case_ids(active_cases),
        "eligible_counts": {mode: len(pool) for mode, pool in eligible.items()},
        "target_count_totals": {mode: sum(target_counts[c][mode] for c in active_cases) for mode in eligible},
        "support_actionability": {
            "empty_anchor_tissue_cases": [case_id for case_id, row in support_actionability.items() if int(row["anchor_tissue_voxels_1_4_5"]) == 0],
            "tiny_anchor_tissue_lt500_cases": {case_id: int(row["anchor_tissue_voxels_1_4_5"]) for case_id, row in support_actionability.items() if 0 < int(row["anchor_tissue_voxels_1_4_5"]) < 500},
            "excluded_unactionable_cases": excluded_unactionable,
            "distance_clip_mm": list(DISTANCE_CLIP_MM),
        },
    }
    payload["sampler_index_sha256"] = stable_json_sha256(payload)
    return {**payload, "weights": weights, "eligible": eligible, "target_counts_by_case": target_counts}


def _batch_from_centers(samples: list[dict[str, Any]], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache) -> dict[str, Any]:
    images = []; labels = []; anchors = []; availability = []; t2 = []
    uncertainty = []; myocardium_support = []; edema_support = []; distance = []
    for sample in samples:
        case_id = str(sample["case_id"])
        center = tuple(int(v) for v in sample["center_zyx"])
        meta = metadata[case_id]
        record = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        images.append(crop_pad(record["images"], center, PATCH_SHAPE, fill=0.0))
        labels.append(crop_pad(record["labels"][None], center, PATCH_SHAPE, fill=0)[0])
        anchors.append(crop_pad(record["anchor_logits"], center, PATCH_SHAPE, fill=-12.0))
        uncertainty.append(crop_pad(record["uncertainty"], center, PATCH_SHAPE, fill=1.0))
        myocardium_support.append(crop_pad(record["myocardium_support"], center, PATCH_SHAPE, fill=0.0))
        edema_support.append(crop_pad(record["edema_support"], center, PATCH_SHAPE, fill=0.0))
        distance.append(crop_pad(record["distance_to_myocardium"], center, PATCH_SHAPE, fill=99.0))
        availability.append(record["availability"])
        t2.append(1.0 if meta.t2_present else 0.0)
    return {
        "images": torch.from_numpy(np.stack(images)).float(),
        "labels": torch.from_numpy(np.stack(labels)).long(),
        "anchor_logits": torch.from_numpy(np.stack(anchors)).float(),
        "availability": torch.from_numpy(np.stack(availability)).float(),
        "t2_present": torch.tensor(t2, dtype=torch.float32),
        "uncertainty": torch.from_numpy(np.stack(uncertainty)).float(),
        "myocardium_support": torch.from_numpy(np.stack(myocardium_support)).float(),
        "edema_support": torch.from_numpy(np.stack(edema_support)).float(),
        "distance_to_myocardium": torch.from_numpy(np.stack(distance)).float(),
        "anchor_value_kind": "log_probabilities",
        "sample_modes": [sample.get("requested_mode", sample.get("mode", "fixed")) for sample in samples],
        "effective_modes": [sample.get("effective_mode", sample.get("mode", "fixed")) for sample in samples],
        "case_trace": [str(sample["case_id"]) for sample in samples],
        "sample_accounting": samples,
    }


def build_batch(
    case_ids: list[str],
    case_to_fold: dict[str, int],
    metadata: Any,
    cache: CaseCache,
    rng: random.Random,
    *,
    stage: str,
    batch_size: int,
    sampler_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    index = sampler_index or build_sampler_index(case_ids, case_to_fold, metadata, cache, stage=stage)
    samples: list[dict[str, Any]] = []
    for requested_mode in sampler_modes(batch_size):
        pool = list(index["eligible"][requested_mode])
        if not pool:
            raise ValueError(f"CARE_DG_EFFECTIVE_SAMPLER_EMPTY_ELIGIBLE_POOL:{stage}:{requested_mode}")
        pool_weights = [float(index["weights"][case_id]) for case_id in pool]
        case_id = rng.choices(pool, weights=pool_weights, k=1)[0]
        meta = metadata[case_id]
        record = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        center, target_count, fallback_reason = choose_effective_center(record, rng, case_id=case_id, mode=requested_mode, t2_present=bool(meta.t2_present))
        effective_mode = requested_mode if requested_mode == "random" or target_count > 0 else "random"
        if requested_mode != "random" and effective_mode != requested_mode:
            raise ValueError(f"CARE_DG_EFFECTIVE_SAMPLER_SILENT_FALLBACK:{case_id}:{requested_mode}")
        samples.append({
            "requested_mode": requested_mode,
            "effective_mode": effective_mode,
            "case_id": case_id,
            "center_zyx": list(center),
            "target_voxel_count_in_patch": int(target_count),
            "fallback_reason": fallback_reason,
        })
    return _batch_from_centers(samples, case_to_fold, metadata, cache)

def move_tensors(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {k: (v.to(device, non_blocking=True) if torch.is_tensor(v) else v) for k, v in batch.items()}


def margin_caps_for_cases(case_ids: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache) -> dict[str, Any]:
    scar_values: list[float] = []
    edema_values: list[float] = []
    for case_id in case_ids:
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        labels = rec["labels"]
        anchor_mask = rec["anchor_mask"]
        anchor = rec["anchor_logits"]
        scar_margin = anchor[SCAR] - np.max(np.delete(anchor, SCAR, axis=0), axis=0)
        scar_error = ((labels == SCAR) != (anchor_mask == SCAR))
        scar_values.extend(np.abs(scar_margin[scar_error]).astype(float).tolist())
        if meta.t2_present:
            zone_gt = (labels == SCAR) | (labels == EDEMA)
            zone_pred = (anchor_mask == SCAR) | (anchor_mask == EDEMA)
            zone_margin = np.maximum(anchor[SCAR], anchor[EDEMA]) - np.max(anchor[list(range(4))], axis=0)
            edema_error = zone_gt != zone_pred
            edema_values.extend(np.abs(zone_margin[edema_error]).astype(float).tolist())
    def bound(values: list[float]) -> dict[str, float | int | str]:
        if values:
            q95 = float(np.quantile(np.asarray(values, dtype=np.float32), 0.95))
            cap = float(np.clip(q95 + 1.0, 2.0, 8.0))
            return {"status": "PASS", "error_voxels": len(values), "q95_abs_anchor_margin": q95, "cap": cap}
        return {"status": "NO_ERROR_VOXELS_FALLBACK_MIN_CAP", "error_voxels": 0, "q95_abs_anchor_margin": 1.0, "cap": 2.0}
    return {"scar": bound(scar_values), "edema_zone": bound(edema_values), "fit_population": "actual_train_cases_only", "case_count": len(case_ids), "case_ids_sha256": sha256_case_ids(case_ids)}


def sampler_quota_audit(
    case_ids: list[str],
    case_to_fold: dict[str, int],
    metadata: Any,
    cache: CaseCache,
    *,
    stage: str,
    batch_size: int,
    samples: int = 1000,
    seed: int = 20260727,
) -> dict[str, Any]:
    rng = random.Random(seed)
    sampler_index = build_sampler_index(case_ids, case_to_fold, metadata, cache, stage=stage)
    effective_counts = {"error_fn": 0, "error_fp": 0, "pathology": 0, "random": 0}
    requested_counts = {"error_fn": 0, "error_fp": 0, "pathology": 0, "random": 0}
    hit = {"error_fn": 0, "error_fp": 0, "pathology": 0}
    denom = {"error_fn": 0, "error_fp": 0, "pathology": 0}
    fallback_reasons: dict[str, int] = {}
    silent_fallback = 0
    batches = math.ceil(samples / batch_size)
    seen = 0
    for _ in range(batches):
        batch = build_batch(case_ids, case_to_fold, metadata, cache, rng, stage=stage, batch_size=batch_size, sampler_index=sampler_index)
        for item in batch["sample_accounting"]:
            if seen >= samples:
                break
            requested = str(item["requested_mode"])
            effective = str(item["effective_mode"])
            requested_counts[requested] += 1
            effective_counts[effective] += 1
            if requested in denom:
                denom[requested] += 1
                if int(item.get("target_voxel_count_in_patch", 0)) > 0 and effective == requested:
                    hit[requested] += 1
            reason = str(item.get("fallback_reason") or "")
            if reason:
                fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1
            if requested != effective:
                silent_fallback += 1
            seen += 1
    fractions = {k: v / float(samples) for k, v in effective_counts.items()}
    hit_rates = {k: hit[k] / float(max(1, denom[k])) for k in hit}
    status = "PASS" if (
        hit_rates["error_fn"] == 1.0
        and hit_rates["error_fp"] == 1.0
        and hit_rates["pathology"] == 1.0
        and silent_fallback == 0
        and abs((fractions["error_fn"] + fractions["error_fp"]) - 0.5) <= 0.02
        and abs(fractions["pathology"] - 0.25) <= 0.02
        and abs(fractions["random"] - 0.25) <= 0.02
    ) else "NEEDS_REPAIR"
    return {
        "status": status,
        "samples": samples,
        "requested_counts": requested_counts,
        "effective_counts": effective_counts,
        "effective_fractions": fractions,
        "target_hit_rates": hit_rates,
        "silent_fallback_count": silent_fallback,
        "fallback_reasons": fallback_reasons,
        "stage": stage,
        "batch_size": batch_size,
        "sampler_index": {k: v for k, v in sampler_index.items() if k not in {"weights", "eligible", "target_counts_by_case"}},
        "eligible_counts": sampler_index["eligible_counts"],
        "sampler_index_sha256": sampler_index["sampler_index_sha256"],
    }


def random_negative_semantics_audit(
    case_ids: list[str],
    case_to_fold: dict[str, int],
    metadata: Any,
    cache: CaseCache,
    *,
    stage: str,
    samples: int = 1000,
    seed: int = 20260727,
) -> dict[str, Any]:
    active_cases = [case_id for case_id in sorted(case_ids) if stage != "B" or metadata[case_id].modality_group == "C0+LGE+T2"]
    if not active_cases:
        raise ValueError(f"CARE_DG_RANDOM_NEGATIVE_AUDIT_EMPTY_STAGE:{stage}")
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    category_counts = {"blood_pool": 0, "remote_background": 0, "historical_anchor_fp": 0, "bright_remote_lge_island": 0, "ordinary_random": 0}
    for idx in range(int(samples)):
        case_id = active_cases[rng.randrange(len(active_cases))]
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        labels = rec["labels"]
        center = (rng.randrange(labels.shape[0]), rng.randrange(labels.shape[1]), rng.randrange(labels.shape[2]))
        anchor_patch = crop_pad(rec["anchor_mask"][None], center, PATCH_SHAPE, fill=0)[0]
        label_patch = crop_pad(rec["labels"][None], center, PATCH_SHAPE, fill=0)[0]
        lge_patch = crop_pad(rec["images"][0:1], center, PATCH_SHAPE, fill=0.0)[0]
        support_patch = crop_pad(rec["myocardium_support"], center, PATCH_SHAPE, fill=0.0)[0]
        blood_pool_voxels = int(np.count_nonzero(np.isin(anchor_patch, [2, 3])))
        support_outside_voxels = int(np.count_nonzero(support_patch < 0.1))
        anchor_scar_fp_voxels = int(np.count_nonzero((anchor_patch == SCAR) & (label_patch != SCAR)))
        zone_anchor = (anchor_patch == SCAR) | (anchor_patch == EDEMA)
        zone_label = (label_patch == SCAR) | (label_patch == EDEMA)
        anchor_edema_zone_fp_voxels = int(np.count_nonzero(zone_anchor & ~zone_label)) if bool(meta.t2_present) else 0
        bright_remote_lge_voxels = int(np.count_nonzero((lge_patch >= 2.5) & (support_patch < 0.1)))
        hits = {
            "blood_pool": blood_pool_voxels > 0,
            "remote_background": support_outside_voxels > 0,
            "historical_anchor_fp": (anchor_scar_fp_voxels + anchor_edema_zone_fp_voxels) > 0,
            "bright_remote_lge_island": bright_remote_lge_voxels > 0,
        }
        ordinary = not any(hits.values())
        for key, value in hits.items():
            if value:
                category_counts[key] += 1
        if ordinary:
            category_counts["ordinary_random"] += 1
        patch_hash = hashlib.sha256(
            f"{case_id}:{stage}:{idx}:{center}".encode("utf-8")
            + anchor_patch.astype(np.int16, copy=False).tobytes()
            + label_patch.astype(np.int16, copy=False).tobytes()
        ).hexdigest()
        rows.append({
            "sample_index": idx,
            "case_id": case_id,
            "center_zyx": list(center),
            "patch_hash": patch_hash,
            "center_anchor_class": int(rec["anchor_mask"][center]),
            "lv_rv_blood_pool_voxel_count": blood_pool_voxels,
            "scar_support_lt_0_1_voxel_count": support_outside_voxels,
            "anchor_scar_fp_voxel_count": anchor_scar_fp_voxels,
            "anchor_edema_zone_fp_voxel_count": anchor_edema_zone_fp_voxels,
            "lge_z_ge_2_5_and_scar_support_lt_0_1_voxel_count": bright_remote_lge_voxels,
            "hits_blood_pool": hits["blood_pool"],
            "hits_remote_background": hits["remote_background"],
            "hits_historical_anchor_fp": hits["historical_anchor_fp"],
            "hits_bright_remote_lge_island": hits["bright_remote_lge_island"],
            "ordinary_random": ordinary,
            "t2_present": bool(meta.t2_present),
        })
    summary = {
        "status": "PASS" if len(rows) == int(samples) else "NEEDS_REPAIR",
        "stage": stage,
        "samples": int(samples),
        "case_count": len(active_cases),
        "case_ids_sha256": sha256_case_ids(active_cases),
        "category_counts": category_counts,
        "category_patch_fractions": {key: value / float(samples) for key, value in category_counts.items()},
        "records": rows,
    }
    summary["audit_sha256"] = stable_json_sha256({k: v for k, v in summary.items() if k != "audit_sha256"})
    return summary


def build_inner_evaluation_plan(
    case_ids: list[str],
    case_to_fold: dict[str, int],
    metadata: Any,
    cache: CaseCache,
    *,
    fold: int,
    split_contract: dict[str, Any],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    mode_counts = {mode: 0 for mode in INNER_EVAL_MODES}
    case_accounting: dict[str, dict[str, Any]] = {}
    for case_id in sorted(case_ids):
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        masks = case_target_masks(rec, bool(meta.t2_present))
        per_case_modes: list[str] = []
        for mode in INNER_EVAL_MODES:
            if mode.startswith("edema_zone") and not bool(meta.t2_present):
                continue
            center = deterministic_center(masks[mode], case_id, mode, "inner_eval")
            if center is None:
                continue
            target_count = target_voxels_in_patch(rec, center, mode, bool(meta.t2_present))
            if target_count <= 0:
                continue
            entries.append({
                "entry_index": len(entries),
                "case_id": case_id,
                "center_zyx": list(center),
                "mode": mode,
                "target_voxel_count_in_patch": int(target_count),
                "augmentation": "none",
                "patch_shape_zyx": list(PATCH_SHAPE),
            })
            mode_counts[mode] += 1
            per_case_modes.append(mode)
        case_accounting[case_id] = {"modality_group": str(meta.modality_group), "t2_present": bool(meta.t2_present), "modes": per_case_modes, "patches": len(per_case_modes)}
    missing_cases = [case_id for case_id, row in case_accounting.items() if int(row["patches"]) == 0]
    if missing_cases:
        raise ValueError(f"CARE_DG_INNER_EVAL_PLAN_CASE_WITHOUT_PATCH:{missing_cases[:5]}")
    payload = {
        "schema_version": 2,
        "gate_revision": "A-R3",
        "fold": fold,
        "created_at_utc": now_utc(),
        "case_count": len(case_ids),
        "case_ids_sha256": sha256_case_ids(case_ids),
        "patch_count": len(entries),
        "mode_counts": mode_counts,
        "case_accounting": case_accounting,
        "entries": entries,
        "objective": "fixed_complete_inner_select_no_aug_patch_loss",
        "stage_a_and_stage_b_share_objective": True,
        "training_rng_dependency": False,
        "split_sha256": split_contract.get("sha256", {}),
        "config_sha256": sha256_file(CONFIG_PATH) if CONFIG_PATH.exists() else "missing",
        "source_hashes": source_hashes(),
    }
    payload["plan_sha256"] = stable_json_sha256({k: v for k, v in payload.items() if k not in {"plan_sha256", "created_at_utc"}})
    return payload


def evaluate_inner(model: torch.nn.Module, plan: dict[str, Any], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, device: torch.device, batch_size: int) -> dict[str, Any]:
    model.eval()
    losses: list[float] = []
    items: list[dict[str, Any]] = []
    entries = list(plan.get("entries") or [])
    with torch.no_grad():
        for offset in range(0, len(entries), max(1, batch_size)):
            chunk = entries[offset : offset + max(1, batch_size)]
            batch = move_tensors(_batch_from_centers(chunk, case_to_fold, metadata, cache), device)
            out = model(
                batch["images"],
                batch["availability"],
                batch["anchor_logits"],
                uncertainty=batch["uncertainty"],
                myocardium_support=batch["myocardium_support"],
                edema_support=batch["edema_support"],
                distance_to_myocardium=batch["distance_to_myocardium"],
                t2_present=batch["t2_present"],
                strict_inputs=True,
                anchor_value_kind=batch["anchor_value_kind"],
            )
            anchor_mask = batch["anchor_logits"].argmax(dim=1)
            loss, metrics = care_dg_loss(out, batch["labels"], anchor_mask, t2_present=batch["t2_present"], edema_reliable=batch["t2_present"])
            loss_value = float(loss.detach().cpu())
            losses.append(loss_value)
            items.append({
                "offset": offset,
                "batch_entries": [int(item["entry_index"]) for item in chunk],
                "case_ids": [str(item["case_id"]) for item in chunk],
                "modes": [str(item["mode"]) for item in chunk],
                "loss": loss_value,
                "metrics": metrics,
            })
    model.train()
    return {
        "status": "PASS" if losses else "NEEDS_REPAIR",
        "plan_sha256": plan.get("plan_sha256"),
        "loss": float(np.mean(losses)) if losses else math.inf,
        "loss_items": items,
        "case_count": plan.get("case_count"),
        "patch_count": plan.get("patch_count"),
        "mode_counts": plan.get("mode_counts"),
    }

def source_hashes() -> dict[str, str]:
    paths = [
        "configs/care_dg/care_dg_v1.yaml",
        "src/care_myocardium/models/care_dg.py",
        "src/care_myocardium/data/care_dg_dataset.py",
        "src/care_myocardium/training/care_dg_trainer.py",
        "src/care_myocardium/inference/care_dg_predictor.py",
        "scripts/training/run_care_dg.py",
        "scripts/inference/run_care_dg_inference.py",
        "scripts/evaluation/evaluate_care_dg.py",
        "scripts/evaluation/select_care_dg_candidate.py",
        "scripts/evaluation/validate_care_dg_packet.py",
        "scripts/evaluation/build_care_dg_validation_packet.py",
        "scripts/evaluation/run_care_dg_gate_a_checks.py",
        "scripts/evaluation/finalize_care_dg_gate_a_r3_evidence.py",
        "scripts/evaluation/validate_care_dg_gate_a_consistency.py",
        "tests/care_dg/test_care_dg_model.py",
    ]
    return {p: sha256_file(REPO_ROOT / p) for p in paths if (REPO_ROOT / p).exists()}





def care_dg_trainable_parameter_groups(model: torch.nn.Module) -> dict[str, Any]:
    groups: dict[str, list[tuple[str, torch.nn.Parameter]]] = {
        "representation_group": [],
        "pathology_group": [],
    }
    unknown: list[str] = []
    seen: dict[int, str] = {}
    duplicates: list[str] = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        root = name.split(".", 1)[0]
        if root in REPRESENTATION_MODULES:
            group = "representation_group"
        elif root in PATHOLOGY_MODULES:
            group = "pathology_group"
        else:
            unknown.append(name)
            continue
        param_id = id(param)
        if param_id in seen:
            duplicates.append(f"{name}|{seen[param_id]}")
        seen[param_id] = name
        groups[group].append((name, param))
    if unknown:
        raise ValueError(f"CARE_DG_OPTIMIZER_PARAMETER_GROUP_UNKNOWN:{unknown[:8]}")
    if duplicates:
        raise ValueError(f"CARE_DG_OPTIMIZER_PARAMETER_GROUP_DUPLICATE:{duplicates[:8]}")
    if not groups["representation_group"] or not groups["pathology_group"]:
        raise ValueError("CARE_DG_OPTIMIZER_PARAMETER_GROUP_EMPTY")
    trainable_ids = {id(p) for _, p in model.named_parameters() if p.requires_grad}
    grouped_ids = {id(param) for rows in groups.values() for _, param in rows}
    if trainable_ids != grouped_ids:
        raise ValueError("CARE_DG_OPTIMIZER_PARAMETER_GROUP_COVERAGE_MISMATCH")
    return {
        "representation_group": groups["representation_group"],
        "pathology_group": groups["pathology_group"],
        "parameter_names": {key: [name for name, _ in rows] for key, rows in groups.items()},
        "parameter_count": {key: int(sum(param.numel() for _, param in rows)) for key, rows in groups.items()},
        "parameter_names_sha256": {
            key: hashlib.sha256("\n".join(name for name, _ in rows).encode("utf-8")).hexdigest()
            for key, rows in groups.items()
        },
    }


def build_care_dg_optimizer(
    model: torch.nn.Module,
    *,
    representation_lr: float,
    pathology_lr: float,
    weight_decay: float,
) -> torch.optim.Optimizer:
    grouped = care_dg_trainable_parameter_groups(model)
    return torch.optim.AdamW(
        [
            {
                "name": "representation_group",
                "params": [param for _, param in grouped["representation_group"]],
                "lr": float(representation_lr),
                "weight_decay": float(weight_decay),
            },
            {
                "name": "pathology_group",
                "params": [param for _, param in grouped["pathology_group"]],
                "lr": float(pathology_lr),
                "weight_decay": float(weight_decay),
            },
        ]
    )


def set_stage_learning_rates(optimizer: torch.optim.Optimizer, *, stage: str, args: argparse.Namespace) -> dict[str, float]:
    if stage == "A":
        target = {
            "representation_group": float(args.lr_stage_a_representation),
            "pathology_group": float(args.lr_stage_a_pathology),
        }
    elif stage == "B":
        target = {
            "representation_group": float(args.lr_stage_b_representation),
            "pathology_group": float(args.lr_stage_b_pathology),
        }
    else:
        raise ValueError(f"unknown CARE-DG training stage: {stage}")
    seen: set[str] = set()
    for group in optimizer.param_groups:
        name = str(group.get("name", ""))
        if name not in target:
            raise ValueError(f"CARE_DG_OPTIMIZER_UNKNOWN_PARAM_GROUP:{name}")
        group["lr"] = target[name]
        group["weight_decay"] = float(args.weight_decay)
        seen.add(name)
    missing = set(target) - seen
    if missing:
        raise ValueError(f"CARE_DG_OPTIMIZER_MISSING_PARAM_GROUP:{sorted(missing)}")
    return target


def current_group_lrs(optimizer: torch.optim.Optimizer) -> dict[str, float]:
    return {str(group.get("name", f"group{idx}")): float(group["lr"]) for idx, group in enumerate(optimizer.param_groups)}


def current_group_weight_decays(optimizer: torch.optim.Optimizer) -> dict[str, float]:
    return {str(group.get("name", f"group{idx}")): float(group.get("weight_decay", 0.0)) for idx, group in enumerate(optimizer.param_groups)}


def amp_autocast_dtype(name: str) -> torch.dtype:
    if name == "bfloat16":
        return torch.bfloat16
    if name == "float16":
        return torch.float16
    raise ValueError(f"unsupported CARE-DG AMP dtype: {name}")


def resolved_training_contract(
    *,
    fold: int,
    args: argparse.Namespace,
    stage_a_steps: int,
    stage_b_steps: int,
    batch_size: int,
    cap_audit: dict[str, Any],
    inner_plan: dict[str, Any],
    split_contract: dict[str, Any],
    sampler_index_a: dict[str, Any],
    sampler_index_b: dict[str, Any] | None,
    sampler_audit_a: dict[str, Any],
    sampler_audit_b: dict[str, Any] | None,
    random_negative_audit_a: dict[str, Any],
    random_negative_audit_b: dict[str, Any] | None,
    model_config: dict[str, Any],
    optimizer_group_report: dict[str, Any],
    device: torch.device,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "method": "CARE-DG",
        "gate_revision": "A-R3",
        "fold": int(fold),
        "seed": int(args.seed),
        "stage_a_optimizer_steps": int(stage_a_steps),
        "stage_b_optimizer_steps": int(stage_b_steps),
        "batch_size": int(batch_size),
        "patch_shape_zyx": list(PATCH_SHAPE),
        "sampler_pattern": list(SAMPLER_PATTERN),
        "learning_rates": {
            "stage_a": {
                "representation_group": float(args.lr_stage_a_representation),
                "pathology_group": float(args.lr_stage_a_pathology),
            },
            "stage_b": {
                "representation_group": float(args.lr_stage_b_representation),
                "pathology_group": float(args.lr_stage_b_pathology),
            },
        },
        "weight_decay": float(args.weight_decay),
        "grad_clip_norm": float(args.grad_clip_norm),
        "gradient_clipping": {"enabled": float(args.grad_clip_norm) > 0.0, "max_norm": float(args.grad_clip_norm)},
        "amp": {"requested": bool(args.amp), "enabled": bool(args.amp and device.type == "cuda"), "dtype": str(args.amp_dtype)},
        "model_channels": {
            "stem_channels": int(model_config["stem_channels"]),
            "context_channels": int(model_config["context_channels"]),
            "encoder_channels": list(model_config["encoder_channels"]),
            "anchor_channels": int(model_config["anchor_channels"]),
        },
        "optimizer_groups": {
            "representation_group": list(REPRESENTATION_MODULES),
            "pathology_group": list(PATHOLOGY_MODULES),
            "parameter_count": optimizer_group_report["parameter_count"],
            "parameter_names_sha256": optimizer_group_report["parameter_names_sha256"],
        },
        "scar_margin_cap_rule": "clip(Q0.95_abs_anchor_error_margin_actual_train+1,2,8)",
        "edema_zone_margin_cap_rule": "clip(Q0.95_abs_anchor_error_margin_actual_train+1,2,8)",
        "actual_margin_caps": {
            "scar": float(cap_audit["scar"]["cap"]),
            "edema_zone": float(cap_audit["edema_zone"]["cap"]),
            "fit_population": str(cap_audit.get("fit_population")),
            "case_ids_sha256": str(cap_audit.get("case_ids_sha256")),
        },
        "loss_weights": {
            "segmentation_dice_plus_bce": 1.0,
            "fn_fp_focal_bce": 0.5,
            "error_margin_improvement": 0.25,
            "identity_anchor_correct": 0.10,
            "remote_positive_pre_support_raw_delta": 0.10,
            "no_t2_edema_loss_weight": 0.0,
        },
        "support_semantics": {
            "support_labels": [1, 4, 5],
            "excluded_labels": [2, 3],
            "scar_shell_mm": 6,
            "edema_zone_shell_mm": 10,
            "distance_to_myocardium_clip_mm": list(DISTANCE_CLIP_MM),
            "hard_crop": False,
        },
        "fixed_inner_evaluation_plan_sha256": str(inner_plan["plan_sha256"]),
        "split_hashes": dict(split_contract.get("sha256") or {}),
        "sampler_hashes": {
            "stage_a_sampler_index_sha256": str(sampler_index_a["sampler_index_sha256"]),
            "stage_b_sampler_index_sha256": str(sampler_index_b["sampler_index_sha256"]) if sampler_index_b else "none",
            "stage_a_audit_status": str(sampler_audit_a.get("status")),
            "stage_b_audit_status": str(sampler_audit_b.get("status")) if sampler_audit_b else "none",
        },
        "composition_semantics": {
            "revision": "GateB_scar_priority_hotfix",
            "order": ["anchor_logits", "bounded_edema_zone_correction", "bounded_scar_correction", "final_six_class_argmax"],
            "required_outputs": ["after_edema_logits", "final_logits_after_scar_priority"],
            "post_scar_overwrite_allowed": False,
            "edema_zone": "final_scar_union_final_pure_edema",
            "pure_edema": "edema_zone_minus_final_scar",
        },
        "random_negative_semantics_audit_hashes": {
            "stage_a_status": str(random_negative_audit_a.get("status")),
            "stage_a_sha256": str(random_negative_audit_a.get("audit_sha256")),
            "stage_b_status": str(random_negative_audit_b.get("status")) if random_negative_audit_b else "none",
            "stage_b_sha256": str(random_negative_audit_b.get("audit_sha256")) if random_negative_audit_b else "none",
        },
        "source_hashes": source_hashes(),
        "config_sha256": sha256_file(CONFIG_PATH) if CONFIG_PATH.exists() else "missing",
    }
    payload["resolved_training_contract_sha256"] = stable_json_sha256(payload)
    return payload


def checkpoint_extra_summary(extra: dict[str, Any]) -> dict[str, Any]:
    runtime_state = dict(extra.get("runtime_state") or {})
    return {
        "extra_keys": sorted(str(k) for k in extra.keys()),
        "hash_contract": extra.get("hash_contract"),
        "runtime_state_keys": sorted(str(k) for k in runtime_state.keys()),
        "stage": runtime_state.get("stage"),
        "local_step": runtime_state.get("local_step"),
        "total_step": runtime_state.get("total_step"),
        "fixed_inner_evaluation_plan_sha256": runtime_state.get("fixed_inner_evaluation_plan_sha256"),
        "has_python_random_state": runtime_state.get("python_random_state") is not None,
        "has_local_random_state": runtime_state.get("local_random_state") is not None,
        "has_numpy_random_state": runtime_state.get("numpy_random_state") is not None,
        "has_torch_cpu_rng_state": runtime_state.get("torch_cpu_rng_state") is not None,
        "torch_cuda_rng_state_count": len(runtime_state.get("torch_cuda_rng_states") or []),
        "has_amp_grad_scaler_state": runtime_state.get("amp_grad_scaler_state") is not None,
    }

def activation_stats(out: dict[str, torch.Tensor], labels: torch.Tensor, anchor_mask: torch.Tensor, t2_present: torch.Tensor) -> dict[str, float]:
    if labels.ndim == 5:
        labels = labels[:, 0]
    if anchor_mask.ndim == 5:
        anchor_mask = anchor_mask[:, 0]
    t2 = t2_present.to(labels.device).view(-1, 1, 1, 1, 1)
    scar_fn = ((labels == SCAR) & (anchor_mask != SCAR)).unsqueeze(1)
    scar_fp = ((labels != SCAR) & (anchor_mask == SCAR)).unsqueeze(1)
    zone_gt = (labels == SCAR) | (labels == EDEMA)
    zone_pred = (anchor_mask == SCAR) | (anchor_mask == EDEMA)
    edema_fn = (zone_gt & ~zone_pred).unsqueeze(1) & (t2 > 0)
    edema_fp = (~zone_gt & zone_pred).unsqueeze(1) & (t2 > 0)
    correct = (labels == anchor_mask).unsqueeze(1)
    def med(t: torch.Tensor, mask: torch.Tensor) -> float:
        vals = t.detach()[mask.expand_as(t)]
        return float(vals.median().cpu()) if vals.numel() else 0.0
    def frac(mask: torch.Tensor) -> float:
        return float(mask.float().mean().cpu())
    return {
        "scar_q_fn_true_fn_median": med(out["scar_q_fn"], scar_fn),
        "scar_q_fn_correct_median": med(out["scar_q_fn"], correct),
        "scar_q_fp_true_fp_median": med(out["scar_q_fp"], scar_fp),
        "scar_q_fp_correct_median": med(out["scar_q_fp"], correct),
        "edema_q_fn_true_fn_median": med(out["edema_q_fn"], edema_fn),
        "edema_q_fn_correct_median": med(out["edema_q_fn"], correct & (t2 > 0)),
        "edema_q_fp_true_fp_median": med(out["edema_q_fp"], edema_fp),
        "edema_q_fp_correct_median": med(out["edema_q_fp"], correct & (t2 > 0)),
        "scar_m_fn_median": float(out["scar_m_fn"].detach().median().cpu()),
        "scar_m_fp_median": float(out["scar_m_fp"].detach().median().cpu()),
        "edema_m_fn_median": float(out["edema_m_fn"].detach()[(t2 > 0).expand_as(out["edema_m_fn"])].median().cpu()) if (t2 > 0).any() else 0.0,
        "edema_m_fp_median": float(out["edema_m_fp"].detach()[(t2 > 0).expand_as(out["edema_m_fp"])].median().cpu()) if (t2 > 0).any() else 0.0,
        "scar_saturation_fraction": frac(out["scar_m_fn"] >= 0.95 * float(out["scar_m_fn"].detach().max().clamp_min(1e-6))),
        "edema_saturation_fraction": frac(out["edema_m_fn"] >= 0.95 * float(out["edema_m_fn"].detach().max().clamp_min(1e-6))),
    }


def contract() -> dict[str, object]:
    return {
        "method": "CARE-DG",
        "seed": 20260727,
        "folds": [0, 1, 2, 3, 4],
        "stage_a_optimizer_steps": 5000,
        "stage_b_optimizer_steps": 3000,
        "batch_size": 8,
        "patch_shape_zyx": list(PATCH_SHAPE),
        "stage_a_representation_lr": STAGE_A_REPRESENTATION_LR,
        "stage_a_pathology_lr": STAGE_A_PATHOLOGY_LR,
        "stage_b_representation_lr": STAGE_B_REPRESENTATION_LR,
        "stage_b_pathology_lr": STAGE_B_PATHOLOGY_LR,
        "weight_decay": WEIGHT_DECAY,
        "grad_clip_norm": GRAD_CLIP_NORM,
        "amp_dtype": AMP_DTYPE,
        "distance_to_myocardium_clip_mm": list(DISTANCE_CLIP_MM),
        "optimizer_groups": {
            "representation_group": list(REPRESENTATION_MODULES),
            "pathology_group": list(PATHOLOGY_MODULES),
        },
        "composition_order": ["anchor_logits", "bounded_edema_zone_correction", "bounded_scar_correction", "final_six_class_argmax"],
        "required_outputs": ["after_edema_logits", "final_logits_after_scar_priority"],
        "runtime_label_formal": "repaired_formal_scar_priority",
        "runtime_labels_protected": sorted(PROTECTED_RUNTIME_LABELS),
        "runtime_forbidden": ["MoSAIC", "full_MMRD", "prototype_dictionary", "SIP", "multi_expert", "old_Cascade"],
        "gpu_execution": "srun --jobid=60657290 --overlap only; serial GPU commands",
    }


def unit_smoke() -> dict[str, object]:
    torch.manual_seed(20260727)
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    images = torch.randn(1, 3, 4, 16, 16)
    anchor = torch.randn(1, 6, 4, 16, 16)
    availability = torch.ones(1, 3)
    out = model(images, availability, anchor)
    return {"status": "PASS", "final_logits_shape": list(out["final_logits"].shape), "has_after_edema_logits": "after_edema_logits" in out, "has_final_logits_after_scar_priority": "final_logits_after_scar_priority" in out, "scar_delta_nonconstant": bool(out["scar_delta"].std().item() > 0), "edema_delta_nonconstant": bool(out["edema_delta"].std().item() > 0)}


def validate_w0(result_root: Path) -> None:
    report = json.loads((result_root / "strict_validator_report.json").read_text(encoding="utf-8"))
    if report.get("status") != "PASS":
        raise SystemExit("CARE_DG_FORMAL_TRAINING_BLOCKED_W0_VALIDATOR_NOT_PASS")
    impl = json.loads((result_root / "implementation_contract.json").read_text(encoding="utf-8"))
    if str(impl.get("status", "")).strip() not in ALLOWED_W0_CONTRACT_STATUSES:
        raise SystemExit("CARE_DG_FORMAL_TRAINING_BLOCKED_W1_NOT_PASS")


def train_fold(fold: int, args: argparse.Namespace, result_root: Path) -> dict[str, Any]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda" and not args.allow_cpu:
        raise SystemExit("CARE_DG_FORMAL_TRAINING_REQUIRES_CUDA")
    torch.manual_seed(args.seed + fold); np.random.seed(args.seed + fold); rng = random.Random(args.seed + fold)
    splits = load_splits(); split = next(row for row in splits if int(row["fold"]) == fold)
    outer_train = sorted(split["train"]); outer_val = sorted(split["val"])
    metadata = load_myops_case_metadata(REPO_ROOT)
    split_contract = deterministic_inner_split(outer_train, fold, metadata)
    train_cases = list(split_contract["actual_train_cases"])
    inner_select = list(split_contract["complete_inner_select_cases"] or split_contract["inner_select_cases"])
    complete_train_cases = list(split_contract["complete_actual_train_cases"])
    preflight_only = bool(args.preflight_steps or args.gate_a_r2_preflight or args.gate_a_r3_preflight or args.gate_b_scar_priority_preflight)
    if args.gate_a_r2_preflight or args.gate_a_r3_preflight or args.gate_b_scar_priority_preflight:
        stage_a_steps = 1; stage_b_steps = 1; batch_size = min(2, args.batch_size)
    elif args.preflight_steps:
        stage_a_steps = int(args.preflight_steps); stage_b_steps = 0; batch_size = min(2, args.batch_size)
    else:
        stage_a_steps = args.stage_a_steps; stage_b_steps = args.stage_b_steps; batch_size = args.batch_size
    runtime_kind = args.runtime_label
    runtime_root = result_root / "runtime" / runtime_kind / f"fold{fold}"
    if runtime_kind in PROTECTED_RUNTIME_LABELS:
        raise SystemExit(f"CARE_DG_RUNTIME_LABEL_PROTECTED_READ_ONLY:{runtime_kind}")
    receipt_path = runtime_root / "fold_training_receipt.json"
    if args.resume and receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        expected_steps = stage_a_steps + stage_b_steps
        if (
            receipt.get("status") == "PASS"
            and bool(receipt.get("preflight_only")) == preflight_only
            and int(receipt.get("actual_optimizer_steps", -1)) == int(expected_steps)
        ):
            print(json.dumps({"fold": fold, "status": "SKIP_COMPLETED_ON_RESUME", "actual_optimizer_steps": expected_steps}), flush=True)
            return receipt
    if runtime_root.exists() and not args.resume:
        import shutil
        shutil.rmtree(runtime_root)
    ckpt_dir = runtime_root / "checkpoints"; ckpt_dir.mkdir(parents=True, exist_ok=True)
    log_rows: list[dict[str, Any]] = []
    ckpt_rows: list[dict[str, Any]] = []
    cache = CaseCache(max_cases=args.cache_cases)
    case_to_fold: dict[str, int] = {}
    for row in json.loads((result_root / "nnunet_oof_anchor_manifest.json").read_text(encoding="utf-8"))["entries"]:
        case_to_fold[str(row["case_id"])] = int(row["source_fold"])
    cap_audit = margin_caps_for_cases(train_cases, case_to_fold, metadata, cache)
    inner_plan = build_inner_evaluation_plan(inner_select, case_to_fold, metadata, cache, fold=fold, split_contract=split_contract)
    sampler_index_a = build_sampler_index(train_cases, case_to_fold, metadata, cache, stage="A")
    sampler_index_b = build_sampler_index(complete_train_cases, case_to_fold, metadata, cache, stage="B") if complete_train_cases else None
    sampler_audit_a = sampler_quota_audit(train_cases, case_to_fold, metadata, cache, stage="A", batch_size=max(8, batch_size), samples=1000, seed=args.seed + fold)
    sampler_audit_b = sampler_quota_audit(complete_train_cases, case_to_fold, metadata, cache, stage="B", batch_size=max(8, batch_size), samples=1000, seed=args.seed + fold + 100000) if sampler_index_b else None
    random_negative_audit_a = random_negative_semantics_audit(train_cases, case_to_fold, metadata, cache, stage="A", samples=1000, seed=args.seed + fold + 200000)
    random_negative_audit_b = random_negative_semantics_audit(complete_train_cases, case_to_fold, metadata, cache, stage="B", samples=1000, seed=args.seed + fold + 300000) if sampler_index_b else None
    write_json(runtime_root / "inner_split_manifest.json", split_contract)
    write_json(runtime_root / "inner_evaluation_plan.json", inner_plan)
    write_json(runtime_root / "sampler_quota_audit_stage_a.json", sampler_audit_a)
    if sampler_audit_b is not None:
        write_json(runtime_root / "sampler_quota_audit_stage_b.json", sampler_audit_b)
    write_json(runtime_root / "sampler_quota_audit.json", sampler_audit_a)
    write_json(runtime_root / "random_negative_semantics_audit_stage_a.json", random_negative_audit_a)
    if random_negative_audit_b is not None:
        write_json(runtime_root / "random_negative_semantics_audit_stage_b.json", random_negative_audit_b)
    write_json(runtime_root / "margin_cap_audit.json", cap_audit)
    for audit_name, audit in [("stage_a", sampler_audit_a), ("stage_b", sampler_audit_b)]:
        if audit is None:
            if stage_b_steps > 0 and audit_name == "stage_b":
                raise RuntimeError(f"sampler quota audit missing for fold={fold} stage=B")
            continue
        if audit.get("status") != "PASS":
            raise RuntimeError(f"sampler quota audit failed for fold={fold} {audit_name}: {audit}")
    model_config = {
        "encoder_channels": tuple(args.encoder_channels),
        "context_channels": args.context_channels,
        "scar_margin_cap": float(cap_audit["scar"]["cap"]),
        "edema_margin_cap": float(cap_audit["edema_zone"]["cap"]),
    }
    model = build_care_dg(model_config).to(device)
    optimizer_group_report = care_dg_trainable_parameter_groups(model)
    resolved_contract = resolved_training_contract(
        fold=fold,
        args=args,
        stage_a_steps=stage_a_steps,
        stage_b_steps=stage_b_steps,
        batch_size=batch_size,
        cap_audit=cap_audit,
        inner_plan=inner_plan,
        split_contract=split_contract,
        sampler_index_a=sampler_index_a,
        sampler_index_b=sampler_index_b,
        sampler_audit_a=sampler_audit_a,
        sampler_audit_b=sampler_audit_b,
        random_negative_audit_a=random_negative_audit_a,
        random_negative_audit_b=random_negative_audit_b,
        model_config=model.config.__dict__,
        optimizer_group_report=optimizer_group_report,
        device=device,
    )
    write_json(runtime_root / "resolved_training_contract.json", resolved_contract)
    hash_contract = {
        "resolved_training_contract_sha256": resolved_contract["resolved_training_contract_sha256"],
        "resolved_training_contract": resolved_contract,
    }
    optimizer = build_care_dg_optimizer(
        model,
        representation_lr=args.lr_stage_a_representation,
        pathology_lr=args.lr_stage_a_pathology,
        weight_decay=args.weight_decay,
    )
    autocast_dtype = amp_autocast_dtype(str(args.amp_dtype))
    scaler = GradScaler("cuda", enabled=bool(args.amp and device.type == "cuda" and str(args.amp_dtype) == "float16"))
    best_inner = math.inf; best_path = None
    started = time.time(); total_steps = 0
    resume_step = 0
    if args.resume and not preflight_only:
        step_ckpts = sorted(ckpt_dir.glob("checkpoint_step*.pt"))
        if step_ckpts:
            resume_ckpt = step_ckpts[-1]
            model, resume_step, _extra = load_care_dg_checkpoint(resume_ckpt, model=model, optimizer=optimizer, scaler=scaler, local_rng=rng, restore_rng=True, expected_hash_contract=hash_contract)
            model = model.to(device)
            total_steps = int(resume_step)
            curve_path = runtime_root / "training_curve.csv"
            if curve_path.exists():
                curve_rows = list(csv.DictReader(curve_path.open(newline="", encoding="utf-8")))
                kept_curve = [row for row in curve_rows if int(row.get("total_step", 0) or 0) <= resume_step]
                write_csv(curve_path, kept_curve)
                log_rows.extend(kept_curve)
            ckpt_manifest_path = runtime_root / "checkpoint_manifest.csv"
            if ckpt_manifest_path.exists():
                existing_ckpts = list(csv.DictReader(ckpt_manifest_path.open(newline="", encoding="utf-8")))
                for row in existing_ckpts:
                    try:
                        step = int(row.get("step", -1))
                    except ValueError:
                        continue
                    if step <= resume_step and str(row.get("stage")) not in {"last", "best"}:
                        ckpt_rows.append(row)
                        try:
                            inner = float(row.get("inner_loss", "inf"))
                        except ValueError:
                            inner = math.inf
                        path = Path(str(row.get("checkpoint_path", "")))
                        if math.isfinite(inner) and inner < best_inner and path.is_file():
                            best_inner = inner
                            best_path = path
            print(json.dumps({"fold": fold, "status": "RESUME_FROM_CHECKPOINT", "checkpoint": str(resume_ckpt), "resume_step": resume_step}), flush=True)
    stage_specs = [("A", stage_a_steps, train_cases), ("B", stage_b_steps, complete_train_cases)]
    for stage, steps, cases in stage_specs:
        if steps <= 0:
            continue
        stage_offset = 0 if stage == "A" else stage_a_steps
        if total_steps >= stage_offset + steps:
            continue
        start_local_step = max(1, total_steps - stage_offset + 1)
        stage_lrs = set_stage_learning_rates(optimizer, stage=stage, args=args)
        for local_step in range(start_local_step, steps + 1):
            total_steps += 1
            sampler_index = sampler_index_a if stage == "A" else sampler_index_b
            batch = build_batch(cases, case_to_fold, metadata, cache, rng, stage=stage, batch_size=batch_size, sampler_index=sampler_index)
            batch = move_tensors(batch, device)
            optimizer.zero_grad(set_to_none=True)
            with autocast("cuda", enabled=bool(args.amp and device.type == "cuda"), dtype=autocast_dtype):
                out = model(
                    batch["images"],
                    batch["availability"],
                    batch["anchor_logits"],
                    uncertainty=batch["uncertainty"],
                    myocardium_support=batch["myocardium_support"],
                    edema_support=batch["edema_support"],
                    distance_to_myocardium=batch["distance_to_myocardium"],
                    t2_present=batch["t2_present"],
                    strict_inputs=True,
                    anchor_value_kind=batch["anchor_value_kind"],
                )
                anchor_mask = batch["anchor_logits"].argmax(dim=1)
                loss, metrics = care_dg_loss(out, batch["labels"], anchor_mask, t2_present=batch["t2_present"], edema_reliable=batch["t2_present"])
            if not torch.isfinite(loss):
                raise RuntimeError(f"nonfinite CARE-DG loss at fold={fold} stage={stage} local_step={local_step}: {float(loss.detach().cpu())}")
            for metric_name, metric_value in metrics.items():
                if not math.isfinite(float(metric_value)):
                    raise RuntimeError(f"nonfinite CARE-DG metric {metric_name} at fold={fold} stage={stage} local_step={local_step}: {metric_value}")
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            grad_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                max_norm=float(args.grad_clip_norm),
                error_if_nonfinite=True,
            ) if float(args.grad_clip_norm) > 0.0 else torch.tensor(0.0, device=device)
            scaler.step(optimizer); scaler.update()
            if local_step == 1 or local_step % args.log_every == 0 or local_step == steps:
                changed = int((out["final_mask"] != anchor_mask).detach().sum().cpu())
                row = {"fold": fold, "stage": stage, "local_step": local_step, "total_step": total_steps, "representation_lr": stage_lrs["representation_group"], "pathology_lr": stage_lrs["pathology_group"], "loss": metrics["loss"], "grad_norm": float(grad_norm.detach().cpu()), "grad_clip_norm": float(args.grad_clip_norm), "amp_dtype": str(args.amp_dtype), "scar_gate": metrics["scar_gate"], "edema_gate": metrics["edema_gate"], "changed_voxels": changed, "scar_delta_std": float(out["scar_delta"].detach().std().cpu()), "edema_delta_std": float(out["edema_delta"].detach().std().cpu()), "elapsed_seconds": round(time.time() - started, 1)}
                row.update(activation_stats(out, batch["labels"], anchor_mask, batch["t2_present"]))
                log_rows.append(row)
                append_csv(runtime_root / "training_curve.csv", row, list(row.keys()))
                print(json.dumps(row), flush=True)
            should_checkpoint = ((not preflight_only) and (total_steps % 1000 == 0 or (stage == "B" and local_step == steps))) or (preflight_only and local_step == steps)
            if should_checkpoint:
                inner_eval = evaluate_inner(model, inner_plan, case_to_fold, metadata, cache, device, batch_size=min(2, batch_size))
                inner_loss = float(inner_eval["loss"])
                name = f"checkpoint_step{total_steps:05d}.pt" if not preflight_only else f"checkpoint_preflight_stage_{stage}_step{total_steps:05d}.pt"
                path = ckpt_dir / name
                save_care_dg_checkpoint(
                    path,
                    model,
                    optimizer,
                    total_steps,
                    {"fold": fold, "stage": stage, "inner_loss": inner_loss, "inner_eval": inner_eval, "outer_val_used_for_selection": False},
                    scaler=scaler,
                    local_rng=rng,
                    stage=stage,
                    local_step=local_step,
                    total_step=total_steps,
                    fixed_inner_plan_hash=str(inner_plan["plan_sha256"]),
                    hash_contract=hash_contract,
                )
                row = {"fold": fold, "stage": stage, "step": total_steps, "local_step": local_step, "representation_lr": stage_lrs["representation_group"], "pathology_lr": stage_lrs["pathology_group"], "weight_decay": args.weight_decay, "grad_clip_norm": float(args.grad_clip_norm), "amp_dtype": str(args.amp_dtype), "resolved_training_contract_sha256": resolved_contract["resolved_training_contract_sha256"], "checkpoint_path": str(path), "checkpoint_sha256": sha256_file(path), "inner_loss": inner_loss, "inner_plan_sha256": inner_plan["plan_sha256"], "selection_population": "fixed_train_side_complete_inner_plan", "outer_val_used": False}
                ckpt_rows.append(row)
                if inner_loss < best_inner:
                    best_inner = inner_loss; best_path = path
    last_path = ckpt_dir / "checkpoint_last.pt"
    terminal_inner_eval = evaluate_inner(model, inner_plan, case_to_fold, metadata, cache, device, batch_size=min(2, batch_size))
    repeat_inner_eval = evaluate_inner(model, inner_plan, case_to_fold, metadata, cache, device, batch_size=min(2, batch_size))
    inner_repeat_exact = terminal_inner_eval == repeat_inner_eval
    write_json(runtime_root / "inner_evaluation_repeat_receipt.json", {"status": "PASS" if inner_repeat_exact else "NEEDS_REPAIR", "first": terminal_inner_eval, "second": repeat_inner_eval})
    save_care_dg_checkpoint(
        last_path,
        model,
        optimizer,
        total_steps,
        {"fold": fold, "stage": "terminal", "inner_loss": float(terminal_inner_eval["loss"]), "inner_eval": terminal_inner_eval, "outer_val_used_for_selection": False},
        scaler=scaler,
        local_rng=rng,
        stage="terminal",
        local_step=0,
        total_step=total_steps,
        fixed_inner_plan_hash=str(inner_plan["plan_sha256"]),
        hash_contract=hash_contract,
    )
    reload_model, reload_step, reload_extra = load_care_dg_checkpoint(last_path, expected_hash_contract=hash_contract)
    reload_model = reload_model.to(device)
    reload_batch = move_tensors(build_batch(train_cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=min(1, batch_size), sampler_index=sampler_index_a), device)
    with torch.no_grad():
        before_reload = model(
            reload_batch["images"],
            reload_batch["availability"],
            reload_batch["anchor_logits"],
            uncertainty=reload_batch["uncertainty"],
            myocardium_support=reload_batch["myocardium_support"],
            edema_support=reload_batch["edema_support"],
            distance_to_myocardium=reload_batch["distance_to_myocardium"],
            t2_present=reload_batch["t2_present"],
            strict_inputs=True,
            anchor_value_kind=reload_batch["anchor_value_kind"],
        )["final_logits"].detach().cpu()
        after_reload = reload_model(
            reload_batch["images"],
            reload_batch["availability"],
            reload_batch["anchor_logits"],
            uncertainty=reload_batch["uncertainty"],
            myocardium_support=reload_batch["myocardium_support"],
            edema_support=reload_batch["edema_support"],
            distance_to_myocardium=reload_batch["distance_to_myocardium"],
            t2_present=reload_batch["t2_present"],
            strict_inputs=True,
            anchor_value_kind=reload_batch["anchor_value_kind"],
        )["final_logits"].detach().cpu()
    checkpoint_reload = {
        "status": "PASS" if reload_step == total_steps and float((before_reload - after_reload).abs().max()) <= 1e-6 and inner_repeat_exact else "NEEDS_REPAIR",
        "reload_step": reload_step,
        "expected_step": total_steps,
        "extra": checkpoint_extra_summary(reload_extra),
        "max_abs_final_logits_delta": float((before_reload - after_reload).abs().max()),
        "inner_evaluation_repeat_exact": bool(inner_repeat_exact),
        "fixed_inner_evaluation_plan_sha256": inner_plan["plan_sha256"],
    }
    if checkpoint_reload["status"] != "PASS":
        raise RuntimeError(f"checkpoint write/reload parity failed for fold={fold}: {checkpoint_reload}")
    terminal_lrs = current_group_lrs(optimizer)
    last_row = {"fold": fold, "stage": "last", "step": total_steps, "local_step": 0, "representation_lr": terminal_lrs.get("representation_group"), "pathology_lr": terminal_lrs.get("pathology_group"), "weight_decay": args.weight_decay, "resolved_training_contract_sha256": resolved_contract["resolved_training_contract_sha256"], "checkpoint_path": str(last_path), "checkpoint_sha256": sha256_file(last_path), "inner_loss": float(terminal_inner_eval["loss"]), "inner_plan_sha256": inner_plan["plan_sha256"], "selection_population": "terminal_last_fixed_inner_plan", "outer_val_used": False}
    ckpt_rows.append(last_row)
    if best_path is None:
        best_path = last_path; best_inner = float(log_rows[-1]["loss"]) if log_rows else math.inf
    best_alias = ckpt_dir / "checkpoint_best.pt"
    best_alias.write_bytes(best_path.read_bytes())
    best_row = {"fold": fold, "stage": "best", "step": total_steps, "local_step": 0, "representation_lr": terminal_lrs.get("representation_group"), "pathology_lr": terminal_lrs.get("pathology_group"), "weight_decay": args.weight_decay, "resolved_training_contract_sha256": resolved_contract["resolved_training_contract_sha256"], "checkpoint_path": str(best_alias), "checkpoint_sha256": sha256_file(best_alias), "inner_loss": best_inner, "inner_plan_sha256": inner_plan["plan_sha256"], "selection_population": "fixed_train_side_complete_inner_plan", "outer_val_used": False}
    ckpt_rows.append(best_row)
    write_csv(runtime_root / "checkpoint_manifest.csv", ckpt_rows)
    receipt = {"fold": fold, "status": "PASS", "runtime_kind": runtime_kind, "runtime_label": runtime_kind, "preflight_only": preflight_only, "formal_training_credit": 0 if preflight_only else total_steps, "validate_w0_status": "PASS", "expected_stage_a_steps": stage_a_steps, "expected_stage_b_steps": stage_b_steps, "actual_optimizer_steps": total_steps, "stage_a_representation_lr": args.lr_stage_a_representation, "stage_a_pathology_lr": args.lr_stage_a_pathology, "stage_b_representation_lr": args.lr_stage_b_representation, "stage_b_pathology_lr": args.lr_stage_b_pathology, "grad_clip_norm": float(args.grad_clip_norm), "amp_dtype": str(args.amp_dtype), "optimizer_group_lrs_terminal": current_group_lrs(optimizer), "optimizer_group_weight_decays_terminal": current_group_weight_decays(optimizer), "outer_train_cases": len(outer_train), "outer_val_cases": len(outer_val), "actual_train_cases": len(train_cases), "inner_train_cases": len(train_cases), "inner_selection_cases": len(inner_select), "complete_trimodal_train_cases": len(complete_train_cases), "complete_inner_selection_cases": len(split_contract["complete_inner_select_cases"]), "t2_reliable_train_cases": sum(bool(metadata[c].t2_present) for c in train_cases), "best_checkpoint": str(best_alias), "last_checkpoint": str(last_path), "best_inner_loss": best_inner, "outer_val_used_for_checkpoint_selection": False, "stage_a_case_ids_sha256": split_contract["sha256"]["actual_train"], "stage_b_case_ids_sha256": split_contract["sha256"]["complete_actual_train"], "inner_select_case_ids_sha256": split_contract["sha256"]["inner_select"], "complete_inner_select_case_ids_sha256": split_contract["sha256"]["complete_inner_select"], "fixed_inner_objective": "fixed_complete_inner_select_no_aug_patch_loss", "fixed_inner_evaluation_plan_path": str(runtime_root / "inner_evaluation_plan.json"), "fixed_inner_evaluation_plan_sha256": inner_plan["plan_sha256"], "inner_evaluation_repeat_exact": bool(inner_repeat_exact), "resolved_training_contract_path": str(runtime_root / "resolved_training_contract.json"), "resolved_training_contract_sha256": resolved_contract["resolved_training_contract_sha256"], "anchor_value_kind": "log_probabilities", "support_map_contract": "myocardium_union_labels_1_4_5_excludes_lv_rv_2_3_soft_shells_6mm_10mm", "checkpoint_write_reload": checkpoint_reload, "margin_cap_audit": cap_audit, "sampler_quota_audit_stage_a": sampler_audit_a, "sampler_quota_audit_stage_b": sampler_audit_b, "sampler_quota_audit": sampler_audit_a, "random_negative_semantics_audit_stage_a": {k: v for k, v in random_negative_audit_a.items() if k != "records"}, "random_negative_semantics_audit_stage_b": ({k: v for k, v in random_negative_audit_b.items() if k != "records"} if random_negative_audit_b else None), "hash_contract": hash_contract, "source_hashes": source_hashes(), "elapsed_seconds": round(time.time() - started, 1), "terminal_time_utc": now_utc(), "curve_rows": len(log_rows), "checkpoint_rows": len(ckpt_rows)}
    write_json(runtime_root / "fold_training_receipt.json", receipt)
    if preflight_only:
        write_json(runtime_root / "preflight_validator_report.json", {
            "created_at_utc": now_utc(),
            "status": "PASS",
            "formal_training_credit": 0,
            "checked": [
                "validate_w0",
                "oof_anchor_loading",
                "probability_to_log_probability",
                "soft_support_maps",
                "effective_sampler_audit_stage_A",
                "effective_sampler_audit_stage_B",
                "fixed_inner_checkpoint_evaluation",
                "margin_cap_train_only",
                "stage_A_one_optimizer_step",
                "stage_B_one_optimizer_step",
                "stage_B_group_learning_rates",
                "scar_priority_composition_anchor_edema_scar_argmax",
                "random_negative_semantics_audit_stage_A",
                "random_negative_semantics_audit_stage_B",
                "resolved_training_contract_hash_bound",
                "checkpoint_write_reload_resume_state",
                "receipt",
            ],
            "receipt_path": str(receipt_path),
        })
    return receipt


def write_training_manifests(result_root: Path, receipts: list[dict[str, Any]]) -> None:
    write_json(result_root / "training_contract.json", {"created_at_utc": now_utc(), **contract(), "formal_training_credit_requires_preflight_false": True})
    fold_rows = []
    checkpoint_rows = []
    activation_rows = []
    for rec in receipts:
        fold_rows.append(rec)
        runtime_kind = str(rec.get("runtime_kind") or ("preflight" if rec.get("preflight_only") else "formal"))
        ckpt_manifest = result_root / "runtime" / runtime_kind / f"fold{rec['fold']}" / "checkpoint_manifest.csv"
        if ckpt_manifest.exists():
            with ckpt_manifest.open(newline="", encoding="utf-8") as f:
                checkpoint_rows.extend(csv.DictReader(f))
        curve = result_root / "runtime" / runtime_kind / f"fold{rec['fold']}" / "training_curve.csv"
        if curve.exists():
            rows = list(csv.DictReader(curve.open(newline="", encoding="utf-8")))
            last = rows[-1] if rows else {}
            activation_rows.append({"fold": rec["fold"], "status": "PASS" if float(last.get("changed_voxels", 0) or 0) > 0 and float(last.get("scar_delta_std", 0) or 0) > 0 and float(last.get("edema_delta_std", 0) or 0) > 0 else "NEEDS_REPAIR", "changed_voxels_last_logged": last.get("changed_voxels", ""), "scar_delta_std_last_logged": last.get("scar_delta_std", ""), "edema_delta_std_last_logged": last.get("edema_delta_std", "")})
    write_csv(result_root / "fold_training_manifest.csv", fold_rows)
    write_csv(result_root / "fold_checkpoint_manifest.csv", checkpoint_rows)
    write_csv(result_root / "fold_mechanism_activation.csv", activation_rows)
    write_csv(result_root / "training_terminal_accounting.csv", [{"fold": r["fold"], "state": r["status"], "exit_code": 0, "runtime_seconds": r["elapsed_seconds"], "actual_optimizer_steps": r["actual_optimizer_steps"], "preflight_only": r["preflight_only"]} for r in receipts])
    expected = {int(r["fold"]): int(r["actual_optimizer_steps"]) for r in receipts if not r.get("preflight_only")}
    undertrained = [f for f in range(5) if expected.get(f) != 8000]
    write_json(result_root / "undertraining_guard.json", {"created_at_utc": now_utc(), "status": "PASS" if not undertrained and len(expected) == 5 else "NEEDS_REPAIR", "undertrained_folds": undertrained, "actual_steps_by_fold": expected})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--unit-smoke", action="store_true")
    parser.add_argument("--formal-train", action="store_true")
    parser.add_argument("--folds", nargs="*", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--seed", type=int, default=20260727)
    parser.add_argument("--stage-a-steps", type=int, default=5000)
    parser.add_argument("--stage-b-steps", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--preflight-steps", type=int, default=0)
    parser.add_argument("--gate-a-r2-preflight", action="store_true")
    parser.add_argument("--gate-a-r3-preflight", action="store_true")
    parser.add_argument("--gate-b-scar-priority-preflight", action="store_true")
    parser.add_argument("--runtime-label", default="repaired_formal_scar_priority")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--amp", action="store_true", default=True)
    parser.add_argument("--cache-cases", type=int, default=48)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--lr-stage-a-representation", type=float, default=STAGE_A_REPRESENTATION_LR)
    parser.add_argument("--lr-stage-a-pathology", type=float, default=STAGE_A_PATHOLOGY_LR)
    parser.add_argument("--lr-stage-b-representation", type=float, default=STAGE_B_REPRESENTATION_LR)
    parser.add_argument("--lr-stage-b-pathology", type=float, default=STAGE_B_PATHOLOGY_LR)
    parser.add_argument("--weight-decay", type=float, default=WEIGHT_DECAY)
    parser.add_argument("--grad-clip-norm", type=float, default=GRAD_CLIP_NORM)
    parser.add_argument("--amp-dtype", choices=["bfloat16", "float16"], default=AMP_DTYPE)
    parser.add_argument("--encoder-channels", nargs=3, type=int, default=[32, 64, 96])
    parser.add_argument("--context-channels", type=int, default=16)
    args = parser.parse_args()
    if args.gate_a_r3_preflight and args.runtime_label != "gate_a_r3_preflight":
        parser.error("--gate-a-r3-preflight requires --runtime-label gate_a_r3_preflight")
    if args.gate_b_scar_priority_preflight and args.runtime_label != "gate_b_scar_priority_preflight":
        parser.error("--gate-b-scar-priority-preflight requires --runtime-label gate_b_scar_priority_preflight")
    if args.print_contract:
        print(json.dumps(contract(), indent=2, sort_keys=True)); return 0
    if args.unit_smoke:
        print(json.dumps(unit_smoke(), indent=2, sort_keys=True)); return 0
    if not args.formal_train:
        parser.error("expected --print-contract, --unit-smoke, or --formal-train")
    result_root = args.result_root if args.result_root.is_absolute() else REPO_ROOT / args.result_root
    validate_w0(result_root)
    result_root.mkdir(parents=True, exist_ok=True)
    receipts = []
    for fold in args.folds:
        receipts.append(train_fold(int(fold), args, result_root))
    write_training_manifests(result_root, receipts)
    print(json.dumps({"status": "PASS", "folds": args.folds, "preflight_only": bool(args.preflight_steps or args.gate_a_r2_preflight or args.gate_a_r3_preflight or args.gate_b_scar_priority_preflight), "receipts": receipts}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
