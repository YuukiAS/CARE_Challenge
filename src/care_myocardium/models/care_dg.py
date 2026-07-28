"""CARE-DG dual-pathology residual correction model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from torch import nn
import torch.nn.functional as F


SCAR_CHANNEL = 5
EDEMA_CHANNEL = 4
ANATOMY_CHANNELS = (0, 1, 2, 3)


def _conv_kernel(level: int) -> tuple[int, int, int]:
    return (1, 3, 3) if level <= 1 else (3, 3, 3)


class ResidualBlock3D(nn.Module):
    def __init__(self, channels: int, *, level: int) -> None:
        super().__init__()
        kernel = _conv_kernel(level)
        padding = tuple(k // 2 for k in kernel)
        self.block = nn.Sequential(
            nn.Conv3d(channels, channels, kernel, padding=padding, bias=False),
            nn.InstanceNorm3d(channels, affine=True),
            nn.SiLU(inplace=True),
            nn.Conv3d(channels, channels, kernel, padding=padding, bias=False),
            nn.InstanceNorm3d(channels, affine=True),
        )
        self.act = nn.SiLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(x + self.block(x))


class Stem3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, (1, 3, 3), padding=(0, 1, 1), bias=False),
            nn.InstanceNorm3d(out_channels, affine=True),
            nn.SiLU(inplace=True),
            ResidualBlock3D(out_channels, level=0),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Encoder3D(nn.Module):
    def __init__(self, in_channels: int, channels: tuple[int, int, int]) -> None:
        super().__init__()
        c0, c1, c2 = channels
        self.level0 = nn.Sequential(nn.Conv3d(in_channels, c0, 1), ResidualBlock3D(c0, level=0))
        self.down1 = nn.Sequential(
            nn.Conv3d(c0, c1, (1, 3, 3), stride=(1, 2, 2), padding=(0, 1, 1), bias=False),
            nn.InstanceNorm3d(c1, affine=True),
            nn.SiLU(inplace=True),
            ResidualBlock3D(c1, level=1),
        )
        self.down2 = nn.Sequential(
            nn.Conv3d(c1, c2, (3, 3, 3), stride=(1, 2, 2), padding=1, bias=False),
            nn.InstanceNorm3d(c2, affine=True),
            nn.SiLU(inplace=True),
            ResidualBlock3D(c2, level=2),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        s0 = self.level0(x)
        s1 = self.down1(s0)
        s2 = self.down2(s1)
        return s0, s1, s2


class PathologyDecoder(nn.Module):
    """Independent decoder producing FN/FP gates and bounded magnitudes."""

    def __init__(self, channels: tuple[int, int, int], out_channels: int = 4) -> None:
        super().__init__()
        c0, c1, c2 = channels
        self.up1 = nn.Sequential(
            nn.Conv3d(c2 + c1, 64, 3, padding=1, bias=False),
            nn.InstanceNorm3d(64, affine=True),
            nn.SiLU(inplace=True),
            ResidualBlock3D(64, level=1),
        )
        self.up0 = nn.Sequential(
            nn.Conv3d(64 + c0, 32, (1, 3, 3), padding=(0, 1, 1), bias=False),
            nn.InstanceNorm3d(32, affine=True),
            nn.SiLU(inplace=True),
            ResidualBlock3D(32, level=0),
        )
        self.head = nn.Conv3d(32, out_channels, 1)

    def forward(self, scales: tuple[torch.Tensor, torch.Tensor, torch.Tensor], *, margin_cap: float) -> dict[str, torch.Tensor]:
        s0, s1, s2 = scales
        u1 = F.interpolate(s2, size=s1.shape[-3:], mode="trilinear", align_corners=False)
        u1 = self.up1(torch.cat([u1, s1], dim=1))
        u0 = F.interpolate(u1, size=s0.shape[-3:], mode="trilinear", align_corners=False)
        feat = self.up0(torch.cat([u0, s0], dim=1))
        raw = self.head(feat)
        cap = float(margin_cap)
        return {
            "q_fn": torch.sigmoid(raw[:, 0:1]),
            "q_fp": torch.sigmoid(raw[:, 1:2]),
            "m_fn": cap * torch.sigmoid(raw[:, 2:3]),
            "m_fp": cap * torch.sigmoid(raw[:, 3:4]),
            "raw": raw,
            "raw_m_fn": raw[:, 2:3],
            "raw_m_fp": raw[:, 3:4],
        }


@dataclass(frozen=True)
class CAREDGConfig:
    image_channels: int = 3
    anchor_channels: int = 6
    stem_channels: int = 8
    context_channels: int = 16
    encoder_channels: tuple[int, int, int] = (32, 64, 96)
    scar_margin_cap: float = 4.0
    edema_margin_cap: float = 4.0


def _as_case_mask(mask: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    if mask.ndim == 1:
        mask = mask[:, None, None, None, None]
    elif mask.ndim == 2:
        mask = mask[:, :, None, None, None]
    if mask.shape[1] != 1:
        mask = mask[:, :1]
    return mask.to(device=reference.device, dtype=reference.dtype).expand(-1, 1, *reference.shape[-3:])


def _ensure_map(x: torch.Tensor | None, reference: torch.Tensor, default: float, *, name: str, strict: bool) -> torch.Tensor:
    if x is None:
        if strict:
            raise ValueError(f"{name} is required in formal CARE-DG mode")
        return reference.new_full((reference.shape[0], 1, *reference.shape[-3:]), float(default))
    if x.ndim == 2:
        x = x[:, :, None, None, None]
    if x.ndim == 4:
        x = x[:, None]
    if x.shape[-3:] != reference.shape[-3:]:
        x = F.interpolate(x.to(reference), size=reference.shape[-3:], mode="trilinear", align_corners=False)
    return x[:, :1].to(device=reference.device, dtype=reference.dtype)


def _availability_map(availability: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    if availability.ndim == 2:
        availability = availability[:, :, None, None, None]
    if availability.ndim != 5 or availability.shape[1] != 3:
        raise ValueError("availability must be [B,3] or [B,3,D,H,W]")
    return availability.to(device=reference.device, dtype=reference.dtype).expand(-1, -1, *reference.shape[-3:])


def _competitor_channels(
    anchor_logits: torch.Tensor,
    pathology_channel: int,
    *,
    competitor_channels: tuple[int, ...] | None = None,
) -> torch.Tensor:
    if competitor_channels is None:
        competitor_channels = tuple(c for c in range(anchor_logits.shape[1]) if c != int(pathology_channel))
    channels = torch.as_tensor(competitor_channels, device=anchor_logits.device, dtype=torch.long)
    local = anchor_logits.index_select(1, channels).argmax(dim=1, keepdim=True)
    return channels[local]


def apply_competitive_correction(
    anchor_logits: torch.Tensor,
    delta: torch.Tensor,
    support: torch.Tensor,
    pathology_channel: int,
    margin_cap: float,
    *,
    competitor_channels: tuple[int, ...] | None = None,
) -> torch.Tensor:
    correction = torch.clamp(delta, -float(margin_cap), float(margin_cap)) * support
    final = anchor_logits.clone()
    competitor = _competitor_channels(anchor_logits, pathology_channel, competitor_channels=competitor_channels)
    final[:, pathology_channel : pathology_channel + 1] = final[:, pathology_channel : pathology_channel + 1] + correction
    final.scatter_add_(1, competitor, -correction)
    return final


def apply_scar_priority_composition(
    anchor_logits: torch.Tensor,
    *,
    scar_delta: torch.Tensor,
    edema_delta: torch.Tensor,
    scar_support: torch.Tensor,
    edema_support: torch.Tensor,
    scar_margin_cap: float,
    edema_margin_cap: float,
    t2_mask: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    after_edema = apply_competitive_correction(
        anchor_logits,
        edema_delta,
        edema_support * t2_mask,
        EDEMA_CHANNEL,
        edema_margin_cap,
        competitor_channels=ANATOMY_CHANNELS,
    )
    final_logits = apply_competitive_correction(
        after_edema,
        scar_delta,
        scar_support,
        SCAR_CHANNEL,
        scar_margin_cap,
        competitor_channels=tuple(c for c in range(anchor_logits.shape[1]) if c != SCAR_CHANNEL),
    )
    return after_edema, final_logits


class CAREDG(nn.Module):
    """Dual-gated residual correction over frozen six-class nnU-Net anchors."""

    def __init__(self, config: CAREDGConfig | None = None) -> None:
        super().__init__()
        self.config = config or CAREDGConfig()
        c = self.config
        self.lge_stem = Stem3D(1, c.stem_channels)
        self.t2_stem = Stem3D(1, c.stem_channels)
        self.c0_stem = Stem3D(1, c.stem_channels)
        self.anchor_context = Stem3D(c.anchor_channels + 2, c.context_channels)
        encoder_in = c.stem_channels * 3 + c.context_channels + 3
        self.encoder = Encoder3D(encoder_in, c.encoder_channels)
        self.scar_decoder = PathologyDecoder(c.encoder_channels)
        self.edema_decoder = PathologyDecoder(c.encoder_channels)

    def forward(
        self,
        images: torch.Tensor,
        availability: torch.Tensor,
        anchor_logits: torch.Tensor,
        *,
        uncertainty: torch.Tensor | None = None,
        myocardium_support: torch.Tensor | None = None,
        edema_support: torch.Tensor | None = None,
        distance_to_myocardium: torch.Tensor | None = None,
        t2_present: torch.Tensor | None = None,
        strict_inputs: bool = False,
        anchor_value_kind: str | None = None,
        force_zero_correction: bool = False,
    ) -> dict[str, torch.Tensor]:
        if images.ndim != 5 or images.shape[1] != 3:
            raise ValueError("images must be [B,3,D,H,W] in LGE,T2,C0 order")
        if anchor_logits.ndim != 5 or anchor_logits.shape[1] != 6:
            raise ValueError("anchor_logits must be [B,6,D,H,W]")
        if images.shape[0] != anchor_logits.shape[0] or images.shape[-3:] != anchor_logits.shape[-3:]:
            raise ValueError("images and anchor_logits must share batch and spatial shape")
        if strict_inputs and anchor_value_kind not in {"logits", "log_probabilities"}:
            raise ValueError("formal CARE-DG mode requires anchor_value_kind='logits' or 'log_probabilities'")

        avail = _availability_map(availability, anchor_logits)
        unc = _ensure_map(uncertainty, anchor_logits, 0.0, name="uncertainty", strict=strict_inputs)
        dist = _ensure_map(distance_to_myocardium, anchor_logits, 0.0, name="distance_to_myocardium", strict=strict_inputs)
        scar_support = _ensure_map(myocardium_support, anchor_logits, 1.0, name="myocardium_support", strict=strict_inputs).clamp(0.0, 1.0)
        edema_zone_support = _ensure_map(edema_support, anchor_logits, 1.0, name="edema_support", strict=strict_inputs).clamp(0.0, 1.0)
        if t2_present is None:
            t2_present = availability[:, 1] if availability.ndim == 2 else availability[:, 1].flatten(1).amax(dim=1)
        t2_mask = _as_case_mask(t2_present, anchor_logits)

        stemmed = torch.cat(
            [
                self.lge_stem(images[:, 0:1] * avail[:, 0:1]),
                self.t2_stem(images[:, 1:2] * avail[:, 1:2]),
                self.c0_stem(images[:, 2:3] * avail[:, 2:3]),
            ],
            dim=1,
        )
        context = self.anchor_context(torch.cat([anchor_logits, unc, dist], dim=1))
        scales = self.encoder(torch.cat([stemmed, context, avail], dim=1))
        scar = self.scar_decoder(scales, margin_cap=self.config.scar_margin_cap)
        edema = self.edema_decoder(scales, margin_cap=self.config.edema_margin_cap)

        scar_delta_raw = scar["q_fn"] * scar["m_fn"] - scar["q_fp"] * scar["m_fp"]
        edema_delta_raw = edema["q_fn"] * edema["m_fn"] - edema["q_fp"] * edema["m_fp"]
        scar_delta = scar_delta_raw
        edema_delta = edema_delta_raw * t2_mask
        if force_zero_correction:
            scar_delta_raw = scar_delta_raw * 0
            edema_delta_raw = edema_delta_raw * 0
            scar_delta = scar_delta * 0
            edema_delta = edema_delta * 0
            scar = {**scar, "q_fn": scar["q_fn"] * 0, "q_fp": scar["q_fp"] * 0, "m_fn": scar["m_fn"] * 0, "m_fp": scar["m_fp"] * 0}
            edema = {**edema, "q_fn": edema["q_fn"] * 0, "q_fp": edema["q_fp"] * 0, "m_fn": edema["m_fn"] * 0, "m_fp": edema["m_fp"] * 0}

        after_edema, final_logits = apply_scar_priority_composition(
            anchor_logits,
            scar_delta=scar_delta,
            edema_delta=edema_delta,
            scar_support=scar_support,
            edema_support=edema_zone_support,
            scar_margin_cap=self.config.scar_margin_cap,
            edema_margin_cap=self.config.edema_margin_cap,
            t2_mask=t2_mask,
        )
        final_mask = final_logits.argmax(dim=1)
        scar_mask = final_mask == SCAR_CHANNEL
        edema_zone_mask = (final_mask == EDEMA_CHANNEL) | scar_mask
        pure_edema_mask = edema_zone_mask & ~scar_mask
        return {
            "anchor_logits": anchor_logits,
            "after_edema_logits": after_edema,
            "final_logits": final_logits,
            "final_logits_after_scar_priority": final_logits,
            "final_mask": final_mask,
            "scar_mask": scar_mask,
            "edema_zone_mask": edema_zone_mask,
            "pure_edema_mask": pure_edema_mask,
            "scar_delta_raw": scar_delta_raw,
            "edema_delta_raw": edema_delta_raw * t2_mask,
            "scar_delta": scar_delta * scar_support,
            "edema_delta": edema_delta * edema_zone_support * t2_mask,
            "scar_q_fn": scar["q_fn"],
            "scar_q_fp": scar["q_fp"],
            "scar_m_fn": scar["m_fn"],
            "scar_m_fp": scar["m_fp"],
            "edema_q_fn": edema["q_fn"] * t2_mask,
            "edema_q_fp": edema["q_fp"] * t2_mask,
            "edema_m_fn": edema["m_fn"] * t2_mask,
            "edema_m_fp": edema["m_fp"] * t2_mask,
            "scar_raw_m_fn": scar["raw_m_fn"],
            "scar_raw_m_fp": scar["raw_m_fp"],
            "edema_raw_m_fn": edema["raw_m_fn"],
            "edema_raw_m_fp": edema["raw_m_fp"],
            "t2_mask": t2_mask,
            "scar_support": scar_support,
            "edema_support": edema_zone_support,
        }


def build_care_dg(config: dict[str, Any] | CAREDGConfig | None = None) -> CAREDG:
    if isinstance(config, CAREDGConfig):
        cfg = config
    else:
        cfg = CAREDGConfig(**(config or {}))
    return CAREDG(cfg)
