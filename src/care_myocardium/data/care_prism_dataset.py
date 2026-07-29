"""Small CARE-PRISM dataset helpers.

Formal W2+ training will extend this module to real patient sampling. W1 uses
these helpers for deterministic mechanism fixtures only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch


@dataclass(frozen=True)
class CAREPRISMSyntheticCase:
    case_id: str
    images: torch.Tensor
    availability: torch.Tensor
    scar_target: torch.Tensor
    edema_zone_target: torch.Tensor
    anatomy_target: torch.Tensor
    t2_present: torch.Tensor


def synthetic_w1_batch(
    *,
    batch_size: int = 1,
    shape: tuple[int, int, int] = (8, 128, 128),
    t2_present: bool = True,
    seed: int = 13,
) -> dict[str, Any]:
    generator = torch.Generator().manual_seed(seed)
    images = torch.randn(batch_size, 3, *shape, generator=generator)
    availability = torch.ones(batch_size, 3)
    if not t2_present:
        availability[:, 1] = 0.0
        images[:, 1] = 0.0
    scar = torch.zeros(batch_size, 1, *shape)
    edema = torch.zeros(batch_size, 1, *shape)
    z0, y0, x0 = max(shape[0] // 2 - 1, 0), shape[1] // 3, shape[2] // 3
    scar[:, :, z0 : z0 + 2, y0 : y0 + 12, x0 : x0 + 12] = 1.0
    if t2_present:
        edema[:, :, z0 : z0 + 2, y0 : y0 + 20, x0 : x0 + 20] = 1.0
    anatomy = torch.zeros(batch_size, 3, *shape)
    anatomy[:, 0:1] = torch.clamp(edema + scar, 0, 1)
    anatomy[:, 1:2, :, shape[1] // 4 : shape[1] // 2, shape[2] // 4 : shape[2] // 2] = 1.0
    anatomy[:, 2:3, :, shape[1] // 2 : 3 * shape[1] // 4, shape[2] // 2 : 3 * shape[2] // 4] = 1.0
    return {
        "case_id": [f"synthetic_w1_{'t2' if t2_present else 'no_t2'}"],
        "images": images,
        "availability": availability,
        "scar_target": scar,
        "edema_zone_target": edema,
        "anatomy_target": anatomy,
        "t2_present": torch.full((batch_size, 1), 1.0 if t2_present else 0.0),
        "scar_burden_class": torch.zeros(batch_size, dtype=torch.long),
        "edema_burden_class": torch.zeros(batch_size, dtype=torch.long),
        "scar_log_ratio": torch.zeros(batch_size, 1),
        "edema_log_ratio": torch.zeros(batch_size, 1),
    }


class CAREPRISMSyntheticDataset(torch.utils.data.Dataset[dict[str, Any]]):
    def __init__(self, *, length: int = 4, shape: tuple[int, int, int] = (8, 128, 128)) -> None:
        self.length = int(length)
        self.shape = shape

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, index: int) -> dict[str, Any]:
        return synthetic_w1_batch(shape=self.shape, t2_present=(index % 2 == 0), seed=13 + index)


def collate_single_case(items: list[dict[str, Any]]) -> dict[str, Any]:
    if len(items) != 1:
        raise ValueError("CARE-PRISM W1 fixtures expect one full patient per batch")
    return items[0]
