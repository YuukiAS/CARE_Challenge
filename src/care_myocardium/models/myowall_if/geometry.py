"""Wall-coordinate transforms and deterministic rank features."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import torch
import torch.nn.functional as F


@dataclass
class WallGeometry:
    centroids_xy: torch.Tensor
    endo_radii: torch.Tensor
    epi_radii: torch.Tensor
    valid: torch.Tensor
    active_slices: torch.Tensor | None = None
    raw_valid: torch.Tensor | None = None
    spacing_zyx: tuple[float, float, float] = (1.0, 1.0, 1.0)


def _theta_values(angles: int, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    return torch.linspace(-math.pi, math.pi, angles + 1, device=device, dtype=dtype)[:-1]


class FrozenStockGeometryCacheBuilder:
    """Builds predicted LV/wall geometry from frozen stock anatomy probabilities."""

    def __init__(self, *, angles: int = 256, min_thickness_mm: float = 1.5, max_thickness_mm: float = 25.0, lv_threshold: float = 0.35, wall_threshold: float = 0.20) -> None:
        self.angles = int(angles)
        self.min_thickness_mm = float(min_thickness_mm)
        self.max_thickness_mm = float(max_thickness_mm)
        self.lv_threshold = float(lv_threshold)
        self.wall_threshold = float(wall_threshold)

    def _repair_angular_gaps(self, endo: torch.Tensor, epi: torch.Tensor, valid: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        repaired_endo = endo.clone()
        repaired_epi = epi.clone()
        repaired_valid = valid.clone()
        angles = valid.numel()
        for idx in range(angles):
            if bool(valid[idx]):
                continue
            valid_idx = torch.nonzero(valid, as_tuple=False).flatten()
            if valid_idx.numel() == 0:
                continue
            circular_delta = torch.remainder(valid_idx - idx + angles // 2, angles) - angles // 2
            nearest = valid_idx[torch.argmin(circular_delta.abs())]
            repaired_endo[idx] = endo[nearest]
            repaired_epi[idx] = epi[nearest]
            repaired_valid[idx] = True
        return repaired_endo, repaired_epi, repaired_valid

    def build_from_probabilities(self, p_lv: torch.Tensor, p_wall: torch.Tensor, *, spacing_zyx: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> WallGeometry:
        if p_lv.ndim == 5:
            p_lv = p_lv[0, 0]
        if p_wall.ndim == 5:
            p_wall = p_wall[0, 0]
        if p_lv.shape != p_wall.shape:
            raise ValueError("p_lv and p_wall must share [Z,Y,X] shape")
        z, y, x = p_lv.shape
        yy, xx = torch.meshgrid(
            torch.arange(y, device=p_lv.device, dtype=p_lv.dtype),
            torch.arange(x, device=p_lv.device, dtype=p_lv.dtype),
            indexing="ij",
        )
        centroids = []
        endo = []
        epi = []
        valid_rows = []
        raw_valid_rows = []
        active_rows = []
        theta = _theta_values(self.angles, p_lv.device, p_lv.dtype)
        cos_t, sin_t = torch.cos(theta), torch.sin(theta)
        max_radius = float(math.sqrt(float(y * y + x * x)))
        radii = torch.linspace(0.0, max_radius, 384, device=p_lv.device, dtype=p_lv.dtype)
        for zi in range(z):
            lv = (p_lv[zi] >= self.lv_threshold).float()
            wall = (p_wall[zi] >= self.wall_threshold).float()
            active_rows.append((lv.sum() >= 16) & (wall.sum() >= 16))
            mass = lv.sum().clamp_min(1.0)
            cy = (yy * lv).sum() / mass
            cx = (xx * lv).sum() / mass
            centroids.append(torch.stack([cy, cx]))
            xs = cx + radii[:, None] * cos_t[None, :]
            ys = cy + radii[:, None] * sin_t[None, :]
            grid_x = xs / max(x - 1, 1) * 2 - 1
            grid_y = ys / max(y - 1, 1) * 2 - 1
            grid = torch.stack([grid_x, grid_y], dim=-1).view(1, -1, self.angles, 2)
            lv_s = F.grid_sample(lv.view(1, 1, y, x), grid, mode="bilinear", align_corners=True)[0, 0]
            wall_s = F.grid_sample(wall.view(1, 1, y, x), grid, mode="bilinear", align_corners=True)[0, 0]
            in_wall = wall_s >= 0.5
            lv_core = lv_s >= 0.5
            first_wall = torch.argmax(in_wall.to(torch.int64), dim=0)
            last_lv = torch.flip(lv_core, dims=(0,)).to(torch.int64).argmax(dim=0)
            last_lv = (radii.numel() - 1) - last_lv
            any_lv = lv_core.any(dim=0)
            any_endo = in_wall.any(dim=0)
            endo_idx = torch.where(any_lv & (last_lv < first_wall), last_lv + 1, first_wall).clamp(max=radii.numel() - 1)
            epi_idx = torch.flip(in_wall, dims=(0,)).to(torch.int64).argmax(dim=0)
            epi_idx = (radii.numel() - 1) - epi_idx
            any_epi = in_wall.any(dim=0)
            r_endo = radii[endo_idx]
            r_epi = radii[epi_idx]
            thickness = (r_epi - r_endo) * float(spacing_zyx[-1])
            ok = any_endo & any_epi & (thickness >= self.min_thickness_mm) & (thickness <= self.max_thickness_mm)
            raw_ok = ok.clone()
            if bool(active_rows[-1]) and float(ok.float().mean().item()) >= 0.90:
                r_endo, r_epi, ok = self._repair_angular_gaps(r_endo, r_epi, ok)
            endo.append(r_endo)
            epi.append(r_epi)
            raw_valid_rows.append(raw_ok)
            valid_rows.append(ok)
        raw_valid = torch.stack(raw_valid_rows)
        return WallGeometry(torch.stack(centroids), torch.stack(endo), torch.stack(epi), torch.stack(valid_rows), torch.stack(active_rows).bool(), raw_valid, spacing_zyx)

    def metrics(self, geom: WallGeometry) -> dict[str, Any]:
        active = geom.active_slices
        valid_for_rate = geom.valid if active is None or not active.any() else geom.valid[active]
        raw_valid = geom.raw_valid if geom.raw_valid is not None else geom.valid
        raw_for_rate = raw_valid if active is None or not active.any() else raw_valid[active]
        valid_fraction = float(valid_for_rate.float().mean().item())
        return {
            "valid_angle_fraction": valid_fraction,
            "raw_valid_angle_fraction": float(raw_for_rate.float().mean().item()),
            "valid_slice_fraction": float((geom.valid.float().mean(dim=1) > 0.5).float().mean().item()),
            "active_slice_count": int(active.sum().item()) if active is not None else int(geom.valid.shape[0]),
            "geometry_valid": valid_fraction >= 0.95,
        }


class WallCoordinateTransform:
    """Samples Cartesian tensors onto a [Z, theta, rho] myocardial-wall lattice."""

    def __init__(self, *, radial_bins: int = 32, angles: int = 256, rho_min: float = -0.15, rho_max: float = 1.15) -> None:
        self.radial_bins = int(radial_bins)
        self.angles = int(angles)
        self.rho_min = float(rho_min)
        self.rho_max = float(rho_max)

    def grid(self, geom: WallGeometry, *, y: int, x: int, dtype: torch.dtype) -> torch.Tensor:
        device = geom.centroids_xy.device
        theta = _theta_values(self.angles, device, dtype)
        rho = torch.linspace(self.rho_min, self.rho_max, self.radial_bins, device=device, dtype=dtype)
        grids = []
        for zi in range(geom.centroids_xy.shape[0]):
            cy, cx = geom.centroids_xy[zi].to(dtype=dtype)
            r = geom.endo_radii[zi].to(dtype=dtype)[:, None] + rho[None, :] * (geom.epi_radii[zi].to(dtype=dtype) - geom.endo_radii[zi].to(dtype=dtype))[:, None]
            xs = cx + torch.cos(theta)[:, None] * r
            ys = cy + torch.sin(theta)[:, None] * r
            grid_x = xs / max(x - 1, 1) * 2 - 1
            grid_y = ys / max(y - 1, 1) * 2 - 1
            grid_z = torch.full_like(grid_x, zi / max(geom.centroids_xy.shape[0] - 1, 1) * 2 - 1)
            grids.append(torch.stack([grid_x, grid_y, grid_z], dim=-1))
        return torch.stack(grids, dim=0)

    def __call__(self, tensor: torch.Tensor, geom: WallGeometry, *, mode: str = "bilinear") -> torch.Tensor:
        if tensor.ndim != 5 or tensor.shape[0] != 1:
            raise ValueError("wall transform currently expects [1,C,Z,Y,X]")
        grid = self.grid(geom, y=tensor.shape[-2], x=tensor.shape[-1], dtype=tensor.dtype).unsqueeze(0)
        return F.grid_sample(tensor, grid, mode=mode, padding_mode="zeros", align_corners=True)


class WallInverseTransform:
    """Approximates wall-field projection back to Cartesian logits."""

    def __init__(self, *, radial_bins: int = 32, angles: int = 256, rho_min: float = -0.15, rho_max: float = 1.15) -> None:
        self.radial_bins = int(radial_bins)
        self.angles = int(angles)
        self.rho_min = float(rho_min)
        self.rho_max = float(rho_max)

    def __call__(self, wall_tensor: torch.Tensor, geom: WallGeometry, *, output_shape: tuple[int, int, int], outside_value: float = -16.0) -> torch.Tensor:
        if wall_tensor.ndim != 5 or wall_tensor.shape[0] != 1:
            raise ValueError("inverse wall transform expects [1,C,Z,A,R]")
        _z, y, x = output_shape
        yy, xx = torch.meshgrid(
            torch.arange(y, device=wall_tensor.device, dtype=wall_tensor.dtype),
            torch.arange(x, device=wall_tensor.device, dtype=wall_tensor.dtype),
            indexing="ij",
        )
        out = wall_tensor.new_full((1, wall_tensor.shape[1], output_shape[0], y, x), float(outside_value))
        for zi in range(output_shape[0]):
            cy, cx = geom.centroids_xy[zi].to(device=wall_tensor.device, dtype=wall_tensor.dtype)
            dy = yy - cy
            dx = xx - cx
            theta = torch.atan2(dy, dx)
            angle_idx = ((theta + math.pi) / (2 * math.pi) * self.angles).round().long().clamp(0, self.angles - 1)
            dist = torch.sqrt(dx * dx + dy * dy)
            re = geom.endo_radii[zi].to(wall_tensor.device, wall_tensor.dtype)[angle_idx]
            rp = geom.epi_radii[zi].to(wall_tensor.device, wall_tensor.dtype)[angle_idx]
            rho = (dist - re) / (rp - re).clamp_min(1e-4)
            radial_idx = ((rho - self.rho_min) / (self.rho_max - self.rho_min) * (self.radial_bins - 1)).round().long()
            valid = radial_idx.ge(0) & radial_idx.lt(self.radial_bins) & geom.valid[zi].to(wall_tensor.device)[angle_idx]
            vals = wall_tensor[0, :, zi].permute(1, 2, 0)[angle_idx, radial_idx.clamp(0, self.radial_bins - 1)]
            out[0, :, zi] = torch.where(valid.unsqueeze(0), vals.permute(2, 0, 1), out[0, :, zi])
        return out


class RobustWallRankFeatures:
    """Computes deterministic LGE/T2 rank and LGE high-frequency channels."""

    def __call__(self, images: torch.Tensor, p_wall: torch.Tensor, availability: torch.Tensor) -> dict[str, torch.Tensor]:
        if images.ndim != 5:
            raise ValueError("images must be [B,3,Z,Y,X]")
        wall = (p_wall > 0.30).to(images.dtype)
        ranks = []
        for channel in (0, 1):
            x = images[:, channel : channel + 1]
            vals = x[wall.bool()]
            if vals.numel() < 8:
                rank = torch.zeros_like(x)
            else:
                lo, hi = torch.quantile(vals.float(), torch.tensor([0.01, 0.99], device=x.device))
                clipped = x.clamp(lo, hi)
                rank = ((clipped - lo) / (hi - lo).clamp_min(1e-6)).clamp(0, 1) * wall
            ranks.append(rank)
        if availability.ndim == 2:
            t2_mask = availability[:, 1:2].view(-1, 1, 1, 1, 1).to(images)
        else:
            t2_mask = availability.to(images)
        blur = F.avg_pool3d(images[:, 0:1], kernel_size=(1, 5, 5), stride=1, padding=(0, 2, 2))
        high = (images[:, 0:1] - blur) * wall
        std = high[wall.bool()].float().std(unbiased=False).clamp_min(1e-6) if wall.bool().any() else high.new_tensor(1.0)
        return {"lge_rank": ranks[0], "t2_rank": ranks[1] * t2_mask, "lge_highfreq": (high / std).clamp(-5, 5)}
