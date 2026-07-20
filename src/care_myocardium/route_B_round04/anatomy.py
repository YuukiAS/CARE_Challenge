"""Small trainable anatomy repair module for Route B Round04 B1."""

from __future__ import annotations

import torch
from torch import nn


class TinyAnatomyRepairNet(nn.Module):
    """Minimal routed+lateral anatomy head used for the B1 optimization gate."""

    def __init__(self, in_channels: int = 3, hidden_channels: int = 12) -> None:
        super().__init__()
        self.routed_stem = nn.Sequential(
            nn.Conv3d(in_channels, hidden_channels, 3, padding=1),
            nn.InstanceNorm3d(hidden_channels),
            nn.SiLU(inplace=True),
            nn.Conv3d(hidden_channels, hidden_channels, 3, padding=1),
            nn.SiLU(inplace=True),
        )
        self.lateral_stem = nn.Sequential(
            nn.Conv3d(in_channels, hidden_channels, 1),
            nn.SiLU(inplace=True),
        )
        self.routed_head = nn.Conv3d(hidden_channels, 3, 1)
        self.lateral_head = nn.Conv3d(hidden_channels, 3, 1)
        self.mix = nn.Parameter(torch.tensor(0.5))

    def forward(self, image: torch.Tensor, availability: torch.Tensor) -> dict[str, torch.Tensor]:
        if image.ndim != 5:
            raise ValueError(f"expected image [B,C,D,H,W], got {tuple(image.shape)}")
        if availability.ndim != 2:
            raise ValueError(f"expected availability [B,C], got {tuple(availability.shape)}")
        masked = image * availability[:, :, None, None, None].clamp(0, 1)
        routed = self.routed_head(self.routed_stem(masked))
        lateral = self.lateral_head(self.lateral_stem(masked))
        alpha = torch.sigmoid(self.mix)
        logits = alpha * routed + (1.0 - alpha) * lateral
        return {"logits": logits, "routed_logits": routed, "lateral_logits": lateral, "mix": alpha}


def anatomy_targets_from_compact(label: torch.Tensor) -> torch.Tensor:
    """Return union/LV/RV anatomy targets from compact CARE MyoPS labels."""

    union = torch.isin(label, torch.tensor([1, 4, 5], device=label.device)).float()
    lv = (label == 2).float()
    rv = (label == 3).float()
    return torch.stack([union, lv, rv], dim=1)
