"""Seven-step SVF registration for Route B Round03."""

from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


def identity_grid(shape: tuple[int, int, int], device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    z, y, x = torch.meshgrid(
        torch.linspace(-1, 1, shape[0], device=device, dtype=dtype),
        torch.linspace(-1, 1, shape[1], device=device, dtype=dtype),
        torch.linspace(-1, 1, shape[2], device=device, dtype=dtype),
        indexing="ij",
    )
    return torch.stack((x, y, z), dim=-1)


def warp(volume: torch.Tensor, displacement: torch.Tensor) -> torch.Tensor:
    grid = identity_grid(volume.shape[-3:], volume.device, volume.dtype).unsqueeze(0)
    return F.grid_sample(volume, grid + displacement.permute(0, 2, 3, 4, 1), mode="bilinear", padding_mode="border", align_corners=True)


def integrate_velocity(velocity: torch.Tensor, steps: int = 7) -> torch.Tensor:
    displacement = velocity / float(2**steps)
    for _ in range(steps):
        displacement = displacement + warp(displacement, displacement)
    return displacement


def jacobian_receipt(displacement: torch.Tensor) -> dict[str, torch.Tensor]:
    dz = displacement[:, 2:3, 1:] - displacement[:, 2:3, :-1]
    dy = displacement[:, 1:2, :, 1:] - displacement[:, 1:2, :, :-1]
    dx = displacement[:, 0:1, :, :, 1:] - displacement[:, 0:1, :, :, :-1]
    min_j = torch.stack([1 + dz.min(), 1 + dy.min(), 1 + dx.min()]).min()
    folding = ((dz < -1).float().mean() + (dy < -1).float().mean() + (dx < -1).float().mean()) / 3.0
    return {"minimum_jacobian": min_j, "folding_rate": folding}


class RouteBRound03SVFRegistration(nn.Module):
    def __init__(self, hidden: int = 16) -> None:
        super().__init__()
        self.integration_steps = 7
        self.net = nn.Sequential(
            nn.Conv3d(2, hidden, 3, padding=1),
            nn.GroupNorm(4, hidden),
            nn.SiLU(),
            nn.Conv3d(hidden, hidden, 3, padding=1),
            nn.GroupNorm(4, hidden),
            nn.SiLU(),
            nn.Conv3d(hidden, 3, 3, padding=1),
        )

    def forward(self, fixed: torch.Tensor, moving: torch.Tensor) -> dict[str, torch.Tensor]:
        velocity = 0.10 * torch.tanh(self.net(torch.cat([fixed, moving], dim=1)))
        displacement = integrate_velocity(velocity, self.integration_steps)
        inverse = integrate_velocity(-velocity, self.integration_steps)
        warped = warp(moving, displacement)
        inv_error = (displacement + warp(inverse, displacement)).abs().mean()
        jac = jacobian_receipt(displacement)
        return {
            "velocity": velocity,
            "displacement": displacement,
            "inverse_displacement": inverse,
            "warped": warped,
            "inverse_composition_error": inv_error,
            **jac,
        }
