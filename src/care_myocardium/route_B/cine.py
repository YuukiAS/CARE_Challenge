"""Route B Cine adapter, registration, and temporal path."""

from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


def _conv(cin: int, cout: int) -> nn.Sequential:
    return nn.Sequential(nn.Conv3d(cin, cout, 3, padding=1), nn.GroupNorm(1, cout), nn.SiLU())


def _grid(shape: tuple[int, int, int], device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    d, h, w = shape
    z, y, x = torch.meshgrid(
        torch.linspace(-1, 1, d, device=device, dtype=dtype),
        torch.linspace(-1, 1, h, device=device, dtype=dtype),
        torch.linspace(-1, 1, w, device=device, dtype=dtype),
        indexing="ij",
    )
    return torch.stack([x, y, z], dim=-1)


def warp(volume: torch.Tensor, displacement: torch.Tensor) -> torch.Tensor:
    base = _grid(volume.shape[-3:], volume.device, volume.dtype).unsqueeze(0).expand(volume.shape[0], -1, -1, -1, -1)
    disp = displacement.permute(0, 2, 3, 4, 1)
    return F.grid_sample(volume, base + disp, mode="bilinear", padding_mode="border", align_corners=True)


def displacement_smoothness(displacement: torch.Tensor) -> torch.Tensor:
    dz = displacement[:, :, 1:] - displacement[:, :, :-1]
    dy = displacement[:, :, :, 1:] - displacement[:, :, :, :-1]
    dx = displacement[:, :, :, :, 1:] - displacement[:, :, :, :, :-1]
    return dz.square().mean() + dy.square().mean() + dx.square().mean()


def jacobian_fold_fraction(displacement: torch.Tensor) -> torch.Tensor:
    # Fast finite-difference plausibility proxy for tiny gate volumes.
    dz = displacement[:, 2:3, 1:] - displacement[:, 2:3, :-1]
    dy = displacement[:, 1:2, :, 1:] - displacement[:, 1:2, :, :-1]
    dx = displacement[:, 0:1, :, :, 1:] - displacement[:, 0:1, :, :, :-1]
    neg = (dz < -1).float().mean() + (dy < -1).float().mean() + (dx < -1).float().mean()
    return neg / 3


class CineFrameAdapter(nn.Module):
    def __init__(self, hidden: int = 8, classes: int = 4) -> None:
        super().__init__()
        self.encoder = nn.Sequential(_conv(1, hidden), _conv(hidden, hidden))
        self.logits = nn.Conv3d(hidden, classes, 1)
        self.features = nn.Conv3d(hidden, hidden, 1)

    def forward(self, frame: torch.Tensor) -> dict[str, torch.Tensor]:
        hidden = self.encoder(frame)
        logits = self.logits(hidden)
        prob = torch.softmax(logits, dim=1).clamp_min(1e-6)
        uncertainty = -(prob * prob.log()).sum(dim=1, keepdim=True) / torch.log(torch.tensor(float(logits.shape[1]), device=logits.device))
        return {"logits": logits, "features": self.features(hidden), "uncertainty": uncertainty}


class LearnedRegistration(nn.Module):
    def __init__(self, hidden: int = 8) -> None:
        super().__init__()
        self.net = nn.Sequential(_conv(2, hidden), _conv(hidden, hidden), nn.Conv3d(hidden, 3, 3, padding=1))

    def forward(self, fixed: torch.Tensor, moving: torch.Tensor) -> dict[str, torch.Tensor]:
        velocity = 0.15 * torch.tanh(self.net(torch.cat([fixed, moving], dim=1)))
        half = velocity / 2.0
        displacement = half + warp(half, half)
        inverse = -displacement
        return {
            "velocity": velocity,
            "displacement": displacement,
            "inverse": inverse,
            "warped": warp(moving, displacement),
            "smoothness": displacement_smoothness(displacement),
            "fold_fraction": jacobian_fold_fraction(displacement),
        }


def classical_tensor_registration_control(fixed: torch.Tensor, moving: torch.Tensor) -> dict[str, torch.Tensor]:
    """Deterministic image-based translation search used as a classical control."""

    best_score = None
    best_shift = (0, 0, 0)
    for dz in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                shifted = torch.roll(moving, shifts=(dz, dy, dx), dims=(-3, -2, -1))
                score = F.cosine_similarity(fixed.flatten(1), shifted.flatten(1), dim=1).mean()
                if best_score is None or bool(score > best_score):
                    best_score = score
                    best_shift = (dz, dy, dx)
    displacement = torch.zeros(fixed.shape[0], 3, *fixed.shape[-3:], device=fixed.device, dtype=fixed.dtype)
    d, h, w = fixed.shape[-3:]
    displacement[:, 0] = 2.0 * best_shift[2] / max(w - 1, 1)
    displacement[:, 1] = 2.0 * best_shift[1] / max(h - 1, 1)
    displacement[:, 2] = 2.0 * best_shift[0] / max(d - 1, 1)
    return {"method": "classical_exhaustive_translation_control", "displacement": displacement, "warped": warp(moving, displacement), "score": best_score}


class TemporalDictionary(nn.Module):
    def __init__(self, channels: int, slots: int = 8) -> None:
        super().__init__()
        self.slots = nn.Parameter(torch.randn(slots, channels) * 0.05)
        self.router = nn.Sequential(nn.Linear(channels + 4, 32), nn.SiLU(), nn.Linear(32, slots))

    def forward(self, evidence: torch.Tensor, quality: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # evidence: B,T,C,D,H,W; quality: B,T,4
        pooled = evidence.mean(dim=(-3, -2, -1))
        logits = self.router(torch.cat([pooled, quality], dim=-1))
        beta = torch.softmax(logits, dim=-1)
        context = torch.einsum("bts,sc->btc", beta, self.slots)
        routed = evidence + context[..., None, None, None]
        return routed, beta


class RouteBCineModel(nn.Module):
    def __init__(self, hidden: int = 8, classes: int = 4) -> None:
        super().__init__()
        self.adapter = CineFrameAdapter(hidden=hidden, classes=classes)
        self.registration = LearnedRegistration(hidden=hidden)
        self.temporal = TemporalDictionary(channels=hidden + classes + 4)
        self.refiner = nn.Sequential(_conv(hidden + classes + 4, hidden), nn.Conv3d(hidden, classes, 1))

    def forward(
        self,
        frames: torch.Tensor,
        *,
        reference_index: int = 0,
        disable_temporal: bool = False,
        use_registered: bool = True,
    ) -> dict[str, torch.Tensor | list[dict[str, torch.Tensor]]]:
        b, t, _, d, h, w = frames.shape
        per_frame = [self.adapter(frames[:, idx]) for idx in range(t)]
        fixed = frames[:, reference_index]
        registered_evidence = []
        registration_reports = []
        for idx, item in enumerate(per_frame):
            image = frames[:, idx]
            if idx == reference_index or not use_registered:
                displacement = torch.zeros(b, 3, d, h, w, device=frames.device, dtype=frames.dtype)
                warped_image = image
                warped_logits = item["logits"]
                fold_fraction = torch.zeros((), device=frames.device, dtype=frames.dtype)
                smoothness = torch.zeros((), device=frames.device, dtype=frames.dtype)
            else:
                reg = self.registration(fixed, image)
                displacement = reg["displacement"]
                warped_image = reg["warped"]
                warped_logits = warp(item["logits"], displacement)
                fold_fraction = reg["fold_fraction"]
                smoothness = reg["smoothness"]
            uncertainty = item["uncertainty"]
            quality = torch.stack(
                [
                    torch.full((b,), float(idx == reference_index), device=frames.device, dtype=frames.dtype),
                    torch.full((b,), float(idx) / max(t - 1, 1), device=frames.device, dtype=frames.dtype),
                    smoothness.expand(b),
                    fold_fraction.expand(b),
                ],
                dim=1,
            )
            evidence = torch.cat([item["features"], warped_logits, uncertainty, displacement], dim=1)
            registered_evidence.append(evidence)
            registration_reports.append({"displacement": displacement, "warped_image": warped_image, "quality": quality})
        evidence_tensor = torch.stack(registered_evidence, dim=1)
        quality_tensor = torch.stack([r["quality"] for r in registration_reports], dim=1)
        if disable_temporal:
            aggregate = evidence_tensor[:, reference_index]
            beta = torch.zeros(b, t, 8, device=frames.device, dtype=frames.dtype)
        else:
            routed, beta = self.temporal(evidence_tensor, quality_tensor)
            frame_weight = torch.softmax(quality_tensor[..., 0] - quality_tensor[..., 2], dim=1).view(b, t, 1, 1, 1, 1)
            aggregate = (routed * frame_weight).sum(dim=1)
        logits = self.refiner(aggregate)
        return {"logits": logits, "beta": beta, "registration_reports": registration_reports, "quality": quality_tensor}


def route_b_cine_loss(outputs: dict[str, torch.Tensor], target: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
    ce = F.cross_entropy(outputs["logits"], target.long())
    beta = outputs["beta"]
    load = beta.mean(dim=(0, 1)).square().sum() if beta.numel() else ce * 0
    smooth = torch.stack([r["quality"][..., 2].mean() for r in outputs["registration_reports"]]).mean()
    fold = torch.stack([r["quality"][..., 3].mean() for r in outputs["registration_reports"]]).mean()
    total = ce + 0.01 * load + 0.05 * smooth + 0.05 * fold
    return total, {
        "ce": float(ce.detach().cpu()),
        "temporal_load": float(load.detach().cpu()),
        "registration_smooth": float(smooth.detach().cpu()),
        "registration_fold": float(fold.detach().cpu()),
        "total": float(total.detach().cpu()),
    }
