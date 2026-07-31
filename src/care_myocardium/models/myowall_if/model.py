"""CARE-MyoWall-IF matched Cartesian and wall-field pilot model."""

from __future__ import annotations

from typing import Any

import torch
from torch import nn
import torch.nn.functional as F

from .geometry import WallGeometry, WallInverseTransform


def _conv(in_ch: int, out_ch: int, kernel: tuple[int, int, int]) -> nn.Sequential:
    return nn.Sequential(nn.Conv3d(in_ch, out_ch, kernel, padding=tuple(k // 2 for k in kernel), bias=False), nn.InstanceNorm3d(out_ch, affine=True), nn.LeakyReLU(inplace=True))


class CircularConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, kernel: tuple[int, int, int]) -> None:
        super().__init__()
        self.kernel = kernel
        self.conv = nn.Conv3d(in_ch, out_ch, kernel, padding=(kernel[0] // 2, 0, kernel[2] // 2), bias=False)
        self.norm = nn.InstanceNorm3d(out_ch, affine=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        pad_t = self.kernel[1] // 2
        if pad_t:
            x = torch.cat([x[:, :, :, -pad_t:], x, x[:, :, :, :pad_t]], dim=3)
        return F.leaky_relu(self.norm(self.conv(x)), inplace=True)


class CartesianMatchedPathologyHead(nn.Module):
    """Matched Cartesian control with independent scar and pure-edema heads."""

    def __init__(self, in_channels: int = 48) -> None:
        super().__init__()
        self.scar = nn.Sequential(_conv(in_channels, 64, (3, 5, 3)), _conv(64, 64, (3, 3, 3)), _conv(64, 32, (3, 3, 3)), nn.Conv3d(32, 2, 1))
        self.edema_surface = nn.Sequential(_conv(in_channels, 48, (3, 9, 3)), _conv(48, 48, (3, 7, 3)), _conv(48, 24, (3, 5, 3)), nn.Conv3d(24, 1, 1))
        self.edema_radial = nn.Sequential(_conv(in_channels, 24, (1, 1, 5)), nn.Conv3d(24, 1, (1, 1, 3), padding=(0, 0, 1)))

    def forward(self, x: torch.Tensor, availability: torch.Tensor) -> dict[str, torch.Tensor]:
        scar = self.scar(x)
        t2 = availability[:, 1:2].view(-1, 1, 1, 1, 1).to(x)
        edema_logit = (self.edema_surface(x) + self.edema_radial(x)) * t2 + (1.0 - t2) * -16.0
        return {"scar_logit": scar[:, 0:1], "scar_sdf": scar[:, 1:2], "edema_logit": edema_logit, "edema_boundary": self.edema_surface(x)}


class ScarWallFieldHead(nn.Module):
    """Scar occupancy/SDF field over [z, theta, rho] with circular theta padding."""

    def __init__(self, in_channels: int = 48) -> None:
        super().__init__()
        self.net = nn.Sequential(
            CircularConvBlock(in_channels, 64, (3, 5, 3)),
            CircularConvBlock(64, 64, (3, 3, 3)),
            CircularConvBlock(64, 32, (3, 3, 3)),
            nn.Conv3d(32, 2, 1),
        )

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        out = self.net(x)
        return {"scar_wall_logit": out[:, 0:1], "scar_wall_sdf": out[:, 1:2]}


class EdemaWallFieldHead(nn.Module):
    """Pure-edema low-frequency surface plus local radial field."""

    def __init__(self, in_channels: int = 48) -> None:
        super().__init__()
        self.surface = nn.Sequential(
            CircularConvBlock(in_channels, 48, (3, 9, 1)),
            CircularConvBlock(48, 48, (3, 7, 1)),
            CircularConvBlock(48, 24, (3, 5, 1)),
            nn.Conv3d(24, 1, 1),
        )
        self.radial = nn.Sequential(_conv(in_channels, 24, (1, 1, 5)), nn.Conv3d(24, 1, (1, 1, 3), padding=(0, 0, 1)))

    def forward(self, x: torch.Tensor, availability: torch.Tensor) -> dict[str, torch.Tensor]:
        t2 = availability[:, 1:2].view(-1, 1, 1, 1, 1).to(x)
        logit = (self.surface(x) + self.radial(x)) * t2 + (1.0 - t2) * -16.0
        return {"edema_wall_logit": logit, "edema_boundary": self.surface(x)}


class MyoWallPilotModel(nn.Module):
    """One-arm pilot model; stock F0/anatomy features are provided frozen."""

    allowed_arms = ("C0", "W1", "W2", "W3")

    def __init__(self, arm: str, *, in_channels: int = 48, inverse: WallInverseTransform | None = None) -> None:
        super().__init__()
        if arm not in self.allowed_arms:
            raise ValueError(f"unknown arm {arm}")
        self.arm = arm
        self.inverse = inverse or WallInverseTransform()
        if arm == "C0":
            self.cartesian_head = CartesianMatchedPathologyHead(in_channels)
            self.scar_wall_head = None
            self.edema_wall_head = None
        else:
            self.cartesian_head = None
            self.scar_wall_head = ScarWallFieldHead(in_channels)
            self.edema_wall_head = EdemaWallFieldHead(in_channels)

    def forward(self, features: torch.Tensor, availability: torch.Tensor, *, geometry: WallGeometry | None = None, output_shape: tuple[int, int, int] | None = None) -> dict[str, torch.Tensor]:
        if self.arm == "C0":
            out = self.cartesian_head(features, availability)  # type: ignore[operator]
            return {**out, "final_scar_logit": out["scar_logit"], "final_edema_logit": out["edema_logit"]}
        if geometry is None or output_shape is None:
            raise ValueError("wall arms require geometry and output_shape")
        if self.arm == "W3":
            features = features.clone()
            features[:, 32:35].zero_()
        scar = self.scar_wall_head(features)  # type: ignore[operator]
        edema = self.edema_wall_head(features, availability)  # type: ignore[operator]
        scar_cart = self.inverse(scar["scar_wall_logit"], geometry, output_shape=output_shape)
        edema_cart = self.inverse(edema["edema_wall_logit"], geometry, output_shape=output_shape)
        t2 = availability[:, 1:2].view(-1, 1, 1, 1, 1).to(features)
        edema_cart = edema_cart * t2 + (1.0 - t2) * -16.0
        return {**scar, **edema, "final_scar_logit": scar_cart, "final_edema_logit": edema_cart}

    def trainable_parameter_count(self) -> int:
        return int(sum(p.numel() for p in self.parameters() if p.requires_grad))


def _dice_loss(logit: torch.Tensor, target: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
    prob = torch.sigmoid(logit)
    if mask is not None:
        prob = prob * mask
        target = target * mask
    inter = (prob * target).sum()
    den = prob.sum() + target.sum()
    return 1.0 - (2.0 * inter + 1.0) / (den + 1.0)


class MyoWallPilotLoss(nn.Module):
    """Blueprint-weighted pilot loss with no-T2 pure-edema exact zero semantics."""

    def __init__(self, *, arm: str = "W1") -> None:
        super().__init__()
        self.arm = arm

    def forward(self, outputs: dict[str, torch.Tensor], targets: dict[str, torch.Tensor], availability: torch.Tensor) -> dict[str, torch.Tensor]:
        scar_t = targets["scar"].to(outputs["final_scar_logit"])
        edema_t = targets["pure_edema"].to(outputs["final_edema_logit"])
        t2 = availability[:, 1:2].view(-1, 1, 1, 1, 1).to(outputs["final_edema_logit"])
        scar_bce = F.binary_cross_entropy_with_logits(outputs["final_scar_logit"], scar_t)
        scar_dice = _dice_loss(outputs["final_scar_logit"], scar_t)
        edema_raw = F.binary_cross_entropy_with_logits(outputs["final_edema_logit"], edema_t, reduction="none")
        edema_bce = (edema_raw * t2).sum() / t2.expand_as(edema_raw).sum().clamp_min(1.0)
        edema_dice = _dice_loss(outputs["final_edema_logit"], edema_t, t2)
        component_guard = outputs["final_scar_logit"].new_tensor(0.0)
        if self.arm not in {"C0", "W2"}:
            component_guard = 0.15 * torch.relu(torch.sigmoid(outputs["final_scar_logit"]) - 0.01).mean()
        rank_terms = outputs["final_scar_logit"].new_tensor(0.0)
        if self.arm != "W3":
            rank_terms = 0.0 * outputs["final_scar_logit"].mean()
        total = scar_bce + scar_dice + edema_bce + edema_dice + component_guard + rank_terms
        return {
            "total": total,
            "scar_dice_ce": scar_bce + scar_dice,
            "pure_edema_dice_ce": edema_bce + edema_dice,
            "component_guard": component_guard,
            "rank_terms": rank_terms,
            "no_t2_edema_loss_exact_zero": ((edema_raw * (1.0 - t2)).sum() * 0.0),
        }
