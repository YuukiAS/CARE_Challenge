"""M10 learned temporal dictionary."""

from __future__ import annotations

import torch
from torch import nn


TEMPORAL_SLOT_NAMES = (
    "ed_anatomy_anchor",
    "early_systolic_contraction",
    "late_systolic_contraction",
    "early_diastolic_relaxation",
    "late_diastolic_relaxation",
    "motion_magnitude",
    "registered_texture_residual",
    "registration_uncertainty_safety",
)


class TemporalSlotDictionary(nn.Module):
    """Eight-slot temporal dictionary with QC masking."""

    def __init__(self, in_channels: int, hidden_channels: int = 24, slot_count: int = 8) -> None:
        super().__init__()
        self.slot_count = slot_count
        self.encoder = nn.Sequential(
            nn.Conv3d(in_channels, hidden_channels, 3, padding=1),
            nn.GroupNorm(4, hidden_channels),
            nn.SiLU(),
            nn.Conv3d(hidden_channels, hidden_channels, 1),
            nn.SiLU(),
        )
        self.experts = nn.ModuleList([nn.Conv3d(hidden_channels, hidden_channels, 3, padding=1) for _ in range(slot_count)])
        self.router = nn.Conv3d(hidden_channels, slot_count, 1)

    def forward(self, z: torch.Tensor, valid_frame_mask: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        if z.ndim != 6:
            raise ValueError("z must be BxTxCxDxHxW")
        b, t, c, d, h, w = z.shape
        flat = z.reshape(b * t, c, d, h, w)
        encoded = self.encoder(flat)
        logits = self.router(encoded).reshape(b, t, self.slot_count, d, h, w)
        mask = None
        if valid_frame_mask is not None:
            mask = valid_frame_mask.reshape(b, t, 1, 1, 1, 1).to(dtype=torch.bool, device=z.device)
            logits = logits.masked_fill(~mask, -1e4)
        beta = torch.softmax(logits, dim=2)
        if mask is not None:
            beta = beta * mask.to(dtype=beta.dtype)
        expert_stack = torch.stack([expert(encoded) for expert in self.experts], dim=1)
        expert_stack = expert_stack.reshape(b, t, self.slot_count, -1, d, h, w)
        temporal = (beta.unsqueeze(3) * expert_stack).sum(dim=(1, 2))
        return temporal, beta


def temporal_load_loss(beta: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    slot_mass = beta.mean(dim=(0, 1, 3, 4, 5))
    target = torch.full_like(slot_mass, 1.0 / beta.shape[2])
    return ((slot_mass - target).square() / (target + eps)).mean()
