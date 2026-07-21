"""Shared prototype and cross-fitted memory provenance helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import torch
import torch.nn.functional as F

from src.care_myocardium.srr_production.anchor_manifest import sha256_text


@dataclass(frozen=True)
class CasePrototypeVectors:
    case_id: str
    shard: int
    t2_present: bool
    scar_positive: torch.Tensor
    scar_negative: torch.Tensor
    edema_positive: torch.Tensor
    edema_negative: torch.Tensor
    feature_hash: str


def hash_tensor(tensor: torch.Tensor) -> str:
    value = tensor.detach().cpu().contiguous()
    h = __import__("hashlib").sha256()
    h.update(str(tuple(value.shape)).encode("utf-8"))
    h.update(str(value.dtype).encode("utf-8"))
    h.update(value.numpy().tobytes())
    return h.hexdigest()


def require_case_exclusive_sources(
    *,
    query_case_id: str,
    query_shard: int,
    provenance_rows: Iterable[dict[str, Any]],
) -> None:
    for row in provenance_rows:
        if str(row.get("case_id")) == str(query_case_id):
            raise ValueError(f"prototype self-leakage: query case {query_case_id} appears in source provenance")
        if int(row.get("shard", -1)) == int(query_shard):
            raise ValueError(f"prototype shard leakage: query shard {query_shard} appears in source provenance")


def merge_case_vectors(records: list[CasePrototypeVectors]) -> dict[str, torch.Tensor]:
    if not records:
        raise ValueError("no case prototype records supplied")

    def cat(name: str) -> torch.Tensor:
        rows = [getattr(record, name) for record in records if getattr(record, name).numel() > 0]
        if not rows:
            first = records[0].scar_positive
            return first.new_empty((0, first.shape[-1] if first.ndim == 2 else 0))
        return F.normalize(torch.cat(rows, dim=0), dim=1)

    return {
        "scar_positive": cat("scar_positive"),
        "scar_negative": cat("scar_negative"),
        "edema_positive": cat("edema_positive"),
        "edema_negative": cat("edema_negative"),
    }


def load_casewise_prototype_memory(
    *,
    model: torch.nn.Module,
    records: list[CasePrototypeVectors],
    source: str,
    strict: bool = True,
) -> dict[str, Any]:
    """Load dictionaries and update M10 memory using each case's own vectors."""

    merged = merge_case_vectors(records)
    req = {
        "scar_positive": int(model.scar_dictionary.positive.shape[0]),
        "scar_negative": int(model.scar_dictionary.negative.shape[0]),
        "edema_positive": int(model.edema_dictionary.positive.shape[0]),
        "edema_negative": int(model.edema_dictionary.negative.shape[0]),
    }
    counts = {key: int(value.shape[0]) for key, value in merged.items()}
    for key, need in req.items():
        if counts[key] < need:
            raise ValueError(f"insufficient real prototype vectors for {key}: {counts[key]} < {need}")

    provenance_rows: list[dict[str, Any]] = []
    for record in records:
        for key in ("scar_positive", "scar_negative", "edema_positive", "edema_negative"):
            tensor = getattr(record, key)
            provenance_rows.append(
                {
                    "case_id": record.case_id,
                    "shard": int(record.shard),
                    "category": key,
                    "t2_present": bool(record.t2_present),
                    "raw_vector_count": int(tensor.shape[0]) if tensor.ndim == 2 else 0,
                    "accepted_vector_count": int(tensor.shape[0]) if tensor.ndim == 2 else 0,
                    "feature_hash": record.feature_hash,
                    "entered_final_bank": bool(tensor.numel() > 0),
                }
            )
    source_cases = [record.case_id for record in records]
    shard_map = {record.case_id: int(record.shard) for record in records}
    base_provenance = {
        "source_cases": source_cases,
        "shards": shard_map,
        "case_feature_rows": provenance_rows,
        "repeat_last_vector_fallback": False,
        "feature_hash": sha256_text("|".join(record.feature_hash for record in records)),
    }
    scar_prov = {**base_provenance, "vector_counts": {"positive": counts["scar_positive"], "negative": counts["scar_negative"]}}
    edema_prov = {
        **base_provenance,
        "vector_counts": {"positive": counts["edema_positive"], "negative": counts["edema_negative"]},
        "no_t2_myocardium_negative_voxels": 0,
    }
    model.scar_dictionary.load_prototype_bank(
        positive=merged["scar_positive"][: req["scar_positive"]],
        negative=merged["scar_negative"][: req["scar_negative"]],
        source=source,
        provenance=scar_prov,
        strict=strict,
    )
    model.edema_dictionary.load_prototype_bank(
        positive=merged["edema_positive"][: req["edema_positive"]],
        negative=merged["edema_negative"][: req["edema_negative"]],
        source=source,
        provenance=edema_prov,
        strict=strict,
    )
    for record in records:
        model.cross_fitted_memory.update(
            "scar",
            "positive",
            "scar_positive",
            record.scar_positive,
            case_id=record.case_id,
            t2_present=record.t2_present,
        )
        model.cross_fitted_memory.update(
            "scar",
            "negative",
            "scar_safe_negative",
            record.scar_negative,
            case_id=record.case_id,
            t2_present=record.t2_present,
        )
        model.cross_fitted_memory.update(
            "edema",
            "positive",
            "t2_present_edema_positive",
            record.edema_positive,
            case_id=record.case_id,
            t2_present=record.t2_present,
        )
        model.cross_fitted_memory.update(
            "edema",
            "negative",
            "t2_present_safe_negative",
            record.edema_negative,
            case_id=record.case_id,
            t2_present=record.t2_present,
        )
    memory_summary = model.cross_fitted_memory.summary()
    return {
        "status": "REAL_CASEWISE_PROTOTYPE_MEMORY_READY",
        "source": source,
        "source_case_ids": source_cases,
        "counts": counts,
        "required": req,
        "scar": scar_prov,
        "edema": edema_prov,
        "memory_summary": memory_summary,
        "case_exclusion_policy": "training queries use cross-fitted counts>0 memory slots from non-query shards; validation/inference use frozen training shards",
        "zero_count_slot_policy": "masked_out_of_similarity",
    }
