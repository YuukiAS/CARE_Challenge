"""M10 learned Cine registration modules."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class RegistrationUNet(nn.Module):
    """Small 3D U-Net that predicts a stationary velocity field."""

    def __init__(self, in_channels: int = 2, channels: tuple[int, int, int, int] = (16, 32, 64, 128)) -> None:
        super().__init__()
        c1, c2, c3, c4 = channels
        self.enc1 = self._block(in_channels, c1)
        self.enc2 = self._block(c1, c2)
        self.enc3 = self._block(c2, c3)
        self.bottleneck = self._block(c3, c4)
        self.up3 = nn.ConvTranspose3d(c4, c3, 2, stride=2)
        self.dec3 = self._block(c3 + c3, c3)
        self.up2 = nn.ConvTranspose3d(c3, c2, 2, stride=2)
        self.dec2 = self._block(c2 + c2, c2)
        self.up1 = nn.ConvTranspose3d(c2, c1, 2, stride=2)
        self.dec1 = self._block(c1 + c1, c1)
        self.velocity = nn.Conv3d(c1, 3, kernel_size=3, padding=1)

    @staticmethod
    def _block(cin: int, cout: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv3d(cin, cout, 3, padding=1),
            nn.GroupNorm(4, cout),
            nn.SiLU(),
            nn.Conv3d(cout, cout, 3, padding=1),
            nn.GroupNorm(4, cout),
            nn.SiLU(),
        )

    def forward(self, fixed: torch.Tensor, moving: torch.Tensor) -> torch.Tensor:
        x = torch.cat([fixed, moving], dim=1)
        e1 = self.enc1(x)
        e2 = self.enc2(F.avg_pool3d(e1, 2))
        e3 = self.enc3(F.avg_pool3d(e2, 2))
        b = self.bottleneck(F.avg_pool3d(e3, 2))
        d3 = self.dec3(torch.cat([self.up3(b), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return 0.25 * torch.tanh(self.velocity(d1))


def identity_grid(shape: tuple[int, int, int], device: torch.device) -> torch.Tensor:
    d, h, w = shape
    zz, yy, xx = torch.meshgrid(
        torch.linspace(-1, 1, d, device=device),
        torch.linspace(-1, 1, h, device=device),
        torch.linspace(-1, 1, w, device=device),
        indexing="ij",
    )
    return torch.stack([xx, yy, zz], dim=-1)


def warp(volume: torch.Tensor, displacement: torch.Tensor) -> torch.Tensor:
    if volume.ndim != 5 or displacement.ndim != 5 or displacement.shape[1] != 3:
        raise ValueError("volume must be BxCxDxHxW and displacement Bx3xDxHxW")
    grid = identity_grid(tuple(volume.shape[-3:]), volume.device).unsqueeze(0).repeat(volume.shape[0], 1, 1, 1, 1)
    disp = displacement.permute(0, 2, 3, 4, 1)
    return F.grid_sample(volume, grid + disp, mode="bilinear", padding_mode="border", align_corners=True)


def smoothness_loss(displacement: torch.Tensor) -> torch.Tensor:
    dz = displacement[:, :, 1:] - displacement[:, :, :-1]
    dy = displacement[:, :, :, 1:] - displacement[:, :, :, :-1]
    dx = displacement[:, :, :, :, 1:] - displacement[:, :, :, :, :-1]
    return dz.square().mean() + dy.square().mean() + dx.square().mean()


def local_ncc_loss(fixed: torch.Tensor, warped: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    f = fixed - fixed.mean(dim=(-3, -2, -1), keepdim=True)
    w = warped - warped.mean(dim=(-3, -2, -1), keepdim=True)
    ncc = (f * w).mean(dim=(-3, -2, -1)) / (f.square().mean(dim=(-3, -2, -1)).sqrt() * w.square().mean(dim=(-3, -2, -1)).sqrt() + eps)
    return 1.0 - ncc.mean()
