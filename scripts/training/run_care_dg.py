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
PROTECTED_RUNTIME_LABELS = {"formal"}


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
    pattern = ["error_fn", "error_fp", "error_fn", "error_fp", "pathology", "pathology", "random", "random"]
    return [pattern[i % len(pattern)] for i in range(batch_size)]


def build_batch(case_ids: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, rng: random.Random, *, stage: str, batch_size: int) -> dict[str, Any]:
    weights = []
    for case_id in case_ids:
        meta = metadata[case_id]
        if stage == "B" and meta.modality_group != "C0+LGE+T2":
            weights.append(0.0)
        else:
            weights.append(4.0 if meta.modality_group == "C0+LGE+T2" else 1.0)
    active = [(c, w) for c, w in zip(case_ids, weights) if w > 0]
    if not active:
        raise ValueError(f"no active cases for stage {stage}")
    population = [c for c, _w in active]
    pop_weights = [w for _c, w in active]
    images = []; labels = []; anchors = []; availability = []; t2 = []
    uncertainty = []; myocardium_support = []; edema_support = []; distance = []
    modes = []
    case_trace = []
    for mode in sampler_modes(batch_size):
        case_id = rng.choices(population, weights=pop_weights, k=1)[0]
        meta = metadata[case_id]
        record = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        center = choose_center(record, rng, mode, bool(meta.t2_present))
        images.append(crop_pad(record["images"], center, PATCH_SHAPE, fill=0.0))
        labels.append(crop_pad(record["labels"][None], center, PATCH_SHAPE, fill=0)[0])
        anchors.append(crop_pad(record["anchor_logits"], center, PATCH_SHAPE, fill=-12.0))
        uncertainty.append(crop_pad(record["uncertainty"], center, PATCH_SHAPE, fill=1.0))
        myocardium_support.append(crop_pad(record["myocardium_support"], center, PATCH_SHAPE, fill=0.0))
        edema_support.append(crop_pad(record["edema_support"], center, PATCH_SHAPE, fill=0.0))
        distance.append(crop_pad(record["distance_to_myocardium"], center, PATCH_SHAPE, fill=99.0))
        availability.append(record["availability"])
        t2.append(1.0 if meta.t2_present else 0.0)
        modes.append(mode)
        case_trace.append(case_id)
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
        "sample_modes": modes,
        "case_trace": case_trace,
    }


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


def sampler_quota_audit(case_ids: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, *, stage: str, batch_size: int, samples: int = 1000, seed: int = 20260727) -> dict[str, Any]:
    rng = random.Random(seed)
    counts = {"error_fn": 0, "error_fp": 0, "pathology": 0, "random": 0}
    batches = math.ceil(samples / batch_size)
    seen = 0
    for _ in range(batches):
        batch = build_batch(case_ids, case_to_fold, metadata, cache, rng, stage=stage, batch_size=batch_size)
        for mode in batch["sample_modes"]:
            if seen >= samples:
                break
            counts[mode] += 1
            seen += 1
    fractions = {k: v / float(samples) for k, v in counts.items()}
    status = "PASS" if abs((fractions["error_fn"] + fractions["error_fp"]) - 0.5) <= 0.02 and abs(fractions["pathology"] - 0.25) <= 0.02 and abs(fractions["random"] - 0.25) <= 0.02 and abs(fractions["error_fn"] - fractions["error_fp"]) <= 0.02 else "NEEDS_REPAIR"
    return {"status": status, "samples": samples, "counts": counts, "fractions": fractions, "stage": stage, "batch_size": batch_size}


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
        "tests/care_dg/test_care_dg_model.py",
    ]
    return {p: sha256_file(REPO_ROOT / p) for p in paths if (REPO_ROOT / p).exists()}


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


def evaluate_inner(model: torch.nn.Module, case_ids: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, rng: random.Random, device: torch.device, batch_size: int) -> float:
    model.eval()
    losses = []
    with torch.no_grad():
        for _ in range(4):
            batch = build_batch(case_ids, case_to_fold, metadata, cache, rng, stage="A", batch_size=batch_size)
            batch = move_tensors(batch, device)
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
            loss, _ = care_dg_loss(out, batch["labels"], anchor_mask, t2_present=batch["t2_present"], edema_reliable=batch["t2_present"])
            losses.append(float(loss.detach().cpu()))
    model.train()
    return float(np.mean(losses)) if losses else math.inf


