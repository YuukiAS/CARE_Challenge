from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from myops.models.blocks import ConvNormAct2d, UpBlock2d
from myops.models.coarse_net import CoarseNet
from myops.models.encoder import Decoder2D, Encoder2D


class MotionDecoder2D(nn.Module):
    def __init__(self, base_channels: int = 16, max_displacement: float = 0.25) -> None:
        super().__init__()
        c = int(base_channels)
        self.max_displacement = float(max_displacement)
        self.bottleneck = ConvNormAct2d(c * 16, c * 8)
        self.up3 = UpBlock2d(c * 8, c * 8, c * 4)
        self.up2 = UpBlock2d(c * 4, c * 4, c * 2)
        self.up1 = UpBlock2d(c * 2, c * 2, c)
        self.flow_head = nn.Conv2d(c, 2, kernel_size=1)

    def forward(self, ref_features: list[torch.Tensor], moving_features: list[torch.Tensor]) -> torch.Tensor:
        r1, r2, r3, rb = ref_features
        m1, m2, m3, mb = moving_features
        b = self.bottleneck(torch.cat([rb, mb], dim=1))
        d3 = self.up3(b, torch.cat([r3, m3], dim=1))
        d2 = self.up2(d3, torch.cat([r2, m2], dim=1))
        d1 = self.up1(d2, torch.cat([r1, m1], dim=1))
        return torch.tanh(self.flow_head(d1)) * self.max_displacement


def _warp_2d(source: torch.Tensor, flow: torch.Tensor) -> torch.Tensor:
    b, _, h, w = source.shape
    yy, xx = torch.meshgrid(
        torch.linspace(-1.0, 1.0, h, device=source.device, dtype=source.dtype),
        torch.linspace(-1.0, 1.0, w, device=source.device, dtype=source.dtype),
        indexing="ij",
    )
    base_grid = torch.stack([xx, yy], dim=-1).unsqueeze(0).expand(b, h, w, 2)
    grid = base_grid + flow.permute(0, 2, 3, 1)
    return F.grid_sample(source, grid, mode="bilinear", padding_mode="border", align_corners=True)


class CineHybridNet(nn.Module):
    """Cine-only hybrid motion/anatomy/pathology model for CineMyoPS.

    Input tensor layout [B, T + 1, H, W]:
        ch 0..T-1: ED-anchored selected cine frames
        ch T: coarse anatomy prior
    """

    def __init__(
        self,
        out_channels: int,
        base_channels: int = 16,
        num_frames: int = 20,
        max_displacement: float = 0.25,
    ) -> None:
        super().__init__()
        if out_channels != 3:
            raise ValueError(f"CineHybridNet expects 3 fine classes, got {out_channels}")
        self.num_frames = int(num_frames)
        self.frame_encoder = Encoder2D(1, int(base_channels))
        self.motion_decoder = MotionDecoder2D(int(base_channels), max_displacement=max_displacement)
        self.anatomy_decoder = Decoder2D(out_channels=2, base_channels=int(base_channels))
        self.pathology_head = CoarseNet(
            in_channels=5,
            out_channels=out_channels,
            base_channels=int(base_channels),
            deep_supervision=False,
        )
        self.temporal_fuse = nn.Conv2d(out_channels, out_channels, kernel_size=1)

    def _reshape_features(
        self, features: list[torch.Tensor], batch_size: int, num_frames: int,
    ) -> list[torch.Tensor]:
        reshaped = []
        for feature in features:
            c, h, w = feature.shape[1:]
            reshaped.append(feature.reshape(batch_size, num_frames, c, h, w))
        return reshaped

    def _features_at(self, features: list[torch.Tensor], frame_index: int) -> list[torch.Tensor]:
        return [level[:, frame_index] for level in features]

    def forward(self, image: torch.Tensor) -> dict[str, torch.Tensor | list[torch.Tensor]]:
        if image.shape[1] < self.num_frames + 1:
            raise ValueError(
                f"CineHybridNet input needs {self.num_frames + 1} channels, got {image.shape[1]}"
            )
        frames = image[:, : self.num_frames]
        coarse_prior = image[:, self.num_frames:self.num_frames + 1]
        b, t, h, w = frames.shape

        flat_frames = frames.reshape(b * t, 1, h, w)
        feature_levels = self._reshape_features(self.frame_encoder(flat_frames), b, t)
        ref_features = self._features_at(feature_levels, 0)

        frame_logits: list[torch.Tensor] = []
        anatomy_logits: list[torch.Tensor] = []
        warped_anatomy: list[torch.Tensor] = []
        warped_images: list[torch.Tensor] = []
        motion_fields: list[torch.Tensor] = []

        for frame_idx in range(t):
            moving_features = self._features_at(feature_levels, frame_idx)
            anatomy = self.anatomy_decoder(moving_features)
            if frame_idx == 0:
                flow = torch.zeros(b, 2, h, w, device=image.device, dtype=image.dtype)
            else:
                flow = self.motion_decoder(ref_features, moving_features)
                if flow.shape[-2:] != (h, w):
                    flow = F.interpolate(flow, size=(h, w), mode="bilinear", align_corners=False)

            anatomy_prob = torch.sigmoid(anatomy)
            warped_prob = _warp_2d(anatomy_prob, flow)
            warped_image = _warp_2d(frames[:, frame_idx:frame_idx + 1], flow)
            path_input = torch.cat([flow, warped_prob, coarse_prior], dim=1)
            path_logits = self.pathology_head(path_input)["logits"]

            anatomy_logits.append(anatomy)
            warped_anatomy.append(warped_prob)
            warped_images.append(warped_image)
            motion_fields.append(flow)
            frame_logits.append(path_logits)

        frame_logits_tensor = torch.stack(frame_logits, dim=1)
        logits = self.temporal_fuse(frame_logits_tensor.mean(dim=1))

        return {
            "logits": logits,
            "frame_logits": frame_logits_tensor,
            "anatomy_logits": torch.stack(anatomy_logits, dim=1),
            "warped_anatomy": torch.stack(warped_anatomy, dim=1),
            "warped_images": torch.stack(warped_images, dim=1),
            "motion_fields": torch.stack(motion_fields, dim=1),
            "ref_image": frames[:, 0:1],
        }
