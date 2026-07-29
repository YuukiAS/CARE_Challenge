"""CARE-ARC single-encoder complete pathology reconstruction model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from torch import nn
import torch.nn.functional as F


MODALITY_ORDER = ("LGE", "T2", "C0")
SCAR_LABEL = 5
EDEMA_LABEL = 4


@dataclass(frozen=True)
class CAREARCConfig:
    in_modalities: int = 3
    stem_channels: int = 16
    fusion_channels: int = 48
    encoder_channels: tuple[int, int, int, int] = (48, 64, 128, 256)
    decoder_channels: tuple[int, int, int] = (128, 64, 32)
    anatomy_classes: int = 4
    alignment_enabled: bool = True
    alignment_offset_limit: float = 4.0
    edema_missing_exact_zero_logit: float = 0.0


def _norm(channels: int) -> nn.InstanceNorm3d:
    return nn.InstanceNorm3d(channels, affine=True)


def _kernel(level: int) -> tuple[int, int, int]:
    return (1, 3, 3) if level <= 1 else (3, 3, 3)


class ResidualBlock3D(nn.Module):
    def __init__(self, channels: int, *, level: int, dilation: int | tuple[int, int, int] = 1) -> None:
        super().__init__()
        kernel = _kernel(level)
        if isinstance(dilation, int):
            dilation_tuple = (1, dilation, dilation) if kernel[0] == 1 else (dilation, dilation, dilation)
        else:
            dilation_tuple = dilation
        padding = tuple((k // 2) * d for k, d in zip(kernel, dilation_tuple))
        self.block = nn.Sequential(
            nn.Conv3d(channels, channels, kernel, padding=padding, dilation=dilation_tuple, bias=False),
            _norm(channels),
            nn.SiLU(inplace=True),
            nn.Conv3d(channels, channels, kernel, padding=padding, dilation=dilation_tuple, bias=False),
            _norm(channels),
        )
        self.act = nn.SiLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(x + self.block(x))


class ModalityStem(nn.Module):
    def __init__(self, out_channels: int = 16) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(1, out_channels, (1, 3, 3), padding=(0, 1, 1), bias=False),
            _norm(out_channels),
            nn.SiLU(inplace=True),
            ResidualBlock3D(out_channels, level=0),
            ResidualBlock3D(out_channels, level=0),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class EncoderStage(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, *, level: int, stride: tuple[int, int, int], blocks: int) -> None:
        super().__init__()
        kernel = _kernel(level)
        padding = tuple(k // 2 for k in kernel)
        layers: list[nn.Module] = [
            nn.Conv3d(in_channels, out_channels, kernel, stride=stride, padding=padding, bias=False),
            _norm(out_channels),
            nn.SiLU(inplace=True),
        ]
        layers.extend(ResidualBlock3D(out_channels, level=level) for _ in range(blocks))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class CAREARCEncoder(nn.Module):
    """The single shared CARE-ARC encoder."""

    def __init__(self, channels: tuple[int, int, int, int] = (48, 64, 128, 256)) -> None:
        super().__init__()
        c0, c1, c2, c3 = channels
        self.e0 = EncoderStage(c0, c0, level=0, stride=(1, 1, 1), blocks=2)
        self.e1 = EncoderStage(c0, c1, level=1, stride=(1, 2, 2), blocks=2)
        self.e2 = EncoderStage(c1, c2, level=2, stride=(1, 2, 2), blocks=3)
        self.e3 = EncoderStage(c2, c3, level=3, stride=(1, 2, 2), blocks=3)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        e0 = self.e0(x)
        e1 = self.e1(e0)
        e2 = self.e2(e1)
        e3 = self.e3(e2)
        return e0, e1, e2, e3


class FeatureAlignmentE2(nn.Module):
    """Identity-initialized LGE-reference alignment at the E2 in-plane scale."""

    def __init__(self, stem_channels: int, e2_channels: int, offset_limit: float = 4.0) -> None:
        super().__init__()
        self.offset_limit = float(offset_limit)
        self.lge_to_e2 = nn.Sequential(
            nn.Conv3d(stem_channels, e2_channels, (1, 3, 3), stride=(1, 4, 4), padding=(0, 1, 1), bias=False),
            _norm(e2_channels),
            nn.SiLU(inplace=True),
        )
        self.t2_to_e2 = nn.Sequential(
            nn.Conv3d(stem_channels, e2_channels, (1, 3, 3), stride=(1, 4, 4), padding=(0, 1, 1), bias=False),
            _norm(e2_channels),
            nn.SiLU(inplace=True),
        )
        self.c0_to_e2 = nn.Sequential(
            nn.Conv3d(stem_channels, e2_channels, (1, 3, 3), stride=(1, 4, 4), padding=(0, 1, 1), bias=False),
            _norm(e2_channels),
            nn.SiLU(inplace=True),
        )
        self.t2_offset = nn.Conv3d(e2_channels * 2, 3, 3, padding=1)
        self.c0_offset = nn.Conv3d(e2_channels * 2, 3, 3, padding=1)
        self.t2_confidence = nn.Conv3d(e2_channels * 2, 1, 3, padding=1)
        self.c0_confidence = nn.Conv3d(e2_channels * 2, 1, 3, padding=1)
        self.mix = nn.Conv3d(e2_channels, e2_channels, 1, bias=False)
        self.reset_identity()

    def reset_identity(self) -> None:
        for layer in (self.t2_offset, self.c0_offset):
            nn.init.zeros_(layer.weight)
            nn.init.zeros_(layer.bias)
        for layer in (self.t2_confidence, self.c0_confidence):
            nn.init.zeros_(layer.weight)
            nn.init.constant_(layer.bias, -4.0)

    def _warp(self, feature: torch.Tensor, offset_pixels: torch.Tensor) -> torch.Tensor:
        b, _c, d, h, w = feature.shape
        dtype = feature.dtype
        device = feature.device
        z = torch.linspace(-1.0, 1.0, d, device=device, dtype=dtype)
        y = torch.linspace(-1.0, 1.0, h, device=device, dtype=dtype)
        x = torch.linspace(-1.0, 1.0, w, device=device, dtype=dtype)
        zz, yy, xx = torch.meshgrid(z, y, x, indexing="ij")
        grid = torch.stack((xx, yy, zz), dim=-1).expand(b, d, h, w, 3).clone()
        scale = feature.new_tensor([max(w - 1, 1) / 2.0, max(h - 1, 1) / 2.0, max(d - 1, 1) / 2.0])
        delta = offset_pixels.permute(0, 2, 3, 4, 1)[..., [2, 1, 0]] / scale
        return F.grid_sample(feature, grid + delta, mode="bilinear", padding_mode="border", align_corners=True)

    def forward(
        self,
        stem_features: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
        e2: torch.Tensor,
        availability: torch.Tensor,
        *,
        enabled: bool,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        lge, t2, c0 = stem_features
        lge_e2 = self.lge_to_e2(lge)
        t2_e2 = self.t2_to_e2(t2)
        c0_e2 = self.c0_to_e2(c0)
        if lge_e2.shape[-3:] != e2.shape[-3:]:
            lge_e2 = F.interpolate(lge_e2, size=e2.shape[-3:], mode="trilinear", align_corners=False)
            t2_e2 = F.interpolate(t2_e2, size=e2.shape[-3:], mode="trilinear", align_corners=False)
            c0_e2 = F.interpolate(c0_e2, size=e2.shape[-3:], mode="trilinear", align_corners=False)
        t2_pair = torch.cat([lge_e2, t2_e2], dim=1)
        c0_pair = torch.cat([lge_e2, c0_e2], dim=1)
        t2_offset = self.offset_limit * torch.tanh(self.t2_offset(t2_pair))
        c0_offset = self.offset_limit * torch.tanh(self.c0_offset(c0_pair))
        t2_conf = torch.sigmoid(self.t2_confidence(t2_pair))
        c0_conf = torch.sigmoid(self.c0_confidence(c0_pair))
        if not enabled:
            t2_offset = torch.zeros_like(t2_offset)
            c0_offset = torch.zeros_like(c0_offset)
            t2_conf = torch.zeros_like(t2_conf)
            c0_conf = torch.zeros_like(c0_conf)
        t2_mask = availability[:, 1].view(-1, 1, 1, 1, 1).to(device=e2.device, dtype=e2.dtype)
        c0_mask = availability[:, 2].view(-1, 1, 1, 1, 1).to(device=e2.device, dtype=e2.dtype)
        t2_aligned = t2_conf * self._warp(t2_e2, t2_offset) + (1.0 - t2_conf) * t2_e2
        c0_aligned = c0_conf * self._warp(c0_e2, c0_offset) + (1.0 - c0_conf) * c0_e2
        update = (t2_aligned - t2_e2) * t2_mask + (c0_aligned - c0_e2) * c0_mask
        return e2 + self.mix(update), {
            "t2_offset": t2_offset,
            "c0_offset": c0_offset,
            "t2_confidence": t2_conf * t2_mask,
            "c0_confidence": c0_conf * c0_mask,
        }


class EvidenceGate(nn.Module):
    def __init__(self, stem_channels: int, hidden: int = 16, order: tuple[int, int, int] = (0, 1, 2)) -> None:
        super().__init__()
        self.order = tuple(order)
        self.mlp = nn.Sequential(
            nn.Linear(stem_channels * 3 + 3, hidden),
            nn.SiLU(inplace=True),
            nn.Linear(hidden, 3),
        )

    def forward(self, stem_features: tuple[torch.Tensor, torch.Tensor, torch.Tensor], availability: torch.Tensor) -> torch.Tensor:
        pooled = [feat.mean(dim=(2, 3, 4)) for feat in stem_features]
        x = torch.cat([*pooled, availability.to(device=pooled[0].device, dtype=pooled[0].dtype)], dim=1)
        logits = self.mlp(x)
        availability_ordered = availability[:, list(self.order)].to(device=logits.device, dtype=logits.dtype)
        logits = logits.masked_fill(availability_ordered <= 0, -1.0e4)
        weights_ordered = torch.softmax(logits, dim=1) * availability_ordered
        weights_ordered = weights_ordered / weights_ordered.sum(dim=1, keepdim=True).clamp_min(1.0e-6)
        weights = torch.zeros_like(weights_ordered)
        for src_idx, modality_idx in enumerate(self.order):
            weights[:, modality_idx] = weights_ordered[:, src_idx]
        return weights


class DecoderBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, *, level: int, extra_dilation: bool = False) -> None:
        super().__init__()
        layers: list[nn.Module] = [
            nn.Conv3d(in_channels, out_channels, _kernel(level), padding=tuple(k // 2 for k in _kernel(level)), bias=False),
            _norm(out_channels),
            nn.SiLU(inplace=True),
            ResidualBlock3D(out_channels, level=level),
        ]
        if extra_dilation:
            layers.extend([ResidualBlock3D(out_channels, level=level, dilation=2), ResidualBlock3D(out_channels, level=level, dilation=3)])
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class AnatomyDecoder(nn.Module):
    def __init__(self, enc: tuple[int, int, int, int], dec: tuple[int, int, int], classes: int) -> None:
        super().__init__()
        c0, c1, c2, c3 = enc
        d2, d1, d0 = dec
        self.up2 = DecoderBlock(c3 + c2, d2, level=2)
        self.up1 = DecoderBlock(d2 + c1, d1, level=1)
        self.up0 = DecoderBlock(d1 + c0, d0, level=0)
        self.head = nn.Conv3d(d0, classes, 1)

    def forward(self, scales: tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
        e0, e1, e2, e3 = scales
        x = F.interpolate(e3, size=e2.shape[-3:], mode="trilinear", align_corners=False)
        x = self.up2(torch.cat([x, e2], dim=1))
        x = F.interpolate(x, size=e1.shape[-3:], mode="trilinear", align_corners=False)
        x = self.up1(torch.cat([x, e1], dim=1))
        x = F.interpolate(x, size=e0.shape[-3:], mode="trilinear", align_corners=False)
        x = self.up0(torch.cat([x, e0], dim=1))
        return self.head(x), x


class PathologyDecoder(nn.Module):
    def __init__(
        self,
        name: str,
        enc: tuple[int, int, int, int],
        dec: tuple[int, int, int],
        stem_channels: int,
        *,
        skip_modality_index: int,
        scar_like: bool,
    ) -> None:
        super().__init__()
        self.name = name
        c0, c1, c2, c3 = enc
        d2, d1, d0 = dec
        self.skip_modality_index = int(skip_modality_index)
        self.coarse_head = nn.Conv3d(c2, 1, 1)
        self.up2 = DecoderBlock(c3 + c2, d2, level=2, extra_dilation=not scar_like)
        self.up1 = DecoderBlock(d2 + c1, d1, level=1)
        self.up0 = DecoderBlock(d1 + c0 + stem_channels, d0, level=0)
        self.burden_head = nn.Sequential(nn.AdaptiveAvgPool3d(1), nn.Flatten(), nn.Linear(c3, 64), nn.SiLU(inplace=True), nn.Linear(64, 1))
        self.presence_head = nn.Sequential(nn.AdaptiveAvgPool3d(1), nn.Flatten(), nn.Linear(c3, 64), nn.SiLU(inplace=True), nn.Linear(64, 1))
        self.film = nn.Sequential(nn.Linear(1, 64), nn.SiLU(inplace=True), nn.Linear(64, d0 * 2))
        self.direct_head = nn.Conv3d(d0, 1, 1)
        self.sdf_mean_head = nn.Conv3d(d0, 1, 1)
        self.sdf_logvar_head = nn.Conv3d(d0, 1, 1)

    def forward(
        self,
        scales: tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],
        stem_features: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    ) -> dict[str, torch.Tensor]:
        e0, e1, e2, e3 = scales
        coarse = self.coarse_head(e2)
        x = F.interpolate(e3, size=e2.shape[-3:], mode="trilinear", align_corners=False)
        x = self.up2(torch.cat([x, e2], dim=1))
        x = F.interpolate(x, size=e1.shape[-3:], mode="trilinear", align_corners=False)
        x = self.up1(torch.cat([x, e1], dim=1))
        x = F.interpolate(x, size=e0.shape[-3:], mode="trilinear", align_corners=False)
        skip = stem_features[self.skip_modality_index]
        if skip.shape[-3:] != e0.shape[-3:]:
            skip = F.interpolate(skip, size=e0.shape[-3:], mode="trilinear", align_corners=False)
        x = self.up0(torch.cat([x, e0, skip], dim=1))
        log_burden = self.burden_head(e3)
        gamma_beta = self.film(log_burden).view(x.shape[0], 2, x.shape[1], 1, 1, 1)
        x_film = x * (1.0 + gamma_beta[:, 0]) + gamma_beta[:, 1]
        return {
            "coarse_extent_logit": coarse,
            "direct_full_logit": self.direct_head(x_film),
            "presence_logit": self.presence_head(e3),
            "log_burden_pred": log_burden,
            "sdf_mean": self.sdf_mean_head(x),
            "sdf_logvar": self.sdf_logvar_head(x).clamp(-5.0, 3.0),
            "film_gamma": gamma_beta[:, 0],
            "film_beta": gamma_beta[:, 1],
            "pre_film_features": x,
            "post_film_features": x_film,
        }


def _availability_map(availability: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    if availability.ndim != 2 or availability.shape[1] != 3:
        raise ValueError("availability must be [B,3] in LGE,T2,C0 order")
    return availability.to(device=reference.device, dtype=reference.dtype).view(-1, 3, 1, 1, 1).expand(-1, -1, *reference.shape[-3:])


def _zero_pathology(outputs: dict[str, torch.Tensor], reference: torch.Tensor) -> dict[str, torch.Tensor]:
    out: dict[str, torch.Tensor] = {}
    for key, value in outputs.items():
        if torch.is_tensor(value):
            if value.ndim == 2:
                out[key] = value * 0.0
            elif value.ndim == 5:
                out[key] = value * 0.0
            else:
                out[key] = value * 0.0
        else:
            out[key] = value
    if out["direct_full_logit"].shape[-3:] != reference.shape[-3:]:
        out["direct_full_logit"] = reference.new_zeros((reference.shape[0], 1, *reference.shape[-3:]))
    return out


class CAREARC(nn.Module):
    """Single-backbone CARE-ARC model.

    The formal trainable pathology path consumes only images and availability.
    ``external_nnunet_context`` is accepted as an ignored audit placeholder so
    tests can prove invariance to OOF/ensemble/zero context substitutions.
    """

    def __init__(self, config: CAREARCConfig | None = None) -> None:
        super().__init__()
        self.config = config or CAREARCConfig()
        c = self.config
        self.lge_stem = ModalityStem(c.stem_channels)
        self.t2_stem = ModalityStem(c.stem_channels)
        self.c0_stem = ModalityStem(c.stem_channels)
        self.fusion = nn.Sequential(
            nn.Conv3d(c.stem_channels * 3 + 3, c.fusion_channels, 1, bias=False),
            _norm(c.fusion_channels),
            nn.SiLU(inplace=True),
        )
        self.encoder = CAREARCEncoder(c.encoder_channels)
        self.alignment = FeatureAlignmentE2(c.stem_channels, c.encoder_channels[2], c.alignment_offset_limit)
        self.scar_gates = nn.ModuleList(EvidenceGate(c.stem_channels, order=(0, 1, 2)) for _ in range(4))
        self.edema_gates = nn.ModuleList(EvidenceGate(c.stem_channels, order=(1, 0, 2)) for _ in range(4))
        self.anatomy_decoder = AnatomyDecoder(c.encoder_channels, c.decoder_channels, c.anatomy_classes)
        self.scar_decoder = PathologyDecoder(
            "scar",
            c.encoder_channels,
            c.decoder_channels,
            c.stem_channels,
            skip_modality_index=0,
            scar_like=True,
        )
        self.edema_decoder = PathologyDecoder(
            "edema",
            c.encoder_channels,
            c.decoder_channels,
            c.stem_channels,
            skip_modality_index=1,
            scar_like=False,
        )

    @property
    def shared_encoder_count(self) -> int:
        return 1

    def forward(
        self,
        images: torch.Tensor,
        availability: torch.Tensor,
        *,
        external_nnunet_context: dict[str, torch.Tensor] | torch.Tensor | None = None,
        alignment_mode: str | None = None,
        return_aux: bool = True,
    ) -> dict[str, Any]:
        if images.ndim != 5 or images.shape[1] != 3:
            raise ValueError("CARE-ARC images must be [B,3,D,H,W] in LGE,T2,C0 order")
        if images.shape[-3] < 1:
            raise ValueError("CARE-ARC requires full volume depth D>=1")
        if external_nnunet_context is not None:
            # Intentionally ignored: external nnU-Net context is audit-only and
            # never enters the trainable pathology graph.
            _ = external_nnunet_context
        availability = availability.to(device=images.device, dtype=images.dtype)
        av_map = _availability_map(availability, images)
        lge = self.lge_stem(images[:, 0:1] * av_map[:, 0:1])
        t2 = self.t2_stem(images[:, 1:2] * av_map[:, 1:2])
        c0 = self.c0_stem(images[:, 2:3] * av_map[:, 2:3])
        fused = self.fusion(torch.cat([lge, t2, c0, av_map], dim=1))
        e0, e1, e2, e3 = self.encoder(fused)
        align_enabled = self.config.alignment_enabled if alignment_mode is None else alignment_mode == "enabled"
        e2, alignment = self.alignment((lge, t2, c0), e2, availability, enabled=align_enabled)
        scales = (e0, e1, e2, e3)
        anatomy_logits, anatomy_features = self.anatomy_decoder(scales)
        scar = self.scar_decoder(scales, (lge, t2, c0))
        edema_raw = self.edema_decoder(scales, (lge, t2, c0))
        t2_present = availability[:, 1:2]
        if torch.any(t2_present <= 0):
            mask = t2_present.view(-1, 1, 1, 1, 1).to(dtype=images.dtype, device=images.device)
            edema = {k: (v * mask if torch.is_tensor(v) and v.ndim == 5 else v * t2_present if torch.is_tensor(v) and v.ndim == 2 else v) for k, v in edema_raw.items()}
        else:
            edema = edema_raw
        edema["direct_full_logit"] = edema["direct_full_logit"] * t2_present.view(-1, 1, 1, 1, 1).to(images)
        edema["coarse_extent_logit"] = edema["coarse_extent_logit"] * t2_present.view(-1, 1, 1, 1, 1).to(images)
        edema["sdf_mean"] = edema["sdf_mean"] * t2_present.view(-1, 1, 1, 1, 1).to(images)
        edema["sdf_logvar"] = edema["sdf_logvar"] * t2_present.view(-1, 1, 1, 1, 1).to(images)
        edema["presence_logit"] = edema["presence_logit"] * t2_present.to(images)
        edema["log_burden_pred"] = edema["log_burden_pred"] * t2_present.to(images)
        out: dict[str, Any] = {
            "anatomy_logits": anatomy_logits,
            "scar": scar,
            "edema": edema,
            "scar_direct_logit": scar["direct_full_logit"],
            "edema_zone_direct_logit": edema["direct_full_logit"],
            "alignment": alignment,
            "scar_gate_weights": [gate((lge, t2, c0), availability) for gate in self.scar_gates],
            "edema_gate_weights": [gate((lge, t2, c0), availability) for gate in self.edema_gates],
        }
        if return_aux:
            out["anatomy_features"] = anatomy_features
        return out


def build_care_arc(config: CAREARCConfig | None = None) -> CAREARC:
    return CAREARC(config)


def trainable_parameter_count(model: nn.Module) -> int:
    return sum(int(p.numel()) for p in model.parameters() if p.requires_grad)
