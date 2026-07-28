"""CARE-DPR data helpers built on the verified CARE-DG fold0 assets."""

from __future__ import annotations

import random
from typing import Any

import numpy as np

from scripts.training.run_care_dg import (
    CaseCache,
    PATCH_SHAPE,
    _batch_from_centers,
    actionable_target_mask,
    build_sampler_index as build_dg_sampler_index,
    crop_pad,
    deterministic_inner_split,
    load_splits,
    sha256_case_ids,
    stable_json_sha256,
)
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL


DPR_SAMPLER_PATTERN = (
    "scar_fn",
    "scar_fp",
    "scar_hard_negative",
    "scar_pathology",
    "edema_fn",
    "edema_fp",
    "edema_hard_negative",
    "edema_pathology",
)


def dpr_target_masks(record: dict[str, np.ndarray], t2_present: bool) -> dict[str, np.ndarray]:
    labels = record["labels"]
    anchor = record["anchor_mask"]
    scar_gt = labels == SCAR_CHANNEL
    scar_pred = anchor == SCAR_CHANNEL
    zone_gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    zone_pred = (anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)
    support = record.get("myocardium_support", np.ones((1, *labels.shape), dtype=np.float32))[0] > 0.1
    edema_support = record.get("edema_support", np.ones((1, *labels.shape), dtype=np.float32))[0] > 0.1
    bright = np.zeros_like(labels, dtype=bool)
    for channel in range(record["images"].shape[0]):
        image = record["images"][channel]
        bright |= image > np.quantile(image, 0.95)
    blood_pool = np.isin(anchor, [2, 3])
    outside_support = ~support
    remote_fp = (scar_pred | zone_pred) & ~zone_gt & outside_support
    high_intensity_no_lesion = bright & ~zone_gt
    scar_hard_negative = (blood_pool | outside_support | remote_fp | high_intensity_no_lesion) & ~scar_gt
    edema_hard_negative = (blood_pool | outside_support | remote_fp | high_intensity_no_lesion) & ~zone_gt if t2_present else np.zeros_like(labels, dtype=bool)
    return {
        "scar_fn": scar_gt & ~scar_pred & support,
        "scar_fp": ~scar_gt & scar_pred & support,
        "scar_hard_negative": scar_hard_negative,
        "scar_pathology": scar_gt & support,
        "edema_fn": (zone_gt & ~zone_pred & edema_support) if t2_present else np.zeros_like(labels, dtype=bool),
        "edema_fp": (~zone_gt & zone_pred & edema_support) if t2_present else np.zeros_like(labels, dtype=bool),
        "edema_hard_negative": edema_hard_negative,
        "edema_pathology": (zone_gt & edema_support) if t2_present else np.zeros_like(labels, dtype=bool),
    }


def build_dpr_sampler_index(case_ids: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, *, stage: str) -> dict[str, Any]:
    active_cases: list[str] = []
    eligible: dict[str, list[str]] = {mode: [] for mode in DPR_SAMPLER_PATTERN}
    target_counts: dict[str, dict[str, int]] = {}
    for case_id in sorted(case_ids):
        meta = metadata[case_id]
        if stage == "B" and meta.modality_group != "C0+LGE+T2":
            continue
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        masks = dpr_target_masks(rec, bool(meta.t2_present))
        active_cases.append(case_id)
        target_counts[case_id] = {k: int(np.count_nonzero(v)) for k, v in masks.items()}
        for mode in DPR_SAMPLER_PATTERN:
            if target_counts[case_id][mode] > 0:
                eligible[mode].append(case_id)
    if not active_cases:
        raise ValueError(f"CARE_DPR_EMPTY_STAGE:{stage}")
    empty = [mode for mode, pool in eligible.items() if not pool]
    if empty:
        raise ValueError(f"CARE_DPR_EMPTY_SAMPLER_POOL:{stage}:{','.join(empty)}")
    payload = {
        "stage": stage,
        "sampler_pattern": list(DPR_SAMPLER_PATTERN),
        "case_ids": active_cases,
        "case_ids_sha256": sha256_case_ids(active_cases),
        "eligible_counts": {mode: len(pool) for mode, pool in eligible.items()},
        "target_count_totals": {mode: sum(target_counts[c][mode] for c in active_cases) for mode in DPR_SAMPLER_PATTERN},
        "no_t2_excluded_from_edema_slots": True,
        "hard_negative_semantics": ["blood_pool", "outside_support_bright_islands", "remote_anchor_fp", "high_intensity_no_lesion"],
    }
    payload["sampler_index_sha256"] = stable_json_sha256(payload)
    return {**payload, "eligible": eligible, "target_counts_by_case": target_counts}


def choose_dpr_center(record: dict[str, np.ndarray], rng: random.Random, *, mode: str, t2_present: bool) -> tuple[tuple[int, int, int], int]:
    target = dpr_target_masks(record, t2_present)[mode]
    coords = np.argwhere(target)
    if not coords.size:
        raise ValueError(f"CARE_DPR_EMPTY_TARGET:{mode}")
    z, y, x = coords[rng.randrange(len(coords))]
    jitter = (rng.randint(-16, 16), rng.randint(-32, 32), rng.randint(-32, 32))
    center = (
        max(0, min(record["labels"].shape[0] - 1, int(z) + jitter[0])),
        max(0, min(record["labels"].shape[1] - 1, int(y) + jitter[1])),
        max(0, min(record["labels"].shape[2] - 1, int(x) + jitter[2])),
    )
    count = int(crop_pad(target.astype(np.uint8)[None], center, PATCH_SHAPE, fill=0)[0].sum())
    if count <= 0:
        center = (int(z), int(y), int(x))
        count = int(crop_pad(target.astype(np.uint8)[None], center, PATCH_SHAPE, fill=0)[0].sum())
    return center, count


def build_dpr_batch(
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
    index = sampler_index or build_dpr_sampler_index(case_ids, case_to_fold, metadata, cache, stage=stage)
    samples: list[dict[str, Any]] = []
    for mode in [DPR_SAMPLER_PATTERN[i % len(DPR_SAMPLER_PATTERN)] for i in range(batch_size)]:
        pool = list(index["eligible"][mode])
        case_id = rng.choice(pool)
        meta = metadata[case_id]
        record = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        center, count = choose_dpr_center(record, rng, mode=mode, t2_present=bool(meta.t2_present))
        samples.append(
            {
                "requested_mode": mode,
                "effective_mode": mode,
                "case_id": case_id,
                "center_zyx": list(center),
                "target_voxel_count_in_patch": int(count),
                "fallback_reason": "",
            }
        )
    batch = _batch_from_centers(samples, case_to_fold, metadata, cache)
    batch["dpr_sampler_pattern"] = list(DPR_SAMPLER_PATTERN)
    return batch


__all__ = [
    "CaseCache",
    "PATCH_SHAPE",
    "DPR_SAMPLER_PATTERN",
    "actionable_target_mask",
    "build_dg_sampler_index",
    "build_dpr_batch",
    "build_dpr_sampler_index",
    "deterministic_inner_split",
    "dpr_target_masks",
    "load_splits",
]
