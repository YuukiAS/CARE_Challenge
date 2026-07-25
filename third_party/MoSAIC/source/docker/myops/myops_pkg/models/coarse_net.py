from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from myops.models.blocks import ConvNormAct2d


class CoarseNet(nn.Module):
    """Standard 2D UNet for coarse anatomy segmentation (Stage 1)."""

    def __init__(
        self, in_channels: int, out_channels: int, base_channels: int = 24, deep_supervision: bool = True,
    ) -> None:
        super().__init__()
        c = int(base_channels)
        self.deep_supervision = bool(deep_supervision)

        self.enc1 = ConvNormAct2d(in_channels, c)
        self.enc2 = ConvNormAct2d(c, c * 2, stride=2)
        self.enc3 = ConvNormAct2d(c * 2, c * 4, stride=2)
        self.bottleneck = ConvNormAct2d(c * 4, c * 8, stride=2)

        self.up3 = nn.ConvTranspose2d(c * 8, c * 4, kernel_size=2, stride=2)
        self.dec3 = ConvNormAct2d(c * 8, c * 4)
        self.up2 = nn.ConvTranspose2d(c * 4, c * 2, kernel_size=2, stride=2)
        self.dec2 = ConvNormAct2d(c * 4, c * 2)
        self.up1 = nn.ConvTranspose2d(c * 2, c, kernel_size=2, stride=2)
        self.dec1 = ConvNormAct2d(c * 2, c)

        self.out_head = nn.Conv2d(c, out_channels, kernel_size=1)
        if self.deep_supervision:
            self.ds3 = nn.Conv2d(c * 4, out_channels, kernel_size=1)
            self.ds2 = nn.Conv2d(c * 2, out_channels, kernel_size=1)

    def _up(self, x: torch.Tensor, skip: torch.Tensor, up: nn.Module, conv: nn.Module) -> torch.Tensor:
        x = up(x)
        if x.shape[-2:] != skip.shape[-2:]:
            x = F.interpolate(x, size=skip.shape[-2:], mode="bilinear", align_corners=False)
        return conv(torch.cat([x, skip], dim=1))

    def forward(self, image: torch.Tensor) -> dict[str, torch.Tensor | list[torch.Tensor]]:
        e1 = self.enc1(image)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        b = self.bottleneck(e3)

        d3 = self._up(b, e3, self.up3, self.dec3)
        d2 = self._up(d3, e2, self.up2, self.dec2)
        d1 = self._up(d2, e1, self.up1, self.dec1)
        logits = self.out_head(d1)

        outputs: dict[str, torch.Tensor | list[torch.Tensor]] = {"logits": logits}
        if self.deep_supervision:
            outputs["deep_supervision"] = [
                F.interpolate(self.ds3(d3), size=logits.shape[-2:], mode="bilinear", align_corners=False),
                F.interpolate(self.ds2(d2), size=logits.shape[-2:], mode="bilinear", align_corners=False),
            ]
        return outputs
