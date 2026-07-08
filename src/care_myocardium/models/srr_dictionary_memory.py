"""Auditable prototype memory helpers for SRR M9.

This module is intentionally small: it provides a first-party memory container
that enforces no-T2 edema-negative safety at update time and emits lightweight
ledger rows for M9 packets.
"""

from __future__ import annotations

from dataclasses import dataclass

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
        }

    def ledger_rows(self) -> list[dict[str, object]]:
        return [event.as_row() for event in self.update_ledger]
