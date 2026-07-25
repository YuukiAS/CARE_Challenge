from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from myops.models.blocks import ConvNormAct2d


class Encoder2D(nn.Module):
    def __init__(self, in_channels: int, base_channels: int) -> None:
        super().__init__()
        c = base_channels
        self.enc1 = ConvNormAct2d(in_channels, c)
        self.enc2 = ConvNormAct2d(c, c * 2, stride=2)
        self.enc3 = ConvNormAct2d(c * 2, c * 4, stride=2)
        self.bottleneck = ConvNormAct2d(c * 4, c * 8, stride=2)

    def forward(self, x: torch.Tensor) -> list[torch.Tensor]:
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        b = self.bottleneck(e3)
        return [e1, e2, e3, b]


class Decoder2D(nn.Module):
    def __init__(self, out_channels: int, base_channels: int) -> None:
        super().__init__()
        c = base_channels
        self.up3 = nn.ConvTranspose2d(c * 8, c * 4, kernel_size=2, stride=2)
        self.dec3 = ConvNormAct2d(c * 8, c * 4)
        self.up2 = nn.ConvTranspose2d(c * 4, c * 2, kernel_size=2, stride=2)
        self.dec2 = ConvNormAct2d(c * 4, c * 2)
        self.up1 = nn.ConvTranspose2d(c * 2, c, kernel_size=2, stride=2)
        self.dec1 = ConvNormAct2d(c * 2, c)
        self.out_head = nn.Conv2d(c, out_channels, kernel_size=1)

    def _up(self, x: torch.Tensor, skip: torch.Tensor, up: nn.Module, conv: nn.Module) -> torch.Tensor:
        x = up(x)
        if x.shape[-2:] != skip.shape[-2:]:
            x = F.interpolate(x, size=skip.shape[-2:], mode="bilinear", align_corners=False)
        return conv(torch.cat([x, skip], dim=1))

    def forward(self, features: list[torch.Tensor]) -> torch.Tensor:
        e1, e2, e3, b = features
        d3 = self._up(b, e3, self.up3, self.dec3)
        d2 = self._up(d3, e2, self.up2, self.dec2)
        d1 = self._up(d2, e1, self.up1, self.dec1)
        return self.out_head(d1)


class ReferenceDecoder2D(nn.Module):
    def __init__(self, out_channels: int, base_channels: int) -> None:
        super().__init__()
        c = base_channels
        self.up3 = nn.ConvTranspose2d(c * 8, c * 4, kernel_size=2, stride=2)
        self.dec3 = ConvNormAct2d(c * 4 + c * 4 + c * 4, c * 4)
        self.up2 = nn.ConvTranspose2d(c * 4, c * 2, kernel_size=2, stride=2)
        self.dec2 = ConvNormAct2d(c * 2 + c * 2 + c * 2, c * 2)
        self.up1 = nn.ConvTranspose2d(c * 2, c, kernel_size=2, stride=2)
        self.dec1 = ConvNormAct2d(c + c + c, c)
        self.out_head = nn.Conv2d(c, out_channels, kernel_size=1)

    def _up_ref(
        self, x: torch.Tensor, skip: torch.Tensor, ref: torch.Tensor,
        up: nn.Module, conv: nn.Module,
    ) -> torch.Tensor:
        x = up(x)
        if x.shape[-2:] != skip.shape[-2:]:
            x = F.interpolate(x, size=skip.shape[-2:], mode="bilinear", align_corners=False)
        return conv(torch.cat([x, skip, ref], dim=1))

    def forward(self, main_features: list[torch.Tensor], ref_features: list[torch.Tensor]) -> torch.Tensor:
        e1, e2, e3, b = main_features
        r1, r2, r3, rb = [f.detach() for f in ref_features]
        d3 = self._up_ref(b, e3, r3, self.up3, self.dec3)
        d2 = self._up_ref(d3, e2, r2, self.up2, self.dec2)
        d1 = self._up_ref(d2, e1, r1, self.up1, self.dec1)
        return self.out_head(d1)
