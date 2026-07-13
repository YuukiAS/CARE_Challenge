"""M10 CineMA-to-CARE adapter modules.

These modules are intentionally small but trainable. They adapt frame-wise
CineMA anatomy evidence to the CARE compact CineMyoPS label space and expose
explicit gradient-bearing parameters for Wave 3 fidelity tests and formal
training entrypoints.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn
from torch.nn import functional as F


@dataclass(frozen=True)
class CineAdapterConfig:
    in_channels: int = 2
    hidden_channels: int = 16
    out_channels: int = 4


class CineMAAdapter(nn.Module):
    """Capacity-matched adapter over image and CineMA anatomy logits."""

    def __init__(self, config: CineAdapterConfig | None = None) -> None:
        super().__init__()
        self.config = config or CineAdapterConfig()
        c = self.config.hidden_channels
        self.stem = nn.Sequential(
            nn.Conv3d(self.config.in_channels, c, kernel_size=3, padding=1),
            nn.GroupNorm(4, c),
            nn.SiLU(),
        )
        self.adapter = nn.Sequential(
            nn.Conv3d(c, c, kernel_size=3, padding=1),
            nn.GroupNorm(4, c),
            nn.SiLU(),
            nn.Conv3d(c, c, kernel_size=1),
            nn.SiLU(),
        )
        self.head = nn.Conv3d(c, self.config.out_channels, kernel_size=1)

    def forward(self, image: torch.Tensor, cinema_prior: torch.Tensor) -> torch.Tensor:
        if image.ndim != 5 or cinema_prior.ndim != 5:
            raise ValueError("image and cinema_prior must be BxCxDxHxW tensors")
        x = torch.cat([image, cinema_prior], dim=1)
        features = self.stem(x)
        return self.head(features + self.adapter(features))


def compact_cine_labels(raw: torch.Tensor) -> torch.Tensor:
    """Map CARE raw labels to compact Cine classes: bg, myo, LV, pathology."""

    out = torch.zeros_like(raw, dtype=torch.long)
    out = torch.where(raw == 200, torch.ones_like(out), out)
    out = torch.where(raw == 500, torch.full_like(out, 2), out)
    out = torch.where(raw == 2221, torch.full_like(out, 3), out)
    return out


def dice_ce_loss(logits: torch.Tensor, target: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    ce = F.cross_entropy(logits, target)
    probs = logits.softmax(dim=1)
    one_hot = F.one_hot(target.clamp_min(0), num_classes=logits.shape[1]).permute(0, 4, 1, 2, 3).float()
    dims = tuple(range(2, logits.ndim))
    inter = (probs * one_hot).sum(dim=dims)
    denom = probs.sum(dim=dims) + one_hot.sum(dim=dims)
    dice = 1.0 - ((2.0 * inter + eps) / (denom + eps)).mean()
    return ce + dice
