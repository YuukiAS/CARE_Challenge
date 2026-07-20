"""Auditable prototype memory helpers for SRR M9/M10.

This module is intentionally small: it provides a first-party memory container
that enforces no-T2 edema-negative safety at update time and emits lightweight
ledger rows for M9 packets.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

import torch.nn.functional as F
import torch


M9_MEMORY_CATEGORIES = (
    "scar_positive",
    "scar_safe_negative",
    "edema_positive",
    "edema_safe_negative",
)


@dataclass(frozen=True)
class PrototypeMemoryUpdate:
    category: str
    case_id: str
    t2_present: bool
    feature_count: int
    accepted: bool
    reason: str

    def as_row(self) -> dict[str, object]:
        return {
            "category": self.category,
            "case_id": self.case_id,
            "t2_present": self.t2_present,
            "feature_count": self.feature_count,
            "accepted": self.accepted,
            "reason": self.reason,
        }


class SafePrototypeMemoryBank(torch.nn.Module):
    """EMA prototype memory with hard edema-negative no-T2 rejection."""

    def __init__(self, channels: int, momentum: float = 0.10) -> None:
        super().__init__()
        self.channels = int(channels)
        self.momentum = float(momentum)
        self.register_buffer("memory", torch.zeros(len(M9_MEMORY_CATEGORIES), self.channels))
        self.register_buffer("counts", torch.zeros(len(M9_MEMORY_CATEGORIES), dtype=torch.long))
        self.category_to_index = {name: idx for idx, name in enumerate(M9_MEMORY_CATEGORIES)}
        self.update_ledger: list[PrototypeMemoryUpdate] = []
        self.provenance: dict[str, list[dict[str, object]]] = {name: [] for name in M9_MEMORY_CATEGORIES}

    def update(self, category: str, features: torch.Tensor, *, case_id: str, t2_present: bool) -> PrototypeMemoryUpdate:
        if category not in self.category_to_index:
            raise ValueError(f"unknown prototype memory category: {category}")
        feature_count = int(features.shape[0]) if features.ndim >= 2 else 0
        if category == "edema_safe_negative" and not bool(t2_present):
            event = PrototypeMemoryUpdate(category, case_id, bool(t2_present), feature_count, False, "REJECT_NO_T2_EDEMA_NEGATIVE")
            self.update_ledger.append(event)
            return event
        if feature_count <= 0:
            event = PrototypeMemoryUpdate(category, case_id, bool(t2_present), feature_count, False, "REJECT_EMPTY_FEATURES")
            self.update_ledger.append(event)
            return event
        flat = features.reshape(feature_count, -1)
        if flat.shape[1] != self.channels:
            raise ValueError(f"feature channel mismatch: expected {self.channels}, got {flat.shape[1]}")
        idx = self.category_to_index[category]
        mean_feature = flat.mean(dim=0).to(device=self.memory.device, dtype=self.memory.dtype)
        if int(self.counts[idx]) == 0:
            self.memory[idx].copy_(mean_feature)
        else:
            self.memory[idx].mul_(1.0 - self.momentum).add_(mean_feature, alpha=self.momentum)
        self.counts[idx] += feature_count
        event = PrototypeMemoryUpdate(category, case_id, bool(t2_present), feature_count, True, "ACCEPTED")
        self.update_ledger.append(event)
        self.provenance[category].append(
            {
                "case_id": str(case_id),
                "category": str(category),
                "t2_present": bool(t2_present),
                "feature_count": int(feature_count),
                "accepted": True,
            }
        )
        return event

    def summary(self) -> dict[str, object]:
        return {
            "memory_type": "ema_prototype_memory",
            "categories": {
                name: {"count": int(self.counts[idx]), "has_memory": bool(int(self.counts[idx]) > 0)}
                for name, idx in self.category_to_index.items()
            },
            "no_t2_edema_negative_policy": "REJECT_NO_T2_EDEMA_NEGATIVE",
            "ledger_events": len(self.update_ledger),
            "accepted_events": sum(1 for row in self.update_ledger if row.status == "ACCEPTED"),
            "provenance": self.provenance,
        }

    def ledger_rows(self) -> list[dict[str, object]]:
        return [event.as_row() for event in self.update_ledger]


M10_PATHOLOGIES = ("scar", "edema")
M10_POSITIVE_SLOTS = 8
M10_NEGATIVE_SLOTS = 12
M10_SHARDS = 4


@dataclass(frozen=True)
class M10MemoryUpdate:
    pathology: str
    polarity: str
    category: str
    case_id: str
    source_shard: int
    query_shard: int
    t2_present: bool
    feature_count: int
    accepted_count: int
    reason: str

    def as_row(self) -> dict[str, object]:
        return {
            "pathology": self.pathology,
            "polarity": self.polarity,
            "category": self.category,
            "case_id": self.case_id,
            "source_shard": self.source_shard,
            "query_shard": self.query_shard,
            "t2_present": self.t2_present,
            "feature_count": self.feature_count,
            "accepted_count": self.accepted_count,
            "reason": self.reason,
        }


def deterministic_memory_shard(case_id: str, *, shard_count: int = M10_SHARDS) -> int:
    digest = hashlib.sha256(str(case_id).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % int(shard_count)


class M10CrossFittedPrototypeMemory(torch.nn.Module):
    """Cross-fitted positive/negative prototype memory for M10 D3.

    A case can query only prototypes sourced from the other three deterministic
    shards.  No-T2 myocardium is neither edema positive nor edema negative: the
    accepted count, EMA update, and gradient-carrying residual contribution are
    all exactly zero.
    """

    def __init__(self, channels: int, *, momentum: float = 0.01, residual_scale: float = 0.1) -> None:
        super().__init__()
        self.channels = int(channels)
        self.momentum = float(momentum)
        self.residual_scale = float(residual_scale)
        shape_pos = (len(M10_PATHOLOGIES), M10_SHARDS, M10_POSITIVE_SLOTS, self.channels)
        shape_neg = (len(M10_PATHOLOGIES), M10_SHARDS, M10_NEGATIVE_SLOTS, self.channels)
        self.register_buffer("positive_mu", torch.zeros(shape_pos))
        self.register_buffer("negative_mu", torch.zeros(shape_neg))
        self.register_buffer("positive_counts", torch.zeros(shape_pos[:-1], dtype=torch.long))
        self.register_buffer("negative_counts", torch.zeros(shape_neg[:-1], dtype=torch.long))
        self.positive_delta = torch.nn.Parameter(torch.zeros(shape_pos))
        self.negative_delta = torch.nn.Parameter(torch.zeros(shape_neg))
        self.pathology_to_index = {name: idx for idx, name in enumerate(M10_PATHOLOGIES)}
        self.update_ledger: list[M10MemoryUpdate] = []
        self.provenance: dict[str, list[dict[str, object]]] = {pathology: [] for pathology in M10_PATHOLOGIES}

    @staticmethod
    def _slot_indices(feature_count: int, slot_count: int, device: torch.device) -> torch.Tensor:
        if feature_count <= 0:
            return torch.empty((0,), dtype=torch.long, device=device)
        return torch.arange(feature_count, device=device, dtype=torch.long) % int(slot_count)

    def _prototype_tensor(self, pathology: str, polarity: str) -> torch.Tensor:
        pidx = self.pathology_to_index[pathology]
        if polarity == "positive":
            return F.normalize(self.positive_mu[pidx] + self.residual_scale * torch.tanh(self.positive_delta[pidx]), dim=-1)
        if polarity == "negative":
            return F.normalize(self.negative_mu[pidx] + self.residual_scale * torch.tanh(self.negative_delta[pidx]), dim=-1)
        raise ValueError(f"unknown polarity: {polarity!r}")

    def update(
        self,
        pathology: str,
        polarity: str,
        category: str,
        features: torch.Tensor,
        *,
        case_id: str,
        t2_present: bool,
    ) -> M10MemoryUpdate:
        if pathology not in self.pathology_to_index:
            raise ValueError(f"unknown pathology: {pathology!r}")
        if polarity not in {"positive", "negative"}:
            raise ValueError(f"unknown polarity: {polarity!r}")
        feature_count = int(features.shape[0]) if features.ndim >= 2 else 0
        shard = deterministic_memory_shard(case_id)
        if pathology == "edema" and not bool(t2_present):
            event = M10MemoryUpdate(pathology, polarity, category, str(case_id), shard, shard, False, feature_count, 0, "REJECT_NO_T2_EDEMA_MEMORY")
            self.update_ledger.append(event)
            return event
        if feature_count <= 0:
            event = M10MemoryUpdate(pathology, polarity, category, str(case_id), shard, shard, bool(t2_present), feature_count, 0, "REJECT_EMPTY_FEATURES")
            self.update_ledger.append(event)
            return event
        flat = features.reshape(feature_count, -1).detach().to(device=self.positive_mu.device, dtype=self.positive_mu.dtype)
        if flat.shape[1] != self.channels:
            raise ValueError(f"feature channel mismatch: expected {self.channels}, got {flat.shape[1]}")
        pidx = self.pathology_to_index[pathology]
        if polarity == "positive":
            mu = self.positive_mu[pidx, shard]
            counts = self.positive_counts[pidx, shard]
            slots = M10_POSITIVE_SLOTS
        else:
            mu = self.negative_mu[pidx, shard]
            counts = self.negative_counts[pidx, shard]
            slots = M10_NEGATIVE_SLOTS
        slot_idx = self._slot_indices(feature_count, slots, flat.device)
        for slot in range(slots):
            selected = flat[slot_idx == slot]
            if selected.numel() == 0:
                continue
            mean_feature = F.normalize(selected.mean(dim=0), dim=0)
            if int(counts[slot]) == 0:
                mu[slot].copy_(mean_feature)
            else:
                mu[slot].mul_(1.0 - self.momentum).add_(mean_feature, alpha=self.momentum)
                mu[slot].copy_(F.normalize(mu[slot], dim=0))
            counts[slot] += int(selected.shape[0])
        event = M10MemoryUpdate(pathology, polarity, category, str(case_id), shard, shard, bool(t2_present), feature_count, feature_count, "ACCEPTED")
        self.update_ledger.append(event)
        self.provenance[pathology].append(
            {
                "case_id": str(case_id),
                "shard": int(shard),
                "polarity": str(polarity),
                "category": str(category),
                "t2_present": bool(t2_present),
                "feature_count": int(feature_count),
                "accepted_count": int(feature_count),
            }
        )
        return event

    def query(self, features: torch.Tensor, *, pathology: str, case_id: str, require_ready: bool = False) -> dict[str, torch.Tensor]:
        if pathology not in self.pathology_to_index:
            raise ValueError(f"unknown pathology: {pathology!r}")
        query_shard = deterministic_memory_shard(case_id)
        include = torch.ones(M10_SHARDS, dtype=torch.bool, device=features.device)
        include[query_shard] = False
        emb = F.normalize(features, dim=1)
        pidx = self.pathology_to_index[pathology]
        pos_counts = self.positive_counts[pidx].to(device=features.device)[include]
        neg_counts = self.negative_counts[pidx].to(device=features.device)[include]
        if require_ready and (not bool((pos_counts > 0).any()) or not bool((neg_counts > 0).any())):
            raise ValueError(f"cross-fitted memory for {pathology} is not ready for case {case_id}: missing positive or negative source shards")
        pos = self._prototype_tensor(pathology, "positive").to(device=features.device, dtype=features.dtype)[include]
        neg = self._prototype_tensor(pathology, "negative").to(device=features.device, dtype=features.dtype)[include]
        pos_flat = pos.reshape(-1, self.channels)
        neg_flat = neg.reshape(-1, self.channels)
        pos_score = 0.07 * torch.logsumexp(torch.einsum("bcdhw,kc->bkdhw", emb, pos_flat) / 0.07, dim=1, keepdim=True)
        neg_score = 0.07 * torch.logsumexp(torch.einsum("bcdhw,kc->bkdhw", emb, neg_flat) / 0.07, dim=1, keepdim=True)
        return {
            "positive_similarity": pos_score,
            "negative_similarity": neg_score,
            "query_shard": torch.tensor(query_shard, device=features.device),
            "source_shards": torch.nonzero(include, as_tuple=False).flatten().to(device=features.device),
            "positive_source_count": pos_counts.sum().to(dtype=features.dtype),
            "negative_source_count": neg_counts.sum().to(dtype=features.dtype),
        }

    def summary(self) -> dict[str, object]:
        return {
            "memory_type": "m10_cross_fitted_ema_plus_learnable_residual",
            "positive_slots_per_pathology": M10_POSITIVE_SLOTS,
            "negative_slots_per_pathology": M10_NEGATIVE_SLOTS,
            "shards": M10_SHARDS,
            "edema_no_t2_policy": "REJECT_NO_T2_EDEMA_MEMORY",
            "ledger_events": len(self.update_ledger),
            "accepted_events": sum(1 for row in self.update_ledger if row.reason == "ACCEPTED"),
            "provenance": self.provenance,
        }

    def ledger_rows(self) -> list[dict[str, object]]:
        return [event.as_row() for event in self.update_ledger]
