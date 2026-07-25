from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from myops.models.blocks import ConvNormAct2d


class CrossModalityFusion(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.att = nn.Sigmoid()
        self.conv = ConvNormAct2d(in_channels // 2 + out_channels * 3, out_channels)

    def forward(
        self, prev: torch.Tensor, skip_c0: torch.Tensor, skip_t2: torch.Tensor, skip_de: torch.Tensor,
    ) -> torch.Tensor:
        prev = self.up(prev)
        if prev.shape[-2:] != skip_de.shape[-2:]:
            prev = F.interpolate(prev, size=skip_de.shape[-2:], mode="bilinear", align_corners=False)
        att_c0 = self.att(skip_c0)
        att_t2 = self.att(skip_t2)
        att = torch.mean(torch.stack([att_c0, att_t2]), dim=0)
        de_gated = skip_de * att
        fused = torch.cat([prev, de_gated, att_c0, att_t2], dim=1)
        return self.conv(fused)


class MSFDecoder(nn.Module):
    def __init__(self, base_channels: int, out_channels: int, deep_supervision: bool = True) -> None:
        super().__init__()
        c = base_channels
        self.fusion3 = CrossModalityFusion(c * 8 * 3, c * 4)
        self.fusion2 = CrossModalityFusion(c * 4, c * 2)
        self.fusion1 = CrossModalityFusion(c * 2, c)

        self.out_head = nn.Conv2d(c, out_channels, kernel_size=1)
        self.deep_supervision = deep_supervision
        if deep_supervision:
            self.ds3 = nn.Conv2d(c * 4, out_channels, kernel_size=1)
            self.ds2 = nn.Conv2d(c * 2, out_channels, kernel_size=1)

    def forward(
        self,
        bottleneck: torch.Tensor,
        skips_lge: list[torch.Tensor],
        skips_c0: list[torch.Tensor],
        skips_t2: list[torch.Tensor],
        spg_gate: nn.Module | None = None,
        coarse_prior: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, list[torch.Tensor]]:
        d3 = self.fusion3(bottleneck, skips_c0[2], skips_t2[2], skips_lge[2])
        if spg_gate is not None and coarse_prior is not None:
            d3 = spg_gate(d3, coarse_prior)

        d2 = self.fusion2(d3, skips_c0[1], skips_t2[1], skips_lge[1])
        if spg_gate is not None and coarse_prior is not None:
            d2 = spg_gate(d2, coarse_prior)

        d1 = self.fusion1(d2, skips_c0[0], skips_t2[0], skips_lge[0])
        if spg_gate is not None and coarse_prior is not None:
            d1 = spg_gate(d1, coarse_prior)

        logits = self.out_head(d1)

        ds_logits: list[torch.Tensor] = []
        if self.deep_supervision:
            ds_logits.append(
                F.interpolate(self.ds3(d3), size=logits.shape[-2:], mode="bilinear", align_corners=False)
            )
            ds_logits.append(
                F.interpolate(self.ds2(d2), size=logits.shape[-2:], mode="bilinear", align_corners=False)
            )

        return logits, ds_logits
