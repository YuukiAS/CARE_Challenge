"""CARE-DPR data helpers built on the verified CARE-DG fold0 assets."""

from __future__ import annotations

import random
from typing import Any

import numpy as np
from scipy import ndimage as ndi

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

HARD_NEGATIVE_SUBTYPES = (
    "blood_pool",
    "outside_support_bright_island",
    "remote_anchor_fp",
    "high_intensity_nonlesion",
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
    outside_support_bright_island = outside_support & bright
    remote_fp = (scar_pred | zone_pred) & ~zone_gt
    high_intensity_no_lesion = bright & ~zone_gt
    scar_hard_negative = (blood_pool | outside_support_bright_island | remote_fp | high_intensity_no_lesion) & ~scar_gt
    edema_hard_negative = (blood_pool | outside_support_bright_island | remote_fp | high_intensity_no_lesion) & ~zone_gt if t2_present else np.zeros_like(labels, dtype=bool)
    return {
        "scar_fn": scar_gt & ~scar_pred & support,
        "scar_fp": ~scar_gt & scar_pred & support,
        "scar_hard_negative": scar_hard_negative,
        "scar_pathology": scar_gt & support,
        "edema_fn": (zone_gt & ~zone_pred & edema_support) if t2_present else np.zeros_like(labels, dtype=bool),
        "edema_fp": (~zone_gt & zone_pred & edema_support) if t2_present else np.zeros_like(labels, dtype=bool),
        "edema_hard_negative": edema_hard_negative,
        "edema_pathology": (zone_gt & edema_support) if t2_present else np.zeros_like(labels, dtype=bool),
        "hard_negative_blood_pool": blood_pool,
        "hard_negative_outside_support_bright_island": outside_support_bright_island,
        "hard_negative_remote_anchor_fp": remote_fp,
        "hard_negative_high_intensity_nonlesion": high_intensity_no_lesion,
    }



def hard_negative_subtype_mask(record: dict[str, np.ndarray], t2_present: bool, *, pathology: str, subtype: str) -> np.ndarray:
    masks = dpr_target_masks(record, t2_present)
    if subtype not in HARD_NEGATIVE_SUBTYPES:
        raise ValueError(f"CARE_DPR_UNKNOWN_HARD_NEGATIVE_SUBTYPE:{subtype}")
    labels = record["labels"]
    key = f"hard_negative_{subtype}"
    if pathology == "scar":
        return (masks[key] & (labels != SCAR_CHANNEL)).astype(bool)
    if not t2_present:
        return np.zeros_like(labels, dtype=bool)
    zone_gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    return (masks[key] & ~zone_gt).astype(bool)


def distance_to_reliable_gt(record: dict[str, np.ndarray], *, pathology: str, t2_present: bool) -> np.ndarray:
    labels = record["labels"]
    if pathology == "scar":
        gt = labels == SCAR_CHANNEL
    elif t2_present:
        gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    else:
        gt = np.zeros_like(labels, dtype=bool)
    if np.any(gt):
        return ndi.distance_transform_edt(~gt).astype(np.float32)[None]
    return np.full((1, *labels.shape), 99.0, dtype=np.float32)

def build_dpr_sampler_index(case_ids: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, *, stage: str) -> dict[str, Any]:
    active_cases: list[str] = []
    eligible: dict[str, list[str]] = {mode: [] for mode in DPR_SAMPLER_PATTERN}
    hard_subtype_eligible: dict[str, dict[str, list[str]]] = {"scar": {sub: [] for sub in HARD_NEGATIVE_SUBTYPES}, "edema_zone": {sub: [] for sub in HARD_NEGATIVE_SUBTYPES}}
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
        for subtype in HARD_NEGATIVE_SUBTYPES:
            if int(np.count_nonzero(hard_negative_subtype_mask(rec, bool(meta.t2_present), pathology="scar", subtype=subtype))) > 0:
                hard_subtype_eligible["scar"][subtype].append(case_id)
            if int(np.count_nonzero(hard_negative_subtype_mask(rec, bool(meta.t2_present), pathology="edema_zone", subtype=subtype))) > 0:
                hard_subtype_eligible["edema_zone"][subtype].append(case_id)
    if not active_cases:
        raise ValueError(f"CARE_DPR_EMPTY_STAGE:{stage}")
    empty = [mode for mode, pool in eligible.items() if not pool]
    if empty:
        raise ValueError(f"CARE_DPR_EMPTY_SAMPLER_POOL:{stage}:{','.join(empty)}")
    empty_subtypes = [f"{pathology}:{subtype}" for pathology, pools in hard_subtype_eligible.items() for subtype, pool in pools.items() if not pool]
    if empty_subtypes:
        raise ValueError(f"CARE_DPR_EMPTY_HARD_NEGATIVE_SUBTYPE_POOL:{stage}:{','.join(empty_subtypes)}")
    payload = {
        "stage": stage,
        "sampler_pattern": list(DPR_SAMPLER_PATTERN),
        "case_ids": active_cases,
        "case_ids_sha256": sha256_case_ids(active_cases),
        "eligible_counts": {mode: len(pool) for mode, pool in eligible.items()},
        "target_count_totals": {mode: sum(target_counts[c][mode] for c in active_cases) for mode in DPR_SAMPLER_PATTERN},
        "no_t2_excluded_from_edema_slots": True,
        "hard_negative_semantics": list(HARD_NEGATIVE_SUBTYPES),
        "hard_negative_subtype_eligible_counts": {pathology: {subtype: len(pool) for subtype, pool in pools.items()} for pathology, pools in hard_subtype_eligible.items()},
        "outside_support_voxel_pool_is_not_primary_hard_negative": True,
    }
    payload["sampler_index_sha256"] = stable_json_sha256(payload)
    return {**payload, "eligible": eligible, "hard_negative_subtype_eligible": hard_subtype_eligible, "target_counts_by_case": target_counts}




def sampler_slots_for_cursor(cursor: int, batch_size: int) -> tuple[list[str], int]:
    start = int(cursor) % len(DPR_SAMPLER_PATTERN)
    slots = [DPR_SAMPLER_PATTERN[(start + i) % len(DPR_SAMPLER_PATTERN)] for i in range(int(batch_size))]
    return slots, (start + int(batch_size)) % len(DPR_SAMPLER_PATTERN)

def hard_negative_subtype_counts(record: dict[str, np.ndarray], t2_present: bool, *, pathology: str, center: tuple[int, int, int]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for subtype in HARD_NEGATIVE_SUBTYPES:
        cropped = crop_pad(hard_negative_subtype_mask(record, t2_present, pathology=pathology, subtype=subtype).astype(np.uint8)[None], center, PATCH_SHAPE, fill=0)[0] > 0
        counts[subtype] = int(np.count_nonzero(cropped))
    return counts

def choose_dpr_center(record: dict[str, np.ndarray], rng: random.Random, *, mode: str, t2_present: bool, hard_negative_subtype: str | None = None) -> tuple[tuple[int, int, int], int]:
    if hard_negative_subtype:
        pathology = "edema_zone" if mode.startswith("edema_") else "scar"
        target = hard_negative_subtype_mask(record, t2_present, pathology=pathology, subtype=hard_negative_subtype)
    else:
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
    sampler_slot_cursor: int = 0,
    hard_negative_subtype_cursor: dict[str, int] | None = None,
) -> dict[str, Any]:
    index = sampler_index or build_dpr_sampler_index(case_ids, case_to_fold, metadata, cache, stage=stage)
    samples: list[dict[str, Any]] = []
    cursor = int(sampler_slot_cursor) % len(DPR_SAMPLER_PATTERN)
    subtype_cursor = {"scar": 0, "edema_zone": 0}
    if hard_negative_subtype_cursor:
        subtype_cursor.update({k: int(v) for k, v in hard_negative_subtype_cursor.items() if k in subtype_cursor})
    for i in range(batch_size):
        mode = sampler_slots_for_cursor(cursor, batch_size)[0][i]
        pathology = "edema_zone" if mode.startswith("edema_") else "scar"
        requested_subtype = ""
        if "hard_negative" in mode:
            requested_subtype = HARD_NEGATIVE_SUBTYPES[subtype_cursor[pathology] % len(HARD_NEGATIVE_SUBTYPES)]
            subtype_cursor[pathology] = (subtype_cursor[pathology] + 1) % len(HARD_NEGATIVE_SUBTYPES)
            pool = list(index["hard_negative_subtype_eligible"][pathology][requested_subtype])
        else:
            pool = list(index["eligible"][mode])
        if not pool:
            raise ValueError(f"CARE_DPR_EMPTY_REQUESTED_SUBTYPE_POOL:{mode}:{requested_subtype}")
        case_id = rng.choice(pool)
        meta = metadata[case_id]
        record = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        center, count = choose_dpr_center(record, rng, mode=mode, t2_present=bool(meta.t2_present), hard_negative_subtype=requested_subtype or None)
        hard_counts = hard_negative_subtype_counts(record, bool(meta.t2_present), pathology=pathology, center=center) if "hard_negative" in mode else {k: 0 for k in HARD_NEGATIVE_SUBTYPES}
        samples.append(
            {
                "sampler_slot_index": (cursor + i) % len(DPR_SAMPLER_PATTERN),
                "requested_mode": mode,
                "effective_mode": mode,
                "case_id": case_id,
                "center_zyx": list(center),
                "target_voxel_count_in_patch": int(count),
                "t2_present": bool(meta.t2_present),
                "hard_negative_subtype": requested_subtype,
                "hard_negative_subtype_counts": hard_counts,
                "fallback_reason": "",
            }
        )
    batch = _batch_from_centers(samples, case_to_fold, metadata, cache)
    primary_masks = []
    distance_to_gt = []
    candidate_types = []
    candidate_pathologies = []
    for sample in samples:
        case_id = str(sample["case_id"])
        meta = metadata[case_id]
        record = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        center = tuple(int(v) for v in sample["center_zyx"])
        mode = str(sample["requested_mode"])
        pathology = "edema_zone" if mode.startswith("edema_") else "scar"
        if "hard_negative" in mode:
            mask = hard_negative_subtype_mask(record, bool(meta.t2_present), pathology=pathology, subtype=str(sample["hard_negative_subtype"]))
            candidate_type = "REVISE_FP"
        else:
            mask = dpr_target_masks(record, bool(meta.t2_present))[mode]
            candidate_type = "REVISE_FP" if mode.endswith("_fp") else "ADD_FN"
        primary_masks.append(crop_pad(mask.astype(np.uint8)[None], center, PATCH_SHAPE, fill=0).astype(np.float32))
        distance_to_gt.append(crop_pad(distance_to_reliable_gt(record, pathology=pathology, t2_present=bool(meta.t2_present)), center, PATCH_SHAPE, fill=99.0).astype(np.float32))
        candidate_types.append(candidate_type)
        candidate_pathologies.append(pathology)
    batch["primary_candidate_mask"] = __import__("torch").from_numpy(np.stack(primary_masks)).float()
    batch["primary_candidate_type"] = candidate_types
    batch["primary_candidate_pathology"] = candidate_pathologies
    batch["distance_to_reliable_gt"] = __import__("torch").from_numpy(np.stack(distance_to_gt)).float()
    batch["dpr_sampler_pattern"] = list(DPR_SAMPLER_PATTERN)
    batch["dpr_sampler_samples"] = samples
    batch["sampler_slot_cursor_before"] = cursor
    batch["sampler_slot_cursor_after"] = (cursor + int(batch_size)) % len(DPR_SAMPLER_PATTERN)
    batch["hard_negative_subtype_cursor_before"] = dict(hard_negative_subtype_cursor or {"scar": 0, "edema_zone": 0})
    batch["hard_negative_subtype_cursor_after"] = subtype_cursor
    return batch


__all__ = [
    "CaseCache",
    "PATCH_SHAPE",
    "DPR_SAMPLER_PATTERN",
    "HARD_NEGATIVE_SUBTYPES",
    "actionable_target_mask",
    "build_dg_sampler_index",
    "build_dpr_batch",
    "build_dpr_sampler_index",
    "hard_negative_subtype_counts",
    "hard_negative_subtype_mask",
    "distance_to_reliable_gt",
    "deterministic_inner_split",
    "dpr_target_masks",
    "load_splits",
    "sampler_slots_for_cursor",
]
