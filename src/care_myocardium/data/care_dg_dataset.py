"""Dataset contracts for CARE-DG.

The formal dataset loader is built around frozen nnU-Net OOF anchors. This file
keeps the tensor contract small and explicit so tests and runners can reject
shape, modality, or label mistakes before GPU training.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset


@dataclass(frozen=True)
class CAREDGCaseRecord:
    case_id: str
    fold: int
    image_path: Path
    label_path: Path
    anchor_probability_path: Path
    anchor_prediction_path: Path
    availability: tuple[float, float, float]
    t2_reliable: bool


def validate_care_dg_batch(batch: dict[str, torch.Tensor]) -> None:
    images = batch["images"]
    anchor = batch["anchor_logits"]
    availability = batch["availability"]
    labels = batch.get("labels")
    if images.ndim != 5 or images.shape[1] != 3:
        raise ValueError("CARE-DG images must be [B,3,D,H,W] in LGE,T2,C0 order")
    if anchor.ndim != 5 or anchor.shape[1] != 6:
        raise ValueError("CARE-DG anchor_logits must be [B,6,D,H,W]")
    if images.shape[0] != anchor.shape[0] or images.shape[-3:] != anchor.shape[-3:]:
        raise ValueError("CARE-DG image and anchor tensors must share batch/spatial shape")
    if availability.shape[:2] != (images.shape[0], 3):
        raise ValueError("CARE-DG availability must have batch x 3 modality entries")
    if labels is not None and labels.shape[0] != images.shape[0]:
        raise ValueError("CARE-DG labels must share batch size")


def aligned_spatial_crop(batch: dict[str, torch.Tensor], start_zyx: tuple[int, int, int], size_zyx: tuple[int, int, int]) -> dict[str, torch.Tensor]:
    """Crop all spatial CARE-DG tensors with the same Z/Y/X window."""

    z0, y0, x0 = [int(v) for v in start_zyx]
    dz, dy, dx = [int(v) for v in size_zyx]
    zslice = slice(z0, z0 + dz)
    yslice = slice(y0, y0 + dy)
    xslice = slice(x0, x0 + dx)
    out: dict[str, torch.Tensor] = {}
    spatial_keys_5d = {
        "images",
        "anchor_logits",
        "uncertainty",
        "myocardium_support",
        "edema_support",
        "distance_to_myocardium",
        "fn_error_map",
        "fp_error_map",
    }
    spatial_keys_4d = {"labels", "anchor_mask"}
    for key, value in batch.items():
        if not torch.is_tensor(value):
            out[key] = value
        elif key in spatial_keys_5d and value.ndim == 5:
            out[key] = value[..., zslice, yslice, xslice]
        elif key in spatial_keys_4d and value.ndim == 4:
            out[key] = value[..., zslice, yslice, xslice]
        else:
            out[key] = value
    validate_care_dg_batch(out)
    return out


class InMemoryCAREDGDataset(Dataset[dict[str, torch.Tensor]]):
    """Small deterministic dataset used for unit tests and real-case gates."""

    def __init__(self, items: list[dict[str, torch.Tensor]]) -> None:
        self.items = items

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        item = {key: value.clone() if torch.is_tensor(value) else value for key, value in self.items[index].items()}
        validate_care_dg_batch(item)
        return item
