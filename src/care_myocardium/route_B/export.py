"""Route B compact-label export helpers."""

from __future__ import annotations

import hashlib

import torch


MYOPS_COMPACT_TO_RAW = {
    0: 0,
    1: 200,
    2: 500,
    3: 600,
    4: 1220,
    5: 2221,
}

CINE_COMPACT_TO_RAW = {
    0: 0,
    1: 200,
    2: 500,
    3: 2221,
}


def _compact_to_raw(labels: torch.Tensor, mapping: dict[int, int]) -> torch.Tensor:
    raw = torch.empty_like(labels, dtype=torch.long)
    assigned = torch.zeros_like(labels, dtype=torch.bool)
    for compact, value in mapping.items():
        mask = labels == int(compact)
        raw[mask] = int(value)
        assigned |= mask
    if not bool(assigned.all()):
        unknown = torch.unique(labels[~assigned]).detach().cpu().tolist()
        raise ValueError(f"unknown compact labels: {unknown}")
    return raw


def compact_myops_to_raw(labels: torch.Tensor) -> torch.Tensor:
    return _compact_to_raw(labels, MYOPS_COMPACT_TO_RAW)


def compact_cine_to_raw(labels: torch.Tensor) -> torch.Tensor:
    return _compact_to_raw(labels, CINE_COMPACT_TO_RAW)


def tensor_hash(tensor: torch.Tensor) -> str:
    array = tensor.detach().cpu().contiguous().numpy()
    return hashlib.sha256(array.tobytes()).hexdigest()
