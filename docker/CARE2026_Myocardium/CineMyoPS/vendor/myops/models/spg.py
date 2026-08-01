from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class SpatialPriorGate(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.sigmoid = nn.Sigmoid()

    def forward(self, features: torch.Tensor, prior_map: torch.Tensor) -> torch.Tensor:
        if prior_map.shape[-2:] != features.shape[-2:]:
            prior = F.adaptive_avg_pool2d(prior_map, features.shape[-2:])
        else:
            prior = prior_map
        gate = self.sigmoid(prior)
        return features * gate.expand_as(features)