def contract() -> dict[str, object]:
    return {
        "method": "CARE-DG",
        "seed": 20260727,
        "folds": [0, 1, 2, 3, 4],
        "stage_a_optimizer_steps": 5000,
        "stage_b_optimizer_steps": 3000,
        "batch_size": 8,
        "patch_shape_zyx": list(PATCH_SHAPE),
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
    return {"status": "PASS", "final_logits_shape": list(out["final_logits"].shape), "scar_delta_nonconstant": bool(out["scar_delta"].std().item() > 0), "edema_delta_nonconstant": bool(out["edema_delta"].std().item() > 0)}


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
    if args.preflight_steps:
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
            and bool(receipt.get("preflight_only")) == bool(args.preflight_steps)
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
    sampler_audit = sampler_quota_audit(train_cases, case_to_fold, metadata, cache, stage="A", batch_size=max(8, batch_size), samples=1000, seed=args.seed + fold)
    write_json(runtime_root / "inner_split_manifest.json", split_contract)
    write_json(runtime_root / "sampler_quota_audit.json", sampler_audit)
    write_json(runtime_root / "margin_cap_audit.json", cap_audit)
    if sampler_audit.get("status") != "PASS":
        raise RuntimeError(f"sampler quota audit failed for fold={fold}: {sampler_audit}")
    model = build_care_dg({
        "encoder_channels": tuple(args.encoder_channels),
        "context_channels": args.context_channels,
        "scar_margin_cap": float(cap_audit["scar"]["cap"]),
        "edema_margin_cap": float(cap_audit["edema_zone"]["cap"]),
    }).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr_stage_a, weight_decay=args.weight_decay)
    scaler = GradScaler("cuda", enabled=bool(args.amp and device.type == "cuda"))
    best_inner = math.inf; best_path = None
    started = time.time(); total_steps = 0
    resume_step = 0
    if args.resume and not args.preflight_steps:
        step_ckpts = sorted(ckpt_dir.glob("checkpoint_step*.pt"))
        if step_ckpts:
            resume_ckpt = step_ckpts[-1]
            model, resume_step, _extra = load_care_dg_checkpoint(resume_ckpt, model=model, optimizer=optimizer)
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
    stage_specs = [("A", stage_a_steps, train_cases, args.lr_stage_a), ("B", stage_b_steps, complete_train_cases, args.lr_stage_b)]
    for stage, steps, cases, lr in stage_specs:
        if steps <= 0:
            continue
        stage_offset = 0 if stage == "A" else stage_a_steps
        if total_steps >= stage_offset + steps:
            continue
        start_local_step = max(1, total_steps - stage_offset + 1)
        for group in optimizer.param_groups:
            group["lr"] = lr
        for local_step in range(start_local_step, steps + 1):
            total_steps += 1
            batch = build_batch(cases, case_to_fold, metadata, cache, rng, stage=stage, batch_size=batch_size)
            batch = move_tensors(batch, device)
            optimizer.zero_grad(set_to_none=True)
            with autocast("cuda", enabled=bool(args.amp and device.type == "cuda")):
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
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
            if local_step == 1 or local_step % args.log_every == 0 or local_step == steps:
                changed = int((out["final_mask"] != anchor_mask).detach().sum().cpu())
                row = {"fold": fold, "stage": stage, "local_step": local_step, "total_step": total_steps, "loss": metrics["loss"], "scar_gate": metrics["scar_gate"], "edema_gate": metrics["edema_gate"], "changed_voxels": changed, "scar_delta_std": float(out["scar_delta"].detach().std().cpu()), "edema_delta_std": float(out["edema_delta"].detach().std().cpu()), "elapsed_seconds": round(time.time() - started, 1)}
                row.update(activation_stats(out, batch["labels"], anchor_mask, batch["t2_present"]))
                log_rows.append(row)
                append_csv(runtime_root / "training_curve.csv", row, list(row.keys()))
                print(json.dumps(row), flush=True)
            if (not args.preflight_steps) and (total_steps % 1000 == 0 or (stage == "B" and local_step == steps)):
                inner_loss = evaluate_inner(model, inner_select, case_to_fold, metadata, cache, rng, device, batch_size=min(2, batch_size))
                path = ckpt_dir / f"checkpoint_step{total_steps:05d}.pt"
                save_care_dg_checkpoint(path, model, optimizer, total_steps, {"fold": fold, "stage": stage, "inner_loss": inner_loss, "outer_val_used_for_selection": False})
                row = {"fold": fold, "stage": stage, "step": total_steps, "checkpoint_path": str(path), "checkpoint_sha256": sha256_file(path), "inner_loss": inner_loss, "selection_population": "train_side_inner_split", "outer_val_used": False}
                ckpt_rows.append(row)
                if inner_loss < best_inner:
                    best_inner = inner_loss; best_path = path
    last_path = ckpt_dir / "checkpoint_last.pt"
    save_care_dg_checkpoint(last_path, model, optimizer, total_steps, {"fold": fold, "stage": "terminal", "outer_val_used_for_selection": False})
    reload_model, reload_step, reload_extra = load_care_dg_checkpoint(last_path)
    reload_model = reload_model.to(device)
    reload_batch = move_tensors(build_batch(train_cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=min(1, batch_size)), device)
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
        "status": "PASS" if reload_step == total_steps and float((before_reload - after_reload).abs().max()) <= 1e-6 else "NEEDS_REPAIR",
        "reload_step": reload_step,
        "expected_step": total_steps,
        "extra": reload_extra,
        "max_abs_final_logits_delta": float((before_reload - after_reload).abs().max()),
    }
    if checkpoint_reload["status"] != "PASS":
        raise RuntimeError(f"checkpoint write/reload parity failed for fold={fold}: {checkpoint_reload}")
    last_row = {"fold": fold, "stage": "last", "step": total_steps, "checkpoint_path": str(last_path), "checkpoint_sha256": sha256_file(last_path), "inner_loss": best_inner, "selection_population": "terminal_last", "outer_val_used": False}
    ckpt_rows.append(last_row)
    if best_path is None:
        best_path = last_path; best_inner = float(log_rows[-1]["loss"]) if log_rows else math.inf
    best_alias = ckpt_dir / "checkpoint_best.pt"
    best_alias.write_bytes(best_path.read_bytes())
    best_row = {"fold": fold, "stage": "best", "step": total_steps, "checkpoint_path": str(best_alias), "checkpoint_sha256": sha256_file(best_alias), "inner_loss": best_inner, "selection_population": "train_side_inner_split", "outer_val_used": False}
    ckpt_rows.append(best_row)
    write_csv(runtime_root / "checkpoint_manifest.csv", ckpt_rows)
    receipt = {"fold": fold, "status": "PASS", "runtime_kind": runtime_kind, "preflight_only": bool(args.preflight_steps), "formal_training_credit": 0 if args.preflight_steps else total_steps, "validate_w0_status": "PASS", "expected_stage_a_steps": stage_a_steps, "expected_stage_b_steps": stage_b_steps, "actual_optimizer_steps": total_steps, "outer_train_cases": len(outer_train), "outer_val_cases": len(outer_val), "actual_train_cases": len(train_cases), "inner_train_cases": len(train_cases), "inner_selection_cases": len(inner_select), "complete_trimodal_train_cases": len(complete_train_cases), "complete_inner_selection_cases": len(split_contract["complete_inner_select_cases"]), "t2_reliable_train_cases": sum(bool(metadata[c].t2_present) for c in train_cases), "best_checkpoint": str(best_alias), "last_checkpoint": str(last_path), "best_inner_loss": best_inner, "outer_val_used_for_checkpoint_selection": False, "stage_a_case_ids_sha256": split_contract["sha256"]["actual_train"], "stage_b_case_ids_sha256": split_contract["sha256"]["complete_actual_train"], "inner_select_case_ids_sha256": split_contract["sha256"]["inner_select"], "complete_inner_select_case_ids_sha256": split_contract["sha256"]["complete_inner_select"], "fixed_inner_objective": split_contract["fixed_inner_objective"], "anchor_value_kind": "log_probabilities", "support_map_contract": "myocardium_union_labels_1_4_5_excludes_lv_rv_2_3_soft_shells_6mm_10mm", "checkpoint_write_reload": checkpoint_reload, "margin_cap_audit": cap_audit, "sampler_quota_audit": sampler_audit, "source_hashes": source_hashes(), "elapsed_seconds": round(time.time() - started, 1), "terminal_time_utc": now_utc(), "curve_rows": len(log_rows), "checkpoint_rows": len(ckpt_rows)}
    write_json(runtime_root / "fold_training_receipt.json", receipt)
    if args.preflight_steps:
        write_json(runtime_root / "preflight_validator_report.json", {
            "created_at_utc": now_utc(),
            "status": "PASS",
            "formal_training_credit": 0,
            "checked": [
                "validate_w0",
                "oof_anchor_loading",
                "probability_to_log_probability",
                "soft_support_maps",
                "sampler",
                "margin_cap_train_only",
                "forward_backward",
                "checkpoint_write_reload",
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
    parser.add_argument("--runtime-label", default="repaired_formal")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--amp", action="store_true", default=True)
    parser.add_argument("--cache-cases", type=int, default=48)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--lr-stage-a", type=float, default=3e-4)
    parser.add_argument("--lr-stage-b", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--encoder-channels", nargs=3, type=int, default=[32, 64, 96])
    parser.add_argument("--context-channels", type=int, default=16)
    args = parser.parse_args()
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
    print(json.dumps({"status": "PASS", "folds": args.folds, "preflight_only": bool(args.preflight_steps), "receipts": receipts}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
