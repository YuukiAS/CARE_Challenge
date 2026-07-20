"""Registered temporal evidence consumer for Route B Round03."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass
class TemporalEvidence:
    reference_logits: torch.Tensor
    reference_features: torch.Tensor
    reference_uncertainty: torch.Tensor
    registered_logits: torch.Tensor
    registered_features: torch.Tensor
    registered_uncertainty: torch.Tensor
    velocity: torch.Tensor
    integrated_displacement: torch.Tensor
    jacobian: torch.Tensor
    motion_magnitude: torch.Tensor
    texture_residual: torch.Tensor
    frame_quality: torch.Tensor
    temporal_position: torch.Tensor
    valid_frame_mask: torch.Tensor


class RouteBRound03TemporalModel(nn.Module):
    required_fields = tuple(TemporalEvidence.__dataclass_fields__.keys())

    def __init__(self, channels: int = 32) -> None:
        super().__init__()
        self.project = nn.Conv3d(4 + 16 + 1 + 4 + 16 + 1 + 3 + 3 + 1 + 1 + 1, channels, 1)
        self.router = nn.Sequential(nn.Linear(channels + 4, 8), nn.SiLU(), nn.Linear(8, 8))
        self.slots = nn.Parameter(torch.randn(8, channels) * 0.02)
        self.head = nn.Conv3d(channels, 4, 1)

    def forward(self, evidence: TemporalEvidence) -> dict[str, torch.Tensor]:
        pieces = [
            evidence.reference_logits,
            evidence.reference_features,
            evidence.reference_uncertainty,
            evidence.registered_logits,
            evidence.registered_features,
            evidence.registered_uncertainty,
            evidence.velocity,
            evidence.integrated_displacement,
            evidence.jacobian,
            evidence.motion_magnitude,
            evidence.texture_residual,
        ]
        x = self.project(torch.cat(pieces, dim=1))
        pooled = x.mean(dim=(-3, -2, -1))
        quality = torch.cat([evidence.frame_quality, evidence.temporal_position, evidence.valid_frame_mask], dim=1)
        weights = torch.softmax(self.router(torch.cat([pooled, quality], dim=1)), dim=1)
        context = weights @ self.slots
        logits = self.head(x + context[..., None, None, None])
        return {"logits": logits, "slot_weights": weights}
