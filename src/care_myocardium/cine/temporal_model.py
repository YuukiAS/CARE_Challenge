"""M10 Cine temporal segmentation model."""

from __future__ import annotations

import torch
from torch import nn

from .cinema_adapter import CineAdapterConfig, CineMAAdapter
from .temporal_dictionary import TemporalSlotDictionary


class CineTemporalModel(nn.Module):
    """Registration-gated temporal dictionary head over ED-space evidence."""

    def __init__(self, image_channels: int = 1, prior_channels: int = 1, hidden_channels: int = 24, out_channels: int = 4) -> None:
        super().__init__()
        self.adapter = CineMAAdapter(CineAdapterConfig(in_channels=image_channels + prior_channels, hidden_channels=hidden_channels, out_channels=out_channels))
        self.temporal_dictionary = TemporalSlotDictionary(in_channels=image_channels + prior_channels + 3, hidden_channels=hidden_channels, slot_count=8)
        self.head = nn.Sequential(
            nn.Conv3d(hidden_channels + out_channels, hidden_channels, 3, padding=1),
            nn.GroupNorm(4, hidden_channels),
            nn.SiLU(),
            nn.Conv3d(hidden_channels, out_channels, 1),
        )

    def forward(
        self,
        ed_image: torch.Tensor,
        ed_prior: torch.Tensor,
        temporal_z: torch.Tensor,
        valid_frame_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        frame0_logits = self.adapter(ed_image, ed_prior)
        temporal, beta = self.temporal_dictionary(temporal_z, valid_frame_mask=valid_frame_mask)
        logits = self.head(torch.cat([frame0_logits, temporal], dim=1))
        return logits, beta
