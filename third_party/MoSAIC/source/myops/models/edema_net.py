from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class _ConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, stride=1, padding=1, bias=True),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, stride=1, padding=1, bias=True),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


class _UpConv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.up = nn.Sequential(
            nn.Upsample(scale_factor=2),
            nn.Conv2d(in_ch, out_ch, kernel_size=3, stride=1, padding=1, bias=True),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.up(x)


class _UNetEncoder(nn.Module):
    def __init__(self, in_ch: int) -> None:
        super().__init__()
        n1 = 64
        filters = [n1, n1 * 2, n1 * 4, n1 * 8, n1 * 16]

        self.Maxpool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.Maxpool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.Maxpool3 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.Maxpool4 = nn.MaxPool2d(kernel_size=2, stride=2)

        self.Conv1 = _ConvBlock(in_ch, filters[0])
        self.Conv2 = _ConvBlock(filters[0], filters[1])
        self.Conv3 = _ConvBlock(filters[1], filters[2])
        self.Conv4 = _ConvBlock(filters[2], filters[3])
        self.Conv5 = _ConvBlock(filters[3], filters[4])

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, ...]:
        e1 = self.Conv1(x)
        e2 = self.Conv2(self.Maxpool1(e1))
        e3 = self.Conv3(self.Maxpool2(e2))
        e4 = self.Conv4(self.Maxpool3(e3))
        e5 = self.Conv5(self.Maxpool4(e4))
        return e1, e2, e3, e4, e5


class _UNetDecoderPlus(nn.Module):
    def __init__(self, out_ch: int, deep_supervision: bool = False) -> None:
        super().__init__()
        n1 = 64
        filters = [n1, n1 * 2, n1 * 4, n1 * 8, n1 * 16]
        self.deep_supervision = deep_supervision

        self.Up5 = _UpConv(2 * filters[4], filters[3])
        self.Up_conv5 = _ConvBlock(3 * filters[3], filters[3])
        self.Up4 = _UpConv(filters[3], filters[2])
        self.Up_conv4 = _ConvBlock(3 * filters[2], filters[2])
        self.Up3 = _UpConv(filters[2], filters[1])
        self.Up_conv3 = _ConvBlock(3 * filters[1], filters[1])
        self.Up2 = _UpConv(filters[1], filters[0])
        self.Up_conv2 = _ConvBlock(3 * filters[0], filters[0])

        self.Conv = nn.Conv2d(filters[0], out_ch, kernel_size=1, stride=1, padding=0)
        self.active = nn.Softmax(dim=1)

        if deep_supervision:
            self.ds4 = nn.Conv2d(filters[2], out_ch, kernel_size=1)
            self.ds3 = nn.Conv2d(filters[1], out_ch, kernel_size=1)

    def forward(
        self, e_ref: tuple[torch.Tensor, ...], e: tuple[torch.Tensor, ...],
    ) -> torch.Tensor | tuple[torch.Tensor, list[torch.Tensor]]:
        d5 = torch.cat((e_ref[4].detach(), e[4]), dim=1)
        d5 = self.Up5(d5)
        d5 = torch.cat((e_ref[3].detach(), e[3], d5), dim=1)
        d5 = self.Up_conv5(d5)

        d4 = self.Up4(d5)
        d4 = torch.cat((e_ref[2].detach(), e[2], d4), dim=1)
        d4 = self.Up_conv4(d4)

        d3 = self.Up3(d4)
        d3 = torch.cat((e_ref[1].detach(), e[1], d3), dim=1)
        d3 = self.Up_conv3(d3)

        d2 = self.Up2(d3)
        d2 = torch.cat((e_ref[0].detach(), e[0], d2), dim=1)
        d2 = self.Up_conv2(d2)

        d1 = self.Conv(d2)
        out = self.active(d1)

        if self.deep_supervision and self.training:
            ds_out4 = self.active(F.interpolate(self.ds4(d4), size=out.shape[-2:], mode="bilinear", align_corners=False))
            ds_out3 = self.active(F.interpolate(self.ds3(d3), size=out.shape[-2:], mode="bilinear", align_corners=False))
            return out, [ds_out4, ds_out3]

        return out


class EdemaNet(nn.Module):
    """Edema segmentation network with dedicated T2 decoder (Stage 2b).

    Three encoders (LGE, C0, T2) with element-wise max cross-modal fusion
    and UNetDecoderPlus with detached reference features.

    Input: LGE [B,1,H,W], C0 [B,1,H,W], T2 [B,1,H,W], cardiac_mask [B,1,H,W]
    Output: softmax probabilities [B,3,H,W] -- (background, myo, edema)
    """

    def __init__(self, use_c0: bool = True, deep_supervision: bool = False) -> None:
        super().__init__()
        self.use_c0 = use_c0
        self.encoder_lge = _UNetEncoder(in_ch=2)
        self.encoder_t2 = _UNetEncoder(in_ch=2)
        if use_c0:
            self.encoder_c0 = _UNetEncoder(in_ch=2)
        self.decoder_t2 = _UNetDecoderPlus(out_ch=3, deep_supervision=deep_supervision)

    def forward(
        self, lge: torch.Tensor, c0: torch.Tensor, t2: torch.Tensor, cardiac_mask: torch.Tensor,
    ) -> torch.Tensor | tuple[torch.Tensor, list[torch.Tensor]]:
        f_lge = self.encoder_lge(torch.cat([lge, cardiac_mask], dim=1))
        f_t2 = self.encoder_t2(torch.cat([t2, cardiac_mask], dim=1))

        if self.use_c0:
            f_c0 = self.encoder_c0(torch.cat([c0, cardiac_mask], dim=1))
            e_ref = tuple(torch.max(f_lge[i], f_c0[i]) for i in range(5))
        else:
            e_ref = f_lge

        return self.decoder_t2(e_ref, f_t2)
