"""Category-aware deterministic prototype helpers for CARE-SRR-Cascade."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Mapping

import torch
from torch.nn import functional as F


SCAR_POSITIVE_CATEGORIES = ("GT_scar",)
SCAR_NEGATIVE_CATEGORIES = (
    "healthy_myo_excluding_scar_edema",
    "LV_blood",
    "RV_blood",
    "outside_GT_union",
    "OOF_anchor_remote_scar_FP",
)
EDEMA_POSITIVE_CATEGORIES = ("GT_edema_union_GT_scar",)
EDEMA_NEGATIVE_CATEGORIES = (
    "outside_GT_union",
    "LV_blood",
    "RV_blood",
    "GT_myo_distance_to_edema_zone_ge_10mm",
)
ALL_CATEGORIES = (
    *SCAR_POSITIVE_CATEGORIES,
    *SCAR_NEGATIVE_CATEGORIES,
    *EDEMA_POSITIVE_CATEGORIES,
    *EDEMA_NEGATIVE_CATEGORIES,
)
LEGACY_CATEGORY_ALIASES = {
    "scar_positive": "GT_scar",
    "scar_negative": "healthy_myo_excluding_scar_edema",
    "edema_positive": "GT_edema_union_GT_scar",
    "edema_negative": "outside_GT_union",
}


def stable_shard(case_id: str, *, repair_id: str = "SCR-R1-RC1", shards: int = 4) -> int:
    digest = hashlib.sha256(f"{case_id}|{repair_id}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % int(shards)


def _seed(case_id: str, category: str, global_seed: int) -> int:
    digest = hashlib.sha256(f"{case_id}|{category}|{int(global_seed)}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


@dataclass(frozen=True)
class CategoryPrototype:
    case_id: str
    shard: int
    pathology: str
    category: str
    polarity: str
    t2_present: bool
    vector: torch.Tensor
    provenance: dict[str, int | str | bool]


@dataclass(frozen=True)
class CasePrototypeRecord:
    case_id: str
    shard: int
    t2_present: bool
    category_vectors: dict[str, torch.Tensor] = field(default_factory=dict)
    categories: tuple[CategoryPrototype, ...] = ()
    provenance: dict[str, int | str | bool] = field(default_factory=dict)

    @property
    def scar_positive(self) -> torch.Tensor:
        return _concat_existing(self.category_vectors, SCAR_POSITIVE_CATEGORIES)

    @property
    def scar_negative(self) -> torch.Tensor:
        return _concat_existing(self.category_vectors, SCAR_NEGATIVE_CATEGORIES)

    @property
    def edema_positive(self) -> torch.Tensor:
        if not self.t2_present:
            return _empty_like_vectors(self.category_vectors)
        return _concat_existing(self.category_vectors, EDEMA_POSITIVE_CATEGORIES)

    @property
    def edema_negative(self) -> torch.Tensor:
        if not self.t2_present:
            return _empty_like_vectors(self.category_vectors)
        return _concat_existing(self.category_vectors, EDEMA_NEGATIVE_CATEGORIES)


def _empty_like_vectors(vectors: Mapping[str, torch.Tensor]) -> torch.Tensor:
    ref = next((v for v in vectors.values() if v.ndim == 2), None)
    width = int(ref.shape[1]) if ref is not None else 0
    device = ref.device if ref is not None else torch.device("cpu")
    return torch.empty((0, width), device=device)


def _concat_existing(vectors: Mapping[str, torch.Tensor], categories: tuple[str, ...]) -> torch.Tensor:
    available = [vectors[name] for name in categories if name in vectors and vectors[name].numel() > 0]
    if not available:
        return _empty_like_vectors(vectors)
    return torch.cat(available, dim=0)


def deterministic_case_category_mean(
    features: torch.Tensor,
    mask: torch.Tensor,
    *,
    case_id: str,
    category: str,
    global_seed: int = 20260725,
    cap: int = 4096,
    min_voxels: int = 32,
) -> tuple[torch.Tensor, dict[str, int | str | bool]]:
    if features.ndim != 4:
        raise ValueError("features must be [C, D, H, W]")
    flat_features = features.reshape(features.shape[0], -1).transpose(0, 1)
    flat_mask = mask.to(device=features.device, dtype=torch.bool).reshape(-1)
    indices = flat_mask.nonzero(as_tuple=False).flatten()
    available = int(indices.numel())
    accepted = min(available, int(cap))
    meta: dict[str, int | str | bool] = {
        "case_id": str(case_id),
        "category": str(category),
        "available_voxels": available,
        "accepted_voxels": accepted,
        "cap": int(cap),
        "min_voxels": int(min_voxels),
        "entered_bank": accepted >= int(min_voxels),
        "sampling": "sha256_seeded_no_replacement",
        "first_N_flat_indices": False,
    }
    if accepted < int(min_voxels):
        return features.new_empty((0, features.shape[0])), meta
    generator = torch.Generator(device="cpu")
    generator.manual_seed(_seed(str(case_id), str(category), int(global_seed)))
    perm = torch.randperm(available, generator=generator, device="cpu")[:accepted].to(device=indices.device)
    selected = indices[perm]
    vector = F.normalize(flat_features[selected].mean(dim=0, keepdim=True), dim=1)
    return vector, meta


def deterministic_case_mean(
    features: torch.Tensor,
    mask: torch.Tensor,
    *,
    cap: int = 4096,
    min_voxels: int = 32,
) -> tuple[torch.Tensor, dict[str, int | bool | str]]:
    return deterministic_case_category_mean(
        features,
        mask,
        case_id="legacy_case",
        category="legacy_category",
        cap=cap,
        min_voxels=min_voxels,
    )


def _category_role(category: str) -> tuple[str, str]:
    if category in SCAR_POSITIVE_CATEGORIES:
        return "scar", "positive"
    if category in SCAR_NEGATIVE_CATEGORIES:
        return "scar", "negative"
    if category in EDEMA_POSITIVE_CATEGORIES:
        return "edema", "positive"
    if category in EDEMA_NEGATIVE_CATEGORIES:
        return "edema", "negative"
    raise ValueError(f"unknown prototype category: {category}")


def build_case_prototype_record(
    *,
    case_id: str,
    shard: int | None = None,
    t2_present: bool,
    features: torch.Tensor,
    masks: dict[str, torch.Tensor],
    cap: int = 4096,
    min_voxels: int = 32,
    global_seed: int = 20260725,
) -> CasePrototypeRecord:
    resolved_shard = stable_shard(case_id) if shard is None else int(shard)
    category_vectors: dict[str, torch.Tensor] = {}
    category_records: list[CategoryPrototype] = []
    provenance: dict[str, int | str | bool] = {
        "case_id": str(case_id),
        "shard": resolved_shard,
        "t2_present": bool(t2_present),
        "cap": int(cap),
        "preserve_negative_categories_separately": True,
        "no_t2_edema_negative_contribution": not bool(t2_present),
    }
    for category in ALL_CATEGORIES:
        pathology, polarity = _category_role(category)
        if pathology == "edema" and not t2_present:
            provenance[f"{category}_accepted"] = 0
            continue
        mask_key = category if category in masks else next((alias for alias, target in LEGACY_CATEGORY_ALIASES.items() if target == category and alias in masks), "")
        if not mask_key:
            provenance[f"{category}_accepted"] = 0
            continue
        vector, meta = deterministic_case_category_mean(
            features,
            masks[mask_key],
            case_id=case_id,
            category=category,
            global_seed=global_seed,
            cap=cap,
            min_voxels=min_voxels,
        )
        provenance[f"{category}_accepted"] = int(meta["accepted_voxels"])
        for alias, target in LEGACY_CATEGORY_ALIASES.items():
            if target == category:
                provenance[f"{alias}_accepted"] = int(meta["accepted_voxels"])
        if vector.numel() == 0:
            continue
        category_vectors[category] = vector
        category_records.append(
            CategoryPrototype(
                case_id=str(case_id),
                shard=resolved_shard,
                pathology=pathology,
                category=category,
                polarity=polarity,
                t2_present=bool(t2_present),
                vector=vector,
                provenance=meta,
            )
        )
    return CasePrototypeRecord(
        case_id=str(case_id),
        shard=resolved_shard,
        t2_present=bool(t2_present),
        category_vectors=category_vectors,
        categories=tuple(category_records),
        provenance=provenance,
    )


def _allowed_records(
    records: list[CasePrototypeRecord],
    *,
    query_case_id: str,
    query_shard: int,
    mode: str,
) -> list[CasePrototypeRecord]:
    if mode == "train":
        return [r for r in records if r.case_id != str(query_case_id) and int(r.shard) != int(query_shard)]
    if mode in {"validation", "calibration", "audit", "official"}:
        return list(records)
    raise ValueError("mode must be train, validation, calibration, audit, or official")


def select_crossfit_prototype_bank(
    records: list[CasePrototypeRecord],
    *,
    query_case_id: str,
    query_shard: int,
    pathology: str,
    mode: str = "train",
    minimum_positive: int = 4,
    minimum_negative: int = 8,
) -> tuple[dict[str, torch.Tensor], dict[str, int | str | bool]]:
    if pathology not in {"scar", "edema"}:
        raise ValueError("pathology must be scar or edema")
    allowed = _allowed_records(records, query_case_id=query_case_id, query_shard=query_shard, mode=mode)
    positive_categories = SCAR_POSITIVE_CATEGORIES if pathology == "scar" else EDEMA_POSITIVE_CATEGORIES
    negative_categories = SCAR_NEGATIVE_CATEGORIES if pathology == "scar" else EDEMA_NEGATIVE_CATEGORIES
    if not allowed:
        raise ValueError("fail-closed insufficient prototype bank: no allowed source cases")
    allowed_before_source_filter = list(allowed)
    excluded_no_t2_source_case_ids: list[str] = []
    if pathology == "edema":
        allowed = [r for r in allowed_before_source_filter if r.t2_present]
        excluded_no_t2_source_case_ids = sorted(
            {r.case_id for r in allowed_before_source_filter if not r.t2_present}
        )
        if not allowed:
            raise ValueError("fail-closed insufficient prototype bank: no T2-present source cases for edema")
    positives = [_concat_existing(r.category_vectors, positive_categories) for r in allowed]
    negatives_by_category = {category: [] for category in negative_categories}
    for record in allowed:
        for category in negative_categories:
            tensor = record.category_vectors.get(category)
            if tensor is not None and tensor.numel() > 0:
                negatives_by_category[category].append(tensor)
    positive_bank = torch.cat([p for p in positives if p.numel() > 0], dim=0) if any(p.numel() > 0 for p in positives) else torch.empty((0, 0))
    negative_parts = [torch.cat(items, dim=0) for items in negatives_by_category.values() if items]
    negative_bank = torch.cat(negative_parts, dim=0) if negative_parts else torch.empty((0, positive_bank.shape[1] if positive_bank.ndim == 2 else 0))
    if positive_bank.numel() > 0:
        positive_bank = F.normalize(positive_bank, dim=1)
    if negative_bank.numel() > 0:
        negative_bank = F.normalize(negative_bank, dim=1)
    negative_category_counts = {category: int(sum(item.shape[0] for item in items)) for category, items in negatives_by_category.items()}
    if positive_bank.shape[0] < int(minimum_positive) or negative_bank.shape[0] < int(minimum_negative):
        raise ValueError(
            "fail-closed insufficient prototype bank: "
            f"{pathology} positive={positive_bank.shape[0]} negative={negative_bank.shape[0]}"
        )
    return {
        "positive": positive_bank,
        "negative": negative_bank,
    }, {
        "query_case_id": str(query_case_id),
        "query_shard": int(query_shard),
        "pathology": pathology,
        "mode": mode,
        "allowed_case_count": len(allowed),
        "allowed_case_count_before_source_filter": len(allowed_before_source_filter),
        "allowed_case_count_after_source_filter": len(allowed),
        "source_eligibility_rule": "edema_requires_t2_present_sources" if pathology == "edema" else "scar_all_crossfit_allowed_sources",
        "excluded_no_t2_source_count": len(excluded_no_t2_source_case_ids),
        "excluded_no_t2_source_case_ids": "|".join(excluded_no_t2_source_case_ids),
        "no_t2_source_records_in_bank": False if pathology == "edema" else "",
        "excluded_query_case": mode == "train",
        "excluded_query_shard": mode == "train",
        "positive_count": int(positive_bank.shape[0]),
        "negative_count": int(negative_bank.shape[0]),
        "negative_categories_preserved": True,
        "negative_category_counts": str(negative_category_counts),
    }


def cosine_similarity_maps(features: torch.Tensor, bank: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    if features.ndim != 4:
        raise ValueError("features must be [C, D, H, W]")
    flat = F.normalize(features.reshape(features.shape[0], -1).transpose(0, 1), dim=1)
    out: dict[str, torch.Tensor] = {}
    for polarity in ("positive", "negative"):
        vectors = bank[polarity].to(device=features.device, dtype=features.dtype)
        if vectors.numel() == 0:
            raise ValueError(f"empty {polarity} prototype bank")
        sim = flat @ F.normalize(vectors, dim=1).transpose(0, 1)
        out[polarity] = sim.max(dim=1).values.reshape(1, *features.shape[1:])
    return out
