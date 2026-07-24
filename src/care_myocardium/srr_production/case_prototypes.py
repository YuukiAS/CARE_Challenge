"""Deterministic case-level prototype helpers for W1 synthetic contract checks."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch.nn import functional as F


@dataclass(frozen=True)
class CasePrototypeRecord:
    case_id: str
    shard: int
    t2_present: bool
    scar_positive: torch.Tensor
    scar_negative: torch.Tensor
    edema_positive: torch.Tensor
    edema_negative: torch.Tensor
    provenance: dict[str, int | str | bool]


def deterministic_case_mean(
    features: torch.Tensor,
    mask: torch.Tensor,
    *,
    cap: int = 4096,
    min_voxels: int = 32,
) -> tuple[torch.Tensor, dict[str, int | bool]]:
    if features.ndim != 4:
        raise ValueError("features must be [C, D, H, W]")
    flat_features = features.reshape(features.shape[0], -1).transpose(0, 1)
    flat_mask = mask.to(device=features.device, dtype=torch.bool).reshape(-1)
    indices = flat_mask.nonzero(as_tuple=False).flatten()
    available = int(indices.numel())
    accepted = min(available, int(cap))
    if accepted < int(min_voxels):
        return features.new_empty((0, features.shape[0])), {
            "available_voxels": available,
            "accepted_voxels": accepted,
            "cap": int(cap),
            "min_voxels": int(min_voxels),
            "entered_bank": False,
        }
    selected = indices[:accepted]
    vector = F.normalize(flat_features[selected].mean(dim=0, keepdim=True), dim=1)
    return vector, {
        "available_voxels": available,
        "accepted_voxels": accepted,
        "cap": int(cap),
        "min_voxels": int(min_voxels),
        "entered_bank": True,
    }


def build_case_prototype_record(
    *,
    case_id: str,
    shard: int,
    t2_present: bool,
    features: torch.Tensor,
    masks: dict[str, torch.Tensor],
    cap: int = 4096,
    min_voxels: int = 32,
) -> CasePrototypeRecord:
    scar_pos, scar_pos_meta = deterministic_case_mean(features, masks["scar_positive"], cap=cap, min_voxels=min_voxels)
    scar_neg, scar_neg_meta = deterministic_case_mean(features, masks["scar_negative"], cap=cap, min_voxels=min_voxels)
    if t2_present:
        edema_pos, edema_pos_meta = deterministic_case_mean(features, masks["edema_positive"], cap=cap, min_voxels=min_voxels)
        edema_neg, edema_neg_meta = deterministic_case_mean(features, masks["edema_negative"], cap=cap, min_voxels=min_voxels)
    else:
        edema_pos = features.new_empty((0, features.shape[0]))
        edema_neg = features.new_empty((0, features.shape[0]))
        edema_pos_meta = {"available_voxels": 0, "accepted_voxels": 0, "cap": int(cap), "min_voxels": int(min_voxels), "entered_bank": False}
        edema_neg_meta = {"available_voxels": 0, "accepted_voxels": 0, "cap": int(cap), "min_voxels": int(min_voxels), "entered_bank": False}
    return CasePrototypeRecord(
        case_id=str(case_id),
        shard=int(shard),
        t2_present=bool(t2_present),
        scar_positive=scar_pos,
        scar_negative=scar_neg,
        edema_positive=edema_pos,
        edema_negative=edema_neg,
        provenance={
            "case_id": str(case_id),
            "shard": int(shard),
            "t2_present": bool(t2_present),
            "scar_positive_accepted": int(scar_pos_meta["accepted_voxels"]),
            "scar_negative_accepted": int(scar_neg_meta["accepted_voxels"]),
            "edema_positive_accepted": int(edema_pos_meta["accepted_voxels"]),
            "edema_negative_accepted": int(edema_neg_meta["accepted_voxels"]),
            "no_t2_edema_negative_contribution": int(0 if t2_present else edema_neg.shape[0]),
            "cap": int(cap),
        },
    )


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
    if mode not in {"train", "validation"}:
        raise ValueError("mode must be train or validation")
    if mode == "train":
        allowed = [r for r in records if r.case_id != str(query_case_id) and int(r.shard) != int(query_shard)]
    else:
        allowed = list(records)

    pos_name = f"{pathology}_positive"
    neg_name = f"{pathology}_negative"
    positives = [getattr(r, pos_name) for r in allowed if getattr(r, pos_name).numel() > 0]
    negatives = [getattr(r, neg_name) for r in allowed if getattr(r, neg_name).numel() > 0]
    if not allowed:
        raise ValueError("fail-closed insufficient prototype bank: no allowed source cases")
    ref = allowed[0].scar_positive if allowed[0].scar_positive.numel() > 0 else allowed[0].scar_negative
    positive_bank = F.normalize(torch.cat(positives, dim=0), dim=1) if positives else ref.new_empty((0, ref.shape[-1]))
    negative_bank = F.normalize(torch.cat(negatives, dim=0), dim=1) if negatives else ref.new_empty((0, ref.shape[-1]))
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
        "excluded_query_case": mode == "train",
        "excluded_query_shard": mode == "train",
        "positive_count": int(positive_bank.shape[0]),
        "negative_count": int(negative_bank.shape[0]),
    }
