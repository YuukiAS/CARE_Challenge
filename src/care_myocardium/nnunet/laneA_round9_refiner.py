"""Lane A Round9 edema-only residual refiner components."""

from __future__ import annotations

import torch
from torch import nn


class EdemaResidualRefiner(nn.Module):
    """Small class_4-only residual refiner for baseline-preserving smoke tests."""

    def __init__(self, in_channels: int, hidden_channels: int = 16) -> None:
        super().__init__()
        final = nn.Conv3d(hidden_channels, 1, kernel_size=1)
        nn.init.zeros_(final.weight)
        nn.init.constant_(final.bias, -8.0)
        self.net = nn.Sequential(
            nn.Conv3d(in_channels, hidden_channels, kernel_size=3, padding=1),
            nn.InstanceNorm3d(hidden_channels, affine=True),
            nn.LeakyReLU(inplace=True),
            final,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def fuse_edema_only(baseline_seg: torch.Tensor, edema_logit: torch.Tensor, threshold: float = 0.5) -> torch.Tensor:
    """Return a segmentation where only class_4 edema may be changed."""

    if baseline_seg.ndim != edema_logit.ndim:
        edema_logit = edema_logit[:, 0]
    refined = baseline_seg.clone()
    edema_mask = (torch.sigmoid(edema_logit) >= threshold) & (baseline_seg != 5)
    refined[edema_mask] = 4
    return refined
