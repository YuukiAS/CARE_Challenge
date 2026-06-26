"""Pathology-specific SRR heads."""

from __future__ import annotations

import torch
from torch import nn


class AnatomyPathologyHeads(nn.Module):
    """Separate anatomy, scar, and edema heads with a soft anatomy prior."""

    def __init__(self, channels: int, prior_strength: float = 0.5) -> None:
        super().__init__()
        self.prior_strength = float(prior_strength)
        self.anatomy = nn.Conv3d(channels, 4, kernel_size=1)
        self.scar = nn.Conv3d(channels, 1, kernel_size=1)
        self.edema = nn.Conv3d(channels, 1, kernel_size=1)

    def forward(
        self,
        anatomy_features: torch.Tensor,
        scar_features: torch.Tensor,
        edema_features: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        anatomy_logits = self.anatomy(anatomy_features)
        union_prior = torch.logsumexp(anatomy_logits[:, 1:4], dim=1, keepdim=True)
        prior_bias = self.prior_strength * torch.tanh(union_prior)
        scar_logits = self.scar(scar_features) + prior_bias
        edema_logits = self.edema(edema_features) + prior_bias
        logits = torch.cat([anatomy_logits, edema_logits, scar_logits], dim=1)
        return {
            "logits": logits,
            "anatomy_logits": anatomy_logits,
            "scar_logits": scar_logits,
            "edema_logits": edema_logits,
            "union_prior_logits": union_prior,
        }
