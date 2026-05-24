"""Lane A Round14 lightweight edema calibrator models.

These models are intentionally small and baseline-preserving. They are meant
for component/feature smoke tests, not as replacement nnU-Net trainers.
"""

from __future__ import annotations

import torch
from torch import nn


EDEMA_CLASS = 4
SCAR_CLASS = 5


class ComponentLogisticCalibrator(nn.Module):
    """Interpretable component accept/reject model."""

    def __init__(self, in_features: int) -> None:
        super().__init__()
        self.linear = nn.Linear(in_features, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x).squeeze(-1)


class VoxelFeatureCalibrator(nn.Module):
    """Tiny voxel-level edema probability calibrator."""

    def __init__(self, in_features: int, hidden_features: int = 16) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_features),
            nn.LeakyReLU(inplace=True),
            nn.Linear(hidden_features, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def assert_scar_unchanged(baseline_seg: torch.Tensor, refined_seg: torch.Tensor) -> int:
    if baseline_seg.shape != refined_seg.shape:
        raise ValueError(f"shape mismatch: baseline={tuple(baseline_seg.shape)} refined={tuple(refined_seg.shape)}")
    changed = ((baseline_seg == SCAR_CLASS) != (refined_seg == SCAR_CLASS)).sum()
    return int(changed.detach().cpu())


def fuse_component_acceptance(
    baseline_seg: torch.Tensor,
    candidate_seg: torch.Tensor,
    accept_mask: torch.Tensor,
) -> torch.Tensor:
    """Fuse accepted class-4 candidate voxels while preserving scar.

    ``accept_mask`` is a boolean voxel mask of accepted candidate edema
    components. Rejected components fall back to the baseline labels.
    """

    if baseline_seg.shape != candidate_seg.shape or baseline_seg.shape != accept_mask.shape:
        raise ValueError(
            "shape mismatch: "
            f"baseline={tuple(baseline_seg.shape)} candidate={tuple(candidate_seg.shape)} accept={tuple(accept_mask.shape)}"
        )
    refined = baseline_seg.clone()
    candidate_edema = (candidate_seg == EDEMA_CLASS) & accept_mask & (baseline_seg != SCAR_CLASS)
    baseline_edema = baseline_seg == EDEMA_CLASS
    refined[candidate_edema] = EDEMA_CLASS
    refined[baseline_edema & (candidate_seg != EDEMA_CLASS)] = baseline_seg[baseline_edema & (candidate_seg != EDEMA_CLASS)]
    return refined
